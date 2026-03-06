"""Tool (external API / integration) management service."""

from __future__ import annotations

import uuid
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from autonomocx.core.exceptions import ConflictError, NotFoundError, ValidationError
from autonomocx.models.tool import RiskLevel, Tool

logger = structlog.get_logger(__name__)


async def list_tools(
    db: AsyncSession,
    org_id: uuid.UUID,
) -> list[Tool]:
    """Return all tools belonging to *org_id*, ordered by name."""
    stmt = (
        select(Tool)
        .where(Tool.org_id == org_id)
        .order_by(Tool.name)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_tool(
    db: AsyncSession,
    tool_id: uuid.UUID,
) -> Tool:
    """Return a single tool.  Raises ``NotFoundError`` if missing."""
    result = await db.execute(select(Tool).where(Tool.id == tool_id))
    tool = result.scalar_one_or_none()
    if tool is None:
        raise NotFoundError(f"Tool {tool_id} not found.")
    return tool


async def create_tool(
    db: AsyncSession,
    org_id: uuid.UUID,
    data: dict,
) -> Tool:
    """Register a new tool.

    Raises ``ConflictError`` if a tool with the same (org, name, version)
    already exists.
    """
    existing = await db.execute(
        select(Tool).where(
            Tool.org_id == org_id,
            Tool.name == data["name"],
            Tool.version == data.get("version", "1.0.0"),
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise ConflictError(
            f"Tool '{data['name']}' v{data.get('version', '1.0.0')} already exists."
        )

    tool = Tool(
        org_id=org_id,
        name=data["name"],
        display_name=data.get("display_name"),
        description=data.get("description"),
        category=data.get("category"),
        parameters_schema=data.get("parameters_schema", {}),
        endpoint_url=data.get("endpoint_url"),
        http_method=data.get("http_method", "POST"),
        headers_template=data.get("headers_template", {}),
        auth_type=data.get("auth_type"),
        auth_config=data.get("auth_config", {}),
        timeout_seconds=data.get("timeout_seconds", 30),
        retry_config=data.get("retry_config", {}),
        risk_level=data.get("risk_level", RiskLevel.LOW),
        requires_approval=data.get("requires_approval", False),
        is_active=data.get("is_active", True),
        is_builtin=False,
        version=data.get("version", "1.0.0"),
    )
    db.add(tool)
    await db.flush()

    logger.info("tool_created", tool_id=str(tool.id), name=tool.name)
    return tool


async def update_tool(
    db: AsyncSession,
    tool_id: uuid.UUID,
    data: dict,
) -> Tool:
    """Partially update a tool definition."""
    tool = await get_tool(db, tool_id)

    if tool.is_builtin:
        raise ValidationError("Built-in tools cannot be modified.")

    updatable = (
        "display_name", "description", "category", "parameters_schema",
        "endpoint_url", "http_method", "headers_template", "auth_type",
        "auth_config", "timeout_seconds", "retry_config", "risk_level",
        "requires_approval", "is_active",
    )
    for field in updatable:
        if field in data:
            setattr(tool, field, data[field])

    db.add(tool)
    await db.flush()

    logger.info("tool_updated", tool_id=str(tool.id))
    return tool


async def delete_tool(
    db: AsyncSession,
    tool_id: uuid.UUID,
) -> None:
    """Soft-delete a tool by deactivating it.

    Built-in tools cannot be deleted.
    """
    tool = await get_tool(db, tool_id)

    if tool.is_builtin:
        raise ValidationError("Built-in tools cannot be deleted.")

    tool.is_active = False
    db.add(tool)
    await db.flush()

    logger.info("tool_deleted", tool_id=str(tool.id))


async def test_tool(
    db: AsyncSession,
    tool_id: uuid.UUID,
    parameters: dict[str, Any],
) -> dict[str, Any]:
    """Execute a dry-run invocation of a tool with the given *parameters*.

    Returns a ``ToolTestResponse``-compatible dict with either the result
    payload or an error description.
    """
    tool = await get_tool(db, tool_id)

    if not tool.is_active:
        raise ValidationError("Cannot test an inactive tool.")

    # TODO: Wire up actual HTTP invocation through the tool executor.
    # For now we validate the schema and return a diagnostic response.

    # Basic schema validation against parameters_schema if present
    errors: list[str] = []
    if tool.parameters_schema:
        required = tool.parameters_schema.get("required", [])
        for req in required:
            if req not in parameters:
                errors.append(f"Missing required parameter: {req}")

    if errors:
        return {
            "tool_id": str(tool.id),
            "tool_name": tool.name,
            "success": False,
            "errors": errors,
            "response": None,
            "latency_ms": 0,
        }

    response = {
        "tool_id": str(tool.id),
        "tool_name": tool.name,
        "success": True,
        "errors": [],
        "response": {
            "message": (
                f"[Test mode] Tool '{tool.name}' validated successfully. "
                "HTTP execution pending full pipeline integration."
            ),
            "endpoint_url": tool.endpoint_url,
            "http_method": tool.http_method,
            "parameters_received": parameters,
        },
        "latency_ms": 0,
    }

    logger.info("tool_tested", tool_id=str(tool.id), success=True)
    return response
