"""Unit tests for authentication utilities and auth service logic."""

from __future__ import annotations

import os
import uuid

import pytest

# Ensure test env vars are set before importing app modules
os.environ.setdefault("SECRET_KEY", "test-secret-key-do-not-use-in-production")
os.environ.setdefault("JWT_SECRET_KEY", "test-jwt-secret-key-do-not-use-in-production")
os.environ.setdefault("APP_ENV", "test")

from autonomocx.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    verify_password,
)


class TestPasswordHashing:
    """Tests for bcrypt password hashing and verification."""

    def test_hash_password_returns_bcrypt_hash(self):
        hashed = get_password_hash("my-secret-password")
        assert hashed.startswith("$2")  # bcrypt prefix
        assert len(hashed) > 50

    def test_hash_password_different_each_time(self):
        h1 = get_password_hash("same-password")
        h2 = get_password_hash("same-password")
        assert h1 != h2  # bcrypt uses random salt

    def test_verify_correct_password(self):
        hashed = get_password_hash("correct-password")
        assert verify_password("correct-password", hashed) is True

    def test_verify_wrong_password(self):
        hashed = get_password_hash("correct-password")
        assert verify_password("wrong-password", hashed) is False

    def test_verify_empty_password(self):
        hashed = get_password_hash("something")
        assert verify_password("", hashed) is False

    def test_hash_and_verify_unicode_password(self):
        password = "p@ssw0rd-with-emojis-and-unicode"
        hashed = get_password_hash(password)
        assert verify_password(password, hashed) is True


class TestTokenCreation:
    """Tests for JWT token creation."""

    def test_create_access_token(self):
        token = create_access_token(subject="user-123")
        assert isinstance(token, str)
        assert len(token) > 20

    def test_access_token_contains_correct_claims(self):
        user_id = str(uuid.uuid4())
        org_id = str(uuid.uuid4())
        token = create_access_token(
            subject=user_id,
            org_id=org_id,
            role="admin",
        )
        payload = decode_token(token)
        assert payload.sub == user_id
        assert payload.org_id == org_id
        assert payload.role == "admin"
        assert payload.token_type == "access"

    def test_create_refresh_token(self):
        token = create_refresh_token(subject="user-456")
        assert isinstance(token, str)

    def test_refresh_token_has_correct_type(self):
        token = create_refresh_token(subject="user-456")
        payload = decode_token(token)
        assert payload.token_type == "refresh"

    def test_access_and_refresh_tokens_differ(self):
        access = create_access_token(subject="user-789")
        refresh = create_refresh_token(subject="user-789")
        assert access != refresh

    def test_token_has_jti(self):
        token = create_access_token(subject="user-101")
        payload = decode_token(token)
        assert payload.jti  # non-empty string
        assert len(payload.jti) > 10

    def test_token_jti_is_unique(self):
        t1 = create_access_token(subject="user-101")
        t2 = create_access_token(subject="user-101")
        p1 = decode_token(t1)
        p2 = decode_token(t2)
        assert p1.jti != p2.jti


class TestTokenDecoding:
    """Tests for JWT token decoding and validation."""

    def test_decode_valid_token(self):
        token = create_access_token(subject="decode-test")
        payload = decode_token(token)
        assert payload.sub == "decode-test"

    def test_decode_invalid_token_raises(self):
        from jose import JWTError

        with pytest.raises(JWTError):
            decode_token("this-is-not-a-valid-jwt")

    def test_decode_tampered_token_raises(self):
        from jose import JWTError

        token = create_access_token(subject="tamper-test")
        # Tamper with the token by changing a character
        tampered = token[:-5] + "XXXXX"
        with pytest.raises(JWTError):
            decode_token(tampered)

    def test_extra_claims_are_preserved(self):
        token = create_access_token(
            subject="extra-test",
            extra_claims={"custom_field": "custom_value"},
        )
        payload = decode_token(token)
        assert payload.raw.get("custom_field") == "custom_value"
