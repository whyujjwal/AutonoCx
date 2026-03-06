"""Tool schemas."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Enums shared with tool models
# ---------------------------------------------------------------------------


class HttpMethod(str, enum.Enum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"


class AuthType(str, enum.Enum):
    NONE = "none"
    API_KEY = "api_key"
    BEARER_TOKEN = "bearer_token"
    BASIC = "basic"
    OAUTH2 = "oauth2"


class RiskLevel(str, enum.Enum):
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
    description: Optional[str] = None
    category: Optional[str] = Field(None, max_length=128)
    parameters_schema: Optional[dict[str, Any]] = Field(
        None, description="JSON Schema describing the tool's input parameters"
    )
    endpoint_url: str = Field(..., description="URL the tool calls at execution time")
    http_method: HttpMethod = Field(default=HttpMethod.POST)
    headers_template: Optional[dict[str, str]] = Field(
        None, description="Header key-value pairs (may contain {{variable}} placeholders)"
    )
    auth_type: AuthType = Field(default=AuthType.NONE)
    auth_config: Optional[dict[str, Any]] = Field(
        None, description="Auth-type-specific configuration"
    )
    timeout_seconds: int = Field(default=30, ge=1, le=300)
    retry_config: Optional[dict[str, Any]] = Field(
        None,
        description="Retry policy, e.g. {'max_retries': 3, 'backoff_factor': 2}",
    )
    risk_level: RiskLevel = Field(default=RiskLevel.LOW)
    requires_approval: bool = Field(
        default=False,
        description="If true, execution must be approved by a human before running",
    )


class ToolUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    display_name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    category: Optional[str] = Field(None, max_length=128)
    parameters_schema: Optional[dict[str, Any]] = None
    endpoint_url: Optional[str] = None
    http_method: Optional[HttpMethod] = None
    headers_template: Optional[dict[str, str]] = None
    auth_type: Optional[AuthType] = None
    auth_config: Optional[dict[str, Any]] = None
    timeout_seconds: Optional[int] = Field(None, ge=1, le=300)
    retry_config: Optional[dict[str, Any]] = None
    risk_level: Optional[RiskLevel] = None
    requires_approval: Optional[bool] = None


# ---------------------------------------------------------------------------
# Responses
# ---------------------------------------------------------------------------


class ToolResponse(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    name: str
    display_name: str
    description: Optional[str] = None
    category: Optional[str] = None
    parameters_schema: Optional[dict[str, Any]] = None
    endpoint_url: str
    http_method: HttpMethod
    headers_template: Optional[dict[str, str]] = None
    auth_type: AuthType
    auth_config: Optional[dict[str, Any]] = None
    timeout_seconds: int
    retry_config: Optional[dict[str, Any]] = None
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
    result: Optional[Any] = None
    execution_time_ms: float = Field(
        ..., description="Wall-clock execution time in milliseconds"
    )
