"""Workflow & workflow-step schemas."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class TriggerType(str, enum.Enum):
    CONVERSATION_START = "conversation_start"
    KEYWORD = "keyword"
    INTENT = "intent"
    SCHEDULE = "schedule"
    WEBHOOK = "webhook"
    MANUAL = "manual"


class StepType(str, enum.Enum):
    LLM_CALL = "llm_call"
    TOOL_CALL = "tool_call"
    CONDITION = "condition"
    HUMAN_HANDOFF = "human_handoff"
    WAIT = "wait"
    TRANSFORM = "transform"


# ---------------------------------------------------------------------------
# Workflow requests
# ---------------------------------------------------------------------------


class WorkflowCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    trigger_type: TriggerType
    trigger_config: Optional[dict[str, Any]] = None


class WorkflowUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    trigger_config: Optional[dict[str, Any]] = None
    is_active: Optional[bool] = None


# ---------------------------------------------------------------------------
# Workflow step requests / responses
# ---------------------------------------------------------------------------


class WorkflowStepCreate(BaseModel):
    step_order: int = Field(..., ge=0)
    step_type: StepType
    config: dict[str, Any] = Field(
        default_factory=dict,
        description="Step-type-specific configuration",
    )
    on_success_step_id: Optional[uuid.UUID] = None
    on_failure_step_id: Optional[uuid.UUID] = None
    timeout_seconds: Optional[int] = Field(None, ge=1, le=3600)


class WorkflowStepResponse(BaseModel):
    id: uuid.UUID
    workflow_id: uuid.UUID
    step_order: int
    step_type: StepType
    config: dict[str, Any]
    on_success_step_id: Optional[uuid.UUID] = None
    on_failure_step_id: Optional[uuid.UUID] = None
    timeout_seconds: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Workflow responses
# ---------------------------------------------------------------------------


class WorkflowResponse(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    name: str
    description: Optional[str] = None
    trigger_type: TriggerType
    trigger_config: Optional[dict[str, Any]] = None
    is_active: bool
    steps: list[WorkflowStepResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
