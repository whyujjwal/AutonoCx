"""Middleware that ensures every request carries a unique X-Request-ID header.

If the client provides one it is re-used; otherwise a new UUID-4 is
generated.  The ID is also attached to structlog's context vars so all
log entries emitted during the request carry it automatically.
"""

from __future__ import annotations

from uuid import uuid4

import structlog
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

_REQUEST_ID_HEADER = "X-Request-ID"


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Inject / propagate ``X-Request-ID`` on every request/response cycle."""

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        # Prefer a client-supplied ID; fall back to a fresh one.
        request_id: str = request.headers.get(_REQUEST_ID_HEADER) or uuid4().hex

        # Store on request state so downstream code can access it.
        request.state.request_id = request_id

        # Bind to structlog context vars (auto-cleared after request).
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)

        response: Response = await call_next(request)
        response.headers[_REQUEST_ID_HEADER] = request_id
        return response
