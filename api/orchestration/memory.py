import asyncio
from typing import Any

from loguru import logger


class SharedMemory:
    """A thread-safe 'Whiteboard' for agents to share state without context bloat."""

    def __init__(self):
        self._state: dict[str, Any] = {}
        self._lock = asyncio.Lock()

    async def set_task(self, key: str, value: Any) -> None:
        """Agents use this to post data to the whiteboard."""
        async with self._lock:
            self._state[key] = value
            logger.debug(f"Whiteboard updated: {key}")

    async def get_task(self, key: str) -> Any | None:
        """Agents use this to pull specific data into their context."""
        async with self._lock:
            return self._state.get(key)

    async def get_all_keys(self) -> list[str]:
        """Returns a list of available whiteboard keys so agents know what to look for."""
        async with self._lock:
            return list(self._state.keys())
