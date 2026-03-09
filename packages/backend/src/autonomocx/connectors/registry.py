"""Singleton registry that manages connector types, instances, and tool mappings.

The registry serves three purposes:

1. **Type catalogue** -- connector classes register themselves so the
   platform knows which integrations are available.
2. **Instance lifecycle** -- per-org connector instances are created,
   cached, and torn down here.
3. **Tool synchronisation** -- each connector's operations are synced
   into the ``tools`` table so the agent can discover and invoke them
   through the standard tool-calling pipeline.
"""

from __future__ import annotations

import uuid
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from autonomocx.models.tool import RiskLevel, Tool

from .base import BaseConnector, ConnectorOperation

logger = structlog.get_logger(__name__)

# Map string risk levels from ConnectorOperation to the RiskLevel enum
_RISK_MAP: dict[str, RiskLevel] = {
    "low": RiskLevel.LOW,
    "medium": RiskLevel.MEDIUM,
    "high": RiskLevel.HIGH,
    "critical": RiskLevel.CRITICAL,
}


class ConnectorRegistry:
    """Central registry for connector types and live instances.

    Typical startup flow::

        registry = ConnectorRegistry()
        registry.register_type("zendesk", ZendeskConnector)
        connector = await registry.initialize_connector(org_id, "zendesk", config)
        tools = await registry.sync_tools(db, org_id, connector)
    """

    # Class-level catalogue of connector implementations keyed by type string.
    _connector_types: dict[str, type[BaseConnector]] = {}

    def __init__(self) -> None:
        # Per-org live instances: (org_id, connector_type) -> instance
        self._instances: dict[tuple[uuid.UUID, str], BaseConnector] = {}
        # Tool-name resolution: (org_id, tool_name) -> (connector_type, operation_name)
        self._tool_mappings: dict[tuple[uuid.UUID, str], tuple[str, str]] = {}

    # ------------------------------------------------------------------
    # Type catalogue
    # ------------------------------------------------------------------

    @classmethod
    def register_type(cls, connector_type: str, connector_cls: type[BaseConnector]) -> None:
        """Register a connector class so it can be instantiated later."""
        cls._connector_types[connector_type] = connector_cls
        logger.info("connector_type_registered", connector_type=connector_type)

    @classmethod
    def list_available_types(cls) -> list[dict[str, str]]:
        """Return a summary of every registered connector type."""
        return [
            {"connector_type": ct, "display_name": klass.display_name}
            for ct, klass in cls._connector_types.items()
        ]

    # ------------------------------------------------------------------
    # Instance lifecycle
    # ------------------------------------------------------------------

    async def initialize_connector(
        self,
        org_id: uuid.UUID,
        connector_type: str,
        config: dict[str, Any],
    ) -> BaseConnector:
        """Create, initialise, and cache a connector instance for *org_id*."""
        connector_cls = self._connector_types.get(connector_type)
        if connector_cls is None:
            msg = f"Unknown connector type: {connector_type}"
            raise ValueError(msg)

        connector = connector_cls()
        await connector.initialize(config)

        self._instances[(org_id, connector_type)] = connector
        logger.info(
            "connector_initialized",
            org_id=str(org_id),
            connector_type=connector_type,
        )
        return connector

    def get_connector(
        self,
        org_id: uuid.UUID,
        connector_type: str,
    ) -> BaseConnector | None:
        """Return a cached connector instance, or ``None``."""
        return self._instances.get((org_id, connector_type))

    def get_for_tool(
        self,
        org_id: uuid.UUID,
        tool_name: str,
    ) -> tuple[BaseConnector, str] | None:
        """Resolve *tool_name* to its backing connector and operation name.

        Returns ``(connector_instance, operation_name)`` or ``None`` if the
        tool is not backed by a connector for this organisation.
        """
        mapping = self._tool_mappings.get((org_id, tool_name))
        if mapping is None:
            return None

        connector_type, operation_name = mapping
        connector = self._instances.get((org_id, connector_type))
        if connector is None:
            return None

        return connector, operation_name

    # ------------------------------------------------------------------
    # Tool synchronisation
    # ------------------------------------------------------------------

    async def sync_tools(
        self,
        db: AsyncSession,
        org_id: uuid.UUID,
        connector: BaseConnector,
    ) -> list[Tool]:
        """Upsert a ``Tool`` row for every operation the connector exposes.

        Returns the list of created / updated ``Tool`` instances.
        """
        operations = connector.get_operations()
        tools: list[Tool] = []

        for op in operations:
            tool = await self._upsert_tool(db, org_id, connector.connector_type, op)
            tools.append(tool)
            self._tool_mappings[(org_id, op.name)] = (connector.connector_type, op.name)

        await db.flush()
        logger.info(
            "connector_tools_synced",
            org_id=str(org_id),
            connector_type=connector.connector_type,
            tool_count=len(tools),
        )
        return tools

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    async def remove_connector(
        self,
        org_id: uuid.UUID,
        connector_type: str,
    ) -> None:
        """Close and discard a connector instance, clearing its tool mappings."""
        key = (org_id, connector_type)
        connector = self._instances.pop(key, None)
        if connector is not None:
            await connector.close()

        # Purge tool mappings that pointed to this connector
        stale_keys = [
            k
            for k, (ct, _) in self._tool_mappings.items()
            if k[0] == org_id and ct == connector_type
        ]
        for k in stale_keys:
            del self._tool_mappings[k]

        logger.info(
            "connector_removed",
            org_id=str(org_id),
            connector_type=connector_type,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    async def _upsert_tool(
        db: AsyncSession,
        org_id: uuid.UUID,
        connector_type: str,
        op: ConnectorOperation,
    ) -> Tool:
        """Create or update a ``Tool`` row for a single connector operation."""
        stmt = select(Tool).where(
            Tool.org_id == org_id,
            Tool.name == op.name,
            Tool.version == "1.0.0",
        )
        result = await db.execute(stmt)
        tool = result.scalar_one_or_none()

        risk = _RISK_MAP.get(op.risk_level, RiskLevel.LOW)

        if tool is not None:
            tool.display_name = op.display_name
            tool.description = op.description
            tool.parameters_schema = op.parameters_schema
            tool.risk_level = risk
            tool.requires_approval = op.requires_approval
            tool.is_active = True
            tool.is_builtin = False
            tool.category = "connector"
            tool.connector_type = connector_type
        else:
            tool = Tool(
                org_id=org_id,
                name=op.name,
                display_name=op.display_name,
                description=op.description,
                category="connector",
                parameters_schema=op.parameters_schema,
                risk_level=risk,
                requires_approval=op.requires_approval,
                is_active=True,
                is_builtin=False,
                version="1.0.0",
                auth_type=connector_type,
            )
            db.add(tool)

        await db.flush()
        return tool
