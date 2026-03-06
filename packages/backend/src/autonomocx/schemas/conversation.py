"""Conversation & message schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from autonomocx.models.conversation import (
    ChannelType,
    ContentType,
    ConversationStatus,
    MessageRole,
    Priority,
)

# ---------------------------------------------------------------------------
# Conversation requests
# ---------------------------------------------------------------------------


class ConversationCreate(BaseModel):
    channel: ChannelType
    customer_id: str | None = Field(None, max_length=255)
    customer_name: str | None = Field(None, max_length=255)
    customer_email: EmailStr | None = None
    customer_phone: str | None = Field(None, max_length=32)
    agent_id: uuid.UUID | None = None
    metadata: dict[str, Any] | None = None


class ConversationUpdate(BaseModel):
    status: ConversationStatus | None = None
    priority: Priority | None = None
    assigned_to: uuid.UUID | None = None


class ConversationFilter(BaseModel):
    status: ConversationStatus | None = None
    channel: ChannelType | None = None
    priority: Priority | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
    customer_id: str | None = None


# ---------------------------------------------------------------------------
# Conversation responses
# ---------------------------------------------------------------------------


class ConversationResponse(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    agent_id: uuid.UUID | None = None
    channel: ChannelType
    channel_id: str | None = None
    customer_id: str | None = None
    customer_name: str | None = None
    customer_email: str | None = None
    customer_phone: str | None = None
    status: ConversationStatus
    priority: Priority
    sentiment: float | None = None
    intent: str | None = None
    assigned_to: uuid.UUID | None = None
    resolved_by: str | None = None
    resolution_time_seconds: int | None = None
    satisfaction_score: float | None = None
    metadata: dict[str, Any] | None = Field(None, alias="metadata_")
    started_at: datetime | None = None
    ended_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class ConversationListResponse(BaseModel):
    """Lighter representation used in list endpoints."""

    id: uuid.UUID
    org_id: uuid.UUID
    agent_id: uuid.UUID | None = None
    channel: ChannelType
    customer_id: str | None = None
    customer_name: str | None = None
    customer_email: str | None = None
    status: ConversationStatus
    priority: Priority
    assigned_to: uuid.UUID | None = None
    last_message: str | None = Field(None, description="Preview of the most recent message")
    message_count: int = Field(0, description="Total messages in the conversation")
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Message requests / responses
# ---------------------------------------------------------------------------


class MessageCreate(BaseModel):
    content: str = Field(..., min_length=1)
    content_type: ContentType = Field(default=ContentType.TEXT)
    metadata: dict[str, Any] | None = None


class MessageResponse(BaseModel):
    id: uuid.UUID
    conversation_id: uuid.UUID
    role: MessageRole
    content: str | None = None
    content_type: ContentType
    metadata: dict[str, Any] | None = Field(None, alias="metadata_")
    tool_call_id: str | None = None
    tool_name: str | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    llm_model_used: str | None = None
    latency_ms: int | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
