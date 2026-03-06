"""Organization management service -- org settings, API key lifecycle."""

from __future__ import annotations

import hashlib
import secrets
import uuid

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from autonomocx.core.exceptions import NotFoundError
from autonomocx.models.organization import Organization

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Lightweight in-memory model for API keys (no separate ORM model yet).
# API keys are stored in the org ``settings`` JSONB column under the key
# "api_keys".  Each entry:
#   { "id": str, "name": str, "prefix": str, "hash": str,
#     "created_by": str, "created_at": str, "revoked": bool }
# ---------------------------------------------------------------------------

_API_KEY_PREFIX_LEN = 8
_API_KEY_RAW_LEN = 48


def _hash_key(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


# ---------------------------------------------------------------------------
# Organization CRUD
# ---------------------------------------------------------------------------


async def get_organization(
    db: AsyncSession,
    org_id: uuid.UUID,
) -> Organization:
    """Return an organization by id.  Raises ``NotFoundError`` if missing."""
    result = await db.execute(select(Organization).where(Organization.id == org_id))
    org = result.scalar_one_or_none()
    if org is None:
        raise NotFoundError(f"Organization {org_id} not found.")
    return org


async def update_organization(
    db: AsyncSession,
    org_id: uuid.UUID,
    data: dict,
) -> Organization:
    """Update mutable fields of an organization."""
    org = await get_organization(db, org_id)

    for field in ("name", "settings", "is_active"):
        if field in data and data[field] is not None:
            setattr(org, field, data[field])

    db.add(org)
    await db.flush()

    logger.info("organization_updated", org_id=str(org.id))
    return org


# ---------------------------------------------------------------------------
# API Key management (stored inside org.settings JSONB)
# ---------------------------------------------------------------------------


async def create_api_key(
    db: AsyncSession,
    org_id: uuid.UUID,
    user_id: uuid.UUID,
    data: dict,
) -> tuple[dict, str]:
    """Generate a new API key and persist its hash.

    Returns ``(api_key_record, raw_key)`` -- the *raw_key* is shown to the
    user only once.
    """
    org = await get_organization(db, org_id)

    raw_key = f"acx_{secrets.token_urlsafe(_API_KEY_RAW_LEN)}"
    prefix = raw_key[:_API_KEY_PREFIX_LEN]
    hashed = _hash_key(raw_key)

    key_record = {
        "id": uuid.uuid4().hex,
        "name": data.get("name", "Unnamed Key"),
        "prefix": prefix,
        "hash": hashed,
        "created_by": str(user_id),
        "created_at": str(uuid.uuid1().time),  # sortable timestamp proxy
        "revoked": False,
    }

    settings = dict(org.settings or {})
    api_keys: list[dict] = settings.get("api_keys", [])
    api_keys.append(key_record)
    settings["api_keys"] = api_keys
    org.settings = settings

    db.add(org)
    await db.flush()

    logger.info("api_key_created", org_id=str(org_id), key_prefix=prefix)
    return key_record, raw_key


async def list_api_keys(
    db: AsyncSession,
    org_id: uuid.UUID,
) -> list[dict]:
    """Return all (non-revoked) API key records for *org_id*."""
    org = await get_organization(db, org_id)
    settings = org.settings or {}
    return [k for k in settings.get("api_keys", []) if not k.get("revoked")]


async def revoke_api_key(
    db: AsyncSession,
    org_id: uuid.UUID,
    key_id: str,
) -> None:
    """Soft-revoke an API key by its internal id.

    Raises ``NotFoundError`` if no key with the given *key_id* exists.
    """
    org = await get_organization(db, org_id)
    settings = dict(org.settings or {})
    api_keys: list[dict] = settings.get("api_keys", [])

    found = False
    for key in api_keys:
        if key["id"] == key_id:
            key["revoked"] = True
            found = True
            break

    if not found:
        raise NotFoundError(f"API key {key_id} not found.")

    settings["api_keys"] = api_keys
    org.settings = settings
    db.add(org)
    await db.flush()

    logger.info("api_key_revoked", org_id=str(org_id), key_id=key_id)
