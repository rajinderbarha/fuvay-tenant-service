"""CONFIGURATION-REGISTRY-REBUILD: governed change-request workflow +
deterministic effective-value resolution over ConfigurationDefinition
(registry.py) + ConfigurationValueVersion (models.py).

Resolution precedence (documented, deterministic, tested):
  1. Code-enforced lock/safety rule (locked=True) -- always wins, no
     lower-authority value can ever override it.
  2. Environment-specific registered override (scope_type="environment")
  3. Vertical override (scope_type="vertical"), only if the definition
     permits vertical scope
  4. Global approved override (scope_type="global")
  5. Code default (ConfigurationDefinition.default_value)

Writes through to the legacy PlatformSetting row on activate() so the two
real, already-wired consumers (booking_cancellation_window_hours,
dispatch_score_weights -- both read via SettingsService.resolve()) observe
governed changes without any change to their own call sites. This is a
disclosed compatibility bridge, not a claim that SettingsService.resolve()
itself was rewritten.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.settings_engine.registry import ConfigurationRegistry, ConfigurationDefinition
from app.engines.settings_engine.models import ConfigurationValueVersion, PlatformSetting, SettingAuditLog
from app.exceptions import ServiceOSException

GLOBAL_SCOPE_ID = "GLOBAL"


class ConfigurationService:

    def __init__(self, db: AsyncSession, request_id: str = "—",
                 actor_id: uuid.UUID | None = None, actor_role: str | None = None):
        self.db = db
        self.request_id = request_id
        self.actor_id = actor_id
        self.actor_role = actor_role

    # ── Registry lookups ─────────────────────────────────────────────────────

    def _definition(self, key: str) -> ConfigurationDefinition:
        d = ConfigurationRegistry.get(key)
        if not d:
            raise ServiceOSException("NOT_FOUND", f"'{key}' is not a registered configuration setting.", status_code=404)
        return d

    def _scope_id_or_global(self, scope_type: str, scope_id: str | None) -> str:
        return scope_id if scope_type != "global" else GLOBAL_SCOPE_ID

    # ── Validation ────────────────────────────────────────────────────────────

    def _validate(self, d: ConfigurationDefinition, scope_type: str, value: Any) -> list[str]:
        errors: list[str] = []
        if d.locked:
            errors.append(f"'{d.key}' is a critical locked setting -- code-controlled, no change request permitted.")
            return errors
        if not d.admin_mutable:
            errors.append(f"'{d.key}' is not admin-mutable.")
        if scope_type not in d.allowed_scopes:
            errors.append(f"scope '{scope_type}' is not permitted for '{d.key}' (allowed: {d.allowed_scopes}).")

        if d.data_type == "boolean" and not isinstance(value, bool):
            errors.append(f"value must be boolean, got {type(value).__name__}")
        elif d.data_type in ("integer", "duration", "percentage") and (isinstance(value, bool) or not isinstance(value, (int, float))):
            errors.append(f"value must be numeric, got {type(value).__name__}")
        elif d.data_type == "decimal" and (isinstance(value, bool) or not isinstance(value, (int, float))):
            errors.append(f"value must be a decimal number, got {type(value).__name__}")
        elif d.data_type in ("string", "timestamp") and not isinstance(value, str):
            errors.append(f"value must be a string, got {type(value).__name__}")
        elif d.data_type == "enum":
            if not d.enum_values:
                errors.append(f"'{d.key}' is declared enum but has no registered enum_values")
            elif value not in d.enum_values:
                errors.append(f"value {value!r} is not one of the allowed values: {d.enum_values}")

        if d.minimum is not None and isinstance(value, (int, float)) and not isinstance(value, bool) and value < d.minimum:
            errors.append(f"value {value} is below the minimum ({d.minimum})")
        if d.maximum is not None and isinstance(value, (int, float)) and not isinstance(value, bool) and value > d.maximum:
            errors.append(f"value {value} exceeds the maximum ({d.maximum})")

        return errors

    def validate(self, key: str, scope_type: str, value: Any) -> dict:
        d = self._definition(key)
        errors = self._validate(d, scope_type, value)
        return {"valid": len(errors) == 0, "errors": errors}

    # ── Effective value resolution (deterministic, documented precedence) ──

    async def resolve_effective_value(self, key: str, vertical_key: str | None = None,
                                       environment: str | None = None) -> dict:
        d = self._definition(key)

        if d.locked:
            return {
                "key": key, "effective_value": d.default_value, "source": "code_locked",
                "scope": "global", "definition_version": 1, "value_version": None,
                "effective_date": None, "fallback_value": d.default_value, "lock_status": "locked",
            }

        # 2. environment override
        if environment:
            env_row = await self._current(key, "environment", environment)
            if env_row:
                return self._resolved(d, env_row, "environment")

        # 3. vertical override (only if the definition permits vertical scope)
        if vertical_key and "vertical" in d.allowed_scopes:
            vert_row = await self._current(key, "vertical", vertical_key)
            if vert_row:
                return self._resolved(d, vert_row, "vertical")

        # 4. global approved override
        global_row = await self._current(key, "global", GLOBAL_SCOPE_ID)
        if global_row:
            return self._resolved(d, global_row, "global")

        # 5. code default
        return {
            "key": key, "effective_value": d.default_value, "source": "code_default",
            "scope": None, "definition_version": 1, "value_version": None,
            "effective_date": None, "fallback_value": d.default_value, "lock_status": "unlocked",
        }

    def _resolved(self, d: ConfigurationDefinition, row: ConfigurationValueVersion, scope: str) -> dict:
        return {
            "key": d.key, "effective_value": row.value.get("v"), "source": scope,
            "scope": scope, "definition_version": 1, "value_version": row.version_number,
            "effective_date": row.effective_from.isoformat() if row.effective_from else None,
            "fallback_value": d.default_value, "lock_status": "unlocked",
        }

    async def _current(self, key: str, scope_type: str, scope_id: str) -> ConfigurationValueVersion | None:
        r = await self.db.execute(select(ConfigurationValueVersion).where(
            ConfigurationValueVersion.setting_key == key,
            ConfigurationValueVersion.scope_type == scope_type,
            ConfigurationValueVersion.scope_id == scope_id,
            ConfigurationValueVersion.status == "active",
        ))
        return r.scalar_one_or_none()

    # ── Change-request workflow ──────────────────────────────────────────────

    async def create_change_request(self, key: str, scope_type: str, scope_id: str | None,
                                     value: Any, *, reason: str, actor_id: uuid.UUID | None) -> dict:
        d = self._definition(key)
        errors = self._validate(d, scope_type, value)
        if errors:
            raise ServiceOSException("VALIDATION_ERROR", "; ".join(errors), status_code=422)
        if not reason or not reason.strip():
            raise ServiceOSException("VALIDATION_ERROR", "A change reason is required.", status_code=422)

        resolved_scope_id = self._scope_id_or_global(scope_type, scope_id)
        if scope_type != "global" and not resolved_scope_id:
            raise ServiceOSException("VALIDATION_ERROR", f"scope_id is required for scope '{scope_type}'.", status_code=422)

        max_version = (await self.db.execute(select(func.max(ConfigurationValueVersion.version_number)).where(
            ConfigurationValueVersion.setting_key == key,
            ConfigurationValueVersion.scope_type == scope_type,
            ConfigurationValueVersion.scope_id == resolved_scope_id,
        ))).scalar() or 0

        row = ConfigurationValueVersion(
            setting_key=key, scope_type=scope_type, scope_id=resolved_scope_id,
            version_number=max_version + 1,
            status="draft" if not d.approval_required else "pending_approval",
            value={"v": value}, change_reason=reason, created_by=actor_id,
        )
        self.db.add(row)
        await self.db.flush()
        await self._audit(key, scope_type, resolved_scope_id, None, value, actor_id, reason,
                          d.risk_level, "change_request.created")
        await self.db.commit()
        return row.to_dict()

    async def approve(self, version_id: uuid.UUID, *, actor_id: uuid.UUID | None) -> dict:
        row = await self._get(version_id)
        d = self._definition(row.setting_key)
        if row.status != "pending_approval":
            raise ServiceOSException("VALIDATION_ERROR", "Only a pending-approval change can be approved.", status_code=422)
        # SELF-APPROVAL-PREVENTION: the creator of a high-risk change must
        # not approve their own change (no break-glass exception implemented
        # here -- add one explicitly if the business ever requires it).
        if actor_id is not None and row.created_by is not None and actor_id == row.created_by:
            raise ServiceOSException("PERMISSION_DENIED",
                "You created this change request -- a different approver is required.", status_code=403)
        row.status = "scheduled" if row.effective_from else "approved"
        row.approved_by = actor_id
        await self._audit(row.setting_key, row.scope_type, row.scope_id, None, row.value.get("v"),
                          actor_id, "approved", d.risk_level, "change_request.approved")
        await self.db.commit()
        await self.db.refresh(row)
        return row.to_dict()

    async def activate(self, version_id: uuid.UUID, *, actor_id: uuid.UUID | None) -> dict:
        row = await self._get(version_id)
        d = self._definition(row.setting_key)
        if row.status not in ("approved", "scheduled", "draft"):
            raise ServiceOSException("VALIDATION_ERROR", f"Cannot activate a version in status '{row.status}'.", status_code=422)
        if d.approval_required and row.status == "draft":
            raise ServiceOSException("VALIDATION_ERROR", "This setting requires approval before activation.", status_code=422)

        prior = await self._current(row.setting_key, row.scope_type, row.scope_id)
        before_value = prior.value.get("v") if prior else d.default_value
        if prior:
            prior.status = "superseded"
            prior.effective_to = datetime.now(timezone.utc)
            await self.db.flush()

        row.status = "active"
        row.activated_by = actor_id
        row.activated_at = datetime.now(timezone.utc)
        if not row.effective_from:
            row.effective_from = row.activated_at
        await self.db.flush()

        # Compatibility bridge: write through to the legacy PlatformSetting
        # row so the 2 real consumers (which call SettingsService.resolve(),
        # not this service) observe the change immediately.
        if row.scope_type == "global":
            await self._write_through_platform_setting(d, row.value.get("v"))

        await self._audit(row.setting_key, row.scope_type, row.scope_id, before_value, row.value.get("v"),
                          actor_id, "activated", d.risk_level, "change_request.activated")
        await self.db.commit()
        await self.db.refresh(row)
        return row.to_dict()

    async def rollback(self, version_id: uuid.UUID, *, actor_id: uuid.UUID | None, reason: str) -> dict:
        if not reason or not reason.strip():
            raise ServiceOSException("VALIDATION_ERROR", "A rollback reason is required.", status_code=422)
        row = await self._get(version_id)
        d = self._definition(row.setting_key)
        if not d.rollback_supported:
            raise ServiceOSException("VALIDATION_ERROR", f"'{row.setting_key}' does not support rollback.", status_code=422)
        if row.status != "active":
            raise ServiceOSException("VALIDATION_ERROR", "Only the currently active version can be rolled back.", status_code=422)

        prior = await self.db.execute(select(ConfigurationValueVersion).where(
            ConfigurationValueVersion.setting_key == row.setting_key,
            ConfigurationValueVersion.scope_type == row.scope_type,
            ConfigurationValueVersion.scope_id == row.scope_id,
            ConfigurationValueVersion.id == row.supersedes_value_id,
        ) if row.supersedes_value_id else select(ConfigurationValueVersion).where(
            ConfigurationValueVersion.setting_key == row.setting_key,
            ConfigurationValueVersion.scope_type == row.scope_type,
            ConfigurationValueVersion.scope_id == row.scope_id,
            ConfigurationValueVersion.version_number == row.version_number - 1,
        ))
        prior_row = prior.scalar_one_or_none()
        restore_value = prior_row.value.get("v") if prior_row else d.default_value

        row.status = "rolled_back"
        row.rolled_back_by = actor_id
        row.rollback_reason = reason
        await self.db.flush()

        max_version = (await self.db.execute(select(func.max(ConfigurationValueVersion.version_number)).where(
            ConfigurationValueVersion.setting_key == row.setting_key,
            ConfigurationValueVersion.scope_type == row.scope_type,
            ConfigurationValueVersion.scope_id == row.scope_id,
        ))).scalar() or 0
        restored = ConfigurationValueVersion(
            setting_key=row.setting_key, scope_type=row.scope_type, scope_id=row.scope_id,
            version_number=max_version + 1, status="active", value={"v": restore_value},
            supersedes_value_id=row.id, change_reason=f"Rollback: {reason}",
            created_by=actor_id, activated_by=actor_id, activated_at=datetime.now(timezone.utc),
            effective_from=datetime.now(timezone.utc),
        )
        self.db.add(restored)
        await self.db.flush()

        if row.scope_type == "global":
            await self._write_through_platform_setting(d, restore_value)

        await self._audit(row.setting_key, row.scope_type, row.scope_id, row.value.get("v"), restore_value,
                          actor_id, reason, d.risk_level, "change_request.rolled_back")
        await self.db.commit()
        await self.db.refresh(restored)
        return restored.to_dict()

    async def list_history(self, key: str, scope_type: str = "global", scope_id: str | None = None) -> list[dict]:
        self._definition(key)
        resolved_scope_id = self._scope_id_or_global(scope_type, scope_id)
        r = await self.db.execute(select(ConfigurationValueVersion).where(
            ConfigurationValueVersion.setting_key == key,
            ConfigurationValueVersion.scope_type == scope_type,
            ConfigurationValueVersion.scope_id == resolved_scope_id,
        ).order_by(ConfigurationValueVersion.version_number.desc()))
        return [v.to_dict() for v in r.scalars().all()]

    # ── Internal helpers ──────────────────────────────────────────────────────

    async def _get(self, version_id: uuid.UUID) -> ConfigurationValueVersion:
        row = await self.db.get(ConfigurationValueVersion, version_id)
        if not row:
            raise ServiceOSException("NOT_FOUND", "Configuration value version not found.", status_code=404)
        return row

    async def _write_through_platform_setting(self, d: ConfigurationDefinition, value: Any) -> None:
        r = await self.db.execute(select(PlatformSetting).where(PlatformSetting.key == d.key))
        existing = r.scalar_one_or_none()
        type_map = {"boolean": "boolean", "integer": "number", "decimal": "number",
                    "duration": "number", "percentage": "number", "structured": "json"}
        setting_type = type_map.get(d.data_type, "string")
        if existing:
            existing.value = {"v": value}
            existing.setting_type = setting_type
        else:
            self.db.add(PlatformSetting(
                key=d.key, value={"v": value}, setting_type=setting_type,
                label=d.label, category=d.owner_module, risk_level=d.risk_level,
                requires_approval=d.approval_required, owner_module=d.owner_module,
            ))
        try:
            from app.engines.settings_engine.constants import REDIS_PLATFORM_SETTING
            from app.redis_client import cache_delete
            await cache_delete(REDIS_PLATFORM_SETTING.format(key=d.key))
        except Exception:
            pass

    async def _audit(self, key: str, scope_type: str, scope_id: str, old_value: Any, new_value: Any,
                     actor_id: uuid.UUID | None, reason: str | None, risk_level: str, action_type: str) -> None:
        self.db.add(SettingAuditLog(
            tenant_id=None, tier=scope_type, key=key,
            old_value={"v": old_value} if old_value is not None else None,
            new_value={"v": new_value}, changed_by=actor_id, reason=reason,
            request_id=self.request_id, risk_level=risk_level, action_type=action_type,
        ))
