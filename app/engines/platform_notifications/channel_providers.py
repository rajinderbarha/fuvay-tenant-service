"""Sprint 27 — Notification Channel Provider Abstraction.

InAppNotificationProvider: actually creates in_app_notifications records.
All external channel stubs: return provider_not_configured unless real config exists.
Do not claim delivered unless provider confirms.
"""
from __future__ import annotations
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.platform_notifications.constants import (
    DELIVERY_PROVIDER_NOT_CONFIGURED, DELIVERY_DELIVERED,
    READ_UNREAD,
)
from app.engines.platform_notifications.models import InAppNotification


@dataclass
class ChannelResult:
    success: bool
    status: str
    provider_name: str
    provider_message_id: str | None = None
    failure_code: str | None = None
    failure_message: str | None = None

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "status": self.status,
            "provider_name": self.provider_name,
            "provider_message_id": self.provider_message_id,
            "failure_code": self.failure_code,
            "failure_message": self.failure_message,
        }


class InAppNotificationProvider:
    """Actually persists the in-app notification record."""

    provider_name = "in_app"

    async def deliver(
        self,
        db: AsyncSession,
        outbox_id: uuid.UUID,
        user_id: uuid.UUID,
        tenant_id: uuid.UUID | None,
        notification_type: str,
        title: str,
        body: str,
        action_url: str | None,
        action_label: str | None,
        source_record_type: str | None,
        source_record_id: uuid.UUID | None,
        severity: str,
    ) -> ChannelResult:
        notif = InAppNotification(
            outbox_id=outbox_id,
            user_id=user_id,
            tenant_id=tenant_id,
            notification_type=notification_type,
            title=title,
            body=body,
            action_url=action_url,
            action_label=action_label,
            source_record_type=source_record_type,
            source_record_id=source_record_id,
            severity=severity,
            read_status=READ_UNREAD,
        )
        db.add(notif)
        await db.flush()
        return ChannelResult(
            success=True,
            status=DELIVERY_DELIVERED,
            provider_name=self.provider_name,
            provider_message_id=str(notif.id),
        )


def _stub_result(provider_name: str) -> ChannelResult:
    return ChannelResult(
        success=False,
        status=DELIVERY_PROVIDER_NOT_CONFIGURED,
        provider_name=provider_name,
        failure_code="PROVIDER_NOT_CONFIGURED",
        failure_message=f"{provider_name.title()} provider is not configured.",
    )


class EmailNotificationProviderStub:
    provider_name = "email_stub"

    async def deliver(self, **_kwargs) -> ChannelResult:
        return _stub_result(self.provider_name)


class SmsNotificationProviderStub:
    provider_name = "sms_stub"

    async def deliver(self, **_kwargs) -> ChannelResult:
        return _stub_result(self.provider_name)


class WhatsAppNotificationProviderStub:
    provider_name = "whatsapp_stub"

    async def deliver(self, **_kwargs) -> ChannelResult:
        return _stub_result(self.provider_name)


class PushNotificationProviderStub:
    provider_name = "push_stub"

    async def deliver(self, **_kwargs) -> ChannelResult:
        return _stub_result(self.provider_name)


_in_app_provider  = InAppNotificationProvider()
_email_provider   = EmailNotificationProviderStub()
_sms_provider     = SmsNotificationProviderStub()
_whatsapp_provider= WhatsAppNotificationProviderStub()
_push_provider    = PushNotificationProviderStub()

CHANNEL_PROVIDERS = {
    "in_app":    _in_app_provider,
    "email":     _email_provider,
    "sms":       _sms_provider,
    "whatsapp":  _whatsapp_provider,
    "push":      _push_provider,
}
