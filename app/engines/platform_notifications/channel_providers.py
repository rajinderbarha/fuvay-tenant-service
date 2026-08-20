"""Sprint 27 — Notification Channel Provider Abstraction.

InAppNotificationProvider: actually creates in_app_notifications records.
All external channel stubs: return provider_not_configured unless real config exists.
Do not claim delivered unless provider confirms.
"""
from __future__ import annotations
import asyncio
import smtplib
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import httpx

from app.engines.platform_notifications.constants import (
    DELIVERY_PROVIDER_NOT_CONFIGURED, DELIVERY_DELIVERED, DELIVERY_FAILED,
    READ_UNREAD,
)
from app.engines.platform_notifications.models import InAppNotification
from app.engines.platform_notifications.channel_config_service import channel_config_service
from app.engines.auth.models import User
from app.engines.platform_notifications.push_device_models import StaffPushDevice


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
        vertical_key: str | None = None,
        is_mandatory: bool = False,
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
            vertical_key=vertical_key,
            is_mandatory=is_mandatory,
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


async def _user(db: AsyncSession, user_id: uuid.UUID | None) -> User | None:
    if not user_id:
        return None
    return (await db.execute(select(User).where(User.id == user_id, User.is_active == True))).scalar_one_or_none()  # noqa: E712


def _failure(provider: str, code: str, message: str) -> ChannelResult:
    return ChannelResult(False, DELIVERY_FAILED, provider, failure_code=code, failure_message=message[:500])


class EmailNotificationProvider:
    provider_name = "smtp"

    async def deliver(self, *, db: AsyncSession, user_id: uuid.UUID | None, title: str, body: str, **_kwargs) -> ChannelResult:
        active = await channel_config_service.get_active(db, "email")
        if not active:
            return _stub_result(self.provider_name)
        config, credentials = active
        user = await _user(db, user_id)
        if not user or not user.email:
            return _failure(self.provider_name, "RECIPIENT_EMAIL_MISSING", "The recipient has no active email address.")

        def send() -> None:
            from email.mime.text import MIMEText
            msg = MIMEText(body, "plain", "utf-8")
            msg["Subject"], msg["From"], msg["To"] = title, config["from_email"], user.email
            cls = smtplib.SMTP_SSL if config.get("use_tls") == "ssl" else smtplib.SMTP
            with cls(config["host"], int(config["port"]), timeout=10) as server:
                if config.get("use_tls") == "starttls":
                    server.starttls()
                server.login(config["username"], credentials["password"])
                server.sendmail(config["from_email"], [user.email], msg.as_string())
        try:
            await asyncio.to_thread(send)
            return ChannelResult(True, DELIVERY_DELIVERED, self.provider_name)
        except Exception as exc:
            return _failure(self.provider_name, "SMTP_DELIVERY_FAILED", str(exc))


class TwilioNotificationProvider:
    def __init__(self, channel: str):
        self.channel = channel
        self.provider_name = "twilio_whatsapp" if channel == "whatsapp" else "twilio_sms"

    async def deliver(self, *, db: AsyncSession, user_id: uuid.UUID | None, body: str, **_kwargs) -> ChannelResult:
        active = await channel_config_service.get_active(db, self.channel)
        if not active:
            return _stub_result(self.provider_name)
        config, credentials = active
        user = await _user(db, user_id)
        if not user or not user.phone:
            return _failure(self.provider_name, "RECIPIENT_PHONE_MISSING", "The recipient has no active phone number.")
        prefix = "whatsapp:" if self.channel == "whatsapp" else ""
        url = f"https://api.twilio.com/2010-04-01/Accounts/{config['account_sid']}/Messages.json"
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(url, auth=(config["account_sid"], credentials["auth_token"]), data={
                    "From": f"{prefix}{config['from_number']}", "To": f"{prefix}{user.phone}", "Body": body,
                })
            payload = response.json() if response.content else {}
            if response.status_code not in {200, 201}:
                return _failure(self.provider_name, "TWILIO_DELIVERY_FAILED", payload.get("message", f"HTTP {response.status_code}"))
            return ChannelResult(True, DELIVERY_DELIVERED, self.provider_name, provider_message_id=payload.get("sid"))
        except Exception as exc:
            return _failure(self.provider_name, "TWILIO_DELIVERY_FAILED", str(exc))


class ExpoPushNotificationProvider:
    provider_name = "expo_push"

    async def deliver(self, *, db: AsyncSession, user_id: uuid.UUID | None, title: str, body: str, payload: dict | None = None, **_kwargs) -> ChannelResult:
        active = await channel_config_service.get_active(db, "push")
        if not active:
            return _stub_result(self.provider_name)
        _config, credentials = active
        devices = (await db.execute(select(StaffPushDevice).where(
            StaffPushDevice.user_id == user_id, StaffPushDevice.revoked_at.is_(None),
        ))).scalars().all()
        tokens = [d.expo_push_token for d in devices]
        if not tokens:
            return _failure(self.provider_name, "RECIPIENT_DEVICE_MISSING", "The recipient has no registered push device.")
        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        if credentials.get("access_token"):
            headers["Authorization"] = f"Bearer {credentials['access_token']}"
        messages = [{"to": token, "title": title, "body": body, "data": payload or {}} for token in tokens]
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post("https://exp.host/--/api/v2/push/send", json=messages, headers=headers)
            result = response.json() if response.content else {}
            tickets = result.get("data", []) if response.status_code == 200 else []
            errors = [t.get("message", "Push rejected") for t in tickets if t.get("status") == "error"]
            sent = [t for t in tickets if t.get("status") == "ok"]
            if response.status_code != 200 or not sent:
                return _failure(self.provider_name, "EXPO_DELIVERY_FAILED", "; ".join(errors) or f"HTTP {response.status_code}")
            return ChannelResult(True, DELIVERY_DELIVERED, self.provider_name, provider_message_id=sent[0].get("id"))
        except Exception as exc:
            return _failure(self.provider_name, "EXPO_DELIVERY_FAILED", str(exc))


_in_app_provider  = InAppNotificationProvider()
_email_provider   = EmailNotificationProvider()
_sms_provider     = TwilioNotificationProvider("sms")
_whatsapp_provider= TwilioNotificationProvider("whatsapp")
_push_provider    = ExpoPushNotificationProvider()

CHANNEL_PROVIDERS = {
    "in_app":    _in_app_provider,
    "email":     _email_provider,
    "sms":       _sms_provider,
    "whatsapp":  _whatsapp_provider,
    "push":      _push_provider,
}
