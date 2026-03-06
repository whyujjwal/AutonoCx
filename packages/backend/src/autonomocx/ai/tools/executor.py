"""Tool execution engine -- invokes tools, handles HTTP calls, retries, and logging."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

import httpx
import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from autonomocx.core.exceptions import ExternalServiceError
from autonomocx.models.action import ActionExecution, ActionStatus
from autonomocx.models.tool import Tool

from .registry import ToolRegistry
from .validator import ParameterValidator, ValidationResult

logger = structlog.get_logger(__name__)


# ------------------------------------------------------------------
# Data models
# ------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ExecutionResult:
    """Outcome of a single tool execution."""

    success: bool
    output: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    execution_time_ms: int = 0
    action_id: uuid.UUID | None = None


# ------------------------------------------------------------------
# Executor
# ------------------------------------------------------------------


class ToolExecutor:
    """Invoke tools and persist execution records to ``action_executions``."""

    def __init__(self) -> None:
        self._validator = ParameterValidator()
        self._http_client: httpx.AsyncClient | None = None

    async def _get_http_client(self) -> httpx.AsyncClient:
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(timeout=30.0)
        return self._http_client

    async def close(self) -> None:
        if self._http_client and not self._http_client.is_closed:
            await self._http_client.aclose()

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    async def execute(
        self,
        tool: Tool,
        parameters: dict[str, Any],
        *,
        conversation_id: uuid.UUID,
        org_id: uuid.UUID,
        agent_id: uuid.UUID | None = None,
        message_id: uuid.UUID | None = None,
        db: AsyncSession,
    ) -> ExecutionResult:
        """Execute a tool and record the result.

        1. Validate parameters against the tool's schema.
        2. Execute via builtin handler or HTTP call.
        3. Persist an ``ActionExecution`` record.
        4. Return the result.
        """
        start = time.monotonic()

        # Validate parameters
        validation = self._validator.validate(
            parameters,
            tool.parameters_schema or {"type": "object", "properties": {}},
        )
        if not validation.is_valid:
            return await self._record_failure(
                db=db,
                tool=tool,
                parameters=parameters,
                conversation_id=conversation_id,
                org_id=org_id,
                agent_id=agent_id,
                message_id=message_id,
                error=f"Parameter validation failed: {'; '.join(validation.errors)}",
                elapsed_ms=self._elapsed_ms(start),
            )

        # Execute
        try:
            output = await self._invoke(tool, validation.sanitised_params)
        except Exception as exc:
            logger.error(
                "tool_execution_error",
                tool=tool.name,
                error=str(exc),
            )
            return await self._record_failure(
                db=db,
                tool=tool,
                parameters=parameters,
                conversation_id=conversation_id,
                org_id=org_id,
                agent_id=agent_id,
                message_id=message_id,
                error=str(exc),
                elapsed_ms=self._elapsed_ms(start),
            )

        elapsed_ms = self._elapsed_ms(start)

        # Persist success
        action = ActionExecution(
            org_id=org_id,
            conversation_id=conversation_id,
            message_id=message_id,
            tool_id=tool.id,
            agent_id=agent_id,
            status=ActionStatus.COMPLETED,
            input_params=parameters,
            output_result=output,
            execution_time_ms=elapsed_ms,
        )
        db.add(action)
        await db.flush()

        logger.info(
            "tool_executed",
            tool=tool.name,
            status="success",
            elapsed_ms=elapsed_ms,
            action_id=str(action.id),
        )

        return ExecutionResult(
            success=True,
            output=output,
            execution_time_ms=elapsed_ms,
            action_id=action.id,
        )

    # ------------------------------------------------------------------
    # Invocation dispatch
    # ------------------------------------------------------------------

    async def _invoke(self, tool: Tool, params: dict[str, Any]) -> dict[str, Any]:
        """Dispatch to builtin handler or HTTP endpoint."""

        # 1. Check for builtin handler
        if tool.is_builtin:
            handler = ToolRegistry.get_builtin_handler(tool.name)
            if handler:
                return await handler.execute(params)
            raise ExternalServiceError(
                f"No builtin handler registered for '{tool.name}'",
                error_code="TOOL_HANDLER_MISSING",
            )

        # 2. HTTP call
        if tool.endpoint_url:
            return await self._http_call(tool, params)

        raise ExternalServiceError(
            f"Tool '{tool.name}' has no endpoint or builtin handler",
            error_code="TOOL_NOT_CONFIGURED",
        )

    async def _http_call(self, tool: Tool, params: dict[str, Any]) -> dict[str, Any]:
        """Execute an HTTP-based tool with retry support."""
        client = await self._get_http_client()
        method = (tool.http_method or "POST").upper()
        url = tool.endpoint_url or ""
        headers = dict(tool.headers_template or {})
        timeout = float(tool.timeout_seconds or 30)

        retry_config = tool.retry_config or {}
        max_retries = retry_config.get("max_retries", 2)
        retry_delay = retry_config.get("delay_seconds", 1.0)

        last_exc: Exception | None = None
        for attempt in range(1, max_retries + 2):
            try:
                if method == "GET":
                    resp = await client.get(url, params=params, headers=headers, timeout=timeout)
                else:
                    resp = await client.request(
                        method, url, json=params, headers=headers, timeout=timeout
                    )

                resp.raise_for_status()
                return resp.json()
            except httpx.HTTPStatusError as exc:
                last_exc = exc
                logger.warning(
                    "tool_http_error",
                    tool=tool.name,
                    status=exc.response.status_code,
                    attempt=attempt,
                )
                if exc.response.status_code < 500 or attempt > max_retries:
                    raise ExternalServiceError(
                        f"Tool HTTP error: {exc.response.status_code}",
                        error_code="TOOL_HTTP_ERROR",
                    ) from exc
            except httpx.RequestError as exc:
                last_exc = exc
                logger.warning(
                    "tool_request_error",
                    tool=tool.name,
                    attempt=attempt,
                    error=str(exc),
                )
                if attempt > max_retries:
                    raise ExternalServiceError(
                        f"Tool request failed: {exc}",
                        error_code="TOOL_REQUEST_ERROR",
                    ) from exc

            # Wait before retry
            import asyncio
            await asyncio.sleep(retry_delay * attempt)

        raise ExternalServiceError(
            f"Tool '{tool.name}' failed after {max_retries + 1} attempts",
            error_code="TOOL_MAX_RETRIES",
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def _record_failure(
        self,
        *,
        db: AsyncSession,
        tool: Tool,
        parameters: dict[str, Any],
        conversation_id: uuid.UUID,
        org_id: uuid.UUID,
        agent_id: uuid.UUID | None,
        message_id: uuid.UUID | None,
        error: str,
        elapsed_ms: int,
    ) -> ExecutionResult:
        action = ActionExecution(
            org_id=org_id,
            conversation_id=conversation_id,
            message_id=message_id,
            tool_id=tool.id,
            agent_id=agent_id,
            status=ActionStatus.FAILED,
            input_params=parameters,
            error_message=error,
            execution_time_ms=elapsed_ms,
        )
        db.add(action)
        await db.flush()

        return ExecutionResult(
            success=False,
            error=error,
            execution_time_ms=elapsed_ms,
            action_id=action.id,
        )

    @staticmethod
    def _elapsed_ms(start: float) -> int:
        return int((time.monotonic() - start) * 1000)
