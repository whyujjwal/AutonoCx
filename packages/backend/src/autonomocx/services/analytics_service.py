"""Analytics and metrics service."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, UTC
from typing import Any, Optional

import structlog
from sqlalchemy import case, cast, func, Float, select
from sqlalchemy.ext.asyncio import AsyncSession

from autonomocx.models.action import ActionExecution, ActionStatus
from autonomocx.models.agent import AgentConfig
from autonomocx.models.conversation import Conversation, ConversationStatus, Message

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

async def get_dashboard_data(
    db: AsyncSession,
    org_id: uuid.UUID,
) -> dict[str, Any]:
    """Return a high-level dashboard payload for *org_id*.

    Includes conversation totals, active counts, pending actions,
    and recent activity for the last 24 hours.
    """
    now = datetime.now(UTC)
    last_24h = now - timedelta(hours=24)
    last_7d = now - timedelta(days=7)

    # --- Conversation counts ---
    total_conv = (await db.execute(
        select(func.count())
        .select_from(Conversation)
        .where(Conversation.org_id == org_id)
    )).scalar_one()

    active_conv = (await db.execute(
        select(func.count())
        .select_from(Conversation)
        .where(
            Conversation.org_id == org_id,
            Conversation.status.in_([
                ConversationStatus.ACTIVE,
                ConversationStatus.WAITING_HUMAN,
                ConversationStatus.ESCALATED,
            ]),
        )
    )).scalar_one()

    new_conv_24h = (await db.execute(
        select(func.count())
        .select_from(Conversation)
        .where(
            Conversation.org_id == org_id,
            Conversation.created_at >= last_24h,
        )
    )).scalar_one()

    resolved_conv_7d = (await db.execute(
        select(func.count())
        .select_from(Conversation)
        .where(
            Conversation.org_id == org_id,
            Conversation.status == ConversationStatus.RESOLVED,
            Conversation.ended_at >= last_7d,
        )
    )).scalar_one()

    # --- Pending actions ---
    pending_actions = (await db.execute(
        select(func.count())
        .select_from(ActionExecution)
        .where(
            ActionExecution.org_id == org_id,
            ActionExecution.status == ActionStatus.AWAITING_APPROVAL,
        )
    )).scalar_one()

    # --- Average resolution time (last 7 days) ---
    avg_resolution = (await db.execute(
        select(func.avg(Conversation.resolution_time_seconds))
        .where(
            Conversation.org_id == org_id,
            Conversation.status == ConversationStatus.RESOLVED,
            Conversation.ended_at >= last_7d,
        )
    )).scalar_one() or 0

    # --- Messages last 24h ---
    msgs_24h = (await db.execute(
        select(func.count())
        .select_from(Message)
        .join(Conversation, Message.conversation_id == Conversation.id)
        .where(
            Conversation.org_id == org_id,
            Message.created_at >= last_24h,
        )
    )).scalar_one()

    return {
        "total_conversations": total_conv,
        "active_conversations": active_conv,
        "new_conversations_24h": new_conv_24h,
        "resolved_conversations_7d": resolved_conv_7d,
        "pending_actions": pending_actions,
        "avg_resolution_time_seconds": round(float(avg_resolution), 1),
        "messages_24h": msgs_24h,
    }


# ---------------------------------------------------------------------------
# Conversation metrics
# ---------------------------------------------------------------------------

async def get_conversation_metrics(
    db: AsyncSession,
    org_id: uuid.UUID,
    date_from: datetime,
    date_to: datetime,
) -> dict[str, Any]:
    """Return conversation metrics over a date range.

    Includes daily counts, status breakdown, channel distribution,
    average sentiment, and average resolution time.
    """
    base = (
        select(Conversation)
        .where(
            Conversation.org_id == org_id,
            Conversation.created_at >= date_from,
            Conversation.created_at <= date_to,
        )
    )

    # Total in range
    total = (await db.execute(
        select(func.count()).select_from(base.subquery())
    )).scalar_one()

    # By status
    status_stmt = (
        select(Conversation.status, func.count().label("count"))
        .where(
            Conversation.org_id == org_id,
            Conversation.created_at >= date_from,
            Conversation.created_at <= date_to,
        )
        .group_by(Conversation.status)
    )
    status_rows = (await db.execute(status_stmt)).all()
    by_status = {row.status.value: row.count for row in status_rows}

    # By channel
    channel_stmt = (
        select(Conversation.channel, func.count().label("count"))
        .where(
            Conversation.org_id == org_id,
            Conversation.created_at >= date_from,
            Conversation.created_at <= date_to,
        )
        .group_by(Conversation.channel)
    )
    channel_rows = (await db.execute(channel_stmt)).all()
    by_channel = {row.channel.value: row.count for row in channel_rows}

    # Average sentiment
    avg_sentiment = (await db.execute(
        select(func.avg(Conversation.sentiment))
        .where(
            Conversation.org_id == org_id,
            Conversation.created_at >= date_from,
            Conversation.created_at <= date_to,
            Conversation.sentiment.is_not(None),
        )
    )).scalar_one()

    # Average resolution time
    avg_resolution = (await db.execute(
        select(func.avg(Conversation.resolution_time_seconds))
        .where(
            Conversation.org_id == org_id,
            Conversation.status == ConversationStatus.RESOLVED,
            Conversation.created_at >= date_from,
            Conversation.created_at <= date_to,
        )
    )).scalar_one()

    # Daily conversation counts
    daily_stmt = (
        select(
            func.date_trunc("day", Conversation.created_at).label("day"),
            func.count().label("count"),
        )
        .where(
            Conversation.org_id == org_id,
            Conversation.created_at >= date_from,
            Conversation.created_at <= date_to,
        )
        .group_by(func.date_trunc("day", Conversation.created_at))
        .order_by(func.date_trunc("day", Conversation.created_at))
    )
    daily_rows = (await db.execute(daily_stmt)).all()
    daily = [
        {"date": row.day.isoformat() if row.day else None, "count": row.count}
        for row in daily_rows
    ]

    return {
        "total": total,
        "by_status": by_status,
        "by_channel": by_channel,
        "avg_sentiment": round(float(avg_sentiment), 3) if avg_sentiment else None,
        "avg_resolution_time_seconds": (
            round(float(avg_resolution), 1) if avg_resolution else None
        ),
        "daily": daily,
    }


# ---------------------------------------------------------------------------
# Action metrics
# ---------------------------------------------------------------------------

async def get_action_metrics(
    db: AsyncSession,
    org_id: uuid.UUID,
    date_from: datetime,
    date_to: datetime,
) -> dict[str, Any]:
    """Return action execution metrics over a date range."""
    base_filter = [
        ActionExecution.org_id == org_id,
        ActionExecution.created_at >= date_from,
        ActionExecution.created_at <= date_to,
    ]

    total = (await db.execute(
        select(func.count()).select_from(ActionExecution).where(*base_filter)
    )).scalar_one()

    # By status
    status_stmt = (
        select(ActionExecution.status, func.count().label("count"))
        .where(*base_filter)
        .group_by(ActionExecution.status)
    )
    status_rows = (await db.execute(status_stmt)).all()
    by_status = {row.status.value: row.count for row in status_rows}

    # Avg execution time
    avg_exec = (await db.execute(
        select(func.avg(ActionExecution.execution_time_ms))
        .where(
            *base_filter,
            ActionExecution.status == ActionStatus.COMPLETED,
        )
    )).scalar_one() or 0

    # By tool (top 10)
    tool_stmt = (
        select(ActionExecution.tool_id, func.count().label("count"))
        .where(*base_filter)
        .group_by(ActionExecution.tool_id)
        .order_by(func.count().desc())
        .limit(10)
    )
    tool_rows = (await db.execute(tool_stmt)).all()
    by_tool = [
        {"tool_id": str(row.tool_id), "count": row.count}
        for row in tool_rows
    ]

    return {
        "total": total,
        "by_status": by_status,
        "avg_execution_time_ms": round(float(avg_exec), 2),
        "by_tool": by_tool,
    }


# ---------------------------------------------------------------------------
# Agent metrics
# ---------------------------------------------------------------------------

async def get_agent_metrics(
    db: AsyncSession,
    org_id: uuid.UUID,
) -> list[dict[str, Any]]:
    """Return per-agent metrics: conversation count, message count, avg sentiment."""
    stmt = (
        select(
            AgentConfig.id,
            AgentConfig.name,
            func.count(Conversation.id.distinct()).label("conversation_count"),
            func.count(Message.id).label("message_count"),
            func.avg(Conversation.sentiment).label("avg_sentiment"),
        )
        .outerjoin(Conversation, Conversation.agent_id == AgentConfig.id)
        .outerjoin(Message, Message.conversation_id == Conversation.id)
        .where(AgentConfig.org_id == org_id)
        .group_by(AgentConfig.id, AgentConfig.name)
        .order_by(func.count(Conversation.id.distinct()).desc())
    )
    rows = (await db.execute(stmt)).all()

    return [
        {
            "agent_id": str(row.id),
            "agent_name": row.name,
            "conversation_count": row.conversation_count,
            "message_count": row.message_count,
            "avg_sentiment": (
                round(float(row.avg_sentiment), 3) if row.avg_sentiment else None
            ),
        }
        for row in rows
    ]


# ---------------------------------------------------------------------------
# Cost breakdown
# ---------------------------------------------------------------------------

async def get_cost_breakdown(
    db: AsyncSession,
    org_id: uuid.UUID,
    date_from: datetime,
    date_to: datetime,
) -> dict[str, Any]:
    """Return LLM cost estimates broken down by model.

    Costs are estimated from token counts using approximate per-token rates.
    """
    # Approximate per-1K-token costs (input / output)
    MODEL_COSTS = {
        "gpt-4o": {"input": 0.005, "output": 0.015},
        "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
        "claude-sonnet-4-20250514": {"input": 0.003, "output": 0.015},
    }
    default_cost = {"input": 0.002, "output": 0.008}

    stmt = (
        select(
            Message.llm_model_used,
            func.sum(Message.prompt_tokens).label("total_prompt_tokens"),
            func.sum(Message.completion_tokens).label("total_completion_tokens"),
            func.count().label("message_count"),
        )
        .join(Conversation, Message.conversation_id == Conversation.id)
        .where(
            Conversation.org_id == org_id,
            Message.created_at >= date_from,
            Message.created_at <= date_to,
            Message.llm_model_used.is_not(None),
        )
        .group_by(Message.llm_model_used)
    )
    rows = (await db.execute(stmt)).all()

    breakdown: list[dict[str, Any]] = []
    total_cost = 0.0

    for row in rows:
        model = row.llm_model_used or "unknown"
        prompt_tokens = row.total_prompt_tokens or 0
        completion_tokens = row.total_completion_tokens or 0
        rates = MODEL_COSTS.get(model, default_cost)

        input_cost = (prompt_tokens / 1000) * rates["input"]
        output_cost = (completion_tokens / 1000) * rates["output"]
        model_cost = input_cost + output_cost
        total_cost += model_cost

        breakdown.append({
            "model": model,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "message_count": row.message_count,
            "estimated_cost_usd": round(model_cost, 4),
        })

    return {
        "breakdown": breakdown,
        "total_estimated_cost_usd": round(total_cost, 4),
        "date_from": date_from.isoformat(),
        "date_to": date_to.isoformat(),
    }
