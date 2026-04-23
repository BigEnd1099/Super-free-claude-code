"""Pydantic models for Anthropic-compatible requests."""

from enum import StrEnum
from typing import Any, Literal

from loguru import logger
from pydantic import BaseModel, field_validator, model_validator

from config.settings import Settings, get_settings


# =============================================================================
# Content Block Types
# =============================================================================
class Role(StrEnum):
    user = "user"
    assistant = "assistant"
    system = "system"


class ContentBlockText(BaseModel):
    type: Literal["text"]
    text: str


class ContentBlockImage(BaseModel):
    type: Literal["image"]
    source: dict[str, Any]


class ContentBlockToolUse(BaseModel):
    type: Literal["tool_use"]
    id: str
    name: str
    input: dict[str, Any]


class ContentBlockToolResult(BaseModel):
    type: Literal["tool_result"]
    tool_use_id: str
    content: str | list[Any] | dict[str, Any]


class ContentBlockThinking(BaseModel):
    type: Literal["thinking"]
    thinking: str


class SystemContent(BaseModel):
    type: Literal["text"]
    text: str


# =============================================================================
# Message Types
# =============================================================================
class Message(BaseModel):
    role: Literal["user", "assistant"]
    content: (
        str
        | list[
            ContentBlockText
            | ContentBlockImage
            | ContentBlockToolUse
            | ContentBlockToolResult
            | ContentBlockThinking
        ]
    )
    reasoning_content: str | None = None


class Tool(BaseModel):
    name: str
    description: str | None = None
    input_schema: dict[str, Any]


class ThinkingConfig(BaseModel):
    enabled: bool = True


# =============================================================================
# Request Models
# =============================================================================
class MessagesRequest(BaseModel):
    model: str | dict[str, Any]
    max_tokens: int | None = None
    messages: list[Message]
    system: str | list[SystemContent] | None = None
    stop_sequences: list[str] | None = None
    stream: bool | None = True
    temperature: float | None = None
    top_p: float | None = None
    top_k: int | None = None
    metadata: dict[str, Any] | None = None
    tools: list[Tool] | None = None
    tool_choice: dict[str, Any] | None = None
    thinking: ThinkingConfig | None = None
    extra_body: dict[str, Any] | None = None
    original_model: str | None = None
    resolved_provider_model: str | None = None

    @model_validator(mode="after")
    def map_model(self) -> MessagesRequest:
        """Map any Claude model name to the configured model (model-aware)."""
        settings = get_settings()
        if self.original_model is None:
            self.original_model = self.model

        model_id = (
            self.model
            if isinstance(self.model, str)
            else self.model.get("id", "unknown")
        )
        resolved_full = settings.resolve_model(model_id)
        self.resolved_provider_model = resolved_full

        target_model = Settings.parse_model_name(resolved_full)
        if isinstance(self.model, str):
            self.model = target_model
        else:
            self.model["id"] = target_model

        if target_model != model_id:
            logger.debug(f"MODEL MAPPING: '{model_id}' -> '{target_model}'")

        return self


class TokenCountRequest(BaseModel):
    model: str
    messages: list[Message]
    system: str | list[SystemContent] | None = None
    tools: list[Tool] | None = None
    thinking: ThinkingConfig | None = None
    tool_choice: dict[str, Any] | None = None

    @field_validator("model")
    @classmethod
    def validate_model_field(
        cls, v: str | dict[str, Any], info
    ) -> str | dict[str, Any]:
        """Map any Claude model name to the configured model (model-aware)."""
        settings = get_settings()
        model_id = v if isinstance(v, str) else v.get("id", "unknown")
        resolved_full = settings.resolve_model(model_id)
        target_model = Settings.parse_model_name(resolved_full)

        if isinstance(v, str):
            return target_model
        else:
            v["id"] = target_model
            return v
