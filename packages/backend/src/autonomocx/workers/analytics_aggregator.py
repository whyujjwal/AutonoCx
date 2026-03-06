"""Periodic metric rollup worker.

Aggregates raw conversation and action data into ``MetricSnapshot``
rows at regular intervals (hourly, daily).  These pre-aggregated
snapshots power the analytics dashboard without requiring expensive
real-time queries.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from autonomocx.models.action import ActionExecution, ActionStatus
from autonomocx.models.analytics import MetricPeriod, MetricSnapshot
from autonomocx.models.conversation import Conversation, ConversationStatus, Message

logger = structlog.get_logger(__name__)


class AnalyticsAggregator:
    """Aggregates operational metrics into periodic snapshots."""

    async def generate_hourly_snapshot(
        self,
        db: AsyncSession,
        org_id: uuid.UUID,
        *,
        hour: datetime | None = None,
    ) -> MetricSnapshot:
        """Generate an hourly metric snapshot for an organization.

        If *hour* is not provided, the previous complete hour is used.

        Metrics collected:
            - total_conversations: conversations started in the period
            - resolved_conversations: conversations resolved in the period
            - avg_resolution_time_seconds: average time to resolution
            - total_messages: messages sent/received
            - total_actions: tool actions executed
            - actions_approved: actions that required and received approval
            - actions_rejected: actions that were rejected
            - escalation_count: conversations escalated to human agents
        """
        if hour is None:
            now = datetime.now(UTC)
            hour = now.replace(minute=0, second=0, microsecond=0) - timedelta(hours=1)

        period_start = hour
        period_end = hour + timedelta(hours=1)

        logger.info(
            "generating_hourly_snapshot",
            org_id=str(org_id),
            period_start=period_start.isoformat(),
            period_end=period_end.isoformat(),
        )

        metrics = await self._collect_metrics(db, org_id, period_start, period_end)

        snapshot = MetricSnapshot(
            id=uuid.uuid4(),
            org_id=org_id,
            period=MetricPeriod.HOURLY,
            period_start=period_start,
            period_end=period_end,
            metrics=metrics,
        )
        db.add(snapshot)
        await db.commit()

        logger.info(
            "hourly_snapshot_generated",
            org_id=str(org_id),
            snapshot_id=str(snapshot.id),
            metrics=metrics,
        )
        return snapshot

    async def generate_daily_snapshot(
        self,
        db: AsyncSession,
        org_id: uuid.UUID,
        *,
        day: datetime | None = None,
    ) -> MetricSnapshot:
        """Generate a daily metric snapshot by aggregating hourly snapshots.

        If *day* is not provided, the previous complete day is used.
        """
        if day is None:
            now = datetime.now(UTC)
            day = (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)

        period_start = day
        period_end = day + timedelta(days=1)

        metrics = await self._collect_metrics(db, org_id, period_start, period_end)

        snapshot = MetricSnapshot(
            id=uuid.uuid4(),
            org_id=org_id,
            period=MetricPeriod.DAILY,
            period_start=period_start,
            period_end=period_end,
            metrics=metrics,
        )
        db.add(snapshot)
        await db.commit()

        logger.info(
            "daily_snapshot_generated",
            org_id=str(org_id),
            snapshot_id=str(snapshot.id),
        )
        return snapshot

    async def _collect_metrics(
        self,
        db: AsyncSession,
        org_id: uuid.UUID,
        period_start: datetime,
        period_end: datetime,
    ) -> dict[str, Any]:
        """Query the database and compute metrics for a time period.

        Returns a dictionary of metric name -> value pairs.
        """
        # -- Conversations --------------------------------------------------
        conv_result = await db.execute(
            select(func.count(Conversation.id)).where(
                Conversation.org_id == org_id,
                Conversation.created_at >= period_start,
                Conversation.created_at < period_end,
            )
        )
        total_conversations = conv_result.scalar() or 0

        resolved_result = await db.execute(
            select(func.count(Conversation.id)).where(
                Conversation.org_id == org_id,
                Conversation.status == ConversationStatus.RESOLVED,
                Conversation.updated_at >= period_start,
                Conversation.updated_at < period_end,
            )
        )
        resolved_conversations = resolved_result.scalar() or 0

        # -- Messages -------------------------------------------------------
        msg_result = await db.execute(
            select(func.count(Message.id)).where(
                Message.created_at >= period_start,
                Message.created_at < period_end,
            )
        )
        total_messages = msg_result.scalar() or 0

        # -- Actions --------------------------------------------------------
        action_result = await db.execute(
            select(func.count(ActionExecution.id)).where(
                ActionExecution.org_id == org_id,
                ActionExecution.created_at >= period_start,
                ActionExecution.created_at < period_end,
            )
        )
        total_actions = action_result.scalar() or 0

        approved_result = await db.execute(
            select(func.count(ActionExecution.id)).where(
                ActionExecution.org_id == org_id,
                ActionExecution.status == ActionStatus.APPROVED,
                ActionExecution.created_at >= period_start,
                ActionExecution.created_at < period_end,
            )
        )
        actions_approved = approved_result.scalar() or 0

        rejected_result = await db.execute(
            select(func.count(ActionExecution.id)).where(
                ActionExecution.org_id == org_id,
                ActionExecution.status == ActionStatus.REJECTED,
                ActionExecution.created_at >= period_start,
                ActionExecution.created_at < period_end,
            )
        )
        actions_rejected = rejected_result.scalar() or 0

        # -- Escalations (conversations assigned to a human) ----------------
        escalation_result = await db.execute(
            select(func.count(Conversation.id)).where(
                Conversation.org_id == org_id,
                Conversation.assigned_to.isnot(None),
                Conversation.updated_at >= period_start,
                Conversation.updated_at < period_end,
            )
        )
        escalation_count = escalation_result.scalar() or 0

        return {
            "total_conversations": total_conversations,
            "resolved_conversations": resolved_conversations,
            "resolution_rate": (
                round(resolved_conversations / total_conversations, 4)
                if total_conversations > 0
                else 0.0
            ),
            "total_messages": total_messages,
            "total_actions": total_actions,
            "actions_approved": actions_approved,
            "actions_rejected": actions_rejected,
            "escalation_count": escalation_count,
            "escalation_rate": (
                round(escalation_count / total_conversations, 4) if total_conversations > 0 else 0.0
            ),
        }

    async def run_all_orgs_hourly(self, db: AsyncSession) -> int:
        """Generate hourly snapshots for every active organization.

        Returns the number of snapshots created.
        """
        from autonomocx.models.organization import Organization

        result = await db.execute(select(Organization.id).where(Organization.is_active.is_(True)))
        org_ids = [row[0] for row in result.all()]

        count = 0
        for org_id in org_ids:
            try:
                await self.generate_hourly_snapshot(db, org_id)
                count += 1
            except Exception as exc:
                logger.exception(
                    "hourly_snapshot_failed",
                    org_id=str(org_id),
                    error=str(exc),
                )
        return count
