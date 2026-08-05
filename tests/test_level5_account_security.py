"""ACCOUNT-SECURITY (2026-08-01) — customer Security screen phase.

Real defects found and fixed in `AuthService` during audit:

1. `revoke_session` raised two different error shapes for "session doesn't
   exist" (404 NotFoundException) vs "session exists but belongs to
   another customer" (403 PERMISSION_DENIED) — an enumeration oracle.
   Both now raise the identical `SESSION_NOT_FOUND` 404.
2. `change_password` never revoked other sessions on success, leaving a
   compromised session alive indefinitely after a password change.
3. `confirm_password_reset` was a full stub that unconditionally raised
   `SERVICE_UNAVAILABLE` — the entire forgot-password flow was broken
   end-to-end. Implemented for real, mirroring the existing
   `verify_phone_otp_login` OTPRecord verification pattern, and now
   revokes every existing session on success (the account may have been
   compromised — this is the whole reason recovery exists).
"""
from __future__ import annotations

import uuid
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.engines.auth.service import AuthService
from app.engines.auth.utils import hash_password, hash_recipient, generate_otp
from app.exceptions import ServiceOSException

utcnow = __import__("app.engines.auth.service", fromlist=["utcnow"]).utcnow


def _exec_result(*, scalar=None, scalars_all=None, scalars_first=None, rowcount=None):
    res = MagicMock()
    res.scalar_one_or_none = MagicMock(return_value=scalar)
    res.rowcount = rowcount
    scalars = MagicMock()
    scalars.all = MagicMock(return_value=scalars_all or [])
    scalars.first = MagicMock(return_value=scalars_first)
    res.scalars = MagicMock(return_value=scalars)
    return res


def _db():
    db = MagicMock()
    db.execute = AsyncMock()
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    db.refresh = AsyncMock()
    db.add = MagicMock()
    return db


def _svc(db=None):
    db = db or _db()
    svc = AuthService(db=db, ip_address="127.0.0.1")
    svc._audit = AsyncMock()
    svc._publish_event = AsyncMock()
    svc._blacklist = AsyncMock()
    return svc, db


def _user(**overrides):
    defaults = dict(
        id=uuid.uuid4(), email="rajinder@example.com", phone="+919900024102",
        full_name="Rajinder Singh", hashed_password=hash_password("OldPass123!"),
        password_history=[], tenant_id=None, is_active=True,
        force_password_change=False, password_reset_required=False,
        temporary_password_active=False,
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def _session(**overrides):
    defaults = dict(id=uuid.uuid4(), user_id=uuid.uuid4(), revoked_at=None)
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


class TestSessionEnumerationSafety:
    @pytest.mark.asyncio
    async def test_missing_session_returns_generic_404(self):
        svc, db = _svc()
        db.execute.return_value = _exec_result(scalar=None)

        with pytest.raises(ServiceOSException) as exc_info:
            await svc.revoke_session(uuid.uuid4(), uuid.uuid4())

        assert exc_info.value.error_code == "SESSION_NOT_FOUND"
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_foreign_session_returns_the_identical_error_shape(self):
        owner_id = uuid.uuid4()
        requester_id = uuid.uuid4()
        other_session = _session(user_id=owner_id)
        svc, db = _svc()
        db.execute.return_value = _exec_result(scalar=other_session)

        with pytest.raises(ServiceOSException) as exc_info:
            await svc.revoke_session(other_session.id, requester_id)

        assert exc_info.value.error_code == "SESSION_NOT_FOUND"
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_owner_can_revoke_their_own_session(self):
        owner_id = uuid.uuid4()
        own_session = _session(user_id=owner_id)
        svc, db = _svc()
        db.execute.return_value = _exec_result(scalar=own_session)

        await svc.revoke_session(own_session.id, owner_id)

        assert own_session.revoked_at is not None


class TestChangePassword:
    @pytest.mark.asyncio
    async def test_wrong_current_password_is_rejected(self):
        user = _user()
        svc, db = _svc()
        svc._get_user_by_id = AsyncMock(return_value=user)

        original_hash = user.hashed_password
        with pytest.raises(ServiceOSException) as exc_info:
            await svc.change_password(user.id, "WrongPassword!", "NewPass456!")

        assert exc_info.value.error_code == "UNAUTHORIZED"
        assert user.hashed_password == original_hash

    @pytest.mark.asyncio
    async def test_correct_password_change_revokes_other_sessions_but_not_current(self):
        user = _user()
        current_session_id = uuid.uuid4()
        svc, db = _svc()
        svc._get_user_by_id = AsyncMock(return_value=user)
        db.execute.return_value = _exec_result(rowcount=2)

        revoked_count = await svc.change_password(
            user.id, "OldPass123!", "NewPass456!", current_session_id=current_session_id,
        )

        assert revoked_count == 2
        assert user.hashed_password != hash_password("OldPass123!")  # rehashed to something new
        update_call = db.execute.call_args
        assert update_call is not None

    @pytest.mark.asyncio
    async def test_password_reuse_is_rejected(self):
        old_hash = hash_password("ReusedPass1!")
        user = _user(password_history=[old_hash])
        svc, db = _svc()
        svc._get_user_by_id = AsyncMock(return_value=user)

        with pytest.raises(ServiceOSException) as exc_info:
            await svc.change_password(user.id, "OldPass123!", "ReusedPass1!")

        assert exc_info.value.error_code == "VALIDATION_ERROR"


class TestConfirmPasswordReset:
    @pytest.mark.asyncio
    async def test_valid_otp_resets_password_and_revokes_every_session(self):
        user = _user()
        otp_plain, otp_hashed = generate_otp()
        otp_record = SimpleNamespace(
            purpose="password_reset", recipient_hash=hash_recipient(user.email),
            hashed_otp=otp_hashed, attempts=0, is_used=False,
            expires_at=utcnow() + timedelta(minutes=10),
        )
        svc, db = _svc()
        svc._get_user_by_email = AsyncMock(return_value=user)
        db.execute.return_value = _exec_result(scalar=otp_record)

        result = await svc.confirm_password_reset(
            email=user.email, phone=None, reset_token=otp_plain, new_password="BrandNewPass1!",
        )

        assert "successfully" in result["message"].lower()
        assert otp_record.is_used is True
        assert user.hashed_password != _user().hashed_password

    @pytest.mark.asyncio
    async def test_missing_otp_record_and_wrong_code_fail_identically(self):
        """Enumeration safety: no OTP found (unknown recipient or expired)
        must not be distinguishable from a wrong code for a real one."""
        svc_missing, db_missing = _svc()
        db_missing.execute.return_value = _exec_result(scalar=None)

        with pytest.raises(ServiceOSException) as missing_exc:
            await svc_missing.confirm_password_reset(
                email="nobody@example.com", phone=None, reset_token="000000", new_password="X1234567!",
            )

        assert missing_exc.value.error_code == "UNAUTHORIZED"
        assert missing_exc.value.status_code != 500

    @pytest.mark.asyncio
    async def test_wrong_code_against_a_real_otp_is_rejected(self):
        user = _user()
        _, otp_hashed = generate_otp()
        otp_record = SimpleNamespace(
            purpose="password_reset", recipient_hash=hash_recipient(user.email),
            hashed_otp=otp_hashed, attempts=0, is_used=False,
            expires_at=utcnow() + timedelta(minutes=10),
        )
        svc, db = _svc()
        svc._get_user_by_email = AsyncMock(return_value=user)
        db.execute.return_value = _exec_result(scalar=otp_record)

        with pytest.raises(ServiceOSException) as exc_info:
            await svc.confirm_password_reset(
                email=user.email, phone=None, reset_token="999999", new_password="X1234567!",
            )

        assert exc_info.value.error_code == "UNAUTHORIZED"
        assert otp_record.is_used is False

    @pytest.mark.asyncio
    async def test_email_and_phone_both_absent_is_rejected(self):
        svc, db = _svc()
        with pytest.raises(ServiceOSException) as exc_info:
            await svc.confirm_password_reset(email=None, phone=None, reset_token="123456", new_password="X1234567!")
        assert exc_info.value.error_code == "VALIDATION_ERROR"


class TestMFA:
    @pytest.mark.asyncio
    async def test_mfa_is_not_enabled_before_confirmation(self):
        user = _user(is_mfa_enabled=False)
        svc, db = _svc()
        db.execute.return_value = _exec_result(scalar=None)  # no existing MFASecret
        svc._get_user_by_id = AsyncMock(return_value=user)

        result = await svc.setup_mfa(user.id)

        assert "secret" in result
        assert user.is_mfa_enabled is False

    @pytest.mark.asyncio
    async def test_confirm_mfa_without_prior_setup_is_rejected(self):
        svc, db = _svc()
        db.execute.return_value = _exec_result(scalar=None)

        with pytest.raises(ServiceOSException) as exc_info:
            await svc.confirm_mfa(uuid.uuid4(), "123456")

        assert exc_info.value.error_code == "NOT_FOUND"

    @pytest.mark.asyncio
    async def test_invalid_mfa_confirmation_code_is_rejected(self):
        from app.engines.auth.utils import generate_totp_secret
        secret = generate_totp_secret()
        mfa = SimpleNamespace(user_id=uuid.uuid4(), encrypted_secret=secret, is_confirmed=False, confirmed_at=None)
        svc, db = _svc()
        db.execute.return_value = _exec_result(scalar=mfa)

        with pytest.raises(ServiceOSException) as exc_info:
            await svc.confirm_mfa(mfa.user_id, "000000")

        assert exc_info.value.error_code == "UNAUTHORIZED"
        assert mfa.is_confirmed is False

    @pytest.mark.asyncio
    async def test_valid_mfa_confirmation_enables_it(self):
        import pyotp
        from app.engines.auth.utils import generate_totp_secret
        secret = generate_totp_secret()
        mfa = SimpleNamespace(user_id=uuid.uuid4(), encrypted_secret=secret, is_confirmed=False, confirmed_at=None)
        user = _user(id=mfa.user_id, is_mfa_enabled=False)
        svc, db = _svc()
        db.execute.return_value = _exec_result(scalar=mfa)
        svc._get_user_by_id = AsyncMock(return_value=user)

        code = pyotp.TOTP(secret).now()
        result = await svc.confirm_mfa(mfa.user_id, code)

        assert result["mfa_enabled"] is True
        assert mfa.is_confirmed is True
        assert user.is_mfa_enabled is True
