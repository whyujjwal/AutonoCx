"""Unit tests for PII detection and masking.

Tests the ``mask_pii`` function and the structlog ``pii_masking_processor``
from ``autonomocx.middleware.pii_filter``.
"""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("APP_ENV", "test")

from autonomocx.middleware.pii_filter import mask_pii, pii_masking_processor


class TestEmailMasking:
    """Tests for email address detection and masking."""

    def test_masks_simple_email(self):
        result = mask_pii("Contact me at user@example.com please")
        assert "user@example.com" not in result
        assert "***EMAIL***" in result

    def test_masks_email_with_plus(self):
        result = mask_pii("Email: user+tag@example.com")
        assert "***EMAIL***" in result

    def test_masks_email_with_dots(self):
        result = mask_pii("first.last@company.co.uk")
        assert "***EMAIL***" in result

    def test_masks_multiple_emails(self):
        result = mask_pii("From a@b.com to c@d.org")
        assert result.count("***EMAIL***") == 2


class TestPhoneMasking:
    """Tests for phone number detection and masking."""

    def test_masks_us_phone_with_dashes(self):
        result = mask_pii("Call me at 234-567-8901")
        assert "234-567-8901" not in result
        assert "***PHONE***" in result

    def test_masks_phone_with_parens(self):
        result = mask_pii("Phone: (234) 567-8901")
        assert "***PHONE***" in result

    def test_masks_phone_with_country_code(self):
        result = mask_pii("Number: +1-234-567-8901")
        assert "***PHONE***" in result

    def test_masks_phone_with_dots(self):
        result = mask_pii("Reach me at 234.567.8901")
        assert "***PHONE***" in result


class TestSSNMasking:
    """Tests for Social Security Number detection and masking."""

    def test_masks_ssn(self):
        result = mask_pii("My SSN is 123-45-6789")
        assert "123-45-6789" not in result
        assert "***SSN***" in result

    def test_does_not_mask_non_ssn_pattern(self):
        # Date-like patterns should not be masked as SSN
        result = mask_pii("Date: 2024-01-15")
        assert "***SSN***" not in result


class TestCardMasking:
    """Tests for credit card number detection and masking."""

    def test_masks_card_with_spaces(self):
        result = mask_pii("Card: 4111 1111 1111 1111")
        assert "***CARD***" in result

    def test_masks_card_with_dashes(self):
        result = mask_pii("Card: 4111-1111-1111-1111")
        assert "***CARD***" in result


class TestIPMasking:
    """Tests for IP address detection and masking."""

    def test_masks_ipv4(self):
        result = mask_pii("Server IP: 192.168.1.100")
        assert "192.168.1.100" not in result
        assert "***IP***" in result

    def test_masks_localhost(self):
        result = mask_pii("Connect to 127.0.0.1")
        assert "***IP***" in result


class TestBearerTokenMasking:
    """Tests for Bearer token detection and masking."""

    def test_masks_bearer_token(self):
        result = mask_pii("Authorization: Bearer eyJhbGciOiJIUzI1NiJ9.payload.sig")
        assert "Bearer ***TOKEN***" in result
        assert "eyJhbGciOiJIUzI1NiJ9" not in result


class TestSensitiveKeyMasking:
    """Tests for sensitive key-based masking in the structlog processor."""

    def test_masks_password_key(self):
        event_dict = {"event": "login", "password": "supersecret"}
        result = pii_masking_processor(None, "info", event_dict)
        assert result["password"] == "***REDACTED***"

    def test_masks_api_key(self):
        event_dict = {"event": "init", "api_key": "sk-abc123"}
        result = pii_masking_processor(None, "info", event_dict)
        assert result["api_key"] == "***REDACTED***"

    def test_masks_token_key(self):
        event_dict = {"event": "auth", "token": "jwt-value"}
        result = pii_masking_processor(None, "info", event_dict)
        assert result["token"] == "***REDACTED***"

    def test_masks_nested_sensitive_keys(self):
        event_dict = {
            "event": "request",
            "headers": {"authorization": "Bearer xyz"},
        }
        result = pii_masking_processor(None, "info", event_dict)
        assert result["headers"]["authorization"] == "***REDACTED***"


class TestMaskPiiPassthrough:
    """Tests for strings that should pass through without masking."""

    def test_normal_text_unchanged(self):
        text = "Hello, how can I help you today?"
        assert mask_pii(text) == text

    def test_empty_string(self):
        assert mask_pii("") == ""

    def test_numbers_that_are_not_pii(self):
        text = "Order #12345 contains 3 items"
        result = mask_pii(text)
        # Should not have PII markers for short numbers
        assert "***SSN***" not in result
