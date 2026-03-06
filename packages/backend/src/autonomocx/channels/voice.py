"""Twilio voice adapter.

Generates TwiML responses for inbound calls and manages the call flow
including speech-to-text (STT) and text-to-speech (TTS) via Twilio.
"""

from __future__ import annotations

import uuid
from datetime import datetime, UTC
from typing import Any

import structlog

from autonomocx.core.config import get_settings
from .base import ChannelAdapter, InboundMessage, OutboundMessage

logger = structlog.get_logger(__name__)


class VoiceAdapter(ChannelAdapter):
    """Adapter for Twilio Programmable Voice.

    Inbound calls trigger TwiML webhooks.  The adapter generates TwiML
    responses that gather speech input (via ``<Gather>`` with speech
    recognition) and speak responses back using ``<Say>``.
    """

    channel_name = "voice"

    def __init__(self) -> None:
        self._settings = get_settings()

    # ── TwiML generation helpers ──────────────────────────────────

    @staticmethod
    def build_greeting_twiml(
        greeting: str = "Hello, welcome to support. How can I help you?",
        *,
        action_url: str = "/api/v1/channels/voice/gather",
        language: str = "en-US",
        voice: str = "Polly.Joanna",
    ) -> str:
        """Generate TwiML for the initial call greeting with speech gathering."""
        return f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Gather input="speech" action="{action_url}" language="{language}" speechTimeout="auto" speechModel="phone_call">
        <Say voice="{voice}">{greeting}</Say>
    </Gather>
    <Say voice="{voice}">I didn't catch that. Goodbye.</Say>
</Response>"""

    @staticmethod
    def build_response_twiml(
        text: str,
        *,
        gather_more: bool = True,
        action_url: str = "/api/v1/channels/voice/gather",
        language: str = "en-US",
        voice: str = "Polly.Joanna",
    ) -> str:
        """Generate TwiML that speaks a response and optionally gathers more input."""
        if gather_more:
            return f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Gather input="speech" action="{action_url}" language="{language}" speechTimeout="auto" speechModel="phone_call">
        <Say voice="{voice}">{text}</Say>
    </Gather>
    <Say voice="{voice}">Thank you for calling. Goodbye.</Say>
</Response>"""
        else:
            return f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="{voice}">{text}</Say>
    <Hangup/>
</Response>"""

    @staticmethod
    def build_transfer_twiml(
        phone_number: str,
        message: str = "Let me transfer you to a human agent.",
        voice: str = "Polly.Joanna",
    ) -> str:
        """Generate TwiML to transfer the call to a human agent."""
        return f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="{voice}">{message}</Say>
    <Dial>{phone_number}</Dial>
</Response>"""

    # ── ChannelAdapter interface ──────────────────────────────────

    async def send_message(self, message: OutboundMessage) -> dict[str, Any]:
        """Generate a TwiML response for an active call.

        In the voice flow, ``send_message`` does not make an outbound HTTP
        call.  Instead it returns the TwiML string that the webhook endpoint
        will return to Twilio.
        """
        twiml = self.build_response_twiml(
            message.content,
            gather_more=message.metadata.get("gather_more", True),
        )
        message_id = str(uuid.uuid4())
        logger.info(
            "voice_response_generated",
            message_id=message_id,
            recipient=message.recipient_id,
        )
        return {
            "message_id": message_id,
            "status": "twiml_generated",
            "twiml": twiml,
        }

    async def receive_message(self, raw_payload: dict[str, Any]) -> InboundMessage:
        """Parse a Twilio voice webhook payload (speech gather result)."""
        return self.parse_incoming(raw_payload)

    def format_outgoing(self, message: OutboundMessage) -> dict[str, Any]:
        """Convert an ``OutboundMessage`` to a TwiML-ready dict."""
        return {
            "text": message.content,
            "voice": message.metadata.get("voice", "Polly.Joanna"),
            "language": message.metadata.get("language", "en-US"),
            "gather_more": message.metadata.get("gather_more", True),
        }

    def parse_incoming(self, raw_payload: dict[str, Any]) -> InboundMessage:
        """Parse a Twilio webhook payload from a speech gather or incoming call.

        Twilio sends form-encoded data which should be parsed to a dict
        before passing here.  Key fields:
        - ``SpeechResult``: transcribed speech
        - ``Confidence``: STT confidence score
        - ``CallSid``: unique call identifier
        - ``From``: caller phone number
        """
        speech_result = raw_payload.get("SpeechResult", "")
        confidence = raw_payload.get("Confidence", "0.0")
        call_sid = raw_payload.get("CallSid", str(uuid.uuid4()))
        caller = raw_payload.get("From", "unknown")
        called = raw_payload.get("To", "")
        call_status = raw_payload.get("CallStatus", "in-progress")

        return InboundMessage(
            channel=self.channel_name,
            channel_message_id=call_sid,
            sender_id=caller,
            content=speech_result,
            content_type="speech",
            metadata={
                "confidence": float(confidence) if confidence else 0.0,
                "call_sid": call_sid,
                "call_status": call_status,
                "called_number": called,
                "digits": raw_payload.get("Digits", ""),
            },
        )

    @staticmethod
    def validate_twilio_signature(
        url: str,
        params: dict[str, str],
        signature: str,
    ) -> bool:
        """Validate a Twilio webhook signature.

        Requires the ``twilio`` package.  Returns ``True`` if the
        signature is valid, ``False`` otherwise.
        """
        try:
            from twilio.request_validator import RequestValidator

            settings = get_settings()
            auth_token = (
                settings.twilio_auth_token.get_secret_value()
                if settings.twilio_auth_token
                else ""
            )
            validator = RequestValidator(auth_token)
            return validator.validate(url, params, signature)
        except ImportError:
            logger.warning("twilio_not_installed", msg="Cannot validate signature without twilio")
            return False
