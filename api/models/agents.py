from typing import Any, Literal
from pydantic import BaseModel, Field

class AgentModelConfig(BaseModel):
    id: str
    speed: Literal["standard", "fast"] = "standard"

class Agent(BaseModel):
    id: str
    type: Literal["agent"] = "agent"
    name: str
    model: str | AgentModelConfig
    system: str | None = None
    description: str | None = None
    tools: list[dict[str, Any]] = []
    skills: list[str] = []
    mcp_servers: list[dict[str, Any]] = []
    callable_agents: list[dict[str, Any]] = []
    metadata: dict[str, Any] = {}
    version: int = 1
    created_at: str
    updated_at: str
    archived_at: str | None = None

class CreateAgentRequest(BaseModel):
    name: str
    model: str | AgentModelConfig
    system: str | None = None
    description: str | None = None
    tools: list[dict[str, Any]] | None = None
    skills: list[str] | None = None
    mcp_servers: list[dict[str, Any]] | None = None
    callable_agents: list[dict[str, Any]] | None = None
    metadata: dict[str, Any] | None = None

class AgentListResponse(BaseModel):
    data: list[dict[str, Any]]

class AgentVersionsResponse(BaseModel):
    data: list[Agent]
