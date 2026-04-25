from loguru import logger

from .memory import SharedMemory
from .tasks import AsyncTaskManager


class TeamState:
    """Holds the memory and active agents for a single session."""

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.memory = SharedMemory()
        self.active_agents: list[str] = []


class AgentTeamManager:
    """Session-isolated registry that manages Missions."""

    def __init__(self):
        self._sessions: dict[str, TeamState] = {}
        self.task_manager = AsyncTaskManager(max_concurrent=3)

    def get_or_create_session(self, session_id: str) -> TeamState:
        """Retrieves or creates a dedicated state for the given session."""
        if session_id not in self._sessions:
            logger.info(f"Initializing new Agent Team session: {session_id}")
            self._sessions[session_id] = TeamState(session_id)
        return self._sessions[session_id]

    def clear_session(self, session_id: str) -> None:
        """Cleans up the session when the mission is complete."""
        if session_id in self._sessions:
            del self._sessions[session_id]
            logger.info(f"Cleared session: {session_id}")


# Global instance for use in routes
team_manager = AgentTeamManager()
