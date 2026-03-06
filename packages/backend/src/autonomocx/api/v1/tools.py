"""Tool CRUD and testing endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from autonomocx.core.database import get_db
from autonomocx.core.dependencies import get_current_user, require_role
from autonomocx.models.tool import RiskLevel
from autonomocx.models.user import User, UserRole
from autonomocx.services.tools import (
    create_tool,
    delete_tool,
    get_tool_by_id,
    list_tools,
    test_tool,
    update_tool,
)

router = APIRouter(prefix="/tools", tags=["tools"])

# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class ToolOut(BaseModel):
    id: UUID
    org_id: UUID
    name: str
    display_name: str | None = None
    description: str | None = None
    category: str | None = None
    parameters_schema: dict[str, Any] | None = None
    endpoint_url: str | None = None
    http_method: str | None = None
    headers_template: dict[str, Any] | None = None
    auth_type: str | None = None
    timeout_seconds: int | None = None
    retry_config: dict[str, Any] | None = None
    risk_level: RiskLevel
    requires_approval: bool
    is_active: bool
    is_builtin: bool
    version: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ToolCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    display_name: str | None = Field(None, max_length=255)
    description: str | None = None
    category: str | None = Field(None, max_length=128)
    parameters_schema: dict[str, Any] | None = None
    endpoint_url: str | None = Field(None, max_length=2048)
    http_method: str | None = Field(None, max_length=10)
    headers_template: dict[str, Any] | None = None
    auth_type: str | None = Field(None, max_length=64)
    auth_config: dict[str, Any] | None = None
    timeout_seconds: int | None = Field(30, ge=1, le=300)
    retry_config: dict[str, Any] | None = None
    risk_level: RiskLevel = RiskLevel.LOW
    requires_approval: bool = False
    version: str = Field("1.0.0", max_length=32)


class ToolUpdateRequest(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    display_name: str | None = Field(None, max_length=255)
    description: str | None = None
    category: str | None = Field(None, max_length=128)
    parameters_schema: dict[str, Any] | None = None
    endpoint_url: str | None = Field(None, max_length=2048)
    http_method: str | None = Field(None, max_length=10)
    headers_template: dict[str, Any] | None = None
    auth_type: str | None = Field(None, max_length=64)
    auth_config: dict[str, Any] | None = None
    timeout_seconds: int | None = Field(None, ge=1, le=300)
    retry_config: dict[str, Any] | None = None
    risk_level: RiskLevel | None = None
    requires_approval: bool | None = None
    is_active: bool | None = None
    version: str | None = Field(None, max_length=32)


class ToolTestRequest(BaseModel):
    input_params: dict[str, Any] = Field(..., description="Parameters to pass to the tool")


class ToolTestResponse(BaseModel):
    success: bool
    status_code: int | None = None
    output: dict[str, Any] | None = None
    error: str | None = None
    execution_time_ms: int


class PaginatedTools(BaseModel):
    items: list[ToolOut]
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
    response_model=PaginatedTools,
    summary="List tools",
)
async def list_org_tools(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    category: str | None = None,
    is_active: bool | None = None,
    risk_level: RiskLevel | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PaginatedTools:
    """Return paginated tools for the current organization."""
    result = await list_tools(
        db,
        org_id=current_user.org_id,
        page=page,
        page_size=page_size,
        category=category,
        is_active=is_active,
        risk_level=risk_level,
    )
    return PaginatedTools(
        items=[ToolOut.model_validate(t) for t in result["items"]],
        total=result["total"],
        page=page,
        page_size=page_size,
        pages=result["pages"],
    )


@router.get(
    "/{tool_id}",
    response_model=ToolOut,
    summary="Get tool details",
)
async def get_tool(
    tool_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ToolOut:
    """Return a specific tool by ID."""
    tool = await get_tool_by_id(db, tool_id=tool_id, org_id=current_user.org_id)
    if tool is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tool not found",
        )
    return ToolOut.model_validate(tool)


@router.post(
    "/",
    response_model=ToolOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a tool",
    dependencies=[Depends(require_role(UserRole.ADMIN, UserRole.DEVELOPER))],
)
async def create_new_tool(
    body: ToolCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ToolOut:
    """Create a new tool definition. Requires ADMIN or DEVELOPER role."""
    tool = await create_tool(
        db,
        org_id=current_user.org_id,
        **body.model_dump(),
    )
    return ToolOut.model_validate(tool)


@router.patch(
    "/{tool_id}",
    response_model=ToolOut,
    summary="Update a tool",
    dependencies=[Depends(require_role(UserRole.ADMIN, UserRole.DEVELOPER))],
)
async def update_existing_tool(
    tool_id: UUID,
    body: ToolUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ToolOut:
    """Update an existing tool definition. Requires ADMIN or DEVELOPER role."""
    tool = await update_tool(
        db,
        tool_id=tool_id,
        org_id=current_user.org_id,
        data=body.model_dump(exclude_unset=True),
    )
    if tool is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tool not found",
        )
    return ToolOut.model_validate(tool)


@router.delete(
    "/{tool_id}",
    response_model=MessageResponse,
    summary="Delete a tool",
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)
async def delete_existing_tool(
    tool_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MessageResponse:
    """Soft-delete a tool. Requires ADMIN role."""
    success = await delete_tool(db, tool_id=tool_id, org_id=current_user.org_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tool not found",
        )
    return MessageResponse(detail="Tool deleted")


@router.post(
    "/{tool_id}/test",
    response_model=ToolTestResponse,
    summary="Test a tool with sample input",
    dependencies=[Depends(require_role(UserRole.ADMIN, UserRole.DEVELOPER))],
)
async def test_tool_endpoint(
    tool_id: UUID,
    body: ToolTestRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ToolTestResponse:
    """Execute a tool with test parameters in a sandboxed context and return the result."""
    tool = await get_tool_by_id(db, tool_id=tool_id, org_id=current_user.org_id)
    if tool is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tool not found",
        )
    result = await test_tool(
        db,
        tool=tool,
        input_params=body.input_params,
    )
    return ToolTestResponse(**result)
