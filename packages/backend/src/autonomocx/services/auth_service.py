"""Authentication service -- login, registration, token management."""

from __future__ import annotations

import re
import uuid
from datetime import datetime, UTC

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from autonomocx.core.config import get_settings
from autonomocx.core.exceptions import (
    AuthenticationError,
    ConflictError,
    NotFoundError,
    ValidationError,
)
from autonomocx.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    verify_password,
)
from autonomocx.models.organization import Organization, PlanType
from autonomocx.models.user import User, UserRole
from autonomocx.schemas.auth import TokenResponse

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _slugify(name: str) -> str:
    """Convert an organization name into a URL-safe slug."""
    slug = name.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug or "org"


def _build_token_response(user: User) -> TokenResponse:
    """Create access + refresh tokens for a given user and wrap in schema."""
    settings = get_settings()
    access = create_access_token(
        subject=str(user.id),
        org_id=str(user.org_id),
        role=user.role.value,
    )
    refresh = create_refresh_token(
        subject=str(user.id),
        org_id=str(user.org_id),
    )
    return TokenResponse(
        access_token=access,
        refresh_token=refresh,
        token_type="bearer",
        expires_in=settings.jwt_access_token_expire_minutes * 60,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def authenticate_user(
    db: AsyncSession,
    email: str,
    password: str,
) -> User:
    """Validate credentials and return the ``User`` row.

    Raises ``AuthenticationError`` on invalid email or password.
    """
    stmt = select(User).where(User.email == email)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if user is None or not verify_password(password, user.password_hash):
        raise AuthenticationError("Invalid email or password.")

    if not user.is_active:
        raise AuthenticationError("Account is deactivated. Contact your administrator.")

    # Touch last_login_at
    user.last_login_at = datetime.now(UTC)
    db.add(user)
    await db.flush()

    logger.info("user_authenticated", user_id=str(user.id), email=user.email)
    return user


async def create_user_and_org(
    db: AsyncSession,
    email: str,
    password: str,
    full_name: str,
    org_name: str,
) -> tuple[User, Organization]:
    """Register a brand-new user and their organization in a single transaction.

    The user is assigned the ``ADMIN`` role for the new organization.
    Raises ``ConflictError`` if the email is already registered.
    """
    # Check for existing email
    existing = await db.execute(select(User).where(User.email == email))
    if existing.scalar_one_or_none() is not None:
        raise ConflictError("A user with this email already exists.")

    # Build unique slug
    base_slug = _slugify(org_name)
    slug = base_slug
    suffix = 0
    while True:
        dup = await db.execute(
            select(Organization).where(Organization.slug == slug)
        )
        if dup.scalar_one_or_none() is None:
            break
        suffix += 1
        slug = f"{base_slug}-{suffix}"

    org = Organization(
        name=org_name,
        slug=slug,
        plan=PlanType.STARTER,
        is_active=True,
        settings={},
    )
    db.add(org)
    await db.flush()  # populate org.id

    user = User(
        org_id=org.id,
        email=email,
        password_hash=get_password_hash(password),
        full_name=full_name,
        role=UserRole.ADMIN,
        is_active=True,
    )
    db.add(user)
    await db.flush()

    logger.info(
        "user_and_org_created",
        user_id=str(user.id),
        org_id=str(org.id),
        org_slug=org.slug,
    )
    return user, org


def create_access_token_for_user(user: User) -> str:
    """Return a signed JWT access token for *user*."""
    return create_access_token(
        subject=str(user.id),
        org_id=str(user.org_id),
        role=user.role.value,
    )


def create_refresh_token_for_user(user: User) -> str:
    """Return a signed JWT refresh token for *user*."""
    return create_refresh_token(
        subject=str(user.id),
        org_id=str(user.org_id),
    )


async def refresh_access_token(
    db: AsyncSession,
    refresh_token: str,
) -> TokenResponse:
    """Validate *refresh_token* and return a fresh ``TokenResponse``.

    Raises ``AuthenticationError`` if the token is invalid, expired, or
    the user no longer exists / is deactivated.
    """
    try:
        payload = decode_token(refresh_token)
    except Exception:
        raise AuthenticationError("Invalid or expired refresh token.")

    if payload.token_type != "refresh":
        raise AuthenticationError("Token is not a refresh token.")

    user_id = uuid.UUID(payload.sub)
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        raise AuthenticationError("User not found.")
    if not user.is_active:
        raise AuthenticationError("Account is deactivated.")

    logger.info("access_token_refreshed", user_id=str(user.id))
    return _build_token_response(user)


async def invalidate_refresh_token(
    redis,  # redis.asyncio.Redis
    refresh_token: str,
) -> None:
    """Add a refresh token to a Redis-backed deny-list so it cannot be reused.

    The entry auto-expires after the token's remaining lifetime.
    """
    try:
        payload = decode_token(refresh_token)
    except Exception:
        # If we can't decode it, there's nothing meaningful to blacklist.
        return

    jti = payload.jti
    if not jti:
        return

    # Store until the token's natural expiry
    if payload.exp is not None:
        ttl_seconds = int((payload.exp - datetime.now(UTC)).total_seconds())
        if ttl_seconds > 0:
            await redis.setex(f"token:blacklist:{jti}", ttl_seconds, "1")
    else:
        # Fallback: blacklist for 7 days
        await redis.setex(f"token:blacklist:{jti}", 7 * 86400, "1")

    logger.info("refresh_token_invalidated", jti=jti)
