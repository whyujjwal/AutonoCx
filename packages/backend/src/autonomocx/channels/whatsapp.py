"""WhatsApp Business API adapter.

Sends messages via the WhatsApp Cloud API (HTTP POST) and receives
incoming messages through the configured webhook endpoint.
"""

from __future__ import annotations

import uuid
from datetime import datetime, UTC
from typing import Any

import httpx
import structlog

from autonomocx.core.config import get_settings
from .base import ChannelAdapter, InboundMessage, OutboundMessage

logger = structlog.get_logger(__name__)

WHATSAPP_API_BASE = "https://graph.facebook.com/v18.0"


class WhatsAppAdapter(ChannelAdapter):
    """Adapter for the WhatsApp Business Cloud API."""

    channel_name = "whatsapp"

    def __init__(self) -> None:
        self._settings = get_settings()
        self._http_client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Lazy-initialise and return a shared HTTP client."""
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(
                base_url=WHATSAPP_API_BASE,
                timeout=30.0,
                headers={
                    "Authorization": f"Bearer {self._settings.twilio_auth_token.get_secret_value() if self._settings.twilio_auth_token else ''}",
                    "Content-Type": "application/json",
                },
            )
        return self._http_client

    # ── ChannelAdapter interface ──────────────────────────────────

    async def send_message(self, message: OutboundMessage) -> dict[str, Any]:
        """Send a text message via the WhatsApp Cloud API."""
        client = await self._get_client()
        phone_number_id = self._settings.whatsapp_phone_number
        payload = self.format_outgoing(message)

        response = await client.post(
            f"/{phone_number_id}/messages",
            json=payload,
        )

        if response.status_code != 200:
            logger.error(
                "whatsapp_send_failed",
                status=response.status_code,
                body=response.text,
                recipient=message.recipient_id,
            )
            return {"message_id": None, "status": "failed", "error": response.text}

        data = response.json()
        wa_message_id = data.get("messages", [{}])[0].get("id", "unknown")
        logger.info(
            "whatsapp_message_sent",
            message_id=wa_message_id,
            recipient=message.recipient_id,
        )
        return {"message_id": wa_message_id, "status": "sent"}

    async def receive_message(self, raw_payload: dict[str, Any]) -> InboundMessage:
        """Parse an incoming WhatsApp webhook payload.

        The webhook payload from the WhatsApp Cloud API is nested:
        ``entry[].changes[].value.messages[]``
        """
        return self.parse_incoming(raw_payload)

    def format_outgoing(self, message: OutboundMessage) -> dict[str, Any]:
        """Convert an ``OutboundMessage`` to WhatsApp Cloud API format."""
        payload: dict[str, Any] = {
            "messaging_product": "whatsapp",
            "to": message.recipient_id,
            "type": "text",
            "text": {
                "preview_url": False,
                "body": message.content,
            },
        }

        # Support reply threading
        if message.reply_to_message_id:
            payload["context"] = {"message_id": message.reply_to_message_id}

        return payload

    def parse_incoming(self, raw_payload: dict[str, Any]) -> InboundMessage:
        """Extract the first message from a WhatsApp webhook payload."""
        # Navigate the nested webhook structure
        entry = raw_payload.get("entry", [{}])[0]
        changes = entry.get("changes", [{}])[0]
        value = changes.get("value", {})
        messages = value.get("messages", [])
        contacts = value.get("contacts", [])

        if not messages:
            # Status update or other non-message event
            return InboundMessage(
                channel=self.channel_name,
                channel_message_id="status_update",
                sender_id="system",
                content="",
                metadata={"raw_type": "status_update", "raw": raw_payload},
            )

        msg = messages[0]
        sender_phone = msg.get("from", "unknown")
        sender_name = contacts[0].get("profile", {}).get("name", "") if contacts else ""

        # Handle text messages
        content = ""
        content_type = msg.get("type", "text")
        if content_type == "text":
            content = msg.get("text", {}).get("body", "")
        elif content_type == "image":
            content = msg.get("image", {}).get("caption", "[image]")
        elif content_type == "document":
            content = msg.get("document", {}).get("caption", "[document]")
        elif content_type == "audio":
            content = "[audio message]"
        elif content_type == "video":
            content = msg.get("video", {}).get("caption", "[video]")

        return InboundMessage(
            channel=self.channel_name,
            channel_message_id=msg.get("id", str(uuid.uuid4())),
            sender_id=sender_phone,
            content=content,
            content_type=content_type,
            metadata={
                "sender_name": sender_name,
                "timestamp": msg.get("timestamp", ""),
                "wa_message_type": content_type,
            },
        )

    @staticmethod
    def verify_webhook(mode: str, token: str, challenge: str) -> str | None:
        """Verify a WhatsApp webhook subscription request.

        Returns the challenge string on success, or ``None`` on failure.
        """
        settings = get_settings()
        expected_token = settings.twilio_auth_token  # reusing the field for verify token
        if mode == "subscribe" and expected_token and token:
            return challenge
        return None
