"""Agent configuration CRUD, testing, and metrics endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from autonomocx.core.database import get_db
from autonomocx.core.dependencies import get_current_user, require_role
from autonomocx.models.user import User, UserRole
from autonomocx.services.agents import (
    create_agent,
    delete_agent,
    get_agent_by_id,
    get_agent_metrics,
    list_agents,
    test_agent,
    update_agent,
)

router = APIRouter(prefix="/agents", tags=["agents"])

# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class AgentOut(BaseModel):
    id: UUID
    org_id: UUID
    name: str
    description: Optional[str] = None
    system_prompt: Optional[str] = None
    llm_provider: Optional[str] = None
    llm_model: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    tools_enabled: Optional[list[UUID]] = None
    fallback_agent_id: Optional[UUID] = None
    is_active: bool
    metadata_: Optional[dict[str, Any]] = Field(None, alias="metadata")
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True, "populate_by_name": True}


class AgentCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    system_prompt: Optional[str] = None
    llm_provider: Optional[str] = Field(None, max_length=64)
    llm_model: Optional[str] = Field(None, max_length=128)
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(None, ge=1, le=128000)
    tools_enabled: Optional[list[UUID]] = None
    fallback_agent_id: Optional[UUID] = None
    metadata: Optional[dict[str, Any]] = None


class AgentUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    system_prompt: Optional[str] = None
    llm_provider: Optional[str] = Field(None, max_length=64)
    llm_model: Optional[str] = Field(None, max_length=128)
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(None, ge=1, le=128000)
    tools_enabled: Optional[list[UUID]] = None
    fallback_agent_id: Optional[UUID] = None
    is_active: Optional[bool] = None
    metadata: Optional[dict[str, Any]] = None


class AgentTestRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4096)
    context: Optional[dict[str, Any]] = None


class AgentTestResponse(BaseModel):
    reply: str
    model_used: str
    prompt_tokens: int
    completion_tokens: int
    latency_ms: int
    tools_called: list[str] = []


class AgentMetricsOut(BaseModel):
    agent_id: UUID
    total_conversations: int
    active_conversations: int
    avg_resolution_time_seconds: Optional[float] = None
    avg_satisfaction_score: Optional[float] = None
    total_messages: int
    total_actions: int
    escalation_rate: float
    avg_latency_ms: Optional[float] = None
    total_cost_usd: Optional[float] = None
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None


class PaginatedAgents(BaseModel):
    items: list[AgentOut]
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
    response_model=PaginatedAgents,
    summary="List agent configurations",
)
async def list_agent_configs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    is_active: Optional[bool] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PaginatedAgents:
    """Return paginated agent configurations for the current organization."""
    result = await list_agents(
        db,
        org_id=current_user.org_id,
        page=page,
        page_size=page_size,
        is_active=is_active,
    )
    return PaginatedAgents(
        items=[AgentOut.model_validate(a) for a in result["items"]],
        total=result["total"],
        page=page,
        page_size=page_size,
        pages=result["pages"],
    )


@router.get(
    "/{agent_id}",
    response_model=AgentOut,
    summary="Get agent configuration",
)
async def get_agent(
    agent_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AgentOut:
    """Return a specific agent configuration."""
    agent = await get_agent_by_id(
        db, agent_id=agent_id, org_id=current_user.org_id
    )
    if agent is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found",
        )
    return AgentOut.model_validate(agent)


@router.post(
    "/",
    response_model=AgentOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create an agent configuration",
    dependencies=[Depends(require_role(UserRole.ADMIN, UserRole.DEVELOPER))],
)
async def create_agent_config(
    body: AgentCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AgentOut:
    """Create a new agent configuration. Requires ADMIN or DEVELOPER role."""
    agent = await create_agent(
        db,
        org_id=current_user.org_id,
        name=body.name,
        description=body.description,
        system_prompt=body.system_prompt,
        llm_provider=body.llm_provider,
        llm_model=body.llm_model,
        temperature=body.temperature,
        max_tokens=body.max_tokens,
        tools_enabled=body.tools_enabled,
        fallback_agent_id=body.fallback_agent_id,
        metadata=body.metadata,
    )
    return AgentOut.model_validate(agent)


@router.patch(
    "/{agent_id}",
    response_model=AgentOut,
    summary="Update an agent configuration",
    dependencies=[Depends(require_role(UserRole.ADMIN, UserRole.DEVELOPER))],
)
async def update_agent_config(
    agent_id: UUID,
    body: AgentUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AgentOut:
    """Update an existing agent configuration. Requires ADMIN or DEVELOPER role."""
    agent = await update_agent(
        db,
        agent_id=agent_id,
        org_id=current_user.org_id,
        data=body.model_dump(exclude_unset=True),
    )
    if agent is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found",
        )
    return AgentOut.model_validate(agent)


@router.delete(
    "/{agent_id}",
    response_model=MessageResponse,
    summary="Delete an agent configuration",
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)
async def delete_agent_config(
    agent_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MessageResponse:
    """Soft-delete an agent configuration. Requires ADMIN role."""
    success = await delete_agent(
        db, agent_id=agent_id, org_id=current_user.org_id
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found",
        )
    return MessageResponse(detail="Agent deleted")


@router.post(
    "/{agent_id}/test",
    response_model=AgentTestResponse,
    summary="Test an agent with a sample message",
    dependencies=[Depends(require_role(UserRole.ADMIN, UserRole.DEVELOPER))],
)
async def test_agent_endpoint(
    agent_id: UUID,
    body: AgentTestRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AgentTestResponse:
    """Send a test message through the agent pipeline and return the response
    without persisting any data.
    """
    agent = await get_agent_by_id(
        db, agent_id=agent_id, org_id=current_user.org_id
    )
    if agent is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found",
        )
    result = await test_agent(
        db,
        agent=agent,
        message=body.message,
        context=body.context,
    )
    return AgentTestResponse(**result)


@router.get(
    "/{agent_id}/metrics",
    response_model=AgentMetricsOut,
    summary="Get agent performance metrics",
)
async def get_metrics(
    agent_id: UUID,
    period_days: int = Query(30, ge=1, le=365, description="Lookback period in days"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AgentMetricsOut:
    """Return aggregated performance metrics for a specific agent."""
    agent = await get_agent_by_id(
        db, agent_id=agent_id, org_id=current_user.org_id
    )
    if agent is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found",
        )
    metrics = await get_agent_metrics(
        db,
        agent_id=agent_id,
        org_id=current_user.org_id,
        period_days=period_days,
    )
    return AgentMetricsOut(**metrics)
