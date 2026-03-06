"""Unit tests for risk scoring logic.

These tests validate the risk scoring heuristics used by the guardrails
system to determine whether an agent action requires human approval.
"""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("APP_ENV", "test")

from autonomocx.models.tool import RiskLevel


# ---------------------------------------------------------------------------
# Risk scoring utility (inline implementation for testing)
# ---------------------------------------------------------------------------
# In production this would live in a dedicated service module.  We define it
# here so the tests are self-contained until the service is built out.


def compute_risk_score(
    *,
    tool_risk_level: RiskLevel,
    involves_pii: bool = False,
    monetary_value: float = 0.0,
    is_irreversible: bool = False,
    confidence: float = 1.0,
) -> float:
    """Compute a composite risk score in the range [0.0, 1.0].

    The score is a weighted combination of:
    - Tool's inherent risk level
    - Whether PII is involved
    - Monetary value of the action
    - Irreversibility of the action
    - Model confidence (lower confidence = higher risk)

    A score above the configured threshold (default 0.7) should trigger
    human-in-the-loop approval.
    """
    # Base score from tool risk level
    risk_level_scores = {
        RiskLevel.LOW: 0.1,
        RiskLevel.MEDIUM: 0.4,
        RiskLevel.HIGH: 0.7,
        RiskLevel.CRITICAL: 0.95,
    }
    base = risk_level_scores.get(tool_risk_level, 0.5)

    # PII modifier
    pii_modifier = 0.15 if involves_pii else 0.0

    # Monetary modifier (scales with amount)
    if monetary_value > 1000:
        money_modifier = 0.2
    elif monetary_value > 100:
        money_modifier = 0.1
    elif monetary_value > 0:
        money_modifier = 0.05
    else:
        money_modifier = 0.0

    # Irreversibility modifier
    irreversible_modifier = 0.15 if is_irreversible else 0.0

    # Confidence modifier (inverted: low confidence = more risk)
    confidence_modifier = max(0.0, (1.0 - confidence) * 0.2)

    score = base + pii_modifier + money_modifier + irreversible_modifier + confidence_modifier
    return min(1.0, max(0.0, round(score, 4)))


def requires_approval(score: float, threshold: float = 0.7) -> bool:
    """Return ``True`` if the risk score exceeds the approval threshold."""
    return score >= threshold


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestRiskScoring:
    """Tests for the ``compute_risk_score`` function."""

    def test_low_risk_tool_scores_low(self):
        score = compute_risk_score(tool_risk_level=RiskLevel.LOW)
        assert score == 0.1
        assert not requires_approval(score)

    def test_critical_risk_tool_scores_high(self):
        score = compute_risk_score(tool_risk_level=RiskLevel.CRITICAL)
        assert score >= 0.9
        assert requires_approval(score)

    def test_pii_increases_score(self):
        without_pii = compute_risk_score(tool_risk_level=RiskLevel.LOW)
        with_pii = compute_risk_score(tool_risk_level=RiskLevel.LOW, involves_pii=True)
        assert with_pii > without_pii

    def test_monetary_value_increases_score(self):
        no_money = compute_risk_score(tool_risk_level=RiskLevel.MEDIUM)
        with_money = compute_risk_score(tool_risk_level=RiskLevel.MEDIUM, monetary_value=500)
        high_money = compute_risk_score(tool_risk_level=RiskLevel.MEDIUM, monetary_value=5000)
        assert with_money > no_money
        assert high_money > with_money

    def test_irreversible_increases_score(self):
        reversible = compute_risk_score(tool_risk_level=RiskLevel.MEDIUM)
        irreversible = compute_risk_score(
            tool_risk_level=RiskLevel.MEDIUM, is_irreversible=True
        )
        assert irreversible > reversible

    def test_low_confidence_increases_score(self):
        high_conf = compute_risk_score(tool_risk_level=RiskLevel.MEDIUM, confidence=0.95)
        low_conf = compute_risk_score(tool_risk_level=RiskLevel.MEDIUM, confidence=0.3)
        assert low_conf > high_conf

    def test_combined_modifiers_cap_at_one(self):
        score = compute_risk_score(
            tool_risk_level=RiskLevel.CRITICAL,
            involves_pii=True,
            monetary_value=10000,
            is_irreversible=True,
            confidence=0.1,
        )
        assert score == 1.0

    def test_score_is_always_between_zero_and_one(self):
        for level in RiskLevel:
            for pii in [True, False]:
                for money in [0, 50, 200, 5000]:
                    score = compute_risk_score(
                        tool_risk_level=level,
                        involves_pii=pii,
                        monetary_value=money,
                    )
                    assert 0.0 <= score <= 1.0

    def test_medium_risk_with_pii_triggers_approval(self):
        score = compute_risk_score(
            tool_risk_level=RiskLevel.MEDIUM,
            involves_pii=True,
            monetary_value=200,
            is_irreversible=True,
        )
        assert requires_approval(score)

    def test_threshold_boundary(self):
        assert requires_approval(0.7) is True
        assert requires_approval(0.69) is False
        assert requires_approval(0.7, threshold=0.71) is False
