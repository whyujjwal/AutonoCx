"""Built-in tool: Look up customer information from the CRM."""

from __future__ import annotations

import asyncio
import hashlib
from datetime import datetime, timedelta
from typing import Any

import structlog

logger = structlog.get_logger(__name__)

TOOL_NAME = "crm_lookup"
TOOL_DESCRIPTION = (
    "Look up customer profile and account information from the CRM system. "
    "Returns contact details, subscription status, and recent activity."
)
TOOL_PARAMETERS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "customer_id": {
            "type": "string",
            "description": "The customer's account identifier.",
        },
        "email": {
            "type": "string",
            "description": "Customer email address (alternative lookup key).",
        },
        "fields": {
            "type": "array",
            "items": {"type": "string"},
            "description": (
                "Specific fields to return. Options: profile, subscription, "
                "orders, activity. Defaults to all."
            ),
        },
    },
    "required": [],
}


class CRMLookupTool:
    """Simulated CRM customer lookup tool."""

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        customer_id = params.get("customer_id", "")
        email = params.get("email", "")
        fields = params.get("fields", ["profile", "subscription", "orders", "activity"])

        if not customer_id and not email:
            return {
                "success": False,
                "error": "Either customer_id or email must be provided.",
            }

        logger.info(
            "builtin_crm_lookup_execute",
            customer_id=customer_id,
            email=email,
        )

        await asyncio.sleep(0.25)

        # Generate deterministic but realistic data based on customer identifier
        seed = customer_id or email
        hash_val = int(hashlib.md5(seed.encode()).hexdigest()[:8], 16)

        result: dict[str, Any] = {
            "success": True,
            "customer_id": customer_id or f"CUS-{hash_val:08X}",
        }

        if "profile" in fields:
            result["profile"] = {
                "name": f"Customer {hash_val % 10000}",
                "email": email or f"customer{hash_val % 10000}@example.com",
                "phone": f"+1-555-{hash_val % 10000:04d}",
                "created_at": (datetime.utcnow() - timedelta(days=hash_val % 730)).isoformat(),
                "tier": ["standard", "premium", "enterprise"][hash_val % 3],
                "verified": True,
            }

        if "subscription" in fields:
            plan_names = ["Basic", "Pro", "Business", "Enterprise"]
            statuses = ["active", "active", "active", "past_due", "cancelled"]
            result["subscription"] = {
                "plan": plan_names[hash_val % len(plan_names)],
                "status": statuses[hash_val % len(statuses)],
                "billing_cycle": "monthly" if hash_val % 2 == 0 else "annual",
                "next_billing_date": (
                    datetime.utcnow() + timedelta(days=hash_val % 30)
                ).isoformat(),
                "monthly_amount": [9.99, 29.99, 79.99, 199.99][hash_val % 4],
                "currency": "USD",
            }

        if "orders" in fields:
            order_count = (hash_val % 12) + 1
            result["recent_orders"] = [
                {
                    "order_id": f"ORD-{(hash_val + i):08X}",
                    "date": (datetime.utcnow() - timedelta(days=i * 15)).isoformat(),
                    "total": round(19.99 + (hash_val + i) % 200, 2),
                    "status": ["delivered", "shipped", "processing"][i % 3],
                }
                for i in range(min(order_count, 5))
            ]
            result["total_order_count"] = order_count

        if "activity" in fields:
            result["recent_activity"] = {
                "last_login": (datetime.utcnow() - timedelta(hours=hash_val % 72)).isoformat(),
                "total_support_tickets": hash_val % 8,
                "open_tickets": hash_val % 3,
                "satisfaction_score": round(3.0 + (hash_val % 20) / 10, 1),
                "lifetime_value": round(99.99 + (hash_val % 5000), 2),
            }

        return result
