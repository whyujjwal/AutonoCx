"""Connector configuration management service."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

import structlog
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from autonomocx.connectors import ConnectorRegistry, ConnectorStatus
from autonomocx.core.exceptions import NotFoundError, ValidationError
from autonomocx.models.connector import ConnectorConfig
from autonomocx.models.tool import Tool

logger = structlog.get_logger(__name__)


async def configure_connector(
    db: AsyncSession,
    *,
    org_id: uuid.UUID,
    connector_type: str,
    config: dict[str, Any],
    display_name: str | None = None,
    registry: ConnectorRegistry,
) -> ConnectorConfig:
    """Configure (or reconfigure) a connector for an organization.

    1. Validate connector type exists in registry.
    2. Initialize a live connector instance (validates credentials).
    3. Persist config to database.
    4. Sync tools from connector operations.
    """
    # Verify connector type is registered
    available = [t["connector_type"] for t in registry.list_available_types()]
    if connector_type not in available:
        raise ValidationError(
            f"Unknown connector type: {connector_type}. "
            f"Available: {', '.join(available)}"
        )

    # Initialize connector (this validates credentials)
    connector = await registry.initialize_connector(
        org_id, connector_type, config
    )

    # Health check
    status = await connector.health_check()

    # Upsert ConnectorConfig
    result = await db.execute(
        select(ConnectorConfig).where(
            ConnectorConfig.org_id == org_id,
            ConnectorConfig.connector_type == connector_type,
        )
    )
    cc = result.scalar_one_or_none()

    if cc is None:
        cc = ConnectorConfig(
            org_id=org_id,
            connector_type=connector_type,
            display_name=display_name or connector.display_name,
            config=config,
            is_active=True,
            status=status.value,
            last_health_check_at=datetime.now(UTC),
        )
        db.add(cc)
    else:
        cc.config = config
        cc.display_name = display_name or connector.display_name
        cc.is_active = True
        cc.status = status.value
        cc.last_health_check_at = datetime.now(UTC)
        cc.error_message = None

    await db.flush()

    # Sync tools from connector operations
    await registry.sync_tools(db, org_id, connector)

    logger.info(
        "connector_configured",
        org_id=str(org_id),
        connector_type=connector_type,
        status=status.value,
    )
    return cc


async def list_connectors(
    db: AsyncSession,
    *,
    org_id: uuid.UUID,
) -> list[ConnectorConfig]:
    """Return all configured connectors for an organization."""
    result = await db.execute(
        select(ConnectorConfig)
        .where(ConnectorConfig.org_id == org_id)
        .order_by(ConnectorConfig.connector_type)
    )
    return list(result.scalars().all())


async def remove_connector(
    db: AsyncSession,
    *,
    org_id: uuid.UUID,
    connector_type: str,
    registry: ConnectorRegistry,
) -> bool:
    """Deactivate a connector and its associated tools.

    Returns True if the connector was found and deactivated.
    """
    result = await db.execute(
        select(ConnectorConfig).where(
            ConnectorConfig.org_id == org_id,
            ConnectorConfig.connector_type == connector_type,
        )
    )
    cc = result.scalar_one_or_none()
    if cc is None:
        return False

    # Deactivate connector config
    cc.is_active = False
    cc.status = ConnectorStatus.DISCONNECTED.value

    # Deactivate associated tools
    await db.execute(
        update(Tool)
        .where(
            Tool.org_id == org_id,
            Tool.connector_type == connector_type,
        )
        .values(is_active=False)
    )

    await db.flush()

    # Remove from registry
    await registry.remove_connector(org_id, connector_type)

    logger.info(
        "connector_removed",
        org_id=str(org_id),
        connector_type=connector_type,
    )
    return True


async def test_connector(
    db: AsyncSession,
    *,
    org_id: uuid.UUID,
    connector_type: str,
    registry: ConnectorRegistry,
) -> dict[str, str | None]:
    """Run a health check on a configured connector.

    Returns ``{"status": ..., "error": ...}``.
    """
    connector = registry.get_connector(org_id, connector_type)
    if connector is None:
        # Try to load from DB and re-initialize
        result = await db.execute(
            select(ConnectorConfig).where(
                ConnectorConfig.org_id == org_id,
                ConnectorConfig.connector_type == connector_type,
                ConnectorConfig.is_active.is_(True),
            )
        )
        cc = result.scalar_one_or_none()
        if cc is None:
            raise NotFoundError(
                f"No active connector of type '{connector_type}' "
                f"found for this organization."
            )
        connector = await registry.initialize_connector(
            org_id, connector_type, cc.config or {}
        )

    status = await connector.health_check()
    error_msg: str | None = None
    if status == ConnectorStatus.ERROR:
        error_msg = "Health check failed"

    # Update status in DB
    await db.execute(
        update(ConnectorConfig)
        .where(
            ConnectorConfig.org_id == org_id,
            ConnectorConfig.connector_type == connector_type,
        )
        .values(
            status=status.value,
            last_health_check_at=datetime.now(UTC),
            error_message=error_msg,
        )
    )
    await db.flush()

    return {
        "connector_type": connector_type,
        "status": status.value,
        "error": error_msg,
    }
