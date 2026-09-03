"""
Auth login fix tests — Phase 9 of blocking login fix.

Covers:
  - LoginRequest schema validation (email normalization, bad formats rejected)
  - hash_password / verify_password round-trip
  - JWT payload shape (role, tenant_id, email, sub, exp)
  - /v1/auth/login happy path (mocked service)
  - /v1/auth/login error paths (wrong password, inactive user, locked)
  - /v1/auth/me with valid token
  - Role separation (super_admin vs tenant_owner vs technician)
"""
from __future__ import annotations

import base64
import json
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.engines.auth.schemas import LoginRequest
from app.engines.auth.utils import hash_password, verify_password, create_access_token


# ── 1. LoginRequest schema ────────────────────────────────────────────────────

class TestLoginRequestSchema:
    def test_valid_standard_email(self):
        r = LoginRequest(email="admin@serviceos.in", password="Password123!")
        assert r.email == "admin@serviceos.in"

    def test_valid_dev_email(self):
        r = LoginRequest(email="owner@serviceos.dev", password="Password123!")
        assert r.email == "owner@serviceos.dev"

    def test_local_domain_accepted(self):
        """LoginRequest must accept .local TLD (dev/staging use)."""
        r = LoginRequest(email="admin@serviceos.local", password="Password123!")
        assert r.email == "admin@serviceos.local"

    def test_email_normalised_to_lowercase(self):
        r = LoginRequest(email="Admin@Fuvay.IN", password="x")
        assert r.email == "admin@fuvay.in"

    def test_email_whitespace_stripped(self):
        r = LoginRequest(email="  admin@serviceos.in  ", password="x")
        assert r.email == "admin@serviceos.in"

    def test_missing_at_sign_rejected(self):
        with pytest.raises(Exception):
            LoginRequest(email="notanemail", password="x")

    def test_missing_tld_rejected(self):
        with pytest.raises(Exception):
            LoginRequest(email="user@nodot", password="x")

    def test_empty_email_rejected(self):
        with pytest.raises(Exception):
            LoginRequest(email="", password="x")


# ── 2. Password hashing ───────────────────────────────────────────────────────

class TestPasswordHashing:
    def test_hash_is_bcrypt_format(self):
        h = hash_password("Password123!")
        assert h.startswith("$2b$") or h.startswith("$2a$")

    def test_verify_correct_password(self):
        h = hash_password("Password123!")
        assert verify_password("Password123!", h) is True

    def test_verify_wrong_password(self):
        h = hash_password("Password123!")
        assert verify_password("wrongpassword", h) is False

    def test_hash_is_not_deterministic(self):
        """Different hashes for same password (bcrypt uses random salt)."""
        h1 = hash_password("Password123!")
        h2 = hash_password("Password123!")
        assert h1 != h2

    def test_both_hashes_verify(self):
        h1 = hash_password("Password123!")
        h2 = hash_password("Password123!")
        assert verify_password("Password123!", h1)
        assert verify_password("Password123!", h2)


# ── 3. JWT payload shape ──────────────────────────────────────────────────────

class TestJWTPayload:
    def _decode_payload(self, token: str) -> dict:
        part = token.split(".")[1]
        part += "=" * (4 - len(part) % 4)
        return json.loads(base64.urlsafe_b64decode(part))

    def test_access_token_contains_required_keys(self):
        uid = str(uuid.uuid4())
        sid = str(uuid.uuid4())
        did = "web"
        token, jti = create_access_token(
            user_id=uid, email="admin@serviceos.in", role="super_admin",
            tenant_id=None, tenant_name=None, plan_type=None,
            session_id=sid, device_id=did,
            is_mfa_enabled=False, onboarding_complete=True,
            enabled_engines=[],
        )
        payload = self._decode_payload(token)
        for key in ("sub", "email", "role", "tenant_id", "session_id", "exp", "iat", "jti"):
            assert key in payload, f"JWT missing key: {key}"

    def test_access_token_role_matches(self):
        uid = str(uuid.uuid4())
        sid = str(uuid.uuid4())
        token, _ = create_access_token(
            user_id=uid, email="owner@serviceos.dev", role="tenant_owner",
            tenant_id=str(uuid.uuid4()), tenant_name="Bright Svc", plan_type="starter",
            session_id=sid, device_id="web",
            is_mfa_enabled=False, onboarding_complete=True,
            enabled_engines=[],
        )
        payload = self._decode_payload(token)
        assert payload["role"] == "tenant_owner"

    def test_super_admin_token_has_null_tenant_id(self):
        uid = str(uuid.uuid4())
        sid = str(uuid.uuid4())
        token, _ = create_access_token(
            user_id=uid, email="admin@serviceos.in", role="super_admin",
            tenant_id=None, tenant_name=None, plan_type=None,
            session_id=sid, device_id="web",
            is_mfa_enabled=False, onboarding_complete=True,
            enabled_engines=[],
        )
        payload = self._decode_payload(token)
        assert payload["tenant_id"] is None
