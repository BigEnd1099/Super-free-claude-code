import asyncio
from collections.abc import AsyncIterator, Callable
from typing import Any, TypeVar

from loguru import logger

from .exceptions import ProviderError

T = TypeVar("T")


async def with_resilience(
    func: Callable[..., Any],
    *args,
    max_retries: int = 3,
    fallback_func: Callable[..., Any] | None = None,
    **kwargs,
) -> Any:
    """Execute a provider function with retries and optional fallback.

    Supports both standard async functions and async generators.
    """
    last_error = None
    for attempt in range(max_retries):
        try:
            return await func(*args, **kwargs)
        except ProviderError as e:
            last_error = e
            if e.status_code == 429:  # Rate limit
                wait_time = 2**attempt
                logger.warning(
                    "Rate limit hit, retrying in {}s... (Attempt {})",
                    wait_time,
                    attempt + 1,
                )
                await asyncio.sleep(wait_time)
                continue
            if e.status_code >= 500:  # Server error
                logger.warning(
                    "Provider server error, retrying... (Attempt {})", attempt + 1
                )
                await asyncio.sleep(1)
                continue
            # Re-raise authentication or client errors immediately
            raise e
        except Exception as e:
            last_error = e
            logger.error("Unexpected error in resilient execution: {}", e)
            break

    if fallback_func:
        logger.info("Retries exhausted, switching to fallback provider...")
        try:
            return await fallback_func(*args, **kwargs)
        except Exception as e:
            logger.error("Fallback provider failed: {}", e)
            if last_error:
                raise last_error from e
            raise e

    if last_error:
        raise last_error
    raise ProviderError("Execution failed after retries", status_code=503)


async def with_resilient_stream(
    func: Callable[..., AsyncIterator[str]],
    *args,
    max_retries: int = 2,
    fallback_func: Callable[..., AsyncIterator[str]] | None = None,
    **kwargs,
) -> AsyncIterator[str]:
    """Execute a provider stream with retries and optional fallback.

    Note: Retrying a stream is only possible if no data has been yielded yet.
    """
    last_error = None
    for attempt in range(max_retries):
        try:
            # We can't easily retry a stream if it fails halfway.
            # This only handles initial connection failures.
            async for chunk in func(*args, **kwargs):
                yield chunk
            return  # Success
        except ProviderError as e:
            last_error = e
            if e.status_code in [429, 500, 502, 503, 504]:
                wait_time = 1.5**attempt
                logger.warning(
                    "Stream failed ({}). Retrying in {:.1f}s...",
                    e.status_code,
                    wait_time,
                )
                await asyncio.sleep(wait_time)
                continue
            raise e
        except Exception as e:
            last_error = e
            logger.error("Unexpected error in resilient stream: {}", e)
            break

    if fallback_func:
        logger.info("Stream retries exhausted, switching to fallback provider...")
        async for chunk in fallback_func(*args, **kwargs):
            yield chunk
        return

    if last_error:
        raise last_error
    raise ProviderError("Stream failed after retries", status_code=503)
