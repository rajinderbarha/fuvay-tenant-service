"""Signup simulation is explicit in staging and never effective in production."""
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.engines.public_registration.service import (
    RegistrationService, MOBILE_OTP_PURPOSE, EMAIL_OTP_PURPOSE,
)


@pytest.mark.asyncio
@pytest.mark.parametrize("environment, enabled, debug, simulated", [
    ("staging", True, False, True),
    ("staging", False, False, False),
    ("development", False, True, True),
    ("production", True, True, False),
])
async def test_signup_otp_delivery_mode(environment, enabled, debug, simulated):
    query = MagicMock()
    query.scalar_one_or_none.return_value = None
    db = MagicMock(execute=AsyncMock(return_value=query))
    pending = SimpleNamespace(id=uuid.uuid4(), mobile="+919041624576", email="owner@example.com")
    settings = SimpleNamespace(APP_ENV=environment, DEBUG=debug, SIGNUP_DEV_OTP_ENABLED=enabled)
    with patch("app.engines.public_registration.service.get_settings", return_value=settings), \
         patch("app.engines.public_registration.service.enforce_otp_send_limits", new=AsyncMock()), \
         patch("app.engines.public_registration.service.generate_otp", return_value=("123456", "hashed")), \
         patch("app.engines.public_registration.service.send_sms", new=AsyncMock()) as sms, \
         patch("app.engines.public_registration.service.send_email", new=AsyncMock()) as email:
        result = await RegistrationService(db)._send_otps(pending)
    assert db.add.call_count == 2  # Both paths still create verifiable OTP records.
    if simulated:
        assert result == {MOBILE_OTP_PURPOSE: "123456", EMAIL_OTP_PURPOSE: "123456"}
        sms.assert_not_awaited()
        email.assert_not_awaited()
    else:
        assert result == {}
        sms.assert_awaited_once()
        email.assert_awaited_once()
