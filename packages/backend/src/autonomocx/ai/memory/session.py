"""Redis-backed session memory for active conversations."""

from __future__ import annotations

import json
import uuid
from typing import Any

import structlog
from redis.asyncio import Redis

logger = structlog.get_logger(__name__)

# Default TTL: 2 hours -- typical upper bound for a support conversation
_DEFAULT_TTL_SECONDS = 7200
_KEY_PREFIX = "session:"


class SessionMemory:
    """Ephemeral key/value store scoped to a conversation, backed by Redis.

    All keys are namespaced under ``session:{conversation_id}:{key}`` so they
    automatically expire once the conversation is idle for longer than the TTL.
    """

    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    # ------------------------------------------------------------------
    # Core operations
    # ------------------------------------------------------------------

    async def store(
        self,
        conversation_id: uuid.UUID | str,
        key: str,
        value: Any,
        ttl: int = _DEFAULT_TTL_SECONDS,
    ) -> None:
        """Persist a value in session memory with an expiry TTL (seconds)."""
        rkey = self._rkey(conversation_id, key)
        serialised = json.dumps(value, default=str)
        await self._redis.setex(rkey, ttl, serialised)
        logger.debug("session_store", conversation_id=str(conversation_id), key=key)

    async def get(
        self,
        conversation_id: uuid.UUID | str,
        key: str,
    ) -> Any | None:
        """Retrieve a single value, returning ``None`` if missing or expired."""
        rkey = self._rkey(conversation_id, key)
        raw = await self._redis.get(rkey)
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return raw.decode() if isinstance(raw, bytes) else raw

    async def get_all(
        self,
        conversation_id: uuid.UUID | str,
    ) -> dict[str, Any]:
        """Return all session keys for a conversation as a flat dict."""
        pattern = f"{_KEY_PREFIX}{conversation_id}:*"
        result: dict[str, Any] = {}

        async for rkey in self._redis.scan_iter(match=pattern, count=100):
            key_str = rkey.decode() if isinstance(rkey, bytes) else rkey
            # Strip prefix to get the user-facing key
            short_key = key_str.split(":", 2)[-1] if ":" in key_str else key_str
            raw = await self._redis.get(rkey)
            if raw is not None:
                try:
                    result[short_key] = json.loads(raw)
                except json.JSONDecodeError:
                    result[short_key] = raw.decode() if isinstance(raw, bytes) else raw

        return result

    async def delete(
        self,
        conversation_id: uuid.UUID | str,
        key: str,
    ) -> None:
        """Remove a single key."""
        rkey = self._rkey(conversation_id, key)
        await self._redis.delete(rkey)

    async def clear(
        self,
        conversation_id: uuid.UUID | str,
    ) -> int:
        """Remove all session keys for a conversation.  Returns count deleted."""
        pattern = f"{_KEY_PREFIX}{conversation_id}:*"
        keys: list[bytes] = []
        async for rkey in self._redis.scan_iter(match=pattern, count=100):
            keys.append(rkey)
        if keys:
            deleted = await self._redis.delete(*keys)
            logger.info(
                "session_clear",
                conversation_id=str(conversation_id),
                keys_deleted=deleted,
            )
            return int(deleted)
        return 0

    async def extend_ttl(
        self,
        conversation_id: uuid.UUID | str,
        key: str,
        ttl: int = _DEFAULT_TTL_SECONDS,
    ) -> None:
        """Refresh the TTL on an existing key (useful when conversation is active)."""
        rkey = self._rkey(conversation_id, key)
        await self._redis.expire(rkey, ttl)

    # ------------------------------------------------------------------
    # Convenience: conversation turn counter
    # ------------------------------------------------------------------

    async def increment_turn(
        self,
        conversation_id: uuid.UUID | str,
        ttl: int = _DEFAULT_TTL_SECONDS,
    ) -> int:
        """Atomically increment and return the turn count for the conversation."""
        rkey = self._rkey(conversation_id, "turn_count")
        count = await self._redis.incr(rkey)
        await self._redis.expire(rkey, ttl)
        return int(count)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    @staticmethod
    def _rkey(conversation_id: uuid.UUID | str, key: str) -> str:
        return f"{_KEY_PREFIX}{conversation_id}:{key}"
