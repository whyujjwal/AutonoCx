"""Channel configuration model."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin

if TYPE_CHECKING:
    from .agent import AgentConfig
    from .organization import Organization


class ChannelConfig(TimestampMixin, Base):
    __tablename__ = "channel_configs"
    __table_args__ = (
        UniqueConstraint(
            "org_id",
            "channel_type",
            "display_name",
            name="uq_channel_configs_org_type_name",
        ),
    )

    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    channel_type: Mapped[str] = mapped_column(String(32), nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    agent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agents.id", ondelete="SET NULL"),
        nullable=True,
    )
    config: Mapped[dict[str, Any] | None] = mapped_column(JSONB, default=dict, nullable=True)
    webhook_secret: Mapped[str | None] = mapped_column(String(512), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # ------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------
    organization: Mapped[Organization] = relationship(
        "Organization", back_populates="channel_configs"
    )
    agent: Mapped[AgentConfig | None] = relationship(
        "AgentConfig", back_populates="channel_configs"
    )

    def __repr__(self) -> str:
        return f"<ChannelConfig {self.channel_type}:{self.display_name!r}>"
