import time

from loguru import logger
from pydantic import BaseModel


class AccountSession(BaseModel):
    account_id: str
    access_token: str
    refresh_token: str | None = None
    expires_at: float
    is_active: bool = True
    rate_limited_until: float = 0
    quota_remaining: int = 1000
    last_used: float = 0


class AuthManager:
    """Manages multiple Antigravity/Google account sessions and rotation."""

    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, "initialized"):
            self.sessions: dict[str, AccountSession] = {}
            self.initialized = True

    def add_session(self, session: AccountSession):
        self.sessions[session.account_id] = session
        logger.info(f"AUTH_MANAGER: Added session for account {session.account_id}")

    def get_best_session(self) -> AccountSession | None:
        """Returns the healthiest session based on quota and rate limits."""
        now = time.time()
        available = [
            s
            for s in self.sessions.values()
            if s.is_active and s.rate_limited_until < now and s.expires_at > now
        ]

        if not available:
            logger.warning("AUTH_MANAGER: No healthy sessions available!")
            return None

        # Sort by quota remaining (descending) and last used (ascending)
        available.sort(key=lambda x: (-x.quota_remaining, x.last_used))

        best = available[0]
        best.last_used = now
        return best

    def report_rate_limit(self, account_id: str, retry_after: int = 60):
        if account_id in self.sessions:
            self.sessions[account_id].rate_limited_until = time.time() + retry_after
            logger.warning(
                f"AUTH_MANAGER: Account {account_id} rate limited for {retry_after}s"
            )

    def update_quota(self, account_id: str, remaining: int):
        if account_id in self.sessions:
            self.sessions[account_id].quota_remaining = remaining

    def get_status(self) -> list[dict]:
        """Returns the status of all managed accounts for the dashboard."""
        now = time.time()
        return [
            {
                "id": s.account_id,
                "active": s.is_active,
                "healthy": s.rate_limited_until < now and s.expires_at > now,
                "quota": s.quota_remaining,
                "expires_in": int(s.expires_at - now) if s.expires_at > now else 0,
            }
            for s in self.sessions.values()
        ]


auth_manager = AuthManager()
