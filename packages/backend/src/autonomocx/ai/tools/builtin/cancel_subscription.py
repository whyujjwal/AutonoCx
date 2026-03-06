"""Built-in tool: Cancel a customer subscription."""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Any

import structlog

logger = structlog.get_logger(__name__)

TOOL_NAME = "cancel_subscription"
TOOL_DESCRIPTION = "Cancel an active customer subscription, effective immediately or at period end."
TOOL_PARAMETERS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "subscription_id": {
            "type": "string",
            "description": "The subscription identifier to cancel.",
        },
        "customer_id": {
            "type": "string",
            "description": "The customer's account identifier.",
        },
        "cancel_at_period_end": {
            "type": "boolean",
            "description": (
                "If true, subscription remains active until the current billing period ends."
            ),
        },
        "reason": {
            "type": "string",
            "description": "Reason for cancellation.",
            "enum": [
                "too_expensive",
                "not_using",
                "missing_features",
                "switching_competitor",
                "poor_support",
                "other",
            ],
        },
    },
    "required": ["subscription_id", "customer_id"],
}


class CancelSubscriptionTool:
    """Simulated subscription cancellation tool."""

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        subscription_id = params["subscription_id"]
        customer_id = params["customer_id"]
        cancel_at_period_end = params.get("cancel_at_period_end", True)
        reason = params.get("reason", "other")

        logger.info(
            "builtin_cancel_subscription_execute",
            subscription_id=subscription_id,
            customer_id=customer_id,
            at_period_end=cancel_at_period_end,
        )

        await asyncio.sleep(0.25)

        period_end = datetime.utcnow() + timedelta(days=14)
        cancellation_id = f"CXL-{uuid.uuid4().hex[:8].upper()}"

        if cancel_at_period_end:
            status = "pending_cancellation"
            effective_date = period_end.isoformat()
            message = (
                f"Subscription {subscription_id} is set to cancel at the end of the "
                f"current billing period ({period_end.strftime('%B %d, %Y')}). "
                f"You will continue to have access until then."
            )
        else:
            status = "cancelled"
            effective_date = datetime.utcnow().isoformat()
            message = (
                f"Subscription {subscription_id} has been cancelled immediately. "
                f"A prorated refund will be processed if applicable."
            )

        return {
            "success": True,
            "cancellation_id": cancellation_id,
            "subscription_id": subscription_id,
            "customer_id": customer_id,
            "status": status,
            "reason": reason,
            "effective_date": effective_date,
            "prorated_refund": 0.0 if cancel_at_period_end else 12.50,
            "message": message,
        }
