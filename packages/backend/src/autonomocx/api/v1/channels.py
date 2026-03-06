"""Channel configuration CRUD and testing endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from autonomocx.core.database import get_db
from autonomocx.core.dependencies import get_current_user, require_role
from autonomocx.models.conversation import ChannelType
from autonomocx.models.user import User, UserRole
from autonomocx.services.channels import (
    create_channel_config,
    delete_channel_config,
    get_channel_config_by_id,
    list_channel_configs,
    test_channel_config,
    update_channel_config,
)

router = APIRouter(prefix="/channels", tags=["channels"])

# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class ChannelConfigOut(BaseModel):
    id: UUID
    org_id: UUID
    agent_id: Optional[UUID] = None
    channel_type: ChannelType
    name: str
    config: Optional[dict[str, Any]] = None
    is_active: bool
    webhook_url: Optional[str] = None
    metadata_: Optional[dict[str, Any]] = Field(None, alias="metadata")
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True, "populate_by_name": True}


class ChannelConfigCreateRequest(BaseModel):
    channel_type: ChannelType
    name: str = Field(..., min_length=1, max_length=255)
    agent_id: Optional[UUID] = None
    config: Optional[dict[str, Any]] = None
    webhook_url: Optional[str] = Field(None, max_length=2048)
    metadata: Optional[dict[str, Any]] = None


class ChannelConfigUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    agent_id: Optional[UUID] = None
    config: Optional[dict[str, Any]] = None
    is_active: Optional[bool] = None
    webhook_url: Optional[str] = Field(None, max_length=2048)
    metadata: Optional[dict[str, Any]] = None


class ChannelTestRequest(BaseModel):
    test_message: str = Field(
        "Hello, this is a test message from AutonoCX.",
        min_length=1,
        max_length=1000,
    )


class ChannelTestResponse(BaseModel):
    success: bool
    channel_type: ChannelType
    response_message: Optional[str] = None
    error: Optional[str] = None
    latency_ms: int


class PaginatedChannelConfigs(BaseModel):
    items: list[ChannelConfigOut]
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
    response_model=PaginatedChannelConfigs,
    summary="List channel configurations",
)
async def list_channels(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    channel_type: Optional[ChannelType] = None,
    is_active: Optional[bool] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PaginatedChannelConfigs:
    """Return paginated channel configurations for the current organization."""
    result = await list_channel_configs(
        db,
        org_id=current_user.org_id,
        page=page,
        page_size=page_size,
        channel_type=channel_type,
        is_active=is_active,
    )
    return PaginatedChannelConfigs(
        items=[ChannelConfigOut.model_validate(c) for c in result["items"]],
        total=result["total"],
        page=page,
        page_size=page_size,
        pages=result["pages"],
    )


@router.get(
    "/{config_id}",
    response_model=ChannelConfigOut,
    summary="Get channel configuration",
)
async def get_channel(
    config_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ChannelConfigOut:
    """Return a specific channel configuration."""
    config = await get_channel_config_by_id(
        db, config_id=config_id, org_id=current_user.org_id
    )
    if config is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Channel configuration not found",
        )
    return ChannelConfigOut.model_validate(config)


@router.post(
    "/",
    response_model=ChannelConfigOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a channel configuration",
    dependencies=[Depends(require_role(UserRole.ADMIN, UserRole.DEVELOPER))],
)
async def create_channel(
    body: ChannelConfigCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ChannelConfigOut:
    """Create a new channel configuration. Requires ADMIN or DEVELOPER role."""
    config = await create_channel_config(
        db,
        org_id=current_user.org_id,
        channel_type=body.channel_type,
        name=body.name,
        agent_id=body.agent_id,
        config=body.config,
        webhook_url=body.webhook_url,
        metadata=body.metadata,
    )
    return ChannelConfigOut.model_validate(config)


@router.patch(
    "/{config_id}",
    response_model=ChannelConfigOut,
    summary="Update a channel configuration",
    dependencies=[Depends(require_role(UserRole.ADMIN, UserRole.DEVELOPER))],
)
async def update_channel(
    config_id: UUID,
    body: ChannelConfigUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ChannelConfigOut:
    """Update an existing channel configuration. Requires ADMIN or DEVELOPER role."""
    config = await update_channel_config(
        db,
        config_id=config_id,
        org_id=current_user.org_id,
        data=body.model_dump(exclude_unset=True),
    )
    if config is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Channel configuration not found",
        )
    return ChannelConfigOut.model_validate(config)


@router.delete(
    "/{config_id}",
    response_model=MessageResponse,
    summary="Delete a channel configuration",
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)
async def delete_channel(
    config_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MessageResponse:
    """Soft-delete a channel configuration. Requires ADMIN role."""
    success = await delete_channel_config(
        db, config_id=config_id, org_id=current_user.org_id
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Channel configuration not found",
        )
    return MessageResponse(detail="Channel configuration deleted")


@router.post(
    "/{config_id}/test",
    response_model=ChannelTestResponse,
    summary="Test a channel configuration",
    dependencies=[Depends(require_role(UserRole.ADMIN, UserRole.DEVELOPER))],
)
async def test_channel(
    config_id: UUID,
    body: ChannelTestRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ChannelTestResponse:
    """Send a test message through the channel to verify configuration."""
    config = await get_channel_config_by_id(
        db, config_id=config_id, org_id=current_user.org_id
    )
    if config is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Channel configuration not found",
        )
    result = await test_channel_config(
        db,
        config=config,
        test_message=body.test_message,
    )
    return ChannelTestResponse(**result)
