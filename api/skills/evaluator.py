import json
from typing import Any

from loguru import logger

from api.dependencies import get_provider_for_type
from config.settings import get_settings

from .base import Skill


class EvaluatorSkill(Skill):
    """
    A skill that evaluates code quality and architectural alignment.
    Uses a GAN-style 'Critique' mechanism to identify potential bugs or deviations.
    """

    @property
    def name(self) -> str:
        return "evaluate_code"

    @property
    def description(self) -> str:
        return (
            "Critically evaluate a code snippet against a set of requirements or specifications. "
            "Use this to identify bugs, security flaws, or architectural deviations BEFORE finalizing an implementation."
        )

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "The code snippet to evaluate.",
                },
                "specification": {
                    "type": "string",
                    "description": "The requirements or technical spec the code should follow.",
                },
                "focus_areas": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Specific areas to focus on (e.g., 'security', 'performance', 'DRY').",
                },
            },
            "required": ["code", "specification"],
        }

    async def execute(self, **kwargs: Any) -> str:
        code = kwargs.get("code")
        spec = kwargs.get("specification")
        focus = kwargs.get("focus_areas", ["logic", "structure", "alignment"])

        settings = get_settings()
        # Use the primary provider (likely NIM)
        provider = get_provider_for_type(settings.provider_type)

        # Build a prompt for the evaluation
        prompt = (
            f"You are a Senior Software Architect. Critically evaluate the following code against the provided specification.\n\n"
            f"### SPECIFICATION:\n{spec}\n\n"
            f"### CODE TO EVALUATE:\n{code}\n\n"
            f"### FOCUS AREAS:\n{', '.join(focus)}\n\n"
            f"Please provide:\n"
            f"1. A Score (0-10) for architectural alignment.\n"
            f"2. A list of potential bugs or edge cases.\n"
            f"3. Specific refactoring suggestions.\n"
            f"4. A final 'PASS' or 'FAIL' recommendation."
        )

        # We need a Request object-like structure for stream_response
        class MockRequest:
            def __init__(self, model, messages):
                self.model = model
                self.messages = messages
                self.thinking = type("obj", (object,), {"enabled": False})()
                self.stream = True

        class MockMessage:
            def __init__(self, role, content):
                self.role = role
                self.content = content

        mock_request = MockRequest(
            model=settings.model, messages=[MockMessage(role="user", content=prompt)]
        )

        full_response = ""
        try:
            # stream_response yields Anthropic-style SSE events
            async for event in provider.stream_response(mock_request):
                if event.startswith("data: "):
                    try:
                        data = json.loads(event[6:])
                        if data.get("type") == "content_block_delta":
                            delta = data.get("delta", {})
                            if delta.get("type") == "text_delta":
                                full_response += delta.get("text", "")
                    except Exception:
                        continue
        except Exception as e:
            logger.error(f"EvaluatorSkill failed to call provider: {e}")
            return f"EVALUATION_ERROR: Could not complete critique. Error: {e!s}"

        return f"CRITIQUE_RESULTS:\n\n{full_response}"
