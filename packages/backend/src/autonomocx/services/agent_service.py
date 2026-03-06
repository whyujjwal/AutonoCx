"""Agent configuration service."""

from __future__ import annotations

import uuid
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from autonomocx.core.exceptions import NotFoundError, ValidationError
from autonomocx.models.agent import AgentConfig

logger = structlog.get_logger(__name__)


async def list_agents(
    db: AsyncSession,
    org_id: uuid.UUID,
) -> list[AgentConfig]:
    """Return all agents belonging to *org_id*."""
    stmt = select(AgentConfig).where(AgentConfig.org_id == org_id).order_by(AgentConfig.name)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_agent(
    db: AsyncSession,
    agent_id: uuid.UUID,
) -> AgentConfig:
    """Return a single agent.  Raises ``NotFoundError`` if missing."""
    result = await db.execute(select(AgentConfig).where(AgentConfig.id == agent_id))
    agent = result.scalar_one_or_none()
    if agent is None:
        raise NotFoundError(f"Agent {agent_id} not found.")
    return agent


async def create_agent(
    db: AsyncSession,
    org_id: uuid.UUID,
    data: dict,
) -> AgentConfig:
    """Create a new agent configuration."""
    agent = AgentConfig(
        org_id=org_id,
        name=data["name"],
        description=data.get("description"),
        system_prompt=data.get("system_prompt"),
        llm_provider=data.get("llm_provider"),
        llm_model=data.get("llm_model"),
        temperature=data.get("temperature"),
        max_tokens=data.get("max_tokens"),
        tools_enabled=data.get("tools_enabled", []),
        fallback_agent_id=data.get("fallback_agent_id"),
        is_active=data.get("is_active", True),
        metadata_=data.get("metadata", {}),
    )
    db.add(agent)
    await db.flush()

    logger.info("agent_created", agent_id=str(agent.id), name=agent.name)
    return agent


async def update_agent(
    db: AsyncSession,
    agent_id: uuid.UUID,
    data: dict,
) -> AgentConfig:
    """Partially update an agent's configuration."""
    agent = await get_agent(db, agent_id)

    updatable = (
        "name",
        "description",
        "system_prompt",
        "llm_provider",
        "llm_model",
        "temperature",
        "max_tokens",
        "tools_enabled",
        "fallback_agent_id",
        "is_active",
        "metadata_",
    )
    for field in updatable:
        if field in data:
            setattr(agent, field, data[field])

    db.add(agent)
    await db.flush()

    logger.info("agent_updated", agent_id=str(agent.id))
    return agent


async def delete_agent(
    db: AsyncSession,
    agent_id: uuid.UUID,
) -> None:
    """Soft-delete an agent by deactivating it.

    Hard deletion is avoided because conversations reference the agent.
    """
    agent = await get_agent(db, agent_id)
    agent.is_active = False
    db.add(agent)
    await db.flush()

    logger.info("agent_deleted", agent_id=str(agent.id))


async def test_agent(
    db: AsyncSession,
    agent_id: uuid.UUID,
    message: str,
) -> dict[str, Any]:
    """Send a test message to an agent and return the response.

    Returns an ``AgentTestResponse``-compatible dict with the generated
    reply, model info, and token usage.
    """
    agent = await get_agent(db, agent_id)

    if not agent.is_active:
        raise ValidationError("Cannot test an inactive agent.")

    # TODO: Wire up actual LLM call through the orchestrator.
    # For now return a diagnostic payload so callers can verify connectivity.
    response = {
        "agent_id": str(agent.id),
        "agent_name": agent.name,
        "input_message": message,
        "response": (
            f"[Test mode] Agent '{agent.name}' received your message. "
            "AI pipeline integration pending."
        ),
        "llm_provider": agent.llm_provider,
        "llm_model": agent.llm_model,
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "latency_ms": 0,
    }

    logger.info("agent_tested", agent_id=str(agent.id))
    return response
