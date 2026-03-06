"""Conversation management endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from autonomocx.core.database import get_db
from autonomocx.core.dependencies import get_current_user
from autonomocx.models.conversation import (
    ChannelType,
    ConversationStatus,
    Priority,
)
from autonomocx.models.user import User
from autonomocx.services.conversations import (
    create_conversation,
    escalate_conversation,
    get_conversation_by_id,
    list_conversations,
    resolve_conversation,
    update_conversation,
)

router = APIRouter(prefix="/conversations", tags=["conversations"])

# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class MessageOut(BaseModel):
    id: UUID
    conversation_id: UUID
    role: str
    content: str | None = None
    content_type: str
    metadata_: dict[str, Any] | None = Field(None, alias="metadata")
    tool_call_id: str | None = None
    tool_name: str | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    llm_model_used: str | None = None
    latency_ms: int | None = None
    created_at: datetime

    model_config = {"from_attributes": True, "populate_by_name": True}


class ConversationOut(BaseModel):
    id: UUID
    org_id: UUID
    agent_id: UUID | None = None
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
    assigned_to: UUID | None = None
    resolved_by: str | None = None
    resolution_time_seconds: int | None = None
    satisfaction_score: float | None = None
    metadata_: dict[str, Any] | None = Field(None, alias="metadata")
    started_at: datetime | None = None
    ended_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True, "populate_by_name": True}


class ConversationDetailOut(ConversationOut):
    messages: list[MessageOut] = []


class ConversationCreateRequest(BaseModel):
    channel: ChannelType
    channel_id: str | None = None
    agent_id: UUID | None = None
    customer_id: str | None = None
    customer_name: str | None = None
    customer_email: str | None = None
    customer_phone: str | None = None
    priority: Priority = Priority.NORMAL
    metadata: dict[str, Any] | None = None


class ConversationUpdateRequest(BaseModel):
    status: ConversationStatus | None = None
    priority: Priority | None = None
    agent_id: UUID | None = None
    assigned_to: UUID | None = None
    metadata: dict[str, Any] | None = None


class EscalateRequest(BaseModel):
    reason: str = Field(..., min_length=1, max_length=1000)
    assign_to: UUID | None = None


class ResolveRequest(BaseModel):
    resolved_by: str = Field(..., min_length=1, max_length=255)
    satisfaction_score: float | None = Field(None, ge=0.0, le=5.0)


class PaginatedConversations(BaseModel):
    items: list[ConversationOut]
    total: int
    page: int
    page_size: int
    pages: int


class MessageResponse(BaseModel):
    detail: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get(
    "/",
    response_model=PaginatedConversations,
    summary="List conversations",
)
async def list_convos(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: ConversationStatus | None = Query(None, alias="status"),
    channel: ChannelType | None = None,
    priority: Priority | None = None,
    agent_id: UUID | None = None,
    assigned_to: UUID | None = None,
    customer_id: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PaginatedConversations:
    """Return paginated, filterable conversations for the current organization."""
    result = await list_conversations(
        db,
        org_id=current_user.org_id,
        page=page,
        page_size=page_size,
        status=status_filter,
        channel=channel,
        priority=priority,
        agent_id=agent_id,
        assigned_to=assigned_to,
        customer_id=customer_id,
    )
    return PaginatedConversations(
        items=[ConversationOut.model_validate(c) for c in result["items"]],
        total=result["total"],
        page=page,
        page_size=page_size,
        pages=result["pages"],
    )


@router.get(
    "/{conversation_id}",
    response_model=ConversationDetailOut,
    summary="Get conversation with messages",
)
async def get_conversation(
    conversation_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ConversationDetailOut:
    """Return a single conversation with its full message history."""
    convo = await get_conversation_by_id(
        db,
        conversation_id=conversation_id,
        org_id=current_user.org_id,
    )
    if convo is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )
    return ConversationDetailOut.model_validate(convo)


@router.post(
    "/",
    response_model=ConversationOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new conversation",
)
async def create_convo(
    body: ConversationCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ConversationOut:
    """Create a new conversation in the current organization."""
    convo = await create_conversation(
        db,
        org_id=current_user.org_id,
        channel=body.channel,
        channel_id=body.channel_id,
        agent_id=body.agent_id,
        customer_id=body.customer_id,
        customer_name=body.customer_name,
        customer_email=body.customer_email,
        customer_phone=body.customer_phone,
        priority=body.priority,
        metadata=body.metadata,
    )
    return ConversationOut.model_validate(convo)


@router.patch(
    "/{conversation_id}",
    response_model=ConversationOut,
    summary="Update conversation",
)
async def update_convo(
    conversation_id: UUID,
    body: ConversationUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ConversationOut:
    """Update status, priority, assignment, or agent of a conversation."""
    convo = await update_conversation(
        db,
        conversation_id=conversation_id,
        org_id=current_user.org_id,
        data=body.model_dump(exclude_unset=True),
    )
    if convo is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )
    return ConversationOut.model_validate(convo)


@router.post(
    "/{conversation_id}/escalate",
    response_model=ConversationOut,
    summary="Escalate conversation to human",
)
async def escalate_convo(
    conversation_id: UUID,
    body: EscalateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ConversationOut:
    """Escalate the conversation to a human agent, optionally assigning to a specific user."""
    convo = await escalate_conversation(
        db,
        conversation_id=conversation_id,
        org_id=current_user.org_id,
        reason=body.reason,
        assign_to=body.assign_to,
        escalated_by=current_user.id,
    )
    if convo is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )
    return ConversationOut.model_validate(convo)


@router.post(
    "/{conversation_id}/resolve",
    response_model=ConversationOut,
    summary="Resolve conversation",
)
async def resolve_convo(
    conversation_id: UUID,
    body: ResolveRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ConversationOut:
    """Mark a conversation as resolved with optional satisfaction score."""
    convo = await resolve_conversation(
        db,
        conversation_id=conversation_id,
        org_id=current_user.org_id,
        resolved_by=body.resolved_by,
        satisfaction_score=body.satisfaction_score,
    )
    if convo is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )
    return ConversationOut.model_validate(convo)
