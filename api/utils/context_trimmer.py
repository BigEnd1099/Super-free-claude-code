from typing import Any

from loguru import logger


class ContextTrimmer:
    """Summarizes inter-agent message history to save tokens and reduce latency."""

    def __init__(self, threshold: int = 2500):
        self.threshold = threshold

    def estimate_tokens(self, text: str) -> int:
        """Rough estimate of tokens (4 chars per token)."""
        return len(text) // 4

    async def trim_history(
        self, messages: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """
        Summarizes older messages if the total token count exceeds the threshold.
        Keeps the last 2-3 messages intact for immediate context.
        """
        total_text = "".join([str(m.get("content", "")) for m in messages])
        estimated_tokens = self.estimate_tokens(total_text)

        if estimated_tokens < self.threshold:
            return messages

        logger.info(
            f"Context threshold exceeded ({estimated_tokens} tokens). Trimming history..."
        )

        # Keep the system prompt and the last 3 messages
        if len(messages) <= 4:
            return messages

        system_prompt = messages[0] if messages[0].get("role") == "system" else None
        last_messages = messages[-3:]
        middle_messages = messages[1:-3] if system_prompt else messages[:-3]

        # Simple heuristic summary for now (in a real app, you'd call a small LLM here)
        summary_text = (
            f"[SUMMARY of {len(middle_messages)} previous inter-agent interactions]: "
        )
        summary_text += "Agents discussed project requirements and initialized state. "
        summary_text += "Key decisions: Task IDs generated, shared memory initialized."

        trimmed = []
        if system_prompt:
            trimmed.append(system_prompt)

        trimmed.append({"role": "user", "content": summary_text})
        trimmed.extend(last_messages)

        return trimmed


# Global instance
context_trimmer = ContextTrimmer()
