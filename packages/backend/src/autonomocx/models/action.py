"""Action execution model."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin

if TYPE_CHECKING:
    from .agent import AgentConfig
    from .conversation import Conversation, Message
    from .organization import Organization
    from .tool import Tool
    from .user import User


class ActionStatus(enum.StrEnum):
    PENDING = "pending"
    AWAITING_APPROVAL = "awaiting_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ActionExecution(TimestampMixin, Base):
    __tablename__ = "action_executions"

    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    message_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("messages.id", ondelete="SET NULL"),
        nullable=True,
    )
    tool_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tools.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    agent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agents.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    status: Mapped[ActionStatus] = mapped_column(
        Enum(ActionStatus, name="action_status", native_enum=False, length=32),
        default=ActionStatus.PENDING,
        nullable=False,
        index=True,
    )
    input_params: Mapped[dict[str, Any] | None] = mapped_column(JSONB, default=dict, nullable=True)
    output_result: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    risk_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 4), nullable=True)
    risk_factors: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    requires_approval: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    approved_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    execution_time_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    idempotency_key: Mapped[str | None] = mapped_column(
        String(255), nullable=True, unique=True, index=True
    )

    # ------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------
    organization: Mapped[Organization] = relationship(
        "Organization", back_populates="action_executions"
    )
    conversation: Mapped[Conversation] = relationship(
        "Conversation", back_populates="action_executions"
    )
    message: Mapped[Message | None] = relationship("Message", back_populates="action_executions")
    tool: Mapped[Tool] = relationship("Tool", back_populates="action_executions")
    agent: Mapped[AgentConfig | None] = relationship(
        "AgentConfig", back_populates="action_executions"
    )
    approver: Mapped[User | None] = relationship(
        "User",
        back_populates="approved_actions",
        foreign_keys=[approved_by],
    )

    def __repr__(self) -> str:
        return f"<ActionExecution {self.id} status={self.status.value}>"
