"""Workflow CRUD and activation endpoints."""

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
from autonomocx.services.workflows import (
    activate_workflow,
    create_workflow,
    delete_workflow,
    get_workflow_by_id,
    list_workflows,
    update_workflow,
)

router = APIRouter(prefix="/workflows", tags=["workflows"])

# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class WorkflowStepOut(BaseModel):
    id: str
    type: str
    config: dict[str, Any]
    next_steps: Optional[list[str]] = None
    condition: Optional[str] = None


class WorkflowOut(BaseModel):
    id: UUID
    org_id: UUID
    name: str
    description: Optional[str] = None
    trigger_type: str
    trigger_config: Optional[dict[str, Any]] = None
    steps: list[WorkflowStepOut] = []
    is_active: bool
    version: int
    metadata_: Optional[dict[str, Any]] = Field(None, alias="metadata")
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True, "populate_by_name": True}


class WorkflowCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    trigger_type: str = Field(..., max_length=64)
    trigger_config: Optional[dict[str, Any]] = None
    steps: list[dict[str, Any]] = Field(
        ..., min_length=1, description="Ordered list of workflow steps"
    )
    metadata: Optional[dict[str, Any]] = None


class WorkflowUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    trigger_type: Optional[str] = Field(None, max_length=64)
    trigger_config: Optional[dict[str, Any]] = None
    steps: Optional[list[dict[str, Any]]] = None
    is_active: Optional[bool] = None
    metadata: Optional[dict[str, Any]] = None


class PaginatedWorkflows(BaseModel):
    items: list[WorkflowOut]
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
    response_model=PaginatedWorkflows,
    summary="List workflows",
)
async def list_org_workflows(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    is_active: Optional[bool] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PaginatedWorkflows:
    """Return paginated workflows for the current organization."""
    result = await list_workflows(
        db,
        org_id=current_user.org_id,
        page=page,
        page_size=page_size,
        is_active=is_active,
    )
    return PaginatedWorkflows(
        items=[WorkflowOut.model_validate(w) for w in result["items"]],
        total=result["total"],
        page=page,
        page_size=page_size,
        pages=result["pages"],
    )


@router.get(
    "/{workflow_id}",
    response_model=WorkflowOut,
    summary="Get workflow",
)
async def get_workflow(
    workflow_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> WorkflowOut:
    """Return a specific workflow configuration."""
    workflow = await get_workflow_by_id(
        db, workflow_id=workflow_id, org_id=current_user.org_id
    )
    if workflow is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow not found",
        )
    return WorkflowOut.model_validate(workflow)


@router.post(
    "/",
    response_model=WorkflowOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a workflow",
    dependencies=[Depends(require_role(UserRole.ADMIN, UserRole.DEVELOPER))],
)
async def create_new_workflow(
    body: WorkflowCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> WorkflowOut:
    """Create a new workflow. Requires ADMIN or DEVELOPER role."""
    workflow = await create_workflow(
        db,
        org_id=current_user.org_id,
        name=body.name,
        description=body.description,
        trigger_type=body.trigger_type,
        trigger_config=body.trigger_config,
        steps=body.steps,
        metadata=body.metadata,
    )
    return WorkflowOut.model_validate(workflow)


@router.patch(
    "/{workflow_id}",
    response_model=WorkflowOut,
    summary="Update a workflow",
    dependencies=[Depends(require_role(UserRole.ADMIN, UserRole.DEVELOPER))],
)
async def update_existing_workflow(
    workflow_id: UUID,
    body: WorkflowUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> WorkflowOut:
    """Update an existing workflow. Requires ADMIN or DEVELOPER role."""
    workflow = await update_workflow(
        db,
        workflow_id=workflow_id,
        org_id=current_user.org_id,
        data=body.model_dump(exclude_unset=True),
    )
    if workflow is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow not found",
        )
    return WorkflowOut.model_validate(workflow)


@router.delete(
    "/{workflow_id}",
    response_model=MessageResponse,
    summary="Delete a workflow",
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)
async def delete_existing_workflow(
    workflow_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MessageResponse:
    """Soft-delete a workflow. Requires ADMIN role."""
    success = await delete_workflow(
        db, workflow_id=workflow_id, org_id=current_user.org_id
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow not found",
        )
    return MessageResponse(detail="Workflow deleted")


@router.post(
    "/{workflow_id}/activate",
    response_model=WorkflowOut,
    summary="Activate a workflow",
    dependencies=[Depends(require_role(UserRole.ADMIN, UserRole.DEVELOPER))],
)
async def activate_workflow_endpoint(
    workflow_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> WorkflowOut:
    """Activate a workflow so it starts processing triggers. Requires ADMIN or DEVELOPER role."""
    workflow = await activate_workflow(
        db,
        workflow_id=workflow_id,
        org_id=current_user.org_id,
    )
    if workflow is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow not found",
        )
    return WorkflowOut.model_validate(workflow)
