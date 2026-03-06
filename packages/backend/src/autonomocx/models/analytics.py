"""Analytics models: MetricSnapshot and CustomerMemory."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin

if TYPE_CHECKING:
    from .organization import Organization


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class MetricPeriod(enum.StrEnum):
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class MemoryType(enum.StrEnum):
    PREFERENCE = "preference"
    FACT = "fact"
    INTERACTION_SUMMARY = "interaction_summary"


# ---------------------------------------------------------------------------
# MetricSnapshot
# ---------------------------------------------------------------------------


class MetricSnapshot(TimestampMixin, Base):
    __tablename__ = "metric_snapshots"
    __table_args__ = (
        UniqueConstraint(
            "org_id",
            "period",
            "period_start",
            name="uq_metric_snapshots_org_period_start",
        ),
    )

    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    period: Mapped[MetricPeriod] = mapped_column(
        Enum(MetricPeriod, name="metric_period", native_enum=False, length=16),
        nullable=False,
    )
    period_start: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    metrics: Mapped[dict[str, Any] | None] = mapped_column(JSONB, default=dict, nullable=True)

    # ------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------
    organization: Mapped[Organization] = relationship(
        "Organization", back_populates="metric_snapshots"
    )

    def __repr__(self) -> str:
        return f"<MetricSnapshot {self.period.value} start={self.period_start}>"


# ---------------------------------------------------------------------------
# CustomerMemory
# ---------------------------------------------------------------------------


class CustomerMemory(TimestampMixin, Base):
    __tablename__ = "customer_memories"

    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    customer_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    memory_type: Mapped[MemoryType] = mapped_column(
        Enum(MemoryType, name="memory_type", native_enum=False, length=32),
        nullable=False,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str | None] = mapped_column(String(255), nullable=True)
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(5, 4), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # ------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------
    organization: Mapped[Organization] = relationship(
        "Organization", back_populates="customer_memories"
    )

    def __repr__(self) -> str:
        return f"<CustomerMemory customer={self.customer_id!r} type={self.memory_type.value}>"
