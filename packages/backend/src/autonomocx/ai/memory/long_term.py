"""Database-backed long-term customer memory.

Stores persistent facts, preferences, and interaction summaries that survive
across conversations, backed by the ``customer_memories`` table.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import Sequence

import structlog
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from autonomocx.models.analytics import CustomerMemory, MemoryType

logger = structlog.get_logger(__name__)


class LongTermMemory:
    """CRUD interface over the ``customer_memories`` table."""

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    async def store_memory(
        self,
        db: AsyncSession,
        *,
        org_id: uuid.UUID,
        customer_id: str,
        memory_type: MemoryType | str,
        content: str,
        source: str | None = None,
        confidence: float | None = None,
        expires_at: datetime | None = None,
    ) -> CustomerMemory:
        """Create (or update if duplicate content exists) a customer memory."""
        if isinstance(memory_type, str):
            memory_type = MemoryType(memory_type)

        # Check for duplicate content to avoid re-storing the same memory
        existing = await self._find_exact(db, org_id, customer_id, content)
        if existing:
            logger.debug(
                "long_term_memory_duplicate",
                customer_id=customer_id,
                memory_id=str(existing.id),
            )
            return existing

        memory = CustomerMemory(
            org_id=org_id,
            customer_id=customer_id,
            memory_type=memory_type,
            content=content,
            source=source,
            confidence=confidence,
            expires_at=expires_at,
        )
        db.add(memory)
        await db.flush()
        logger.info(
            "long_term_memory_stored",
            memory_id=str(memory.id),
            customer_id=customer_id,
            type=memory_type.value,
        )
        return memory

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    async def get_memories(
        self,
        db: AsyncSession,
        org_id: uuid.UUID,
        customer_id: str,
        *,
        memory_types: list[MemoryType] | None = None,
        limit: int = 50,
    ) -> Sequence[CustomerMemory]:
        """Return all non-expired memories for a customer, newest first."""
        now = datetime.utcnow()
        conditions = [
            CustomerMemory.org_id == org_id,
            CustomerMemory.customer_id == customer_id,
            or_(
                CustomerMemory.expires_at.is_(None),
                CustomerMemory.expires_at > now,
            ),
        ]
        if memory_types:
            conditions.append(CustomerMemory.memory_type.in_(memory_types))

        stmt = (
            select(CustomerMemory)
            .where(and_(*conditions))
            .order_by(CustomerMemory.created_at.desc())
            .limit(limit)
        )
        result = await db.execute(stmt)
        return result.scalars().all()

    async def search_memories(
        self,
        db: AsyncSession,
        org_id: uuid.UUID,
        customer_id: str,
        query: str,
        *,
        limit: int = 10,
    ) -> Sequence[CustomerMemory]:
        """Simple text search over customer memories using ILIKE."""
        now = datetime.utcnow()
        stmt = (
            select(CustomerMemory)
            .where(
                and_(
                    CustomerMemory.org_id == org_id,
                    CustomerMemory.customer_id == customer_id,
                    CustomerMemory.content.ilike(f"%{query}%"),
                    or_(
                        CustomerMemory.expires_at.is_(None),
                        CustomerMemory.expires_at > now,
                    ),
                )
            )
            .order_by(CustomerMemory.created_at.desc())
            .limit(limit)
        )
        result = await db.execute(stmt)
        return result.scalars().all()

    # ------------------------------------------------------------------
    # Delete / cleanup
    # ------------------------------------------------------------------

    async def delete_expired(
        self,
        db: AsyncSession,
        org_id: uuid.UUID,
    ) -> int:
        """Remove all expired memories for an organisation.  Returns count deleted."""
        from sqlalchemy import delete as sa_delete

        now = datetime.utcnow()
        stmt = (
            sa_delete(CustomerMemory)
            .where(
                and_(
                    CustomerMemory.org_id == org_id,
                    CustomerMemory.expires_at.isnot(None),
                    CustomerMemory.expires_at <= now,
                )
            )
        )
        result = await db.execute(stmt)
        count = result.rowcount  # type: ignore[union-attr]
        if count:
            logger.info("long_term_memory_cleanup", org_id=str(org_id), deleted=count)
        return count

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    @staticmethod
    async def _find_exact(
        db: AsyncSession,
        org_id: uuid.UUID,
        customer_id: str,
        content: str,
    ) -> CustomerMemory | None:
        stmt = (
            select(CustomerMemory)
            .where(
                and_(
                    CustomerMemory.org_id == org_id,
                    CustomerMemory.customer_id == customer_id,
                    CustomerMemory.content == content,
                )
            )
            .limit(1)
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()
