"""Secure lifecycle management for notification delivery providers."""
from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import smtplib
from datetime import datetime, timezone
from email.utils import parseaddr
import uuid

import httpx
from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.engines.platform_notifications.constants import ALL_CHANNELS, CHANNEL_IN_APP
from app.engines.notification.models import NotificationChannelConfig
from app.engines.platform_notifications.models import NotificationChannelConfigAudit
from app.exceptions import ServiceOSException


PROVIDER_DEFINITIONS: dict[str, dict] = {
    "in_app": {
        "provider": "ServiceOS Inbox", "description": "Durable notifications stored in the ServiceOS inbox.",
        "fields": [], "managed": False,
    },
    "email": {
        "provider": "SMTP", "description": "Transactional email through your SMTP provider.", "managed": True,
        "fields": [
            {"key": "host", "label": "SMTP host", "type": "text", "required": True, "secret": False, "placeholder": "smtp.example.com"},
            {"key": "port", "label": "SMTP port", "type": "number", "required": True, "secret": False, "placeholder": "587"},
            {"key": "username", "label": "Username", "type": "text", "required": True, "secret": False, "placeholder": "notifications@example.com"},
            {"key": "from_email", "label": "From email", "type": "email", "required": True, "secret": False, "placeholder": "notifications@example.com"},
            {"key": "password", "label": "Password / API key", "type": "password", "required": True, "secret": True, "placeholder": "Enter to set or rotate"},
            {"key": "use_tls", "label": "TLS mode", "type": "select", "required": True, "secret": False,
             "options": [{"value": "starttls", "label": "STARTTLS"}, {"value": "ssl", "label": "Implicit TLS"}, {"value": "none", "label": "No TLS (not recommended)"}]},
        ],
    },
    "sms": {
        "provider": "Twilio SMS", "description": "SMS delivery through Twilio Messaging.", "managed": True,
        "fields": [
            {"key": "account_sid", "label": "Account SID", "type": "text", "required": True, "secret": False, "placeholder": "AC..."},
            {"key": "auth_token", "label": "Auth token", "type": "password", "required": True, "secret": True, "placeholder": "Enter to set or rotate"},
            {"key": "from_number", "label": "Sending number", "type": "text", "required": True, "secret": False, "placeholder": "+14155550100"},
        ],
    },
    "whatsapp": {
        "provider": "Twilio WhatsApp", "description": "Approved WhatsApp templates and messages through Twilio.", "managed": True,
        "fields": [
            {"key": "account_sid", "label": "Account SID", "type": "text", "required": True, "secret": False, "placeholder": "AC..."},
            {"key": "auth_token", "label": "Auth token", "type": "password", "required": True, "secret": True, "placeholder": "Enter to set or rotate"},
            {"key": "from_number", "label": "WhatsApp sender", "type": "text", "required": True, "secret": False, "placeholder": "+14155238886"},
        ],
    },
    "push": {
        "provider": "Expo Push", "description": "Native mobile push to registered Expo devices.", "managed": True,
        "fields": [
            {"key": "access_token", "label": "Expo access token (optional)", "type": "password", "required": False, "secret": True, "placeholder": "Optional enhanced security token"},
        ],
    },
}

PLATFORM_CONFIG_TENANT_ID = uuid.UUID("00000000-0000-0000-0000-000000000000")


class NotificationChannelConfigService:
    def _fernet(self) -> Fernet:
        settings = get_settings()
        configured = settings.NOTIFICATION_CREDENTIAL_KEY.strip()
        if configured:
            try:
                return Fernet(configured.encode())
            except (ValueError, TypeError) as exc:
                raise RuntimeError("NOTIFICATION_CREDENTIAL_KEY is not a valid Fernet key") from exc
        material = hashlib.sha256(settings.SECRET_KEY.encode("utf-8")).digest()
        return Fernet(base64.urlsafe_b64encode(material))

    def _encrypt(self, credentials: dict) -> str | None:
        if not credentials:
            return None
        return self._fernet().encrypt(json.dumps(credentials, separators=(",", ":")).encode()).decode()

    def decrypt(self, row: NotificationChannelConfig | None) -> dict:
        if not row or not row.encrypted_credentials:
            return {}
        try:
            return json.loads(self._fernet().decrypt(row.encrypted_credentials.encode()).decode())
        except (InvalidToken, ValueError, json.JSONDecodeError) as exc:
            raise ServiceOSException("CHANNEL_CREDENTIAL_DECRYPTION_FAILED", "Stored channel credentials cannot be decrypted. Rotate the credentials.", status_code=409) from exc

    @staticmethod
    def _state(row: NotificationChannelConfig | None) -> dict:
        if not row:
            return {"configured": False, "enabled": False, "last_test_status": None}
        return {
            "configured": bool(row.encrypted_credentials or row.config),
            "enabled": row.is_enabled,
            "last_test_status": row.last_test_status,
            "credential_fingerprint": row.credential_fingerprint,
        }

    async def get_row(self, db: AsyncSession, channel: str) -> NotificationChannelConfig | None:
        return (await db.execute(select(NotificationChannelConfig).where(
            NotificationChannelConfig.tenant_id == PLATFORM_CONFIG_TENANT_ID,
            NotificationChannelConfig.channel == channel))).scalar_one_or_none()

    async def get_active(self, db: AsyncSession, channel: str) -> tuple[dict, dict] | None:
        row = await self.get_row(db, channel)
        if not row or not row.is_enabled or row.last_test_status != "passed":
            return None
        return dict(row.config or {}), self.decrypt(row)

    async def list_public(self, db: AsyncSession) -> list[dict]:
        rows = (await db.execute(select(NotificationChannelConfig).where(
            NotificationChannelConfig.tenant_id == PLATFORM_CONFIG_TENANT_ID,
        ))).scalars().all()
        by_channel = {r.channel: r for r in rows}
        return [self.public_item(channel, by_channel.get(channel)) for channel in ALL_CHANNELS]

    def public_item(self, channel: str, row: NotificationChannelConfig | None) -> dict:
        definition = PROVIDER_DEFINITIONS[channel]
        if channel == CHANNEL_IN_APP:
            return {
                "channel": channel, "provider": definition["provider"], "description": definition["description"],
                "managed": False, "configured": True, "setup_complete": True, "enabled": True, "verified": True,
                "state": "Available",
                "fields": [], "last_tested_at": None, "last_test_status": "passed",
                "last_test_message": "Built-in durable inbox is operational.", "credential_fingerprint": None,
            }
        credentials = self.decrypt(row) if row else {}
        config = dict(row.config or {}) if row else {}
        fields = []
        for field in definition["fields"]:
            item = dict(field)
            value = credentials.get(field["key"]) if field["secret"] else config.get(field["key"])
            item["has_value"] = value not in (None, "")
            item["value"] = "" if field["secret"] else (str(value) if value is not None else "")
            fields.append(item)
        setup_complete = bool(row) and all((not f["required"]) or f["has_value"] for f in fields)
        enabled = bool(row and row.is_enabled)
        verified = bool(row and row.last_test_status == "passed")
        live = enabled and verified
        state = "Available" if live else "Failed" if row and row.last_test_status == "failed" else "Ready to enable" if setup_complete else "Not Configured"
        return {
            "channel": channel, "provider": definition["provider"], "description": definition["description"],
            "managed": True, "configured": live, "setup_complete": setup_complete,
            "enabled": enabled, "verified": verified, "state": state, "fields": fields,
            "last_tested_at": row.last_tested_at.isoformat() if row and row.last_tested_at else None,
            "last_test_status": row.last_test_status if row else None,
            "last_test_message": row.last_test_message if row else None,
            "credential_fingerprint": row.credential_fingerprint if row else None,
        }

    def _validate(self, channel: str, config: dict, credentials: dict) -> None:
        definition = PROVIDER_DEFINITIONS.get(channel)
        if not definition or channel == CHANNEL_IN_APP:
            raise ServiceOSException("CHANNEL_NOT_CONFIGURABLE", "This notification channel is not configurable.", status_code=422)
        missing = []
        for field in definition["fields"]:
            value = credentials.get(field["key"]) if field["secret"] else config.get(field["key"])
            if field["required"] and value in (None, ""):
                missing.append(field["label"])
        if missing:
            raise ServiceOSException("CHANNEL_CONFIG_INCOMPLETE", f"Required fields missing: {', '.join(missing)}", status_code=422)
        if channel == "email":
            try:
                port = int(config.get("port", 0))
            except (TypeError, ValueError):
                port = 0
            if not 1 <= port <= 65535:
                raise ServiceOSException("CHANNEL_CONFIG_INVALID", "SMTP port must be between 1 and 65535.", status_code=422)
            if parseaddr(str(config.get("from_email", "")))[1] != config.get("from_email") or "@" not in str(config.get("from_email", "")):
                raise ServiceOSException("CHANNEL_CONFIG_INVALID", "Enter a valid from email address.", status_code=422)
            if str(config.get("host", "")).startswith(("http://", "https://")):
                raise ServiceOSException("CHANNEL_CONFIG_INVALID", "SMTP host must not include a URL scheme.", status_code=422)
        if channel in {"sms", "whatsapp"}:
            if not str(config.get("account_sid", "")).startswith("AC"):
                raise ServiceOSException("CHANNEL_CONFIG_INVALID", "Twilio Account SID must start with AC.", status_code=422)
            if not str(config.get("from_number", "")).startswith("+"):
                raise ServiceOSException("CHANNEL_CONFIG_INVALID", "Sender number must use E.164 format, for example +14155550100.", status_code=422)

    async def save(self, db: AsyncSession, channel: str, values: dict, actor_id: uuid.UUID | None) -> dict:
        if channel not in PROVIDER_DEFINITIONS:
            raise ServiceOSException("CHANNEL_NOT_FOUND", "Unknown notification channel.", status_code=404)
        row = await self.get_row(db, channel)
        before = self._state(row)
        definition = PROVIDER_DEFINITIONS[channel]
        existing_credentials = self.decrypt(row)
        config = dict(row.config or {}) if row else {}
        original_config = dict(config)
        credentials = dict(existing_credentials)
        secrets_changed = False
        allowed = {f["key"]: f for f in definition["fields"]}
        for key, value in values.items():
            field = allowed.get(key)
            if not field:
                continue
            if field["secret"]:
                if value not in (None, ""):
                    credentials[key] = str(value)
                    secrets_changed = True
            else:
                config[key] = str(value).strip() if not isinstance(value, bool) else value
        if channel == "email":
            config.setdefault("use_tls", "starttls")
        self._validate(channel, config, credentials)
        fingerprint = hashlib.sha256(json.dumps(credentials, sort_keys=True).encode()).hexdigest()[:12] if credentials else None
        if not row:
            row = NotificationChannelConfig(tenant_id=PLATFORM_CONFIG_TENANT_ID, channel=channel, provider_name=definition["provider"], config={}, is_enabled=False)
            db.add(row)
        row.provider_name = definition["provider"]
        row.config = config
        row.encrypted_credentials = self._encrypt(credentials)
        row.credential_fingerprint = fingerprint
        row.configured_by_user_id = actor_id
        if secrets_changed or config != original_config or before.get("configured") is False:
            row.is_enabled = False
            row.last_test_status = None
            row.last_tested_at = None
            row.last_test_message = "Configuration saved. Test the connection before enabling delivery."
        await db.flush()
        after = self._state(row)
        db.add(NotificationChannelConfigAudit(channel=channel, action="configured", actor_user_id=actor_id, before_state=before, after_state=after))
        await db.commit()
        await db.refresh(row)
        return self.public_item(channel, row)

    async def set_enabled(self, db: AsyncSession, channel: str, enabled: bool, actor_id: uuid.UUID | None) -> dict:
        row = await self.get_row(db, channel)
        if not row:
            raise ServiceOSException("CHANNEL_CONFIG_INCOMPLETE", "Configure this channel first.", status_code=422)
        before = self._state(row)
        if enabled and row.last_test_status != "passed":
            raise ServiceOSException("CHANNEL_TEST_REQUIRED", "Run a successful connection test before enabling delivery.", status_code=409)
        row.is_enabled = enabled
        row.configured_by_user_id = actor_id
        await db.flush()
        db.add(NotificationChannelConfigAudit(channel=channel, action="enabled" if enabled else "disabled", actor_user_id=actor_id, before_state=before, after_state=self._state(row)))
        await db.commit()
        return self.public_item(channel, row)

    async def test(self, db: AsyncSession, channel: str, actor_id: uuid.UUID | None) -> dict:
        row = await self.get_row(db, channel)
        if not row:
            raise ServiceOSException("CHANNEL_CONFIG_INCOMPLETE", "Configure this channel first.", status_code=422)
        config, credentials = dict(row.config or {}), self.decrypt(row)
        self._validate(channel, config, credentials)
        passed, message = await self._test_connection(channel, config, credentials)
        row.last_tested_at = datetime.now(timezone.utc)
        row.last_test_status = "passed" if passed else "failed"
        row.last_test_message = message[:500]
        if not passed:
            row.is_enabled = False
        db.add(NotificationChannelConfigAudit(channel=channel, action="connection_test", actor_user_id=actor_id, before_state=None, after_state={"passed": passed, "message": message[:200]}))
        await db.commit()
        if not passed:
            raise ServiceOSException("CHANNEL_CONNECTION_FAILED", message, status_code=422)
        return self.public_item(channel, row)

    async def audit(self, db: AsyncSession, channel: str, limit: int = 50) -> list[dict]:
        rows = (await db.execute(select(NotificationChannelConfigAudit).where(
            NotificationChannelConfigAudit.channel == channel,
        ).order_by(NotificationChannelConfigAudit.created_at.desc()).limit(limit))).scalars().all()
        return [{
            "id": str(item.id), "channel": item.channel, "action": item.action,
            "actor_user_id": str(item.actor_user_id) if item.actor_user_id else None,
            "before_state": item.before_state, "after_state": item.after_state,
            "created_at": item.created_at.isoformat(),
        } for item in rows]

    async def _test_connection(self, channel: str, config: dict, credentials: dict) -> tuple[bool, str]:
        try:
            if channel == "email":
                def smtp_test() -> None:
                    cls = smtplib.SMTP_SSL if config.get("use_tls") == "ssl" else smtplib.SMTP
                    with cls(config["host"], int(config["port"]), timeout=10) as server:
                        if config.get("use_tls") == "starttls":
                            server.starttls()
                        server.login(config["username"], credentials["password"])
                await asyncio.to_thread(smtp_test)
                return True, "SMTP authentication succeeded."
            if channel in {"sms", "whatsapp"}:
                url = f"https://api.twilio.com/2010-04-01/Accounts/{config['account_sid']}.json"
                async with httpx.AsyncClient(timeout=10) as client:
                    response = await client.get(url, auth=(config["account_sid"], credentials["auth_token"]))
                if response.status_code != 200:
                    return False, f"Twilio rejected the credentials (HTTP {response.status_code})."
                return True, "Twilio account authentication succeeded."
            if channel == "push":
                async with httpx.AsyncClient(timeout=10) as client:
                    response = await client.get("https://exp.host")
                return response.status_code < 500, "Expo Push gateway is reachable."
        except Exception as exc:
            return False, f"Connection failed: {str(exc)[:350]}"
        return False, "Unsupported provider test."


channel_config_service = NotificationChannelConfigService()
