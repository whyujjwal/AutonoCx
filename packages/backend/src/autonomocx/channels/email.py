"""Email channel adapter.

Sends messages via SMTP and parses inbound emails from webhook payloads
(e.g. from SendGrid Inbound Parse, Mailgun routes, or a custom IMAP poller).
"""

from __future__ import annotations

import email as email_lib
import smtplib
import uuid
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, UTC
from typing import Any

import structlog

from autonomocx.core.config import get_settings
from .base import ChannelAdapter, InboundMessage, OutboundMessage

logger = structlog.get_logger(__name__)


class EmailAdapter(ChannelAdapter):
    """Adapter for email-based customer support.

    Outgoing messages are sent via SMTP.  Incoming messages are expected
    to arrive as parsed JSON payloads from an inbound email webhook
    (e.g., SendGrid Inbound Parse or a custom IMAP worker).
    """

    channel_name = "email"

    def __init__(self) -> None:
        self._settings = get_settings()

    # ── ChannelAdapter interface ──────────────────────────────────

    async def send_message(self, message: OutboundMessage) -> dict[str, Any]:
        """Send an email via SMTP.

        Note: This performs blocking I/O in an async context.  In production,
        this should be offloaded to a background worker or use an async SMTP
        library like ``aiosmtplib``.
        """
        settings = self._settings
        if not settings.smtp_host or not settings.smtp_username:
            logger.error("email_send_failed", reason="SMTP not configured")
            return {"message_id": None, "status": "not_configured"}

        payload = self.format_outgoing(message)

        try:
            msg = MIMEMultipart("alternative")
            msg["From"] = settings.smtp_from_email or settings.smtp_username
            msg["To"] = message.recipient_id
            msg["Subject"] = message.metadata.get(
                "subject", "Support Update"
            )
            msg["Message-ID"] = f"<{uuid.uuid4().hex}@autonomocx>"

            # Attach both plain text and HTML
            msg.attach(MIMEText(message.content, "plain"))
            if html_body := payload.get("html_body"):
                msg.attach(MIMEText(html_body, "html"))

            with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
                if settings.smtp_use_tls:
                    server.starttls()
                if settings.smtp_password:
                    server.login(
                        settings.smtp_username,
                        settings.smtp_password.get_secret_value(),
                    )
                server.send_message(msg)

            message_id = msg["Message-ID"]
            logger.info(
                "email_sent",
                message_id=message_id,
                recipient=message.recipient_id,
            )
            return {"message_id": message_id, "status": "sent"}

        except Exception as exc:
            logger.exception(
                "email_send_failed",
                recipient=message.recipient_id,
                error=str(exc),
            )
            return {"message_id": None, "status": "failed", "error": str(exc)}

    async def receive_message(self, raw_payload: dict[str, Any]) -> InboundMessage:
        """Parse an incoming email webhook payload."""
        return self.parse_incoming(raw_payload)

    def format_outgoing(self, message: OutboundMessage) -> dict[str, Any]:
        """Convert an ``OutboundMessage`` to an email-ready dict."""
        html_body = message.metadata.get("html_body")
        if not html_body:
            # Wrap plain text in minimal HTML
            escaped = message.content.replace("&", "&amp;").replace("<", "&lt;")
            html_body = f"<div style='font-family: sans-serif; line-height: 1.5;'><p>{escaped}</p></div>"

        return {
            "to": message.recipient_id,
            "from": self._settings.smtp_from_email or self._settings.smtp_username,
            "subject": message.metadata.get("subject", "Support Update"),
            "text_body": message.content,
            "html_body": html_body,
            "in_reply_to": message.reply_to_message_id,
            "attachments": message.attachments,
        }

    def parse_incoming(self, raw_payload: dict[str, Any]) -> InboundMessage:
        """Parse an inbound email payload into an ``InboundMessage``.

        Supports common webhook formats (SendGrid, Mailgun) as well as
        a generic format with ``from``, ``subject``, ``text``, ``html`` fields.
        """
        sender = raw_payload.get("from", raw_payload.get("sender", "unknown@unknown.com"))
        subject = raw_payload.get("subject", "(no subject)")
        text_body = raw_payload.get("text", raw_payload.get("body-plain", ""))
        html_body = raw_payload.get("html", raw_payload.get("body-html", ""))
        message_id = raw_payload.get(
            "Message-ID",
            raw_payload.get("message-id", str(uuid.uuid4())),
        )

        # Extract email address from "Name <email>" format
        if "<" in sender and ">" in sender:
            sender_email = sender.split("<")[1].rstrip(">")
        else:
            sender_email = sender

        attachments = []
        for att in raw_payload.get("attachments", []):
            attachments.append({
                "filename": att.get("filename", "unknown"),
                "content_type": att.get("content-type", "application/octet-stream"),
                "size": att.get("size", 0),
                "url": att.get("url", ""),
            })

        return InboundMessage(
            channel=self.channel_name,
            channel_message_id=message_id,
            sender_id=sender_email,
            content=text_body or html_body,
            content_type="text" if text_body else "html",
            attachments=attachments,
            metadata={
                "subject": subject,
                "sender_name": sender.split("<")[0].strip() if "<" in sender else "",
                "html_body": html_body,
                "in_reply_to": raw_payload.get("In-Reply-To", ""),
                "references": raw_payload.get("References", ""),
            },
        )
