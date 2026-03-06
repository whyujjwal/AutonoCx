"""Action execution service -- approval workflows and action lifecycle."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from autonomocx.core.exceptions import NotFoundError, ValidationError
from autonomocx.models.action import ActionExecution, ActionStatus
from autonomocx.schemas.common import PaginatedResponse

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# List / Read
# ---------------------------------------------------------------------------


async def list_actions(
    db: AsyncSession,
    org_id: uuid.UUID,
    filters: dict[str, Any] | None = None,
    page: int = 1,
    page_size: int = 20,
) -> PaginatedResponse:
    """Return a paginated, filterable list of action executions."""
    filters = filters or {}
    base = select(ActionExecution).where(ActionExecution.org_id == org_id)

    if "status" in filters and filters["status"]:
        base = base.where(ActionExecution.status == filters["status"])
    if "tool_id" in filters and filters["tool_id"]:
        base = base.where(ActionExecution.tool_id == filters["tool_id"])
    if "agent_id" in filters and filters["agent_id"]:
        base = base.where(ActionExecution.agent_id == filters["agent_id"])
    if "conversation_id" in filters and filters["conversation_id"]:
        base = base.where(ActionExecution.conversation_id == filters["conversation_id"])
    if "date_from" in filters and filters["date_from"]:
        base = base.where(ActionExecution.created_at >= filters["date_from"])
    if "date_to" in filters and filters["date_to"]:
        base = base.where(ActionExecution.created_at <= filters["date_to"])

    count_stmt = select(func.count()).select_from(base.subquery())
    total = (await db.execute(count_stmt)).scalar_one()

    stmt = (
        base.order_by(ActionExecution.created_at.desc())
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


async def get_pending_actions(
    db: AsyncSession,
    org_id: uuid.UUID,
) -> list[ActionExecution]:
    """Return all actions currently awaiting human approval."""
    stmt = (
        select(ActionExecution)
        .where(
            ActionExecution.org_id == org_id,
            ActionExecution.status == ActionStatus.AWAITING_APPROVAL,
        )
        .order_by(ActionExecution.created_at.asc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_action(
    db: AsyncSession,
    action_id: uuid.UUID,
) -> ActionExecution:
    """Return a single action execution.  Raises ``NotFoundError`` if missing."""
    result = await db.execute(select(ActionExecution).where(ActionExecution.id == action_id))
    action = result.scalar_one_or_none()
    if action is None:
        raise NotFoundError(f"Action execution {action_id} not found.")
    return action


# ---------------------------------------------------------------------------
# Approve / Reject
# ---------------------------------------------------------------------------


async def approve_action(
    db: AsyncSession,
    action_id: uuid.UUID,
    user_id: uuid.UUID,
    notes: str | None = None,
) -> ActionExecution:
    """Approve a pending action and transition it to ``APPROVED``.

    After approval the action is eligible for execution by the action
    executor (which will move it to EXECUTING -> COMPLETED/FAILED).
    """
    action = await get_action(db, action_id)

    if action.status != ActionStatus.AWAITING_APPROVAL:
        raise ValidationError(f"Action is in '{action.status.value}' state and cannot be approved.")

    action.status = ActionStatus.APPROVED
    action.approved_by = user_id
    action.approved_at = datetime.now(UTC)

    # Store reviewer notes in the output metadata
    if notes:
        output = dict(action.output_result or {})
        output["approval_notes"] = notes
        action.output_result = output

    db.add(action)
    await db.flush()

    logger.info(
        "action_approved",
        action_id=str(action.id),
        approved_by=str(user_id),
    )
    return action


async def reject_action(
    db: AsyncSession,
    action_id: uuid.UUID,
    user_id: uuid.UUID,
    reason: str | None = None,
) -> ActionExecution:
    """Reject a pending action."""
    action = await get_action(db, action_id)

    if action.status != ActionStatus.AWAITING_APPROVAL:
        raise ValidationError(f"Action is in '{action.status.value}' state and cannot be rejected.")

    action.status = ActionStatus.REJECTED
    action.approved_by = user_id
    action.approved_at = datetime.now(UTC)
    action.rejection_reason = reason

    db.add(action)
    await db.flush()

    logger.info(
        "action_rejected",
        action_id=str(action.id),
        rejected_by=str(user_id),
        reason=reason,
    )
    return action


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------


async def get_action_stats(
    db: AsyncSession,
    org_id: uuid.UUID,
) -> dict[str, Any]:
    """Return aggregate action statistics for the dashboard.

    Returns an ``ActionStats``-compatible dict with counts by status,
    average execution time, and approval metrics.
    """
    select(ActionExecution).where(ActionExecution.org_id == org_id)

    # Status counts
    status_stmt = (
        select(
            ActionExecution.status,
            func.count().label("count"),
        )
        .where(ActionExecution.org_id == org_id)
        .group_by(ActionExecution.status)
    )
    status_result = await db.execute(status_stmt)
    status_counts: dict[str, int] = {row[0].value: row[1] for row in status_result}

    # Average execution time for completed actions
    avg_exec_stmt = select(func.avg(ActionExecution.execution_time_ms)).where(
        ActionExecution.org_id == org_id,
        ActionExecution.status == ActionStatus.COMPLETED,
    )
    avg_exec = (await db.execute(avg_exec_stmt)).scalar_one() or 0

    # Approval rate: approved / (approved + rejected)
    approved_count = status_counts.get("approved", 0) + status_counts.get("completed", 0)
    rejected_count = status_counts.get("rejected", 0)
    total_reviewed = approved_count + rejected_count
    approval_rate = (approved_count / total_reviewed * 100) if total_reviewed > 0 else 0.0

    # Total
    total_count = sum(status_counts.values())

    return {
        "total": total_count,
        "status_counts": status_counts,
        "avg_execution_time_ms": round(float(avg_exec), 2),
        "approval_rate_percent": round(approval_rate, 2),
        "pending_count": status_counts.get("awaiting_approval", 0),
    }
