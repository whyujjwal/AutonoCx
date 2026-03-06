"""Organization management and API key endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from autonomocx.core.database import get_db
from autonomocx.core.dependencies import get_current_user, require_role
from autonomocx.models.organization import PlanType
from autonomocx.models.user import User, UserRole
from autonomocx.services.organizations import (
    create_api_key,
    get_org_api_keys,
    get_organization,
    revoke_api_key,
    update_organization,
)

router = APIRouter(prefix="/organizations", tags=["organizations"])

# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class OrganizationOut(BaseModel):
    id: UUID
    name: str
    slug: str
    plan: PlanType
    settings: Optional[dict[str, Any]] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class OrganizationUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    settings: Optional[dict[str, Any]] = None


class ApiKeyOut(BaseModel):
    id: UUID
    name: str
    prefix: str = Field(..., description="First 8 characters of the key for identification")
    scopes: list[str]
    is_active: bool
    last_used_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ApiKeyCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    scopes: list[str] = Field(default_factory=lambda: ["read", "write"])
    expires_in_days: Optional[int] = Field(
        None, ge=1, le=365, description="Days until key expires (null = never)"
    )


class ApiKeyCreateResponse(BaseModel):
    """Returned only on creation -- includes the full secret key exactly once."""
    id: UUID
    name: str
    key: str = Field(..., description="Full API key (shown only once)")
    prefix: str
    scopes: list[str]
    expires_at: Optional[datetime] = None
    created_at: datetime


class MessageResponse(BaseModel):
    detail: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get(
    "/current",
    response_model=OrganizationOut,
    summary="Get current organization",
)
async def get_current_org(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> OrganizationOut:
    """Return the organization the current user belongs to."""
    org = await get_organization(db, org_id=current_user.org_id)
    if org is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )
    return OrganizationOut.model_validate(org)


@router.patch(
    "/current",
    response_model=OrganizationOut,
    summary="Update organization settings",
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)
async def update_current_org(
    body: OrganizationUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> OrganizationOut:
    """Update the current organization name or settings. Requires ADMIN role."""
    org = await update_organization(
        db,
        org_id=current_user.org_id,
        data=body.model_dump(exclude_unset=True),
    )
    if org is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )
    return OrganizationOut.model_validate(org)


@router.get(
    "/current/api-keys",
    response_model=list[ApiKeyOut],
    summary="List API keys",
)
async def list_api_keys(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ApiKeyOut]:
    """Return all API keys for the current organization."""
    keys = await get_org_api_keys(db, org_id=current_user.org_id)
    return [ApiKeyOut.model_validate(k) for k in keys]


@router.post(
    "/current/api-keys",
    response_model=ApiKeyCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new API key",
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)
async def create_new_api_key(
    body: ApiKeyCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ApiKeyCreateResponse:
    """Generate a new API key. The full key is returned only once. Requires ADMIN role."""
    result = await create_api_key(
        db,
        org_id=current_user.org_id,
        created_by=current_user.id,
        name=body.name,
        scopes=body.scopes,
        expires_in_days=body.expires_in_days,
    )
    return ApiKeyCreateResponse(
        id=result["id"],
        name=result["name"],
        key=result["key"],
        prefix=result["prefix"],
        scopes=result["scopes"],
        expires_at=result.get("expires_at"),
        created_at=result["created_at"],
    )


@router.delete(
    "/current/api-keys/{key_id}",
    response_model=MessageResponse,
    summary="Revoke an API key",
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)
async def delete_api_key(
    key_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MessageResponse:
    """Revoke (soft-delete) an API key. Requires ADMIN role."""
    success = await revoke_api_key(db, key_id=key_id, org_id=current_user.org_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found",
        )
    return MessageResponse(detail="API key revoked")
