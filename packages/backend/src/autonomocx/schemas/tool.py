"""Tool schemas."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# Enums shared with tool models
# ---------------------------------------------------------------------------


class HttpMethod(enum.StrEnum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"


class AuthType(enum.StrEnum):
    NONE = "none"
    API_KEY = "api_key"
    BEARER_TOKEN = "bearer_token"
    BASIC = "basic"
    OAUTH2 = "oauth2"


class RiskLevel(enum.StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# ---------------------------------------------------------------------------
# Requests
# ---------------------------------------------------------------------------


class ToolCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    display_name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    category: str | None = Field(None, max_length=128)
    parameters_schema: dict[str, Any] | None = Field(
        None, description="JSON Schema describing the tool's input parameters"
    )
    endpoint_url: str = Field(..., description="URL the tool calls at execution time")
    http_method: HttpMethod = Field(default=HttpMethod.POST)
    headers_template: dict[str, str] | None = Field(
        None, description="Header key-value pairs (may contain {{variable}} placeholders)"
    )
    auth_type: AuthType = Field(default=AuthType.NONE)
    auth_config: dict[str, Any] | None = Field(None, description="Auth-type-specific configuration")
    timeout_seconds: int = Field(default=30, ge=1, le=300)
    retry_config: dict[str, Any] | None = Field(
        None,
        description="Retry policy, e.g. {'max_retries': 3, 'backoff_factor': 2}",
    )
    risk_level: RiskLevel = Field(default=RiskLevel.LOW)
    requires_approval: bool = Field(
        default=False,
        description="If true, execution must be approved by a human before running",
    )


class ToolUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    display_name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    category: str | None = Field(None, max_length=128)
    parameters_schema: dict[str, Any] | None = None
    endpoint_url: str | None = None
    http_method: HttpMethod | None = None
    headers_template: dict[str, str] | None = None
    auth_type: AuthType | None = None
    auth_config: dict[str, Any] | None = None
    timeout_seconds: int | None = Field(None, ge=1, le=300)
    retry_config: dict[str, Any] | None = None
    risk_level: RiskLevel | None = None
    requires_approval: bool | None = None


# ---------------------------------------------------------------------------
# Responses
# ---------------------------------------------------------------------------


class ToolResponse(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    name: str
    display_name: str
    description: str | None = None
    category: str | None = None
    parameters_schema: dict[str, Any] | None = None
    endpoint_url: str
    http_method: HttpMethod
    headers_template: dict[str, str] | None = None
    auth_type: AuthType
    auth_config: dict[str, Any] | None = None
    timeout_seconds: int
    retry_config: dict[str, Any] | None = None
    risk_level: RiskLevel
    requires_approval: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Tool testing
# ---------------------------------------------------------------------------


class ToolTestRequest(BaseModel):
    parameters: dict[str, Any] = Field(
        default_factory=dict,
        description="Parameters to pass to the tool for a test invocation",
    )


class ToolTestResponse(BaseModel):
    success: bool
    result: Any | None = None
    execution_time_ms: float = Field(..., description="Wall-clock execution time in milliseconds")
