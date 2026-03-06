"""Agent configuration schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# Requests
# ---------------------------------------------------------------------------


class AgentCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    system_prompt: str | None = None
    llm_provider: str | None = Field(None, max_length=64)
    llm_model: str | None = Field(None, max_length=128)
    temperature: float | None = Field(None, ge=0.0, le=2.0)
    max_tokens: int | None = Field(None, ge=1)
    tools_enabled: list[uuid.UUID] | None = Field(default_factory=list)


class AgentUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    system_prompt: str | None = None
    llm_provider: str | None = Field(None, max_length=64)
    llm_model: str | None = Field(None, max_length=128)
    temperature: float | None = Field(None, ge=0.0, le=2.0)
    max_tokens: int | None = Field(None, ge=1)
    tools_enabled: list[uuid.UUID] | None = None


# ---------------------------------------------------------------------------
# Responses
# ---------------------------------------------------------------------------


class AgentResponse(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    name: str
    description: str | None = None
    system_prompt: str | None = None
    llm_provider: str | None = None
    llm_model: str | None = None
    temperature: float | None = None
    max_tokens: int | None = None
    tools_enabled: list[uuid.UUID] | None = None
    fallback_agent_id: uuid.UUID | None = None
    is_active: bool
    metadata: dict[str, Any] | None = Field(None, alias="metadata_")
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


# ---------------------------------------------------------------------------
# Agent testing
# ---------------------------------------------------------------------------


class AgentTestRequest(BaseModel):
    message: str = Field(..., min_length=1)


class AgentTestResponse(BaseModel):
    response: str
    latency_ms: float = Field(..., description="Round-trip time in milliseconds")
    tokens_used: int = Field(..., description="Total tokens (prompt + completion) consumed")
