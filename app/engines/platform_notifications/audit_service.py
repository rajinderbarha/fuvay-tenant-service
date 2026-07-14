"""Sprint 27 — Platform Audit Log Service.

Wraps the existing platform_audit_logs table (from security engine).
Append-only. Sensitive fields redacted. Admin-only access.
"""
from __future__ import annotations
import uuid
from datetime import datetime, timezone

import structlog
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.platform_notifications.constants import (
    SENSITIVE_FIELDS,
    ERR_AUDIT_LOG_NOT_FOUND, ERR_AUDIT_LOG_ACCESS_DENIED,
)
from app.engines.security.models import PlatformAuditLog

log = structlog.get_logger("platform_audit")
utcnow = lambda: datetime.now(timezone.utc)


class PlatformAuditLogService:

    async def write_audit_log(
        self,
        db: AsyncSession,
        action: str,
        resource_type: str,
        actor_type: str,
        actor_user_id: uuid.UUID | None = None,
        tenant_id: uuid.UUID | None = None,
        resource_id: uuid.UUID | None = None,
        engine_key: str | None = None,
        old_value: dict | None = None,
        new_value: dict | None = None,
        metadata: dict | None = None,
        ip_address: str | None = None,
        request_id: str | None = None,
        severity: str = "info",
    ) -> PlatformAuditLog:
        """Append-only audit log write. Never UPDATE or DELETE."""
        safe_before = self.redact_sensitive_fields(old_value) if old_value else None
        safe_after  = self.redact_sensitive_fields(new_value) if new_value else None

        entry = PlatformAuditLog(
            tenant_id=tenant_id,
            actor_id=actor_user_id,
            actor_role=actor_type,
            actor_ip=ip_address,
            operation=action,
            engine_id=engine_key or resource_type,
            entity_type=resource_type,
            entity_id=str(resource_id) if resource_id else None,
            before_state=safe_before,
            after_state=safe_after,
            request_id=request_id,
            is_high_risk=(severity == "critical"),
            meta=metadata or {},
        )
        db.add(entry)
        await db.flush()
        return entry

    async def write_from_domain_event(
        self,
        db: AsyncSession,
        event_key: str,
        resource_type: str,
        resource_id: uuid.UUID | None,
        actor_user_id: uuid.UUID | None,
        actor_type: str,
        tenant_id: uuid.UUID | None,
        payload: dict | None = None,
    ) -> PlatformAuditLog:
        """Write audit log from a notification/domain event."""
        return await self.write_audit_log(
            db=db,
            action=event_key,
            resource_type=resource_type,
            actor_type=actor_type,
            actor_user_id=actor_user_id,
            tenant_id=tenant_id,
            resource_id=resource_id,
            engine_key="platform_notifications",
            new_value=self.redact_sensitive_fields(payload or {}),
        )

    async def get_audit_logs(
        self,
        db: AsyncSession,
        actor_type: str,
        tenant_id: uuid.UUID | None = None,
        resource_type: str | None = None,
        action: str | None = None,
        engine_key: str | None = None,
        actor_user_id_filter: uuid.UUID | None = None,
        search: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> dict:
        # Provider can only see own tenant; customer cannot access audit
        q = select(PlatformAuditLog)
        if actor_type not in ("admin", "super_admin"):
            if tenant_id:
                q = q.where(PlatformAuditLog.tenant_id == tenant_id)
            else:
                raise ValueError(ERR_AUDIT_LOG_ACCESS_DENIED)

        if tenant_id and actor_type == "provider":
            q = q.where(PlatformAuditLog.tenant_id == tenant_id)
        if resource_type:
            q = q.where(PlatformAuditLog.entity_type == resource_type)
        if action:
            q = q.where(PlatformAuditLog.operation.ilike(f"%{action}%"))
        if engine_key:
            q = q.where(PlatformAuditLog.engine_id == engine_key)
        if actor_user_id_filter:
            q = q.where(PlatformAuditLog.actor_id == actor_user_id_filter)
        if search:
            q = q.where(
                or_(
                    PlatformAuditLog.operation.ilike(f"%{search}%"),
                    PlatformAuditLog.entity_type.ilike(f"%{search}%"),
                    PlatformAuditLog.entity_id.ilike(f"%{search}%"),
                )
            )

        total_r = await db.execute(select(func.count()).select_from(q.subquery()))
        total = total_r.scalar_one()
        r = await db.execute(q.order_by(PlatformAuditLog.created_at.desc()).limit(limit).offset(offset))
        items = r.scalars().all()
        return {
            "items": [self._to_dict(a) for a in items],
            "total": total, "limit": limit, "offset": offset,
        }

    async def get_record_timeline(
        self,
        db: AsyncSession,
        resource_type: str,
        resource_id: uuid.UUID,
        actor_type: str,
        tenant_id: uuid.UUID | None = None,
    ) -> list[dict]:
        q = select(PlatformAuditLog).where(
            PlatformAuditLog.entity_type == resource_type,
            PlatformAuditLog.entity_id == str(resource_id),
        )
        if actor_type == "provider" and tenant_id:
            q = q.where(PlatformAuditLog.tenant_id == tenant_id)
        elif actor_type not in ("admin", "super_admin", "provider"):
            raise ValueError(ERR_AUDIT_LOG_ACCESS_DENIED)

        r = await db.execute(q.order_by(PlatformAuditLog.created_at.asc()))
        return [self._to_dict(a) for a in r.scalars().all()]

    def sanitize_audit_payload(self, payload: dict) -> dict:
        return self.redact_sensitive_fields(payload)

    def redact_sensitive_fields(self, payload: dict | None) -> dict:
        if not payload:
            return {}
        result = {}
        for k, v in payload.items():
            if k.lower() in SENSITIVE_FIELDS or any(s in k.lower() for s in SENSITIVE_FIELDS):
                result[k] = "[REDACTED]"
            else:
                # MODULE-L5-11: recurse into lists too, not just dicts. Previously
                # a secret inside a list (e.g. {"users": [{"password": "x"}]}) was
                # stored RAW in the audit log — a data leak, since audit payloads
                # routinely carry arrays of records (bulk ops, multi-item events).
                result[k] = self._redact_value(v)
        return result

    def _redact_value(self, v):
        if isinstance(v, dict):
            return self.redact_sensitive_fields(v)
        if isinstance(v, list):
            return [self._redact_value(item) for item in v]
        return v

    def _to_dict(self, audit: PlatformAuditLog) -> dict:
        return {
            "id": str(audit.id),
            "actor_id": str(audit.actor_id) if audit.actor_id else None,
            "actor_role": audit.actor_role,
            "actor_ip": audit.actor_ip,
            "action": audit.operation,
            "engine_key": audit.engine_id,
            "resource_type": audit.entity_type,
            "resource_id": audit.entity_id,
            "tenant_id": str(audit.tenant_id) if audit.tenant_id else None,
            "old_value": audit.before_state,
            "new_value": audit.after_state,
            "is_high_risk": audit.is_high_risk,
            "request_id": audit.request_id,
            "created_at": audit.created_at.isoformat(),
        }
