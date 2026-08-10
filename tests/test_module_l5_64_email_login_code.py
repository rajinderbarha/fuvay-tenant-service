"""MODULE-L5-64 — signing in with an emailed code, and the reset email that never sent.

`POST /v1/auth/otp/send` has been summarised as "Send OTP to phone or email" and has
accepted an `email` field since it was written. The router passed
`phone=body.phone or ""`, so an email request stored a record against the hash of an
empty string and answered "OTP sent." Nothing was ever emailed, and `/otp/verify`
required a phone, so even a delivered code had nowhere to be redeemed.

The security properties are the point of most of these tests. A sign-in form that
behaves differently for a registered address is an account list for anyone who asks,
and a 6-digit code with no attempt limit is a lock that opens on the millionth try.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.engines.auth.schemas import OTPSendRequest, OTPVerifyRequest
from app.exceptions import ServiceOSException


class TestTheContractAcceptsBothChannels:
    def test_verify_accepts_an_email_instead_of_a_phone(self):
        # `phone` was required, so the emailed code had no way to be redeemed.
        body = OTPVerifyRequest(email="raj@example.com", otp="123456")
        assert body.email == "raj@example.com"
        assert body.phone is None

    def test_verify_still_accepts_a_phone(self):
        body = OTPVerifyRequest(phone="+919876543210", otp="123456")
        assert body.phone == "+919876543210"

    def test_verify_refuses_a_request_with_neither(self):
        with pytest.raises(ValueError):
            OTPVerifyRequest(otp="123456")

    def test_send_accepts_the_email_login_purpose(self):
        assert OTPSendRequest(email="raj@example.com", purpose="email_login").purpose == "email_login"


def _service(*, user=None, email_configured=True, delivered=True):
    """An AuthService with its collaborators stubbed, for the branches worth pinning."""
    from app.engines.auth.service import AuthService

    svc = AuthService.__new__(AuthService)
    svc.db = MagicMock()
    svc.db.add = MagicMock()
    svc.db.flush = AsyncMock()
    svc.ip_address = "127.0.0.1"
    svc._get_user_by_email = AsyncMock(return_value=user)
    svc._audit = AsyncMock()
    svc._log_login_event = AsyncMock()
    svc._build_token_pair = AsyncMock(return_value={
        "access_token": "at", "refresh_token": "rt",
    })
    svc._user_to_profile = MagicMock(return_value={"id": "u-1"})
    svc._tenant_to_ctx = AsyncMock(return_value=None)
    return svc


def _user(**overrides):
    user = MagicMock()
    user.id = "u-1"
    user.tenant_id = None
    user.is_active = True
    user.is_verified = False
    user.email = "raj@example.com"
    for key, value in overrides.items():
        setattr(user, key, value)
    return user


class TestSendingIsEnumerationSafe:
    @pytest.mark.asyncio
    async def test_an_unknown_address_gets_the_same_answer_as_a_real_one(self):
        # This is the whole reason the message is worded "if an account exists": a
        # different response for a registered address turns the sign-in form into an
        # account-existence oracle.
        known = _service(user=_user())
        unknown = _service(user=None)
        with patch("app.email_client.is_email_configured", return_value=True), \
             patch("app.email_client.send_login_code_email", new=AsyncMock(return_value=True)), \
             patch("app.engines.auth.service.get_settings", return_value=MagicMock(DEBUG=False)):
            a = await known.send_email_otp("raj@example.com")
            b = await unknown.send_email_otp("nobody@example.com")

        assert a["message"] == b["message"]
        assert "otp_hint" not in a and "otp_hint" not in b

    @pytest.mark.asyncio
    async def test_no_code_is_stored_for_an_address_with_no_account(self):
        # Nothing to redeem, so nothing to write -- an unknown address cannot be used to
        # fill the table with records nobody will ever use.
        svc = _service(user=None)
        with patch("app.email_client.is_email_configured", return_value=True), \
             patch("app.email_client.send_login_code_email", new=AsyncMock()) as send:
            await svc.send_email_otp("nobody@example.com")

        svc.db.add.assert_not_called()
        send.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_a_deactivated_account_is_treated_as_no_account(self):
        svc = _service(user=_user(is_active=False))
        with patch("app.email_client.is_email_configured", return_value=True), \
             patch("app.email_client.send_login_code_email", new=AsyncMock()) as send:
            await svc.send_email_otp("raj@example.com")

        send.assert_not_awaited()


class TestItRefusesRatherThanPretends:
    @pytest.mark.asyncio
    async def test_no_mailer_configured_is_an_error_not_a_silent_success(self):
        # A code the customer will never receive is worse than not offering the option,
        # because they sit and wait for it.
        svc = _service(user=_user())
        with patch("app.email_client.is_email_configured", return_value=False):
            with pytest.raises(ServiceOSException) as exc:
                await svc.send_email_otp("raj@example.com")

        assert "not available" in exc.value.detail.lower()

    @pytest.mark.asyncio
    async def test_a_failed_send_is_reported(self):
        svc = _service(user=_user())
        with patch("app.email_client.is_email_configured", return_value=True), \
             patch("app.email_client.send_login_code_email", new=AsyncMock(return_value=False)):
            with pytest.raises(ServiceOSException):
                await svc.send_email_otp("raj@example.com")

    @pytest.mark.asyncio
    async def test_the_code_is_never_in_the_response_outside_debug(self):
        svc = _service(user=_user())
        with patch("app.email_client.is_email_configured", return_value=True), \
             patch("app.email_client.send_login_code_email", new=AsyncMock(return_value=True)), \
             patch("app.engines.auth.service.get_settings", return_value=MagicMock(DEBUG=False)):
            result = await svc.send_email_otp("raj@example.com")

        assert "otp_hint" not in result


class TestVerifying:
    @staticmethod
    def _svc_with_record(record, user=None):
        svc = _service(user=user)
        result = MagicMock()
        result.scalar_one_or_none = MagicMock(return_value=record)
        svc.db.execute = AsyncMock(return_value=result)
        return svc

    @staticmethod
    def _record(attempts=0):
        record = MagicMock()
        record.attempts = attempts
        record.hashed_otp = "hashed"
        record.is_used = False
        return record

    @pytest.mark.asyncio
    async def test_no_record_and_a_wrong_code_fail_identically(self):
        # Same wording either way: otherwise the error itself says whether a code was
        # ever sent to that address.
        no_record = self._svc_with_record(None)
        with pytest.raises(ServiceOSException) as absent:
            await no_record.verify_email_otp_login(
                email="raj@example.com", otp="123456", device_id="d", device_name=None,
                user_agent=None)

        wrong = self._svc_with_record(self._record(), user=_user())
        with patch("app.engines.auth.service.verify_otp", return_value=False):
            with pytest.raises(ServiceOSException) as bad_code:
                await wrong.verify_email_otp_login(
                    email="raj@example.com", otp="000000", device_id="d", device_name=None,
                    user_agent=None)

        assert absent.value.detail == bad_code.value.detail

    @pytest.mark.asyncio
    async def test_a_fourth_attempt_burns_the_code(self):
        # Three guesses at six digits is the entire protection; leaving the record live
        # makes brute force a matter of time.
        record = self._record(attempts=3)
        svc = self._svc_with_record(record, user=_user())
        with patch("app.engines.auth.service.verify_otp", return_value=True):
            with pytest.raises(ServiceOSException):
                await svc.verify_email_otp_login(
                    email="raj@example.com", otp="123456", device_id="d", device_name=None,
                    user_agent=None)

        assert record.is_used is True

    @pytest.mark.asyncio
    async def test_a_correct_code_returns_a_session_and_marks_it_used(self):
        record = self._record()
        user = _user()
        svc = self._svc_with_record(record, user=user)
        with patch("app.engines.auth.service.verify_otp", return_value=True):
            result = await svc.verify_email_otp_login(
                email="raj@example.com", otp="123456", device_id="d", device_name=None,
                user_agent=None)

        assert result["access_token"] == "at"
        assert record.is_used is True
        # Holding the emailed code proves the address, which is what verification means.
        assert user.is_verified is True

    @pytest.mark.asyncio
    async def test_a_deactivated_account_cannot_redeem_a_code(self):
        svc = self._svc_with_record(self._record(), user=_user(is_active=False))
        with patch("app.engines.auth.service.verify_otp", return_value=True):
            with pytest.raises(ServiceOSException):
                await svc.verify_email_otp_login(
                    email="raj@example.com", otp="123456", device_id="d", device_name=None,
                    user_agent=None)


class TestTheResetEmailThatNeverSent:
    def test_the_function_admin_reset_imports_actually_exists_now(self):
        # `AuthService.admin_send_password_reset` imported `send_password_reset_email`
        # inside a try whose `except Exception` logged a warning. The function did not
        # exist, so every admin-triggered reset raised ImportError, was swallowed, and
        # recorded `email_sent: False` while the admin was told it had been sent.
        from app.email_client import is_email_configured, send_password_reset_email

        assert callable(send_password_reset_email)
        assert callable(is_email_configured)

    @pytest.mark.asyncio
    async def test_neither_email_contains_a_clickable_link(self):
        # A sign-in or reset message that trains customers to click through to a
        # credential form is the exact shape of the phishing it should prevent.
        from app import email_client

        bodies = []

        async def capture(to, subject, body):
            bodies.append(body)
            return True

        with patch.object(email_client, "send_email", new=capture):
            await email_client.send_login_code_email("raj@example.com", "123456", 10)
            await email_client.send_password_reset_email("raj@example.com", "Raj", "tok", 24)

        assert len(bodies) == 2
        for body in bodies:
            assert "http://" not in body and "https://" not in body

    @pytest.mark.asyncio
    async def test_the_login_email_states_the_code_and_its_expiry(self):
        from app import email_client

        captured = {}

        async def capture(to, subject, body):
            captured.update(to=to, subject=subject, body=body)
            return True

        with patch.object(email_client, "send_email", new=capture):
            await email_client.send_login_code_email("raj@example.com", "654321", 10)

        assert "654321" in captured["body"]
        assert "10 minutes" in captured["body"]
        assert captured["to"] == "raj@example.com"
