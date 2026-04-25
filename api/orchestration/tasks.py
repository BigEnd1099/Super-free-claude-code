import asyncio
from collections.abc import Callable, Coroutine
from typing import Any

from loguru import logger

from providers.rate_limit import GlobalRateLimiter


class AsyncTaskManager:
    """Manages parallel tool execution with backoff and concurrency limits."""

    def __init__(self, max_concurrent: int = 3):
        # Local concurrency limit for parallel tool blocks
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.rate_limiter = GlobalRateLimiter.get_instance()

    async def _execute_with_backoff(
        self, task_func: Callable[[], Coroutine], max_retries: int = 3
    ) -> Any:
        """Executes a task with jittered exponential backoff for 429s."""
        # We use the existing execute_with_retry if possible, or wrap it.
        # Since task_func is already a coroutine creation, we just call it.

        try:
            return await self.rate_limiter.execute_with_retry(
                lambda: task_func(), max_retries=max_retries
            )
        except Exception as e:
            logger.error(f"Task failed after retries: {e}")
            raise

    async def dispatch_parallel(
        self, tasks: list[Callable[[], Coroutine]]
    ) -> list[Any]:
        """Dispatches multiple agent tasks concurrently."""

        async def bounded_task(task):
            async with self.semaphore:
                return await self._execute_with_backoff(task)

        logger.info(f"Dispatching {len(tasks)} tasks in parallel...")
        results = await asyncio.gather(
            *(bounded_task(t) for t in tasks), return_exceptions=True
        )
        return results
