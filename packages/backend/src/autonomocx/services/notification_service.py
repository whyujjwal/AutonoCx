"""Real-time notification service -- Redis pub/sub for supervisors."""

from __future__ import annotations

import json
import uuid
from typing import Any

import structlog

logger = structlog.get_logger(__name__)

# Redis channel naming convention
_CHANNEL_PREFIX = "autonomocx:notifications"


def _supervisor_channel(org_id: uuid.UUID) -> str:
    """Return the Redis pub/sub channel name for supervisor notifications."""
    return f"{_CHANNEL_PREFIX}:{org_id}:supervisor"


def _escalation_channel(org_id: uuid.UUID) -> str:
    """Return the Redis pub/sub channel name for escalation notifications."""
    return f"{_CHANNEL_PREFIX}:{org_id}:escalation"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def notify_supervisor(
    redis: Any,  # redis.asyncio.Redis
    org_id: uuid.UUID,
    action_execution: Any,  # ActionExecution ORM instance
) -> None:
    """Publish an action-approval notification to supervisors.

    Supervisors subscribe to the ``supervisor`` channel via WebSocket
    or SSE and receive real-time alerts when new actions require
    approval.
    """
    payload = {
        "type": "action_approval_required",
        "org_id": str(org_id),
        "action_id": str(action_execution.id),
        "tool_id": str(action_execution.tool_id),
        "conversation_id": str(action_execution.conversation_id),
        "status": (
            action_execution.status.value
            if hasattr(action_execution.status, "value")
            else str(action_execution.status)
        ),
        "input_params": action_execution.input_params,
        "risk_score": str(action_execution.risk_score) if action_execution.risk_score else None,
        "requires_approval": action_execution.requires_approval,
        "created_at": (
            action_execution.created_at.isoformat()
            if hasattr(action_execution, "created_at") and action_execution.created_at
            else None
        ),
    }

    channel = _supervisor_channel(org_id)
    message = json.dumps(payload, default=str)
    await redis.publish(channel, message)

    logger.info(
        "supervisor_notified",
        org_id=str(org_id),
        action_id=str(action_execution.id),
        channel=channel,
    )


async def notify_escalation(
    redis: Any,  # redis.asyncio.Redis
    org_id: uuid.UUID,
    conversation: Any,  # Conversation ORM instance
) -> None:
    """Publish an escalation notification when a conversation is escalated.

    Human agents monitoring the escalation channel receive an alert with
    the conversation details so they can take over.
    """
    payload = {
        "type": "conversation_escalated",
        "org_id": str(org_id),
        "conversation_id": str(conversation.id),
        "customer_id": conversation.customer_id,
        "customer_name": conversation.customer_name,
        "customer_email": conversation.customer_email,
        "channel": (
            conversation.channel.value
            if hasattr(conversation.channel, "value")
            else str(conversation.channel)
        ),
        "priority": (
            conversation.priority.value
            if hasattr(conversation.priority, "value")
            else str(conversation.priority)
        ),
        "sentiment": conversation.sentiment,
        "intent": conversation.intent,
        "assigned_to": str(conversation.assigned_to) if conversation.assigned_to else None,
        "status": (
            conversation.status.value
            if hasattr(conversation.status, "value")
            else str(conversation.status)
        ),
        "started_at": (
            conversation.started_at.isoformat()
            if hasattr(conversation, "started_at") and conversation.started_at
            else None
        ),
    }

    channel = _escalation_channel(org_id)
    message = json.dumps(payload, default=str)
    await redis.publish(channel, message)

    logger.info(
        "escalation_notified",
        org_id=str(org_id),
        conversation_id=str(conversation.id),
        channel=channel,
    )
