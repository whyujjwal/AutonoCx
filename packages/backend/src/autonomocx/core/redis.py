"""Redis connection pool management for caching, rate-limiting, and pub/sub."""

from __future__ import annotations

import redis.asyncio as aioredis
import structlog

from autonomocx.core.config import get_settings

logger = structlog.get_logger(__name__)


class RedisManager:
    """Manages a shared async Redis connection pool.

    Usage::

        redis_manager = RedisManager()
        await redis_manager.connect()
        client = redis_manager.client
        await client.set("key", "value")
        ...
        await redis_manager.disconnect()
    """

    def __init__(self) -> None:
        self._pool: aioredis.ConnectionPool | None = None
        self._client: aioredis.Redis | None = None

    # ── Lifecycle ──────────────────────────────────────────────────────

    async def connect(self) -> None:
        """Create the connection pool and a Redis client bound to it."""
        if self._client is not None:
            return  # already connected

        settings = get_settings()
        self._pool = aioredis.ConnectionPool.from_url(
            settings.redis_url,
            max_connections=settings.redis_max_connections,
            socket_timeout=settings.redis_socket_timeout,
            socket_connect_timeout=settings.redis_socket_connect_timeout,
            decode_responses=True,
        )
        self._client = aioredis.Redis(connection_pool=self._pool)

        # Quick health check
        try:
            await self._client.ping()  # type: ignore[misc]
            logger.info("redis_connected", url=settings.redis_url)
        except Exception:
            logger.error("redis_connection_failed", url=settings.redis_url)
            raise

    async def disconnect(self) -> None:
        """Gracefully close the client and drain the pool."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None
        if self._pool is not None:
            await self._pool.aclose()
            self._pool = None
        logger.info("redis_disconnected")

    # ── Accessors ──────────────────────────────────────────────────────

    @property
    def client(self) -> aioredis.Redis:
        """Return the connected Redis client.

        Raises ``RuntimeError`` if ``connect()`` has not been called.
        """
        if self._client is None:
            raise RuntimeError(
                "Redis client is not initialised. Call `await redis_manager.connect()` first."
            )
        return self._client

    @property
    def is_connected(self) -> bool:
        return self._client is not None


# Module-level singleton so the rest of the app can import it directly.
redis_manager = RedisManager()


async def get_redis() -> aioredis.Redis:
    """FastAPI dependency that returns the shared Redis client."""
    return redis_manager.client
