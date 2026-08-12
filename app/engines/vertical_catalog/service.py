"""Vertical Catalog Service — business logic."""
from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select, update, text, func
from sqlalchemy.ext.asyncio import AsyncSession

from datetime import datetime, timezone

from app.engines.vertical_catalog.models import (
    Vertical, CatalogModuleDefinition, VerticalCatalogModule, VerticalMenuConfig,
    VerticalEngineMapping, TenantVerticalEnrollment, VerticalAuditLog,
)

# Real runtime bug fixed here (TENANT-ADMIN-LIFECYCLE-CLOSURE): the three
# activation-lifecycle states below were introduced in
# `vertical_catalog.activation` and are passed to `transition_enrollment`
# by `approve_enrollment` / `try_auto_activate`, but were never added to
# this allowlist -- so EVERY activation attempt raised
# `ValueError("Invalid enrollment status ...")` and no tenant could ever
# be auto-activated.
ENROLLMENT_STATUSES = {
    "draft", "submitted", "under_review", "changes_requested",
    "approved", "approved_pending_activation",
    "activation_requirements_pending", "activating",
    "active", "suspended", "rejected",
}

# The subset an API CLIENT (Admin UI) may request directly. "active" and
# "activating" are deliberately excluded: reaching them means every
# activation gate has genuinely passed, which only
# `activation.try_auto_activate` can determine. Letting an admin PATCH
# straight to "active" would bypass the entire gate system and mark a
# tenant live with, for example, no service area or no payout account.
CLIENT_REQUESTABLE_STATUSES = ENROLLMENT_STATUSES - {"active", "activating"}


class VerticalCatalogService:

    # ── Verticals ─────────────────────────────────────────────────────────────

    async def list_verticals(self, db: AsyncSession, *, include_disabled: bool = False) -> list[dict]:
        q = select(Vertical).order_by(Vertical.sort_order)
        if not include_disabled:
            q = q.where(Vertical.is_enabled == True)  # noqa: E712
        rows = (await db.execute(q)).scalars().all()
        return [self._v_dict(v) for v in rows]

    async def get_vertical(self, db: AsyncSession, key: str) -> dict | None:
        v = await self._by_key(db, key)
        if not v:
            return None
        modules = await self._modules_for_vertical(db, v.id)
        d = self._v_dict(v)
        d["modules"] = modules
        return d

    async def enable_vertical(self, db: AsyncSession, key: str, *, actor_id=None) -> dict:
        v = await self._by_key(db, key)
        if not v:
            raise ValueError(f"Vertical '{key}' not found")
        before = self._v_dict(v)
        v.is_enabled = True
        v.enabled_by = actor_id
        v.enabled_at = datetime.now(timezone.utc)
        v.disable_reason = None
        await db.flush()
        db.add(VerticalAuditLog(vertical_id=v.id, actor_id=actor_id, action_type="vertical.enable",
                                 before_state=before, after_state=self._v_dict(v)))
        await db.commit()
        await db.refresh(v)
        return self._v_dict(v)

    async def disable_vertical(self, db: AsyncSession, key: str, *, actor_id=None, reason: str | None = None) -> dict:
        v = await self._by_key(db, key)
        if not v:
            raise ValueError(f"Vertical '{key}' not found")
        before = self._v_dict(v)
        v.is_enabled = False
        v.disabled_by = actor_id
        v.disabled_at = datetime.now(timezone.utc)
        v.disable_reason = reason
        await db.flush()
        db.add(VerticalAuditLog(vertical_id=v.id, actor_id=actor_id, action_type="vertical.disable",
                                 before_state=before, after_state=self._v_dict(v), notes=reason))
        await db.commit()
        await db.refresh(v)
        return self._v_dict(v)

    async def disable_impact(self, db: AsyncSession, key: str) -> dict:
        """Impact summary shown before a disable confirmation (spec: active
        tenants/enrollments affected, so admin can't disable blind)."""
        v = await self._by_key(db, key)
        if not v:
            raise ValueError(f"Vertical '{key}' not found")
        rows = (await db.execute(
            select(TenantVerticalEnrollment.status, func.count())
            .where(TenantVerticalEnrollment.vertical_id == v.id)
            .group_by(TenantVerticalEnrollment.status)
        )).all()
        by_status = {status: count for status, count in rows}
        return {
            "vertical_key": key,
            "active_tenant_enrollments": by_status.get("active", 0),
            "under_review_enrollments": by_status.get("under_review", 0) + by_status.get("submitted", 0),
            "enrollments_by_status": by_status,
        }

    async def update_vertical(self, db: AsyncSession, key: str, payload: dict, *, actor_id=None) -> dict:
        v = await self._by_key(db, key)
        if not v:
            raise ValueError(f"Vertical '{key}' not found")
        before = self._v_dict(v)
        allowed = {
            "label", "description", "icon", "color", "sort_order", "finance_model", "meta", "is_beta",
            "capabilities", "onboarding_requirements", "registration_allowed", "lifecycle_status",
        }
        for k, val in payload.items():
            if k in allowed:
                setattr(v, k, val)
        await db.flush()
        db.add(VerticalAuditLog(vertical_id=v.id, actor_id=actor_id, action_type="vertical.update",
                                 before_state=before, after_state=self._v_dict(v)))
        await db.commit()
        await db.refresh(v)
        return self._v_dict(v)

    # ── Tenant-Vertical Enrollments ───────────────────────────────────────────

    async def list_enrollments(self, db: AsyncSession, *, vertical_key: str | None = None,
                                tenant_id=None, status: str | None = None) -> list[dict]:
        q = select(TenantVerticalEnrollment)
        if vertical_key:
            v = await self._by_key(db, vertical_key)
            if not v:
                raise ValueError(f"Vertical '{vertical_key}' not found")
            q = q.where(TenantVerticalEnrollment.vertical_id == v.id)
        if tenant_id:
            q = q.where(TenantVerticalEnrollment.tenant_id == tenant_id)
        if status:
            q = q.where(TenantVerticalEnrollment.status == status)
        rows = (await db.execute(q.order_by(TenantVerticalEnrollment.created_at.desc()))).scalars().all()
        return [self._enrollment_dict(r) for r in rows]

    async def get_or_create_enrollment(self, db: AsyncSession, tenant_id, vertical_key: str) -> dict:
        v = await self._by_key(db, vertical_key)
        if not v:
            raise ValueError(f"Vertical '{vertical_key}' not found")
        existing = (await db.execute(
            select(TenantVerticalEnrollment).where(
                TenantVerticalEnrollment.tenant_id == tenant_id,
                TenantVerticalEnrollment.vertical_id == v.id,
            )
        )).scalar_one_or_none()
        if existing:
            return self._enrollment_dict(existing)
        row = TenantVerticalEnrollment(tenant_id=tenant_id, vertical_id=v.id, status="draft")
        db.add(row)
        await db.commit()
        await db.refresh(row)
        return self._enrollment_dict(row)

    async def transition_enrollment(self, db: AsyncSession, enrollment_id, new_status: str, *,
                                     actor_id=None, reason: str | None = None) -> dict:
        if new_status not in ENROLLMENT_STATUSES:
            raise ValueError(f"Invalid enrollment status '{new_status}'")
        row = (await db.execute(
            select(TenantVerticalEnrollment).where(TenantVerticalEnrollment.id == enrollment_id)
        )).scalar_one_or_none()
        if not row:
            raise ValueError("Enrollment not found")
        before = self._enrollment_dict(row)
        now = datetime.now(timezone.utc)
        row.status = new_status
        row.reviewed_by = actor_id
        row.reviewed_at = now
        if new_status == "active":
            row.activated_at = now
            row.suspended_at = None
            row.suspend_reason = None
        elif new_status == "suspended":
            row.suspended_at = now
            row.suspend_reason = reason
        elif new_status == "rejected":
            row.rejection_reason = reason
        elif new_status == "changes_requested":
            row.changes_requested_note = reason
        elif new_status == "submitted":
            row.submitted_at = now
        await db.flush()
        db.add(VerticalAuditLog(vertical_id=row.vertical_id, tenant_id=row.tenant_id, actor_id=actor_id,
                                 action_type=f"enrollment.{new_status}", before_state=before,
                                 after_state=self._enrollment_dict(row), notes=reason))
        await db.commit()
        await db.refresh(row)
        return self._enrollment_dict(row)

    async def submit_for_review(self, db: AsyncSession, tenant_id, vertical_key: str, *,
                                actor_id=None) -> dict:
        """Validate and submit a tenant's vertical setup for Admin review.

        This is the single tenant-to-Admin handoff.  The enrollment drives
        tenant routing while ``tenants.verification_status`` drives the
        existing Admin onboarding queue, so both records must move together.
        """
        from app.engines.vertical_catalog.declarations import get_declaration_status
        from app.engines.vertical_catalog.home_services_setup_service import get_setup_overview
        from app.exceptions import ServiceOSException

        enrollment = await self.get_or_create_enrollment(db, tenant_id, vertical_key)
        if enrollment["status"] not in ("draft", "draft_setup", "changes_requested"):
            raise ServiceOSException(
                "VERTICAL_SETUP_ALREADY_SUBMITTED",
                f"This setup cannot be submitted from '{enrollment['status']}' status.",
                status_code=409,
            )

        overview = await get_setup_overview(db, tenant_id)
        incomplete = [
            section["key"] for section in overview["sections"]
            if section["required"] and section["status"] != "complete"
        ]
        if incomplete:
            raise ServiceOSException(
                "VERTICAL_SETUP_INCOMPLETE",
                "Complete all required setup sections before submitting for review.",
                status_code=422,
                context={"incomplete_sections": incomplete},
            )

        declarations = await get_declaration_status(
            db, uuid.UUID(str(tenant_id)), uuid.UUID(enrollment["vertical_id"])
        )
        if not declarations["all_accepted"]:
            raise ServiceOSException(
                "ONBOARDING_DECLARATIONS_REQUIRED",
                "Accept all required declarations before submitting for review.",
                status_code=422,
            )

        # The legacy Admin onboarding workspace is intentionally retained,
        # but it reads Tenant.verification_status. Keep it synchronized with
        # the canonical vertical enrollment in the same transaction committed
        # by transition_enrollment below.
        await db.execute(
            text(
                "UPDATE tenants SET verification_status='pending', "
                "status='under_review', updated_at=NOW() WHERE id=:tid"
            ),
            {"tid": str(tenant_id)},
        )
        return await self.transition_enrollment(
            db, uuid.UUID(enrollment["id"]), "submitted", actor_id=actor_id
        )

    def _enrollment_dict(self, r: TenantVerticalEnrollment) -> dict:
        return {
            "id": str(r.id), "tenant_id": str(r.tenant_id), "vertical_id": str(r.vertical_id),
            "status": r.status, "requested_at": r.requested_at.isoformat() if r.requested_at else None,
            "submitted_at": r.submitted_at.isoformat() if r.submitted_at else None,
            "reviewed_by": str(r.reviewed_by) if r.reviewed_by else None,
            "reviewed_at": r.reviewed_at.isoformat() if r.reviewed_at else None,
            "activated_at": r.activated_at.isoformat() if r.activated_at else None,
            "suspended_at": r.suspended_at.isoformat() if r.suspended_at else None,
            "suspend_reason": r.suspend_reason, "rejection_reason": r.rejection_reason,
            "changes_requested_note": r.changes_requested_note, "admin_notes": r.admin_notes,
        }

    # ── Catalog Modules ───────────────────────────────────────────────────────

    async def list_modules(self, db: AsyncSession) -> list[dict]:
        rows = (await db.execute(
            select(CatalogModuleDefinition).order_by(CatalogModuleDefinition.sort_order)
        )).scalars().all()
        return [self._mod_dict(m) for m in rows]

    async def toggle_module(self, db: AsyncSession, vertical_key: str, module_key: str, enabled: bool) -> dict:
        v = await self._by_key(db, vertical_key)
        if not v:
            raise ValueError(f"Vertical '{vertical_key}' not found")
        m = await self._module_by_key(db, module_key)
        if not m:
            raise ValueError(f"Module '{module_key}' not found")

        vcm = (await db.execute(
            select(VerticalCatalogModule).where(
                VerticalCatalogModule.vertical_id == v.id,
                VerticalCatalogModule.module_id == m.id,
            )
        )).scalar_one_or_none()

        if vcm:
            if vcm.is_required and not enabled:
                raise ValueError(f"Module '{module_key}' is required for this vertical and cannot be disabled")
            vcm.is_enabled = enabled
        else:
            if not enabled:
                return {"status": "no_change"}
            vcm = VerticalCatalogModule(
                vertical_id=v.id, module_id=m.id, is_enabled=True, is_required=False
            )
            db.add(vcm)

        await db.commit()
        return {"vertical_key": vertical_key, "module_key": module_key, "is_enabled": enabled}

    # ── Engine Mappings ───────────────────────────────────────────────────────

    async def list_engine_mappings(self, db: AsyncSession, vertical_key: str) -> list[dict]:
        v = await self._by_key(db, vertical_key)
        if not v:
            raise ValueError(f"Vertical '{vertical_key}' not found")
        rows = (await db.execute(
            select(VerticalEngineMapping).where(
                VerticalEngineMapping.vertical_id == v.id
            ).order_by(VerticalEngineMapping.sort_order)
        )).scalars().all()
        return [self._engine_mapping_dict(m) for m in rows]

    async def set_engine_mappings(self, db: AsyncSession, vertical_key: str, mappings: list[dict]) -> list[dict]:
        v = await self._by_key(db, vertical_key)
        if not v:
            raise ValueError(f"Vertical '{vertical_key}' not found")
        existing = (await db.execute(
            select(VerticalEngineMapping).where(VerticalEngineMapping.vertical_id == v.id)
        )).scalars().all()
        for row in existing:
            await db.delete(row)
        await db.flush()
        for i, m in enumerate(mappings):
            db.add(VerticalEngineMapping(
                vertical_id=v.id, engine_key=m["engine_key"],
                is_required=m.get("is_required", False), sort_order=m.get("sort_order", i),
            ))
        await db.commit()
        return await self.list_engine_mappings(db, vertical_key)

    def _engine_mapping_dict(self, m: VerticalEngineMapping) -> dict:
        return {
            "id": str(m.id), "vertical_id": str(m.vertical_id), "engine_key": m.engine_key,
            "is_required": m.is_required, "sort_order": m.sort_order,
        }

    # ── Effective Navigation Menu ─────────────────────────────────────────────

    # Which verticals require each cross-vertical "Operations"/"Finance" nav item.
    # Keys match the operation_visibility flags returned by get_effective_menu().
    _OPERATION_VERTICAL_RULES: dict[str, set[str]] = {
        "jobs_field_ops": {"home_services", "repair_services", "cleaning_services", "automotive"},
        "site_visits": {"real_estate"},
        "orders": {"restaurant", "product_marketplace", "marketplace_products"},
        "leads_crm": {"coaching", "real_estate", "professional_services"},
        "appointments": {"coaching", "professional_services", "real_estate"},
        # Home-Services-only finance concepts (usage credits / security deposit model —
        # never real tenant payouts; see business rules in Trust & Quality / Tenant Detail work).
        "security_deposit": {"home_services"},
        "usage_credits": {"home_services"},
    }

    async def get_effective_menu(self, db: AsyncSession) -> dict:
        """Returns the full sidebar menu config: universal modules + per-vertical enabled
        modules + cross-vertical "operation visibility" flags (Jobs/Site Visits/Orders/
        Leads CRM/Appointments/Finance items that must not show for every vertical)."""
        verticals = await self.list_verticals(db, include_disabled=True)
        modules = await self.list_modules(db)
        universal = [m for m in modules if m["is_universal"]]

        enabled_keys = {v["key"] for v in verticals if v["is_enabled"]}

        result: list[dict] = []
        for v in verticals:
            mods = await self._modules_for_vertical(db, uuid.UUID(v["id"]))
            result.append({
                "vertical_key": v["key"],
                "vertical_label": v["label"],
                "is_enabled": v["is_enabled"],
                "is_beta": v["is_beta"],
                "icon": v["icon"],
                "color": v["color"],
                "modules": [m for m in mods if m["is_enabled"]],
            })

        operation_visibility = {
            op_key: bool(enabled_keys & required_verticals)
            for op_key, required_verticals in self._OPERATION_VERTICAL_RULES.items()
        }

        return {
            "universal_modules": universal,
            "verticals": result,
            "enabled_vertical_keys": sorted(enabled_keys),
            "operation_visibility": operation_visibility,
        }

    # ── Private helpers ───────────────────────────────────────────────────────

    async def _by_key(self, db: AsyncSession, key: str) -> Vertical | None:
        return (await db.execute(
            select(Vertical).where(Vertical.key == key)
        )).scalar_one_or_none()

    async def _module_by_key(self, db: AsyncSession, key: str) -> CatalogModuleDefinition | None:
        return (await db.execute(
            select(CatalogModuleDefinition).where(CatalogModuleDefinition.key == key)
        )).scalar_one_or_none()

    async def _modules_for_vertical(self, db: AsyncSession, vertical_id: uuid.UUID) -> list[dict]:
        rows = (await db.execute(text("""
            SELECT
                cmd.key, cmd.label, cmd.icon, cmd.admin_path, cmd.module_group,
                cmd.is_universal, cmd.sort_order,
                vcm.is_enabled, vcm.is_required, vcm.custom_label
            FROM vertical_catalog_modules vcm
            JOIN catalog_module_definitions cmd ON cmd.id = vcm.module_id
            WHERE vcm.vertical_id = :vid
            ORDER BY vcm.sort_order
        """), {"vid": str(vertical_id)})).fetchall()
        return [
            {
                "key": r.key,
                "label": r.custom_label or r.label,
                "icon": r.icon,
                "admin_path": r.admin_path,
                "module_group": r.module_group,
                "is_universal": r.is_universal,
                "is_enabled": r.is_enabled,
                "is_required": r.is_required,
            }
            for r in rows
        ]

    def _v_dict(self, v: Vertical) -> dict:
        return {
            "id": str(v.id),
            "key": v.key,
            "slug": v.slug,
            "label": v.label,
            "description": v.description,
            "icon": v.icon,
            "color": v.color,
            "is_enabled": v.is_enabled,
            "is_beta": v.is_beta,
            "sort_order": v.sort_order,
            "finance_model": v.finance_model,
            "meta": v.meta,
            "lifecycle_status": v.lifecycle_status,
            "registration_allowed": v.registration_allowed,
            "capabilities": v.capabilities or [],
            "onboarding_requirements": v.onboarding_requirements,
            "enabled_by": str(v.enabled_by) if v.enabled_by else None,
            "disabled_by": str(v.disabled_by) if v.disabled_by else None,
            "enabled_at": v.enabled_at.isoformat() if v.enabled_at else None,
            "disabled_at": v.disabled_at.isoformat() if v.disabled_at else None,
            "disable_reason": v.disable_reason,
        }

    def _mod_dict(self, m: CatalogModuleDefinition) -> dict:
        return {
            "id": str(m.id),
            "key": m.key,
            "label": m.label,
            "icon": m.icon,
            "admin_path": m.admin_path,
            "module_group": m.module_group,
            "is_universal": m.is_universal,
            "sort_order": m.sort_order,
        }
