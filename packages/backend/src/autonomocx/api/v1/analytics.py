"""Analytics dashboard and reporting endpoints."""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from autonomocx.core.database import get_db
from autonomocx.core.dependencies import get_current_user
from autonomocx.models.user import User
from autonomocx.services.analytics import (
    get_action_metrics,
    get_agent_performance,
    get_conversation_metrics,
    get_cost_breakdown,
    get_dashboard_summary,
)

router = APIRouter(prefix="/analytics", tags=["analytics"])

# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class DashboardKPI(BaseModel):
    total_conversations: int
    active_conversations: int
    avg_resolution_time_seconds: float | None = None
    avg_satisfaction_score: float | None = None
    total_messages_today: int
    total_actions_today: int
    escalation_rate: float
    ai_resolution_rate: float
    pending_approvals: int
    total_cost_today_usd: float | None = None


class TimeSeriesPoint(BaseModel):
    timestamp: datetime
    value: float
    label: str | None = None


class ConversationMetrics(BaseModel):
    period_start: date
    period_end: date
    total: int
    by_status: dict[str, int]
    by_channel: dict[str, int]
    by_priority: dict[str, int]
    avg_resolution_time_seconds: float | None = None
    avg_satisfaction_score: float | None = None
    trend: list[TimeSeriesPoint] = []


class ActionMetrics(BaseModel):
    period_start: date
    period_end: date
    total: int
    by_status: dict[str, int]
    approval_rate: float | None = None
    avg_execution_time_ms: float | None = None
    top_tools: list[dict[str, int | str]] = []
    trend: list[TimeSeriesPoint] = []


class AgentPerformanceItem(BaseModel):
    agent_id: UUID
    agent_name: str
    total_conversations: int
    avg_resolution_time_seconds: float | None = None
    avg_satisfaction_score: float | None = None
    escalation_rate: float
    total_messages: int
    total_actions: int
    avg_latency_ms: float | None = None
    total_cost_usd: float | None = None


class AgentPerformanceReport(BaseModel):
    period_start: date
    period_end: date
    agents: list[AgentPerformanceItem]


class CostLineItem(BaseModel):
    category: str
    model: str | None = None
    provider: str | None = None
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost_usd: float


class CostBreakdown(BaseModel):
    period_start: date
    period_end: date
    total_cost_usd: float
    items: list[CostLineItem]
    daily_trend: list[TimeSeriesPoint] = []


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get(
    "/dashboard",
    response_model=DashboardKPI,
    summary="Dashboard KPI summary",
)
async def dashboard(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DashboardKPI:
    """Return real-time KPI summary for the analytics dashboard."""
    result = await get_dashboard_summary(db, org_id=current_user.org_id)
    return DashboardKPI(**result)


@router.get(
    "/conversations",
    response_model=ConversationMetrics,
    summary="Conversation metrics over time",
)
async def conversation_metrics(
    period_days: int = Query(30, ge=1, le=365),
    channel: str | None = None,
    agent_id: UUID | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ConversationMetrics:
    """Return conversation volume and quality metrics with time series data."""
    result = await get_conversation_metrics(
        db,
        org_id=current_user.org_id,
        period_days=period_days,
        channel=channel,
        agent_id=agent_id,
    )
    return ConversationMetrics(**result)


@router.get(
    "/actions",
    response_model=ActionMetrics,
    summary="Action execution metrics",
)
async def action_metrics(
    period_days: int = Query(30, ge=1, le=365),
    tool_id: UUID | None = None,
    agent_id: UUID | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ActionMetrics:
    """Return action execution metrics with approval rates and tool usage."""
    result = await get_action_metrics(
        db,
        org_id=current_user.org_id,
        period_days=period_days,
        tool_id=tool_id,
        agent_id=agent_id,
    )
    return ActionMetrics(**result)


@router.get(
    "/agents",
    response_model=AgentPerformanceReport,
    summary="Per-agent performance metrics",
)
async def agent_performance(
    period_days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AgentPerformanceReport:
    """Return performance metrics broken down by agent."""
    result = await get_agent_performance(
        db,
        org_id=current_user.org_id,
        period_days=period_days,
    )
    return AgentPerformanceReport(**result)


@router.get(
    "/cost",
    response_model=CostBreakdown,
    summary="LLM cost breakdown",
)
async def cost_breakdown(
    period_days: int = Query(30, ge=1, le=365),
    provider: str | None = None,
    model: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CostBreakdown:
    """Return LLM cost breakdown by provider, model, and day."""
    result = await get_cost_breakdown(
        db,
        org_id=current_user.org_id,
        period_days=period_days,
        provider=provider,
        model=model,
    )
    return CostBreakdown(**result)
