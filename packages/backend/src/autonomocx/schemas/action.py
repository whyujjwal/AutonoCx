"""Action execution schemas."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class ActionStatus(str, enum.Enum):
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"


# ---------------------------------------------------------------------------
# Responses
# ---------------------------------------------------------------------------


class ActionResponse(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    conversation_id: uuid.UUID
    message_id: Optional[uuid.UUID] = None
    agent_id: uuid.UUID
    tool_id: uuid.UUID
    tool_name: str
    parameters: Optional[dict[str, Any]] = None
    result: Optional[dict[str, Any]] = None
    status: ActionStatus
    error_message: Optional[str] = None
    execution_time_ms: Optional[float] = None
    requires_approval: bool
    approved_by: Optional[uuid.UUID] = None
    approved_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Requests
# ---------------------------------------------------------------------------


class ActionApproveRequest(BaseModel):
    notes: Optional[str] = Field(
        None, max_length=1000, description="Optional approval notes"
    )


class ActionRejectRequest(BaseModel):
    reason: str = Field(
        ..., min_length=1, max_length=1000, description="Reason for rejection"
    )


# ---------------------------------------------------------------------------
# Filters & statistics
# ---------------------------------------------------------------------------


class ActionFilter(BaseModel):
    status: Optional[ActionStatus] = None
    tool_id: Optional[uuid.UUID] = None
    conversation_id: Optional[uuid.UUID] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None


class ActionStats(BaseModel):
    total: int
    completed: int
    failed: int
    pending_approval: int
    avg_execution_time_ms: Optional[float] = Field(
        None, description="Average execution time across completed actions"
    )
