"""Application-wide custom exceptions and FastAPI exception handlers."""

from __future__ import annotations

from typing import Any

import structlog
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

logger = structlog.get_logger(__name__)


# ── Base exception ─────────────────────────────────────────────────────


class AppError(Exception):
    """Base exception for all application-specific errors.

    Sub-classes set sensible defaults for ``status_code`` and ``error_code``
    so callers can simply raise without boilerplate.
    """

    status_code: int = 500
    error_code: str = "INTERNAL_ERROR"
    message: str = "An unexpected error occurred."

    def __init__(
        self,
        message: str | None = None,
        *,
        status_code: int | None = None,
        error_code: str | None = None,
        detail: Any = None,
    ) -> None:
        if message is not None:
            self.message = message
        if status_code is not None:
            self.status_code = status_code
        if error_code is not None:
            self.error_code = error_code
        self.detail = detail
        super().__init__(self.message)

    def to_dict(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "error": {
                "code": self.error_code,
                "message": self.message,
            }
        }
        if self.detail is not None:
            body["error"]["detail"] = self.detail
        return body


# ── Concrete exceptions ───────────────────────────────────────────────


class NotFoundError(AppError):
    status_code = 404
    error_code = "NOT_FOUND"
    message = "The requested resource was not found."


class AuthenticationError(AppError):
    status_code = 401
    error_code = "AUTHENTICATION_ERROR"
    message = "Could not validate credentials."


class AuthorizationError(AppError):
    status_code = 403
    error_code = "AUTHORIZATION_ERROR"
    message = "You do not have permission to perform this action."


class ValidationError(AppError):
    status_code = 422
    error_code = "VALIDATION_ERROR"
    message = "Request validation failed."


class RateLimitError(AppError):
    status_code = 429
    error_code = "RATE_LIMIT_EXCEEDED"
    message = "Too many requests. Please try again later."


class ExternalServiceError(AppError):
    status_code = 502
    error_code = "EXTERNAL_SERVICE_ERROR"
    message = "An external service returned an unexpected error."


class ConflictError(AppError):
    status_code = 409
    error_code = "CONFLICT"
    message = "The request conflicts with the current state of the resource."


# ── FastAPI exception handlers ─────────────────────────────────────────


async def _app_exception_handler(request: Request, exc: AppError) -> JSONResponse:
    """Handler for all ``AppError`` sub-classes."""
    logger.warning(
        "app_exception",
        error_code=exc.error_code,
        status_code=exc.status_code,
        message=exc.message,
        path=str(request.url),
        method=request.method,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.to_dict(),
    )


async def _unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all for any exception that is not an ``AppError``."""
    logger.exception(
        "unhandled_exception",
        path=str(request.url),
        method=request.method,
        exc_type=type(exc).__name__,
    )
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred.",
            }
        },
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Attach exception handlers to the FastAPI application."""
    app.add_exception_handler(AppError, _app_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, _unhandled_exception_handler)
