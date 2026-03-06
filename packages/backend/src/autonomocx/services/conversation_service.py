"""Conversation lifecycle service."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from autonomocx.core.exceptions import NotFoundError, ValidationError
from autonomocx.models.conversation import (
    Conversation,
    ConversationStatus,
    Priority,
)
from autonomocx.schemas.common import PaginatedResponse

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# List / Read
# ---------------------------------------------------------------------------


async def list_conversations(
    db: AsyncSession,
    org_id: uuid.UUID,
    filters: dict[str, Any] | None = None,
    page: int = 1,
    page_size: int = 20,
) -> PaginatedResponse:
    """Return a paginated, filterable list of conversations for *org_id*."""
    filters = filters or {}
    base = select(Conversation).where(Conversation.org_id == org_id)

    # Dynamic filters
    if "status" in filters and filters["status"]:
        base = base.where(Conversation.status == filters["status"])
    if "channel" in filters and filters["channel"]:
        base = base.where(Conversation.channel == filters["channel"])
    if "priority" in filters and filters["priority"]:
        base = base.where(Conversation.priority == filters["priority"])
    if "assigned_to" in filters and filters["assigned_to"]:
        base = base.where(Conversation.assigned_to == filters["assigned_to"])
    if "customer_id" in filters and filters["customer_id"]:
        base = base.where(Conversation.customer_id == filters["customer_id"])
    if "agent_id" in filters and filters["agent_id"]:
        base = base.where(Conversation.agent_id == filters["agent_id"])
    if "date_from" in filters and filters["date_from"]:
        base = base.where(Conversation.created_at >= filters["date_from"])
    if "date_to" in filters and filters["date_to"]:
        base = base.where(Conversation.created_at <= filters["date_to"])

    # Count
    count_stmt = select(func.count()).select_from(base.subquery())
    total = (await db.execute(count_stmt)).scalar_one()

    # Page
    stmt = (
        base.order_by(Conversation.updated_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    rows = (await db.execute(stmt)).scalars().all()

    return PaginatedResponse.create(
        items=list(rows),
        total=total,
        page=page,
        page_size=page_size,
    )


async def get_conversation(
    db: AsyncSession,
    conversation_id: uuid.UUID,
) -> Conversation:
    """Return a single conversation.  Raises ``NotFoundError`` if missing."""
    result = await db.execute(select(Conversation).where(Conversation.id == conversation_id))
    conv = result.scalar_one_or_none()
    if conv is None:
        raise NotFoundError(f"Conversation {conversation_id} not found.")
    return conv


# ---------------------------------------------------------------------------
# Create / Update
# ---------------------------------------------------------------------------


async def create_conversation(
    db: AsyncSession,
    org_id: uuid.UUID,
    data: dict,
) -> Conversation:
    """Start a new conversation."""
    conv = Conversation(
        org_id=org_id,
        agent_id=data.get("agent_id"),
        channel=data["channel"],
        channel_id=data.get("channel_id"),
        customer_id=data.get("customer_id"),
        customer_name=data.get("customer_name"),
        customer_email=data.get("customer_email"),
        customer_phone=data.get("customer_phone"),
        status=ConversationStatus.ACTIVE,
        priority=data.get("priority", Priority.NORMAL),
        metadata_=data.get("metadata", {}),
        started_at=datetime.now(UTC),
    )
    db.add(conv)
    await db.flush()

    logger.info(
        "conversation_created",
        conversation_id=str(conv.id),
        org_id=str(org_id),
        channel=conv.channel.value,
    )
    return conv


async def update_conversation(
    db: AsyncSession,
    conversation_id: uuid.UUID,
    data: dict,
) -> Conversation:
    """Partially update a conversation's mutable fields."""
    conv = await get_conversation(db, conversation_id)

    mutable_fields = (
        "status",
        "priority",
        "sentiment",
        "intent",
        "assigned_to",
        "agent_id",
        "metadata_",
        "customer_name",
        "customer_email",
        "customer_phone",
    )
    for field in mutable_fields:
        if field in data and data[field] is not None:
            setattr(conv, field, data[field])

    db.add(conv)
    await db.flush()

    logger.info("conversation_updated", conversation_id=str(conv.id))
    return conv


# ---------------------------------------------------------------------------
# Status transitions
# ---------------------------------------------------------------------------


async def escalate_conversation(
    db: AsyncSession,
    conversation_id: uuid.UUID,
    assigned_to: uuid.UUID,
) -> Conversation:
    """Escalate a conversation to a human supervisor.

    Sets status to ``ESCALATED`` and assigns the given user.
    """
    conv = await get_conversation(db, conversation_id)

    if conv.status in (ConversationStatus.RESOLVED, ConversationStatus.CLOSED):
        raise ValidationError("Cannot escalate a resolved or closed conversation.")

    conv.status = ConversationStatus.ESCALATED
    conv.assigned_to = assigned_to
    db.add(conv)
    await db.flush()

    logger.info(
        "conversation_escalated",
        conversation_id=str(conv.id),
        assigned_to=str(assigned_to),
    )
    return conv


async def resolve_conversation(
    db: AsyncSession,
    conversation_id: uuid.UUID,
    resolved_by: str,
) -> Conversation:
    """Mark a conversation as resolved.

    Computes resolution time from ``started_at`` to now.
    """
    conv = await get_conversation(db, conversation_id)

    if conv.status == ConversationStatus.CLOSED:
        raise ValidationError("Cannot resolve a closed conversation.")

    now = datetime.now(UTC)
    conv.status = ConversationStatus.RESOLVED
    conv.resolved_by = resolved_by
    conv.ended_at = now

    if conv.started_at is not None:
        delta = now - conv.started_at
        conv.resolution_time_seconds = int(delta.total_seconds())

    db.add(conv)
    await db.flush()

    logger.info(
        "conversation_resolved",
        conversation_id=str(conv.id),
        resolved_by=resolved_by,
        resolution_seconds=conv.resolution_time_seconds,
    )
    return conv
