"""Inbound webhook endpoints for external channels."""

from __future__ import annotations

import hashlib
import hmac
import logging
from typing import Any, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from autonomocx.core.config import get_settings
from autonomocx.core.database import get_db
from autonomocx.services.webhooks import (
    handle_email_inbound,
    handle_twilio_sms_inbound,
    handle_twilio_voice_inbound,
    handle_whatsapp_inbound,
)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class WebhookResponse(BaseModel):
    status: str = "ok"
    message: Optional[str] = None


class WhatsAppMessage(BaseModel):
    """Simplified WhatsApp inbound message payload."""
    from_number: str = Field(..., alias="From")
    to_number: str = Field(..., alias="To")
    body: str = Field("", alias="Body")
    num_media: int = Field(0, alias="NumMedia")
    message_sid: str = Field(..., alias="MessageSid")
    account_sid: str = Field(..., alias="AccountSid")


class EmailInbound(BaseModel):
    """Inbound email payload (e.g., from SendGrid Inbound Parse or similar)."""
    from_email: str = Field(..., alias="from")
    to_email: str = Field(..., alias="to")
    subject: str = ""
    text: str = ""
    html: Optional[str] = None
    headers: Optional[str] = None
    envelope: Optional[str] = None
    attachments: Optional[int] = 0


# ---------------------------------------------------------------------------
# Signature verification helpers
# ---------------------------------------------------------------------------


def _verify_twilio_signature(
    request_url: str,
    params: dict[str, str],
    signature: str,
) -> bool:
    """Verify a Twilio webhook signature using the auth token."""
    settings = get_settings()
    if not settings.twilio_auth_token:
        logger.warning("Twilio auth token not configured; skipping signature check")
        return True

    auth_token = settings.twilio_auth_token.get_secret_value()

    # Build the data string per Twilio's specification
    data = request_url
    for key in sorted(params.keys()):
        data += key + params[key]

    computed = hmac.new(
        auth_token.encode("utf-8"),
        data.encode("utf-8"),
        hashlib.sha1,
    ).digest()

    import base64
    expected = base64.b64encode(computed).decode("utf-8")
    return hmac.compare_digest(expected, signature)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/whatsapp",
    response_model=WebhookResponse,
    summary="WhatsApp inbound webhook",
)
async def whatsapp_webhook(
    request: Request,
    x_twilio_signature: str = Header("", alias="X-Twilio-Signature"),
    db: AsyncSession = Depends(get_db),
) -> WebhookResponse:
    """Receive inbound WhatsApp messages via Twilio.

    Verifies the Twilio request signature, then dispatches the
    message to the appropriate conversation pipeline.
    """
    form_data = await request.form()
    params = {k: str(v) for k, v in form_data.items()}

    # Signature verification
    if x_twilio_signature:
        request_url = str(request.url)
        if not _verify_twilio_signature(request_url, params, x_twilio_signature):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid Twilio signature",
            )

    await handle_whatsapp_inbound(
        db,
        from_number=params.get("From", ""),
        to_number=params.get("To", ""),
        body=params.get("Body", ""),
        message_sid=params.get("MessageSid", ""),
        num_media=int(params.get("NumMedia", "0")),
        media_urls={
            k: v for k, v in params.items() if k.startswith("MediaUrl")
        },
    )
    return WebhookResponse(message="WhatsApp message received")


@router.post(
    "/twilio/voice",
    summary="Twilio voice webhook",
)
async def twilio_voice_webhook(
    request: Request,
    x_twilio_signature: str = Header("", alias="X-Twilio-Signature"),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Handle an inbound Twilio voice call.

    Returns TwiML response to control the call flow (e.g., IVR menu,
    speech-to-text, or connection to an agent).
    """
    form_data = await request.form()
    params = {k: str(v) for k, v in form_data.items()}

    # Signature verification
    if x_twilio_signature:
        request_url = str(request.url)
        if not _verify_twilio_signature(request_url, params, x_twilio_signature):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid Twilio signature",
            )

    twiml_response = await handle_twilio_voice_inbound(
        db,
        call_sid=params.get("CallSid", ""),
        from_number=params.get("From", ""),
        to_number=params.get("To", ""),
        call_status=params.get("CallStatus", ""),
        speech_result=params.get("SpeechResult"),
        digits=params.get("Digits"),
    )

    from fastapi.responses import Response

    return Response(
        content=twiml_response,
        media_type="application/xml",
    )


@router.post(
    "/twilio/sms",
    response_model=WebhookResponse,
    summary="Twilio SMS webhook",
)
async def twilio_sms_webhook(
    request: Request,
    x_twilio_signature: str = Header("", alias="X-Twilio-Signature"),
    db: AsyncSession = Depends(get_db),
) -> WebhookResponse:
    """Receive inbound SMS messages via Twilio.

    Verifies the Twilio request signature, then dispatches the
    message to the appropriate conversation pipeline.
    """
    form_data = await request.form()
    params = {k: str(v) for k, v in form_data.items()}

    # Signature verification
    if x_twilio_signature:
        request_url = str(request.url)
        if not _verify_twilio_signature(request_url, params, x_twilio_signature):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid Twilio signature",
            )

    await handle_twilio_sms_inbound(
        db,
        from_number=params.get("From", ""),
        to_number=params.get("To", ""),
        body=params.get("Body", ""),
        message_sid=params.get("MessageSid", ""),
    )
    return WebhookResponse(message="SMS message received")


@router.post(
    "/email",
    response_model=WebhookResponse,
    summary="Email inbound webhook",
)
async def email_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> WebhookResponse:
    """Receive inbound emails via a provider webhook (e.g., SendGrid Inbound Parse).

    The exact payload format depends on the email provider configuration.
    This endpoint handles the common fields and dispatches to the
    conversation pipeline.
    """
    content_type = request.headers.get("content-type", "")

    if "application/json" in content_type:
        payload = await request.json()
    else:
        # Form-encoded (SendGrid Inbound Parse default)
        form_data = await request.form()
        payload = {k: str(v) for k, v in form_data.items()}

    await handle_email_inbound(
        db,
        from_email=payload.get("from", payload.get("from_email", "")),
        to_email=payload.get("to", payload.get("to_email", "")),
        subject=payload.get("subject", ""),
        text_body=payload.get("text", ""),
        html_body=payload.get("html"),
        headers=payload.get("headers"),
        envelope=payload.get("envelope"),
        num_attachments=int(payload.get("attachments", 0)),
    )
    return WebhookResponse(message="Email received")
