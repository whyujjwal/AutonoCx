"""Middleware that resolves the organisation context from the JWT.

After the ``RequestIdMiddleware`` runs and the ``Authorization`` header
is available, this middleware decodes the JWT (without raising on
failure -- unauthenticated requests simply get no org context) and
stores the ``org_id`` on ``request.state`` and in structlog context vars.

Downstream code can then access the org via::

    request.state.org_id      # str | None
    request.state.user_sub    # str | None
    request.state.user_role   # str | None
"""

from __future__ import annotations

import structlog
from jose import JWTError
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from autonomocx.core.security import decode_token

logger = structlog.get_logger(__name__)

# Paths that should never attempt JWT parsing (saves a decode per request).
_SKIP_PREFIXES: tuple[str, ...] = (
    "/docs",
    "/redoc",
    "/openapi.json",
    "/health",
    "/ready",
)


class OrgContextMiddleware(BaseHTTPMiddleware):
    """Extract org_id and user metadata from the JWT into request.state."""

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        # Default to None; may be overwritten below.
        request.state.org_id = None
        request.state.user_sub = None
        request.state.user_role = None

        path = request.url.path
        if any(path.startswith(p) for p in _SKIP_PREFIXES):
            return await call_next(request)

        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token_str = auth_header[7:]
            try:
                payload = decode_token(token_str)
                request.state.org_id = payload.org_id
                request.state.user_sub = payload.sub
                request.state.user_role = payload.role

                # Enrich structured logs for the rest of this request.
                structlog.contextvars.bind_contextvars(
                    org_id=payload.org_id,
                    user_sub=payload.sub,
                    user_role=payload.role,
                )
            except JWTError:
                # Token is invalid or expired -- that is fine here; the
                # auth dependency will reject the request if needed.
                pass

        return await call_next(request)
