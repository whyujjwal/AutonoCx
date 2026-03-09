"""Pydantic schemas for connector endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Requests
# ---------------------------------------------------------------------------


class ConnectorConfigureRequest(BaseModel):
    """Request body for configuring a connector."""

    config: dict[str, Any] = Field(..., description="Connector credentials and settings")
    display_name: str | None = Field(None, max_length=255)


# ---------------------------------------------------------------------------
# Responses
# ---------------------------------------------------------------------------


class ConnectorOut(BaseModel):
    """Connector configuration response."""

    id: UUID
    org_id: UUID
    connector_type: str
    display_name: str | None = None
    is_active: bool
    status: str
    last_health_check_at: datetime | None = None
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ConnectorHealthResponse(BaseModel):
    """Health check response."""

    connector_type: str
    status: str
    error: str | None = None


class ConnectorAvailableOut(BaseModel):
    """Available connector type info."""

    connector_type: str
    display_name: str


class ConnectorOperationOut(BaseModel):
    """Connector operation info."""

    name: str
    display_name: str
    description: str
    parameters_schema: dict[str, Any]
    risk_level: str
    requires_approval: bool
