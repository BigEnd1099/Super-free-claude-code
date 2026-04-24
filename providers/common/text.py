"""Shared text extraction utilities."""

from typing import Any


def extract_text_from_content(content: Any) -> str:
    """Extract concatenated text from message content (str or list of content blocks)."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            text = getattr(block, "text", "")
            if text and isinstance(text, str):
                parts.append(text)
        return "".join(parts)
    return ""


COMMON_PREAMBLES = [
    "Certainly!",
    "I can help with that.",
    "I understand.",
    "Sure thing!",
    "As an AI,",
    "I'll be happy to",
    "Here is",
    "Let me",
    "I have",
    "I'd be glad to",
    "Absolutely!",
]


class PreambleStripper:
    """Buffers and strips common AI preambles from streaming text."""

    def __init__(self, enabled: bool = True, preambles: list[str] | None = None):
        self.enabled = enabled
        self.preambles = preambles or COMMON_PREAMBLES
        self.buffer = ""
        self.done = not enabled
        # Preambles are usually short (max 50-100 chars)
        self.max_buffer_len = 120

    def feed(self, delta: str) -> str:
        """Feed a delta and return the potentially stripped text."""
        if self.done:
            return delta

        self.buffer += delta

        # Keep buffering until we have enough to make a decision
        if len(self.buffer) < self.max_buffer_len:
            return ""

        return self._strip()

    def flush(self) -> str:
        """Flush the buffer and return any remaining text."""
        if self.done:
            return ""
        return self._strip()

    def _strip(self) -> str:
        """Internal stripping logic."""
        result = self.buffer
        for p in self.preambles:
            # Handle variations with spaces/newlines
            if result.lstrip().startswith(p):
                # Remove the preamble and any immediate whitespace/newlines after it
                stripped = result.lstrip()[len(p) :].lstrip()
                result = stripped
                break

        self.done = True
        self.buffer = ""
        return result
