"""Named entity extraction from customer messages.

Uses a combination of regex-based fast extraction and optional LLM-based
extraction for complex or ambiguous cases.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

import structlog

logger = structlog.get_logger(__name__)


# ------------------------------------------------------------------
# Data models
# ------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Entity:
    """A single extracted entity."""

    type: str  # order_id, email, phone, amount, date, product, tracking_number, name
    value: str
    confidence: float  # 0.0 - 1.0
    start: int = -1  # char offset in original text (-1 if unknown)
    end: int = -1


@dataclass(slots=True)
class ExtractionResult:
    """Collection of entities extracted from a message."""

    entities: list[Entity] = field(default_factory=list)
    raw_text: str = ""

    def by_type(self, entity_type: str) -> list[Entity]:
        return [e for e in self.entities if e.type == entity_type]

    def first(self, entity_type: str) -> Entity | None:
        matches = self.by_type(entity_type)
        return matches[0] if matches else None


# ------------------------------------------------------------------
# Regex patterns
# ------------------------------------------------------------------

_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    # Email
    ("email", re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b")),
    # Phone (international, US, common formats)
    (
        "phone",
        re.compile(
            r"(?:\+?\d{1,3}[\s\-.]?)?"
            r"(?:\(?\d{2,4}\)?[\s\-.]?)"
            r"\d{3,4}[\s\-.]?\d{3,4}\b"
        ),
    ),
    # Order ID (common patterns: ORD-12345, #12345, ORDER-ABC-123)
    (
        "order_id",
        re.compile(
            r"\b(?:ORD|ORDER|INV|INVOICE)[#\-_]?\s*[A-Z0-9\-]{4,20}\b",
            re.IGNORECASE,
        ),
    ),
    # Tracking number (common carrier patterns)
    (
        "tracking_number",
        re.compile(
            r"\b(?:1Z[A-Z0-9]{16}|"  # UPS
            r"\d{12,22}|"  # FedEx/USPS
            r"[A-Z]{2}\d{9}[A-Z]{2})\b"  # International
        ),
    ),
    # Currency amount ($12.34, USD 100, 50.00 EUR)
    (
        "amount",
        re.compile(
            r"(?:(?:USD|EUR|GBP|CAD|AUD)\s*)?[\$\u20AC\u00A3]?\s*\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?"
            r"(?:\s*(?:USD|EUR|GBP|CAD|AUD|dollars?|euros?|pounds?))?",
            re.IGNORECASE,
        ),
    ),
    # Date (various common formats)
    (
        "date",
        re.compile(
            r"\b(?:"
            r"\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4}|"
            r"\d{4}[/\-\.]\d{1,2}[/\-\.]\d{1,2}|"
            r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2},?\s+\d{4}|"
            r"\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{4}"
            r")\b",
            re.IGNORECASE,
        ),
    ),
]


# ------------------------------------------------------------------
# Extractor
# ------------------------------------------------------------------


class EntityExtractor:
    """Extract named entities from text using regex-based pattern matching.

    This provides fast, reliable extraction without needing an LLM call.
    For ambiguous cases, the intent classifier's entity output can supplement.
    """

    def extract_entities(self, text: str) -> ExtractionResult:
        """Extract all recognised entities from *text*."""
        entities: list[Entity] = []
        seen_values: set[str] = set()

        for entity_type, pattern in _PATTERNS:
            for match in pattern.finditer(text):
                value = match.group().strip()
                # Deduplicate
                norm_value = value.lower()
                if norm_value in seen_values:
                    continue
                seen_values.add(norm_value)

                # Assign confidence based on pattern specificity
                confidence = self._confidence_for(entity_type, value)
                entities.append(
                    Entity(
                        type=entity_type,
                        value=value,
                        confidence=confidence,
                        start=match.start(),
                        end=match.end(),
                    )
                )

        # Sort by position in text
        entities.sort(key=lambda e: e.start if e.start >= 0 else float("inf"))

        return ExtractionResult(entities=entities, raw_text=text)

    def merge_with_llm_entities(
        self,
        regex_result: ExtractionResult,
        llm_entities: list[dict],
    ) -> ExtractionResult:
        """Merge regex-extracted entities with LLM-extracted entities.

        LLM entities fill gaps for types the regex missed.  Regex entities
        are preferred when both extract the same value.
        """
        existing_values = {e.value.lower() for e in regex_result.entities}
        merged = list(regex_result.entities)

        for llm_ent in llm_entities:
            value = str(llm_ent.get("value", "")).strip()
            if not value or value.lower() in existing_values:
                continue
            merged.append(
                Entity(
                    type=llm_ent.get("type", "unknown"),
                    value=value,
                    confidence=float(llm_ent.get("confidence", 0.6)),
                )
            )
            existing_values.add(value.lower())

        return ExtractionResult(entities=merged, raw_text=regex_result.raw_text)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _confidence_for(entity_type: str, value: str) -> float:
        """Heuristic confidence based on type and value quality."""
        base_confidence: dict[str, float] = {
            "email": 0.95,
            "phone": 0.80,
            "order_id": 0.90,
            "tracking_number": 0.85,
            "amount": 0.85,
            "date": 0.80,
        }
        conf = base_confidence.get(entity_type, 0.70)

        # Boost for longer / more specific values
        if entity_type == "order_id" and len(value) >= 8:
            conf = min(conf + 0.05, 1.0)
        if entity_type == "phone" and len(value.replace(" ", "").replace("-", "")) >= 10:
            conf = min(conf + 0.10, 1.0)

        return conf
