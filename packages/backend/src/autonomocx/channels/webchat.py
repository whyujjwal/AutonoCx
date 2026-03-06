"""WebSocket-based web chat adapter.

Handles real-time bidirectional messaging for the embedded web widget.
Messages are sent and received over WebSocket connections managed by
the FastAPI WebSocket endpoint.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

import structlog
from fastapi import WebSocket

from .base import ChannelAdapter, InboundMessage, OutboundMessage

logger = structlog.get_logger(__name__)


class WebChatAdapter(ChannelAdapter):
    """Adapter for the AutonoCX embedded web chat widget.

    Unlike HTTP-based channels, the web chat adapter holds a reference
    to the active WebSocket connection per session and sends/receives
    messages through it directly.
    """

    channel_name = "webchat"

    def __init__(self) -> None:
        # session_id -> WebSocket mapping (managed externally by the WS endpoint)
        self._connections: dict[str, WebSocket] = {}

    # ── Connection management ─────────────────────────────────────

    def register_connection(self, session_id: str, websocket: WebSocket) -> None:
        """Register an active WebSocket connection for a session."""
        self._connections[session_id] = websocket
        logger.info("webchat_connection_registered", session_id=session_id)

    def unregister_connection(self, session_id: str) -> None:
        """Remove a WebSocket connection when the session ends."""
        self._connections.pop(session_id, None)
        logger.info("webchat_connection_unregistered", session_id=session_id)

    def get_connection(self, session_id: str) -> WebSocket | None:
        """Return the WebSocket for *session_id*, or ``None``."""
        return self._connections.get(session_id)

    # ── ChannelAdapter interface ──────────────────────────────────

    async def send_message(self, message: OutboundMessage) -> dict[str, Any]:
        """Send a message to the user over their active WebSocket."""
        ws = self.get_connection(message.recipient_id)
        if ws is None:
            logger.warning(
                "webchat_send_no_connection",
                recipient_id=message.recipient_id,
            )
            return {"message_id": None, "status": "no_connection"}

        payload = self.format_outgoing(message)
        await ws.send_json(payload)

        message_id = str(uuid.uuid4())
        logger.info(
            "webchat_message_sent",
            message_id=message_id,
            recipient_id=message.recipient_id,
        )
        return {"message_id": message_id, "status": "sent"}

    async def receive_message(self, raw_payload: dict[str, Any]) -> InboundMessage:
        """Parse an incoming WebSocket JSON frame into an ``InboundMessage``."""
        return self.parse_incoming(raw_payload)

    def format_outgoing(self, message: OutboundMessage) -> dict[str, Any]:
        """Convert an ``OutboundMessage`` to the JSON structure the widget expects."""
        return {
            "type": "message",
            "content": message.content,
            "content_type": message.content_type,
            "attachments": message.attachments,
            "conversation_id": str(message.conversation_id) if message.conversation_id else None,
            "timestamp": datetime.now(UTC).isoformat(),
            "metadata": message.metadata,
        }

    def parse_incoming(self, raw_payload: dict[str, Any]) -> InboundMessage:
        """Convert a raw WebSocket JSON frame into an ``InboundMessage``."""
        return InboundMessage(
            channel=self.channel_name,
            channel_message_id=raw_payload.get("message_id", str(uuid.uuid4())),
            sender_id=raw_payload.get("session_id", "anonymous"),
            content=raw_payload.get("content", ""),
            content_type=raw_payload.get("content_type", "text"),
            attachments=raw_payload.get("attachments", []),
            metadata=raw_payload.get("metadata", {}),
            conversation_id=(
                uuid.UUID(raw_payload["conversation_id"])
                if raw_payload.get("conversation_id")
                else None
            ),
        )
