"""Audit logging service."""

from __future__ import annotations

import csv
import io
import uuid
from typing import Any

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from autonomocx.models.audit import AuditLog
from autonomocx.schemas.common import PaginatedResponse

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Write
# ---------------------------------------------------------------------------


async def log_action(
    db: AsyncSession,
    org_id: uuid.UUID,
    user_id: uuid.UUID | None,
    actor_type: str,
    action: str,
    resource_type: str,
    resource_id: str | None = None,
    details: dict[str, Any] | None = None,
    request_id: str | None = None,
) -> AuditLog:
    """Record a single audit log entry.

    ``actor_type`` distinguishes between ``"user"``, ``"system"``, or
    ``"agent"`` initiated actions.
    """
    entry = AuditLog(
        org_id=org_id,
        user_id=user_id,
        actor_type=actor_type,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details or {},
        request_id=request_id,
    )
    db.add(entry)
    await db.flush()

    logger.debug(
        "audit_logged",
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        actor_type=actor_type,
    )
    return entry


# ---------------------------------------------------------------------------
# Read
# ---------------------------------------------------------------------------


async def query_audit_logs(
    db: AsyncSession,
    org_id: uuid.UUID,
    filters: dict[str, Any] | None = None,
    page: int = 1,
    page_size: int = 50,
) -> PaginatedResponse:
    """Return a paginated, filterable list of audit log entries."""
    filters = filters or {}
    base = select(AuditLog).where(AuditLog.org_id == org_id)

    if "user_id" in filters and filters["user_id"]:
        base = base.where(AuditLog.user_id == filters["user_id"])
    if "actor_type" in filters and filters["actor_type"]:
        base = base.where(AuditLog.actor_type == filters["actor_type"])
    if "action" in filters and filters["action"]:
        base = base.where(AuditLog.action == filters["action"])
    if "resource_type" in filters and filters["resource_type"]:
        base = base.where(AuditLog.resource_type == filters["resource_type"])
    if "resource_id" in filters and filters["resource_id"]:
        base = base.where(AuditLog.resource_id == filters["resource_id"])
    if "date_from" in filters and filters["date_from"]:
        base = base.where(AuditLog.created_at >= filters["date_from"])
    if "date_to" in filters and filters["date_to"]:
        base = base.where(AuditLog.created_at <= filters["date_to"])

    count_stmt = select(func.count()).select_from(base.subquery())
    total = (await db.execute(count_stmt)).scalar_one()

    stmt = base.order_by(AuditLog.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    rows = (await db.execute(stmt)).scalars().all()

    return PaginatedResponse.create(
        items=list(rows),
        total=total,
        page=page,
        page_size=page_size,
    )


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------


async def export_audit_logs(
    db: AsyncSession,
    org_id: uuid.UUID,
    filters: dict[str, Any] | None = None,
) -> bytes:
    """Export matching audit log entries as CSV bytes.

    Applies the same filters as ``query_audit_logs`` but without
    pagination (returns all matching rows).
    """
    filters = filters or {}
    base = select(AuditLog).where(AuditLog.org_id == org_id)

    if "user_id" in filters and filters["user_id"]:
        base = base.where(AuditLog.user_id == filters["user_id"])
    if "actor_type" in filters and filters["actor_type"]:
        base = base.where(AuditLog.actor_type == filters["actor_type"])
    if "action" in filters and filters["action"]:
        base = base.where(AuditLog.action == filters["action"])
    if "resource_type" in filters and filters["resource_type"]:
        base = base.where(AuditLog.resource_type == filters["resource_type"])
    if "date_from" in filters and filters["date_from"]:
        base = base.where(AuditLog.created_at >= filters["date_from"])
    if "date_to" in filters and filters["date_to"]:
        base = base.where(AuditLog.created_at <= filters["date_to"])

    stmt = base.order_by(AuditLog.created_at.desc())
    rows = (await db.execute(stmt)).scalars().all()

    # Build CSV
    output = io.StringIO()
    writer = csv.writer(output)

    # Header
    writer.writerow(
        [
            "id",
            "timestamp",
            "actor_type",
            "user_id",
            "action",
            "resource_type",
            "resource_id",
            "request_id",
            "details",
        ]
    )

    for entry in rows:
        writer.writerow(
            [
                str(entry.id),
                entry.created_at.isoformat() if entry.created_at else "",
                entry.actor_type,
                str(entry.user_id) if entry.user_id else "",
                entry.action,
                entry.resource_type,
                entry.resource_id or "",
                entry.request_id or "",
                str(entry.details) if entry.details else "",
            ]
        )

    return output.getvalue().encode("utf-8")
