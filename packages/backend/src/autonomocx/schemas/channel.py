"""Channel configuration schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field

from autonomocx.models.conversation import ChannelType


# ---------------------------------------------------------------------------
# Requests
# ---------------------------------------------------------------------------


class ChannelConfigCreate(BaseModel):
    channel_type: ChannelType
    display_name: str = Field(..., min_length=1, max_length=255)
    agent_id: Optional[uuid.UUID] = None
    config: Optional[dict[str, Any]] = Field(
        None,
        description="Channel-specific configuration (API keys, webhook URLs, etc.)",
    )


class ChannelConfigUpdate(BaseModel):
    display_name: Optional[str] = Field(None, min_length=1, max_length=255)
    agent_id: Optional[uuid.UUID] = None
    config: Optional[dict[str, Any]] = None
    is_active: Optional[bool] = None


# ---------------------------------------------------------------------------
# Responses
# ---------------------------------------------------------------------------


class ChannelConfigResponse(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    channel_type: ChannelType
    display_name: str
    agent_id: Optional[uuid.UUID] = None
    config: Optional[dict[str, Any]] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ChannelTestResponse(BaseModel):
    success: bool
    message: str = Field(..., description="Human-readable result or error detail")
    latency_ms: Optional[float] = Field(
        None, description="Round-trip time in milliseconds (null on failure)"
    )
