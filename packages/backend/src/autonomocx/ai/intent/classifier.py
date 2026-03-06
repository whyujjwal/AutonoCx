"""Intent classification using LLM-based analysis."""

from __future__ import annotations

import json
from dataclasses import dataclass, field

import structlog

from autonomocx.ai.llm.base import LLMRequest, LLMResponse
from autonomocx.ai.llm.router import LLMRouter

logger = structlog.get_logger(__name__)

# ------------------------------------------------------------------
# Data models
# ------------------------------------------------------------------

_CLASSIFICATION_SYSTEM_PROMPT = """\
You are an intent classification engine for a customer-support AI platform.

Given a customer message and a list of available intents, classify the message
into the single best-matching intent.  Return a JSON object with these fields:

- "intent": the matched intent name (string) -- MUST be one of the available intents, \
or "unknown" if none match.
- "confidence": a float between 0.0 and 1.0 indicating classification confidence.
- "sub_intents": a list of secondary intents that might also apply (strings, possibly empty).
- "entities": a list of objects each with "type", "value", and "confidence".
  Recognised entity types: order_id, email, phone, amount, date, product, \
account_number, tracking_number, name.

Respond ONLY with valid JSON.  No markdown fences, no explanation.
"""

# Default intents when the caller does not provide a list
DEFAULT_INTENTS: list[str] = [
    "order_status",
    "refund_request",
    "cancel_subscription",
    "billing_inquiry",
    "technical_support",
    "account_update",
    "product_inquiry",
    "complaint",
    "feedback",
    "greeting",
    "farewell",
    "unknown",
]


@dataclass(frozen=True, slots=True)
class IntentResult:
    """Result of intent classification."""

    intent: str
    confidence: float
    sub_intents: list[str] = field(default_factory=list)
    entities: list[dict] = field(default_factory=list)
    raw_response: str = ""


# ------------------------------------------------------------------
# Classifier
# ------------------------------------------------------------------


class IntentClassifier:
    """Classify customer messages into intents using an LLM call."""

    def __init__(self, llm_router: LLMRouter) -> None:
        self._router = llm_router

    async def classify_intent(
        self,
        message: str,
        available_intents: list[str] | None = None,
        *,
        conversation_history: list[dict] | None = None,
    ) -> IntentResult:
        """Classify *message* against *available_intents* (defaults used if ``None``)."""
        intents = available_intents or DEFAULT_INTENTS

        user_prompt = f"Available intents: {json.dumps(intents)}\n\nCustomer message: {message}"

        # Optionally include recent conversation history for context
        messages: list[dict] = [
            {"role": "system", "content": _CLASSIFICATION_SYSTEM_PROMPT},
        ]
        if conversation_history:
            # Include last 3 turns for context
            for turn in conversation_history[-3:]:
                messages.append(turn)
        messages.append({"role": "user", "content": user_prompt})

        request = LLMRequest(
            messages=messages,
            temperature=0.0,
            max_tokens=512,
        )

        try:
            response: LLMResponse = await self._router.route(request)
            return self._parse_response(response.content)
        except Exception:
            logger.exception("intent_classification_failed", message=message[:120])
            return IntentResult(intent="unknown", confidence=0.0)

    # ------------------------------------------------------------------
    # Parsing
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_response(raw: str) -> IntentResult:
        """Parse the LLM JSON response into an IntentResult."""
        # Strip markdown fences if model includes them anyway
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[-1]
        if cleaned.endswith("```"):
            cleaned = cleaned.rsplit("```", 1)[0]
        cleaned = cleaned.strip()

        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError:
            logger.warning("intent_parse_failed", raw=raw[:200])
            return IntentResult(intent="unknown", confidence=0.0, raw_response=raw)

        return IntentResult(
            intent=data.get("intent", "unknown"),
            confidence=float(data.get("confidence", 0.0)),
            sub_intents=data.get("sub_intents", []),
            entities=data.get("entities", []),
            raw_response=raw,
        )
