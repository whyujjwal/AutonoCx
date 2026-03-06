"""Audit log schemas."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class ActorType(enum.StrEnum):
    USER = "user"
    AGENT = "agent"
    SYSTEM = "system"
    API_KEY = "api_key"


class AuditAction(enum.StrEnum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    LOGIN = "login"
    LOGOUT = "logout"
    APPROVE = "approve"
    REJECT = "reject"
    EXECUTE = "execute"
    ESCALATE = "escalate"


class ResourceType(enum.StrEnum):
    USER = "user"
    ORGANIZATION = "organization"
    AGENT = "agent"
    CONVERSATION = "conversation"
    MESSAGE = "message"
    TOOL = "tool"
    ACTION = "action"
    KNOWLEDGE_BASE = "knowledge_base"
    DOCUMENT = "document"
    WORKFLOW = "workflow"
    CHANNEL = "channel"
    PROMPT = "prompt"
    API_KEY = "api_key"


# ---------------------------------------------------------------------------
# Response
# ---------------------------------------------------------------------------


class AuditLogResponse(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    user_id: uuid.UUID | None = None
    actor_type: ActorType
    action: AuditAction
    resource_type: ResourceType
    resource_id: uuid.UUID | None = None
    description: str | None = None
    changes: dict[str, Any] | None = Field(
        None, description="Before/after snapshot of changed fields"
    )
    ip_address: str | None = None
    user_agent: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Filter
# ---------------------------------------------------------------------------


class AuditLogFilter(BaseModel):
    actor_type: ActorType | None = None
    action: AuditAction | None = None
    resource_type: ResourceType | None = None
    user_id: uuid.UUID | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
