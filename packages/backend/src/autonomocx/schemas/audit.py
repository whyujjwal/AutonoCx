"""Audit log schemas."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class ActorType(str, enum.Enum):
    USER = "user"
    AGENT = "agent"
    SYSTEM = "system"
    API_KEY = "api_key"


class AuditAction(str, enum.Enum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    LOGIN = "login"
    LOGOUT = "logout"
    APPROVE = "approve"
    REJECT = "reject"
    EXECUTE = "execute"
    ESCALATE = "escalate"


class ResourceType(str, enum.Enum):
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
    user_id: Optional[uuid.UUID] = None
    actor_type: ActorType
    action: AuditAction
    resource_type: ResourceType
    resource_id: Optional[uuid.UUID] = None
    description: Optional[str] = None
    changes: Optional[dict[str, Any]] = Field(
        None, description="Before/after snapshot of changed fields"
    )
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Filter
# ---------------------------------------------------------------------------


class AuditLogFilter(BaseModel):
    actor_type: Optional[ActorType] = None
    action: Optional[AuditAction] = None
    resource_type: Optional[ResourceType] = None
    user_id: Optional[uuid.UUID] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
