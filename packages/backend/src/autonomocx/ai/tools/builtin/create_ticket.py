"""Built-in tool: Create a CRM support ticket."""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime
from typing import Any

import structlog

logger = structlog.get_logger(__name__)

TOOL_NAME = "create_ticket"
TOOL_DESCRIPTION = "Create a new support ticket in the CRM system for tracking and escalation."
TOOL_PARAMETERS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "customer_id": {
            "type": "string",
            "description": "The customer's account identifier.",
        },
        "subject": {
            "type": "string",
            "description": "Brief subject line for the ticket.",
            "maxLength": 255,
        },
        "description": {
            "type": "string",
            "description": "Detailed description of the issue.",
        },
        "priority": {
            "type": "string",
            "description": "Ticket priority level.",
            "enum": ["low", "normal", "high", "urgent"],
        },
        "category": {
            "type": "string",
            "description": "Issue category for routing.",
            "enum": [
                "billing",
                "technical",
                "product",
                "shipping",
                "account",
                "general",
            ],
        },
        "assign_to_team": {
            "type": "string",
            "description": "Team to assign the ticket to (optional).",
        },
    },
    "required": ["customer_id", "subject", "description"],
}


class CreateTicketTool:
    """Simulated CRM ticket creation tool."""

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        customer_id = params["customer_id"]
        subject = params["subject"]
        priority = params.get("priority", "normal")
        category = params.get("category", "general")

        logger.info(
            "builtin_create_ticket_execute",
            customer_id=customer_id,
            priority=priority,
            category=category,
        )

        await asyncio.sleep(0.15)

        ticket_id = f"TKT-{uuid.uuid4().hex[:8].upper()}"

        # Simulate SLA based on priority
        sla_hours = {
            "urgent": 1,
            "high": 4,
            "normal": 24,
            "low": 72,
        }
        response_sla = sla_hours.get(priority, 24)

        return {
            "success": True,
            "ticket_id": ticket_id,
            "customer_id": customer_id,
            "subject": subject,
            "description": params.get("description", ""),
            "priority": priority,
            "category": category,
            "status": "open",
            "assigned_team": params.get("assign_to_team", f"{category}_support"),
            "created_at": datetime.utcnow().isoformat(),
            "sla_response_hours": response_sla,
            "message": (
                f"Support ticket {ticket_id} has been created with {priority} priority. "
                f"Our {category} team will respond within {response_sla} hours."
            ),
        }
