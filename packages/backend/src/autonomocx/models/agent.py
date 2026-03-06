"""Agent configuration model."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin

if TYPE_CHECKING:
    from .action import ActionExecution
    from .channel import ChannelConfig
    from .conversation import Conversation
    from .organization import Organization


class AgentConfig(TimestampMixin, Base):
    __tablename__ = "agents"

    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    system_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    llm_provider: Mapped[str | None] = mapped_column(String(64), nullable=True)
    llm_model: Mapped[str | None] = mapped_column(String(128), nullable=True)
    temperature: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tools_enabled: Mapped[list[uuid.UUID] | None] = mapped_column(
        ARRAY(UUID(as_uuid=True)), default=list, nullable=True
    )
    fallback_agent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agents.id", ondelete="SET NULL"),
        nullable=True,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    metadata_: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata", JSONB, default=dict, nullable=True
    )

    # ------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------
    organization: Mapped[Organization] = relationship("Organization", back_populates="agents")
    fallback_agent: Mapped[AgentConfig | None] = relationship(
        "AgentConfig", remote_side="AgentConfig.id", lazy="selectin"
    )
    conversations: Mapped[list[Conversation]] = relationship(
        "Conversation", back_populates="agent", lazy="noload"
    )
    action_executions: Mapped[list[ActionExecution]] = relationship(
        "ActionExecution", back_populates="agent", lazy="noload"
    )
    channel_configs: Mapped[list[ChannelConfig]] = relationship(
        "ChannelConfig", back_populates="agent", lazy="noload"
    )

    def __repr__(self) -> str:
        return f"<AgentConfig {self.name!r}>"
