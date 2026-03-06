"""Built-in tool: Check the status of a customer claim or warranty request."""

from __future__ import annotations

import asyncio
import random
from datetime import datetime, timedelta
from typing import Any

import structlog

logger = structlog.get_logger(__name__)

TOOL_NAME = "check_claim_status"
TOOL_DESCRIPTION = "Check the current status of a customer claim, warranty, or return request."
TOOL_PARAMETERS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "claim_id": {
            "type": "string",
            "description": "The claim or case identifier.",
        },
        "customer_id": {
            "type": "string",
            "description": "The customer's account identifier (optional, for verification).",
        },
    },
    "required": ["claim_id"],
}


class CheckClaimStatusTool:
    """Simulated claim status lookup tool."""

    _STATUSES: list[dict[str, Any]] = [
        {
            "status": "under_review",
            "description": "Your claim is currently being reviewed by our team.",
            "estimated_resolution": 3,
        },
        {
            "status": "approved",
            "description": "Your claim has been approved. Processing is underway.",
            "estimated_resolution": 0,
        },
        {
            "status": "pending_documentation",
            "description": "We need additional documentation to process your claim.",
            "estimated_resolution": 5,
        },
        {
            "status": "in_progress",
            "description": "Your claim is actively being processed.",
            "estimated_resolution": 2,
        },
        {
            "status": "resolved",
            "description": "Your claim has been resolved.",
            "estimated_resolution": 0,
        },
    ]

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        claim_id = params["claim_id"]
        customer_id = params.get("customer_id")

        logger.info(
            "builtin_check_claim_status_execute",
            claim_id=claim_id,
            customer_id=customer_id,
        )

        await asyncio.sleep(0.2)

        # Deterministic but varied results based on claim_id hash
        status_info = self._STATUSES[hash(claim_id) % len(self._STATUSES)]
        filed_date = datetime.utcnow() - timedelta(days=random.randint(1, 14))
        est_days = int(status_info["estimated_resolution"])

        result: dict[str, Any] = {
            "success": True,
            "claim_id": claim_id,
            "status": status_info["status"],
            "status_description": status_info["description"],
            "filed_date": filed_date.isoformat(),
            "last_updated": datetime.utcnow().isoformat(),
        }

        if est_days > 0:
            est_date = datetime.utcnow() + timedelta(days=est_days)
            result["estimated_resolution_date"] = est_date.isoformat()

        if status_info["status"] == "pending_documentation":
            result["required_documents"] = [
                "Proof of purchase (receipt or order confirmation)",
                "Photos of the defective item",
            ]

        result["message"] = (
            f"Claim {claim_id}: {status_info['description']} "
            f"Filed on {filed_date.strftime('%B %d, %Y')}."
        )

        return result
