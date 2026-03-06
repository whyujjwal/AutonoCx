"""Sentiment analysis and urgency detection."""

from __future__ import annotations

import enum
import json
from dataclasses import dataclass

import structlog

from autonomocx.ai.llm.base import LLMRequest, LLMResponse
from autonomocx.ai.llm.router import LLMRouter

logger = structlog.get_logger(__name__)


# ------------------------------------------------------------------
# Data models
# ------------------------------------------------------------------


class Sentiment(enum.StrEnum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"


class UrgencyLevel(enum.StrEnum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


@dataclass(frozen=True, slots=True)
class SentimentResult:
    sentiment: Sentiment
    score: float  # -1.0 (very negative) to 1.0 (very positive)
    explanation: str = ""


@dataclass(frozen=True, slots=True)
class UrgencyResult:
    level: UrgencyLevel
    score: float  # 0.0 to 1.0
    indicators: list[str]


# ------------------------------------------------------------------
# Prompts
# ------------------------------------------------------------------

_SENTIMENT_SYSTEM = """\
You are a sentiment analysis engine for customer-support messages.

Analyse the customer message and return a JSON object with:
- "sentiment": one of "positive", "neutral", "negative"
- "score": a float from -1.0 (extremely negative) to 1.0 (extremely positive)
- "explanation": a brief one-sentence explanation

Respond ONLY with valid JSON.  No markdown fences.
"""

_URGENCY_SYSTEM = """\
You are an urgency detection engine for customer-support messages.

Given the customer message and any available context, return a JSON object:
- "level": one of "low", "normal", "high", "urgent"
- "score": a float from 0.0 (not urgent at all) to 1.0 (extremely urgent)
- "indicators": a list of strings naming the urgency signals you detected \
(e.g., "time_pressure", "emotional_distress", "financial_impact", \
"service_outage", "legal_mention", "escalation_request")

Respond ONLY with valid JSON.  No markdown fences.
"""


# ------------------------------------------------------------------
# Analyser
# ------------------------------------------------------------------


class SentimentAnalyser:
    """Analyse customer message sentiment and urgency using an LLM."""

    def __init__(self, llm_router: LLMRouter) -> None:
        self._router = llm_router

    async def analyze_sentiment(self, message: str) -> SentimentResult:
        """Return sentiment classification for *message*."""
        request = LLMRequest(
            messages=[
                {"role": "system", "content": _SENTIMENT_SYSTEM},
                {"role": "user", "content": message},
            ],
            temperature=0.0,
            max_tokens=256,
        )
        try:
            response: LLMResponse = await self._router.route(request)
            return self._parse_sentiment(response.content)
        except Exception:
            logger.exception("sentiment_analysis_failed", message=message[:120])
            return SentimentResult(sentiment=Sentiment.NEUTRAL, score=0.0)

    async def detect_urgency(
        self,
        message: str,
        context: str | None = None,
    ) -> UrgencyResult:
        """Detect urgency level for *message* with optional context."""
        user_content = message
        if context:
            user_content = f"Context: {context}\n\nCustomer message: {message}"

        request = LLMRequest(
            messages=[
                {"role": "system", "content": _URGENCY_SYSTEM},
                {"role": "user", "content": user_content},
            ],
            temperature=0.0,
            max_tokens=256,
        )
        try:
            response: LLMResponse = await self._router.route(request)
            return self._parse_urgency(response.content)
        except Exception:
            logger.exception("urgency_detection_failed", message=message[:120])
            return UrgencyResult(level=UrgencyLevel.NORMAL, score=0.3, indicators=[])

    # ------------------------------------------------------------------
    # Parsing helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _clean_json(raw: str) -> str:
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[-1]
        if cleaned.endswith("```"):
            cleaned = cleaned.rsplit("```", 1)[0]
        return cleaned.strip()

    def _parse_sentiment(self, raw: str) -> SentimentResult:
        try:
            data = json.loads(self._clean_json(raw))
        except json.JSONDecodeError:
            logger.warning("sentiment_parse_failed", raw=raw[:200])
            return SentimentResult(sentiment=Sentiment.NEUTRAL, score=0.0)

        try:
            sentiment = Sentiment(data.get("sentiment", "neutral"))
        except ValueError:
            sentiment = Sentiment.NEUTRAL

        return SentimentResult(
            sentiment=sentiment,
            score=float(data.get("score", 0.0)),
            explanation=data.get("explanation", ""),
        )

    def _parse_urgency(self, raw: str) -> UrgencyResult:
        try:
            data = json.loads(self._clean_json(raw))
        except json.JSONDecodeError:
            logger.warning("urgency_parse_failed", raw=raw[:200])
            return UrgencyResult(level=UrgencyLevel.NORMAL, score=0.3, indicators=[])

        try:
            level = UrgencyLevel(data.get("level", "normal"))
        except ValueError:
            level = UrgencyLevel.NORMAL

        return UrgencyResult(
            level=level,
            score=float(data.get("score", 0.3)),
            indicators=data.get("indicators", []),
        )
