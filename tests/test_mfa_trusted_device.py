"""
Technician mobile app Phase G: POST /v1/auth/mfa/verify hardcoded
device_id="web" for every caller and had no remember_device field at all,
so `UserSession.is_trusted` could never be set via the MFA path regardless
of what the client sent (login()'s equivalent trust check already worked
correctly for non-MFA logins -- this closes the same gap for MFA-gated
accounts). Verifies the fix without touching the existing password-login
trust behavior.
"""
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.engines.auth.models import UserSession
from app.engines.auth.schemas import MFAVerifyRequest
from app.engines.auth.service import AuthService


def test_mfa_verify_request_accepts_device_id_and_remember_device():
    body = MFAVerifyRequest(mfa_challenge_token="tok", code="123456", device_id="mobile-abc", device_name="iPhone", remember_device=True)
    assert body.device_id == "mobile-abc"
    assert body.remember_device is True


def test_mfa_verify_request_defaults_preserve_prior_behavior():
    body = MFAVerifyRequest(mfa_challenge_token="tok", code="123456")
    assert body.device_id == "web"
    assert body.remember_device is False


@pytest.mark.asyncio
async def test_verify_mfa_sets_is_trusted_when_remember_device_and_real_device_id():
    from app.engines.auth.utils import create_mfa_challenge_token

    user_id = uuid.uuid4()
    fake_user = MagicMock(id=user_id, email="tech@biz.io", tenant_id=None, role="technician", is_mfa_enabled=True)
    fake_secret = MagicMock(encrypted_secret="JBSWY3DPEHPK3PXP", is_confirmed=True)

    db = MagicMock()
    svc = AuthService(db=db)
    svc._get_user_by_id = AsyncMock(return_value=fake_user)
    svc._audit = AsyncMock()
    svc._build_token_pair = AsyncMock(return_value={"access_token": "a", "refresh_token": "r"})
    svc._user_to_profile = MagicMock(return_value={})
    svc._tenant_to_ctx = AsyncMock(return_value=None)
    svc.resolve_post_login_destination = AsyncMock(return_value={"next_destination": "technician_app", "reason_code": "TECHNICIAN_ROLE_NO_PORTAL_ACCESS"})

    secret_result = MagicMock(); secret_result.scalar_one_or_none.return_value = fake_secret
    db.execute = AsyncMock(return_value=secret_result)
    db.add = MagicMock()
    db.flush = AsyncMock()

    import pyotp
    valid_code = pyotp.TOTP(fake_secret.encrypted_secret).now()
    challenge = create_mfa_challenge_token(str(user_id), fake_user.email)

    await svc.verify_mfa(
        mfa_challenge_token=challenge, code=valid_code,
        device_id="mobile-real-device-id", device_name="Pixel 8", user_agent="ServiceOSTechnicianApp/1.0",
        remember_device=True,
    )

    created_session = next(call.args[0] for call in db.add.call_args_list if isinstance(call.args[0], UserSession))
    assert created_session.is_trusted is True
    assert created_session.device_id == "mobile-real-device-id"


@pytest.mark.asyncio
async def test_verify_mfa_never_trusts_without_remember_device_even_with_real_device_id():
    from app.engines.auth.utils import create_mfa_challenge_token
    import pyotp

    user_id = uuid.uuid4()
    fake_user = MagicMock(id=user_id, email="tech2@biz.io", tenant_id=None, role="technician", is_mfa_enabled=True)
    fake_secret = MagicMock(encrypted_secret="JBSWY3DPEHPK3PXP", is_confirmed=True)

    db = MagicMock()
    svc = AuthService(db=db)
    svc._get_user_by_id = AsyncMock(return_value=fake_user)
    svc._audit = AsyncMock()
    svc._build_token_pair = AsyncMock(return_value={"access_token": "a", "refresh_token": "r"})
    svc._user_to_profile = MagicMock(return_value={})
    svc._tenant_to_ctx = AsyncMock(return_value=None)
    svc.resolve_post_login_destination = AsyncMock(return_value={"next_destination": "technician_app", "reason_code": "x"})

    secret_result = MagicMock(); secret_result.scalar_one_or_none.return_value = fake_secret
    db.execute = AsyncMock(return_value=secret_result)
    db.add = MagicMock()
    db.flush = AsyncMock()

    valid_code = pyotp.TOTP(fake_secret.encrypted_secret).now()
    challenge = create_mfa_challenge_token(str(user_id), fake_user.email)

    await svc.verify_mfa(
        mfa_challenge_token=challenge, code=valid_code,
        device_id="mobile-real-device-id", device_name="Pixel 8", user_agent="ua",
        remember_device=False,
    )

    created_session = next(call.args[0] for call in db.add.call_args_list if isinstance(call.args[0], UserSession))
    assert created_session.is_trusted is False


@pytest.mark.asyncio
async def test_verify_mfa_preserves_forced_password_change_policy():
    from app.engines.auth.utils import create_mfa_challenge_token
    import pyotp

    user_id = uuid.uuid4()
    fake_user = MagicMock(
        id=user_id, email="admin@serviceos.in", tenant_id=None, role="super_admin",
        is_mfa_enabled=True, force_password_change=True,
        password_reset_required=False, temporary_password_active=False,
    )
    fake_secret = MagicMock(encrypted_secret="JBSWY3DPEHPK3PXP", is_confirmed=True)

    db = MagicMock()
    svc = AuthService(db=db)
    svc._get_user_by_id = AsyncMock(return_value=fake_user)
    svc._audit = AsyncMock()
    svc._build_token_pair = AsyncMock(return_value={"access_token": "a", "refresh_token": "r"})
    svc._user_to_profile = MagicMock(return_value={"role": "super_admin"})
    svc._tenant_to_ctx = AsyncMock(return_value=None)

    secret_result = MagicMock(); secret_result.scalar_one_or_none.return_value = fake_secret
    db.execute = AsyncMock(return_value=secret_result)
    db.add = MagicMock()
    db.flush = AsyncMock()

    result = await svc.verify_mfa(
        mfa_challenge_token=create_mfa_challenge_token(str(user_id), fake_user.email),
        code=pyotp.TOTP(fake_secret.encrypted_secret).now(),
        device_id="web", device_name="Admin Browser", user_agent="ua",
    )

    assert result["requires_password_change"] is True
    assert result["redirect_to"] == "/change-password-required"
    assert result["refresh_token"] is None
