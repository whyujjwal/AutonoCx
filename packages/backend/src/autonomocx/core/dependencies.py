"""FastAPI dependencies for authentication, authorisation, and database access."""

from __future__ import annotations

from collections.abc import Callable
from typing import Annotated, Any

import structlog
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from autonomocx.core.database import get_db as _get_db
from autonomocx.core.exceptions import AuthenticationError, AuthorizationError
from autonomocx.core.security import TokenPayload, decode_token

logger = structlog.get_logger(__name__)

# Re-export so other modules can import from a single place.
get_db = _get_db

_bearer_scheme = HTTPBearer(auto_error=False)


# ── Token resolution ───────────────────────────────────────────────────


async def _resolve_token(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(_bearer_scheme),
    ],
) -> TokenPayload:
    """Extract and validate the JWT from the ``Authorization: Bearer`` header."""
    if credentials is None:
        raise AuthenticationError("Missing authorization header.")

    try:
        payload = decode_token(credentials.credentials)
    except JWTError as exc:
        logger.warning("jwt_decode_failed", error=str(exc))
        raise AuthenticationError("Invalid or expired token.") from exc

    if payload.token_type != "access":
        raise AuthenticationError("Invalid token type. Expected an access token.")

    if not payload.sub:
        raise AuthenticationError("Token is missing a subject claim.")

    return payload


# ── Public dependencies ────────────────────────────────────────────────


async def get_current_user(
    token: Annotated[TokenPayload, Depends(_resolve_token)],
) -> TokenPayload:
    """Return the validated ``TokenPayload`` for the current request.

    Downstream route handlers and dependencies can use the payload to
    look up the full user record from the database when needed.
    """
    return token


async def get_current_active_user(
    current_user: Annotated[TokenPayload, Depends(get_current_user)],
) -> TokenPayload:
    """Ensure the current user is active.

    This is a thin wrapper today -- it returns the same payload.  When
    the user model is added you can augment this to load the DB record
    and check ``is_active``.
    """
    # Placeholder: once User model exists, load and check is_active.
    return current_user


def require_role(*allowed_roles: str) -> Callable[..., Any]:
    """Return a dependency that verifies the user has one of *allowed_roles*.

    Usage::

        @router.get("/admin", dependencies=[Depends(require_role("admin", "superadmin"))])
        async def admin_only():
            ...
    """

    async def _check_role(
        current_user: Annotated[TokenPayload, Depends(get_current_active_user)],
    ) -> TokenPayload:
        if current_user.role not in allowed_roles:
            logger.warning(
                "authorization_denied",
                user=current_user.sub,
                required_roles=allowed_roles,
                actual_role=current_user.role,
            )
            raise AuthorizationError(
                f"Role '{current_user.role}' is not authorised. "
                f"Required: {', '.join(allowed_roles)}."
            )
        return current_user

    return _check_role


# ── WebSocket auth ────────────────────────────────────────────────────


async def get_current_user_ws(
    token: str,
    db: AsyncSession,
) -> Any:
    """Authenticate a WebSocket connection using a raw JWT token string.

    Unlike HTTP dependencies the token is passed explicitly (from a query
    parameter) rather than via the ``Authorization`` header.  Returns the
    ``User`` ORM object so the caller has access to ``org_id``, ``full_name``,
    etc.
    """
    from sqlalchemy import select

    from autonomocx.models.user import User

    try:
        payload = decode_token(token)
    except JWTError as exc:
        logger.warning("ws_jwt_decode_failed", error=str(exc))
        raise AuthenticationError("Invalid or expired token.") from exc

    if payload.token_type != "access":
        raise AuthenticationError("Invalid token type. Expected an access token.")

    if not payload.sub:
        raise AuthenticationError("Token is missing a subject claim.")

    result = await db.execute(
        select(User).where(User.id == payload.sub)
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise AuthenticationError("User not found.")
    if not user.is_active:
        raise AuthenticationError("User account is disabled.")
    return user


# ── Convenience type aliases ───────────────────────────────────────────

CurrentUser = Annotated[TokenPayload, Depends(get_current_user)]
ActiveUser = Annotated[TokenPayload, Depends(get_current_active_user)]
DbSession = Annotated[AsyncSession, Depends(get_db)]
