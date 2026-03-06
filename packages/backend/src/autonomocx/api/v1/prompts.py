"""Prompt template CRUD with versioning, publishing, and rollback."""

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
from autonomocx.services.prompts import (
    create_prompt_template,
    create_prompt_version,
    delete_prompt_template,
    get_prompt_template,
    list_prompt_templates,
    publish_prompt_version,
    rollback_prompt_version,
    update_prompt_template,
)

router = APIRouter(prefix="/prompts", tags=["prompts"])

# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class PromptVersionOut(BaseModel):
    id: UUID
    prompt_template_id: UUID
    version_number: int
    content: str
    variables: list[str] = []
    is_published: bool
    published_at: Optional[datetime] = None
    created_by: Optional[UUID] = None
    change_notes: Optional[str] = None
    metadata_: Optional[dict[str, Any]] = Field(None, alias="metadata")
    created_at: datetime

    model_config = {"from_attributes": True, "populate_by_name": True}


class PromptTemplateOut(BaseModel):
    id: UUID
    org_id: UUID
    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    current_version: Optional[int] = None
    is_active: bool
    metadata_: Optional[dict[str, Any]] = Field(None, alias="metadata")
    created_at: datetime
    updated_at: datetime
    active_version: Optional[PromptVersionOut] = None

    model_config = {"from_attributes": True, "populate_by_name": True}


class PromptTemplateCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    category: Optional[str] = Field(None, max_length=128)
    content: str = Field(..., min_length=1, description="Initial prompt content")
    variables: list[str] = Field(
        default_factory=list,
        description="Template variable names (e.g., ['customer_name', 'issue'])",
    )
    metadata: Optional[dict[str, Any]] = None


class PromptTemplateUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    category: Optional[str] = Field(None, max_length=128)
    is_active: Optional[bool] = None
    metadata: Optional[dict[str, Any]] = None


class PromptVersionCreateRequest(BaseModel):
    content: str = Field(..., min_length=1)
    variables: list[str] = Field(default_factory=list)
    change_notes: Optional[str] = Field(None, max_length=1000)


class PaginatedPromptTemplates(BaseModel):
    items: list[PromptTemplateOut]
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
    response_model=PaginatedPromptTemplates,
    summary="List prompt templates",
)
async def list_prompts(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    category: Optional[str] = None,
    is_active: Optional[bool] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PaginatedPromptTemplates:
    """Return paginated prompt templates for the current organization."""
    result = await list_prompt_templates(
        db,
        org_id=current_user.org_id,
        page=page,
        page_size=page_size,
        category=category,
        is_active=is_active,
    )
    return PaginatedPromptTemplates(
        items=[PromptTemplateOut.model_validate(p) for p in result["items"]],
        total=result["total"],
        page=page,
        page_size=page_size,
        pages=result["pages"],
    )


@router.get(
    "/{template_id}",
    response_model=PromptTemplateOut,
    summary="Get prompt template",
)
async def get_prompt(
    template_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PromptTemplateOut:
    """Return a specific prompt template with its active version."""
    template = await get_prompt_template(
        db, template_id=template_id, org_id=current_user.org_id
    )
    if template is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prompt template not found",
        )
    return PromptTemplateOut.model_validate(template)


@router.post(
    "/",
    response_model=PromptTemplateOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a prompt template",
    dependencies=[Depends(require_role(UserRole.ADMIN, UserRole.DEVELOPER))],
)
async def create_prompt(
    body: PromptTemplateCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PromptTemplateOut:
    """Create a new prompt template with an initial version. Requires ADMIN or DEVELOPER role."""
    template = await create_prompt_template(
        db,
        org_id=current_user.org_id,
        created_by=current_user.id,
        name=body.name,
        description=body.description,
        category=body.category,
        content=body.content,
        variables=body.variables,
        metadata=body.metadata,
    )
    return PromptTemplateOut.model_validate(template)


@router.patch(
    "/{template_id}",
    response_model=PromptTemplateOut,
    summary="Update prompt template metadata",
    dependencies=[Depends(require_role(UserRole.ADMIN, UserRole.DEVELOPER))],
)
async def update_prompt(
    template_id: UUID,
    body: PromptTemplateUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PromptTemplateOut:
    """Update prompt template name, description, or category. Requires ADMIN or DEVELOPER role."""
    template = await update_prompt_template(
        db,
        template_id=template_id,
        org_id=current_user.org_id,
        data=body.model_dump(exclude_unset=True),
    )
    if template is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prompt template not found",
        )
    return PromptTemplateOut.model_validate(template)


@router.delete(
    "/{template_id}",
    response_model=MessageResponse,
    summary="Delete a prompt template",
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)
async def delete_prompt(
    template_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MessageResponse:
    """Soft-delete a prompt template and all its versions. Requires ADMIN role."""
    success = await delete_prompt_template(
        db, template_id=template_id, org_id=current_user.org_id
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prompt template not found",
        )
    return MessageResponse(detail="Prompt template deleted")


@router.post(
    "/{template_id}/versions",
    response_model=PromptVersionOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new prompt version",
    dependencies=[Depends(require_role(UserRole.ADMIN, UserRole.DEVELOPER))],
)
async def create_version(
    template_id: UUID,
    body: PromptVersionCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PromptVersionOut:
    """Create a new draft version for a prompt template. Requires ADMIN or DEVELOPER role."""
    # Verify template exists
    template = await get_prompt_template(
        db, template_id=template_id, org_id=current_user.org_id
    )
    if template is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prompt template not found",
        )
    version = await create_prompt_version(
        db,
        template_id=template_id,
        created_by=current_user.id,
        content=body.content,
        variables=body.variables,
        change_notes=body.change_notes,
    )
    return PromptVersionOut.model_validate(version)


@router.post(
    "/{template_id}/versions/{version_id}/publish",
    response_model=PromptVersionOut,
    summary="Publish a prompt version",
    dependencies=[Depends(require_role(UserRole.ADMIN, UserRole.DEVELOPER))],
)
async def publish_version(
    template_id: UUID,
    version_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PromptVersionOut:
    """Publish a specific version, making it the active version for the template."""
    version = await publish_prompt_version(
        db,
        template_id=template_id,
        version_id=version_id,
        org_id=current_user.org_id,
    )
    if version is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prompt version not found",
        )
    return PromptVersionOut.model_validate(version)


@router.post(
    "/{template_id}/versions/{version_id}/rollback",
    response_model=PromptVersionOut,
    summary="Rollback to a previous prompt version",
    dependencies=[Depends(require_role(UserRole.ADMIN, UserRole.DEVELOPER))],
)
async def rollback_version(
    template_id: UUID,
    version_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PromptVersionOut:
    """Rollback to a previously published version, re-publishing it as the active version."""
    version = await rollback_prompt_version(
        db,
        template_id=template_id,
        version_id=version_id,
        org_id=current_user.org_id,
    )
    if version is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prompt version not found",
        )
    return PromptVersionOut.model_validate(version)
