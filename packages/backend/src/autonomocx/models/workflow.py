"""Workflow and workflow-step models."""

from __future__ import annotations

import enum
import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin

if TYPE_CHECKING:
    from .organization import Organization


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class TriggerType(enum.StrEnum):
    INTENT = "intent"
    KEYWORD = "keyword"
    MANUAL = "manual"
    SCHEDULED = "scheduled"


class StepType(enum.StrEnum):
    CONDITION = "condition"
    TOOL_CALL = "tool_call"
    LLM_PROMPT = "llm_prompt"
    HUMAN_HANDOFF = "human_handoff"
    WAIT = "wait"
    BRANCH = "branch"
    LOOP = "loop"


# ---------------------------------------------------------------------------
# Workflow
# ---------------------------------------------------------------------------


class Workflow(TimestampMixin, Base):
    __tablename__ = "workflows"

    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    trigger_type: Mapped[TriggerType] = mapped_column(
        Enum(TriggerType, name="trigger_type", native_enum=False, length=16),
        nullable=False,
    )
    trigger_config: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB, default=dict, nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    # ------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------
    organization: Mapped[Organization] = relationship("Organization", back_populates="workflows")
    steps: Mapped[list[WorkflowStep]] = relationship(
        "WorkflowStep",
        back_populates="workflow",
        order_by="WorkflowStep.step_order",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Workflow {self.name!r} v{self.version}>"


# ---------------------------------------------------------------------------
# WorkflowStep
# ---------------------------------------------------------------------------


class WorkflowStep(TimestampMixin, Base):
    __tablename__ = "workflow_steps"

    workflow_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workflows.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    step_order: Mapped[int] = mapped_column(Integer, nullable=False)
    step_type: Mapped[StepType] = mapped_column(
        Enum(StepType, name="step_type", native_enum=False, length=32),
        nullable=False,
    )
    config: Mapped[dict[str, Any] | None] = mapped_column(JSONB, default=dict, nullable=True)
    on_success_step_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workflow_steps.id", ondelete="SET NULL"),
        nullable=True,
    )
    on_failure_step_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workflow_steps.id", ondelete="SET NULL"),
        nullable=True,
    )
    timeout_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # ------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------
    workflow: Mapped[Workflow] = relationship("Workflow", back_populates="steps")
    on_success_step: Mapped[WorkflowStep | None] = relationship(
        "WorkflowStep",
        remote_side="WorkflowStep.id",
        foreign_keys=[on_success_step_id],
        lazy="selectin",
    )
    on_failure_step: Mapped[WorkflowStep | None] = relationship(
        "WorkflowStep",
        remote_side="WorkflowStep.id",
        foreign_keys=[on_failure_step_id],
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<WorkflowStep order={self.step_order} type={self.step_type.value}>"
