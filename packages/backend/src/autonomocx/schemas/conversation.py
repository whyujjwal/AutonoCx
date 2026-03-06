"""Conversation & message schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

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
    customer_id: Optional[str] = Field(None, max_length=255)
    customer_name: Optional[str] = Field(None, max_length=255)
    customer_email: Optional[EmailStr] = None
    customer_phone: Optional[str] = Field(None, max_length=32)
    agent_id: Optional[uuid.UUID] = None
    metadata: Optional[dict[str, Any]] = None


class ConversationUpdate(BaseModel):
    status: Optional[ConversationStatus] = None
    priority: Optional[Priority] = None
    assigned_to: Optional[uuid.UUID] = None


class ConversationFilter(BaseModel):
    status: Optional[ConversationStatus] = None
    channel: Optional[ChannelType] = None
    priority: Optional[Priority] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    customer_id: Optional[str] = None


# ---------------------------------------------------------------------------
# Conversation responses
# ---------------------------------------------------------------------------


class ConversationResponse(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    agent_id: Optional[uuid.UUID] = None
    channel: ChannelType
    channel_id: Optional[str] = None
    customer_id: Optional[str] = None
    customer_name: Optional[str] = None
    customer_email: Optional[str] = None
    customer_phone: Optional[str] = None
    status: ConversationStatus
    priority: Priority
    sentiment: Optional[float] = None
    intent: Optional[str] = None
    assigned_to: Optional[uuid.UUID] = None
    resolved_by: Optional[str] = None
    resolution_time_seconds: Optional[int] = None
    satisfaction_score: Optional[float] = None
    metadata: Optional[dict[str, Any]] = Field(None, alias="metadata_")
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class ConversationListResponse(BaseModel):
    """Lighter representation used in list endpoints."""

    id: uuid.UUID
    org_id: uuid.UUID
    agent_id: Optional[uuid.UUID] = None
    channel: ChannelType
    customer_id: Optional[str] = None
    customer_name: Optional[str] = None
    customer_email: Optional[str] = None
    status: ConversationStatus
    priority: Priority
    assigned_to: Optional[uuid.UUID] = None
    last_message: Optional[str] = Field(
        None, description="Preview of the most recent message"
    )
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
    metadata: Optional[dict[str, Any]] = None


class MessageResponse(BaseModel):
    id: uuid.UUID
    conversation_id: uuid.UUID
    role: MessageRole
    content: Optional[str] = None
    content_type: ContentType
    metadata: Optional[dict[str, Any]] = Field(None, alias="metadata_")
    tool_call_id: Optional[str] = None
    tool_name: Optional[str] = None
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    llm_model_used: Optional[str] = None
    latency_ms: Optional[int] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
