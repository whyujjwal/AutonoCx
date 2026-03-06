"""Organization & API-key schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from autonomocx.models.organization import PlanType

# ---------------------------------------------------------------------------
# Organization requests / responses
# ---------------------------------------------------------------------------


class OrgUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    settings: dict[str, Any] | None = None


class OrgResponse(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    plan: PlanType
    settings: dict[str, Any] | None = None
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# API Key requests / responses
# ---------------------------------------------------------------------------


class ApiKeyCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    scopes: list[str] = Field(
        default_factory=list,
        description="List of permission scopes (e.g. ['conversations:read', 'agents:write'])",
    )
    expires_at: datetime | None = Field(
        None, description="Optional expiration timestamp; null means never expires"
    )


class ApiKeyResponse(BaseModel):
    id: uuid.UUID
    key_prefix: str = Field(..., description="First 8 characters of the key for identification")
    name: str
    scopes: list[str]
    expires_at: datetime | None = None
    last_used_at: datetime | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ApiKeyCreatedResponse(ApiKeyResponse):
    """Returned once on creation -- the only time the raw key is visible."""

    raw_key: str = Field(..., description="Full API key; shown only at creation time")
