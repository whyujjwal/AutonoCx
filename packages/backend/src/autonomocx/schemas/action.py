"""Action execution schemas."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class ActionStatus(enum.StrEnum):
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
    message_id: uuid.UUID | None = None
    agent_id: uuid.UUID
    tool_id: uuid.UUID
    tool_name: str
    parameters: dict[str, Any] | None = None
    result: dict[str, Any] | None = None
    status: ActionStatus
    error_message: str | None = None
    execution_time_ms: float | None = None
    requires_approval: bool
    approved_by: uuid.UUID | None = None
    approved_at: datetime | None = None
    rejection_reason: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Requests
# ---------------------------------------------------------------------------


class ActionApproveRequest(BaseModel):
    notes: str | None = Field(None, max_length=1000, description="Optional approval notes")


class ActionRejectRequest(BaseModel):
    reason: str = Field(..., min_length=1, max_length=1000, description="Reason for rejection")


# ---------------------------------------------------------------------------
# Filters & statistics
# ---------------------------------------------------------------------------


class ActionFilter(BaseModel):
    status: ActionStatus | None = None
    tool_id: uuid.UUID | None = None
    conversation_id: uuid.UUID | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None


class ActionStats(BaseModel):
    total: int
    completed: int
    failed: int
    pending_approval: int
    avg_execution_time_ms: float | None = Field(
        None, description="Average execution time across completed actions"
    )
