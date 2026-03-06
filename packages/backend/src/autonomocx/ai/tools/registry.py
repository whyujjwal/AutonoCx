"""Tool definition registry -- manages available tools and formats them for LLM calls."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from typing import Any

import structlog
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from autonomocx.models.tool import Tool

logger = structlog.get_logger(__name__)


class ToolRegistry:
    """Discover, register, and format tool definitions.

    Tools are stored in the ``tools`` database table.  This class provides
    a high-level interface for the orchestrator to query which tools an
    agent has access to and to format them for the LLM's function-calling
    protocol.
    """

    # In-memory cache of builtin tool handlers (name -> callable)
    _builtin_handlers: dict[str, Any] = {}

    @classmethod
    def register_builtin(cls, name: str, handler: Any) -> None:
        """Register a built-in tool handler (typically at application startup)."""
        cls._builtin_handlers[name] = handler
        logger.info("tool_registered", name=name, builtin=True)

    @classmethod
    def get_builtin_handler(cls, name: str) -> Any | None:
        return cls._builtin_handlers.get(name)

    # ------------------------------------------------------------------
    # Database queries
    # ------------------------------------------------------------------

    async def get_tool(
        self,
        db: AsyncSession,
        name: str,
        org_id: uuid.UUID,
    ) -> Tool | None:
        """Look up a single tool by name within an organisation."""
        stmt = (
            select(Tool)
            .where(
                and_(
                    Tool.org_id == org_id,
                    Tool.name == name,
                    Tool.is_active == True,  # noqa: E712
                )
            )
            .limit(1)
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_tools_by_ids(
        self,
        db: AsyncSession,
        tool_ids: list[uuid.UUID],
    ) -> Sequence[Tool]:
        """Return active tools matching the given IDs."""
        if not tool_ids:
            return []
        stmt = select(Tool).where(
            and_(
                Tool.id.in_(tool_ids),
                Tool.is_active == True,  # noqa: E712
            )
        )
        result = await db.execute(stmt)
        return result.scalars().all()

    async def get_tools_for_agent(
        self,
        db: AsyncSession,
        agent_config: Any,
    ) -> Sequence[Tool]:
        """Return all tools enabled for a given agent."""
        tool_ids = getattr(agent_config, "tools_enabled", None)
        if not tool_ids:
            return []
        return await self.get_tools_by_ids(db, tool_ids)

    # ------------------------------------------------------------------
    # LLM formatting
    # ------------------------------------------------------------------

    def format_for_llm(self, tools: Sequence[Tool]) -> list[dict[str, Any]]:
        """Convert a list of Tool ORM objects to OpenAI function-calling format.

        Each entry looks like::

            {
                "type": "function",
                "function": {
                    "name": "process_refund",
                    "description": "Process a refund for an order.",
                    "parameters": { ... JSON Schema ... }
                }
            }
        """
        formatted: list[dict[str, Any]] = []
        for tool in tools:
            schema = tool.parameters_schema or {"type": "object", "properties": {}}
            formatted.append(
                {
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description or "",
                        "parameters": schema,
                    },
                }
            )
        return formatted
