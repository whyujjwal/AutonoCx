"""Zendesk connector -- ticket management, contact search, and comments.

Provides five operations:

- ``zendesk_lookup_ticket``       -- fetch a single ticket by ID
- ``zendesk_create_ticket``       -- create a new ticket
- ``zendesk_update_ticket``       -- update an existing ticket (requires approval)
- ``zendesk_search_contacts``     -- search users by query string
- ``zendesk_list_ticket_comments`` -- list comments on a ticket
"""

from __future__ import annotations

import base64
from typing import Any

import httpx
import structlog

from .base import BaseConnector, ConnectorOperation, ConnectorResult, ConnectorStatus

logger = structlog.get_logger(__name__)


class ZendeskConnector(BaseConnector):
    """Connector adapter for the Zendesk Support REST API (v2)."""

    connector_type: str = "zendesk"
    display_name: str = "Zendesk"

    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None
        self._base_url: str = ""
        self._auth_header: str = ""

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def initialize(self, config: dict[str, Any]) -> None:
        """Configure the HTTP client with Zendesk credentials.

        Required keys in *config*:
            - ``subdomain``  -- Zendesk subdomain (e.g. ``"acme"``)
            - ``email``      -- agent email address
            - ``api_token``  -- Zendesk API token
        """
        subdomain: str = config["subdomain"]
        email: str = config["email"]
        api_token: str = config["api_token"]

        self._base_url = f"https://{subdomain}.zendesk.com"

        raw_credentials = f"{email}/token:{api_token}"
        auth = base64.b64encode(raw_credentials.encode()).decode()
        self._auth_header = f"Basic {auth}"

        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            headers={
                "Authorization": self._auth_header,
                "Content-Type": "application/json",
            },
            timeout=30.0,
        )
        logger.info("zendesk_initialized", subdomain=subdomain)

    async def health_check(self) -> ConnectorStatus:
        """Verify connectivity by hitting the ``/api/v2/users/me.json`` endpoint."""
        if self._client is None:
            return ConnectorStatus.DISCONNECTED

        try:
            resp = await self._client.get("/api/v2/users/me.json")
            if resp.status_code == 200:
                return ConnectorStatus.CONNECTED
            logger.warning("zendesk_health_check_failed", status=resp.status_code)
            return ConnectorStatus.ERROR
        except httpx.HTTPError as exc:
            logger.error("zendesk_health_check_error", error=str(exc))
            return ConnectorStatus.ERROR

    async def close(self) -> None:
        """Close the underlying ``httpx.AsyncClient``."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    # ------------------------------------------------------------------
    # Operations catalogue
    # ------------------------------------------------------------------

    def get_operations(self) -> list[ConnectorOperation]:
        """Return the five standard Zendesk operations."""
        return [
            ConnectorOperation(
                name="zendesk_lookup_ticket",
                display_name="Lookup Zendesk Ticket",
                description="Retrieve a Zendesk support ticket by its numeric ID.",
                parameters_schema={
                    "type": "object",
                    "properties": {
                        "ticket_id": {
                            "type": "integer",
                            "description": "Zendesk ticket ID",
                        },
                    },
                    "required": ["ticket_id"],
                },
                risk_level="low",
            ),
            ConnectorOperation(
                name="zendesk_create_ticket",
                display_name="Create Zendesk Ticket",
                description="Create a new support ticket in Zendesk.",
                parameters_schema={
                    "type": "object",
                    "properties": {
                        "subject": {
                            "type": "string",
                            "description": "Ticket subject line",
                        },
                        "description": {
                            "type": "string",
                            "description": "Ticket body / first comment",
                        },
                        "priority": {
                            "type": "string",
                            "enum": ["low", "normal", "high", "urgent"],
                            "description": "Ticket priority",
                        },
                        "requester_email": {
                            "type": "string",
                            "description": "Email of the ticket requester",
                        },
                        "tags": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Tags to attach to the ticket",
                        },
                    },
                    "required": ["subject", "description"],
                },
                risk_level="medium",
            ),
            ConnectorOperation(
                name="zendesk_update_ticket",
                display_name="Update Zendesk Ticket",
                description="Update an existing Zendesk ticket (status, priority, comment, tags).",
                parameters_schema={
                    "type": "object",
                    "properties": {
                        "ticket_id": {
                            "type": "integer",
                            "description": "Zendesk ticket ID to update",
                        },
                        "status": {
                            "type": "string",
                            "enum": [
                                "new",
                                "open",
                                "pending",
                                "hold",
                                "solved",
                                "closed",
                            ],
                            "description": "New ticket status",
                        },
                        "priority": {
                            "type": "string",
                            "enum": ["low", "normal", "high", "urgent"],
                            "description": "New ticket priority",
                        },
                        "comment": {
                            "type": "string",
                            "description": "Public comment to add",
                        },
                        "tags": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Tags to set on the ticket",
                        },
                    },
                    "required": ["ticket_id"],
                },
                risk_level="medium",
                requires_approval=True,
            ),
            ConnectorOperation(
                name="zendesk_search_contacts",
                display_name="Search Zendesk Contacts",
                description="Search for Zendesk users / contacts by query string.",
                parameters_schema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query (name, email, etc.)",
                        },
                    },
                    "required": ["query"],
                },
                risk_level="low",
            ),
            ConnectorOperation(
                name="zendesk_list_ticket_comments",
                display_name="List Ticket Comments",
                description="List all comments on a Zendesk ticket.",
                parameters_schema={
                    "type": "object",
                    "properties": {
                        "ticket_id": {
                            "type": "integer",
                            "description": "Zendesk ticket ID",
                        },
                    },
                    "required": ["ticket_id"],
                },
                risk_level="low",
            ),
        ]

    # ------------------------------------------------------------------
    # Operation dispatch
    # ------------------------------------------------------------------

    async def execute_operation(
        self,
        operation_name: str,
        parameters: dict[str, Any],
    ) -> ConnectorResult:
        """Dispatch *operation_name* to the appropriate private handler."""
        handlers: dict[str, Any] = {
            "zendesk_lookup_ticket": self._lookup_ticket,
            "zendesk_create_ticket": self._create_ticket,
            "zendesk_update_ticket": self._update_ticket,
            "zendesk_search_contacts": self._search_contacts,
            "zendesk_list_ticket_comments": self._list_comments,
        }

        handler = handlers.get(operation_name)
        if handler is None:
            return ConnectorResult(
                success=False,
                error=f"Unknown operation: {operation_name}",
            )

        return await handler(parameters)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _http_error_msg(exc: httpx.HTTPStatusError) -> str:
        """Build a concise error string from an HTTP status error."""
        return f"HTTP {exc.response.status_code}: {exc.response.text}"

    # ------------------------------------------------------------------
    # Private API methods
    # ------------------------------------------------------------------

    async def _lookup_ticket(self, params: dict[str, Any]) -> ConnectorResult:
        """GET /api/v2/tickets/{ticket_id}.json"""
        assert self._client is not None  # noqa: S101
        ticket_id: int = params["ticket_id"]

        try:
            resp = await self._client.get(
                f"/api/v2/tickets/{ticket_id}.json",
            )
            resp.raise_for_status()
            data = resp.json()
            return ConnectorResult(
                success=True, data=data.get("ticket", data),
            )
        except httpx.HTTPStatusError as exc:
            logger.warning(
                "zendesk_lookup_failed",
                ticket_id=ticket_id,
                status=exc.response.status_code,
            )
            return ConnectorResult(
                success=False, error=self._http_error_msg(exc),
            )
        except httpx.HTTPError as exc:
            logger.error(
                "zendesk_lookup_error",
                ticket_id=ticket_id,
                error=str(exc),
            )
            return ConnectorResult(success=False, error=str(exc))

    async def _create_ticket(self, params: dict[str, Any]) -> ConnectorResult:
        """POST /api/v2/tickets.json"""
        assert self._client is not None  # noqa: S101

        ticket_body: dict[str, Any] = {
            "subject": params["subject"],
            "description": params["description"],
        }
        if "priority" in params:
            ticket_body["priority"] = params["priority"]
        if "requester_email" in params:
            ticket_body["requester"] = {"email": params["requester_email"]}
        if "tags" in params:
            ticket_body["tags"] = params["tags"]

        try:
            resp = await self._client.post(
                "/api/v2/tickets.json",
                json={"ticket": ticket_body},
            )
            resp.raise_for_status()
            data = resp.json()
            return ConnectorResult(
                success=True, data=data.get("ticket", data),
            )
        except httpx.HTTPStatusError as exc:
            logger.warning(
                "zendesk_create_failed",
                status=exc.response.status_code,
            )
            return ConnectorResult(
                success=False, error=self._http_error_msg(exc),
            )
        except httpx.HTTPError as exc:
            logger.error("zendesk_create_error", error=str(exc))
            return ConnectorResult(success=False, error=str(exc))

    async def _update_ticket(self, params: dict[str, Any]) -> ConnectorResult:
        """PUT /api/v2/tickets/{ticket_id}.json"""
        assert self._client is not None  # noqa: S101
        ticket_id: int = params["ticket_id"]

        ticket_body: dict[str, Any] = {}
        if "status" in params:
            ticket_body["status"] = params["status"]
        if "priority" in params:
            ticket_body["priority"] = params["priority"]
        if "comment" in params:
            ticket_body["comment"] = {
                "body": params["comment"],
                "public": True,
            }
        if "tags" in params:
            ticket_body["tags"] = params["tags"]

        try:
            resp = await self._client.put(
                f"/api/v2/tickets/{ticket_id}.json",
                json={"ticket": ticket_body},
            )
            resp.raise_for_status()
            data = resp.json()
            return ConnectorResult(
                success=True, data=data.get("ticket", data),
            )
        except httpx.HTTPStatusError as exc:
            logger.warning(
                "zendesk_update_failed",
                ticket_id=ticket_id,
                status=exc.response.status_code,
            )
            return ConnectorResult(
                success=False, error=self._http_error_msg(exc),
            )
        except httpx.HTTPError as exc:
            logger.error(
                "zendesk_update_error",
                ticket_id=ticket_id,
                error=str(exc),
            )
            return ConnectorResult(success=False, error=str(exc))

    async def _search_contacts(self, params: dict[str, Any]) -> ConnectorResult:
        """GET /api/v2/users/search.json?query={query}"""
        assert self._client is not None  # noqa: S101
        query: str = params["query"]

        try:
            resp = await self._client.get(
                "/api/v2/users/search.json",
                params={"query": query},
            )
            resp.raise_for_status()
            data = resp.json()
            return ConnectorResult(
                success=True,
                data={"users": data.get("users", [])},
            )
        except httpx.HTTPStatusError as exc:
            logger.warning(
                "zendesk_search_failed",
                status=exc.response.status_code,
            )
            return ConnectorResult(
                success=False, error=self._http_error_msg(exc),
            )
        except httpx.HTTPError as exc:
            logger.error("zendesk_search_error", error=str(exc))
            return ConnectorResult(success=False, error=str(exc))

    async def _list_comments(self, params: dict[str, Any]) -> ConnectorResult:
        """GET /api/v2/tickets/{ticket_id}/comments.json"""
        assert self._client is not None  # noqa: S101
        ticket_id: int = params["ticket_id"]

        try:
            resp = await self._client.get(
                f"/api/v2/tickets/{ticket_id}/comments.json",
            )
            resp.raise_for_status()
            data = resp.json()
            return ConnectorResult(
                success=True,
                data={"comments": data.get("comments", [])},
            )
        except httpx.HTTPStatusError as exc:
            logger.warning(
                "zendesk_comments_failed",
                ticket_id=ticket_id,
                status=exc.response.status_code,
            )
            return ConnectorResult(
                success=False, error=self._http_error_msg(exc),
            )
        except httpx.HTTPError as exc:
            logger.error(
                "zendesk_comments_error",
                ticket_id=ticket_id,
                error=str(exc),
            )
            return ConnectorResult(success=False, error=str(exc))
