"""
Claude Ultimate + Antigravity - Unified Proxy & Managed Agents
Unified entry point for free LLM access and local managed agents.
Run with: uv run uvicorn server:app --host 0.0.0.0 --port 8082
"""

from api.app import app, create_app

__all__ = ["app", "create_app"]

if __name__ == "__main__":
    import uvicorn

    from cli.process_registry import kill_all_best_effort
    from config.settings import get_settings

    settings = get_settings()
    try:
        # timeout_graceful_shutdown ensures uvicorn doesn't hang on task cleanup.
        uvicorn.run(
            app,
            host=settings.host,
            port=settings.port,
            log_level="debug",
            timeout_graceful_shutdown=5,
        )
    finally:
        # Safety net: cleanup subprocesses if lifespan shutdown doesn't fully run.
        kill_all_best_effort()
