from loguru import logger

from config.settings import Settings


class ModelRouter:
    """Intelligent model router for tiered routing and demotion."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.quota_usage = {}  # Model -> Tokens used

    def route(self, task_type: str, payload: dict) -> str:
        """Determines the best model for the given task and payload."""

        if task_type in ["background", "metadata", "graph_scan"]:
            logger.info(f"ROUTER: Demoting {task_type} to Flash/Haiku")
            return self.settings.model_haiku or "gemini-1.5-flash"

        is_planning = (
            payload.get("metadata", {}).get("mode") == "planning"
            or "plan" in str(payload.get("messages", [])[-1].get("content", "")).lower()
        )

        if is_planning and self.settings.enable_planning_mode:
            logger.info("ROUTER: Routing planning task to High-Tier (Opus/Sonnet)")
            return (
                self.settings.model_opus
                or self.settings.model_sonnet
                or "claude-3-opus"
            )

        return self.settings.model_sonnet or self.settings.model or "claude-3-sonnet"

    def track_usage(self, model: str, tokens: int):
        """Tracks token usage for quota-aware scheduling."""
        self.quota_usage[model] = self.quota_usage.get(model, 0) + tokens

        # If model is near quota (simulated), recommend switch
        if self.quota_usage[model] > 1000000:  # 1M tokens limit
            logger.warning(f"ROUTER: Model {model} is near quota limit.")


router = None


def get_router(settings: Settings) -> ModelRouter:
    global router
    if router is None:
        router = ModelRouter(settings)
    return router
