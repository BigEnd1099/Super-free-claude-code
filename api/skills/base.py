from abc import ABC, abstractmethod
from typing import Any


class Skill(ABC):
    """Base class for all pluggable skills (Superpowers)."""

    @property
    @abstractmethod
    def name(self) -> str:
        """The tool name as seen by the LLM."""

    @property
    @abstractmethod
    def description(self) -> str:
        """Detailed description for LLM tool selection."""

    @property
    def input_schema(self) -> dict[str, Any]:
        """JSON Schema for the tool inputs."""
        return {
            "type": "object",
            "properties": {},
        }

    @property
    def path(self) -> str:
        """The filesystem path to the skill source."""
        return "internal"

    @property
    def version(self) -> str:
        """The version of the skill."""
        return "1.0.0"

    @abstractmethod
    async def execute(self, **kwargs: Any) -> str:
        """The actual logic of the superpower."""
