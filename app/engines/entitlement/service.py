"""FINAL-L5-04B — Entitlement Domain Service.

Single canonical place for tenant module/category entitlement resolution
and mutation logic. No router should query tenant_module_entitlements /
tenant_category_entitlements directly — everything routes through here so
effective-date logic, status logic, and tenant isolation stay centralized.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import or_, select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.admin_catalog.models import ServiceGroup, ServiceCategory
from app.engines.entitlement.models import (
    EntitlementAuditLog,
    TenantCategoryEntitlement,
    TenantModuleEntitlement,
)
from app.engines.vertical_catalog.models import Vertical


class EntitlementConflictError(Exception):
    """Raised when a mutation would create a duplicate active row or invalid parent/child relationship."""


class EntitlementNotFoundError(Exception):
    pass


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _is_effective(row) -> bool:
    """Status ACTIVE alone isn't enough — effective_from/effective_until must also hold."""
    if row.status != "ACTIVE":
        return False
    now = _now()
    if row.effective_from and row.effective_from > now:
        return False
    if row.effective_until and row.effective_until < now:
        return False
    return True


class EntitlementService:

    # ── Reads ────────────────────────────────────────────────────────────────

    async def get_tenant_modules(self, db: AsyncSession, tenant_id: uuid.UUID, *, effective_only: bool = True) -> list[dict]:
        q = select(TenantModuleEntitlement, Vertical).join(
            Vertical, Vertical.id == TenantModuleEntitlement.module_id
        ).where(TenantModuleEntitlement.tenant_id == tenant_id)
        rows = (await db.execute(q)).all()
        out = []
        for ent, vertical in rows:
            if effective_only and not _is_effective(ent):
                continue
            out.append(self._module_dict(ent, vertical))
        return out

    async def get_tenant_categories(self, db: AsyncSession, tenant_id: uuid.UUID, *, module_id: uuid.UUID | None = None, effective_only: bool = True) -> list[dict]:
        q = select(TenantCategoryEntitlement, ServiceGroup).join(
            ServiceGroup, ServiceGroup.id == TenantCategoryEntitlement.category_id
        ).where(TenantCategoryEntitlement.tenant_id == tenant_id)
        if module_id:
            q = q.join(TenantModuleEntitlement, TenantModuleEntitlement.id == TenantCategoryEntitlement.module_entitlement_id).where(
                TenantModuleEntitlement.module_id == module_id
            )
        rows = (await db.execute(q)).all()
        out = []
        for ent, group in rows:
            if effective_only and not _is_effective(ent):
                continue
            out.append(self._category_dict(ent, group))
        return out

    async def has_module_entitlement(self, db: AsyncSession, tenant_id: uuid.UUID, module_key: str) -> bool:
        v = (await db.execute(select(Vertical).where(Vertical.key == module_key))).scalar_one_or_none()
        if not v:
            return False
        row = (await db.execute(
            select(TenantModuleEntitlement).where(
                TenantModuleEntitlement.tenant_id == tenant_id,
                TenantModuleEntitlement.module_id == v.id,
                TenantModuleEntitlement.status == "ACTIVE",
            )
        )).scalar_one_or_none()
        return bool(row) and _is_effective(row)

    async def has_category_entitlement(self, db: AsyncSession, tenant_id: uuid.UUID, category_id: uuid.UUID) -> bool:
        """Single-tenant convenience wrapper — for per-request checks (e.g. a
        mutation guard). For matching/candidate-list contexts, use
        get_entitled_tenant_ids_for_category() instead to avoid N+1 queries."""
        entitled = await self.get_entitled_tenant_ids_for_category(db, category_id, tenant_ids=[tenant_id])
        return tenant_id in entitled

    async def ensure_registration_category_access(
        self, db: AsyncSession, *, tenant_id: uuid.UUID, category_id: uuid.UUID,
        actor_id: uuid.UUID | None = None, actor_role: str | None = None,
        request_id: str | None = None,
    ) -> bool:
        """Fill an absent signup grant on an explicit service-enable request.

        Home Services registration already includes its active service groups.
        Older registrations and groups added after signup can lack these rows.
        Repair only missing rows, never an explicit inactive/expired grant.
        Persist the canonical grants so matching and confirmation agree. Seats,
        provider approval and service publication remain independent gates.
        The caller owns the transaction; no partial setup is committed here.
        """
        from app.engines.tenant_engine.models import Tenant
        from app.engines.public_registration.models import PendingTenantRegistration
        from app.engines.vertical_catalog.models import TenantVerticalEnrollment

        # Serialize concurrent clicks for this tenant, including two groups.
        tenant = (await db.execute(select(Tenant).where(Tenant.id == tenant_id)
                                  .with_for_update())).scalar_one_or_none()
        if not tenant or tenant.status not in {'onboarding_pending', 'under_review', 'awaiting_documents', 'active', 'trial', 'pending_activation'}:
            return False
        if await self.has_category_entitlement(db, tenant_id, category_id):
            return True
        group = await db.get(ServiceGroup, category_id)
        if not group or group.status != 'active' or group.deleted_at:
            return False
        category = await db.get(ServiceCategory, group.category_id)
        if not category or not category.is_active or (category.vertical_type or category.category_type) != 'home_services':
            return False
        vertical = (await db.execute(select(Vertical).where(Vertical.key == 'home_services'))).scalar_one_or_none()
        if not vertical or not vertical.is_enabled:
            return False
        # Any existing category decision wins, including suspended/expired and
        # future-dated rows. Never turn a denied entitlement back on implicitly.
        category_row = (await db.execute(select(TenantCategoryEntitlement).where(
            TenantCategoryEntitlement.tenant_id == tenant_id,
            TenantCategoryEntitlement.category_id == category_id).limit(1))).scalar_one_or_none()
        if category_row is not None:
            return False
        module = (await db.execute(select(TenantModuleEntitlement).where(
            TenantModuleEntitlement.tenant_id == tenant_id,
            TenantModuleEntitlement.module_id == vertical.id)
            .order_by(TenantModuleEntitlement.created_at.desc()).limit(1))).scalar_one_or_none()
        if module is not None and not _is_effective(module):
            return False
        enrollment = (await db.execute(select(TenantVerticalEnrollment).where(
            TenantVerticalEnrollment.tenant_id == tenant_id,
            TenantVerticalEnrollment.vertical_id == vertical.id))).scalar_one_or_none()
        if not enrollment or enrollment.status not in {
            'draft_setup', 'draft', 'submitted', 'under_review', 'changes_requested',
            'approved', 'approved_pending_activation', 'activation_requirements_pending', 'activating', 'active',
        }:
            return False
        policy_grant = module is not None and (module.configuration or {}).get('grant_policy') == 'active_vertical_service_groups'
        if not policy_grant:
            # A bare enrollment is not proof of entitlement: old self-signups
            # must be backed by an actual completed registration in this vertical.
            registration = (await db.execute(select(PendingTenantRegistration.id).where(
                PendingTenantRegistration.created_tenant_id == tenant_id,
                PendingTenantRegistration.status == 'completed',
                PendingTenantRegistration.selected_vertical_key == 'home_services',
            ).limit(1))).scalar_one_or_none()
            if registration is None or (module is not None and module.source != 'tenant_registration'):
                return False
        if module is None:
            await self.assign_module_entitlement(db, tenant_id=tenant_id, module_key='home_services',
                actor_id=actor_id, actor_role=actor_role, request_id=request_id,
                source='tenant_registration', configuration={'grant_policy':'active_vertical_service_groups'}, commit=False)
        await self.assign_category_entitlement(db, tenant_id=tenant_id, category_id=category_id,
            actor_id=actor_id, actor_role=actor_role, request_id=request_id,
            source='tenant_registration', configuration={'grant_policy':'active_vertical_service_groups'}, commit=False)
        return await self.has_category_entitlement(db, tenant_id, category_id)

    async def get_entitled_tenant_ids_for_category(
        self, db: AsyncSession, category_id: uuid.UUID, *, tenant_ids: list[uuid.UUID] | None = None,
    ) -> set[uuid.UUID]:
        """FINAL-L5-04C — canonical, bulk-safe effective-entitlement resolver.

        Returns the subset of `tenant_ids` (or, if None, ALL tenants) that
        currently hold an effective category entitlement for `category_id`,
        in a single query — this is the function matching/candidate-list
        code must use instead of calling has_category_entitlement() once
        per candidate (a real N+1 pattern that would not scale).

        "Effective" requires all 8 mission conditions:
          1. row exists, 2. status ACTIVE, 3. effective_from passed,
          4. effective_until not passed, 5. parent module entitlement is
          itself effective (ACTIVE + its own effective window), 6. the
          global module (verticals.is_enabled) is active, 7. the global
          category (service_categories.is_active) is active, 8. the
          category belongs to the correct module (enforced structurally —
          the join chain below only reaches a module via the category's
          own real parent, so a mismatched module can never match).
        """
        now = _now()
        q = (
            select(TenantCategoryEntitlement.tenant_id)
            .join(TenantModuleEntitlement, TenantModuleEntitlement.id == TenantCategoryEntitlement.module_entitlement_id)
            .join(ServiceGroup, ServiceGroup.id == TenantCategoryEntitlement.category_id)
            .join(ServiceCategory, ServiceCategory.id == ServiceGroup.category_id)
            .join(Vertical, Vertical.id == TenantModuleEntitlement.module_id)
            .where(
                TenantCategoryEntitlement.category_id == category_id,
                TenantModuleEntitlement.tenant_id == TenantCategoryEntitlement.tenant_id,
                Vertical.key == func.coalesce(func.nullif(ServiceCategory.vertical_type, ''), ServiceCategory.category_type),
                TenantCategoryEntitlement.status == "ACTIVE",
                TenantModuleEntitlement.status == "ACTIVE",
                Vertical.is_enabled.is_(True),
                ServiceCategory.is_active.is_(True),
                ServiceGroup.status == 'active',
                ServiceGroup.deleted_at.is_(None),
                (TenantCategoryEntitlement.effective_from.is_(None)) | (TenantCategoryEntitlement.effective_from <= now),
                (TenantCategoryEntitlement.effective_until.is_(None)) | (TenantCategoryEntitlement.effective_until >= now),
                (TenantModuleEntitlement.effective_from.is_(None)) | (TenantModuleEntitlement.effective_from <= now),
                (TenantModuleEntitlement.effective_until.is_(None)) | (TenantModuleEntitlement.effective_until >= now),
            )
        )
        if tenant_ids is not None:
            if not tenant_ids:
                return set()
            q = q.where(TenantCategoryEntitlement.tenant_id.in_(tenant_ids))
        rows = (await db.execute(q)).scalars().all()
        return set(rows)

    async def get_category_entitlement_exclusion_reason(
        self, db: AsyncSession, tenant_id: uuid.UUID, category_id: uuid.UUID,
    ) -> str | None:
        """Diagnostic-only — returns a specific reason code for why a tenant
        is NOT effectively entitled, for matching-diagnostics surfaces. Not
        used in the hot bulk-candidate path (that uses the set-based bulk
        resolver above); intended for single-tenant admin/debug lookups."""
        row = (await db.execute(
            select(TenantCategoryEntitlement).where(
                TenantCategoryEntitlement.tenant_id == tenant_id,
                TenantCategoryEntitlement.category_id == category_id,
            ).order_by(TenantCategoryEntitlement.created_at.desc())
        )).scalars().first()
        if not row:
            return "TENANT_CATEGORY_NOT_ENTITLED"
        if row.status != "ACTIVE":
            return "ENTITLEMENT_INACTIVE"
        if not _is_effective(row):
            return "ENTITLEMENT_EXPIRED"
        module_row = (await db.execute(
            select(TenantModuleEntitlement).where(TenantModuleEntitlement.id == row.module_entitlement_id)
        )).scalar_one_or_none()
        if not module_row or module_row.tenant_id != tenant_id or module_row.status != "ACTIVE" or not _is_effective(module_row):
            return "TENANT_MODULE_NOT_ENTITLED"
        group = (await db.execute(select(ServiceGroup).where(ServiceGroup.id == category_id))).scalar_one_or_none()
        vertical = (await db.execute(select(Vertical).where(Vertical.id == module_row.module_id))).scalar_one_or_none()
        if not vertical or not vertical.is_enabled:
            return "GLOBAL_MODULE_INACTIVE"
        if not group or group.status != 'active' or group.deleted_at:
            return "GLOBAL_CATEGORY_INACTIVE"
        if group:
            cat = (await db.execute(select(ServiceCategory).where(ServiceCategory.id == group.category_id))).scalar_one_or_none()
            if not cat or not cat.is_active:
                return "GLOBAL_CATEGORY_INACTIVE"
            if (cat.vertical_type or cat.category_type) != vertical.key:
                return "TENANT_MODULE_NOT_ENTITLED"
        return None

    async def resolve_effective_entitlements(self, db: AsyncSession, tenant_id: uuid.UUID, *, effective_only: bool = True) -> dict[str, Any]:
        modules = await self.get_tenant_modules(db, tenant_id, effective_only=effective_only)
        categories = await self.get_tenant_categories(db, tenant_id, effective_only=effective_only)
        return {"modules": modules, "categories": categories}

    async def get_history(self, db: AsyncSession, tenant_id: uuid.UUID) -> list[dict]:
        q = select(EntitlementAuditLog).where(EntitlementAuditLog.tenant_id == tenant_id).order_by(EntitlementAuditLog.created_at.desc())
        rows = (await db.execute(q)).scalars().all()
        return [self._audit_dict(r) for r in rows]

    # ── Mutations ────────────────────────────────────────────────────────────

    async def assign_module_entitlement(
        self, db: AsyncSession, *, tenant_id: uuid.UUID, module_key: str,
        actor_id: uuid.UUID | None, actor_role: str | None, source: str = "admin_manual",
        request_id: str | None = None, configuration: dict | None = None,
        commit: bool = True,
    ) -> dict:
        v = (await db.execute(select(Vertical).where(Vertical.key == module_key))).scalar_one_or_none()
        if not v:
            raise EntitlementNotFoundError(f"module '{module_key}' not found")

        existing = (await db.execute(
            select(TenantModuleEntitlement).where(
                TenantModuleEntitlement.tenant_id == tenant_id,
                TenantModuleEntitlement.module_id == v.id,
                TenantModuleEntitlement.status == "ACTIVE",
            )
        )).scalar_one_or_none()
        if existing:
            # idempotent success — re-assigning an already-active entitlement is a no-op, not an error
            return self._module_dict(existing, v)

        ent = TenantModuleEntitlement(
            tenant_id=tenant_id, module_id=v.id, status="ACTIVE", source=source,
            configuration=configuration, enabled_at=_now(), created_by=actor_id, updated_by=actor_id,
        )
        db.add(ent)
        await db.flush()
        await self._audit(db, tenant_id=tenant_id, entity_type="module", entity_id=ent.id,
                           event="MODULE_ENTITLEMENT_ASSIGNED", previous_status=None, new_status="ACTIVE",
                           actor_id=actor_id, actor_role=actor_role, source=source, request_id=request_id)
        if commit:
            await db.commit()
        return self._module_dict(ent, v)

    async def grant_registration_defaults(
        self, db: AsyncSession, *, tenant_id: uuid.UUID, module_key: str,
        actor_id: uuid.UUID | None, actor_role: str | None,
        request_id: str | None = None, commit: bool = True,
    ) -> dict[str, Any]:
        """Grant the active catalog selected during public registration.

        A vertical enrollment tracks onboarding state, but service enablement
        and matching intentionally enforce the separate entitlement tables.
        New registrations therefore receive the selected module and its active
        service groups. Admin can still disable either level through the
        existing audited control plane. ``commit=False`` keeps signup atomic.
        """
        module = await self.assign_module_entitlement(
            db,
            tenant_id=tenant_id,
            module_key=module_key,
            actor_id=actor_id,
            actor_role=actor_role,
            source="tenant_registration",
            request_id=request_id,
            configuration={"grant_policy": "active_vertical_service_groups"},
            commit=False,
        )
        groups = (await db.execute(
            select(ServiceGroup)
            .join(ServiceCategory, ServiceCategory.id == ServiceGroup.category_id)
            .where(
                ServiceCategory.is_active.is_(True),
                or_(
                    ServiceCategory.vertical_type == module_key,
                    ServiceCategory.category_type == module_key,
                ),
                ServiceGroup.status == "active",
                ServiceGroup.deleted_at.is_(None),
            )
            .order_by(ServiceGroup.display_order, ServiceGroup.name)
        )).scalars().all()

        categories = []
        for group in groups:
            categories.append(await self.assign_category_entitlement(
                db,
                tenant_id=tenant_id,
                category_id=group.id,
                actor_id=actor_id,
                actor_role=actor_role,
                source="tenant_registration",
                request_id=request_id,
                configuration={"grant_policy": "active_vertical_service_groups"},
                commit=False,
            ))
        if commit:
            await db.commit()
        return {"module": module, "categories": categories}

    async def disable_module_entitlement(
        self, db: AsyncSession, *, tenant_id: uuid.UUID, module_key: str,
        actor_id: uuid.UUID | None, actor_role: str | None, reason: str | None = None, request_id: str | None = None,
        cascade_categories: bool = True,
    ) -> dict:
        v = (await db.execute(select(Vertical).where(Vertical.key == module_key))).scalar_one_or_none()
        if not v:
            raise EntitlementNotFoundError(f"module '{module_key}' not found")
        ent = (await db.execute(
            select(TenantModuleEntitlement).where(
                TenantModuleEntitlement.tenant_id == tenant_id,
                TenantModuleEntitlement.module_id == v.id,
                TenantModuleEntitlement.status == "ACTIVE",
            )
        )).scalar_one_or_none()
        if not ent:
            raise EntitlementNotFoundError(f"no active entitlement for module '{module_key}'")

        prev = ent.status
        ent.status = "INACTIVE"
        ent.disabled_at = _now()
        ent.updated_by = actor_id
        ent.version += 1
        await self._audit(db, tenant_id=tenant_id, entity_type="module", entity_id=ent.id,
                           event="MODULE_ENTITLEMENT_DISABLED", previous_status=prev, new_status="INACTIVE",
                           actor_id=actor_id, actor_role=actor_role, reason=reason, request_id=request_id)

        # CASCADE_STATUS_UPDATE policy (see MODULE_DISABLE_CASCADE_POLICY.md):
        # child category rows become ineffective but are not deleted, and their
        # own status is left untouched so a module re-enable restores them
        # without needing to remember/re-derive prior category state.
        if cascade_categories:
            cat_rows = (await db.execute(
                select(TenantCategoryEntitlement).where(
                    TenantCategoryEntitlement.module_entitlement_id == ent.id,
                    TenantCategoryEntitlement.status == "ACTIVE",
                )
            )).scalars().all()
            for cat in cat_rows:
                await self._audit(db, tenant_id=tenant_id, entity_type="category", entity_id=cat.id,
                                   event="CATEGORY_ENTITLEMENT_CASCADED_INEFFECTIVE", previous_status="ACTIVE",
                                   new_status="ACTIVE", actor_id=actor_id, actor_role=actor_role,
                                   reason="row status unchanged; ineffective while parent module is INACTIVE",
                                   request_id=request_id)

        await db.commit()
        return self._module_dict(ent, v)

    async def reenable_module_entitlement(
        self, db: AsyncSession, *, tenant_id: uuid.UUID, module_key: str,
        actor_id: uuid.UUID | None, actor_role: str | None, request_id: str | None = None,
    ) -> dict:
        v = (await db.execute(select(Vertical).where(Vertical.key == module_key))).scalar_one_or_none()
        if not v:
            raise EntitlementNotFoundError(f"module '{module_key}' not found")
        ent = (await db.execute(
            select(TenantModuleEntitlement).where(
                TenantModuleEntitlement.tenant_id == tenant_id,
                TenantModuleEntitlement.module_id == v.id,
            ).order_by(TenantModuleEntitlement.created_at.desc())
        )).scalars().first()
        if not ent:
            raise EntitlementNotFoundError(f"no entitlement row for module '{module_key}'")

        prev = ent.status
        ent.status = "ACTIVE"
        ent.disabled_at = None
        ent.enabled_at = _now()
        ent.updated_by = actor_id
        ent.version += 1
        await self._audit(db, tenant_id=tenant_id, entity_type="module", entity_id=ent.id,
                           event="MODULE_ENTITLEMENT_REENABLED", previous_status=prev, new_status="ACTIVE",
                           actor_id=actor_id, actor_role=actor_role, request_id=request_id)
        await db.commit()
        return self._module_dict(ent, v)

    async def assign_category_entitlement(
        self, db: AsyncSession, *, tenant_id: uuid.UUID, category_id: uuid.UUID,
        actor_id: uuid.UUID | None, actor_role: str | None, source: str = "admin_manual",
        request_id: str | None = None, configuration: dict | None = None,
        commit: bool = True,
    ) -> dict:
        group = (await db.execute(select(ServiceGroup).where(ServiceGroup.id == category_id))).scalar_one_or_none()
        if not group:
            raise EntitlementNotFoundError(f"category '{category_id}' not found")

        # Category must belong to a module the tenant already has an ACTIVE
        # entitlement for — resolved via the parent service_category's
        # vertical_type/category_type string match against verticals.key
        # (see the data model report for why this is a string match, not an FK:
        # service_categories has no vertical_id column in this codebase).
        parent_category = (await db.execute(select(ServiceCategory).where(ServiceCategory.id == group.category_id))).scalar_one_or_none()
        vertical_key = (parent_category.vertical_type or parent_category.category_type) if parent_category else None
        if not vertical_key:
            raise EntitlementConflictError(f"category '{category_id}' has no resolvable parent module/vertical")

        v = (await db.execute(select(Vertical).where(Vertical.key == vertical_key))).scalar_one_or_none()
        if not v:
            raise EntitlementConflictError(f"category '{category_id}' parent vertical '{vertical_key}' does not exist")

        module_ent = (await db.execute(
            select(TenantModuleEntitlement).where(
                TenantModuleEntitlement.tenant_id == tenant_id,
                TenantModuleEntitlement.module_id == v.id,
                TenantModuleEntitlement.status == "ACTIVE",
            )
        )).scalar_one_or_none()
        if not module_ent:
            raise EntitlementConflictError(f"tenant has no active module entitlement for '{vertical_key}'; assign the module first")

        existing = (await db.execute(
            select(TenantCategoryEntitlement).where(
                TenantCategoryEntitlement.tenant_id == tenant_id,
                TenantCategoryEntitlement.category_id == category_id,
                TenantCategoryEntitlement.status == "ACTIVE",
            )
        )).scalar_one_or_none()
        if existing:
            return self._category_dict(existing, group)

        ent = TenantCategoryEntitlement(
            tenant_id=tenant_id, category_id=category_id, module_entitlement_id=module_ent.id,
            status="ACTIVE", source=source, configuration=configuration, enabled_at=_now(),
            created_by=actor_id, updated_by=actor_id,
        )
        db.add(ent)
        await db.flush()
        await self._audit(db, tenant_id=tenant_id, entity_type="category", entity_id=ent.id,
                           event="CATEGORY_ENTITLEMENT_ASSIGNED", previous_status=None, new_status="ACTIVE",
                           actor_id=actor_id, actor_role=actor_role, source=source, request_id=request_id)
        if commit:
            await db.commit()
        return self._category_dict(ent, group)

    async def disable_category_entitlement(
        self, db: AsyncSession, *, tenant_id: uuid.UUID, category_id: uuid.UUID,
        actor_id: uuid.UUID | None, actor_role: str | None, reason: str | None = None, request_id: str | None = None,
    ) -> dict:
        ent = (await db.execute(
            select(TenantCategoryEntitlement).where(
                TenantCategoryEntitlement.tenant_id == tenant_id,
                TenantCategoryEntitlement.category_id == category_id,
                TenantCategoryEntitlement.status == "ACTIVE",
            )
        )).scalar_one_or_none()
        if not ent:
            raise EntitlementNotFoundError(f"no active entitlement for category '{category_id}'")
        group = (await db.execute(select(ServiceGroup).where(ServiceGroup.id == category_id))).scalar_one_or_none()

        prev = ent.status
        ent.status = "INACTIVE"
        ent.disabled_at = _now()
        ent.updated_by = actor_id
        ent.version += 1
        await self._audit(db, tenant_id=tenant_id, entity_type="category", entity_id=ent.id,
                           event="CATEGORY_ENTITLEMENT_DISABLED", previous_status=prev, new_status="INACTIVE",
                           actor_id=actor_id, actor_role=actor_role, reason=reason, request_id=request_id)
        await db.commit()
        return self._category_dict(ent, group)

    async def reenable_category_entitlement(
        self, db: AsyncSession, *, tenant_id: uuid.UUID, category_id: uuid.UUID,
        actor_id: uuid.UUID | None, actor_role: str | None, request_id: str | None = None,
    ) -> dict:
        ent = (await db.execute(
            select(TenantCategoryEntitlement).where(
                TenantCategoryEntitlement.tenant_id == tenant_id,
                TenantCategoryEntitlement.category_id == category_id,
            ).order_by(TenantCategoryEntitlement.created_at.desc())
        )).scalars().first()
        if not ent:
            raise EntitlementNotFoundError(f"no entitlement row for category '{category_id}'")

        module_ent = (await db.execute(
            select(TenantModuleEntitlement).where(TenantModuleEntitlement.id == ent.module_entitlement_id)
        )).scalar_one_or_none()
        if not module_ent or module_ent.status != "ACTIVE":
            raise EntitlementConflictError("cannot re-enable a category whose parent module entitlement is not ACTIVE")

        group = (await db.execute(select(ServiceGroup).where(ServiceGroup.id == category_id))).scalar_one_or_none()
        prev = ent.status
        ent.status = "ACTIVE"
        ent.disabled_at = None
        ent.enabled_at = _now()
        ent.updated_by = actor_id
        ent.version += 1
        await self._audit(db, tenant_id=tenant_id, entity_type="category", entity_id=ent.id,
                           event="CATEGORY_ENTITLEMENT_REENABLED", previous_status=prev, new_status="ACTIVE",
                           actor_id=actor_id, actor_role=actor_role, request_id=request_id)
        await db.commit()
        return self._category_dict(ent, group)

    # ── Internal helpers ─────────────────────────────────────────────────────

    async def _audit(self, db: AsyncSession, **kwargs) -> None:
        db.add(EntitlementAuditLog(**kwargs))
        await db.flush()

    def _module_dict(self, ent: TenantModuleEntitlement, vertical: Vertical) -> dict:
        return {
            "id": str(ent.id), "tenant_id": str(ent.tenant_id),
            "module_id": str(vertical.id), "module_key": vertical.key, "module_label": vertical.label,
            "status": ent.status, "source": ent.source, "configuration": ent.configuration,
            "enabled_at": ent.enabled_at.isoformat() if ent.enabled_at else None,
            "disabled_at": ent.disabled_at.isoformat() if ent.disabled_at else None,
            "effective_from": ent.effective_from.isoformat() if ent.effective_from else None,
            "effective_until": ent.effective_until.isoformat() if ent.effective_until else None,
            "version": ent.version, "created_at": ent.created_at.isoformat(), "updated_at": ent.updated_at.isoformat(),
        }

    def _category_dict(self, ent: TenantCategoryEntitlement, group: ServiceGroup | None) -> dict:
        return {
            "id": str(ent.id), "tenant_id": str(ent.tenant_id),
            "category_id": str(ent.category_id), "category_slug": group.code if group else None,
            "category_label": group.name if group else None,
            "module_entitlement_id": str(ent.module_entitlement_id),
            "status": ent.status, "source": ent.source, "configuration": ent.configuration,
            "enabled_at": ent.enabled_at.isoformat() if ent.enabled_at else None,
            "disabled_at": ent.disabled_at.isoformat() if ent.disabled_at else None,
            "effective_from": ent.effective_from.isoformat() if ent.effective_from else None,
            "effective_until": ent.effective_until.isoformat() if ent.effective_until else None,
            "version": ent.version, "created_at": ent.created_at.isoformat(), "updated_at": ent.updated_at.isoformat(),
        }

    def _audit_dict(self, row: EntitlementAuditLog) -> dict:
        return {
            "id": str(row.id), "tenant_id": str(row.tenant_id), "entity_type": row.entity_type,
            "entity_id": str(row.entity_id), "event": row.event,
            "previous_status": row.previous_status, "new_status": row.new_status,
            "actor_id": str(row.actor_id) if row.actor_id else None, "actor_role": row.actor_role,
            "reason": row.reason, "source": row.source, "request_id": row.request_id,
            "created_at": row.created_at.isoformat(),
        }


entitlement_service = EntitlementService()
