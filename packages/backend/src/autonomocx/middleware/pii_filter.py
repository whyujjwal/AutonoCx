"""PII masking processor for structlog.

This module provides a structlog processor that scrubs personally
identifiable information (PII) from log event values *before* they are
serialised.  It handles:

* Email addresses
* US phone numbers (various formats)
* US Social Security Numbers
* Credit-card numbers (basic Luhn-length patterns)
* IP addresses (v4)
* Bearer tokens in ``Authorization`` headers

The processor is intentionally conservative -- it prefers false-positives
(masking something that is not PII) over false-negatives (leaking real
PII into logs).

Usage::

    import structlog
    from autonomocx.middleware.pii_filter import pii_masking_processor

    structlog.configure(
        processors=[
            ...,
            pii_masking_processor,
            ...,
        ],
    )

It can also be used standalone::

    from autonomocx.middleware.pii_filter import mask_pii
    clean = mask_pii("Contact me at user@example.com")
    # => "Contact me at ***EMAIL***"
"""

from __future__ import annotations

import re
from typing import Any

# ── Compiled patterns ──────────────────────────────────────────────────

# Order matters: more specific patterns should be checked first.
_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    # SSN: 123-45-6789
    (re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), "***SSN***"),
    # Credit-card-like (13-19 digits, optionally separated by dashes/spaces)
    (re.compile(r"\b(?:\d[ -]*?){13,19}\b"), "***CARD***"),
    # Email
    (re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"), "***EMAIL***"),
    # US phone: +1-234-567-8901, (234) 567-8901, 234-567-8901, 2345678901
    (
        re.compile(
            r"(?:\+?1[-.\s]?)?"
            r"(?:\(\d{3}\)|\d{3})[-.\s]?"
            r"\d{3}[-.\s]?\d{4}\b"
        ),
        "***PHONE***",
    ),
    # IPv4
    (re.compile(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b"), "***IP***"),
    # Bearer tokens
    (re.compile(r"Bearer\s+[A-Za-z0-9\-._~+/]+=*", re.IGNORECASE), "Bearer ***TOKEN***"),
]

# Keys whose values should be fully masked regardless of pattern matches.
_SENSITIVE_KEYS: frozenset[str] = frozenset(
    {
        "password",
        "passwd",
        "secret",
        "token",
        "access_token",
        "refresh_token",
        "api_key",
        "apikey",
        "authorization",
        "credit_card",
        "ssn",
        "social_security",
    }
)


# ── Public helpers ─────────────────────────────────────────────────────


def mask_pii(value: str) -> str:
    """Return *value* with PII patterns replaced by placeholder labels."""
    for pattern, replacement in _PATTERNS:
        value = pattern.sub(replacement, value)
    return value


def _mask_value(key: str, value: Any) -> Any:
    """Mask a single value based on its key name and/or content."""
    # If the key itself is sensitive, redact entirely.
    if key.lower() in _SENSITIVE_KEYS:
        return "***REDACTED***"

    if isinstance(value, str):
        return mask_pii(value)

    if isinstance(value, dict):
        return {k: _mask_value(k, v) for k, v in value.items()}

    if isinstance(value, (list, tuple)):
        return type(value)(_mask_value(key, item) for item in value)

    return value


# ── Structlog processor ───────────────────────────────────────────────


def pii_masking_processor(
    logger: Any,
    method_name: str,
    event_dict: dict[str, Any],
) -> dict[str, Any]:
    """Structlog processor that scrubs PII from all event dict values."""
    return {k: _mask_value(k, v) for k, v in event_dict.items()}
