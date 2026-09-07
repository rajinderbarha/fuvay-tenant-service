"""Razorpay credentials resolve from the admin-configured encrypted channel
when it is enabled and passing, and fall back to env vars otherwise -- the
same resolution contract already proven for WhatsApp/Instagram."""
import uuid
from unittest.mock import AsyncMock, patch

import pytest

from app.integrations import razorpay_client


@pytest.mark.asyncio
async def test_no_db_falls_back_to_env_settings():
    fake_settings = type("S", (), {
        "RAZORPAY_KEY_ID": "rzp_test_env", "RAZORPAY_KEY_SECRET": "env_secret",
        "RAZORPAY_WEBHOOK_SECRET": "env_webhook",
    })()
    with patch("app.integrations.razorpay_client.get_settings", return_value=fake_settings):
        key_id, key_secret, webhook_secret = await razorpay_client._resolve_credentials(None)
    assert (key_id, key_secret, webhook_secret) == ("rzp_test_env", "env_secret", "env_webhook")


@pytest.mark.asyncio
async def test_enabled_and_passing_admin_config_overrides_env():
    fake_settings = type("S", (), {
        "RAZORPAY_KEY_ID": "rzp_test_env", "RAZORPAY_KEY_SECRET": "env_secret",
        "RAZORPAY_WEBHOOK_SECRET": "env_webhook",
    })()
    active = ({"key_id": "rzp_live_admin"}, {"key_secret": "admin_secret", "webhook_secret": "admin_webhook"})
    with patch("app.integrations.razorpay_client.get_settings", return_value=fake_settings), \
         patch("app.engines.platform_notifications.channel_config_service.channel_config_service.get_active",
               AsyncMock(return_value=active)):
        key_id, key_secret, webhook_secret = await razorpay_client._resolve_credentials(object())
    assert (key_id, key_secret, webhook_secret) == ("rzp_live_admin", "admin_secret", "admin_webhook")


@pytest.mark.asyncio
async def test_disabled_or_unverified_admin_config_does_not_override_env():
    # get_active() itself already enforces is_enabled AND last_test_status == "passed"
    # (see NotificationChannelConfigService.get_active) -- it returns None otherwise.
    fake_settings = type("S", (), {
        "RAZORPAY_KEY_ID": "rzp_test_env", "RAZORPAY_KEY_SECRET": "env_secret",
        "RAZORPAY_WEBHOOK_SECRET": "env_webhook",
    })()
    with patch("app.integrations.razorpay_client.get_settings", return_value=fake_settings), \
         patch("app.engines.platform_notifications.channel_config_service.channel_config_service.get_active",
               AsyncMock(return_value=None)):
        key_id, key_secret, webhook_secret = await razorpay_client._resolve_credentials(object())
    assert (key_id, key_secret, webhook_secret) == ("rzp_test_env", "env_secret", "env_webhook")


@pytest.mark.asyncio
async def test_admin_config_lookup_failure_falls_back_instead_of_raising():
    fake_settings = type("S", (), {
        "RAZORPAY_KEY_ID": "rzp_test_env", "RAZORPAY_KEY_SECRET": "env_secret",
        "RAZORPAY_WEBHOOK_SECRET": "env_webhook",
    })()
    with patch("app.integrations.razorpay_client.get_settings", return_value=fake_settings), \
         patch("app.engines.platform_notifications.channel_config_service.channel_config_service.get_active",
               AsyncMock(side_effect=RuntimeError("db down"))):
        key_id, key_secret, webhook_secret = await razorpay_client._resolve_credentials(object())
    assert (key_id, key_secret, webhook_secret) == ("rzp_test_env", "env_secret", "env_webhook")


@pytest.mark.asyncio
async def test_verify_webhook_signature_uses_resolved_secret():
    import hashlib, hmac
    fake_settings = type("S", (), {
        "RAZORPAY_KEY_ID": "", "RAZORPAY_KEY_SECRET": "", "RAZORPAY_WEBHOOK_SECRET": "",
    })()
    active = ({"key_id": "rzp_live_admin"}, {"key_secret": "s", "webhook_secret": "admin_webhook"})
    body = b'{"event":"payment.captured"}'
    sig = hmac.new(b"admin_webhook", body, hashlib.sha256).hexdigest()
    with patch("app.integrations.razorpay_client.get_settings", return_value=fake_settings), \
         patch("app.engines.platform_notifications.channel_config_service.channel_config_service.get_active",
               AsyncMock(return_value=active)):
        assert await razorpay_client.verify_webhook_signature(body, sig, db=object())
        assert not await razorpay_client.verify_webhook_signature(body, "wrong", db=object())


@pytest.mark.asyncio
async def test_get_key_id_never_returns_a_secret():
    fake_settings = type("S", (), {
        "RAZORPAY_KEY_ID": "rzp_test_env", "RAZORPAY_KEY_SECRET": "env_secret",
        "RAZORPAY_WEBHOOK_SECRET": "",
    })()
    with patch("app.integrations.razorpay_client.get_settings", return_value=fake_settings):
        key_id = await razorpay_client.get_key_id(None)
    assert key_id == "rzp_test_env"
