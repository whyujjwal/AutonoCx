"""CORS middleware setup."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from autonomocx.core.config import Settings


def setup_cors(app: FastAPI, settings: Settings) -> None:
    """Attach ``CORSMiddleware`` to the FastAPI application.

    The allowed origins, methods, and headers are read from :class:`Settings`
    so they can be configured per environment without code changes.
    """
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allowed_origins,
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=settings.cors_allowed_methods,
        allow_headers=settings.cors_allowed_headers,
        expose_headers=[
            "X-Request-ID",
            "X-RateLimit-Limit",
            "X-RateLimit-Remaining",
            "X-RateLimit-Reset",
        ],
    )
