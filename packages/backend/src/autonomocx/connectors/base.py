"""Abstract base class and shared data types for all connectors.

Every connector adapter must subclass ``BaseConnector`` and implement
the four abstract methods.  The ``ConnectorOperation`` and
``ConnectorResult`` frozen dataclasses provide a connector-agnostic
contract so the orchestration engine does not need to know which
external system is backing a given tool.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class ConnectorStatus(StrEnum):
    """Health-check status for a connector instance."""

    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"


@dataclass(frozen=True, slots=True)
class ConnectorOperation:
    """Descriptor for a single operation exposed by a connector.

    Each operation maps 1-to-1 with a ``Tool`` row so the agent can
    invoke it via the standard tool-calling pipeline.
    """

    name: str
    display_name: str
    description: str
    parameters_schema: dict[str, Any]
    risk_level: str = "low"
    requires_approval: bool = False


@dataclass(frozen=True, slots=True)
class ConnectorResult:
    """Outcome of executing a connector operation.

    ``data`` carries the parsed response on success; ``error`` carries
    a human-readable message on failure.  ``raw_response`` preserves the
    unprocessed API payload for audit / debugging.
    """

    success: bool
    data: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    raw_response: dict[str, Any] | None = None


class BaseConnector(ABC):
    """Abstract base class for external-system connectors.

    Subclasses must set ``connector_type`` and ``display_name`` at the
    class level and implement the four abstract lifecycle methods.
    """

    connector_type: str = "base"
    display_name: str = "Base Connector"

    @abstractmethod
    async def initialize(self, config: dict[str, Any]) -> None:
        """Bootstrap the connector with vendor-specific credentials.

        Implementations should validate required keys and establish
        any persistent HTTP clients or SDK sessions.
        """
        ...

    @abstractmethod
    async def health_check(self) -> ConnectorStatus:
        """Return the current connectivity status."""
        ...

    @abstractmethod
    def get_operations(self) -> list[ConnectorOperation]:
        """Return every operation this connector can perform."""
        ...

    @abstractmethod
    async def execute_operation(
        self,
        operation_name: str,
        parameters: dict[str, Any],
    ) -> ConnectorResult:
        """Execute *operation_name* with the given *parameters*.

        Implementations must never raise; they should catch vendor
        exceptions and wrap them in a ``ConnectorResult(success=False)``.
        """
        ...

    async def close(self) -> None:
        """Release resources (HTTP clients, open sockets, etc.).

        Override in subclasses that hold persistent connections.
        """
