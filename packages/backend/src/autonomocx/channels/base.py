"""Abstract base class for all channel adapters.

Every channel adapter must implement the four core methods defined here.
The ``InboundMessage`` and ``OutboundMessage`` dataclasses serve as a
channel-agnostic message envelope so the orchestration engine does not
need to know which channel produced or will consume a message.
"""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, UTC
from enum import Enum
from typing import Any


class MessageDirection(str, Enum):
    INBOUND = "inbound"
    OUTBOUND = "outbound"


@dataclass
class InboundMessage:
    """Normalised representation of a message received from an end user."""

    channel: str
    channel_message_id: str
    sender_id: str
    content: str
    content_type: str = "text"
    attachments: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    conversation_id: uuid.UUID | None = None
    org_id: uuid.UUID | None = None


@dataclass
class OutboundMessage:
    """Normalised representation of a message to be sent to an end user."""

    channel: str
    recipient_id: str
    content: str
    content_type: str = "text"
    attachments: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    conversation_id: uuid.UUID | None = None
    reply_to_message_id: str | None = None


class ChannelAdapter(ABC):
    """Abstract base class for channel adapters.

    Subclasses implement the four lifecycle methods:

    - ``send_message``     -- deliver a message to the channel
    - ``receive_message``  -- accept a raw payload and produce an InboundMessage
    - ``format_outgoing``  -- convert an OutboundMessage into channel-native format
    - ``parse_incoming``   -- convert a raw channel payload into an InboundMessage
    """

    channel_name: str = "base"

    @abstractmethod
    async def send_message(self, message: OutboundMessage) -> dict[str, Any]:
        """Send *message* through the channel.

        Returns a dict with at least ``{"message_id": "<channel-specific-id>"}``
        on success, or raises on failure.
        """
        ...

    @abstractmethod
    async def receive_message(self, raw_payload: dict[str, Any]) -> InboundMessage:
        """Accept a raw webhook / WebSocket payload and return an ``InboundMessage``.

        This is a convenience wrapper around ``parse_incoming`` that may also
        perform signature verification or other channel-specific validation.
        """
        ...

    @abstractmethod
    def format_outgoing(self, message: OutboundMessage) -> dict[str, Any]:
        """Convert an ``OutboundMessage`` into the channel's native payload format.

        This is a pure transformation; it does **not** perform I/O.
        """
        ...

    @abstractmethod
    def parse_incoming(self, raw_payload: dict[str, Any]) -> InboundMessage:
        """Convert a raw channel payload into an ``InboundMessage``.

        This is a pure transformation; it does **not** perform I/O.
        """
        ...
