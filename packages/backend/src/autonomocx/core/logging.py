"""Structured logging configuration powered by structlog.

Call ``setup_logging()`` once during application startup to configure
structlog with JSON output (production) or coloured console output
(development).
"""

from __future__ import annotations

import logging
import sys
from typing import TYPE_CHECKING

import structlog

if TYPE_CHECKING:
    from autonomocx.core.config import Settings


def setup_logging(settings: Settings) -> None:
    """Configure structlog and the stdlib logging bridge.

    In *production* the output is newline-delimited JSON so it can be
    ingested by any log aggregator.  In *development* we use a coloured
    console renderer for human readability.
    """

    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)

    # Shared processors that run for every log event
    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.ExtraAdder(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]

    if settings.app_env == "production":
        # JSON lines for structured log ingestion
        renderer: structlog.types.Processor = structlog.processors.JSONRenderer()
    else:
        # Pretty console output during development
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.processors.format_exc_info,
            renderer,
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # ── Bridge stdlib logging into structlog ───────────────────────────
    # This ensures that third-party libraries (uvicorn, sqlalchemy, etc.)
    # also emit structlog-formatted output.
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        structlog.stdlib.ProcessorFormatter(
            processors=[
                structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                *shared_processors,
                structlog.processors.format_exc_info,
                renderer,
            ],
        )
    )

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(log_level)

    # Quieten noisy loggers
    for noisy in ("uvicorn.access", "sqlalchemy.engine", "httpcore", "httpx"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    # If DB echo is requested, let SQLAlchemy engine logs through
    if settings.db_echo:
        logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO)


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Return a structlog bound logger, optionally namespaced."""
    return structlog.get_logger(name)
