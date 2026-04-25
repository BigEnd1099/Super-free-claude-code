"""OmX (Structured Architectural Planning) logic."""

import time
from typing import Any

from loguru import logger

from config.settings import Settings


async def run_omx_planning(
    prompt: str, model: str, settings: Settings, nim_client: Any = None
) -> tuple[str, int]:
    """Generate a structured architectural plan (OmX) for a complex task.

    Returns (planning_text, tokens).
    """
    if not settings.enable_planning_mode:
        return "", 0

    try:
        if nim_client is None:
            # Fallback for internal use if client isn't passed
            import httpx

            from providers.openai_compat import AsyncOpenAI

            nim_client = AsyncOpenAI(
                api_key=settings.nvidia_nim_api_key,
                base_url="https://integrate.api.nvidia.com/v1",
                timeout=httpx.Timeout(20.0, connect=2.0),
            )

        # Use a high-capacity model for architectural planning
        planning_model = "meta/llama-3.3-70b-instruct"

        logger.info("OmX_PLANNING: Generating strategic plan...")
        start_time = time.time()

        response = await nim_client.chat.completions.create(
            model=planning_model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are the Antigravity OmX Architect. Your goal is to provide a structured, "
                        "high-level architectural plan for the given coding task. "
                        "Format your response with the following sections:\n"
                        "1. OBJECTIVE: (1 sentence)\n"
                        "2. STRATEGY: (Key technical approach)\n"
                        "3. RISKS: (Edge cases or pitfalls)\n"
                        "4. EXECUTION: (Step-by-step logic)\n\n"
                        "Be extremely concise. Max 120 words total. Focus on root-cause engineering."
                    ),
                },
                {
                    "role": "user",
                    "content": prompt[:2000],  # Cap input
                },
            ],
            max_tokens=300,
            temperature=0.2,
        )

        plan = response.choices[0].message.content
        usage = getattr(response, "usage", None)
        tokens = getattr(usage, "total_tokens", 300) if usage else 300
        duration = time.time() - start_time

        logger.info(
            "OmX_PLANNING: Plan generated successfully in {:.2f}s. ({} tokens)",
            duration,
            tokens,
        )

        formatted_plan = (
            f"\n\n### <STRATEGIC_PLAN_OmX>\n{plan}\n### </STRATEGIC_PLAN_OmX>"
        )
        return formatted_plan, tokens

    except Exception as e:
        logger.warning(f"OmX_PLANNING_FAILED: {e}")
        return "", 0
