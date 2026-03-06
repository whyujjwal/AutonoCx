"""Prompt template & version schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# Prompt template requests
# ---------------------------------------------------------------------------


class PromptTemplateCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    category: str | None = Field(None, max_length=128)
    description: str | None = None


class PromptTemplateUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    is_active: bool | None = None


# ---------------------------------------------------------------------------
# Prompt version requests / responses
# ---------------------------------------------------------------------------


class PromptVersionCreate(BaseModel):
    content: str = Field(..., min_length=1)
    variables: list[str] | None = Field(
        default_factory=list,
        description=(
            "Template variable names used in the content (e.g. ['customer_name', 'order_id'])"
        ),
    )
    change_notes: str | None = Field(
        None, max_length=1000, description="Summary of what changed in this version"
    )


class PromptVersionResponse(BaseModel):
    id: uuid.UUID
    template_id: uuid.UUID
    version_number: int
    content: str
    variables: list[str] | None = None
    change_notes: str | None = None
    created_by: uuid.UUID | None = None
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
    category: str | None = None
    description: str | None = None
    is_active: bool
    active_version: PromptVersionResponse | None = Field(
        None, description="The currently active prompt version, if any"
    )
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
