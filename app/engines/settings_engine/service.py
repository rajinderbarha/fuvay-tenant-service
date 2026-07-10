"""Settings Engine — SettingsService. Resolution chain: TENANT → PLAN → PLATFORM → default."""
from __future__ import annotations
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.engines.settings_engine.constants import (
    SettingTier, PLATFORM_DEFAULTS, REDIS_SETTING, REDIS_PLATFORM_SETTING,
)
from app.engines.settings_engine.models import (
    PlatformSetting, PlanSetting, TenantSetting, SettingAuditLog, FeatureFlag,
)
from app.exceptions import ServiceOSException, NotFoundException
from app.redis_client import get_redis, cache_set, cache_get, cache_delete
from app.schemas.base import encode_cursor, decode_cursor

MASKED_VALUE = "••••••••"

# The one concrete cross-setting business rule from the P0 ticket: ServiceOS Home
# Services is a direct-payment model — tenant payouts cannot be turned on unless
# the platform is also configured to collect payment.
IMPACT_RULES = {
    "tenant_payouts_enabled": {
        "blocked_unless": {"key": "payment_collection_enabled", "equals": True},
        "message": "Cannot enable tenant_payouts_enabled while payment_collection_enabled=false. "
                   "ServiceOS Home Services uses a direct-payment model — customers pay providers "
                   "directly, so the platform does not collect payment or make payouts.",
    },
}

logger = structlog.get_logger("settings.service")
utcnow = lambda: datetime.now(timezone.utc)


class SettingsService:
    def __init__(self, db: AsyncSession, request_id: str = "—",
                 actor_id: uuid.UUID | None = None, actor_role: str | None = None):
        self.db = db
        self.redis = get_redis()
        self.request_id = request_id
        self.actor_id = actor_id
        self.actor_role = actor_role

    async def _audit(self, tier: str, key: str, old_value: Any,
                     new_value: Any, tenant_id: uuid.UUID | None = None, reason: str | None = None,
                     risk_level: str = "low", action_type: str = "updated"):
        self.db.add(SettingAuditLog(
            tenant_id=tenant_id, tier=tier, key=key,
            old_value={"v": old_value} if old_value is not None else None,
            new_value={"v": new_value}, changed_by=self.actor_id, reason=reason,
            request_id=self.request_id, risk_level=risk_level, action_type=action_type,
        ))
        if tier == "platform":
            from app.core.audit import record_platform_audit
            await record_platform_audit(
                self.db, operation="setting.changed", engine_id="settings",
                tenant_id=tenant_id, entity_type="setting", entity_id=key,
                actor_id=self.actor_id, actor_role=self.actor_role,
                request_id=self.request_id,
                before={"v": old_value} if old_value is not None else None,
                after={"v": new_value},
            )

    async def _invalidate(self, key: str, tenant_id: str | None = None):
        try:
            if tenant_id:
                await cache_delete(REDIS_SETTING.format(tenant_id=tenant_id, key=key))
            await cache_delete(REDIS_PLATFORM_SETTING.format(key=key))
        except Exception:
            pass

    def _unwrap(self, setting_obj) -> Any:
        if setting_obj and setting_obj.value:
            return setting_obj.value.get("v")
        return None

    # ── Core resolve method ────────────────────────────────────────────────────
    async def resolve(self, key: str, tenant_id: uuid.UUID | None = None,
                      plan_type: str | None = None) -> dict:
        """Resolve a setting through TENANT → PLAN → PLATFORM → code_default."""
        cache_key = REDIS_SETTING.format(tenant_id=str(tenant_id) if tenant_id else "none", key=key)
        try:
            cached = await self.redis.get(cache_key)
            if cached:
                import json
                return json.loads(cached)
        except Exception:
            pass

        source = "code_default"
        value = PLATFORM_DEFAULTS.get(key)

        # Platform level
        pr = await self.db.execute(select(PlatformSetting).where(PlatformSetting.key == key))
        plat = pr.scalar_one_or_none()
        if plat:
            value = self._unwrap(plat)
            source = SettingTier.PLATFORM

        # Plan level
        if plan_type:
            planr = await self.db.execute(select(PlanSetting).where(
                PlanSetting.plan_type == plan_type, PlanSetting.key == key))
            plan_s = planr.scalar_one_or_none()
            if plan_s:
                value = self._unwrap(plan_s)
                source = SettingTier.PLAN

        # Tenant level (highest priority)
        if tenant_id:
            tr = await self.db.execute(select(TenantSetting).where(
                TenantSetting.tenant_id == tenant_id, TenantSetting.key == key))
            tenant_s = tr.scalar_one_or_none()
            if tenant_s:
                value = self._unwrap(tenant_s)
                source = SettingTier.TENANT

        result = {"key": key, "value": value, "source": source,
                  "tenant_id": str(tenant_id) if tenant_id else None,
                  "plan_type": plan_type}
        try:
            import json
            await self.redis.setex(cache_key, 300, json.dumps(result))
        except Exception:
            pass
        return result

    # ── Platform settings (5 methods) ─────────────────────────────────────────
    def _setting_to_dict(self, s: PlatformSetting) -> dict:
        value = MASKED_VALUE if s.is_secret else self._unwrap(s)
        return {
            "key": s.key, "label": s.label or s.key, "value": value,
            "type": s.setting_type, "description": s.description, "is_public": s.is_public,
            "category": s.category, "allowed_values": s.allowed_values_json,
            "is_secret": s.is_secret, "risk_level": s.risk_level,
            "requires_approval": s.requires_approval, "requires_restart": s.requires_restart,
            "is_runtime_editable": s.is_runtime_editable, "owner_module": s.owner_module,
            "status": s.status,
            "updated_at": s.updated_at.isoformat() if s.updated_at else None,
        }

    async def list_platform_settings(self, limit: int, cursor: str | None,
                                      category: str | None = None,
                                      is_secret: bool | None = None,
                                      status: str | None = None) -> dict:
        q = select(PlatformSetting).order_by(PlatformSetting.key)
        if category: q = q.where(PlatformSetting.category == category)
        if is_secret is not None: q = q.where(PlatformSetting.is_secret == is_secret)
        if status: q = q.where(PlatformSetting.status == status)
        if cursor:
            try:
                c = decode_cursor(cursor)
                q = q.where(PlatformSetting.key > c["key"])
            except Exception:
                pass
        q = q.limit(limit + 1)
        r = await self.db.execute(q)
        items = r.scalars().all()
        has_next = len(items) > limit; items = items[:limit]
        nc = encode_cursor({"key": items[-1].key}) if has_next and items else None
        return {"settings": [self._setting_to_dict(s) for s in items],
                "has_next": has_next, "next_cursor": nc}

    async def get_platform_setting(self, key: str) -> dict:
        r = await self.db.execute(select(PlatformSetting).where(PlatformSetting.key == key))
        s = r.scalar_one_or_none()
        if not s:
            default = PLATFORM_DEFAULTS.get(key)
            if default is None:
                raise NotFoundException("PlatformSetting", key)
            return {"key": key, "value": default, "source": "code_default"}
        return self._setting_to_dict(s)

    def _validate_value_type(self, value: Any, setting_type: str,
                              allowed_values: list | None = None) -> None:
        if setting_type == "boolean" and not isinstance(value, bool):
            raise ServiceOSException("VALIDATION_ERROR",
                f"Setting value must be a boolean, got {type(value).__name__}: {value!r}")
        if setting_type in ("number", "currency", "percentage", "duration") and (
                isinstance(value, bool) or not isinstance(value, (int, float))):
            raise ServiceOSException("VALIDATION_ERROR",
                f"Setting value must be a number, got {type(value).__name__}: {value!r}")
        if setting_type == "list" and not isinstance(value, list):
            raise ServiceOSException("VALIDATION_ERROR",
                f"Setting value must be a list, got {type(value).__name__}: {value!r}")
        if setting_type in ("string", "secret") and not isinstance(value, str):
            raise ServiceOSException("VALIDATION_ERROR",
                f"Setting value must be a string, got {type(value).__name__}: {value!r}")
        if setting_type == "enum" and allowed_values and value not in allowed_values:
            raise ServiceOSException("VALIDATION_ERROR",
                f"Setting value {value!r} is not one of the allowed values: {allowed_values}")

    async def set_platform_setting(self, key: str, value: Any, setting_type: str | None = None,
                                    description: str | None = None,
                                    label: str | None = None, category: str | None = None,
                                    is_secret: bool | None = None, risk_level: str | None = None,
                                    requires_approval: bool | None = None,
                                    requires_restart: bool | None = None,
                                    is_runtime_editable: bool | None = None,
                                    owner_module: str | None = None,
                                    allowed_values: list | None = None,
                                    reason: str | None = None) -> dict:
        r = await self.db.execute(select(PlatformSetting).where(PlatformSetting.key == key))
        existing = r.scalar_one_or_none()
        old_value = self._unwrap(existing) if existing else None

        if existing and existing.risk_level == "critical" and not reason:
            raise ServiceOSException("VALIDATION_ERROR",
                "A reason is required to change a critical-risk setting.")

        effective_type = setting_type or (existing.setting_type if existing else "string")
        effective_allowed = allowed_values if allowed_values is not None else (
            existing.allowed_values_json if existing else None)
        self._validate_value_type(value, effective_type, effective_allowed)

        if existing:
            existing.value = {"v": value}
            existing.setting_type = effective_type
            if description is not None: existing.description = description
            if label is not None: existing.label = label
            if category is not None: existing.category = category
            if is_secret is not None: existing.is_secret = is_secret
            if risk_level is not None: existing.risk_level = risk_level
            if requires_approval is not None: existing.requires_approval = requires_approval
            if requires_restart is not None: existing.requires_restart = requires_restart
            if is_runtime_editable is not None: existing.is_runtime_editable = is_runtime_editable
            if owner_module is not None: existing.owner_module = owner_module
            if allowed_values is not None: existing.allowed_values_json = allowed_values
        else:
            self.db.add(PlatformSetting(
                key=key, value={"v": value}, setting_type=effective_type,
                description=description, set_by=self.actor_id,
                label=label, category=category or "general_platform",
                is_secret=is_secret or False, risk_level=risk_level or "low",
                requires_approval=requires_approval or False,
                requires_restart=requires_restart or False,
                is_runtime_editable=True if is_runtime_editable is None else is_runtime_editable,
                owner_module=owner_module, allowed_values_json=allowed_values,
            ))
        effective_is_secret = is_secret if is_secret is not None else (existing.is_secret if existing else False)
        audit_old = MASKED_VALUE if effective_is_secret and old_value is not None else old_value
        audit_new = MASKED_VALUE if effective_is_secret else value
        await self._audit(SettingTier.PLATFORM, key, audit_old, audit_new, reason=reason,
                           risk_level=risk_level or (existing.risk_level if existing else "low"))
        await self._invalidate(key)
        response_value = MASKED_VALUE if effective_is_secret else value
        return {"key": key, "value": response_value, "tier": SettingTier.PLATFORM}

    async def delete_platform_setting(self, key: str) -> dict:
        r = await self.db.execute(select(PlatformSetting).where(PlatformSetting.key == key))
        s = r.scalar_one_or_none()
        if not s: raise NotFoundException("PlatformSetting", key)
        await self.db.delete(s)
        await self._invalidate(key)
        return {"key": key, "deleted": True, "note": "Platform default restored."}

    async def bulk_set_platform(self, settings: list[dict]) -> dict:
        results = []
        for item in settings:
            try:
                await self.set_platform_setting(item["key"], item["value"],
                    item.get("type","string"), item.get("description"))
                results.append({"key": item["key"], "status": "set"})
            except Exception as e:
                results.append({"key": item["key"], "status": "failed", "error": str(e)})
        return {"results": results, "total": len(settings),
                "succeeded": sum(1 for r in results if r["status"] == "set")}

    # ── Plan settings (3 methods) ──────────────────────────────────────────────
    async def list_plan_settings(self, plan_type: str) -> dict:
        r = await self.db.execute(select(PlanSetting).where(
            PlanSetting.plan_type == plan_type).order_by(PlanSetting.key))
        items = r.scalars().all()
        return {"plan_type": plan_type,
                "settings": [{"key": s.key, "value": self._unwrap(s), "type": s.setting_type}
                             for s in items]}

    async def set_plan_setting(self, plan_type: str, key: str, value: Any, setting_type: str) -> dict:
        r = await self.db.execute(select(PlanSetting).where(
            PlanSetting.plan_type == plan_type, PlanSetting.key == key))
        existing = r.scalar_one_or_none()
        old = self._unwrap(existing) if existing else None
        if existing:
            existing.value = {"v": value}; existing.setting_type = setting_type
        else:
            self.db.add(PlanSetting(plan_type=plan_type, key=key, value={"v": value},
                setting_type=setting_type, set_by=self.actor_id))
        await self._audit(SettingTier.PLAN, key, old, value)
        await self._invalidate(key)
        return {"plan_type": plan_type, "key": key, "value": value}

    async def delete_plan_setting(self, plan_type: str, key: str) -> dict:
        r = await self.db.execute(select(PlanSetting).where(
            PlanSetting.plan_type == plan_type, PlanSetting.key == key))
        s = r.scalar_one_or_none()
        if not s: raise NotFoundException("PlanSetting", f"{plan_type}:{key}")
        await self.db.delete(s)
        await self._invalidate(key)
        return {"plan_type": plan_type, "key": key, "deleted": True}

    # ── Tenant settings (4 methods) ────────────────────────────────────────────
    async def list_tenant_settings(self, tenant_id: uuid.UUID) -> dict:
        r = await self.db.execute(select(TenantSetting).where(
            TenantSetting.tenant_id == tenant_id).order_by(TenantSetting.key))
        items = r.scalars().all()
        return {"tenant_id": str(tenant_id),
                "settings": [{"key": s.key, "value": self._unwrap(s), "type": s.setting_type,
                              "reason": s.reason} for s in items]}

    async def set_tenant_setting(self, tenant_id: uuid.UUID, key: str,
                                  value: Any, setting_type: str, reason: str | None,
                                  expires_at: datetime | None = None,
                                  requires_approval: bool = False) -> dict:
        if not reason:
            raise ServiceOSException("VALIDATION_ERROR", "A reason is required to create a tenant override.")
        r = await self.db.execute(select(TenantSetting).where(
            TenantSetting.tenant_id == tenant_id, TenantSetting.key == key))
        existing = r.scalar_one_or_none()
        old = self._unwrap(existing) if existing else None
        if existing:
            existing.value = {"v": value}; existing.reason = reason
            existing.expires_at = expires_at; existing.requires_approval = requires_approval
            existing.status = "active"
        else:
            self.db.add(TenantSetting(tenant_id=tenant_id, key=key, value={"v": value},
                setting_type=setting_type, set_by=self.actor_id, reason=reason,
                expires_at=expires_at, requires_approval=requires_approval))
        await self._audit(SettingTier.TENANT, key, old, value, tenant_id=tenant_id, reason=reason,
                           action_type="override_created")
        await self._invalidate(key, str(tenant_id))
        return {"tenant_id": str(tenant_id), "key": key, "value": value}

    async def delete_tenant_setting(self, tenant_id: uuid.UUID, key: str,
                                     reason: str | None = None) -> dict:
        r = await self.db.execute(select(TenantSetting).where(
            TenantSetting.tenant_id == tenant_id, TenantSetting.key == key))
        s = r.scalar_one_or_none()
        if not s: raise NotFoundException("TenantSetting", key)
        old = self._unwrap(s)
        await self.db.delete(s)
        await self._audit(SettingTier.TENANT, key, old, None, tenant_id=tenant_id, reason=reason,
                           action_type="override_revoked")
        await self._invalidate(key, str(tenant_id))
        return {"tenant_id": str(tenant_id), "key": key, "deleted": True,
                "note": "Reverted to plan/platform default."}

    async def list_all_tenant_overrides(self, limit: int = 100) -> dict:
        r = await self.db.execute(select(TenantSetting).order_by(TenantSetting.updated_at.desc()).limit(limit))
        items = r.scalars().all()
        return {"overrides": [{
            "id": str(o.id), "tenant_id": str(o.tenant_id), "key": o.key,
            "value": self._unwrap(o), "reason": o.reason,
            "expires_at": o.expires_at.isoformat() if o.expires_at else None,
            "requires_approval": o.requires_approval, "status": o.status,
            "created_at": o.created_at.isoformat() if o.created_at else None,
        } for o in items]}

    async def resolve_setting(self, key: str, tenant_id: uuid.UUID | None,
                               plan_type: str | None) -> dict:
        return await self.resolve(key, tenant_id, plan_type)

    # ── Audit log (1 method) ──────────────────────────────────────────────────
    async def get_audit_log(self, tenant_id: uuid.UUID | None, key: str | None,
                             limit: int, cursor: str | None) -> dict:
        q = select(SettingAuditLog).order_by(SettingAuditLog.created_at.desc())
        if tenant_id: q = q.where(SettingAuditLog.tenant_id == tenant_id)
        if key: q = q.where(SettingAuditLog.key == key)
        if cursor:
            try:
                c = decode_cursor(cursor)
                q = q.where(SettingAuditLog.created_at < datetime.fromisoformat(c["created_at"]))
            except Exception:
                pass
        q = q.limit(limit + 1)
        r = await self.db.execute(q)
        logs = r.scalars().all()
        has_next = len(logs) > limit; logs = logs[:limit]
        nc = encode_cursor({"created_at": logs[-1].created_at.isoformat()}) if has_next and logs else None
        return {"logs": [{"log_id": str(l.id), "tier": l.tier, "key": l.key,
                "old_value": l.old_value.get("v") if l.old_value else None,
                "new_value": l.new_value.get("v"), "reason": l.reason,
                "actor": str(l.changed_by) if l.changed_by else None,
                "request_id": l.request_id, "risk_level": l.risk_level,
                "action_type": l.action_type, "tenant_id": str(l.tenant_id) if l.tenant_id else None,
                "created_at": l.created_at.isoformat()} for l in logs],
                "has_next": has_next, "next_cursor": nc}

    # ── Version history / rollback ──────────────────────────────────────────
    async def get_setting_history(self, key: str, limit: int = 50) -> dict:
        r = await self.db.execute(select(SettingAuditLog).where(
            SettingAuditLog.key == key
        ).order_by(SettingAuditLog.created_at.desc()).limit(limit))
        logs = r.scalars().all()
        return {"key": key, "history": [{
            "log_id": str(l.id), "tier": l.tier,
            "old_value": l.old_value.get("v") if l.old_value else None,
            "new_value": l.new_value.get("v"), "changed_by": str(l.changed_by) if l.changed_by else None,
            "reason": l.reason, "request_id": l.request_id, "action_type": l.action_type,
            "rollback_available": l.tier == SettingTier.PLATFORM,
            "created_at": l.created_at.isoformat(),
        } for l in logs]}

    async def rollback_setting(self, log_id: uuid.UUID, reason: str) -> dict:
        if not reason:
            raise ServiceOSException("VALIDATION_ERROR", "A reason is required to roll back a setting.")
        r = await self.db.execute(select(SettingAuditLog).where(SettingAuditLog.id == log_id))
        log = r.scalar_one_or_none()
        if not log:
            raise NotFoundException("SettingAuditLog", str(log_id))
        if log.tier != SettingTier.PLATFORM:
            raise ServiceOSException("VALIDATION_ERROR", "Only platform-level settings support rollback.")
        old_value = log.old_value.get("v") if log.old_value else None
        pr = await self.db.execute(select(PlatformSetting).where(PlatformSetting.key == log.key))
        setting = pr.scalar_one_or_none()
        if not setting:
            raise NotFoundException("PlatformSetting", log.key)
        if setting.is_secret:
            raise ServiceOSException("VALIDATION_ERROR",
                "Secret settings cannot be rolled back automatically — audit history only stores "
                "a masked value for secrets. Set the new secret value directly instead.")
        current_value = self._unwrap(setting)
        setting.value = {"v": old_value}
        await self._audit(SettingTier.PLATFORM, log.key, current_value, old_value, reason=reason,
                           risk_level=setting.risk_level, action_type="rollback")
        await self._invalidate(log.key)
        return {"key": log.key, "rolled_back_to": old_value, "reason": reason}

    # ── Impact preview ───────────────────────────────────────────────────────
    async def check_impact(self, key: str, new_value: Any) -> dict:
        warnings: list[str] = []
        blocked = False
        blocker_message = None

        rule = IMPACT_RULES.get(key)
        if rule and new_value == True:
            dep = rule["blocked_unless"]
            dep_resolved = await self.resolve(dep["key"])
            if dep_resolved["value"] != dep["equals"]:
                blocked = True
                blocker_message = rule["message"]

        r = await self.db.execute(select(PlatformSetting).where(PlatformSetting.key == key))
        setting = r.scalar_one_or_none()
        requires_approval = setting.requires_approval if setting else False
        requires_restart = setting.requires_restart if setting else False
        risk_level = setting.risk_level if setting else "low"

        if risk_level in ("high", "critical"):
            warnings.append(f"This is a {risk_level}-risk setting — changes affect platform-wide behavior.")
        if requires_restart:
            warnings.append("This setting requires a service restart to take effect.")
        if requires_approval:
            warnings.append("This setting requires approval before the change takes effect.")

        return {
            "key": key, "blocked": blocked, "blocker_message": blocker_message,
            "risk_level": risk_level, "requires_approval": requires_approval,
            "requires_restart": requires_restart, "rollback_available": True,
            "warnings": warnings,
        }

    # ── Effective value resolver (rich) ──────────────────────────────────────
    async def resolve_effective_value(self, key: str, tenant_id: uuid.UUID | None,
                                       plan_type: str | None) -> dict:
        default_value = PLATFORM_DEFAULTS.get(key)
        pr = await self.db.execute(select(PlatformSetting).where(PlatformSetting.key == key))
        plat = pr.scalar_one_or_none()
        global_value = self._unwrap(plat) if plat else default_value

        plan_value = None
        if plan_type:
            planr = await self.db.execute(select(PlanSetting).where(
                PlanSetting.plan_type == plan_type, PlanSetting.key == key))
            plan_s = planr.scalar_one_or_none()
            plan_value = self._unwrap(plan_s) if plan_s else None

        tenant_value = None
        if tenant_id:
            tr = await self.db.execute(select(TenantSetting).where(
                TenantSetting.tenant_id == tenant_id, TenantSetting.key == key))
            tenant_s = tr.scalar_one_or_none()
            tenant_value = self._unwrap(tenant_s) if tenant_s else None

        resolved = await self.resolve(key, tenant_id, plan_type)
        return {
            "key": key, "default_value": default_value, "global_value": global_value,
            "plan_override": plan_value, "tenant_override": tenant_value,
            "effective_value": resolved["value"], "resolution_path": resolved["source"],
            "warnings": [],
        }

    # ── Summary ──────────────────────────────────────────────────────────────
    async def get_summary(self) -> dict:
        from sqlalchemy import func
        total = await self.db.scalar(select(func.count(PlatformSetting.id))) or 0
        active = await self.db.scalar(select(func.count(PlatformSetting.id)).where(
            PlatformSetting.status == "active")) or 0
        secret = await self.db.scalar(select(func.count(PlatformSetting.id)).where(
            PlatformSetting.is_secret == True)) or 0
        pending_approval = await self.db.scalar(select(func.count(PlatformSetting.id)).where(
            PlatformSetting.requires_approval == True)) or 0
        tenant_overrides = await self.db.scalar(select(func.count(TenantSetting.id))) or 0
        plan_overrides = await self.db.scalar(select(func.count(PlanSetting.id))) or 0
        week_ago = utcnow() - timedelta(days=7)
        changed_this_week = await self.db.scalar(select(func.count(SettingAuditLog.id)).where(
            SettingAuditLog.created_at >= week_ago)) or 0
        rollback_available = await self.db.scalar(select(func.count(SettingAuditLog.id.distinct())).where(
            SettingAuditLog.tier == SettingTier.PLATFORM)) or 0
        return {
            "total_settings": total, "active_settings": active, "invalid_settings": 0,
            "secret_settings": secret, "pending_approval": pending_approval,
            "tenant_overrides": tenant_overrides, "plan_overrides": plan_overrides,
            "changed_this_week": changed_this_week,
            "rollback_available": min(rollback_available, total),
        }

    # ── Seed defaults ────────────────────────────────────────────────────────
    async def seed_defaults(self, preview: bool = False, force: bool = False) -> dict:
        from app.engines.settings_engine.seed_data import SERVICEOS_DEFAULT_SETTINGS
        existing_r = await self.db.execute(select(PlatformSetting.key))
        existing_keys = {row[0] for row in existing_r.all()}

        to_create, to_skip = [], []
        for item in SERVICEOS_DEFAULT_SETTINGS:
            if item["key"] in existing_keys and not force:
                to_skip.append(item["key"])
            else:
                to_create.append(item)

        if preview:
            return {"would_create": [i["key"] for i in to_create], "would_skip": to_skip,
                    "total_defaults": len(SERVICEOS_DEFAULT_SETTINGS)}

        created = []
        for item in to_create:
            if item["key"] in existing_keys:
                r = await self.db.execute(select(PlatformSetting).where(PlatformSetting.key == item["key"]))
                existing = r.scalar_one_or_none()
                if existing:
                    existing.value = {"v": item["value"]}
                    existing.label = item["label"]
                    existing.category = item["category"]
                    existing.setting_type = item["setting_type"]
                    existing.description = item.get("description")
                    existing.is_secret = item.get("is_secret", False)
                    existing.risk_level = item.get("risk_level", "low")
                    existing.requires_approval = item.get("requires_approval", False)
                    existing.requires_restart = item.get("requires_restart", False)
                    existing.owner_module = item.get("owner_module")
                    existing.allowed_values_json = item.get("allowed_values")
            else:
                self.db.add(PlatformSetting(
                    key=item["key"], label=item["label"], value={"v": item["value"]},
                    setting_type=item["setting_type"], category=item["category"],
                    description=item.get("description"), is_secret=item.get("is_secret", False),
                    risk_level=item.get("risk_level", "low"), requires_approval=item.get("requires_approval", False),
                    requires_restart=item.get("requires_restart", False),
                    owner_module=item.get("owner_module"),
                    allowed_values_json=item.get("allowed_values"), set_by=self.actor_id,
                ))
            created.append(item["key"])
            await self._audit(SettingTier.PLATFORM, item["key"], None, item["value"],
                               reason="Seeded ServiceOS default settings", action_type="created")
        return {"created": created, "skipped": to_skip, "total_defaults": len(SERVICEOS_DEFAULT_SETTINGS)}

    # ── Feature flags ────────────────────────────────────────────────────────
    async def list_feature_flags(self) -> dict:
        r = await self.db.execute(select(FeatureFlag).order_by(FeatureFlag.flag_key))
        return {"flags": [f.to_dict() for f in r.scalars().all()]}

    async def create_feature_flag(self, data: dict) -> dict:
        flag = FeatureFlag(
            flag_key=data["flag_key"], label=data["label"], description=data.get("description"),
            status=data.get("status", "disabled"), rollout_type=data.get("rollout_type", "global"),
            rollout_percent=data.get("rollout_percent"), category_scope=data.get("category_scope"),
            tenant_scope=data.get("tenant_scope"), owner_module=data.get("owner_module"),
        )
        self.db.add(flag)
        await self.db.flush()
        return flag.to_dict()

    async def update_feature_flag(self, flag_id: uuid.UUID, data: dict) -> dict:
        r = await self.db.execute(select(FeatureFlag).where(FeatureFlag.id == flag_id))
        flag = r.scalar_one_or_none()
        if not flag: raise NotFoundException("FeatureFlag", str(flag_id))
        for field in ("label", "description", "status", "rollout_type", "rollout_percent",
                      "category_scope", "owner_module"):
            if field in data and data[field] is not None:
                setattr(flag, field, data[field])
        return flag.to_dict()

    async def set_feature_flag_status(self, flag_id: uuid.UUID, status: str) -> dict:
        r = await self.db.execute(select(FeatureFlag).where(FeatureFlag.id == flag_id))
        flag = r.scalar_one_or_none()
        if not flag: raise NotFoundException("FeatureFlag", str(flag_id))
        flag.status = status
        return flag.to_dict()
