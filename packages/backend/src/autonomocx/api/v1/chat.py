"""WebSocket endpoint for real-time chat."""

from __future__ import annotations

import json
import logging
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, status
from sqlalchemy.ext.asyncio import AsyncSession

from autonomocx.core.database import get_db
from autonomocx.core.dependencies import get_current_user_ws
from autonomocx.models.user import User
from autonomocx.services.chat import ChatSessionManager
from autonomocx.services.conversations import get_conversation_by_id

router = APIRouter(tags=["chat"])

logger = logging.getLogger(__name__)

# Module-level connection manager singleton
_manager = ChatSessionManager()


# ---------------------------------------------------------------------------
# WebSocket message protocol
# ---------------------------------------------------------------------------
# Inbound (client -> server):
#   {"type": "message.send", "content": "...", "content_type": "text"}
#   {"type": "typing.start"}
#   {"type": "typing.stop"}
#   {"type": "message.read", "message_id": "..."}
#
# Outbound (server -> client):
#   {"type": "message.new",       "data": {...message...}}
#   {"type": "message.sent",      "data": {...message...}}
#   {"type": "typing.indicator",  "data": {"user_id": "...", "is_typing": true}}
#   {"type": "action.requested",  "data": {...action...}}
#   {"type": "action.completed",  "data": {...action...}}
#   {"type": "error",             "data": {"detail": "..."}}
# ---------------------------------------------------------------------------


async def _send_json(ws: WebSocket, msg_type: str, data: Any = None) -> None:
    """Helper to send a typed JSON frame."""
    payload: dict[str, Any] = {"type": msg_type}
    if data is not None:
        payload["data"] = data
    await ws.send_json(payload)


async def _handle_message_send(
    ws: WebSocket,
    conversation_id: UUID,
    user: User,
    payload: dict[str, Any],
    db: AsyncSession,
) -> None:
    """Process an inbound message.send event."""
    from autonomocx.services.messages import send_message

    content = payload.get("content", "")
    content_type = payload.get("content_type", "text")

    if not content:
        await _send_json(ws, "error", {"detail": "Empty message content"})
        return

    result = await send_message(
        db,
        conversation_id=conversation_id,
        org_id=user.org_id,
        content=content,
        content_type=content_type,
        role="customer",
        metadata=payload.get("metadata"),
    )

    # Broadcast the user message to all participants
    await _manager.broadcast(
        conversation_id,
        {"type": "message.new", "data": _serialize_message(result["user_message"])},
    )

    # If an AI reply was generated, broadcast it too
    if result.get("assistant_message") is not None:
        await _manager.broadcast(
            conversation_id,
            {
                "type": "message.new",
                "data": _serialize_message(result["assistant_message"]),
            },
        )

    # Confirm to sender
    await _send_json(
        ws,
        "message.sent",
        _serialize_message(result["user_message"]),
    )


async def _handle_typing(
    ws: WebSocket,
    conversation_id: UUID,
    user: User,
    is_typing: bool,
) -> None:
    """Broadcast a typing indicator to all other participants."""
    await _manager.broadcast(
        conversation_id,
        {
            "type": "typing.indicator",
            "data": {
                "user_id": str(user.id),
                "user_name": user.full_name,
                "is_typing": is_typing,
            },
        },
        exclude_ws=ws,
    )


def _serialize_message(msg: Any) -> dict[str, Any]:
    """Convert a Message ORM object (or dict) to a JSON-safe dict."""
    if isinstance(msg, dict):
        return msg
    return {
        "id": str(msg.id),
        "conversation_id": str(msg.conversation_id),
        "role": msg.role.value if hasattr(msg.role, "value") else msg.role,
        "content": msg.content,
        "content_type": (
            msg.content_type.value if hasattr(msg.content_type, "value") else msg.content_type
        ),
        "created_at": msg.created_at.isoformat() if msg.created_at else None,
    }


# ---------------------------------------------------------------------------
# WebSocket endpoint
# ---------------------------------------------------------------------------


@router.websocket("/ws/{conversation_id}")
async def websocket_chat(
    websocket: WebSocket,
    conversation_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Real-time chat WebSocket for a specific conversation.

    Authentication is performed via a ``token`` query parameter.
    Protocol messages are JSON objects with a ``type`` field.
    """
    # --- authenticate -------------------------------------------------------
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    try:
        user = await get_current_user_ws(token=token, db=db)
    except Exception:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    # --- verify conversation access -----------------------------------------
    convo = await get_conversation_by_id(
        db,
        conversation_id=conversation_id,
        org_id=user.org_id,
    )
    if convo is None:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    # --- accept & register --------------------------------------------------
    await websocket.accept()
    await _manager.connect(conversation_id, websocket)

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                await _send_json(websocket, "error", {"detail": "Invalid JSON"})
                continue

            msg_type = payload.get("type", "")

            if msg_type == "message.send":
                await _handle_message_send(websocket, conversation_id, user, payload, db)
            elif msg_type == "typing.start":
                await _handle_typing(websocket, conversation_id, user, True)
            elif msg_type == "typing.stop":
                await _handle_typing(websocket, conversation_id, user, False)
            elif msg_type == "message.read":
                # Acknowledge silently -- persistence handled elsewhere
                pass
            else:
                await _send_json(
                    websocket,
                    "error",
                    {"detail": f"Unknown message type: {msg_type}"},
                )

    except WebSocketDisconnect:
        logger.info(
            "WebSocket disconnected: user=%s conversation=%s",
            user.id,
            conversation_id,
        )
    except Exception:
        logger.exception(
            "WebSocket error: user=%s conversation=%s",
            user.id,
            conversation_id,
        )
    finally:
        await _manager.disconnect(conversation_id, websocket)
