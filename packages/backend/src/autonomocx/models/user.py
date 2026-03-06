"""User model."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin

if TYPE_CHECKING:
    from .action import ActionExecution
    from .audit import AuditLog
    from .conversation import Conversation
    from .organization import Organization
    from .prompt import PromptVersion


class UserRole(enum.StrEnum):
    ADMIN = "admin"
    SUPERVISOR = "supervisor"
    AGENT_REVIEWER = "agent_reviewer"
    DEVELOPER = "developer"
    VIEWER = "viewer"


class User(TimestampMixin, Base):
    __tablename__ = "users"

    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(512), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role", native_enum=False, length=32),
        default=UserRole.VIEWER,
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # ------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------
    organization: Mapped[Organization] = relationship("Organization", back_populates="users")
    assigned_conversations: Mapped[list[Conversation]] = relationship(
        "Conversation",
        back_populates="assigned_user",
        foreign_keys="Conversation.assigned_to",
        lazy="noload",
    )
    approved_actions: Mapped[list[ActionExecution]] = relationship(
        "ActionExecution",
        back_populates="approver",
        foreign_keys="ActionExecution.approved_by",
        lazy="noload",
    )
    audit_logs: Mapped[list[AuditLog]] = relationship(
        "AuditLog", back_populates="user", lazy="noload"
    )
    prompt_versions: Mapped[list[PromptVersion]] = relationship(
        "PromptVersion", back_populates="creator", lazy="noload"
    )

    def __repr__(self) -> str:
        return f"<User {self.email!r}>"
