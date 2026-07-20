"""Notification Engine — NotificationService."""
from __future__ import annotations
import hashlib, re, uuid
from datetime import datetime, timezone
import structlog
from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.engines.notification.constants import (
    NotifStatus, MAX_RETRY_ATTEMPTS, VALID_EVENT_TYPES, VALID_CHANNELS,
    VALID_AUDIENCES, VALID_APP_SCOPES, VALID_SCOPE_TYPES, VALID_STATUSES,
    VALID_LANGUAGES, DEFAULT_LANGUAGE, EVENT_VARIABLES, COMMON_VARIABLES,
    CUSTOMER_FORBIDDEN_VARIABLES,
)
from app.engines.notification.models import (
    NotificationTemplate, NotificationRecord, NotificationChannelConfig,
    NotificationTemplateVersion, NotificationTestSend, NotificationTemplateAuditLog,
)
from app.exceptions import ServiceOSException, NotFoundException
from app.redis_client import get_redis
from app.schemas.base import encode_cursor, decode_cursor

logger = structlog.get_logger("notification.service")
utcnow = lambda: datetime.now(timezone.utc)


class NotificationService:
    def __init__(self, db: AsyncSession, request_id: str = "—",
                 actor_id: uuid.UUID | None = None, actor_role: str | None = None,
                 actor_tenant_id: uuid.UUID | None = None):
        self.db = db; self.redis = get_redis()
        self.request_id = request_id; self.actor_id = actor_id; self.actor_role = actor_role
        self.actor_tenant_id = actor_tenant_id

    def _require_trusted_tenant(self, requested_tenant_id: uuid.UUID) -> uuid.UUID:
        """Slice 2F-36: set_channel_config accepted a client-supplied
        tenant_id path param with no comparison to the caller's own
        tenant. super_admin is exempt (platform-wide)."""
        if self.actor_role == "super_admin":
            return requested_tenant_id
        if self.actor_tenant_id is None:
            raise ServiceOSException(
                "PERMISSION_DENIED", "No tenant context.",
                blocking_rule="notification_mutation_requires_trusted_tenant_context")
        if requested_tenant_id != self.actor_tenant_id:
            raise ServiceOSException(
                "PERMISSION_DENIED", "You do not have access to this tenant's notification settings.",
                blocking_rule="notification_mutation_cross_tenant_denied")
        return self.actor_tenant_id

    def _rec_dict(self, n: NotificationRecord) -> dict:
        return {"notification_id": str(n.id), "tenant_id": str(n.tenant_id),
                "recipient_id": str(n.recipient_id), "notif_type": n.notif_type,
                "channel": n.channel, "title": n.title, "status": n.status,
                "attempt_count": n.attempt_count, "reference_id": n.reference_id,
                "delivered_at": n.delivered_at.isoformat() if n.delivered_at else None,
                "failed_reason": n.failed_reason, "created_at": n.created_at.isoformat()}

    # ── Send (core method) ────────────────────────────────────────────────────
    async def send(self, tenant_id: uuid.UUID, recipient_id: uuid.UUID,
                   recipient_type: str, notif_type: str, channel: str,
                   data: dict, reference_id: str | None,
                   reference_type: str | None, idempotency_key: str | None) -> dict:
        # Idempotency
        if idempotency_key:
            ex = await self.db.execute(select(NotificationRecord).where(
                NotificationRecord.idempotency_key == idempotency_key))
            existing = ex.scalar_one_or_none()
            if existing:
                return {**self._rec_dict(existing), "idempotent": True}

        # Resolve template
        tmpl = await self._resolve_template(tenant_id, notif_type, channel)
        if not tmpl:
            raise ServiceOSException("NOT_FOUND",
                f"No active template for {notif_type}/{channel}.")

        # Interpolate body
        body = tmpl.body
        title = tmpl.title or ""
        for k, v in data.items():
            body = body.replace(f"{{{{{k}}}}}", str(v))
            title = title.replace(f"{{{{{k}}}}}", str(v))

        rec = NotificationRecord(
            tenant_id=tenant_id, recipient_id=recipient_id,
            recipient_type=recipient_type, notif_type=notif_type,
            channel=channel, title=title, body=body, data=data,
            status=NotifStatus.QUEUED, idempotency_key=idempotency_key,
            reference_id=reference_id, reference_type=reference_type,
            template_id=tmpl.id,
        )
        self.db.add(rec); await self.db.flush()

        # Dispatch via per-channel handler
        try:
            from app.engines.notification.dispatchers import dispatch
            await dispatch(channel, rec)
        except Exception as e:
            logger.warning("notification.dispatch_failed", error=str(e))
        rec.status = NotifStatus.SENT
        rec.attempt_count = 1
        rec.last_attempt_at = utcnow()

        logger.info("notification.sent", tenant_id=str(tenant_id),
                    type=notif_type, channel=channel)
        return {**self._rec_dict(rec), "idempotent": False}

    async def _resolve_template(self, tenant_id: uuid.UUID, notif_type: str, channel: str):
        # Tenant-specific first
        r = await self.db.execute(select(NotificationTemplate).where(
            NotificationTemplate.tenant_id == tenant_id,
            NotificationTemplate.notif_type == notif_type,
            NotificationTemplate.channel == channel,
            NotificationTemplate.is_active == True))
        t = r.scalar_one_or_none()
        if t: return t
        # Platform default
        r2 = await self.db.execute(select(NotificationTemplate).where(
            NotificationTemplate.tenant_id == None,
            NotificationTemplate.notif_type == notif_type,
            NotificationTemplate.channel == channel,
            NotificationTemplate.is_active == True))
        return r2.scalar_one_or_none()

    async def get_status(self, notification_id: uuid.UUID) -> dict:
        r = await self.db.execute(select(NotificationRecord).where(
            NotificationRecord.id == notification_id))
        n = r.scalar_one_or_none()
        if not n: raise NotFoundException("Notification", str(notification_id))
        return self._rec_dict(n)

    async def list_notifications(self, tenant_id: uuid.UUID, status: str | None,
                                  limit: int, cursor: str | None) -> dict:
        q = select(NotificationRecord).where(
            NotificationRecord.tenant_id == tenant_id
        ).order_by(NotificationRecord.created_at.desc())
        if status: q = q.where(NotificationRecord.status == status)
        if cursor:
            try:
                c = decode_cursor(cursor)
                q = q.where(NotificationRecord.created_at < datetime.fromisoformat(c["created_at"]))
            except Exception: pass
        q = q.limit(limit + 1)
        r = await self.db.execute(q)
        items = r.scalars().all()
        has_next = len(items) > limit; items = items[:limit]
        nc = encode_cursor({"created_at": items[-1].created_at.isoformat()}) if has_next and items else None
        return {"notifications": [self._rec_dict(n) for n in items],
                "has_next": has_next, "next_cursor": nc}

    async def retry_failed(self, notification_id: uuid.UUID) -> dict:
        r = await self.db.execute(select(NotificationRecord).where(
            NotificationRecord.id == notification_id))
        n = r.scalar_one_or_none()
        if not n: raise NotFoundException("Notification", str(notification_id))
        if n.status not in (NotifStatus.FAILED, NotifStatus.BOUNCED):
            raise ServiceOSException("CONFLICT", f"Cannot retry a {n.status} notification.")
        if n.attempt_count >= MAX_RETRY_ATTEMPTS:
            raise ServiceOSException("CONFLICT",
                f"Max retry attempts ({MAX_RETRY_ATTEMPTS}) reached.")
        n.status = NotifStatus.QUEUED
        n.attempt_count += 1
        n.last_attempt_at = utcnow()
        return self._rec_dict(n)

    # ── Templates (4 methods) ─────────────────────────────────────────────────
    async def list_templates(self, tenant_id: uuid.UUID | None) -> dict:
        q = select(NotificationTemplate)
        if tenant_id: q = q.where(NotificationTemplate.tenant_id == tenant_id)
        else: q = q.where(NotificationTemplate.tenant_id == None)
        r = await self.db.execute(q.order_by(NotificationTemplate.notif_type))
        items = r.scalars().all()
        return {"templates": [{"template_id": str(t.id), "notif_type": t.notif_type,
                "channel": t.channel, "title": t.title, "is_active": t.is_active,
                "variables": t.variables} for t in items]}

    async def create_template(self, tenant_id: uuid.UUID | None, data: dict) -> dict:
        t = NotificationTemplate(tenant_id=tenant_id, notif_type=data["notif_type"],
            channel=data["channel"], title=data.get("title"), body=data["body"],
            variables=data.get("variables",[]), vertical=data.get("vertical"))
        self.db.add(t); await self.db.flush()
        return {"template_id": str(t.id), "notif_type": t.notif_type, "channel": t.channel}

    async def update_template(self, template_id: uuid.UUID, data: dict) -> dict:
        r = await self.db.execute(select(NotificationTemplate).where(
            NotificationTemplate.id == template_id))
        t = r.scalar_one_or_none()
        if not t: raise NotFoundException("Template", str(template_id))
        for f in ("title","body","variables","is_active"):
            if f in data and data[f] is not None: setattr(t, f, data[f])
        return {"template_id": str(t.id), "updated": True}

    async def delete_template(self, template_id: uuid.UUID) -> dict:
        r = await self.db.execute(select(NotificationTemplate).where(
            NotificationTemplate.id == template_id))
        t = r.scalar_one_or_none()
        if not t: raise NotFoundException("Template", str(template_id))
        t.is_active = False
        return {"template_id": str(template_id), "deactivated": True}

    # ── Channel config (3 methods) ────────────────────────────────────────────
    async def list_channels(self, tenant_id: uuid.UUID) -> dict:
        r = await self.db.execute(select(NotificationChannelConfig).where(
            NotificationChannelConfig.tenant_id == tenant_id))
        items = r.scalars().all()
        return {"channels": [{"channel": c.channel, "is_enabled": c.is_enabled,
                "verified_at": c.verified_at.isoformat() if c.verified_at else None}
               for c in items]}

    async def set_channel_config(self, tenant_id: uuid.UUID, channel: str,
                                  config: dict, is_enabled: bool) -> dict:
        tenant_id = self._require_trusted_tenant(tenant_id)
        r = await self.db.execute(select(NotificationChannelConfig).where(
            NotificationChannelConfig.tenant_id == tenant_id,
            NotificationChannelConfig.channel == channel))
        existing = r.scalar_one_or_none()
        if existing:
            existing.config = config; existing.is_enabled = is_enabled
        else:
            self.db.add(NotificationChannelConfig(tenant_id=tenant_id, channel=channel,
                config=config, is_enabled=is_enabled))
        return {"tenant_id": str(tenant_id), "channel": channel, "is_enabled": is_enabled}

    async def test_channel(self, tenant_id: uuid.UUID, channel: str) -> dict:
        return {"tenant_id": str(tenant_id), "channel": channel,
                "test_sent": True, "message": f"Test {channel} dispatched."}

    # ═══════════════════════════════════════════════════════════════════════
    # ENTERPRISE NOTIFICATION TEMPLATE CENTER (migration 102)
    # ═══════════════════════════════════════════════════════════════════════

    def _audit(self, action_type: str, template_id: uuid.UUID | None = None,
               old_value: dict | None = None, new_value: dict | None = None,
               reason: str | None = None) -> None:
        self.db.add(NotificationTemplateAuditLog(
            action_type=action_type, template_id=template_id,
            actor_user_id=self.actor_id, actor_role=self.actor_role,
            old_value_json=old_value, new_value_json=new_value,
            reason=reason, request_id=self.request_id,
        ))

    async def _get_template(self, template_id: uuid.UUID) -> NotificationTemplate:
        t = await self.db.get(NotificationTemplate, template_id)
        if not t:
            raise NotFoundException("Template", str(template_id))
        return t

    @staticmethod
    def _allowed_variables(event_type: str | None, audience: str | None) -> set[str]:
        allowed = set(COMMON_VARIABLES) | set(EVENT_VARIABLES.get(event_type or "", []))
        if audience == "customer":
            allowed -= CUSTOMER_FORBIDDEN_VARIABLES
        return allowed

    @staticmethod
    def _extract_variables(text: str | None) -> set[str]:
        if not text:
            return set()
        return set(re.findall(r"\{\{(\w+)\}\}", text))

    def validate_variables(self, event_type: str | None, audience: str | None,
                            *texts: str | None) -> dict:
        used = set()
        for t in texts:
            used |= self._extract_variables(t)
        allowed = self._allowed_variables(event_type, audience)
        unknown = used - allowed
        forbidden = used & CUSTOMER_FORBIDDEN_VARIABLES if audience == "customer" else set()
        return {
            "valid": not unknown and not forbidden,
            "used_variables": sorted(used),
            "allowed_variables": sorted(allowed),
            "unknown_variables": sorted(unknown),
            "forbidden_variables": sorted(forbidden),
        }

    # ── List / Summary ───────────────────────────────────────────────────────

    async def list_templates_admin(self, filters: dict) -> dict:
        q = select(NotificationTemplate)
        if filters.get("channel"):
            q = q.where(NotificationTemplate.channel == filters["channel"])
        if filters.get("event_type"):
            q = q.where(NotificationTemplate.event_type == filters["event_type"])
        if filters.get("audience"):
            q = q.where(NotificationTemplate.audience == filters["audience"])
        if filters.get("app_scope"):
            q = q.where(NotificationTemplate.app_scope == filters["app_scope"])
        if filters.get("scope_type"):
            q = q.where(NotificationTemplate.scope_type == filters["scope_type"])
        if filters.get("vertical_key"):
            q = q.where(NotificationTemplate.vertical == filters["vertical_key"])
        if filters.get("tenant_id"):
            q = q.where(NotificationTemplate.tenant_id == filters["tenant_id"])
        if filters.get("language"):
            q = q.where(NotificationTemplate.language == filters["language"])
        if filters.get("status"):
            q = q.where(NotificationTemplate.status == filters["status"])
        if filters.get("search"):
            s = f"%{filters['search']}%"
            q = q.where((NotificationTemplate.title.ilike(s)) |
                        (NotificationTemplate.body.ilike(s)) |
                        (NotificationTemplate.event_type.ilike(s)))
        q = q.order_by(NotificationTemplate.updated_at.desc().nullslast())
        rows = (await self.db.execute(q)).scalars().all()
        return {"items": [t.to_admin_dict() for t in rows], "total": len(rows)}

    async def get_summary(self) -> dict:
        rows = (await self.db.execute(select(NotificationTemplate))).scalars().all()
        total = len(rows)
        active = sum(1 for t in rows if t.status == "active")
        draft = sum(1 for t in rows if t.status == "draft")
        platform_defaults = sum(1 for t in rows if t.is_platform_default)
        tenant_overrides = sum(1 for t in rows if t.tenant_id is not None)
        validation_errors = sum(1 for t in rows if t.status == "validation_failed")
        return {
            "total_templates": total, "active_templates": active, "draft_templates": draft,
            "platform_defaults": platform_defaults, "tenant_overrides": tenant_overrides,
            "missing_translations": 0,  # only en/hi/pa scaffolding exists; real count is Phase 2
            "validation_errors": validation_errors, "failed_deliveries": 0,
        }

    # ── CRUD ──────────────────────────────────────────────────────────────────

    def _validate_scope_and_event(self, data: dict) -> None:
        if data.get("event_type") not in VALID_EVENT_TYPES:
            raise ServiceOSException("VALIDATION_ERROR", f"event_type must be one of {sorted(VALID_EVENT_TYPES)}")
        if data.get("channel") not in VALID_CHANNELS:
            raise ServiceOSException("VALIDATION_ERROR", f"channel must be one of {sorted(VALID_CHANNELS)}")
        if data.get("audience") not in VALID_AUDIENCES:
            raise ServiceOSException("VALIDATION_ERROR", f"audience must be one of {sorted(VALID_AUDIENCES)}")
        if data.get("app_scope") not in VALID_APP_SCOPES:
            raise ServiceOSException("VALIDATION_ERROR", f"app_scope must be one of {sorted(VALID_APP_SCOPES)}")
        scope_type = data.get("scope_type", "platform_default")
        if scope_type not in VALID_SCOPE_TYPES:
            raise ServiceOSException("VALIDATION_ERROR", f"scope_type must be one of {sorted(VALID_SCOPE_TYPES)}")
        if scope_type == "tenant" and not data.get("tenant_id"):
            raise ServiceOSException("VALIDATION_ERROR", "tenant_id is required when scope_type is 'tenant'.")
        if scope_type == "vertical" and not data.get("vertical_key"):
            raise ServiceOSException("VALIDATION_ERROR", "vertical_key is required when scope_type is 'vertical'.")
        lang = data.get("language", DEFAULT_LANGUAGE)
        if lang not in VALID_LANGUAGES:
            raise ServiceOSException("VALIDATION_ERROR", f"language must be one of {sorted(VALID_LANGUAGES)}")

    async def create_template_admin(self, data: dict) -> dict:
        self._validate_scope_and_event(data)
        validation = self.validate_variables(
            data.get("event_type"), data.get("audience"),
            data.get("title"), data.get("body"), data.get("subject"), data.get("html_body"))
        if not validation["valid"]:
            raise ServiceOSException("VALIDATION_ERROR",
                f"Unknown or forbidden variables: {validation['unknown_variables'] + validation['forbidden_variables']}")

        scope_type = data.get("scope_type", "platform_default")
        t = NotificationTemplate(
            tenant_id=data.get("tenant_id"), notif_type=data["event_type"], channel=data["channel"],
            title=data.get("title"), body=data.get("body", ""), variables=validation["used_variables"],
            is_active=(data.get("status", "draft") == "active"), vertical=data.get("vertical_key"),
            event_type=data["event_type"], audience=data["audience"], app_scope=data["app_scope"],
            scope_type=scope_type, category_id=data.get("category_id"),
            language=data.get("language", DEFAULT_LANGUAGE), status=data.get("status", "draft"),
            subject=data.get("subject"), html_body=data.get("html_body"),
            plain_text_body=data.get("plain_text_body"), action_label=data.get("action_label"),
            action_url=data.get("action_url"), priority=data.get("priority", "normal"),
            is_platform_default=(scope_type == "platform_default"), is_system=False,
            fallback_template_id=data.get("fallback_template_id"),
            created_by_user_id=self.actor_id, updated_by_user_id=self.actor_id,
        )
        self.db.add(t)
        await self.db.flush()
        self.db.add(NotificationTemplateVersion(
            template_id=t.id, version_number=1, snapshot_json=t.to_admin_dict(),
            changed_by_user_id=self.actor_id, change_reason="Initial creation.",
        ))
        self._audit("notification_template.created", template_id=t.id, new_value=t.to_admin_dict())
        await self.db.commit()
        return t.to_admin_dict()

    async def update_template_admin(self, template_id: uuid.UUID, data: dict, reason: str | None = None) -> dict:
        t = await self._get_template(template_id)
        old = t.to_admin_dict()

        editable = ("title", "body", "subject", "html_body", "plain_text_body", "action_label",
                    "action_url", "priority", "language")
        for f in editable:
            if f in data and data[f] is not None:
                setattr(t, f, data[f])
        if "variables" in data:
            t.variables = data["variables"]

        validation = self.validate_variables(t.event_type, t.audience, t.title, t.body, t.subject, t.html_body)
        if not validation["valid"]:
            raise ServiceOSException("VALIDATION_ERROR",
                f"Unknown or forbidden variables: {validation['unknown_variables'] + validation['forbidden_variables']}")

        t.updated_by_user_id = self.actor_id

        version_count = (await self.db.execute(
            select(func.count()).select_from(NotificationTemplateVersion)
            .where(NotificationTemplateVersion.template_id == t.id))).scalar() or 0
        self.db.add(NotificationTemplateVersion(
            template_id=t.id, version_number=version_count + 1, snapshot_json=t.to_admin_dict(),
            changed_by_user_id=self.actor_id, change_reason=reason or "Updated.",
        ))
        self._audit("notification_template.updated", template_id=t.id, old_value=old, new_value=t.to_admin_dict(), reason=reason)
        await self.db.commit()
        return t.to_admin_dict()

    async def activate_template(self, template_id: uuid.UUID) -> dict:
        t = await self._get_template(template_id)
        old = t.to_admin_dict()
        t.status = "active"
        t.is_active = True
        self._audit("notification_template.activated", template_id=t.id, old_value=old, new_value=t.to_admin_dict())
        await self.db.commit()
        return t.to_admin_dict()

    async def deactivate_template(self, template_id: uuid.UUID) -> dict:
        t = await self._get_template(template_id)
        old = t.to_admin_dict()
        t.status = "inactive"
        t.is_active = False
        self._audit("notification_template.deactivated", template_id=t.id, old_value=old, new_value=t.to_admin_dict())
        await self.db.commit()
        return t.to_admin_dict()

    async def archive_template(self, template_id: uuid.UUID) -> dict:
        t = await self._get_template(template_id)
        old = t.to_admin_dict()
        t.status = "archived"
        t.is_active = False
        t.archived_at = utcnow()
        self._audit("notification_template.archived", template_id=t.id, old_value=old, new_value=t.to_admin_dict())
        await self.db.commit()
        return t.to_admin_dict()

    async def delete_template_admin(self, template_id: uuid.UUID) -> dict:
        t = await self._get_template(template_id)
        if t.is_platform_default:
            raise ServiceOSException("PERMISSION_DENIED", "Platform default templates cannot be deleted directly. Archive or clone/override instead.")
        if t.status == "active":
            raise ServiceOSException("CONFLICT", "Active templates cannot be deleted. Deactivate first.")
        old = t.to_admin_dict()
        await self.db.delete(t)
        self._audit("notification_template.deleted", template_id=template_id, old_value=old)
        await self.db.commit()
        return {"template_id": str(template_id), "deleted": True}

    async def clone_template(self, template_id: uuid.UUID) -> dict:
        src = await self._get_template(template_id)
        clone = NotificationTemplate(
            tenant_id=None, notif_type=src.event_type, channel=src.channel,
            title=f"{src.title} (Copy)" if src.title else None, body=src.body, variables=src.variables,
            is_active=False, vertical=src.vertical,
            event_type=src.event_type, audience=src.audience, app_scope=src.app_scope,
            scope_type="platform_default", category_id=src.category_id, language=src.language,
            status="draft", subject=src.subject, html_body=src.html_body,
            plain_text_body=src.plain_text_body, action_label=src.action_label,
            action_url=src.action_url, priority=src.priority,
            is_platform_default=False, is_system=False, fallback_template_id=src.id,
            created_by_user_id=self.actor_id, updated_by_user_id=self.actor_id,
        )
        self.db.add(clone)
        await self.db.flush()
        self.db.add(NotificationTemplateVersion(
            template_id=clone.id, version_number=1, snapshot_json=clone.to_admin_dict(),
            changed_by_user_id=self.actor_id, change_reason=f"Cloned from {src.id}.",
        ))
        self._audit("notification_template.cloned", template_id=clone.id, new_value=clone.to_admin_dict())
        await self.db.commit()
        return clone.to_admin_dict()

    async def create_override(self, template_id: uuid.UUID, scope_type: str,
                               tenant_id: uuid.UUID | None = None, vertical_key: str | None = None) -> dict:
        src = await self._get_template(template_id)
        if scope_type == "tenant" and not tenant_id:
            raise ServiceOSException("VALIDATION_ERROR", "tenant_id is required for a tenant override.")
        if scope_type == "vertical" and not vertical_key:
            raise ServiceOSException("VALIDATION_ERROR", "vertical_key is required for a vertical override.")
        override = NotificationTemplate(
            tenant_id=tenant_id, notif_type=src.event_type, channel=src.channel,
            title=src.title, body=src.body, variables=src.variables,
            is_active=False, vertical=vertical_key,
            event_type=src.event_type, audience=src.audience, app_scope=src.app_scope,
            scope_type=scope_type, category_id=src.category_id, language=src.language,
            status="draft", subject=src.subject, html_body=src.html_body,
            plain_text_body=src.plain_text_body, action_label=src.action_label,
            action_url=src.action_url, priority=src.priority,
            is_platform_default=False, is_system=False, fallback_template_id=src.id,
            created_by_user_id=self.actor_id, updated_by_user_id=self.actor_id,
        )
        self.db.add(override)
        await self.db.flush()
        self._audit("notification_template.override_created", template_id=override.id, new_value=override.to_admin_dict())
        await self.db.commit()
        return override.to_admin_dict()

    async def resolve_effective_template(self, event_type: str, channel: str, audience: str,
                                          tenant_id: uuid.UUID | None = None,
                                          vertical_key: str | None = None) -> dict:
        path = []
        if tenant_id:
            r = await self.db.execute(select(NotificationTemplate).where(
                NotificationTemplate.event_type == event_type, NotificationTemplate.channel == channel,
                NotificationTemplate.audience == audience, NotificationTemplate.tenant_id == tenant_id,
                NotificationTemplate.status == "active"))
            t = r.scalar_one_or_none()
            path.append({"scope": "tenant", "matched": bool(t)})
            if t:
                return {"effective_template": t.to_admin_dict(), "resolution_path": path}
        if vertical_key:
            r = await self.db.execute(select(NotificationTemplate).where(
                NotificationTemplate.event_type == event_type, NotificationTemplate.channel == channel,
                NotificationTemplate.audience == audience, NotificationTemplate.vertical == vertical_key,
                NotificationTemplate.tenant_id.is_(None), NotificationTemplate.status == "active"))
            t = r.scalar_one_or_none()
            path.append({"scope": "vertical", "matched": bool(t)})
            if t:
                return {"effective_template": t.to_admin_dict(), "resolution_path": path}
        r = await self.db.execute(select(NotificationTemplate).where(
            NotificationTemplate.event_type == event_type, NotificationTemplate.channel == channel,
            NotificationTemplate.audience == audience, NotificationTemplate.is_platform_default == True,  # noqa: E712
            NotificationTemplate.status == "active"))
        t = r.scalar_one_or_none()
        path.append({"scope": "platform_default", "matched": bool(t)})
        return {"effective_template": t.to_admin_dict() if t else None, "resolution_path": path}

    # ── Preview / Test Send ──────────────────────────────────────────────────

    @staticmethod
    def _render(text: str | None, data: dict) -> tuple[str, list[str]]:
        if not text:
            return "", []
        missing = []
        def _sub(m):
            key = m.group(1)
            if key not in data:
                missing.append(key)
                return m.group(0)
            return str(data[key])
        rendered = re.sub(r"\{\{(\w+)\}\}", _sub, text)
        return rendered, missing

    async def render_preview(self, template_id: uuid.UUID, sample_data: dict) -> dict:
        t = await self._get_template(template_id)
        title, missing_title = self._render(t.title, sample_data)
        body, missing_body = self._render(t.body, sample_data)
        subject, missing_subject = self._render(t.subject, sample_data)
        missing = sorted(set(missing_title) | set(missing_body) | set(missing_subject))
        self._audit("notification_template.previewed", template_id=t.id, new_value={"sample_data": sample_data})
        await self.db.commit()
        return {
            "rendered_title": title, "rendered_body": body, "rendered_subject": subject,
            "channel": t.channel, "variable_values_used": sample_data, "missing_variables": missing,
            "warnings": [f"Missing value for {{{{{m}}}}} — fallback text left as-is." for m in missing],
        }

    async def test_send(self, template_id: uuid.UUID, recipient: str, sample_data: dict) -> dict:
        t = await self._get_template(template_id)
        title, _ = self._render(t.title, sample_data)
        body, _ = self._render(t.body, sample_data)
        ts = NotificationTestSend(
            template_id=t.id, recipient=recipient, sample_payload_json=sample_data,
            rendered_title=title, rendered_body=body, sent_by_user_id=self.actor_id,
        )
        self.db.add(ts)
        await self.db.flush()
        self._audit("notification_template.test_sent", template_id=t.id,
                    new_value={"recipient": recipient, "rendered_title": title})
        await self.db.commit()
        return {**ts.to_dict(), "is_test": True, "message": "Test notification sent (not a real workflow trigger)."}

    # ── Versions ──────────────────────────────────────────────────────────────

    async def list_versions(self, template_id: uuid.UUID) -> dict:
        rows = (await self.db.execute(
            select(NotificationTemplateVersion).where(NotificationTemplateVersion.template_id == template_id)
            .order_by(NotificationTemplateVersion.version_number.desc()))).scalars().all()
        return {"items": [v.to_dict() for v in rows]}

    async def rollback_template(self, template_id: uuid.UUID, version_number: int, reason: str) -> dict:
        if not reason or not reason.strip():
            raise ServiceOSException("VALIDATION_ERROR", "reason is required to roll back a template.")
        t = await self._get_template(template_id)
        v = (await self.db.execute(
            select(NotificationTemplateVersion).where(
                NotificationTemplateVersion.template_id == template_id,
                NotificationTemplateVersion.version_number == version_number))).scalar_one_or_none()
        if not v:
            raise NotFoundException("Template version", f"{template_id}/{version_number}")
        snap = v.snapshot_json
        old = t.to_admin_dict()
        for f in ("title", "body", "subject", "html_body", "plain_text_body", "action_label",
                  "action_url", "priority", "variables"):
            if f in snap:
                setattr(t, f, snap[f])
        t.updated_by_user_id = self.actor_id

        version_count = (await self.db.execute(
            select(func.count()).select_from(NotificationTemplateVersion)
            .where(NotificationTemplateVersion.template_id == t.id))).scalar() or 0
        self.db.add(NotificationTemplateVersion(
            template_id=t.id, version_number=version_count + 1, snapshot_json=t.to_admin_dict(),
            changed_by_user_id=self.actor_id, change_reason=f"Rollback to v{version_number}: {reason}",
        ))
        self._audit("notification_template.rollback", template_id=t.id, old_value=old,
                    new_value=t.to_admin_dict(), reason=reason)
        await self.db.commit()
        return t.to_admin_dict()

    # ── Delivery Analytics ────────────────────────────────────────────────────

    async def delivery_analytics(self, template_id: uuid.UUID) -> dict:
        rows = (await self.db.execute(
            select(NotificationRecord).where(NotificationRecord.template_id == template_id))).scalars().all()
        sent = len(rows)
        delivered = sum(1 for r in rows if r.status in ("sent", "delivered"))
        failed = sum(1 for r in rows if r.status in ("failed", "bounced"))
        last_failure = next((r.failed_reason for r in reversed(rows) if r.failed_reason), None)
        return {
            "sent": sent, "delivered": delivered, "opened": 0, "clicked": 0, "failed": failed,
            "delivery_rate": round(delivered / sent * 100, 1) if sent else 0.0,
            "failure_rate": round(failed / sent * 100, 1) if sent else 0.0,
            "average_send_time_ms": None, "last_failure_reason": last_failure,
        }

    async def list_audit_logs(self, template_id: uuid.UUID | None = None, limit: int = 100) -> dict:
        q = select(NotificationTemplateAuditLog).order_by(NotificationTemplateAuditLog.created_at.desc()).limit(limit)
        if template_id:
            q = q.where(NotificationTemplateAuditLog.template_id == template_id)
        rows = (await self.db.execute(q)).scalars().all()
        return {"items": [a.to_dict() for a in rows]}

    # ── Seed Defaults ─────────────────────────────────────────────────────────

    async def seed_defaults_preview(self) -> dict:
        from app.engines.notification.seed_data import DEFAULT_TEMPLATE_SPECS
        return {"templates_to_create": len(DEFAULT_TEMPLATE_SPECS) * 3}  # 3 channels each

    async def seed_defaults(self) -> dict:
        from app.engines.notification.seed_data import DEFAULT_TEMPLATE_SPECS
        created = 0
        for spec in DEFAULT_TEMPLATE_SPECS:
            for channel in ("in_app", "email", "push"):
                existing = (await self.db.execute(select(NotificationTemplate).where(
                    NotificationTemplate.event_type == spec["event_type"],
                    NotificationTemplate.channel == channel,
                    NotificationTemplate.audience == spec["audience"],
                    NotificationTemplate.tenant_id.is_(None),
                    NotificationTemplate.is_platform_default == True,  # noqa: E712
                ))).scalars().first()
                if existing:
                    continue
                t = NotificationTemplate(
                    tenant_id=None, notif_type=spec["event_type"], channel=channel,
                    title=spec["title"], body=spec["body"], variables=spec.get("variables", []),
                    is_active=True, vertical=None,
                    event_type=spec["event_type"], audience=spec["audience"], app_scope=spec["app_scope"],
                    scope_type="platform_default", language=DEFAULT_LANGUAGE, status="active",
                    subject=spec.get("subject", spec["title"]) if channel == "email" else None,
                    priority="normal", is_platform_default=True, is_system=True,
                    created_by_user_id=self.actor_id, updated_by_user_id=self.actor_id,
                )
                self.db.add(t)
                await self.db.flush()
                self.db.add(NotificationTemplateVersion(
                    template_id=t.id, version_number=1, snapshot_json=t.to_admin_dict(),
                    changed_by_user_id=self.actor_id, change_reason="Seeded default.",
                ))
                created += 1
        self._audit("notification_template.seed_defaults", new_value={"created": created})
        await self.db.commit()
        return {"created": created}
