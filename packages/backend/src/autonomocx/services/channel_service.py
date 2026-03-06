"""Channel configuration service."""

from __future__ import annotations

import secrets
import uuid
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from autonomocx.core.exceptions import NotFoundError, ValidationError
from autonomocx.models.channel import ChannelConfig

logger = structlog.get_logger(__name__)

# Supported channel types and their required config keys
_CHANNEL_REQUIREMENTS: dict[str, list[str]] = {
    "webchat": [],
    "whatsapp": ["phone_number_id", "access_token"],
    "email": ["smtp_host", "smtp_port", "imap_host"],
    "voice": ["twilio_account_sid", "twilio_auth_token"],
    "sms": ["twilio_account_sid", "twilio_auth_token", "phone_number"],
    "slack": ["bot_token", "signing_secret"],
}


def _validate_channel_config(channel_type: str, config: dict) -> list[str]:
    """Return a list of missing required config keys for *channel_type*."""
    required = _CHANNEL_REQUIREMENTS.get(channel_type, [])
    return [k for k in required if k not in config or not config[k]]


async def list_channels(
    db: AsyncSession,
    org_id: uuid.UUID,
) -> list[ChannelConfig]:
    """Return all channel configurations for *org_id*."""
    stmt = (
        select(ChannelConfig)
        .where(ChannelConfig.org_id == org_id)
        .order_by(ChannelConfig.display_name)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_channel(
    db: AsyncSession,
    channel_id: uuid.UUID,
) -> ChannelConfig:
    """Return a single channel config.  Raises ``NotFoundError`` if missing."""
    result = await db.execute(select(ChannelConfig).where(ChannelConfig.id == channel_id))
    ch = result.scalar_one_or_none()
    if ch is None:
        raise NotFoundError(f"Channel {channel_id} not found.")
    return ch


async def create_channel(
    db: AsyncSession,
    org_id: uuid.UUID,
    data: dict,
) -> ChannelConfig:
    """Create a new channel configuration.

    Validates that the required config keys for the channel type are
    present and generates a random webhook secret.
    """
    channel_type = data["channel_type"]
    config = data.get("config", {})

    missing = _validate_channel_config(channel_type, config)
    if missing:
        raise ValidationError(f"Missing required config for '{channel_type}': {', '.join(missing)}")

    ch = ChannelConfig(
        org_id=org_id,
        channel_type=channel_type,
        display_name=data["display_name"],
        agent_id=data.get("agent_id"),
        config=config,
        webhook_secret=secrets.token_urlsafe(32),
        is_active=data.get("is_active", True),
    )
    db.add(ch)
    await db.flush()

    logger.info(
        "channel_created",
        channel_id=str(ch.id),
        channel_type=channel_type,
    )
    return ch


async def update_channel(
    db: AsyncSession,
    channel_id: uuid.UUID,
    data: dict,
) -> ChannelConfig:
    """Partially update a channel configuration."""
    ch = await get_channel(db, channel_id)

    for field in ("display_name", "agent_id", "config", "is_active"):
        if field in data:
            setattr(ch, field, data[field])

    # Re-validate config if it was changed
    if "config" in data:
        missing = _validate_channel_config(ch.channel_type, ch.config or {})
        if missing:
            raise ValidationError(
                f"Missing required config for '{ch.channel_type}': {', '.join(missing)}"
            )

    db.add(ch)
    await db.flush()

    logger.info("channel_updated", channel_id=str(ch.id))
    return ch


async def delete_channel(
    db: AsyncSession,
    channel_id: uuid.UUID,
) -> None:
    """Delete a channel configuration."""
    ch = await get_channel(db, channel_id)
    await db.delete(ch)
    await db.flush()

    logger.info("channel_deleted", channel_id=str(channel_id))


async def test_channel(
    db: AsyncSession,
    channel_id: uuid.UUID,
) -> dict[str, Any]:
    """Test connectivity for a channel configuration.

    Returns a ``ChannelTestResponse``-compatible dict indicating
    whether the channel credentials are valid and reachable.
    """
    ch = await get_channel(db, channel_id)

    if not ch.is_active:
        raise ValidationError("Cannot test an inactive channel.")

    # TODO: Implement actual connectivity tests per channel type:
    #   - webchat: always pass (no external dependency)
    #   - whatsapp: verify WhatsApp Business API token
    #   - email: attempt SMTP EHLO + IMAP login
    #   - voice/sms: verify Twilio credentials
    #   - slack: call auth.test API

    # For now, validate config completeness
    config = ch.config or {}
    missing = _validate_channel_config(ch.channel_type, config)

    if missing:
        return {
            "channel_id": str(ch.id),
            "channel_type": ch.channel_type,
            "success": False,
            "message": f"Missing configuration: {', '.join(missing)}",
            "details": {"missing_keys": missing},
        }

    return {
        "channel_id": str(ch.id),
        "channel_type": ch.channel_type,
        "success": True,
        "message": (
            f"Channel '{ch.display_name}' configuration is valid. "
            "Full connectivity test pending integration."
        ),
        "details": {},
    }
