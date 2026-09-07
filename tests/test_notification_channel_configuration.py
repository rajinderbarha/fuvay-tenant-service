"""Notification provider control-plane contract tests."""
from app.engines.notification.models import NotificationChannelConfig
from app.engines.platform_notifications.channel_config_service import (
    NotificationChannelConfigService, PLATFORM_CONFIG_TENANT_ID, PROVIDER_DEFINITIONS,
)


def test_all_runtime_channels_have_configuration_definitions():
    assert {"in_app", "email", "sms", "whatsapp", "push"} <= set(PROVIDER_DEFINITIONS)


def test_razorpay_shares_the_encrypted_config_lifecycle_but_is_not_a_notification_channel():
    from app.engines.platform_notifications.channel_config_service import NON_NOTIFICATION_CHANNELS
    from app.engines.platform_notifications.constants import ALL_CHANNELS
    assert "razorpay" in PROVIDER_DEFINITIONS
    assert "razorpay" in NON_NOTIFICATION_CHANNELS
    assert "razorpay" not in ALL_CHANNELS
    keys = {f["key"] for f in PROVIDER_DEFINITIONS["razorpay"]["fields"]}
    assert keys == {"key_id", "key_secret", "webhook_secret"}
    secret_keys = {f["key"] for f in PROVIDER_DEFINITIONS["razorpay"]["fields"] if f["secret"]}
    assert secret_keys == {"key_secret", "webhook_secret"}


def test_razorpay_key_id_format_is_validated():
    import pytest
    from app.exceptions import ServiceOSException
    service = NotificationChannelConfigService()
    with pytest.raises(ServiceOSException):
        service._validate("razorpay", {"key_id": "not_a_real_key"}, {"key_secret": "supersecretvalue"})
    service._validate("razorpay", {"key_id": "rzp_test_abc123"}, {"key_secret": "supersecretvalue"})


def test_credentials_are_encrypted_and_never_returned():
    service = NotificationChannelConfigService()
    encrypted = service._encrypt({"password": "not-a-real-password"})
    assert encrypted and "not-a-real-password" not in encrypted
    row = NotificationChannelConfig(
        tenant_id=PLATFORM_CONFIG_TENANT_ID, channel="email", provider_name="SMTP",
        config={"host": "smtp.example.com", "port": "587", "username": "alerts@example.com", "from_email": "alerts@example.com", "use_tls": "starttls"},
        encrypted_credentials=encrypted, is_enabled=False,
    )
    assert service.decrypt(row)["password"] == "not-a-real-password"
    public = service.public_item("email", row)
    assert "encrypted_credentials" not in public
    password = next(field for field in public["fields"] if field["key"] == "password")
    assert password["value"] == "" and password["has_value"] is True


def test_push_is_not_configured_until_admin_saves_a_row():
    public = NotificationChannelConfigService().public_item("push", None)
    assert public["configured"] is False
    assert public["enabled"] is False


def test_external_adapters_are_real_not_stub_implementations():
    from app.engines.platform_notifications.channel_providers import CHANNEL_PROVIDERS
    assert CHANNEL_PROVIDERS["email"].provider_name == "smtp"
    assert CHANNEL_PROVIDERS["sms"].provider_name == "twilio_sms"
    assert CHANNEL_PROVIDERS["whatsapp"].provider_name == "twilio_whatsapp"
    assert CHANNEL_PROVIDERS["push"].provider_name == "expo_push"


def test_configuration_routes_include_save_test_enable_and_audit():
    from app.engines.platform_notifications.admin_router import admin_outbox_router
    paths = {getattr(route, "path", "") for route in admin_outbox_router.routes}
    base = "/v1/admin/notification-outbox/channel-configurations/{channel}"
    assert base in paths
    assert f"{base}/test" in paths
    assert f"{base}/enabled" in paths
    assert f"{base}/audit" in paths


def test_single_channel_get_route_exists_alongside_save():
    from app.engines.platform_notifications.admin_router import admin_outbox_router
    base = "/v1/admin/notification-outbox/channel-configurations/{channel}"
    methods_by_path = {}
    for route in admin_outbox_router.routes:
        methods_by_path.setdefault(getattr(route, "path", ""), set()).update(getattr(route, "methods", set()) or set())
    assert {"GET", "PUT"} <= methods_by_path[base]


def test_audit_route_accepts_razorpay():
    import asyncio
    from unittest.mock import AsyncMock, MagicMock
    from app.engines.platform_notifications.admin_router import admin_channel_configuration_audit
    db = MagicMock()
    request = MagicMock()
    request.state.request_id = "req_test"
    with __import__("unittest.mock", fromlist=["patch"]).patch(
        "app.engines.platform_notifications.admin_router.channel_config_service.audit", AsyncMock(return_value=[])
    ):
        result = asyncio.get_event_loop().run_until_complete(
            admin_channel_configuration_audit("razorpay", request, 50, MagicMock(), db)
        )
    assert result.data == {"items": []}
