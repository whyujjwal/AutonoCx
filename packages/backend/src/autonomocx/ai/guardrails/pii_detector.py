"""PII detection and masking using regex patterns.

Detects: emails, phone numbers, SSNs, credit card numbers, IP addresses,
and dates of birth.  Provides a ``mask`` method to replace detected PII
with ``[REDACTED]`` tokens.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import structlog

logger = structlog.get_logger(__name__)


@dataclass(frozen=True, slots=True)
class PIIMatch:
    """A single PII occurrence found in text."""

    type: str  # email, phone, ssn, credit_card, ip_address, date_of_birth
    value: str
    start: int
    end: int
    confidence: float = 0.9


# ------------------------------------------------------------------
# Patterns
# ------------------------------------------------------------------

_PII_PATTERNS: list[tuple[str, re.Pattern[str], float]] = [
    # Credit card numbers (Visa, MC, Amex, Discover -- 13-19 digits)
    (
        "credit_card",
        re.compile(
            r"\b(?:"
            r"4[0-9]{12}(?:[0-9]{3})?|"  # Visa
            r"5[1-5][0-9]{14}|"  # MasterCard
            r"3[47][0-9]{13}|"  # Amex
            r"6(?:011|5[0-9]{2})[0-9]{12}"  # Discover
            r")\b"
        ),
        0.95,
    ),
    # Credit card with separators
    (
        "credit_card",
        re.compile(r"\b(?:\d{4}[\s\-]\d{4}[\s\-]\d{4}[\s\-]\d{4})\b"),
        0.92,
    ),
    # SSN (US Social Security Number)
    (
        "ssn",
        re.compile(r"\b\d{3}[\-\s]?\d{2}[\-\s]?\d{4}\b"),
        0.85,
    ),
    # Email
    (
        "email",
        re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b"),
        0.95,
    ),
    # Phone numbers (international and US)
    (
        "phone",
        re.compile(
            r"(?:\+?\d{1,3}[\s\-.]?)?"
            r"(?:\(?\d{2,4}\)?[\s\-.]?)"
            r"\d{3,4}[\s\-.]?\d{3,4}\b"
        ),
        0.80,
    ),
    # IP addresses (IPv4)
    (
        "ip_address",
        re.compile(
            r"\b(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}"
            r"(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\b"
        ),
        0.90,
    ),
    # Date of birth (common formats)
    (
        "date_of_birth",
        re.compile(
            r"\b(?:DOB|date of birth|born|birthday)[:\s]*"
            r"(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})",
            re.IGNORECASE,
        ),
        0.85,
    ),
]


# ------------------------------------------------------------------
# Detector
# ------------------------------------------------------------------


class PIIDetector:
    """Detect and optionally mask personally identifiable information in text."""

    def detect(self, text: str) -> list[PIIMatch]:
        """Scan *text* and return all PII matches found."""
        if not text:
            return []

        matches: list[PIIMatch] = []
        seen_spans: set[tuple[int, int]] = set()

        for pii_type, pattern, confidence in _PII_PATTERNS:
            for m in pattern.finditer(text):
                span = (m.start(), m.end())
                # Avoid overlapping matches
                if any(self._overlaps(span, s) for s in seen_spans):
                    continue
                seen_spans.add(span)

                # Additional validation for SSNs to reduce false positives
                if pii_type == "ssn" and not self._validate_ssn(m.group()):
                    continue

                matches.append(
                    PIIMatch(
                        type=pii_type,
                        value=m.group(),
                        start=m.start(),
                        end=m.end(),
                        confidence=confidence,
                    )
                )

        # Sort by position
        matches.sort(key=lambda pm: pm.start)
        return matches

    def mask(self, text: str, replacement: str = "[REDACTED]") -> str:
        """Replace all detected PII in *text* with *replacement*."""
        if not text:
            return text

        pii_matches = self.detect(text)
        if not pii_matches:
            return text

        # Replace from the end so indices remain valid
        result = text
        for match in reversed(pii_matches):
            result = result[: match.start] + replacement + result[match.end :]

        logger.debug("pii_masked", count=len(pii_matches), types=[m.type for m in pii_matches])
        return result

    def has_pii(self, text: str) -> bool:
        """Quick check: does the text contain any PII?"""
        return len(self.detect(text)) > 0

    def summary(self, text: str) -> dict[str, int]:
        """Return a count of each PII type found."""
        matches = self.detect(text)
        counts: dict[str, int] = {}
        for m in matches:
            counts[m.type] = counts.get(m.type, 0) + 1
        return counts

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _overlaps(a: tuple[int, int], b: tuple[int, int]) -> bool:
        return a[0] < b[1] and b[0] < a[1]

    @staticmethod
    def _validate_ssn(value: str) -> bool:
        """Additional SSN validation to reduce false positives."""
        digits = re.sub(r"[\-\s]", "", value)
        if len(digits) != 9:
            return False
        # SSN cannot start with 000, 666, or 9xx
        area = int(digits[:3])
        if area == 0 or area == 666 or area >= 900:
            return False
        # Group and serial cannot be 0
        group = int(digits[3:5])
        serial = int(digits[5:])
        if group == 0 or serial == 0:
            return False
        return True
