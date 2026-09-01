"""Encrypted, admin-controlled Meta booking channel configuration."""
from __future__ import annotations

import hashlib
import json
import re
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.messaging_gateway import meta_client
from app.engines.messaging_gateway.constants import (
    CHANNEL_INSTAGRAM,
    CHANNEL_WHATSAPP,
    CONFIG_CHANNEL_BY_PUBLIC,
    CONFIG_CHANNEL_INSTAGRAM,
    CONFIG_CHANNEL_WHATSAPP,
    DEFAULT_GRAPH_API_VERSION,
    VALID_CHANNELS,
)
from app.engines.notification.models import NotificationChannelConfig
from app.engines.platform_notifications.channel_config_service import (
    PLATFORM_CONFIG_TENANT_ID,
    channel_config_service,
)
from app.engines.platform_notifications.models import NotificationChannelConfigAudit
from app.exceptions import ServiceOSException


CHANNEL_DEFINITIONS: dict[str, dict[str, Any]] = {
    CHANNEL_WHATSAPP: {
        "storage_key": CONFIG_CHANNEL_WHATSAPP,
        "label": "WhatsApp booking",
        "provider": "Meta WhatsApp Cloud API",
        "description": "Book and track home services from a WhatsApp conversation.",
        "business_field": "phone_number_id",
        "fields": [
            {"key": "phone_number_id", "label": "Phone number ID", "type": "text", "required": True, "secret": False, "placeholder": "Meta WhatsApp phone number ID"},
            {"key": "business_account_id", "label": "WhatsApp Business Account ID", "type": "text", "required": False, "secret": False, "placeholder": "Optional WABA ID"},
            {"key": "booking_flow_id", "label": "Published booking Flow ID", "type": "text", "required": False, "secret": False, "placeholder": "Optional Meta Flow ID"},
            {"key": "api_version", "label": "Graph API version", "type": "text", "required": True, "secret": False, "placeholder": DEFAULT_GRAPH_API_VERSION},
            {"key": "app_secret", "label": "Meta app secret", "type": "password", "required": True, "secret": True, "placeholder": "Enter to set or rotate"},
            {"key": "verify_token", "label": "Webhook verify token", "type": "password", "required": True, "secret": True, "placeholder": "Choose a long random value"},
            {"key": "access_token", "label": "Permanent system-user access token", "type": "password", "required": True, "secret": True, "placeholder": "Enter to set or rotate"},
        ],
    },
    CHANNEL_INSTAGRAM: {
        "storage_key": CONFIG_CHANNEL_INSTAGRAM,
        "label": "Instagram booking",
        "provider": "Meta Instagram Messaging API",
        "description": "Book and track home services from Instagram Direct.",
        "business_field": "instagram_account_id",
        "fields": [
            {"key": "instagram_account_id", "label": "Instagram professional account ID", "type": "text", "required": True, "secret": False, "placeholder": "Instagram professional account ID"},
            {"key": "api_version", "label": "Graph API version", "type": "text", "required": True, "secret": False, "placeholder": DEFAULT_GRAPH_API_VERSION},
            {"key": "app_secret", "label": "Meta app secret", "type": "password", "required": True, "secret": True, "placeholder": "Enter to set or rotate"},
            {"key": "verify_token", "label": "Webhook verify token", "type": "password", "required": True, "secret": True, "placeholder": "Choose a long random value"},
            {"key": "access_token", "label": "Instagram access token", "type": "password", "required": True, "secret": True, "placeholder": "Enter to set or rotate"},
        ],
    },
}


class MessagingChannelConfigService:
    async def _row(self, db: AsyncSession, channel: str) -> NotificationChannelConfig | None:
        definition = self._definition(channel)
        return (await db.execute(select(NotificationChannelConfig).where(
            NotificationChannelConfig.tenant_id == PLATFORM_CONFIG_TENANT_ID,
            NotificationChannelConfig.channel == definition["storage_key"],
        ))).scalar_one_or_none()

    @staticmethod
    def _definition(channel: str) -> dict[str, Any]:
        if channel not in VALID_CHANNELS:
            raise ServiceOSException("MESSAGING_CHANNEL_NOT_FOUND", "Unknown messaging channel.", status_code=404)
        return CHANNEL_DEFINITIONS[channel]

    def _credentials(self, row: NotificationChannelConfig | None) -> dict[str, Any]:
        return channel_config_service.decrypt(row)

    def _merged(self, row: NotificationChannelConfig | None) -> dict[str, Any]:
        return {**(dict(row.config or {}) if row else {}), **self._credentials(row)}

    async def get(self, db: AsyncSession, channel: str, *, require_enabled: bool = False) -> dict[str, Any] | None:
        row = await self._row(db, channel)
        if not row:
            return None
        if require_enabled and (not row.is_enabled or row.last_test_status != "passed"):
            return None
        return self._merged(row)

    async def list_public(self, db: AsyncSession) -> list[dict[str, Any]]:
        return [await self.public_item(db, channel) for channel in (CHANNEL_WHATSAPP, CHANNEL_INSTAGRAM)]

    async def public_item(self, db: AsyncSession, channel: str) -> dict[str, Any]:
        definition = self._definition(channel)
        row = await self._row(db, channel)
        credentials = self._credentials(row)
        config = dict(row.config or {}) if row else {}
        fields = []
        for source in definition["fields"]:
            field = dict(source)
            value = credentials.get(field["key"]) if field["secret"] else config.get(field["key"])
            field["has_value"] = value not in (None, "")
            field["value"] = "" if field["secret"] else str(value or "")
            fields.append(field)
        complete = all(not item["required"] or item["has_value"] for item in fields)
        tested = bool(row and row.last_test_status == "passed")
        enabled = bool(row and row.is_enabled)
        return {
            "channel": channel,
            "label": definition["label"],
            "provider": definition["provider"],
            "description": definition["description"],
            "configured": complete,
            "enabled": enabled,
            "verified": tested,
            "state": "Live" if enabled and tested else "Failed" if row and row.last_test_status == "failed" else "Ready to enable" if complete and tested else "Needs testing" if complete else "Not configured",
            "fields": fields,
            "webhook_path": f"/v1/messaging/meta/webhook/{channel}",
            "last_tested_at": row.last_tested_at.isoformat() if row and row.last_tested_at else None,
            "last_test_status": row.last_test_status if row else None,
            "last_test_message": row.last_test_message if row else None,
            "credential_fingerprint": row.credential_fingerprint if row else None,
            "profile_synced_at": config.get("profile_synced_at"),
            "profile_sync_status": config.get("profile_sync_status"),
            "profile_sync_message": config.get("profile_sync_message"),
            "booking_flow_configured": bool(
                channel == CHANNEL_WHATSAPP and config.get("booking_flow_id")
            ),
        }

    def _validate(self, channel: str, config: dict[str, Any], credentials: dict[str, Any]) -> None:
        definition = self._definition(channel)
        missing = []
        for field in definition["fields"]:
            value = credentials.get(field["key"]) if field["secret"] else config.get(field["key"])
            if field["required"] and not str(value or "").strip():
                missing.append(field["label"])
        if missing:
            raise ServiceOSException("MESSAGING_CHANNEL_CONFIG_INCOMPLETE", f"Required fields missing: {', '.join(missing)}", status_code=422)
        business_id = str(config.get(definition["business_field"]) or "")
        if not business_id.isdigit():
            raise ServiceOSException("MESSAGING_CHANNEL_CONFIG_INVALID", "Meta business account IDs must contain digits only.", status_code=422)
        if not re.fullmatch(r"v\d+\.0", str(config.get("api_version") or "")):
            raise ServiceOSException("MESSAGING_CHANNEL_CONFIG_INVALID", "Graph API version must look like v26.0.", status_code=422)
        if channel == CHANNEL_WHATSAPP:
            flow_id = str(config.get("booking_flow_id") or "").strip()
            if flow_id and not flow_id.isdigit():
                raise ServiceOSException(
                    "MESSAGING_CHANNEL_CONFIG_INVALID",
                    "The WhatsApp booking Flow ID must contain digits only.",
                    status_code=422,
                )
        if len(str(credentials.get("verify_token") or "")) < 24:
            raise ServiceOSException("MESSAGING_CHANNEL_CONFIG_INVALID", "Webhook verify token must be at least 24 characters.", status_code=422)

    async def save(self, db: AsyncSession, channel: str, values: dict[str, Any], actor_id: uuid.UUID | None) -> dict[str, Any]:
        definition = self._definition(channel)
        row = await self._row(db, channel)
        before = self._state(row)
        config = dict(row.config or {}) if row else {}
        credentials = self._credentials(row)
        allowed = {field["key"]: field for field in definition["fields"]}
        changed = False
        for key, value in values.items():
            field = allowed.get(key)
            if not field:
                continue
            if field["secret"]:
                if value not in (None, ""):
                    credentials[key] = str(value).strip()
                    changed = True
            else:
                next_value = str(value).strip()
                if config.get(key) != next_value:
                    changed = True
                config[key] = next_value
        config.setdefault("api_version", DEFAULT_GRAPH_API_VERSION)
        self._validate(channel, config, credentials)
        if not row:
            row = NotificationChannelConfig(
                tenant_id=PLATFORM_CONFIG_TENANT_ID,
                channel=definition["storage_key"],
                provider_name=definition["provider"],
                config={},
                is_enabled=False,
            )
            db.add(row)
            changed = True
        row.provider_name = definition["provider"]
        row.config = config
        row.encrypted_credentials = channel_config_service._encrypt(credentials)
        row.credential_fingerprint = hashlib.sha256(json.dumps(credentials, sort_keys=True).encode()).hexdigest()[:12]
        row.configured_by_user_id = actor_id
        if changed:
            row.is_enabled = False
            row.last_test_status = None
            row.last_tested_at = None
            row.last_test_message = "Configuration saved. Test the connection before enabling booking."
        await db.flush()
        db.add(NotificationChannelConfigAudit(
            channel=definition["storage_key"], action="configured", actor_user_id=actor_id,
            before_state=before, after_state=self._state(row),
        ))
        await db.commit()
        return await self.public_item(db, channel)

    async def test(self, db: AsyncSession, channel: str, actor_id: uuid.UUID | None) -> dict[str, Any]:
        definition = self._definition(channel)
        row = await self._row(db, channel)
        if not row:
            raise ServiceOSException("MESSAGING_CHANNEL_CONFIG_INCOMPLETE", "Configure this channel first.", status_code=422)
        merged = self._merged(row)
        self._validate(channel, dict(row.config or {}), self._credentials(row))
        passed, message, alternates = await meta_client.test_connection(channel, merged)
        if passed and alternates:
            # Meta may name the SAME account by a different id in an inbound
            # webhook than the one the send API is addressed with. Record the
            # alternates so `accepts_business_id` recognises both, rather than
            # dropping every real message as "not our account".
            config = dict(row.config or {})
            known = {str(i) for i in (config.get("alternate_business_ids") or [])}
            config["alternate_business_ids"] = sorted(known | {str(a) for a in alternates})
            row.config = config
        row.last_tested_at = datetime.now(timezone.utc)
        row.last_test_status = "passed" if passed else "failed"
        row.last_test_message = message[:500]
        row.verified_at = row.last_tested_at if passed else None
        if not passed:
            row.is_enabled = False
        db.add(NotificationChannelConfigAudit(
            channel=definition["storage_key"], action="connection_test", actor_user_id=actor_id,
            before_state=None, after_state={"passed": passed, "message": message[:200]},
        ))
        await db.commit()
        if not passed:
            raise ServiceOSException("MESSAGING_CHANNEL_CONNECTION_FAILED", message, status_code=422)
        return await self.public_item(db, channel)

    async def set_enabled(self, db: AsyncSession, channel: str, enabled: bool, actor_id: uuid.UUID | None) -> dict[str, Any]:
        definition = self._definition(channel)
        row = await self._row(db, channel)
        if not row:
            raise ServiceOSException("MESSAGING_CHANNEL_CONFIG_INCOMPLETE", "Configure this channel first.", status_code=422)
        if enabled and row.last_test_status != "passed":
            raise ServiceOSException("MESSAGING_CHANNEL_TEST_REQUIRED", "Run a successful connection test before enabling booking.", status_code=409)
        before = self._state(row)
        row.is_enabled = enabled
        row.configured_by_user_id = actor_id
        db.add(NotificationChannelConfigAudit(
            channel=definition["storage_key"], action="enabled" if enabled else "disabled",
            actor_user_id=actor_id, before_state=before, after_state=self._state(row),
        ))
        await db.commit()
        return await self.public_item(db, channel)

    async def sync_profile(
        self, db: AsyncSession, channel: str, actor_id: uuid.UUID | None,
    ) -> dict[str, Any]:
        """Publish Instagram's managed conversation entry points.

        Kept separate from save/test/enable so an ordinary deployment or
        credential rotation cannot silently rewrite a live business profile.
        """
        if channel != CHANNEL_INSTAGRAM:
            raise ServiceOSException(
                "MESSAGING_PROFILE_UNSUPPORTED",
                "Managed conversation entry points are available for Instagram only.",
                status_code=422,
            )
        definition = self._definition(channel)
        row = await self._row(db, channel)
        if not row:
            raise ServiceOSException(
                "MESSAGING_CHANNEL_CONFIG_INCOMPLETE",
                "Configure Instagram first.", status_code=422,
            )
        if row.last_test_status != "passed":
            raise ServiceOSException(
                "MESSAGING_CHANNEL_TEST_REQUIRED",
                "Run a successful connection test before publishing Instagram entry points.",
                status_code=409,
            )

        result = await meta_client.sync_instagram_profile(self._merged(row))
        now = datetime.now(timezone.utc)
        response = result.get("response") if isinstance(result, dict) else None
        error = response.get("error") if isinstance(response, dict) else None
        message = (
            "Four booking icebreakers are live on Instagram."
            if result.get("sent") else
            str((error or {}).get("message") or result.get("reason") or
                "Meta rejected the Instagram profile update.")
        )
        config = dict(row.config or {})
        config.update({
            "profile_synced_at": now.isoformat(),
            "profile_sync_status": "passed" if result.get("sent") else "failed",
            "profile_sync_message": message[:500],
        })
        row.config = config
        row.configured_by_user_id = actor_id
        db.add(NotificationChannelConfigAudit(
            channel=definition["storage_key"], action="profile_sync",
            actor_user_id=actor_id, before_state=None,
            after_state={"passed": bool(result.get("sent")), "message": message[:200]},
        ))
        await db.commit()
        if not result.get("sent"):
            raise ServiceOSException(
                "MESSAGING_PROFILE_SYNC_FAILED", message, status_code=422,
            )
        return await self.public_item(db, channel)

    async def audit(self, db: AsyncSession, channel: str, limit: int = 50) -> list[dict[str, Any]]:
        storage_key = self._definition(channel)["storage_key"]
        rows = (await db.execute(select(NotificationChannelConfigAudit).where(
            NotificationChannelConfigAudit.channel == storage_key,
        ).order_by(NotificationChannelConfigAudit.created_at.desc()).limit(limit))).scalars().all()
        return [{
            "id": str(item.id), "channel": channel, "action": item.action,
            "actor_user_id": str(item.actor_user_id) if item.actor_user_id else None,
            "before_state": item.before_state, "after_state": item.after_state,
            "created_at": item.created_at.isoformat(),
        } for item in rows]

    async def accepts_business_id(self, db: AsyncSession, channel: str, business_id: str | None) -> bool:
        """Is this inbound event addressed to the account we are configured for?

        Accepts every identifier Meta uses for that one account, not only the
        one the send API is addressed with: Instagram names the same account by
        its app-scoped id in some places and its professional-account id in
        others, and matching on a single id silently drops real messages.
        """
        config = await self.get(db, channel, require_enabled=True)
        if not config or not business_id:
            return False
        field = self._definition(channel)["business_field"]
        accepted = {str(config.get(field) or "")}
        accepted.update(str(i) for i in (config.get("alternate_business_ids") or []))
        accepted.discard("")
        return str(business_id) in accepted

    @staticmethod
    def _state(row: NotificationChannelConfig | None) -> dict[str, Any]:
        return {
            "configured": bool(row and (row.config or row.encrypted_credentials)),
            "enabled": bool(row and row.is_enabled),
            "last_test_status": row.last_test_status if row else None,
            "credential_fingerprint": row.credential_fingerprint if row else None,
        }


messaging_channel_config_service = MessagingChannelConfigService()
