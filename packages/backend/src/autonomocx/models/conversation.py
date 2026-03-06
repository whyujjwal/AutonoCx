"""Conversation and Message models."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, List, Optional

from sqlalchemy import (
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin

if TYPE_CHECKING:
    from .action import ActionExecution
    from .agent import AgentConfig
    from .organization import Organization
    from .user import User


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class ChannelType(str, enum.Enum):
    WEBCHAT = "webchat"
    WHATSAPP = "whatsapp"
    EMAIL = "email"
    VOICE = "voice"
    SMS = "sms"


class ConversationStatus(str, enum.Enum):
    ACTIVE = "active"
    WAITING_HUMAN = "waiting_human"
    ESCALATED = "escalated"
    RESOLVED = "resolved"
    CLOSED = "closed"


class Priority(str, enum.Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class MessageRole(str, enum.Enum):
    CUSTOMER = "customer"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


class ContentType(str, enum.Enum):
    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"
    FILE = "file"
    ACTION_CARD = "action_card"


# ---------------------------------------------------------------------------
# Conversation
# ---------------------------------------------------------------------------


class Conversation(TimestampMixin, Base):
    __tablename__ = "conversations"

    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    agent_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agents.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    channel: Mapped[ChannelType] = mapped_column(
        Enum(ChannelType, name="channel_type_enum", native_enum=False, length=32),
        nullable=False,
    )
    channel_id: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    customer_id: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, index=True
    )
    customer_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    customer_email: Mapped[Optional[str]] = mapped_column(String(320), nullable=True)
    customer_phone: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    status: Mapped[ConversationStatus] = mapped_column(
        Enum(ConversationStatus, name="conversation_status", native_enum=False, length=32),
        default=ConversationStatus.ACTIVE,
        nullable=False,
        index=True,
    )
    priority: Mapped[Priority] = mapped_column(
        Enum(Priority, name="priority_level", native_enum=False, length=16),
        default=Priority.NORMAL,
        nullable=False,
    )
    sentiment: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    intent: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    assigned_to: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    resolved_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    resolution_time_seconds: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True
    )
    satisfaction_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    metadata_: Mapped[Optional[dict[str, Any]]] = mapped_column(
        "metadata", JSONB, default=dict, nullable=True
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # ------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------
    organization: Mapped["Organization"] = relationship(
        "Organization", back_populates="conversations"
    )
    agent: Mapped[Optional["AgentConfig"]] = relationship(
        "AgentConfig", back_populates="conversations"
    )
    assigned_user: Mapped[Optional["User"]] = relationship(
        "User",
        back_populates="assigned_conversations",
        foreign_keys=[assigned_to],
    )
    messages: Mapped[List["Message"]] = relationship(
        "Message",
        back_populates="conversation",
        order_by="Message.created_at",
        lazy="selectin",
    )
    action_executions: Mapped[List["ActionExecution"]] = relationship(
        "ActionExecution", back_populates="conversation", lazy="noload"
    )

    def __repr__(self) -> str:
        return f"<Conversation {self.id} status={self.status.value}>"


# ---------------------------------------------------------------------------
# Message
# ---------------------------------------------------------------------------


class Message(TimestampMixin, Base):
    __tablename__ = "messages"

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[MessageRole] = mapped_column(
        Enum(MessageRole, name="message_role", native_enum=False, length=16),
        nullable=False,
    )
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    content_type: Mapped[ContentType] = mapped_column(
        Enum(ContentType, name="content_type_enum", native_enum=False, length=32),
        default=ContentType.TEXT,
        nullable=False,
    )
    metadata_: Mapped[Optional[dict[str, Any]]] = mapped_column(
        "metadata", JSONB, default=dict, nullable=True
    )
    tool_call_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    tool_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    prompt_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    completion_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    llm_model_used: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    latency_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # ------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------
    conversation: Mapped["Conversation"] = relationship(
        "Conversation", back_populates="messages"
    )
    action_executions: Mapped[List["ActionExecution"]] = relationship(
        "ActionExecution", back_populates="message", lazy="noload"
    )

    def __repr__(self) -> str:
        return f"<Message {self.id} role={self.role.value}>"
