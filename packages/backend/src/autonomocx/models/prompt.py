"""Prompt template and version models."""

from __future__ import annotations

import enum
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin

if TYPE_CHECKING:
    from .organization import Organization
    from .user import User


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class PromptCategory(enum.StrEnum):
    SYSTEM = "system"
    INTENT = "intent"
    TOOL = "tool"
    GUARD = "guard"
    GREETING = "greeting"


# ---------------------------------------------------------------------------
# PromptTemplate
# ---------------------------------------------------------------------------


class PromptTemplate(TimestampMixin, Base):
    __tablename__ = "prompt_templates"

    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[PromptCategory] = mapped_column(
        Enum(PromptCategory, name="prompt_category", native_enum=False, length=16),
        nullable=False,
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    active_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("prompt_versions.id", ondelete="SET NULL", use_alter=True),
        nullable=True,
    )

    # ------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------
    organization: Mapped[Organization] = relationship(
        "Organization", back_populates="prompt_templates"
    )
    versions: Mapped[list[PromptVersion]] = relationship(
        "PromptVersion",
        back_populates="template",
        foreign_keys="PromptVersion.template_id",
        order_by="PromptVersion.version_number",
        lazy="selectin",
    )
    active_version: Mapped[PromptVersion | None] = relationship(
        "PromptVersion",
        foreign_keys=[active_version_id],
        post_update=True,
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<PromptTemplate {self.name!r}>"


# ---------------------------------------------------------------------------
# PromptVersion
# ---------------------------------------------------------------------------


class PromptVersion(TimestampMixin, Base):
    __tablename__ = "prompt_versions"
    __table_args__ = (
        UniqueConstraint(
            "template_id",
            "version_number",
            name="uq_prompt_versions_template_version",
        ),
    )

    template_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("prompt_templates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    variables: Mapped[list[str] | None] = mapped_column(ARRAY(String), default=list, nullable=True)
    change_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    performance_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_published: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # ------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------
    template: Mapped[PromptTemplate] = relationship(
        "PromptTemplate",
        back_populates="versions",
        foreign_keys=[template_id],
    )
    creator: Mapped[User | None] = relationship("User", back_populates="prompt_versions")

    def __repr__(self) -> str:
        return f"<PromptVersion template={self.template_id} v{self.version_number}>"
