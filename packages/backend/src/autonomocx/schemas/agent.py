"""Agent configuration schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Requests
# ---------------------------------------------------------------------------


class AgentCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    system_prompt: Optional[str] = None
    llm_provider: Optional[str] = Field(None, max_length=64)
    llm_model: Optional[str] = Field(None, max_length=128)
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(None, ge=1)
    tools_enabled: Optional[list[uuid.UUID]] = Field(default_factory=list)


class AgentUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    system_prompt: Optional[str] = None
    llm_provider: Optional[str] = Field(None, max_length=64)
    llm_model: Optional[str] = Field(None, max_length=128)
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(None, ge=1)
    tools_enabled: Optional[list[uuid.UUID]] = None


# ---------------------------------------------------------------------------
# Responses
# ---------------------------------------------------------------------------


class AgentResponse(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    name: str
    description: Optional[str] = None
    system_prompt: Optional[str] = None
    llm_provider: Optional[str] = None
    llm_model: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    tools_enabled: Optional[list[uuid.UUID]] = None
    fallback_agent_id: Optional[uuid.UUID] = None
    is_active: bool
    metadata: Optional[dict[str, Any]] = Field(None, alias="metadata_")
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
    latency_ms: float = Field(
        ..., description="Round-trip time in milliseconds"
    )
    tokens_used: int = Field(
        ..., description="Total tokens (prompt + completion) consumed"
    )
