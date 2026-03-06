"""Message endpoints for a conversation."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from autonomocx.core.database import get_db
from autonomocx.core.dependencies import get_current_user
from autonomocx.models.conversation import ContentType, MessageRole
from autonomocx.models.user import User
from autonomocx.services.conversations import get_conversation_by_id
from autonomocx.services.messages import get_messages, send_message

router = APIRouter(prefix="/conversations", tags=["messages"])

# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class MessageOut(BaseModel):
    id: UUID
    conversation_id: UUID
    role: MessageRole
    content: str | None = None
    content_type: ContentType
    metadata_: dict[str, Any] | None = Field(None, alias="metadata")
    tool_call_id: str | None = None
    tool_name: str | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    llm_model_used: str | None = None
    latency_ms: int | None = None
    created_at: datetime

    model_config = {"from_attributes": True, "populate_by_name": True}


class SendMessageRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=32000)
    content_type: ContentType = ContentType.TEXT
    role: MessageRole = MessageRole.CUSTOMER
    metadata: dict[str, Any] | None = None


class SendMessageResponse(BaseModel):
    """Response includes both the sent message and the AI-generated reply (if any)."""

    user_message: MessageOut
    assistant_message: MessageOut | None = None


class PaginatedMessages(BaseModel):
    items: list[MessageOut]
    total: int
    page: int
    page_size: int
    pages: int


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get(
    "/{conversation_id}/messages",
    response_model=PaginatedMessages,
    summary="Get conversation messages",
)
async def list_messages(
    conversation_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PaginatedMessages:
    """Return paginated messages for a conversation, ordered chronologically."""
    # Verify conversation exists and belongs to user's org
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

    result = await get_messages(
        db,
        conversation_id=conversation_id,
        page=page,
        page_size=page_size,
    )
    return PaginatedMessages(
        items=[MessageOut.model_validate(m) for m in result["items"]],
        total=result["total"],
        page=page,
        page_size=page_size,
        pages=result["pages"],
    )


@router.post(
    "/{conversation_id}/messages",
    response_model=SendMessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Send a message (triggers AI pipeline)",
)
async def create_message(
    conversation_id: UUID,
    body: SendMessageRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SendMessageResponse:
    """Send a message in a conversation.

    When the sender role is ``customer``, the AI pipeline is triggered
    automatically and an assistant reply is generated and returned alongside
    the original message.
    """
    # Verify conversation
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

    result = await send_message(
        db,
        conversation_id=conversation_id,
        org_id=current_user.org_id,
        content=body.content,
        content_type=body.content_type,
        role=body.role,
        metadata=body.metadata,
    )

    response = SendMessageResponse(
        user_message=MessageOut.model_validate(result["user_message"]),
    )
    if result.get("assistant_message") is not None:
        response.assistant_message = MessageOut.model_validate(result["assistant_message"])
    return response
