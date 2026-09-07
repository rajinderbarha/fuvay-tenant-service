"""Vertical Catalog Service — business logic."""
from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import or_, select, update, text, func
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

    async def list_verticals_directory(
        self, db: AsyncSession, *, include_disabled: bool = True, q: str | None = None,
        status: str | None = None, finance_model: str | None = None,
        lifecycle_status: str | None = None, release_stage: str | None = None,
        registration_allowed: bool | None = None, is_beta: bool | None = None,
        page: int = 1, page_size: int = 25, sort_by: str = "sort_order",
        sort_dir: str = "asc",
    ) -> dict:
        """Database-backed administrative directory for the vertical registry."""
        conditions = []
        if not include_disabled:
            conditions.append(Vertical.is_enabled.is_(True))
        if status == "enabled":
            conditions.append(Vertical.is_enabled.is_(True))
        elif status == "disabled":
            conditions.append(Vertical.is_enabled.is_(False))
        if q and q.strip():
            needle = f"%{q.strip()}%"
            conditions.append(or_(Vertical.label.ilike(needle), Vertical.key.ilike(needle),
                                  Vertical.slug.ilike(needle), Vertical.description.ilike(needle)))
        if finance_model:
            conditions.append(Vertical.finance_model == finance_model)
        if lifecycle_status:
            conditions.append(Vertical.lifecycle_status == lifecycle_status)
        if release_stage:
            conditions.append(Vertical.release_stage == release_stage)
        if registration_allowed is not None:
            conditions.append(Vertical.registration_allowed == registration_allowed)
        if is_beta is not None:
            conditions.append(Vertical.is_beta == is_beta)

        total = int((await db.execute(
            select(func.count()).select_from(Vertical).where(*conditions)
        )).scalar_one())
        sort_columns = {
            "sort_order": Vertical.sort_order, "label": Vertical.label,
            "key": Vertical.key, "finance_model": Vertical.finance_model,
            "lifecycle_status": Vertical.lifecycle_status, "release_stage": Vertical.release_stage,
            "updated_at": Vertical.updated_at,
        }
        column = sort_columns.get(sort_by, Vertical.sort_order)
        ordering = column.desc().nullslast() if sort_dir == "desc" else column.asc().nullsfirst()
        rows = (await db.execute(
            select(Vertical).where(*conditions).order_by(ordering, Vertical.id.asc())
            .offset((page - 1) * page_size).limit(page_size)
        )).scalars().all()
        ids = [row.id for row in rows]
        module_counts: dict[uuid.UUID, tuple[int, int]] = {}
        enrollment_counts: dict[uuid.UUID, tuple[int, int]] = {}
        if ids:
            for vid, total_modules, enabled_modules in (await db.execute(
                select(VerticalCatalogModule.vertical_id, func.count(),
                       func.count().filter(VerticalCatalogModule.is_enabled.is_(True)))
                .join(CatalogModuleDefinition, CatalogModuleDefinition.id == VerticalCatalogModule.module_id)
                .where(VerticalCatalogModule.vertical_id.in_(ids))
                .where(CatalogModuleDefinition.navigation_status == "available")
                .group_by(VerticalCatalogModule.vertical_id)
            )).all():
                module_counts[vid] = (int(total_modules), int(enabled_modules))
            for vid, total_enrollments, active_enrollments in (await db.execute(
                select(TenantVerticalEnrollment.vertical_id, func.count(),
                       func.count().filter(TenantVerticalEnrollment.status == "active"))
                .where(TenantVerticalEnrollment.vertical_id.in_(ids))
                .group_by(TenantVerticalEnrollment.vertical_id)
            )).all():
                enrollment_counts[vid] = (int(total_enrollments), int(active_enrollments))
        items = []
        for row in rows:
            item = self._v_dict(row)
            item["module_count"], item["enabled_module_count"] = module_counts.get(row.id, (0, 0))
            item["enrollment_count"], item["active_enrollment_count"] = enrollment_counts.get(row.id, (0, 0))
            items.append(item)
        return {"items": items, "total": total, "page": page, "page_size": page_size,
                "pages": max(1, (total + page_size - 1) // page_size)}

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
        # These are operational records, not enrollment metadata. A disable
        # blocks new entry but deliberately leaves existing work untouched,
        # so administrators must see both counts before confirming it.
        from app.engines.final_records.models import ServiceJob
        from app.engines.home_service_booking.models import HomeServiceBookingDraft
        active_jobs = (await db.execute(
            select(func.count(ServiceJob.id)).where(
                ServiceJob.status.notin_(("completed", "cancelled", "voided", "failed"))
            )
        )).scalar() or 0
        draft_bookings = (await db.execute(
            select(func.count(HomeServiceBookingDraft.id)).where(
                HomeServiceBookingDraft.status.notin_(("converted", "expired", "cancelled", "failed"))
            )
        )).scalar() or 0
        return {
            "vertical_key": key,
            "active_tenant_enrollments": by_status.get("active", 0),
            "under_review_enrollments": by_status.get("under_review", 0) + by_status.get("submitted", 0),
            "active_jobs": int(active_jobs),
            "draft_bookings_in_progress": int(draft_bookings),
            "enrollments_by_status": by_status,
        }

    async def get_capability_registry(self, db: AsyncSession, key: str) -> dict:
        """Return ownership and runtime behaviour, not editable feature flags."""
        if not await self._by_key(db, key):
            raise ValueError(f"Vertical '{key}' not found")
        if key != "home_services":
            return {"vertical_key": key, "groups": []}
        return {
            "vertical_key": key,
            "groups": [
                {"name": "Provider setup", "capabilities": [
                    {"name": "Tenant onboarding gates", "status": "enabled", "owner": "Admin + Backend policy",
                     "source": "Tenant setup rules",
                     "action_href": "/admin/catalog-workspace?tab=setup-rules",
                     "action_label": "Manage setup rules",
                     "runtime_behaviour": "Business profile, documents, catalog, coverage, staff, finance and declarations gate submission and activation."},
                    {"name": "Catalog blueprint", "status": "enabled", "owner": "Admin",
                     "source": "Catalog Workspace",
                     "action_href": "/admin/catalog-workspace",
                     "action_label": "Open catalog workspace",
                     "runtime_behaviour": "Admins define categories, groups, services, job types, types, brands, questions, options, workflow and checklist requirements."},
                    {"name": "Tenant-owned pricing", "status": "enabled", "owner": "Tenant",
                     "source": "Tenant service setup",
                     "runtime_behaviour": "Providers configure prices within the published admin blueprint."},
                ]},
                {"name": "Customer experience", "capabilities": [
                    {"name": "Provider-published fixed pricing", "status": "enabled", "owner": "Tenant + Backend policy",
                     "source": "Customer booking API",
                     "runtime_behaviour": "The customer confirms one server-resolved provider price; inspection jobs disclose the visit fee and quote process."},
                    {"name": "Customer provider selection", "status": "disabled", "owner": "Code-controlled",
                     "source": "Matching engine",
                     "runtime_behaviour": "The matching engine selects the eligible provider."},
                    {"name": "Native customer booking", "status": "enabled", "owner": "Backend policy",
                     "source": "Customer app",
                     "action_href": "/admin/home-services/bookings-jobs",
                     "action_label": "Monitor bookings",
                     "runtime_behaviour": "Customer app booking drafts convert into canonical service bookings and jobs; no web customer mode is listed as a module."},
                ]},
                {"name": "Service execution", "capabilities": [
                    {"name": "Native booking-to-completion", "status": "enabled", "owner": "Backend policy",
                     "source": "Customer app + Staff app",
                     "action_href": "/admin/home-services/bookings-jobs",
                     "action_label": "Open operations",
                     "runtime_behaviour": "Booking, assignment, quote, work and completion use one canonical job."},
                    {"name": "Exactly-once completion charge", "status": "enabled", "owner": "Backend policy",
                     "source": "Usage credit ledger",
                     "action_href": "/admin/home-services/finance?tab=credits",
                     "action_label": "Open credits",
                     "runtime_behaviour": "A completed job posts one idempotent Usage Credit ledger deduction."},
                    {"name": "Complaint, refund and warranty remedy", "status": "enabled", "owner": "Customer + Provider",
                     "source": "Warranty evidence and provider remedy flow",
                     "runtime_behaviour": "The provider reviews the technician's ground work and resolves the case directly with the customer. Admin does not adjudicate; an SLA breach posts the configured tenant Usage Credit penalty."},
                ]},
                {"name": "Finance", "capabilities": [
                    {"name": "Usage Credits", "status": "enabled", "owner": "Platform",
                     "source": "Home Services Finance",
                     "action_href": "/admin/home-services/finance",
                     "action_label": "Open finance",
                     "runtime_behaviour": "Provider platform charges use the immutable credit ledger."},
                    {"name": "Job-type monetization rules", "status": "enabled", "owner": "Admin",
                     "source": "Monetization policy",
                     "action_href": "/admin/home-services/finance?tab=monetization",
                     "action_label": "Manage monetization",
                     "runtime_behaviour": "Commission and completion-credit rules are configured once in Home Services Finance and resolved per job type."},
                ]},
            ],
            "policy_boundaries": [
                {"policy": "Business profile changes after activation", "owner": "Admin approval required"},
                {"policy": "Business name changes", "owner": "Admin approval + document reverification"},
                {"policy": "Service prices and visit fees", "owner": "Tenant-owned"},
                {"policy": "Commission and completion-credit rules", "owner": "Admin-controlled"},
                {"policy": "Warranty minimum", "owner": "Admin policy; provider can only extend"},
                {"policy": "Complaint, refund and warranty resolution", "owner": "Customer and provider; no Admin adjudication"},
            ],
        }

    async def get_dependency_health(self, db: AsyncSession, key: str) -> dict:
        """Project configured engine mappings and their latest persisted checks."""
        v = await self._by_key(db, key)
        if not v:
            raise ValueError(f"Vertical '{key}' not found")
        mappings = (await db.execute(
            select(VerticalEngineMapping).where(VerticalEngineMapping.vertical_id == v.id)
            .order_by(VerticalEngineMapping.sort_order)
        )).scalars().all()
        from app.engines.engine_mgmt.models import PlatformEngine, EngineHealthCheck
        checks = []
        for mapping in mappings:
            engine = (await db.execute(
                select(PlatformEngine).where(PlatformEngine.engine_key == mapping.engine_key)
            )).scalar_one_or_none()
            latest = None
            if engine:
                latest = (await db.execute(
                    select(EngineHealthCheck).where(EngineHealthCheck.engine_id == engine.id)
                    .order_by(EngineHealthCheck.checked_at.desc()).limit(1)
                )).scalar_one_or_none()
            status = "unverified"
            if latest:
                status = "healthy" if latest.health_status in ("healthy", "ok", "up") else "unhealthy"
            # "locked" means core configuration is protected from admin
            # mutation; it is not an outage. Only a genuinely unavailable
            # registry state is unhealthy without a persisted health check.
            elif engine and engine.global_status not in ("enabled", "locked"):
                status = "unhealthy"
            checks.append({
                "engine_key": mapping.engine_key,
                "required": mapping.is_required,
                "status": status,
                "last_checked_at": latest.checked_at.isoformat() if latest and latest.checked_at else None,
            })
        if not mappings:
            checks.append({
                "engine_key": "vertical_engine_mappings",
                "required": True,
                "status": "unverified",
                "last_checked_at": None,
                "detail": "No persisted engine dependency mappings are configured for this vertical.",
            })
        healthy = sum(1 for check in checks if check["status"] == "healthy")
        return {"vertical_key": key, "checks": checks, "healthy_count": healthy, "total_count": len(checks)}

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
        if new_status in ("approved_pending_activation", "rejected", "changes_requested") and (
            not row.submitted_at or row.status in ("draft", "draft_setup")
        ):
            from app.exceptions import ServiceOSException
            raise ServiceOSException("PROVIDER_NOT_SUBMITTED", "Provider must submit setup before an Admin review decision.", status_code=409)
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
        # The caller owns the transaction: review, documents and activation
        # must either all succeed or all roll back together.
        await db.flush()
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

        # Step 3 only validates service configuration. Now that coverage and
        # hours exist, run full publication in the SAME review transaction.
        # A direct submit request must not hand unbookable drafts to Admin.
        if vertical_key == "home_services":
            from app.engines.admin_catalog.models import TenantService
            from app.engines.admin_catalog.tenant_service import TenantCatalogService
            offerings = (await db.execute(select(TenantService).where(
                TenantService.tenant_id == uuid.UUID(str(tenant_id)),
                TenantService.is_enabled.is_(True), TenantService.is_active.is_(True),
                TenantService.deleted_at.is_(None),
            ))).scalars().all()
            catalog = TenantCatalogService(db, actor_tenant_id=uuid.UUID(str(tenant_id)))
            for offering in offerings:
                await catalog.publish_service(offering.id)

        # The legacy Admin onboarding workspace is intentionally retained,
        # but it reads Tenant.verification_status. Keep it synchronized with
        # the canonical vertical enrollment in the same request transaction.
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

    async def toggle_module(
        self, db: AsyncSession, vertical_key: str, module_key: str, enabled: bool,
        *, actor_id=None, reason: str | None = None,
    ) -> dict:
        v = await self._by_key(db, vertical_key)
        if not v:
            raise ValueError(f"Vertical '{vertical_key}' not found")
        m = await self._module_by_key(db, module_key)
        if not m:
            raise ValueError(f"Module '{module_key}' not found")

        if m.navigation_status != "available":
            raise ValueError(
                f"Module '{module_key}' cannot be enabled because its admin navigation status is "
                f"'{m.navigation_status}'"
            )

        vcm = (await db.execute(
            select(VerticalCatalogModule).where(
                VerticalCatalogModule.vertical_id == v.id,
                VerticalCatalogModule.module_id == m.id,
            )
        )).scalar_one_or_none()

        if not vcm:
            # A module assignment is a curated vertical-to-screen contract,
            # not a generic feature flag.  Silently creating one allowed an
            # unrelated vertical to expose another vertical's admin page.
            raise ValueError(f"Module '{module_key}' is not assigned to vertical '{vertical_key}'")
        if vcm.is_required and not enabled:
            raise ValueError(f"Module '{module_key}' is required for this vertical and cannot be disabled")
        if vcm.is_enabled == enabled:
            return {
                "vertical_key": vertical_key, "module_key": module_key,
                "is_enabled": enabled, "status": "no_change",
            }

        before = {"module_key": module_key, "is_enabled": vcm.is_enabled}
        vcm.is_enabled = enabled
        db.add(VerticalAuditLog(
            vertical_id=v.id,
            actor_id=actor_id,
            action_type="vertical.navigation_module.enable" if enabled else "vertical.navigation_module.disable",
            before_state=before,
            after_state={"module_key": module_key, "is_enabled": enabled},
            notes=(reason or f"{('Enabled' if enabled else 'Disabled')} {m.label} in the admin navigation").strip(),
        ))

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
        # Home-Services-only usage-credit finance concept. Customer service
        # payments still go directly to the provider.
        "usage_credits": {"home_services"},
    }

    async def get_effective_menu(self, db: AsyncSession) -> dict:
        """Returns the full sidebar menu config: universal modules + per-vertical enabled
        modules + cross-vertical "operation visibility" flags (Jobs/Site Visits/Orders/
        Leads CRM/Appointments/Finance items that must not show for every vertical)."""
        verticals = await self.list_verticals(db, include_disabled=True)
        modules = await self.list_modules(db)
        universal = [m for m in modules if m["is_universal"] and m["navigation_status"] == "available"]

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
                "modules": [
                    m for m in mods
                    if m["is_enabled"] and m["navigation_status"] == "available"
                ],
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
                cmd.id, cmd.key, cmd.label, cmd.description, cmd.icon, cmd.admin_path, cmd.module_group,
                cmd.is_universal, cmd.sort_order, cmd.navigation_status, cmd.navigation_status_reason,
                vcm.is_enabled, vcm.is_required, vcm.custom_label
            FROM vertical_catalog_modules vcm
            JOIN catalog_module_definitions cmd ON cmd.id = vcm.module_id
            WHERE vcm.vertical_id = :vid
            ORDER BY vcm.sort_order
        """), {"vid": str(vertical_id)})).fetchall()
        return [
            {
                "key": r.key,
                "id": str(r.id),
                "label": r.custom_label or r.label,
                "description": r.description,
                "icon": r.icon,
                "admin_path": r.admin_path,
                "module_group": r.module_group,
                "is_universal": r.is_universal,
                "is_enabled": r.is_enabled,
                "is_required": r.is_required,
                "sort_order": r.sort_order,
                "navigation_status": r.navigation_status,
                "navigation_status_reason": r.navigation_status_reason,
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
            "release_stage": v.release_stage,
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
            "description": m.description,
            "icon": m.icon,
            "admin_path": m.admin_path,
            "module_group": m.module_group,
            "is_universal": m.is_universal,
            "sort_order": m.sort_order,
            "navigation_status": m.navigation_status,
            "navigation_status_reason": m.navigation_status_reason,
        }
