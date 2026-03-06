"""Action execution endpoints: list, approve/reject (HITL queue), stats."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from autonomocx.core.database import get_db
from autonomocx.core.dependencies import get_current_user, require_role
from autonomocx.models.action import ActionStatus
from autonomocx.models.user import User, UserRole
from autonomocx.services.actions import (
    approve_action,
    get_action_by_id,
    get_action_stats,
    list_actions,
    list_pending_actions,
    reject_action,
)

router = APIRouter(prefix="/actions", tags=["actions"])

# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class ActionOut(BaseModel):
    id: UUID
    org_id: UUID
    conversation_id: UUID
    message_id: Optional[UUID] = None
    tool_id: UUID
    agent_id: Optional[UUID] = None
    status: ActionStatus
    input_params: Optional[dict[str, Any]] = None
    output_result: Optional[dict[str, Any]] = None
    error_message: Optional[str] = None
    risk_score: Optional[Decimal] = None
    risk_factors: Optional[dict[str, Any]] = None
    requires_approval: bool
    approved_by: Optional[UUID] = None
    approved_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    execution_time_ms: Optional[int] = None
    retry_count: int
    idempotency_key: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ActionDetailOut(ActionOut):
    """Extended action view with related entity names for display."""
    tool_name: Optional[str] = None
    agent_name: Optional[str] = None
    approver_name: Optional[str] = None
    conversation_customer_name: Optional[str] = None


class ApproveRequest(BaseModel):
    comment: Optional[str] = Field(None, max_length=1000)


class RejectRequest(BaseModel):
    reason: str = Field(..., min_length=1, max_length=1000)


class ActionStatsOut(BaseModel):
    total: int
    pending: int
    awaiting_approval: int
    approved: int
    rejected: int
    completed: int
    failed: int
    cancelled: int
    avg_execution_time_ms: Optional[float] = None
    approval_rate: Optional[float] = None
    avg_risk_score: Optional[float] = None


class PaginatedActions(BaseModel):
    items: list[ActionOut]
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
    response_model=PaginatedActions,
    summary="List action executions",
)
async def list_action_executions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: Optional[ActionStatus] = Query(None, alias="status"),
    tool_id: Optional[UUID] = None,
    agent_id: Optional[UUID] = None,
    conversation_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PaginatedActions:
    """Return filtered, paginated action executions for the current organization."""
    result = await list_actions(
        db,
        org_id=current_user.org_id,
        page=page,
        page_size=page_size,
        status=status_filter,
        tool_id=tool_id,
        agent_id=agent_id,
        conversation_id=conversation_id,
    )
    return PaginatedActions(
        items=[ActionOut.model_validate(a) for a in result["items"]],
        total=result["total"],
        page=page,
        page_size=page_size,
        pages=result["pages"],
    )


@router.get(
    "/pending",
    response_model=PaginatedActions,
    summary="List pending approvals (HITL queue)",
)
async def list_pending_approvals(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PaginatedActions:
    """Return actions awaiting human approval (Human-in-the-Loop queue)."""
    result = await list_pending_actions(
        db,
        org_id=current_user.org_id,
        page=page,
        page_size=page_size,
    )
    return PaginatedActions(
        items=[ActionOut.model_validate(a) for a in result["items"]],
        total=result["total"],
        page=page,
        page_size=page_size,
        pages=result["pages"],
    )


@router.get(
    "/stats",
    response_model=ActionStatsOut,
    summary="Action execution statistics",
)
async def action_statistics(
    period_days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ActionStatsOut:
    """Return aggregated action execution statistics for the current organization."""
    stats = await get_action_stats(
        db,
        org_id=current_user.org_id,
        period_days=period_days,
    )
    return ActionStatsOut(**stats)


@router.get(
    "/{action_id}",
    response_model=ActionDetailOut,
    summary="Get action details",
)
async def get_action(
    action_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ActionDetailOut:
    """Return full details of a specific action execution."""
    action = await get_action_by_id(
        db, action_id=action_id, org_id=current_user.org_id
    )
    if action is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Action not found",
        )
    return ActionDetailOut(**action)


@router.post(
    "/{action_id}/approve",
    response_model=ActionOut,
    summary="Approve a pending action",
    dependencies=[
        Depends(require_role(UserRole.ADMIN, UserRole.SUPERVISOR, UserRole.AGENT_REVIEWER))
    ],
)
async def approve_action_endpoint(
    action_id: UUID,
    body: ApproveRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ActionOut:
    """Approve a pending action for execution. Requires ADMIN, SUPERVISOR, or AGENT_REVIEWER role."""
    action = await approve_action(
        db,
        action_id=action_id,
        org_id=current_user.org_id,
        approved_by=current_user.id,
        comment=body.comment,
    )
    if action is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Action not found or not in awaiting_approval status",
        )
    return ActionOut.model_validate(action)


@router.post(
    "/{action_id}/reject",
    response_model=ActionOut,
    summary="Reject a pending action",
    dependencies=[
        Depends(require_role(UserRole.ADMIN, UserRole.SUPERVISOR, UserRole.AGENT_REVIEWER))
    ],
)
async def reject_action_endpoint(
    action_id: UUID,
    body: RejectRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ActionOut:
    """Reject a pending action with a reason. Requires ADMIN, SUPERVISOR, or AGENT_REVIEWER role."""
    action = await reject_action(
        db,
        action_id=action_id,
        org_id=current_user.org_id,
        rejected_by=current_user.id,
        reason=body.reason,
    )
    if action is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Action not found or not in awaiting_approval status",
        )
    return ActionOut.model_validate(action)
