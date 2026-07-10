"""Sprint 27 — Platform NotificationService.

Rules:
- in_app channel always works (provider stores record).
- External channels return provider_not_configured if not configured.
- Notification failure NEVER rolls back business transaction.
- All outbox changes are committed in their own transaction.
"""
from __future__ import annotations
import uuid
import re
from datetime import datetime, timezone

import structlog
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.platform_notifications.constants import (
    CHANNEL_IN_APP, ALL_CHANNELS,
    DELIVERY_PENDING, DELIVERY_FAILED, DELIVERY_PREFERENCE_DISABLED,
    READ_READ, READ_UNREAD, READ_ARCHIVED,
    NOTIF_EVENT_CREATED, NOTIF_EVENT_PROCESSED, NOTIF_EVENT_FAILED,
    ERR_NOTIF_TEMPLATE_NOT_FOUND, ERR_NOTIF_OUTBOX_NOT_FOUND,
    ERR_NOTIF_OUTBOX_ACCESS_DENIED, ERR_NOTIF_RETRY_NOT_ALLOWED,
    ERR_IN_APP_NOT_FOUND, ERR_IN_APP_ACCESS_DENIED,
    MAX_RETRY_COUNT,
)
from app.engines.platform_notifications.models import (
    NotificationEvent, NotificationOutbox, InAppNotification,
    NotifEventTemplate, NotificationPreference,
)
from app.engines.platform_notifications.channel_providers import CHANNEL_PROVIDERS
from app.engines.platform_notifications.event_registry import NotificationEventRegistry

log = structlog.get_logger("platform_notifications")
utcnow = lambda: datetime.now(timezone.utc)


class NotificationService:

    async def fire_event(
        self,
        db: AsyncSession,
        event_key: str,
        payload: dict,
        tenant_id: uuid.UUID | None = None,
        customer_id: uuid.UUID | None = None,
        actor_user_id: uuid.UUID | None = None,
        source_record_type: str | None = None,
        source_record_id: uuid.UUID | None = None,
        recipients: list[dict] | None = None,
    ) -> NotificationEvent | None:
        """Create notification event + outbox records. Never raises — logs on error."""
        try:
            cfg = NotificationEventRegistry.get(event_key)
            if not cfg or not cfg.is_enabled:
                return None

            event = NotificationEvent(
                event_key=event_key,
                event_name=cfg.event_name,
                source_engine=cfg.source_engine,
                source_record_type=source_record_type,
                source_record_id=source_record_id,
                tenant_id=tenant_id,
                customer_id=customer_id,
                actor_user_id=actor_user_id,
                payload=payload,
                severity=cfg.severity,
                status=NOTIF_EVENT_CREATED,
            )
            db.add(event)
            await db.flush()

            if recipients:
                for recip in recipients:
                    await self._create_outbox_for_recipient(
                        db, event, cfg, recip, payload,
                        source_record_type, source_record_id,
                    )

            event.status = NOTIF_EVENT_PROCESSED
            event.processed_at = utcnow()
            await db.commit()
            return event
        except Exception as exc:
            log.warning("notification.fire_event_failed", event_key=event_key, error=str(exc))
            return None

    async def _create_outbox_for_recipient(
        self,
        db: AsyncSession,
        event: NotificationEvent,
        cfg,
        recip: dict,
        payload: dict,
        source_record_type: str | None,
        source_record_id: uuid.UUID | None,
    ) -> None:
        user_id = recip.get("user_id")
        if not user_id:
            return
        recipient_type = recip.get("recipient_type", "customer")

        for channel in cfg.default_channels:
            pref_enabled = await self._check_preference(db, uuid.UUID(str(user_id)), event.event_key, channel)

            tmpl = await self._get_template(db, f"{event.event_key}.{channel}")
            if not tmpl:
                tmpl = await self._get_template(db, cfg.template_key)

            if not tmpl:
                log.warning("notification.template_missing", event_key=event.event_key, channel=channel)
                continue

            title = self._render(tmpl.subject_template or tmpl.template_name, payload)
            body  = self._render(tmpl.body_template, payload)
            action_url   = self._render(tmpl.action_url_template or "", payload) or None
            action_label = tmpl.action_label_template

            outbox = NotificationOutbox(
                notification_event_id=event.id,
                recipient_user_id=uuid.UUID(str(user_id)),
                recipient_type=recipient_type,
                tenant_id=event.tenant_id,
                channel=channel,
                template_key=tmpl.template_key,
                title=title,
                body=body,
                action_url=action_url,
                action_label=action_label,
                payload=payload,
                delivery_status=DELIVERY_PENDING if pref_enabled else DELIVERY_PREFERENCE_DISABLED,
                max_retries=MAX_RETRY_COUNT,
            )
            db.add(outbox)
            await db.flush()

            if pref_enabled:
                await self._dispatch_outbox(db, outbox, source_record_type, source_record_id)

    async def dispatch_pending(self, db: AsyncSession, limit: int = 50) -> dict:
        """Process pending outbox records. Safe to run repeatedly."""
        r = await db.execute(
            select(NotificationOutbox)
            .where(NotificationOutbox.delivery_status == DELIVERY_PENDING)
            .order_by(NotificationOutbox.created_at)
            .limit(limit)
        )
        items = r.scalars().all()
        processed = failed = skipped = 0
        for outbox in items:
            try:
                await self._dispatch_outbox(db, outbox, None, None)
                processed += 1
            except Exception as exc:
                log.warning("dispatch.failed", outbox_id=str(outbox.id), error=str(exc))
                failed += 1
        await db.commit()
        return {"processed": processed, "failed": failed, "skipped": skipped}

    async def retry_failed(self, db: AsyncSession, limit: int = 50) -> dict:
        """Retry failed outbox records that haven't exceeded max_retries."""
        r = await db.execute(
            select(NotificationOutbox)
            .where(
                NotificationOutbox.delivery_status == DELIVERY_FAILED,
                NotificationOutbox.retry_count < NotificationOutbox.max_retries,
            )
            .order_by(NotificationOutbox.created_at)
            .limit(limit)
        )
        items = r.scalars().all()
        retried = skipped = 0
        for outbox in items:
            outbox.delivery_status = DELIVERY_PENDING
            outbox.retry_count += 1
            retried += 1
        await db.commit()
        return {"retried": retried, "skipped": skipped}

    async def get_outbox_record(
        self,
        db: AsyncSession,
        outbox_id: uuid.UUID,
    ) -> NotificationOutbox:
        r = await db.execute(select(NotificationOutbox).where(NotificationOutbox.id == outbox_id))
        outbox = r.scalars().first()
        if not outbox:
            raise ValueError(ERR_NOTIF_OUTBOX_NOT_FOUND)
        return outbox

    async def retry_outbox(
        self,
        db: AsyncSession,
        outbox_id: uuid.UUID,
    ) -> NotificationOutbox:
        outbox = await self.get_outbox_record(db, outbox_id)
        if outbox.retry_count >= outbox.max_retries:
            raise ValueError(ERR_NOTIF_RETRY_NOT_ALLOWED)
        outbox.retry_count += 1
        outbox.delivery_status = DELIVERY_PENDING
        await db.commit()
        return outbox

    async def list_outbox(
        self,
        db: AsyncSession,
        delivery_status: str | None = None,
        channel: str | None = None,
        recipient_type: str | None = None,
        tenant_id: uuid.UUID | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> dict:
        q = select(NotificationOutbox)
        if delivery_status:
            q = q.where(NotificationOutbox.delivery_status == delivery_status)
        if channel:
            q = q.where(NotificationOutbox.channel == channel)
        if recipient_type:
            q = q.where(NotificationOutbox.recipient_type == recipient_type)
        if tenant_id:
            q = q.where(NotificationOutbox.tenant_id == tenant_id)
        total_r = await db.execute(select(func.count()).select_from(q.subquery()))
        total = total_r.scalar_one()
        r = await db.execute(q.order_by(NotificationOutbox.created_at.desc()).limit(limit).offset(offset))
        items = r.scalars().all()
        return {"items": [i.to_dict() for i in items], "total": total, "limit": limit, "offset": offset}

    # ── In-app notifications ──────────────────────────────────────────────────

    async def get_user_notifications(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        read_status: str | None = None,
        limit: int = 30,
        offset: int = 0,
    ) -> dict:
        q = select(InAppNotification).where(InAppNotification.user_id == user_id)
        if read_status:
            q = q.where(InAppNotification.read_status == read_status)
        total_r = await db.execute(select(func.count()).select_from(q.subquery()))
        total = total_r.scalar_one()
        r = await db.execute(q.order_by(InAppNotification.created_at.desc()).limit(limit).offset(offset))
        items = r.scalars().all()
        return {"items": [i.to_dict() for i in items], "total": total, "unread_count": None}

    async def get_unread_count(self, db: AsyncSession, user_id: uuid.UUID) -> int:
        r = await db.execute(
            select(func.count()).where(
                InAppNotification.user_id == user_id,
                InAppNotification.read_status == READ_UNREAD,
            )
        )
        return r.scalar_one()

    async def mark_notification_read(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        notification_id: uuid.UUID,
    ) -> InAppNotification:
        r = await db.execute(
            select(InAppNotification).where(
                InAppNotification.id == notification_id,
                InAppNotification.user_id == user_id,
            )
        )
        notif = r.scalars().first()
        if not notif:
            raise ValueError(ERR_IN_APP_NOT_FOUND)
        notif.read_status = READ_READ
        notif.read_at = utcnow()
        await db.commit()
        return notif

    async def mark_all_read(self, db: AsyncSession, user_id: uuid.UUID) -> int:
        r = await db.execute(
            select(InAppNotification).where(
                InAppNotification.user_id == user_id,
                InAppNotification.read_status == READ_UNREAD,
            )
        )
        items = r.scalars().all()
        now = utcnow()
        for n in items:
            n.read_status = READ_READ
            n.read_at = now
        await db.commit()
        return len(items)

    # ── Notification preferences ──────────────────────────────────────────────

    async def get_preferences(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
    ) -> list[NotificationPreference]:
        r = await db.execute(
            select(NotificationPreference).where(NotificationPreference.user_id == user_id)
        )
        return r.scalars().all()

    async def update_preference(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        tenant_id: uuid.UUID | None,
        event_key: str,
        channel: str,
        is_enabled: bool,
    ) -> NotificationPreference:
        r = await db.execute(
            select(NotificationPreference).where(
                NotificationPreference.user_id == user_id,
                NotificationPreference.event_key == event_key,
                NotificationPreference.channel == channel,
            )
        )
        pref = r.scalars().first()
        if pref:
            pref.is_enabled = is_enabled
        else:
            pref = NotificationPreference(
                user_id=user_id, tenant_id=tenant_id,
                event_key=event_key, channel=channel, is_enabled=is_enabled,
            )
            db.add(pref)
        await db.commit()
        return pref

    # ── Templates ─────────────────────────────────────────────────────────────

    async def list_templates(self, db: AsyncSession, channel: str | None = None) -> list[dict]:
        q = select(NotifEventTemplate)
        if channel:
            q = q.where(NotifEventTemplate.channel == channel)
        r = await db.execute(q.order_by(NotifEventTemplate.template_key))
        return [t.to_dict() for t in r.scalars().all()]

    async def create_template(self, db: AsyncSession, data: dict) -> NotifEventTemplate:
        tmpl = NotifEventTemplate(**{k: v for k, v in data.items() if hasattr(NotifEventTemplate, k)})
        db.add(tmpl)
        await db.commit()
        return tmpl

    async def update_template(
        self, db: AsyncSession, template_id: uuid.UUID, data: dict,
    ) -> NotifEventTemplate:
        r = await db.execute(select(NotifEventTemplate).where(NotifEventTemplate.id == template_id))
        tmpl = r.scalars().first()
        if not tmpl:
            raise ValueError(ERR_NOTIF_TEMPLATE_NOT_FOUND)
        for k, v in data.items():
            if hasattr(tmpl, k) and k not in ("id", "created_at"):
                setattr(tmpl, k, v)
        await db.commit()
        return tmpl

    async def set_template_active(
        self, db: AsyncSession, template_id: uuid.UUID, is_active: bool,
    ) -> NotifEventTemplate:
        r = await db.execute(select(NotifEventTemplate).where(NotifEventTemplate.id == template_id))
        tmpl = r.scalars().first()
        if not tmpl:
            raise ValueError(ERR_NOTIF_TEMPLATE_NOT_FOUND)
        tmpl.is_active = is_active
        await db.commit()
        return tmpl

    # ── Private helpers ───────────────────────────────────────────────────────

    async def _dispatch_outbox(
        self,
        db: AsyncSession,
        outbox: NotificationOutbox,
        source_record_type: str | None,
        source_record_id: uuid.UUID | None,
    ) -> None:
        provider = CHANNEL_PROVIDERS.get(outbox.channel)
        if not provider:
            outbox.delivery_status = DELIVERY_FAILED
            outbox.failure_code = "UNKNOWN_CHANNEL"
            return

        if outbox.channel == CHANNEL_IN_APP:
            result = await provider.deliver(
                db=db,
                outbox_id=outbox.id,
                user_id=outbox.recipient_user_id,
                tenant_id=outbox.tenant_id,
                notification_type=outbox.template_key,
                title=outbox.title,
                body=outbox.body,
                action_url=outbox.action_url,
                action_label=outbox.action_label,
                source_record_type=source_record_type,
                source_record_id=source_record_id,
                severity=DELIVERY_PENDING,
            )
        else:
            result = await provider.deliver()

        outbox.delivery_status = result.status
        outbox.provider_name = result.provider_name
        outbox.provider_message_id = result.provider_message_id
        outbox.failure_code = result.failure_code
        outbox.failure_message = result.failure_message
        if result.success:
            outbox.sent_at = utcnow()

    async def _get_template(
        self, db: AsyncSession, template_key: str,
    ) -> NotifEventTemplate | None:
        r = await db.execute(
            select(NotifEventTemplate).where(
                NotifEventTemplate.template_key == template_key,
                NotifEventTemplate.is_active == True,
            )
        )
        return r.scalars().first()

    async def _check_preference(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        event_key: str,
        channel: str,
    ) -> bool:
        r = await db.execute(
            select(NotificationPreference).where(
                NotificationPreference.user_id == user_id,
                NotificationPreference.event_key == event_key,
                NotificationPreference.channel == channel,
            )
        )
        pref = r.scalars().first()
        if pref is None:
            return True  # default enabled
        return pref.is_enabled

    @staticmethod
    def _render(template: str | None, payload: dict) -> str:
        if not template:
            return ""
        result = template
        for k, v in payload.items():
            result = result.replace(f"{{{{{k}}}}}", str(v))
        # Remove unresolved placeholders safely (no XSS — this is server-side only)
        result = re.sub(r"\{\{[^}]+\}\}", "", result)
        return result.strip()
