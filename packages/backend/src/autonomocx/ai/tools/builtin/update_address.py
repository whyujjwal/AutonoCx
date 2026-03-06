"""Built-in tool: Update a customer's shipping or billing address."""

from __future__ import annotations

import asyncio
from typing import Any

import structlog

logger = structlog.get_logger(__name__)

TOOL_NAME = "update_address"
TOOL_DESCRIPTION = "Update a customer's shipping or billing address on file."
TOOL_PARAMETERS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "customer_id": {
            "type": "string",
            "description": "The customer's account identifier.",
        },
        "address_type": {
            "type": "string",
            "description": "Whether this is a shipping or billing address.",
            "enum": ["shipping", "billing"],
        },
        "street": {
            "type": "string",
            "description": "Street address (line 1).",
        },
        "street2": {
            "type": "string",
            "description": "Street address line 2 (apartment, suite, etc.).",
        },
        "city": {
            "type": "string",
            "description": "City name.",
        },
        "state": {
            "type": "string",
            "description": "State or province code.",
        },
        "postal_code": {
            "type": "string",
            "description": "ZIP or postal code.",
        },
        "country": {
            "type": "string",
            "description": "Two-letter country code (ISO 3166-1 alpha-2).",
            "minLength": 2,
            "maxLength": 2,
        },
    },
    "required": ["customer_id", "address_type", "street", "city", "state", "postal_code", "country"],
}


class UpdateAddressTool:
    """Simulated address update tool."""

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        customer_id = params["customer_id"]
        address_type = params["address_type"]

        logger.info(
            "builtin_update_address_execute",
            customer_id=customer_id,
            address_type=address_type,
        )

        await asyncio.sleep(0.2)

        formatted_address = ", ".join(
            filter(None, [
                params.get("street"),
                params.get("street2"),
                params.get("city"),
                f"{params.get('state', '')} {params.get('postal_code', '')}".strip(),
                params.get("country"),
            ])
        )

        return {
            "success": True,
            "customer_id": customer_id,
            "address_type": address_type,
            "updated_address": {
                "street": params.get("street"),
                "street2": params.get("street2"),
                "city": params.get("city"),
                "state": params.get("state"),
                "postal_code": params.get("postal_code"),
                "country": params.get("country"),
            },
            "formatted_address": formatted_address,
            "message": (
                f"The {address_type} address for customer {customer_id} "
                f"has been updated to: {formatted_address}"
            ),
        }
