import os
import sys

# Ensure project root is in path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from loguru import logger
from mcp.server.fastmcp import FastMCP

try:
    from api.telemetry import mission_manager
    from config.settings import get_settings
except ImportError:
    # If run directly as python api/mcp_server.py
    from telemetry import mission_manager

    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from config.settings import get_settings

# Ensure logs go to stderr so they don't corrupt the MCP stdout stream
logger.remove()
logger.add(sys.stderr, level="INFO")

settings = get_settings()

# Initialize FastMCP server
mcp = FastMCP("SuperFCC")


@mcp.tool()
async def get_mission_status() -> str:
    """Get the current mission telemetry, uptime, and active sessions from the live proxy."""
    import httpx

    port = os.getenv("PORT", "8082")
    base_url = f"http://localhost:{port}"
    token = os.getenv("ANTHROPIC_AUTH_TOKEN", "freecc")

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(
                f"{base_url}/v1/mission/status", headers={"x-api-key": token}
            )
            if resp.status_code == 200:
                return str(resp.json())
            return f"Error: Proxy returned status {resp.status_code}"
    except Exception as e:
        # Fallback to local if server is offline (though it will likely be 0)
        status = mission_manager.get_status()
        return f"Proxy Offline ({e}). Local state: {status}"


@mcp.tool()
async def reset_all_missions() -> str:
    """Abort all active proxy sessions and reset mission manager state on the live proxy."""
    import httpx

    port = os.getenv("PORT", "8082")
    base_url = f"http://localhost:{port}"
    token = os.getenv("ANTHROPIC_AUTH_TOKEN", "freecc")

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(
                f"{base_url}/v1/mission/stop", headers={"x-api-key": token}
            )
            if resp.status_code == 200:
                return "All missions have been reset on the live proxy."
            return f"Error: Proxy returned status {resp.status_code}"
    except Exception as e:
        return f"Failed to connect to proxy: {e}"


@mcp.tool()
async def update_settings(key: str, value: str) -> str:
    """Update dynamic engine settings on the live proxy (e.g., planning:on, thinking:off)."""
    import httpx

    port = os.getenv("PORT", "8082")
    base_url = f"http://localhost:{port}"
    token = os.getenv("ANTHROPIC_AUTH_TOKEN", "freecc")

    val_bool = value.lower() in ["on", "true", "1", "yes"]
    payload = {key: val_bool}

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(
                f"{base_url}/v1/config", json=payload, headers={"x-api-key": token}
            )
            if resp.status_code == 200:
                return f"Setting updated on live proxy: {key} = {val_bool}"
            return f"Error: Proxy returned status {resp.status_code}"
    except Exception as e:
        return f"Failed to connect to proxy: {e}"


@mcp.resource("config://current")
def get_current_config() -> str:
    """Read the current active engine intelligence configuration."""
    return str(settings.dict())


if __name__ == "__main__":
    mcp.run()
