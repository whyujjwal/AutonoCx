"""Main API router aggregation.

Imports all v1 routers and includes them under the ``/api/v1`` prefix.
"""

from __future__ import annotations

from fastapi import APIRouter

from autonomocx.api.v1 import (
    actions,
    agents,
    analytics,
    audit,
    auth,
    channels,
    chat,
    connectors,
    conversations,
    knowledge,
    messages,
    organizations,
    prompts,
    tools,
    users,
    webhooks,
    workflows,
)

# ---------------------------------------------------------------------------
# v1 sub-router -- groups all versioned endpoints
# ---------------------------------------------------------------------------

v1_router = APIRouter(prefix="/v1")

# Auth (no additional prefix -- auth.py already defines /auth)
v1_router.include_router(auth.router)

# Users
v1_router.include_router(users.router)

# Organizations
v1_router.include_router(organizations.router)

# Conversations
v1_router.include_router(conversations.router)

# Messages (nested under /conversations/{id}/messages, prefix defined in messages.py)
v1_router.include_router(messages.router)

# Agents
v1_router.include_router(agents.router)

# Tools
v1_router.include_router(tools.router)

# Actions (HITL queue)
v1_router.include_router(actions.router)

# Knowledge bases & documents
v1_router.include_router(knowledge.router)

# Workflows
v1_router.include_router(workflows.router)

# Channels
v1_router.include_router(channels.router)

# Prompts & versions
v1_router.include_router(prompts.router)

# Analytics & reporting
v1_router.include_router(analytics.router)

# Audit logs
v1_router.include_router(audit.router)

# Real-time chat (WebSocket)
v1_router.include_router(chat.router)

# Inbound webhooks
v1_router.include_router(webhooks.router)

# Connectors (CRM integrations)
v1_router.include_router(connectors.router)

# ---------------------------------------------------------------------------
# Top-level API router
# ---------------------------------------------------------------------------

api_router = APIRouter(prefix="/api")
api_router.include_router(v1_router)
