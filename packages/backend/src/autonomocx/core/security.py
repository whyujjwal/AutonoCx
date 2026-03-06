"""JWT token management and password hashing utilities."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from jose import JWTError, jwt
from passlib.context import CryptContext

from autonomocx.core.config import get_settings

# ── Password hashing ──────────────────────────────────────────────────

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_password_hash(plain_password: str) -> str:
    """Return a bcrypt hash of *plain_password*."""
    return _pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Return ``True`` if *plain_password* matches *hashed_password*."""
    return _pwd_context.verify(plain_password, hashed_password)


# ── JWT helpers ───────────────────────────────────────────────────────


class TokenPayload:
    """Typed wrapper around a decoded JWT payload."""

    def __init__(self, payload: dict[str, Any]) -> None:
        self.sub: str = payload.get("sub", "")
        self.org_id: str | None = payload.get("org_id")
        self.role: str | None = payload.get("role")
        self.token_type: str = payload.get("type", "access")
        self.jti: str = payload.get("jti", "")
        self.exp: datetime | None = (
            datetime.fromtimestamp(payload["exp"], tz=UTC) if "exp" in payload else None
        )
        self.iat: datetime | None = (
            datetime.fromtimestamp(payload["iat"], tz=UTC) if "iat" in payload else None
        )
        self.raw = payload


def create_access_token(
    subject: str,
    *,
    org_id: str | None = None,
    role: str | None = None,
    extra_claims: dict[str, Any] | None = None,
    expires_delta: timedelta | None = None,
) -> str:
    """Create a signed JWT access token."""
    settings = get_settings()
    now = datetime.now(UTC)
    expire = now + (
        expires_delta
        if expires_delta is not None
        else timedelta(minutes=settings.jwt_access_token_expire_minutes)
    )

    claims: dict[str, Any] = {
        "sub": subject,
        "type": "access",
        "iat": now,
        "exp": expire,
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
        "jti": uuid4().hex,
    }
    if org_id is not None:
        claims["org_id"] = org_id
    if role is not None:
        claims["role"] = role
    if extra_claims:
        claims.update(extra_claims)

    return jwt.encode(
        claims,
        settings.effective_jwt_secret,
        algorithm=settings.jwt_algorithm,
    )


def create_refresh_token(
    subject: str,
    *,
    org_id: str | None = None,
    expires_delta: timedelta | None = None,
) -> str:
    """Create a signed JWT refresh token (longer-lived, minimal claims)."""
    settings = get_settings()
    now = datetime.now(UTC)
    expire = now + (
        expires_delta
        if expires_delta is not None
        else timedelta(days=settings.jwt_refresh_token_expire_days)
    )

    claims: dict[str, Any] = {
        "sub": subject,
        "type": "refresh",
        "iat": now,
        "exp": expire,
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
        "jti": uuid4().hex,
    }
    if org_id is not None:
        claims["org_id"] = org_id

    return jwt.encode(
        claims,
        settings.effective_jwt_secret,
        algorithm=settings.jwt_algorithm,
    )


def decode_token(token: str) -> TokenPayload:
    """Decode and validate a JWT token.  Raises ``JWTError`` on failure."""
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.effective_jwt_secret,
            algorithms=[settings.jwt_algorithm],
            issuer=settings.jwt_issuer,
            audience=settings.jwt_audience,
        )
    except JWTError:
        raise
    return TokenPayload(payload)
