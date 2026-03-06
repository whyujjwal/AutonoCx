"""Built-in tool: Generate a payment link for a customer."""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Any

import structlog

logger = structlog.get_logger(__name__)

TOOL_NAME = "generate_payment_link"
TOOL_DESCRIPTION = "Generate a secure, one-time payment link for a customer invoice or balance."
TOOL_PARAMETERS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "customer_id": {
            "type": "string",
            "description": "The customer's account identifier.",
        },
        "amount": {
            "type": "number",
            "description": "Payment amount.",
            "minimum": 0.01,
        },
        "currency": {
            "type": "string",
            "description": "Three-letter currency code (e.g. USD, EUR).",
            "minLength": 3,
            "maxLength": 3,
        },
        "description": {
            "type": "string",
            "description": "Description shown on the payment page.",
        },
        "expires_in_hours": {
            "type": "integer",
            "description": "Number of hours until the link expires (default 72).",
            "minimum": 1,
            "maximum": 720,
        },
    },
    "required": ["customer_id", "amount", "currency"],
}


class GeneratePaymentLinkTool:
    """Simulated payment link generation tool."""

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        customer_id = params["customer_id"]
        amount = params["amount"]
        currency = params.get("currency", "USD").upper()
        description = params.get("description", "Payment")
        expires_in_hours = params.get("expires_in_hours", 72)

        logger.info(
            "builtin_generate_payment_link_execute",
            customer_id=customer_id,
            amount=amount,
            currency=currency,
        )

        await asyncio.sleep(0.2)

        link_id = uuid.uuid4().hex[:12]
        expiry = datetime.utcnow() + timedelta(hours=expires_in_hours)

        return {
            "success": True,
            "payment_link_id": f"PAY-{link_id.upper()}",
            "url": f"https://pay.autonomocx.com/p/{link_id}",
            "customer_id": customer_id,
            "amount": amount,
            "currency": currency,
            "description": description,
            "expires_at": expiry.isoformat(),
            "status": "active",
            "message": (
                f"Payment link generated for {currency} {amount:.2f}. "
                f"The link is valid until {expiry.strftime('%B %d, %Y at %H:%M UTC')}."
            ),
        }
