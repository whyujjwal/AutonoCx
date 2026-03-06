"""SMS adapter via Twilio Programmable Messaging.

Sends SMS messages through the Twilio API and receives inbound SMS
via webhook.
"""

from __future__ import annotations

import uuid
from datetime import datetime, UTC
from typing import Any

import structlog

from autonomocx.core.config import get_settings
from .base import ChannelAdapter, InboundMessage, OutboundMessage

logger = structlog.get_logger(__name__)


class SMSAdapter(ChannelAdapter):
    """Adapter for SMS messaging via Twilio."""

    channel_name = "sms"

    def __init__(self) -> None:
        self._settings = get_settings()
        self._client = None

    def _get_twilio_client(self):
        """Lazy-initialise the Twilio REST client."""
        if self._client is None:
            try:
                from twilio.rest import Client

                settings = self._settings
                auth_token = (
                    settings.twilio_auth_token.get_secret_value()
                    if settings.twilio_auth_token
                    else ""
                )
                self._client = Client(settings.twilio_account_sid, auth_token)
            except ImportError:
                logger.error("twilio_not_installed", msg="twilio package required for SMS")
                raise
        return self._client

    # ── ChannelAdapter interface ──────────────────────────────────

    async def send_message(self, message: OutboundMessage) -> dict[str, Any]:
        """Send an SMS message via Twilio.

        Note: The Twilio Python SDK uses synchronous HTTP.  In production,
        consider wrapping this in ``asyncio.to_thread`` or using a task queue.
        """
        try:
            client = self._get_twilio_client()
            payload = self.format_outgoing(message)

            twilio_message = client.messages.create(
                body=payload["body"],
                from_=payload["from"],
                to=payload["to"],
                status_callback=payload.get("status_callback"),
            )

            logger.info(
                "sms_sent",
                message_sid=twilio_message.sid,
                recipient=message.recipient_id,
            )
            return {
                "message_id": twilio_message.sid,
                "status": "sent",
            }

        except Exception as exc:
            logger.exception(
                "sms_send_failed",
                recipient=message.recipient_id,
                error=str(exc),
            )
            return {"message_id": None, "status": "failed", "error": str(exc)}

    async def receive_message(self, raw_payload: dict[str, Any]) -> InboundMessage:
        """Parse an inbound SMS webhook payload from Twilio."""
        return self.parse_incoming(raw_payload)

    def format_outgoing(self, message: OutboundMessage) -> dict[str, Any]:
        """Convert an ``OutboundMessage`` to a Twilio-compatible dict."""
        settings = self._settings

        # Truncate to SMS length limits (1600 chars for multi-segment)
        body = message.content
        if len(body) > 1600:
            body = body[:1597] + "..."

        payload: dict[str, Any] = {
            "body": body,
            "from": settings.twilio_phone_number,
            "to": message.recipient_id,
        }

        # Optional status callback
        if settings.twilio_webhook_url:
            payload["status_callback"] = f"{settings.twilio_webhook_url}/sms/status"

        # Media attachments (MMS)
        if message.attachments:
            payload["media_url"] = [
                att["url"] for att in message.attachments if att.get("url")
            ]

        return payload

    def parse_incoming(self, raw_payload: dict[str, Any]) -> InboundMessage:
        """Parse a Twilio inbound SMS webhook payload.

        Twilio sends form-encoded data which should be parsed to a dict
        before passing here.  Key fields:
        - ``Body``: the message text
        - ``From``: sender phone number
        - ``MessageSid``: unique message identifier
        - ``NumMedia``: number of attached media files
        """
        body = raw_payload.get("Body", "")
        sender = raw_payload.get("From", "unknown")
        message_sid = raw_payload.get("MessageSid", str(uuid.uuid4()))
        to_number = raw_payload.get("To", "")

        # Parse media attachments
        attachments = []
        num_media = int(raw_payload.get("NumMedia", 0))
        for i in range(num_media):
            media_url = raw_payload.get(f"MediaUrl{i}", "")
            media_type = raw_payload.get(f"MediaContentType{i}", "")
            if media_url:
                attachments.append({
                    "url": media_url,
                    "content_type": media_type,
                    "index": i,
                })

        return InboundMessage(
            channel=self.channel_name,
            channel_message_id=message_sid,
            sender_id=sender,
            content=body,
            content_type="text",
            attachments=attachments,
            metadata={
                "to_number": to_number,
                "num_segments": raw_payload.get("NumSegments", "1"),
                "from_city": raw_payload.get("FromCity", ""),
                "from_state": raw_payload.get("FromState", ""),
                "from_country": raw_payload.get("FromCountry", ""),
                "sms_status": raw_payload.get("SmsStatus", ""),
            },
        )
