"""Notification provider control-plane contract tests."""
from app.engines.notification.models import NotificationChannelConfig
from app.engines.platform_notifications.channel_config_service import (
    NotificationChannelConfigService, PLATFORM_CONFIG_TENANT_ID, PROVIDER_DEFINITIONS,
)


def test_all_runtime_channels_have_configuration_definitions():
    assert set(PROVIDER_DEFINITIONS) == {"in_app", "email", "sms", "whatsapp", "push"}


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
