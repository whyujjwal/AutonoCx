"""Audit log query and export endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from autonomocx.core.database import get_db
from autonomocx.core.dependencies import get_current_user, require_role
from autonomocx.models.user import User, UserRole
from autonomocx.services.audit import export_audit_logs_csv, query_audit_logs

router = APIRouter(
    prefix="/audit",
    tags=["audit"],
    dependencies=[Depends(require_role(UserRole.ADMIN, UserRole.SUPERVISOR))],
)

# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class AuditLogOut(BaseModel):
    id: UUID
    org_id: UUID
    user_id: UUID | None = None
    user_email: str | None = None
    action: str
    resource_type: str
    resource_id: str | None = None
    details: dict[str, Any] | None = None
    ip_address: str | None = None
    user_agent: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class PaginatedAuditLogs(BaseModel):
    items: list[AuditLogOut]
    total: int
    page: int
    page_size: int
    pages: int


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get(
    "/",
    response_model=PaginatedAuditLogs,
    summary="Query audit logs",
)
async def list_audit_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    action: str | None = Query(None, description="Filter by action type"),
    resource_type: str | None = Query(None, description="Filter by resource type"),
    resource_id: str | None = Query(None, description="Filter by resource ID"),
    user_id: UUID | None = Query(None, description="Filter by user"),
    start_date: datetime | None = Query(None, description="Start of date range"),
    end_date: datetime | None = Query(None, description="End of date range"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PaginatedAuditLogs:
    """Return filtered, paginated audit logs. Requires ADMIN or SUPERVISOR role."""
    result = await query_audit_logs(
        db,
        org_id=current_user.org_id,
        page=page,
        page_size=page_size,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        user_id=user_id,
        start_date=start_date,
        end_date=end_date,
    )
    return PaginatedAuditLogs(
        items=[AuditLogOut.model_validate(log) for log in result["items"]],
        total=result["total"],
        page=page,
        page_size=page_size,
        pages=result["pages"],
    )


@router.get(
    "/export",
    summary="Export audit logs as CSV",
    response_class=StreamingResponse,
)
async def export_audit_logs(
    action: str | None = Query(None),
    resource_type: str | None = Query(None),
    user_id: UUID | None = Query(None),
    start_date: datetime | None = Query(None),
    end_date: datetime | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StreamingResponse:
    """Export filtered audit logs as a downloadable CSV file.

    Requires ADMIN or SUPERVISOR role.
    """
    csv_stream = await export_audit_logs_csv(
        db,
        org_id=current_user.org_id,
        action=action,
        resource_type=resource_type,
        user_id=user_id,
        start_date=start_date,
        end_date=end_date,
    )
    return StreamingResponse(
        csv_stream,
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=audit_logs.csv",
        },
    )
