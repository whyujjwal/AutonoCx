"""Message service -- CRUD and the main customer-message processing entry point."""

from __future__ import annotations

import uuid
from datetime import datetime, UTC
from typing import Any

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from autonomocx.core.exceptions import NotFoundError
from autonomocx.models.conversation import (
    ContentType,
    Conversation,
    ConversationStatus,
    Message,
    MessageRole,
)
from autonomocx.schemas.common import PaginatedResponse

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Read
# ---------------------------------------------------------------------------

async def get_messages(
    db: AsyncSession,
    conversation_id: uuid.UUID,
    page: int = 1,
    page_size: int = 50,
) -> PaginatedResponse:
    """Return paginated messages for a conversation, oldest first."""
    base = select(Message).where(Message.conversation_id == conversation_id)

    count_stmt = select(func.count()).select_from(base.subquery())
    total = (await db.execute(count_stmt)).scalar_one()

    stmt = (
        base
        .order_by(Message.created_at.asc())
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


# ---------------------------------------------------------------------------
# Create (low-level)
# ---------------------------------------------------------------------------

async def create_message(
    db: AsyncSession,
    conversation_id: uuid.UUID,
    data: dict,
) -> Message:
    """Insert a new message row.

    ``data`` should contain at minimum ``role`` and ``content``.
    """
    msg = Message(
        conversation_id=conversation_id,
        role=data["role"],
        content=data.get("content"),
        content_type=data.get("content_type", ContentType.TEXT),
        metadata_=data.get("metadata", {}),
        tool_call_id=data.get("tool_call_id"),
        tool_name=data.get("tool_name"),
        prompt_tokens=data.get("prompt_tokens"),
        completion_tokens=data.get("completion_tokens"),
        llm_model_used=data.get("llm_model_used"),
        latency_ms=data.get("latency_ms"),
    )
    db.add(msg)
    await db.flush()

    logger.debug(
        "message_created",
        message_id=str(msg.id),
        conversation_id=str(conversation_id),
        role=msg.role.value,
    )
    return msg


# ---------------------------------------------------------------------------
# Main AI pipeline entry point
# ---------------------------------------------------------------------------

async def process_customer_message(
    db: AsyncSession,
    redis: Any,  # redis.asyncio.Redis
    conversation_id: uuid.UUID,
    content: str,
) -> Message:
    """Process an inbound customer message through the AI pipeline.

    High-level flow:
    1. Persist the customer message.
    2. Ensure the conversation is active.
    3. Delegate to the orchestrator / agent pipeline (stubbed here).
    4. Persist and return the assistant response message.

    This is the single entry point that routers / channel adapters call
    when a new customer message arrives.
    """
    # --- 1. Persist customer message ---
    customer_msg = await create_message(db, conversation_id, {
        "role": MessageRole.CUSTOMER,
        "content": content,
        "content_type": ContentType.TEXT,
    })

    # --- 2. Load conversation context ---
    result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    conversation = result.scalar_one_or_none()
    if conversation is None:
        raise NotFoundError(f"Conversation {conversation_id} not found.")

    # Re-activate if the conversation was waiting for human input
    if conversation.status == ConversationStatus.WAITING_HUMAN:
        conversation.status = ConversationStatus.ACTIVE
        db.add(conversation)
        await db.flush()

    # --- 3. Call orchestrator (to be implemented in autonomocx.ai) ---
    # The orchestrator is responsible for:
    #   - Loading agent config
    #   - Building the LLM prompt (system prompt + history + knowledge retrieval)
    #   - Calling the LLM
    #   - Executing any tool calls (which may require approval)
    #   - Returning the final assistant response
    #
    # For now we produce a placeholder response that downstream modules will
    # replace once the AI pipeline package is wired in.

    start_ts = datetime.now(UTC)

    # TODO: Replace with actual orchestrator call:
    #   from autonomocx.ai.orchestrator import run_agent_turn
    #   ai_response = await run_agent_turn(db, redis, conversation, customer_msg)
    assistant_content = (
        "[AutonoCX AI pipeline not yet connected] "
        "Your message has been received and queued for processing."
    )
    model_used = "pending"
    prompt_tokens = 0
    completion_tokens = 0

    elapsed_ms = int((datetime.now(UTC) - start_ts).total_seconds() * 1000)

    # --- 4. Persist assistant response ---
    assistant_msg = await create_message(db, conversation_id, {
        "role": MessageRole.ASSISTANT,
        "content": assistant_content,
        "content_type": ContentType.TEXT,
        "llm_model_used": model_used,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "latency_ms": elapsed_ms,
    })

    logger.info(
        "customer_message_processed",
        conversation_id=str(conversation_id),
        customer_msg_id=str(customer_msg.id),
        assistant_msg_id=str(assistant_msg.id),
        latency_ms=elapsed_ms,
    )

    return assistant_msg
