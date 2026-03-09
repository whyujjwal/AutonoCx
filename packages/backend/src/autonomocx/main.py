"""FastAPI application factory for AutonoCX.

Start the server in development with::

    uvicorn autonomocx.main:app --reload
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.responses import ORJSONResponse

from autonomocx.api.router import api_router
from autonomocx.api.v1.connectors import set_registry
from autonomocx.connectors import ConnectorRegistry
from autonomocx.connectors.zendesk import ZendeskConnector
from autonomocx.core.config import Settings, get_settings
from autonomocx.core.database import dispose_engine, init_engine
from autonomocx.core.exceptions import register_exception_handlers
from autonomocx.core.logging import setup_logging
from autonomocx.core.redis import redis_manager
from autonomocx.middleware.cors import setup_cors
from autonomocx.middleware.org_context import OrgContextMiddleware
from autonomocx.middleware.rate_limit import RateLimitMiddleware
from autonomocx.middleware.request_id import RequestIdMiddleware

logger = structlog.get_logger(__name__)


# ── Lifespan ───────────────────────────────────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """Manage startup / shutdown resources.

    * **Startup**: initialise the database engine, connect to Redis, and
      log a ready message.
    * **Shutdown**: disconnect from Redis and dispose of the DB engine
      so all pooled connections are released cleanly.
    """
    settings = get_settings()

    # ── startup ────────────────────────────────────────────────────
    logger.info("app_starting", env=settings.app_env)
    await init_engine()
    logger.info("database_engine_initialised")

    try:
        await redis_manager.connect()
    except Exception:
        logger.warning("redis_unavailable_at_startup")
        # The app can still run with degraded rate-limiting / caching.

    # ── Connector registry ────────────────────────────────────────
    registry = ConnectorRegistry()
    registry.register_type("zendesk", ZendeskConnector)
    set_registry(registry)
    logger.info("connector_registry_initialised", types=["zendesk"])

    logger.info("app_ready", host=settings.host, port=settings.port)

    yield  # ── application is running ────────────────────────────

    # ── shutdown ───────────────────────────────────────────────────
    logger.info("app_shutting_down")
    await redis_manager.disconnect()
    await dispose_engine()
    logger.info("app_shutdown_complete")


# ── App factory ────────────────────────────────────────────────────────


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build and return the fully-configured FastAPI application."""
    if settings is None:
        settings = get_settings()

    # Logging must be configured first so every subsequent log call uses
    # the correct renderer and level.
    setup_logging(settings)

    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        description="Autonomous Enterprise Support Agent Platform",
        docs_url="/docs" if settings.app_env != "production" else None,
        redoc_url="/redoc" if settings.app_env != "production" else None,
        openapi_url="/openapi.json" if settings.app_env != "production" else None,
        lifespan=lifespan,
        default_response_class=ORJSONResponse,
    )

    # ── Exception handlers ─────────────────────────────────────────
    register_exception_handlers(app)

    # ── Middleware (outermost first) ───────────────────────────────
    # Note: Starlette processes middleware bottom-to-top on the way
    # *in* and top-to-bottom on the way *out*, so add them in reverse
    # logical order.

    # 1. CORS (must be outermost)
    setup_cors(app, settings)

    # 2. Request ID
    app.add_middleware(RequestIdMiddleware)

    # 3. Organisation context from JWT
    app.add_middleware(OrgContextMiddleware)

    # 4. Rate limiting (Redis-backed)
    async def _redis_getter():
        return redis_manager.client

    app.add_middleware(RateLimitMiddleware, redis_getter=_redis_getter)

    # ── Health / readiness probes ──────────────────────────────────

    @app.get("/health", tags=["infra"], include_in_schema=False)
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/ready", tags=["infra"], include_in_schema=False)
    async def readiness() -> dict[str, str | bool]:
        redis_ok = False
        try:
            if redis_manager.is_connected:
                await redis_manager.client.ping()  # type: ignore[misc]
                redis_ok = True
        except Exception:
            pass
        return {"status": "ok", "redis": redis_ok}

    # ── API routers ───────────────────────────────────────────────
    app.include_router(api_router)

    return app


# Module-level instance used by ``uvicorn autonomocx.main:app``
app: FastAPI = create_app()
