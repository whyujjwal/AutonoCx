"""Prompt template & version schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Prompt template requests
# ---------------------------------------------------------------------------


class PromptTemplateCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    category: Optional[str] = Field(None, max_length=128)
    description: Optional[str] = None


class PromptTemplateUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    is_active: Optional[bool] = None


# ---------------------------------------------------------------------------
# Prompt version requests / responses
# ---------------------------------------------------------------------------


class PromptVersionCreate(BaseModel):
    content: str = Field(..., min_length=1)
    variables: Optional[list[str]] = Field(
        default_factory=list,
        description="Template variable names used in the content (e.g. ['customer_name', 'order_id'])",
    )
    change_notes: Optional[str] = Field(
        None, max_length=1000, description="Summary of what changed in this version"
    )


class PromptVersionResponse(BaseModel):
    id: uuid.UUID
    template_id: uuid.UUID
    version_number: int
    content: str
    variables: Optional[list[str]] = None
    change_notes: Optional[str] = None
    created_by: Optional[uuid.UUID] = None
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Prompt template responses
# ---------------------------------------------------------------------------


class PromptTemplateResponse(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    name: str
    category: Optional[str] = None
    description: Optional[str] = None
    is_active: bool
    active_version: Optional[PromptVersionResponse] = Field(
        None, description="The currently active prompt version, if any"
    )
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
