"""FastAPI route handlers."""

import asyncio
import json
import time
import traceback
import uuid
from typing import Any

import psutil
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import StreamingResponse
from loguru import logger

from config.settings import Settings
from providers.common import get_user_facing_error_message
from providers.exceptions import InvalidRequestError, ProviderError

from .agents_db import agents_db
from .auth.routes import router as auth_router
from .dependencies import (
    check_depth,
    get_provider_for_type,
    get_settings,
    require_api_key,
    update_provider_configs,
)
from .graph.routes import router as graph_router
from .models.agents import AgentListResponse, AgentVersionsResponse, CreateAgentRequest
from .models.anthropic import MessagesRequest, TokenCountRequest
from .models.responses import ModelResponse, ModelsListResponse, TokenCountResponse
from .models.skills import SkillListResponse
from .optimization_handlers import try_optimizations
from .orchestration.manager import team_manager
from .planning import run_omx_planning
from .request_utils import get_token_count
from .skills.loader import skill_loader
from .telemetry import mission_manager
from .utils.context_trimmer import context_trimmer

router = APIRouter()
router.include_router(graph_router)
router.include_router(auth_router)


@router.get("/pulse")
async def pulse_stream(request: Request):
    """Stream server stats (CPU, Memory, Uptime) for the dashboard."""

    async def event_generator():
        start_time = getattr(request.app.state, "start_time", time.time())
        while True:
            try:
                stats = {
                    "cpu": psutil.cpu_percent(),
                    "memory": psutil.virtual_memory().percent,
                    "uptime": int(time.time() - start_time),
                    "status": "healthy",
                }
                yield f"data: {json.dumps(stats)}\n\n"
            except Exception as e:
                logger.error(f"Pulse error: {e}")
                yield f"data: {json.dumps({'status': 'error', 'message': str(e)})}\n\n"
            await asyncio.sleep(1)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


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


# SHADOW INTELLIGENCE ASSETS: Persistent client for connection pooling
_NIM_CLIENT: Any = None


async def get_nim_client(settings: Settings):
    global _NIM_CLIENT
    if _NIM_CLIENT is None:
        import httpx

        from providers.openai_compat import AsyncOpenAI

        # Connection pooling enabled by default in AsyncOpenAI/httpx
        _NIM_CLIENT = AsyncOpenAI(
            api_key=settings.nvidia_nim_api_key,
            base_url="https://integrate.api.nvidia.com/v1",
            timeout=httpx.Timeout(10.0, connect=2.0),
        )
    return _NIM_CLIENT


async def run_shadow_intelligence(
    prompt: str, model: str, settings: Settings
) -> tuple[str, int]:
    """Analyze prompt in background using a 70B model with connection pooling. Returns (intel, tokens)."""
    if not settings.enable_hyper_analysis:
        return "", 0

    try:
        client = await get_nim_client(settings)

        # Use the 70B resilient model for intelligence
        analysis_model = "meta/llama-3.3-70b-instruct"

        logger.info("HYPER_ANALYSIS: Generating shadow intelligence...")
        response = await client.chat.completions.create(
            model=analysis_model,
            messages=[
                {
                    "role": "system",
                    "content": "You are the Antigravity Shadow Intelligence. Provide 3 extremely brief 'Hyper-Insights' (Context, Risk, Strategy) for the given coding task. Max 60 words total.",
                },
                {
                    "role": "user",
                    "content": prompt[:1000],  # Cap input
                },
            ],
            max_tokens=150,
            temperature=0.1,
        )

        intel = response.choices[0].message.content
        tokens = response.usage.total_tokens if hasattr(response, "usage") else 150

        logger.info(
            "HYPER_ANALYSIS: Intelligence generated successfully. ({} tokens)", tokens
        )
        return (
            f"\n\n### <MISSION_INTEL_BY_ANTIGRAVITY>\n{intel}\n### </MISSION_INTEL_BY_ANTIGRAVITY>",
            tokens,
        )
    except Exception as e:
        logger.warning(f"HYPER_ANALYSIS_FAILED: {e}")
        return "", 0


def perturb_prompt(text: str) -> str:
    """Adversarial Mode (Parseltongue) - Perturb sensitive words to bypass filters."""
    # Comprehensive homoglyph mapping
    homoglyphs = {
        "a": "а",  # cyrillic a # noqa: RUF001
        "e": "е",  # cyrillic e # noqa: RUF001
        "i": "і",  # cyrillic i # noqa: RUF001
        "o": "о",  # cyrillic o # noqa: RUF001
        "p": "р",  # cyrillic p # noqa: RUF001
        "c": "с",  # cyrillic c # noqa: RUF001
        "y": "у",  # cyrillic y # noqa: RUF001
        "x": "х",  # cyrillic x # noqa: RUF001
        "s": "ѕ",  # macedonian dze # noqa: RUF001
        "k": "κ",  # greek kappa
        "n": "ո",  # armenian o # noqa: RUF001
        "v": "ν",  # greek nu # noqa: RUF001
    }
    # Targeted words that often trigger filters
    sensitive_words = [
        "system",
        "root",
        "password",
        "hack",
        "bypass",
        "exploit",
        "secret",
        "private",
        "admin",
        "sudo",
        "jailbreak",
        "override",
        "credential",
        "token",
        "auth",
        "login",
        "vulnerability",
    ]

    words = text.split()
    for i, word in enumerate(words):
        # Remove punctuation for matching
        clean_word = "".join(c for c in word.lower() if c.isalnum())
        if clean_word in sensitive_words:
            # Replace characters with homoglyphs, preserving original case if no homoglyph exists
            # Note: The homoglyph map only contains lowercase keys.
            perturbed = ""
            for char in word:
                lower_char = char.lower()
                if lower_char in homoglyphs:
                    # We use the lowercase homoglyph for both cases for simplicity,
                    # as many homoglyphs are visually similar in both cases or
                    # uppercase equivalents aren't as common in the map.
                    perturbed += homoglyphs[lower_char]
                else:
                    perturbed += char
            words[i] = perturbed

    return " ".join(words)


def strip_preambles(text: str) -> str:
    """Raw Mode (STM) - Strip hedges and preambles."""
    preambles = [
        "Certainly!",
        "I can help with that.",
        "I understand.",
        "Sure thing!",
        "As an AI,",
        "I'll be happy to",
        "Here is",
        "Let me",
        "I have",
    ]
    cleaned = text
    for p in preambles:
        if cleaned.strip().startswith(p):
            cleaned = cleaned.replace(p, "", 1).strip()
    return cleaned


# =============================================================================
# Mission Management (Collaborative Intelligence)
# =============================================================================


# Mission Manager imported from .telemetry


@router.get("/v1/mission/status")
async def get_mission_status():
    return mission_manager.get_status()


@router.get("/v1/health/rate-limit")
async def get_rate_limit_health():
    from providers.rate_limit import GlobalRateLimiter

    limiter = GlobalRateLimiter.get_instance()
    return limiter.get_usage_metrics()


@router.post("/v1/mission/stop")
async def stop_missions():
    """Abort all active missions and reset the mission manager."""
    mission_manager.active_sessions.clear()
    mission_manager.change_log.clear()
    mission_manager.tool_count = 0
    mission_manager.total_tokens = 0
    mission_manager.total_cost = 0.0
    mission_manager.model_stats.clear()
    logger.info("MISSION_MANAGER: Reset all metrics and sessions.")
    return {"status": "success", "message": "All missions reset."}


# =============================================================================
# Orchestration & Whiteboard
# =============================================================================
@router.post("/v1/orchestration/whiteboard/set")
async def whiteboard_set(key: str, value: Any, request: Request):
    """Post data to the shared whiteboard."""
    session_id = request.headers.get("x-session-id", "default")
    session = team_manager.get_or_create_session(session_id)
    await session.memory.set_task(key, value)
    return {"status": "success", "key": key}


@router.get("/v1/orchestration/whiteboard/get")
async def whiteboard_get(key: str, request: Request):
    """Retrieve data from the shared whiteboard."""
    session_id = request.headers.get("x-session-id", "default")
    session = team_manager.get_or_create_session(session_id)
    value = await session.memory.get_task(key)
    return {"key": key, "value": value}


@router.get("/v1/orchestration/whiteboard/keys")
async def whiteboard_keys(request: Request):
    """List all available whiteboard keys."""
    session_id = request.headers.get("x-session-id", "default")
    session = team_manager.get_or_create_session(session_id)
    keys = await session.memory.get_all_keys()
    return {"keys": keys}


# =============================================================================
# Routes
# =============================================================================
@router.post("/v1/messages")
async def create_message(
    request_data: MessagesRequest,
    raw_request: Request,
    settings: Settings = Depends(get_settings),
    _auth=Depends(require_api_key),
    _depth: int = Depends(check_depth),
):
    """Create a message (always streaming)."""

    try:
        if not request_data.messages:
            raise InvalidRequestError("messages cannot be empty")

        # MISSION CONTROL: Detect tool results in the request
        for msg in request_data.messages:
            if msg.role == "user" and isinstance(msg.content, list):
                from .models.anthropic import ContentBlockToolResult

                for block in msg.content:
                    if isinstance(block, ContentBlockToolResult):
                        import asyncio

                        from .websockets import manager

                        asyncio.create_task(
                            manager.broadcast(
                                {
                                    "type": "tool_result",
                                    "tool_use_id": block.tool_use_id,
                                    "status": "RECEIVED_BY_ARCHITECT",
                                }
                            )
                        )

        optimized = try_optimizations(request_data, settings)
        if optimized is not None:
            return optimized

        # Inject dynamically loaded skills (Superpowers)
        if skill_loader.skills:
            if not request_data.tools:
                request_data.tools = []

            for skill_def in skill_loader.get_tool_definitions():
                if not any(t.name == skill_def["name"] for t in request_data.tools):
                    from .models.anthropic import Tool

                    request_data.tools.append(Tool(**skill_def))

        # Apply context trimming for inter-agent efficiency
        msg_dicts = [m.model_dump() for m in request_data.messages]
        trimmed_dicts = await context_trimmer.trim_history(msg_dicts)
        if len(trimmed_dicts) != len(msg_dicts):
            from .models.anthropic import Message

            request_data.messages = [Message(**m) for m in trimmed_dicts]

        # Apply model/agent override if present in request state
        override = getattr(raw_request.state, "model_override", None)
        if override:
            if override.startswith("agent_"):
                agent = agents_db.get_agent(override)
                if agent:
                    logger.info(
                        "AGENT_OVERRIDE: id={} name={}", override, agent["name"]
                    )

                    # Broadcast Orchestration Event
                    import asyncio

                    from .websockets import manager

                    asyncio.create_task(
                        manager.broadcast(
                            {
                                "type": "orchestration",
                                "agent": agent["name"],
                                "action": "INJECT_PERSONA",
                                "status": "SUCCESS",
                            }
                        )
                    )

                    # Inject callable agents as tools
                    callable_agents = agent.get("callable_agents") or []
                    if callable_agents:
                        if not request_data.tools:
                            request_data.tools = []

                        agent_tools_desc = []
                        for ca in callable_agents:
                            ca_id = ca["id"]
                            ca_name = ca["name"]
                            tool_name = f"call_agent_{ca_id.replace('agent_', '')}"

                            # Check if tool already exists
                            if not any(t.name == tool_name for t in request_data.tools):
                                from .models.anthropic import Tool

                                request_data.tools.append(
                                    Tool(
                                        name=tool_name,
                                        description=f"Call specialized agent: {ca_name}. Use this for tasks requiring {ca_name}'s expertise.",
                                        input_schema={
                                            "type": "object",
                                            "properties": {
                                                "prompt": {
                                                    "type": "string",
                                                    "description": "The specific instruction or question for the agent.",
                                                }
                                            },
                                            "required": ["prompt"],
                                        },
                                    )
                                )
                                agent_tools_desc.append(f"- {tool_name}: {ca_name}")

                        if agent_tools_desc:
                            orchestration_prompt = (
                                "\n\n### Agent Orchestration:\n"
                                "You have access to specialized sub-agents. To use them, call their respective tools. "
                                "The results will be provided back to you.\n"
                                + "\n".join(agent_tools_desc)
                            )
                            if isinstance(request_data.system, str):
                                request_data.system += orchestration_prompt
                            elif isinstance(request_data.system, list):
                                from .models.anthropic import SystemContent

                                request_data.system.append(
                                    SystemContent(
                                        type="text", text=orchestration_prompt
                                    )
                                )
                            else:
                                request_data.system = orchestration_prompt

                    request_data.resolved_provider_model = agent["model"]
                    # Prepend agent system prompt if present
                    if agent.get("system"):
                        if isinstance(request_data.system, str):
                            request_data.system = (
                                f"{agent['system']}\n\n{request_data.system}"
                            )
                        elif isinstance(request_data.system, list):
                            from .models.anthropic import SystemContent

                            request_data.system.insert(
                                0, SystemContent(type="text", text=agent["system"])
                            )
                        else:
                            request_data.system = agent["system"]
                else:
                    logger.warning("AGENT_NOT_FOUND: id={}", override)
            else:
                logger.info("MODEL_OVERRIDE: model={}", override)
                request_data.resolved_provider_model = override

        # Resolve provider from the model-aware mapping
        resolved_model = request_data.resolved_provider_model

        if not resolved_model:
            from providers.common.router import get_router

            router_instance = get_router(settings)

            # Determine task type
            task_type = "standard"
            if request_data.metadata and request_data.metadata.get("background"):
                task_type = "background"

            resolved_model = router_instance.route(task_type, request_data.model_dump())
            logger.info("ROUTER: Tiered routing selected model={}", resolved_model)
        else:
            resolved_model = resolved_model or settings.model

        # Define request_id early for shadow intelligence/planning logging
        request_id = f"req_{uuid.uuid4().hex[:12]}"

        # HYPER-ANALYSIS: Shadow Intelligence Phase
        if settings.enable_hyper_analysis and request_data.messages:
            last_msg = request_data.messages[-1].content
            prompt_text = ""
            if isinstance(last_msg, str):
                prompt_text = last_msg
            elif isinstance(last_msg, list):
                for block in last_msg:
                    if getattr(block, "type", None) == "text":
                        prompt_text += getattr(block, "text", "")
                    elif isinstance(block, dict) and block.get("type") == "text":
                        prompt_text += block.get("text", "")

            if prompt_text:
                shadow_intel, shadow_tokens = await run_shadow_intelligence(
                    prompt_text, resolved_model, settings
                )
                if shadow_intel:
                    mission_manager.log_tokens(
                        shadow_tokens,
                        model="llama-3.3-70b",
                        request_id=request_id if "request_id" in locals() else None,
                    )
                    if isinstance(request_data.system, str):
                        request_data.system += shadow_intel
                    elif isinstance(request_data.system, list):
                        from .models.anthropic import SystemContent

                        request_data.system.append(
                            SystemContent(type="text", text=shadow_intel)
                        )

        # OmX: Structured Architectural Planning Phase
        if settings.enable_planning_mode and request_data.messages:
            last_msg = request_data.messages[-1].content
            prompt_text = ""
            if isinstance(last_msg, str):
                prompt_text = last_msg
            elif isinstance(last_msg, list):
                for block in last_msg:
                    if getattr(block, "type", None) == "text":
                        prompt_text += getattr(block, "text", "")
                    elif isinstance(block, dict) and block.get("type") == "text":
                        prompt_text += block.get("text", "")

            if prompt_text:
                nim_client = await get_nim_client(settings)
                omx_plan, omx_tokens = await run_omx_planning(
                    prompt_text, resolved_model, settings, nim_client=nim_client
                )
                if omx_plan:
                    mission_manager.log_tokens(
                        omx_tokens,
                        model="llama-3.3-70b",
                        request_id=request_id if "request_id" in locals() else None,
                    )
                    if isinstance(request_data.system, str):
                        request_data.system += omx_plan
                    elif isinstance(request_data.system, list):
                        from .models.anthropic import SystemContent

                        request_data.system.append(
                            SystemContent(type="text", text=omx_plan)
                        )
                    else:
                        request_data.system = omx_plan

        # Adversarial Mode: Perturb User Messages
        if settings.enable_adversarial_mode:
            for msg in request_data.messages:
                if msg.role == "user":
                    if isinstance(msg.content, str):
                        msg.content = perturb_prompt(msg.content)
                    elif isinstance(msg.content, list):
                        for block in msg.content:
                            from api.models.anthropic import ContentBlockText

                            if isinstance(block, ContentBlockText):
                                block.text = perturb_prompt(block.text)
                            elif (
                                isinstance(block, dict) and block.get("type") == "text"
                            ):
                                block["text"] = perturb_prompt(block["text"])
        if "/" not in resolved_model:
            logger.warning(
                "MODEL_WITHOUT_PROVIDER: model={} - defaulting to nvidia_nim",
                resolved_model,
            )
            resolved_model = f"nvidia_nim/{resolved_model}"
            request_data.resolved_provider_model = resolved_model

        provider_type = Settings.parse_provider_type(resolved_model)
        provider = get_provider_for_type(provider_type)

        # Configure fallback (e.g. NVIDIA NIM -> OpenRouter)
        fallback_provider = None
        if provider_type == "nvidia_nim" and settings.open_router_api_key:
            import contextlib

            with contextlib.suppress(Exception):
                fallback_provider = get_provider_for_type("open_router")

        from providers.resilience import with_resilient_stream

        # MISSION CONTROL: Start session
        mission_manager.start_session(request_id, resolved_model)

        logger.info(
            "API_REQUEST: request_id={} model={} messages={}",
            request_id,
            request_data.model,
            len(request_data.messages),
        )

        input_tokens = get_token_count(
            request_data.messages, request_data.system, request_data.tools
        )
        mission_manager.log_tokens(
            input_tokens, model=resolved_model, request_id=request_id
        )
        if "router_instance" in locals():
            router_instance.track_usage(resolved_model, input_tokens)

        import asyncio

        from .websockets import manager

        asyncio.create_task(
            manager.broadcast(
                {
                    "type": "traffic",
                    "method": "POST",
                    "path": "/v1/messages",
                    "model": resolved_model,
                    "tokens": input_tokens,
                    "status": "STREAMING",
                    "request_id": request_id,
                }
            )
        )

        # NEURAL SELF-CORRECTION LOOP
        # This wrapper allows the proxy to intercept tool calls and potentially
        # auto-retry if specific patterns are detected (e.g. sub-agent failure)
        async def recursive_telemetry_wrapper(gen):
            """Intercept tool calls and execute internal tools (Stress Test)."""
            try:
                active_tool_call = None
                async for chunk in gen:
                    # Mission Control pulse
                    # OPTIMIZATION: Only parse JSON if the chunk contains specific neural markers
                    if (
                        '"type": "tool_use"' in chunk
                        or '"type": "message_stop"' in chunk
                    ):
                        try:
                            data_str = chunk.split("data: ", 1)[1]
                            data = json.loads(data_str)

                            # Handle tool use
                            if (
                                data.get("type") == "content_block_start"
                                and data.get("content_block", {}).get("type")
                                == "tool_use"
                            ):
                                active_tool_call = data["content_block"]
                                mission_manager.log_tool(
                                    request_id,
                                    active_tool_call["name"],
                                    active_tool_call.get("input", {}),
                                )
                                mission_manager.log_event(
                                    request_id,
                                    "tool_use",
                                    {
                                        "name": active_tool_call["name"],
                                        "input": active_tool_call.get("input", {}),
                                    },
                                )

                            # Handle usage/tokens
                            if data.get("type") == "message_stop":
                                usage = data.get("message", {}).get("usage", {})
                                if usage.get("output_tokens"):
                                    mission_manager.log_tokens(
                                        usage["output_tokens"],
                                        model=resolved_model,
                                        request_id=request_id,
                                    )
                                    if "router_instance" in locals():
                                        router_instance.track_usage(
                                            resolved_model, usage["output_tokens"]
                                        )

                            # NEURAL VERIFICATION: Thinking Signature
                            if settings.enable_thinking and (
                                data.get("type") == "content_block_delta"
                                or data.get("type") == "content_block_start"
                            ):
                                content = ""
                                if data.get("delta", {}).get("text"):
                                    content = data["delta"]["text"]
                                elif data.get("content_block", {}).get("text"):
                                    content = data["content_block"]["text"]

                                if content:
                                    mission_manager.verify_thinking(request_id, content)
                        except Exception:
                            pass
                    yield chunk
            finally:
                # CRITICAL: Always end session to prevent 'Ghost Sessions'
                mission_manager.end_session(request_id)

        # Priming: Get the first chunk to catch immediate errors (401, 429, etc.)
        # before the StreamingResponse starts and sends 200 OK headers.
        full_gen = recursive_telemetry_wrapper(
            with_resilient_stream(
                provider.stream_response,
                request_data,
                input_tokens=input_tokens,
                request_id=request_id,
                fallback_func=fallback_provider.stream_response
                if fallback_provider
                else None,
            )
        )

        try:
            # We use __aiter__() and __anext__() to manually pull the first chunk.
            # This will execute code up to the first 'yield' in the provider.
            iterator = full_gen.__aiter__()
            first_chunk = await iterator.__anext__()
        except StopAsyncIteration:
            # Handle empty stream case
            return StreamingResponse(
                iter([]),
                media_type="text/event-stream",
            )
        except Exception:
            # Re-raise to be caught by the outer except blocks and return correct status code
            raise

        async def combined_generator():
            yield first_chunk
            async for chunk in iterator:
                yield chunk

        return StreamingResponse(
            combined_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    except ProviderError as e:
        # MISSION CONTROL: Broadcast failure
        import asyncio

        from .websockets import manager

        asyncio.create_task(
            manager.broadcast(
                {
                    "type": "tool_use",
                    "tool": "PROVIDER_SYSTEM",
                    "status": "INTERCEPTED_FAILURE",
                    "error": str(e),
                    "request_id": request_id if "request_id" in locals() else "unknown",
                }
            )
        )
        if "request_id" in locals():
            mission_manager.log_event(request_id, "error", {"message": str(e)})
            mission_manager.end_session(request_id, success=False)
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
    active_model = settings.model
    if mission_manager.active_sessions:
        # Use the model of the most recently started active session
        latest_session = list(mission_manager.active_sessions.values())[-1]
        active_model = latest_session.get("model", active_model)

    return {
        "status": "ok",
        "provider": settings.provider_type,
        "model": active_model,
        "mapping": {
            "opus": settings.model_opus,
            "sonnet": settings.model_sonnet,
            "haiku": settings.model_haiku,
        },
        "total_tokens": mission_manager.total_tokens,
        "total_cost": round(mission_manager.total_cost, 4),
        "tool_count": mission_manager.tool_count,
        "settings": {
            "hyper_analysis": settings.enable_hyper_analysis,
            "thinking": settings.enable_thinking,
            "adversarial": settings.enable_adversarial_mode,
            "raw_mode": settings.enable_raw_mode,
            "planning": settings.enable_planning_mode,
        },
        "ui": "/ui",
    }


@router.post("/v1/config")
async def update_config(
    payload: dict,
    settings: Settings = Depends(get_settings),
    _auth=Depends(require_api_key),
):
    """Update global settings dynamically."""
    if "hyper_analysis" in payload:
        settings.enable_hyper_analysis = bool(payload["hyper_analysis"])

    if "thinking" in payload:
        settings.enable_thinking = bool(payload["thinking"])

    if "adversarial" in payload:
        settings.enable_adversarial_mode = bool(payload["adversarial"])

    if "raw_mode" in payload:
        settings.enable_raw_mode = bool(payload["raw_mode"])

    if "planning" in payload:
        settings.enable_planning_mode = bool(payload["planning"])

    update_provider_configs(settings)
    return {
        "status": "success",
        "settings": {
            "hyper_analysis": settings.enable_hyper_analysis,
            "thinking": settings.enable_thinking,
            "adversarial": settings.enable_adversarial_mode,
            "raw_mode": settings.enable_raw_mode,
            "planning": settings.enable_planning_mode,
        },
    }


@router.get("/v1/config")
async def get_config(
    settings: Settings = Depends(get_settings),
    _auth=Depends(require_api_key),
):
    """Get current dynamic settings."""
    return {
        "hyper_analysis": settings.enable_hyper_analysis,
        "thinking": settings.enable_thinking,
        "adversarial": settings.enable_adversarial_mode,
        "raw_mode": settings.enable_raw_mode,
        "planning": settings.enable_planning_mode,
        "provider": settings.provider_type,
        "model": settings.model,
    }


@router.api_route("/", methods=["HEAD", "OPTIONS"])
async def probe_root(_auth=Depends(require_api_key)):
    """Respond to compatibility probes for the root endpoint."""
    return _probe_response("GET, HEAD, OPTIONS")


@router.get("/health")
@router.get("/v1/health")
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
        "created_at": "2024-01-01T00:00:00Z",
    }


@router.post("/v1/login")
@router.post("/v1/auth/token")
async def mock_login():
    """Mock login success."""
    return {"token": "freecc", "expires_at": "2099-01-01T00:00:00Z"}


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
async def create_agent(
    request_data: CreateAgentRequest, _auth=Depends(require_api_key)
):
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
    from .models.agents import Agent

    return AgentVersionsResponse(data=[Agent(**v) for v in versions])


@router.post("/agents/{agent_id}/archive")
async def archive_agent(agent_id: str, _auth=Depends(require_api_key)):
    """Archive an agent persona."""
    agent = agents_db.archive_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    logger.info("AGENT_ARCHIVED: id={}", agent_id)
    return agent


@router.get("/v1/skills/catalog")
async def get_skills_catalog(
    category: str | None = None, _auth=Depends(require_api_key)
):
    from .skills.catalog import catalog

    if category:
        return {"skills": catalog.get_skills_by_category(category)}
    return {"skills": catalog.get_all_skills(), "bundles": catalog.bundles}


@router.get("/v1/skills/search")
async def search_skills(query: str, _auth=Depends(require_api_key)):
    from .skills.catalog import catalog

    return {"skills": catalog.search_skills(query)}


@router.get("/v1/skills", response_model=SkillListResponse)
async def list_skills(
    settings: Settings = Depends(get_settings), _auth=Depends(require_api_key)
):
    """List available skills from the unified skill loader."""
    skills = []
    try:
        from .models.skills import SkillInfo

        for name, skill in skill_loader.skills.items():
            try:
                skills.append(
                    SkillInfo(
                        id=str(name),
                        name=str(skill.name or name),
                        description=str(skill.description or "No description"),
                        path=str(skill.path or "unknown"),
                        version=str(getattr(skill, "version", "1.0.0")),
                        category=str(getattr(skill, "category", "Uncategorized")),
                        tags=list(getattr(skill, "tags", [])),
                    )
                )
            except Exception as se:
                logger.warning(f"Skipping invalid skill {name}: {se}")
    except Exception as e:
        logger.error(f"Error listing skills: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve skills: {e!s}"
        ) from None

    return SkillListResponse(data=skills)


@router.post("/config/mapping")
async def update_mapping(
    request_data: dict,
    settings: Settings = Depends(get_settings),
    _auth=Depends(require_api_key),
):
    """Update model mapping configuration in-memory."""
    if "opus" in request_data:
        settings.model_opus = request_data["opus"]
    if "sonnet" in request_data:
        settings.model_sonnet = request_data["sonnet"]
    if "haiku" in request_data:
        settings.model_haiku = request_data["haiku"]

    logger.info(
        "MAPPING_UPDATED: opus={} sonnet={} haiku={}",
        settings.model_opus,
        settings.model_sonnet,
        settings.model_haiku,
    )
    return {
        "status": "updated",
        "mapping": {
            "opus": settings.model_opus,
            "sonnet": settings.model_sonnet,
            "haiku": settings.model_haiku,
        },
    }
