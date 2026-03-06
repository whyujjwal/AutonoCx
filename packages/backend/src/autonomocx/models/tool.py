"""Tool model."""

from __future__ import annotations

import enum
import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, Enum, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin

if TYPE_CHECKING:
    from .action import ActionExecution
    from .organization import Organization


class RiskLevel(enum.StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Tool(TimestampMixin, Base):
    __tablename__ = "tools"
    __table_args__ = (
        UniqueConstraint("org_id", "name", "version", name="uq_tools_org_name_version"),
    )

    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str | None] = mapped_column(String(128), nullable=True)
    parameters_schema: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB, default=dict, nullable=True
    )
    endpoint_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    http_method: Mapped[str | None] = mapped_column(String(10), nullable=True)
    headers_template: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB, default=dict, nullable=True
    )
    auth_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    auth_config: Mapped[dict[str, Any] | None] = mapped_column(JSONB, default=dict, nullable=True)
    timeout_seconds: Mapped[int | None] = mapped_column(Integer, default=30, nullable=True)
    retry_config: Mapped[dict[str, Any] | None] = mapped_column(JSONB, default=dict, nullable=True)
    risk_level: Mapped[RiskLevel] = mapped_column(
        Enum(RiskLevel, name="risk_level", native_enum=False, length=16),
        default=RiskLevel.LOW,
        nullable=False,
    )
    requires_approval: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_builtin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    version: Mapped[str] = mapped_column(String(32), default="1.0.0", nullable=False)

    # ------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------
    organization: Mapped[Organization] = relationship("Organization", back_populates="tools")
    action_executions: Mapped[list[ActionExecution]] = relationship(
        "ActionExecution", back_populates="tool", lazy="noload"
    )

    def __repr__(self) -> str:
        return f"<Tool {self.name!r} v{self.version}>"
