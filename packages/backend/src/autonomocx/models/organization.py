"""Organization model."""

from __future__ import annotations

import enum
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, Enum, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin

if TYPE_CHECKING:
    from .action import ActionExecution
    from .agent import AgentConfig
    from .analytics import CustomerMemory, MetricSnapshot
    from .audit import AuditLog
    from .channel import ChannelConfig
    from .conversation import Conversation
    from .knowledge import KnowledgeBase
    from .prompt import PromptTemplate
    from .tool import Tool
    from .user import User
    from .workflow import Workflow


class PlanType(enum.StrEnum):
    STARTER = "starter"
    GROWTH = "growth"
    ENTERPRISE = "enterprise"


class Organization(TimestampMixin, Base):
    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    plan: Mapped[PlanType] = mapped_column(
        Enum(PlanType, name="plan_type", native_enum=False, length=32),
        default=PlanType.STARTER,
        nullable=False,
    )
    settings: Mapped[dict[str, Any] | None] = mapped_column(JSONB, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # ------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------
    users: Mapped[list[User]] = relationship("User", back_populates="organization", lazy="selectin")
    agents: Mapped[list[AgentConfig]] = relationship(
        "AgentConfig", back_populates="organization", lazy="selectin"
    )
    conversations: Mapped[list[Conversation]] = relationship(
        "Conversation", back_populates="organization", lazy="noload"
    )
    tools: Mapped[list[Tool]] = relationship("Tool", back_populates="organization", lazy="noload")
    action_executions: Mapped[list[ActionExecution]] = relationship(
        "ActionExecution", back_populates="organization", lazy="noload"
    )
    knowledge_bases: Mapped[list[KnowledgeBase]] = relationship(
        "KnowledgeBase", back_populates="organization", lazy="noload"
    )
    workflows: Mapped[list[Workflow]] = relationship(
        "Workflow", back_populates="organization", lazy="noload"
    )
    channel_configs: Mapped[list[ChannelConfig]] = relationship(
        "ChannelConfig", back_populates="organization", lazy="noload"
    )
    prompt_templates: Mapped[list[PromptTemplate]] = relationship(
        "PromptTemplate", back_populates="organization", lazy="noload"
    )
    audit_logs: Mapped[list[AuditLog]] = relationship(
        "AuditLog", back_populates="organization", lazy="noload"
    )
    metric_snapshots: Mapped[list[MetricSnapshot]] = relationship(
        "MetricSnapshot", back_populates="organization", lazy="noload"
    )
    customer_memories: Mapped[list[CustomerMemory]] = relationship(
        "CustomerMemory", back_populates="organization", lazy="noload"
    )

    def __repr__(self) -> str:
        return f"<Organization {self.slug!r}>"
