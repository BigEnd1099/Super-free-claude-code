"""FastAPI route handlers."""

import traceback
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import StreamingResponse
from loguru import logger

from config.settings import Settings
from providers.common import get_user_facing_error_message
from providers.exceptions import InvalidRequestError, ProviderError

from .dependencies import get_provider_for_type, get_settings, require_api_key
from .models.anthropic import MessagesRequest, TokenCountRequest
from .models.responses import ModelResponse, ModelsListResponse, TokenCountResponse
from .models.agents import AgentListResponse, AgentVersionsResponse, CreateAgentRequest
from .agents_db import agents_db
from .optimization_handlers import try_optimizations
from .request_utils import get_token_count

router = APIRouter()


SUPPORTED_CLAUDE_MODELS = [
    ModelResponse(
        id="claude-opus-4-20250514",
        display_name="Claude Opus 4",
        created_at="2025-05-14T00:00:00Z",
    ),
    ModelResponse(
        id="claude-sonnet-4-20250514",
        display_name="Claude Sonnet 4",
        created_at="2025-05-14T00:00:00Z",
    ),
    ModelResponse(
        id="claude-haiku-4-20250514",
        display_name="Claude Haiku 4",
        created_at="2025-05-14T00:00:00Z",
    ),
    ModelResponse(
        id="claude-3-opus-20240229",
        display_name="Claude 3 Opus",
        created_at="2024-02-29T00:00:00Z",
    ),
    ModelResponse(
        id="claude-3-5-sonnet-20241022",
        display_name="Claude 3.5 Sonnet",
        created_at="2024-10-22T00:00:00Z",
    ),
    ModelResponse(
        id="claude-3-haiku-20240307",
        display_name="Claude 3 Haiku",
        created_at="2024-03-07T00:00:00Z",
    ),
    ModelResponse(
        id="claude-3-5-haiku-20241022",
        display_name="Claude 3.5 Haiku",
        created_at="2024-10-22T00:00:00Z",
    ),
]


def _probe_response(allow: str) -> Response:
    """Return an empty success response for compatibility probes."""
    return Response(status_code=204, headers={"Allow": allow})


# =============================================================================
# Routes
# =============================================================================
@router.post("/v1/messages")
async def create_message(
    request_data: MessagesRequest,
    raw_request: Request,
    settings: Settings = Depends(get_settings),
    _auth=Depends(require_api_key),
):
    """Create a message (always streaming)."""

    try:
        if not request_data.messages:
            raise InvalidRequestError("messages cannot be empty")

        optimized = try_optimizations(request_data, settings)
        if optimized is not None:
            return optimized
        # Apply model/agent override if present in request state
        override = getattr(raw_request.state, "model_override", None)
        if override:
            if override.startswith("agent_"):
                agent = agents_db.get_agent(override)
                if agent:
                    logger.info("AGENT_OVERRIDE: id={} name={}", override, agent["name"])
                    request_data.resolved_provider_model = agent["model"]
                    # Prepend agent system prompt if present
                    if agent.get("system"):
                        if isinstance(request_data.system, str):
                            request_data.system = f"{agent['system']}\n\n{request_data.system}"
                        elif isinstance(request_data.system, list):
                            from .models.anthropic import SystemContent
                            request_data.system.insert(0, SystemContent(type="text", text=agent["system"]))
                        else:
                            request_data.system = agent["system"]
                else:
                    logger.warning("AGENT_NOT_FOUND: id={}", override)
            else:
                logger.info("MODEL_OVERRIDE: model={}", override)
                request_data.resolved_provider_model = override

        # Resolve provider from the model-aware mapping
        resolved_model = request_data.resolved_provider_model or settings.model
        if "/" not in resolved_model:
            logger.warning("MODEL_WITHOUT_PROVIDER: model={} - defaulting to nvidia_nim", resolved_model)
            resolved_model = f"nvidia_nim/{resolved_model}"
            request_data.resolved_provider_model = resolved_model

        provider_type = Settings.parse_provider_type(resolved_model)
        provider = get_provider_for_type(provider_type)

        request_id = f"req_{uuid.uuid4().hex[:12]}"
        logger.info(
            "API_REQUEST: request_id={} model={} messages={}",
            request_id,
            request_data.model,
            len(request_data.messages),
        )
        logger.debug("FULL_PAYLOAD [{}]: {}", request_id, request_data.model_dump())

        input_tokens = get_token_count(
            request_data.messages, request_data.system, request_data.tools
        )
        return StreamingResponse(
            provider.stream_response(
                request_data,
                input_tokens=input_tokens,
                request_id=request_id,
            ),
            media_type="text/event-stream",
            headers={
                "X-Accel-Buffering": "no",
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            },
        )

    except ProviderError:
        raise
    except Exception as e:
        logger.error(f"Error: {e!s}\n{traceback.format_exc()}")
        raise HTTPException(
            status_code=getattr(e, "status_code", 500),
            detail=get_user_facing_error_message(e),
        ) from e


@router.api_route("/v1/messages", methods=["HEAD", "OPTIONS"])
async def probe_messages(_auth=Depends(require_api_key)):
    """Respond to Claude compatibility probes for the messages endpoint."""
    return _probe_response("POST, HEAD, OPTIONS")


@router.post("/v1/messages/count_tokens")
async def count_tokens(request_data: TokenCountRequest, _auth=Depends(require_api_key)):
    """Count tokens for a request."""
    request_id = f"req_{uuid.uuid4().hex[:12]}"
    with logger.contextualize(request_id=request_id):
        try:
            tokens = get_token_count(
                request_data.messages, request_data.system, request_data.tools
            )
            logger.info(
                "COUNT_TOKENS: request_id={} model={} messages={} input_tokens={}",
                request_id,
                getattr(request_data, "model", "unknown"),
                len(request_data.messages),
                tokens,
            )
            return TokenCountResponse(input_tokens=tokens)
        except Exception as e:
            logger.error(
                "COUNT_TOKENS_ERROR: request_id={} error={}\n{}",
                request_id,
                get_user_facing_error_message(e),
                traceback.format_exc(),
            )
            raise HTTPException(
                status_code=500, detail=get_user_facing_error_message(e)
            ) from e


@router.api_route("/v1/messages/count_tokens", methods=["HEAD", "OPTIONS"])
async def probe_count_tokens(_auth=Depends(require_api_key)):
    """Respond to Claude compatibility probes for the token count endpoint."""
    return _probe_response("POST, HEAD, OPTIONS")


@router.get("/")
async def root(
    settings: Settings = Depends(get_settings), _auth=Depends(require_api_key)
):
    """Root endpoint."""
    return {
        "status": "ok",
        "provider": settings.provider_type,
        "model": settings.model,
        "mapping": {
            "opus": settings.model_opus,
            "sonnet": settings.model_sonnet,
            "haiku": settings.model_haiku,
        },
        "ui": "/ui"
    }


@router.api_route("/", methods=["HEAD", "OPTIONS"])
async def probe_root(_auth=Depends(require_api_key)):
    """Respond to compatibility probes for the root endpoint."""
    return _probe_response("GET, HEAD, OPTIONS")


@router.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


@router.api_route("/health", methods=["HEAD", "OPTIONS"])
async def probe_health():
    """Respond to compatibility probes for the health endpoint."""
    return _probe_response("GET, HEAD, OPTIONS")


@router.get("/v1/models", response_model=ModelsListResponse)
async def list_models(_auth=Depends(require_api_key)):
    """List the Claude model ids this proxy advertises for compatibility."""
    return ModelsListResponse(
        data=SUPPORTED_CLAUDE_MODELS,
        first_id=SUPPORTED_CLAUDE_MODELS[0].id if SUPPORTED_CLAUDE_MODELS else None,
        has_more=False,
        last_id=SUPPORTED_CLAUDE_MODELS[-1].id if SUPPORTED_CLAUDE_MODELS else None,
    )


# =============================================================================
# Auth & User Mocks (Claude Code Compatibility)
# =============================================================================

@router.get("/v1/users/me")
async def users_me(_auth=Depends(require_api_key)):
    """Mock user info for Claude Code."""
    return {
        "id": "user_antigravity_01",
        "email": "antigravity@local.dev",
        "name": "Antigravity User",
        "created_at": "2024-01-01T00:00:00Z"
    }

@router.post("/v1/login")
@router.post("/v1/auth/token")
async def mock_login():
    """Mock login success."""
    return {
        "token": "freecc",
        "expires_at": "2099-01-01T00:00:00Z"
    }

@router.get("/v1/auth/status")
async def mock_auth_status():
    """Mock auth status."""
    return {"status": "authenticated"}


@router.post("/stop")
async def stop_cli(request: Request, _auth=Depends(require_api_key)):
    """Stop all CLI sessions and pending tasks."""
    handler = getattr(request.app.state, "message_handler", None)
    if not handler:
        # Fallback if messaging not initialized
        cli_manager = getattr(request.app.state, "cli_manager", None)
        if cli_manager:
            await cli_manager.stop_all()
            logger.info("STOP_CLI: source=cli_manager cancelled_count=N/A")
            return {"status": "stopped", "source": "cli_manager"}
        raise HTTPException(status_code=503, detail="Messaging system not initialized")

    count = await handler.stop_all_tasks()
    logger.info("STOP_CLI: source=handler cancelled_count={}", count)
    return {"status": "stopped", "cancelled_count": count}


# =============================================================================
# Managed Agents Routes
# =============================================================================

@router.get("/agents", response_model=AgentListResponse)
@router.get("/v1/agents", response_model=AgentListResponse)
async def list_agents(_auth=Depends(require_api_key)):
    """List all registered agents."""
    return AgentListResponse(data=agents_db.get_all_agents())


@router.post("/agents")
@router.post("/v1/agents")
async def create_agent(request_data: CreateAgentRequest, _auth=Depends(require_api_key)):
    """Create a new agent persona."""
    agent_id = f"agent_{uuid.uuid4().hex[:12]}"
    agent = agents_db.create_agent(agent_id, request_data.model_dump())
    logger.info("AGENT_CREATED: id={} name={}", agent_id, agent["name"])
    return agent


@router.post("/agents/{agent_id}")
async def update_agent(
    agent_id: str, request_data: dict, _auth=Depends(require_api_key)
):
    """Update an existing agent persona (creates a new version)."""
    agent = agents_db.update_agent(agent_id, request_data)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    logger.info("AGENT_UPDATED: id={} version={}", agent_id, agent["version"])
    return agent


@router.get("/agents/{agent_id}/versions", response_model=AgentVersionsResponse)
async def list_agent_versions(agent_id: str, _auth=Depends(require_api_key)):
    """List all versions of a specific agent."""
    versions = agents_db.get_agent_versions(agent_id)
    if versions is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    return AgentVersionsResponse(data=versions)


@router.post("/agents/{agent_id}/archive")
async def archive_agent(agent_id: str, _auth=Depends(require_api_key)):
    """Archive an agent persona."""
    agent = agents_db.archive_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    logger.info("AGENT_ARCHIVED: id={}", agent_id)
    return agent


@router.post("/config/mapping")
async def update_mapping(
    request_data: dict, settings: Settings = Depends(get_settings), _auth=Depends(require_api_key)
):
    """Update model mapping configuration in-memory."""
    if "opus" in request_data:
        settings.model_opus = request_data["opus"]
    if "sonnet" in request_data:
        settings.model_sonnet = request_data["sonnet"]
    if "haiku" in request_data:
        settings.model_haiku = request_data["haiku"]
    
    logger.info("MAPPING_UPDATED: opus={} sonnet={} haiku={}", 
                settings.model_opus, settings.model_sonnet, settings.model_haiku)
    return {"status": "updated", "mapping": {
        "opus": settings.model_opus,
        "sonnet": settings.model_sonnet,
        "haiku": settings.model_haiku
    }}
