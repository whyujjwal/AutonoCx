"""Redis-backed sliding-window rate-limiting middleware.

Limits are expressed as *requests per minute* (RPM).  Each route can
optionally override the default RPM by including ``rate_limit`` in its
``kwargs`` or by decorating the endpoint function with a
``_rate_limit_rpm`` attribute.

The middleware uses a simple Redis sorted-set sliding window:
  - key: ``rl:<identifier>:<path>``
  - score/member: request timestamp in milliseconds

Standard ``X-RateLimit-*`` response headers are always set so that
clients can self-throttle.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

import structlog
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

if TYPE_CHECKING:
    import redis.asyncio as aioredis

from autonomocx.core.config import get_settings

logger = structlog.get_logger(__name__)

_WINDOW_SECONDS = 60  # 1-minute window


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Sliding-window rate limiter backed by Redis sorted sets."""

    def __init__(self, app, *, redis_getter=None) -> None:  # noqa: ANN001
        super().__init__(app)
        self._redis_getter = redis_getter

    # ── helpers ────────────────────────────────────────────────────────

    def _get_identifier(self, request: Request) -> str:
        """Build a per-user or per-IP identifier."""
        # Prefer authenticated user id from request state (set by auth middleware).
        user_sub = getattr(getattr(request, "state", None), "user_sub", None)
        if user_sub:
            return f"user:{user_sub}"

        # Fall back to client IP.
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return f"ip:{forwarded.split(',')[0].strip()}"
        client = request.client
        return f"ip:{client.host}" if client else "ip:unknown"

    def _resolve_rpm(self, request: Request) -> int:
        """Determine the RPM limit for this request.

        If the matched route handler has a ``_rate_limit_rpm`` attribute
        we use that; otherwise we fall back to the global default.
        """
        settings = get_settings()
        route = request.scope.get("route")
        if route is not None:
            endpoint = getattr(route, "endpoint", None)
            custom_rpm = getattr(endpoint, "_rate_limit_rpm", None)
            if custom_rpm is not None:
                return int(custom_rpm)
        return settings.rate_limit_default_rpm

    # ── main dispatch ─────────────────────────────────────────────────

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        settings = get_settings()

        # Skip rate limiting if disabled or if we have no Redis getter.
        if not settings.rate_limit_enabled or self._redis_getter is None:
            return await call_next(request)

        try:
            redis: aioredis.Redis = await self._redis_getter()
        except Exception:
            # If Redis is down, fail open so user traffic is not blocked.
            logger.warning("rate_limit_redis_unavailable")
            return await call_next(request)

        identifier = self._get_identifier(request)
        rpm = self._resolve_rpm(request)
        key = f"rl:{identifier}:{request.url.path}"

        now_ms = int(time.time() * 1000)
        window_start_ms = now_ms - (_WINDOW_SECONDS * 1000)

        pipe = redis.pipeline(transaction=True)
        # Remove entries outside the window
        pipe.zremrangebyscore(key, 0, window_start_ms)
        # Count remaining entries
        pipe.zcard(key)
        # Add current request
        pipe.zadd(key, {str(now_ms): now_ms})
        # Set TTL so keys auto-expire
        pipe.expire(key, _WINDOW_SECONDS + 1)
        results = await pipe.execute()

        current_count: int = results[1]  # zcard result

        # Build rate-limit headers
        remaining = max(0, rpm - current_count - 1)
        reset_at = int(time.time()) + _WINDOW_SECONDS

        headers = {
            "X-RateLimit-Limit": str(rpm),
            "X-RateLimit-Remaining": str(remaining),
            "X-RateLimit-Reset": str(reset_at),
        }

        if current_count >= rpm:
            logger.warning(
                "rate_limit_exceeded",
                identifier=identifier,
                path=request.url.path,
                rpm=rpm,
            )
            return JSONResponse(
                status_code=429,
                content={
                    "error": {
                        "code": "RATE_LIMIT_EXCEEDED",
                        "message": "Too many requests. Please try again later.",
                    }
                },
                headers=headers,
            )

        response = await call_next(request)
        for k, v in headers.items():
            response.headers[k] = v
        return response


def rate_limit(rpm: int):
    """Decorator to set a per-route RPM override.

    Usage::

        @router.get("/expensive")
        @rate_limit(10)
        async def expensive_endpoint():
            ...
    """

    def decorator(func):  # noqa: ANN001
        func._rate_limit_rpm = rpm
        return func

    return decorator
