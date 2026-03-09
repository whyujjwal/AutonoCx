"""CRM connector configuration and management endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from autonomocx.connectors import ConnectorRegistry
from autonomocx.core.database import get_db
from autonomocx.core.dependencies import get_current_user, require_role
from autonomocx.models.user import User, UserRole
from autonomocx.schemas.connector import (
    ConnectorAvailableOut,
    ConnectorConfigureRequest,
    ConnectorHealthResponse,
    ConnectorOperationOut,
    ConnectorOut,
)
from autonomocx.services.connector_service import (
    configure_connector,
    list_connectors,
    remove_connector,
    test_connector,
)

router = APIRouter(prefix="/connectors", tags=["connectors"])

# Module-level registry reference set during app startup
_registry: ConnectorRegistry | None = None


def set_registry(registry: ConnectorRegistry) -> None:
    """Called from app lifespan to inject the registry."""
    global _registry  # noqa: PLW0603
    _registry = registry


def _get_registry() -> ConnectorRegistry:
    if _registry is None:
        raise RuntimeError("ConnectorRegistry not initialised")
    return _registry


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get(
    "/available",
    response_model=list[ConnectorAvailableOut],
    summary="List available connector types",
)
async def available_types(
    _: User = Depends(get_current_user),
) -> list[ConnectorAvailableOut]:
    """Return connector types that can be configured."""
    registry = _get_registry()
    return [
        ConnectorAvailableOut(**t)
        for t in registry.list_available_types()
    ]


@router.get(
    "/",
    response_model=list[ConnectorOut],
    summary="List configured connectors",
)
async def list_configured(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ConnectorOut]:
    """Return connectors configured for the current organization."""
    configs = await list_connectors(db, org_id=current_user.org_id)
    return [ConnectorOut.model_validate(c) for c in configs]


@router.post(
    "/{connector_type}/configure",
    response_model=ConnectorOut,
    status_code=status.HTTP_201_CREATED,
    summary="Configure a connector",
    dependencies=[
        Depends(require_role(UserRole.ADMIN, UserRole.DEVELOPER))
    ],
)
async def configure(
    connector_type: str,
    body: ConnectorConfigureRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ConnectorOut:
    """Configure (or reconfigure) a CRM connector.

    Validates credentials by running a health check.
    Automatically syncs connector operations as AI-callable tools.
    """
    registry = _get_registry()
    try:
        cc = await configure_connector(
            db,
            org_id=current_user.org_id,
            connector_type=connector_type,
            config=body.config,
            display_name=body.display_name,
            registry=registry,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    return ConnectorOut.model_validate(cc)


@router.delete(
    "/{connector_type}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove a connector",
    dependencies=[
        Depends(require_role(UserRole.ADMIN, UserRole.DEVELOPER))
    ],
)
async def remove(
    connector_type: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Deactivate a connector and its associated tools."""
    registry = _get_registry()
    found = await remove_connector(
        db,
        org_id=current_user.org_id,
        connector_type=connector_type,
        registry=registry,
    )
    if not found:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No connector '{connector_type}' configured",
        )


@router.post(
    "/{connector_type}/test",
    response_model=ConnectorHealthResponse,
    summary="Test connector health",
)
async def health_check(
    connector_type: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ConnectorHealthResponse:
    """Run a health check on a configured connector."""
    registry = _get_registry()
    result = await test_connector(
        db,
        org_id=current_user.org_id,
        connector_type=connector_type,
        registry=registry,
    )
    return ConnectorHealthResponse(**result)


@router.get(
    "/{connector_type}/operations",
    response_model=list[ConnectorOperationOut],
    summary="List connector operations",
)
async def get_operations(
    connector_type: str,
    current_user: User = Depends(get_current_user),
) -> list[ConnectorOperationOut]:
    """Return the operations exposed by a connector type."""
    registry = _get_registry()
    connector = registry.get_connector(
        current_user.org_id, connector_type
    )
    if connector is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Connector '{connector_type}' not active",
        )
    return [
        ConnectorOperationOut(
            name=op.name,
            display_name=op.display_name,
            description=op.description,
            parameters_schema=op.parameters_schema,
            risk_level=op.risk_level,
            requires_approval=op.requires_approval,
        )
        for op in connector.get_operations()
    ]
