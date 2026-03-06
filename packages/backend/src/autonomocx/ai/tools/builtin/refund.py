"""Built-in tool: Process a refund for an order."""

from __future__ import annotations

import asyncio
import uuid
from typing import Any

import structlog

logger = structlog.get_logger(__name__)

TOOL_NAME = "process_refund"
TOOL_DESCRIPTION = "Process a full or partial refund for a customer order."
TOOL_PARAMETERS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "order_id": {
            "type": "string",
            "description": "The order identifier to refund.",
        },
        "amount": {
            "type": "number",
            "description": "Refund amount in the order's currency. Omit for a full refund.",
            "minimum": 0.01,
        },
        "reason": {
            "type": "string",
            "description": "Reason for the refund.",
            "enum": [
                "defective_product",
                "wrong_item",
                "not_as_described",
                "changed_mind",
                "late_delivery",
                "other",
            ],
        },
    },
    "required": ["order_id", "reason"],
}


class ProcessRefundTool:
    """Simulated refund processing tool."""

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        order_id = params["order_id"]
        amount = params.get("amount")
        reason = params.get("reason", "other")

        logger.info("builtin_refund_execute", order_id=order_id, amount=amount, reason=reason)

        # Simulate API latency
        await asyncio.sleep(0.3)

        refund_id = f"REF-{uuid.uuid4().hex[:8].upper()}"
        refund_amount = amount if amount else 99.99  # Default full-refund amount

        return {
            "success": True,
            "refund_id": refund_id,
            "order_id": order_id,
            "refund_amount": refund_amount,
            "currency": "USD",
            "reason": reason,
            "status": "processed",
            "estimated_arrival": "3-5 business days",
            "message": (
                f"Refund of ${refund_amount:.2f} has been processed for order {order_id}. "
                "The amount will be returned to the original payment"
                " method within 3-5 business days."
            ),
        }
