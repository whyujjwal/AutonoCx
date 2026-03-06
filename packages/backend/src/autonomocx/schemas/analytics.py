"""Analytics & dashboard schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from autonomocx.models.conversation import ChannelType, ConversationStatus, Priority


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------


class DashboardData(BaseModel):
    total_conversations: int = Field(
        ..., description="Total conversations in the selected period"
    )
    autonomous_resolutions: int = Field(
        ..., description="Conversations resolved without human intervention"
    )
    escalation_rate: float = Field(
        ..., ge=0.0, le=1.0, description="Fraction of conversations escalated to humans"
    )
    avg_resolution_seconds: Optional[float] = Field(
        None, description="Mean time to resolution in seconds"
    )
    avg_satisfaction: Optional[float] = Field(
        None, ge=0.0, le=5.0, description="Average CSAT score (0-5)"
    )
    total_actions: int = Field(
        ..., description="Total tool actions executed"
    )
    action_success_rate: float = Field(
        ..., ge=0.0, le=1.0, description="Fraction of actions that completed successfully"
    )
    cost_per_ticket: Optional[float] = Field(
        None, ge=0.0, description="Average LLM cost per conversation in USD"
    )
    hallucination_rate: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Estimated fraction of responses flagged as hallucinations",
    )


# ---------------------------------------------------------------------------
# Time-series
# ---------------------------------------------------------------------------


class MetricsTimeSeriesPoint(BaseModel):
    timestamp: datetime
    value: float


# ---------------------------------------------------------------------------
# Conversation-level metrics
# ---------------------------------------------------------------------------


class ConversationMetrics(BaseModel):
    total: int
    by_channel: dict[ChannelType, int] = Field(
        default_factory=dict,
        description="Conversation count broken down by channel",
    )
    by_status: dict[ConversationStatus, int] = Field(
        default_factory=dict,
        description="Conversation count broken down by status",
    )
    by_priority: dict[Priority, int] = Field(
        default_factory=dict,
        description="Conversation count broken down by priority",
    )
    resolution_time_series: list[MetricsTimeSeriesPoint] = Field(
        default_factory=list,
        description="Average resolution time over time buckets",
    )


# ---------------------------------------------------------------------------
# Cost breakdown
# ---------------------------------------------------------------------------


class CostBreakdown(BaseModel):
    total_cost: float = Field(..., ge=0.0, description="Total cost in USD")
    by_provider: dict[str, float] = Field(
        default_factory=dict,
        description="Cost broken down by LLM provider",
    )
    by_model: dict[str, float] = Field(
        default_factory=dict,
        description="Cost broken down by model name",
    )
    cost_per_conversation: Optional[float] = Field(
        None, ge=0.0, description="Average cost per conversation in USD"
    )
