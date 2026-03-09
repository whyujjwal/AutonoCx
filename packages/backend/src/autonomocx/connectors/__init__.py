"""Pluggable connector registry for external system integrations."""

from .base import BaseConnector, ConnectorOperation, ConnectorResult, ConnectorStatus
from .registry import ConnectorRegistry

__all__ = [
    "BaseConnector",
    "ConnectorOperation",
    "ConnectorResult",
    "ConnectorStatus",
    "ConnectorRegistry",
]
