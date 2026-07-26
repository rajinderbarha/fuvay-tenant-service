"""Admin Catalog — Tenant Service Enablement.

Tenants enable master services from the admin catalog.
Tenant cannot change job_type, cannot price below admin min, cannot select
unsupported brands/types.
"""
from __future__ import annotations
import uuid
from decimal import Decimal
from datetime import datetime, timezone

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.admin_catalog.models import (
    MasterService, ServiceCategory, ServicePricingRule,
    TenantService, TenantServiceType, TenantServiceBrand,
    MasterServiceType, MasterServiceBrand, ServiceType, Brand,
    ServiceBlueprintVersion,
)
from app.engines.admin_catalog.bargain_engine import (
    compute_symmetric_customer_price_tiers, BargainValidationError,
)
from app.engines.serviceability.models import TenantServiceArea
from app.engines.entitlement.service import entitlement_service
from app.exceptions import ServiceOSException, NotFoundException

utcnow = lambda: datetime.now(timezone.utc)


class TenantCatalogService:
    def __init__(self, db: AsyncSession, request_id: str = "—",
                 actor_id: uuid.UUID | None = None,
                 actor_role: str | None = None,
                 actor_tenant_id: uuid.UUID | None = None):
        self.db = db
        self.request_id = request_id
        self.actor_id = actor_id
        self.actor_role = actor_role
        self.actor_tenant_id = actor_tenant_id

    def _require_tenant_id(self, tenant_id_raw) -> uuid.UUID:
        # Slice 2F-8: enable_service/disable_service accept an optional
        # `tenant_id` query parameter (originally intended to let a platform
        # role act on a specific tenant's behalf), but this method previously
        # used ANY supplied tenant_id_raw unconditionally -- a tenant_owner
        # (who legitimately holds TENANT_UPDATE) could pass a foreign
        # tenant_id and enable/disable a service for a tenant they do not
        # belong to. Mirrors the FINAL-L5-05Q pattern already used in
        # serviceability's admin router: a non-platform actor's supplied
        # tenant_id must match their own actor_tenant_id, or the request is
        # rejected outright.
        if tenant_id_raw:
            candidate = tenant_id_raw if isinstance(tenant_id_raw, uuid.UUID) else uuid.UUID(str(tenant_id_raw))
            if (self.actor_role not in self.PLATFORM_ROLES
                    and self.actor_tenant_id is not None
                    and candidate != self.actor_tenant_id):
                raise ServiceOSException(
                    "PERMISSION_DENIED",
                    "Cannot act on another tenant's catalog.",
                    status_code=403,
                )
            return candidate
        if self.actor_tenant_id:
            return self.actor_tenant_id
        raise ServiceOSException("TENANT_NOT_FOUND", "tenant_id is required.", status_code=422)

    # ═══════════════════════════════════════════════════════════
    # Available Services (from admin master catalog)
    # ═══════════════════════════════════════════════════════════

    async def get_home_services_category_id(self) -> uuid.UUID:
        res = await self.db.execute(
            select(ServiceCategory).where(ServiceCategory.vertical_type == "home_services"))
        cat = res.scalars().first()
        if not cat:
            raise ServiceOSException("HOME_SERVICES_CATEGORY_NOT_FOUND",
                "No Home Services category is configured.", status_code=422)
        return cat.id

    async def list_available_services(self, tenant_id_raw=None, category_id: uuid.UUID | None = None) -> dict:
        """All active master services — with is_enabled flag per tenant.
        category_id is optional and additive (existing callers unaffected);
        the Home Services Setup Wizard always passes the Home Services
        category id so it never sees another vertical's catalog."""
        tenant_id = self._require_tenant_id(tenant_id_raw)

        stmt = select(MasterService).where(
            MasterService.is_active == True,
            MasterService.deleted_at.is_(None),
        )
        if category_id:
            stmt = stmt.where(MasterService.category_id == category_id)
        svc_res = await self.db.execute(stmt.order_by(MasterService.display_order, MasterService.service_name))
        services = svc_res.scalars().all()

        # Which ones the tenant has already enabled
        enabled_res = await self.db.execute(
            select(TenantService).where(
                TenantService.tenant_id == tenant_id,
                TenantService.is_enabled == True,
                TenantService.deleted_at.is_(None),
            ))
        enabled_set = {ts.master_service_id for ts in enabled_res.scalars().all()}

        return {"services": [
            {
                "service_id": str(s.id),
                "category_id": str(s.category_id),
                "service_name": s.service_name,
                "description": s.description,
                "job_type": s.job_type,
                "pricing_model": s.pricing_model,
                "base_price": float(s.base_price),
                "min_price": float(s.min_price) if s.min_price else None,
                "max_price": float(s.max_price) if s.max_price else None,
                "visit_fee": float(s.visit_fee),
                "is_brand_required": s.is_brand_required,
                "is_type_required": s.is_type_required,
                "requires_checklist": s.requires_checklist,
                "tenant_override_allowed": s.tenant_override_allowed,
                "is_active": s.is_active,
                "is_enabled": s.id in enabled_set,
            }
            for s in services
        ]}

    # ═══════════════════════════════════════════════════════════
    # Enabled Services (tenant's active list)
    # ═══════════════════════════════════════════════════════════

    async def list_enabled_services(self, tenant_id_raw=None, category_id: uuid.UUID | None = None) -> dict:
        tenant_id = self._require_tenant_id(tenant_id_raw)
        stmt = select(TenantService).where(
            TenantService.tenant_id == tenant_id,
            TenantService.is_enabled == True,
            TenantService.deleted_at.is_(None),
        )
        if category_id:
            stmt = stmt.where(TenantService.category_id == category_id)
        res = await self.db.execute(stmt.order_by(TenantService.created_at))
        services = res.scalars().all()
        return {"services": [self._ts_dict(ts) for ts in services]}

    async def list_home_services_available(self, tenant_id_raw=None) -> dict:
        cat_id = await self.get_home_services_category_id()
        return await self.list_available_services(tenant_id_raw, category_id=cat_id)

    async def list_home_services_enabled(self, tenant_id_raw=None) -> dict:
        cat_id = await self.get_home_services_category_id()
        return await self.list_enabled_services(tenant_id_raw, category_id=cat_id)

    async def get_enabled_service(self, tenant_service_id: uuid.UUID) -> dict:
        ts = await self._load_tenant_service(tenant_service_id)
        self._assert_tenant_owns_ts(ts)
        return self._ts_dict(ts)

    # ═══════════════════════════════════════════════════════════
    # Enable Service
    # ═══════════════════════════════════════════════════════════

    async def enable_service(self, data: dict, tenant_id_raw=None) -> dict:
        tenant_id = self._require_tenant_id(tenant_id_raw)
        svc_id_raw = data.get("master_service_id")
        if not svc_id_raw:
            raise ServiceOSException("MASTER_SERVICE_NOT_FOUND", "master_service_id is required.", status_code=422)
        svc_id = uuid.UUID(str(svc_id_raw))

        # Load master service
        svc_res = await self.db.execute(
            select(MasterService).where(MasterService.id == svc_id, MasterService.deleted_at.is_(None)))
        svc = svc_res.scalar_one_or_none()
        if not svc:
            raise NotFoundException("MasterService", str(svc_id))
        if not svc.is_active:
            raise ServiceOSException("MASTER_SERVICE_INACTIVE", "Service is not active.", status_code=422)

        # Check category active
        cat_res = await self.db.execute(
            select(ServiceCategory).where(ServiceCategory.id == svc.category_id))
        cat = cat_res.scalar_one_or_none()
        if not cat or not cat.is_active:
            raise ServiceOSException("SERVICE_CATEGORY_INACTIVE", "Service category is inactive.", status_code=422)

        # FINAL-L5-04B: tenant must hold an ACTIVE entitlement for the
        # service_group this service belongs to before it can configure it.
        # This is a real backend enforcement point, not just a hidden menu
        # item — see FINAL_L5_04B_SERVICE_SETUP_ENFORCEMENT_REPORT.md.
        if svc.service_group_id:
            has_entitlement = await entitlement_service.has_category_entitlement(
                self.db, tenant_id, svc.service_group_id
            )
            if not has_entitlement:
                raise ServiceOSException(
                    "CATEGORY_NOT_ENTITLED",
                    "Your tenant does not have an active entitlement for this service's category.",
                    status_code=403,
                )

        # Check not already enabled
        existing = await self.db.execute(
            select(TenantService).where(
                TenantService.tenant_id == tenant_id,
                TenantService.master_service_id == svc_id,
                TenantService.deleted_at.is_(None),
            ))
        existing_ts = existing.scalar_one_or_none()
        if existing_ts and existing_ts.is_enabled:
            raise ServiceOSException("TENANT_SERVICE_ALREADY_ENABLED", "Service is already enabled for this tenant.", status_code=409)

        if existing_ts:
            # Re-enable
            existing_ts.is_enabled = True
            ts = existing_ts
        else:
            # Validate price overrides
            tenant_base  = _decimal_or_none(data.get("tenant_base_price"))
            tenant_min   = _decimal_or_none(data.get("tenant_min_price"))
            tenant_max   = _decimal_or_none(data.get("tenant_max_price"))
            tenant_visit = _decimal_or_none(data.get("tenant_visit_fee"))

            # MODULE-L5-03: `is not None`, not truthiness — Decimal('0') is falsy,
            # so the old `any([...])`/`if tenant_min and ...` skipped validation
            # when a tenant set price 0, storing a floor-bypassing value.
            if any(v is not None for v in (tenant_base, tenant_min, tenant_max, tenant_visit)):
                if not svc.tenant_override_allowed:
                    raise ServiceOSException("TENANT_SERVICE_OVERRIDE_NOT_ALLOWED",
                        "Price override is not allowed for this service.", status_code=422)
                self._validate_price_overrides(svc, tenant_base, tenant_min, tenant_max, tenant_visit)

            ts = TenantService(
                tenant_id=tenant_id,
                master_service_id=svc_id,
                category_id=svc.category_id,
                job_type=svc.job_type,
                is_enabled=True,
                tenant_display_name=data.get("tenant_display_name"),
                tenant_description=data.get("tenant_description"),
                tenant_base_price=tenant_base,
                tenant_min_price=tenant_min,
                tenant_max_price=tenant_max,
                tenant_visit_fee=tenant_visit,
                override_allowed=svc.tenant_override_allowed,
                requires_brand=svc.is_brand_required,
                requires_type=svc.is_type_required,
                is_active=True,
            )
            self.db.add(ts)

        await self.db.flush()
        return self._ts_dict(ts)

    def _validate_price_overrides(self, svc, tenant_base, tenant_min, tenant_max, tenant_visit) -> None:
        """MODULE-L5-03: canonical platform-floor / ceiling / non-negative
        enforcement for tenant price overrides. Shared by create and update so
        the platform floor cannot be bypassed through either path. Uses
        `is not None` so a 0 override is validated, not silently skipped."""
        for lbl, val in (("tenant_min_price", tenant_min), ("tenant_max_price", tenant_max),
                         ("tenant_base_price", tenant_base), ("tenant_visit_fee", tenant_visit)):
            if val is not None and val < 0:
                raise ServiceOSException("TENANT_PRICE_NEGATIVE",
                    f"{lbl} cannot be negative.", status_code=422)
        if tenant_min is not None and svc is not None and svc.min_price is not None and tenant_min < svc.min_price:
            raise ServiceOSException("TENANT_PRICE_BELOW_ADMIN_MIN",
                f"Tenant min price cannot be below admin min (₹{svc.min_price}).", status_code=422)
        if tenant_max is not None and svc is not None and svc.max_price is not None and tenant_max > svc.max_price:
            raise ServiceOSException("TENANT_PRICE_ABOVE_ADMIN_MAX",
                f"Tenant max price cannot exceed admin max (₹{svc.max_price}).", status_code=422)

    async def update_enabled_service(self, tenant_service_id: uuid.UUID, data: dict) -> dict:
        ts = await self._load_tenant_service(tenant_service_id)
        self._assert_tenant_owns_ts(ts)

        if not ts.override_allowed:
            for field in ("tenant_base_price", "tenant_min_price", "tenant_max_price", "tenant_visit_fee"):
                if data.get(field) is not None:
                    raise ServiceOSException("TENANT_SERVICE_OVERRIDE_NOT_ALLOWED",
                        "Price override is not allowed for this service.", status_code=422)

        # MODULE-L5-03 FIX: the update path previously did ZERO price validation
        # and blindly setattr'd any provided price — a clean platform-floor
        # bypass (a tenant could update below admin min, to 0, or negative).
        # Validate the effective (post-update) override values against the
        # master service's admin floor/ceiling before persisting.
        svc = (await self.db.execute(
            select(MasterService).where(MasterService.id == ts.master_service_id)
        )).scalar_one_or_none()
        eff = {}
        for field in ("tenant_base_price", "tenant_min_price", "tenant_max_price", "tenant_visit_fee"):
            if field in data and data[field] is not None:
                eff[field] = Decimal(str(data[field]))
            else:
                eff[field] = getattr(ts, field)
        self._validate_price_overrides(svc, eff["tenant_base_price"], eff["tenant_min_price"],
                                       eff["tenant_max_price"], eff["tenant_visit_fee"])

        for field in ("tenant_display_name", "tenant_description"):
            if field in data and data[field] is not None:
                setattr(ts, field, data[field])
        for field in ("tenant_base_price", "tenant_min_price", "tenant_max_price", "tenant_visit_fee"):
            if field in data and data[field] is not None:
                setattr(ts, field, Decimal(str(data[field])))

        await self.db.flush()
        return self._ts_dict(ts)

    async def disable_service(self, data: dict = None, tenant_id_raw=None) -> dict:
        tenant_id = self._require_tenant_id(tenant_id_raw)
        svc_id_raw = (data or {}).get("master_service_id")
        if not svc_id_raw:
            raise ServiceOSException("MASTER_SERVICE_NOT_FOUND", "master_service_id is required.", status_code=422)
        svc_id = uuid.UUID(str(svc_id_raw))
        res = await self.db.execute(
            select(TenantService).where(
                TenantService.tenant_id == tenant_id,
                TenantService.master_service_id == svc_id,
                TenantService.deleted_at.is_(None),
            ))
        ts = res.scalar_one_or_none()
        if not ts:
            raise ServiceOSException("TENANT_SERVICE_NOT_ENABLED", "Service is not enabled for this tenant.", status_code=404)
        ts.is_enabled = False
        await self.db.flush()
        return {"disabled": True, "tenant_service_id": str(ts.id)}

    # ═══════════════════════════════════════════════════════════
    # Tenant Supported Types
    # ═══════════════════════════════════════════════════════════

    async def get_tenant_service_types(self, tenant_service_id: uuid.UUID) -> dict:
        ts = await self._load_tenant_service(tenant_service_id)
        self._assert_tenant_owns_ts(ts)
        res = await self.db.execute(
            select(TenantServiceType, ServiceType)
            .join(ServiceType, ServiceType.id == TenantServiceType.service_type_id)
            .where(TenantServiceType.tenant_service_id == tenant_service_id,
                   TenantServiceType.is_enabled == True))
        rows = res.all()
        return {"types": [
            {"id": str(tst.id), "service_type_id": str(tst.service_type_id),
             "name": st.name, "is_enabled": tst.is_enabled,
             "tenant_price_adjustment": float(tst.tenant_price_adjustment) if tst.tenant_price_adjustment else None}
            for tst, st in rows
        ]}

    async def set_tenant_service_types(self, tenant_service_id: uuid.UUID, type_ids: list[str]) -> dict:
        ts = await self._load_tenant_service(tenant_service_id)
        self._assert_tenant_owns_ts(ts)

        # Validate all type_ids are mapped to the master service
        admin_types_res = await self.db.execute(
            select(MasterServiceType).where(
                MasterServiceType.master_service_id == ts.master_service_id,
                MasterServiceType.is_active == True))
        allowed_type_ids = {str(m.service_type_id) for m in admin_types_res.scalars().all()}

        for tid in type_ids:
            if tid not in allowed_type_ids:
                raise ServiceOSException("SERVICE_TYPE_NOT_SUPPORTED",
                    f"Type {tid} is not mapped to this service by admin.", status_code=422)

        # Deactivate all existing, then upsert new ones
        existing_res = await self.db.execute(
            select(TenantServiceType).where(TenantServiceType.tenant_service_id == tenant_service_id))
        existing_map = {str(x.service_type_id): x for x in existing_res.scalars().all()}

        for tid in type_ids:
            type_uuid = uuid.UUID(tid)
            if tid in existing_map:
                existing_map[tid].is_enabled = True
            else:
                tst = TenantServiceType(
                    tenant_id=ts.tenant_id, tenant_service_id=tenant_service_id,
                    service_type_id=type_uuid, is_enabled=True)
                self.db.add(tst)

        # Disable ones not in new list
        for tid, tst in existing_map.items():
            if tid not in type_ids:
                tst.is_enabled = False

        await self.db.flush()
        return await self.get_tenant_service_types(tenant_service_id)

    # ═══════════════════════════════════════════════════════════
    # Tenant Supported Brands
    # ═══════════════════════════════════════════════════════════

    async def get_tenant_service_brands(self, tenant_service_id: uuid.UUID) -> dict:
        """Brand *enablement* is type-independent (a tenant supports LG or
        not, regardless of which types they price it for) — restricted to
        the service_type_id IS NULL marker row per brand so this list isn't
        polluted by the per-type pricing rows created via set_brand_pricing
        (migration 120 — Type-Dependent Brand Pricing)."""
        ts = await self._load_tenant_service(tenant_service_id)
        self._assert_tenant_owns_ts(ts)
        res = await self.db.execute(
            select(TenantServiceBrand, Brand)
            .join(Brand, Brand.id == TenantServiceBrand.brand_id)
            .where(TenantServiceBrand.tenant_service_id == tenant_service_id,
                   TenantServiceBrand.service_type_id.is_(None),
                   TenantServiceBrand.is_enabled == True))
        rows = res.all()
        return {"brands": [
            {"id": str(tsb.id), "brand_id": str(tsb.brand_id),
             "name": b.name, "is_enabled": tsb.is_enabled,
             "tenant_price_adjustment": float(tsb.tenant_price_adjustment) if tsb.tenant_price_adjustment else None}
            for tsb, b in rows
        ]}

    async def set_tenant_service_brands(self, tenant_service_id: uuid.UUID, brand_ids: list[str]) -> dict:
        ts = await self._load_tenant_service(tenant_service_id)
        self._assert_tenant_owns_ts(ts)

        # Validate brands are mapped to master service
        admin_brands_res = await self.db.execute(
            select(MasterServiceBrand).where(
                MasterServiceBrand.master_service_id == ts.master_service_id,
                MasterServiceBrand.is_active == True))
        allowed_brand_ids = {str(m.brand_id) for m in admin_brands_res.scalars().all()}

        for bid in brand_ids:
            if bid not in allowed_brand_ids:
                raise ServiceOSException("BRAND_NOT_SUPPORTED",
                    f"Brand {bid} is not mapped to this service by admin.", status_code=422)

        existing_res = await self.db.execute(
            select(TenantServiceBrand).where(TenantServiceBrand.tenant_service_id == tenant_service_id))
        existing_map = {str(x.brand_id): x for x in existing_res.scalars().all()}

        for bid in brand_ids:
            brand_uuid = uuid.UUID(bid)
            if bid in existing_map:
                existing_map[bid].is_enabled = True
            else:
                tsb = TenantServiceBrand(
                    tenant_id=ts.tenant_id, tenant_service_id=tenant_service_id,
                    brand_id=brand_uuid, is_enabled=True)
                self.db.add(tsb)

        for bid, tsb in existing_map.items():
            if bid not in brand_ids:
                tsb.is_enabled = False

        await self.db.flush()
        return await self.get_tenant_service_brands(tenant_service_id)

    # ═══════════════════════════════════════════════════════════
    # Home Services Service Setup Wizard — per-type / per-brand pricing
    # (Step 3 / Step 3B), price preview, and publish (Step 6)
    # ═══════════════════════════════════════════════════════════

    async def _find_admin_pricing_rule(self, master_service_id: uuid.UUID,
                                        service_type_id: uuid.UUID | None,
                                        brand_id: uuid.UUID | None) -> ServicePricingRule | None:
        """Same scoping the admin console writes to (global default rule,
        no tier/city) — the tenant reads the admin-approved floor/ceiling
        from the identical row the admin console's Types & Pricing /
        Brands tabs create."""
        stmt = select(ServicePricingRule).where(
            ServicePricingRule.master_service_id == master_service_id,
            ServicePricingRule.deleted_at.is_(None),
            ServicePricingRule.is_active == True,
            ServicePricingRule.tier_id.is_(None),
            ServicePricingRule.city.is_(None),
        )
        stmt = stmt.where(ServicePricingRule.service_type_id == service_type_id) if service_type_id \
            else stmt.where(ServicePricingRule.service_type_id.is_(None))
        stmt = stmt.where(ServicePricingRule.brand_id == brand_id) if brand_id \
            else stmt.where(ServicePricingRule.brand_id.is_(None))
        return (await self.db.execute(stmt)).scalars().first()

    async def get_type_pricing_for_setup(self, tenant_service_id: uuid.UUID) -> dict:
        ts = await self._load_tenant_service(tenant_service_id)
        self._assert_tenant_owns_ts(ts)
        res = await self.db.execute(
            select(TenantServiceType, ServiceType)
            .join(ServiceType, ServiceType.id == TenantServiceType.service_type_id)
            .where(TenantServiceType.tenant_service_id == tenant_service_id,
                   TenantServiceType.is_enabled == True))
        rows = res.all()
        out = []
        for tst, st in rows:
            rule = await self._find_admin_pricing_rule(ts.master_service_id, tst.service_type_id, None)
            admin_floor = float(rule.min_price) if rule and rule.min_price is not None else None
            admin_ceiling = float(rule.max_price) if rule and rule.max_price is not None else None
            fee_pct = float(rule.platform_fee_percent) if rule and rule.platform_fee_percent is not None else 10.0
            tenant_min = float(tst.tenant_min_price) if tst.tenant_min_price is not None else None
            tenant_max = float(tst.tenant_max_price) if tst.tenant_max_price is not None else None
            preview = None
            if tenant_min is not None and tenant_max is not None:
                try:
                    preview = compute_symmetric_customer_price_tiers(tenant_min, tenant_max, fee_pct)
                except BargainValidationError:
                    preview = None
            out.append({
                "tenant_service_type_id": str(tst.id), "service_type_id": str(tst.service_type_id),
                "name": st.name,
                "admin_floor_price": admin_floor, "admin_ceiling_price": admin_ceiling,
                "platform_fee_percent": fee_pct,
                "tenant_min_price": tenant_min, "tenant_max_price": tenant_max,
                "customer_price_preview": preview,
            })
        return {"types": out}

    async def set_type_pricing(self, tenant_service_id: uuid.UUID, service_type_id: uuid.UUID,
                                tenant_min_price, tenant_max_price) -> dict:
        ts = await self._load_tenant_service(tenant_service_id)
        self._assert_tenant_owns_ts(ts)
        res = await self.db.execute(
            select(TenantServiceType).where(
                TenantServiceType.tenant_service_id == tenant_service_id,
                TenantServiceType.service_type_id == service_type_id,
                TenantServiceType.is_enabled == True))
        tst = res.scalar_one_or_none()
        if not tst:
            raise ServiceOSException("SERVICE_TYPE_NOT_SUPPORTED",
                "This type is not selected for this service.", status_code=422)

        rule = await self._find_admin_pricing_rule(ts.master_service_id, service_type_id, None)
        admin_floor = rule.min_price if rule else None
        admin_ceiling = rule.max_price if rule else None
        if admin_floor is None or admin_ceiling is None:
            raise ServiceOSException("ADMIN_PRICE_RANGE_NOT_CONFIGURED",
                "Admin has not configured a price range for this type yet.", status_code=422)

        tmin = _decimal_or_none(tenant_min_price)
        tmax = _decimal_or_none(tenant_max_price)
        if tmin is None or tmax is None:
            raise ServiceOSException("PRICE_RANGE_REQUIRED",
                "Both minimum and maximum price are required.", status_code=422)
        if tmin > tmax:
            raise ServiceOSException("INVALID_PRICE_RANGE",
                "Minimum price cannot exceed maximum price.", status_code=422)
        if tmin < admin_floor:
            raise ServiceOSException("TENANT_PRICE_BELOW_ADMIN_MIN",
                f"Your minimum price cannot be below the admin floor (Rs. {admin_floor}).", status_code=422)
        if tmax > admin_ceiling:
            raise ServiceOSException("TENANT_PRICE_ABOVE_ADMIN_MAX",
                f"Your maximum price cannot exceed the admin ceiling (Rs. {admin_ceiling}).", status_code=422)

        tst.tenant_min_price = tmin
        tst.tenant_max_price = tmax
        await self.db.flush()
        return await self.get_type_pricing_for_setup(tenant_service_id)

    async def get_brand_pricing_for_setup(self, tenant_service_id: uuid.UUID,
                                           service_type_id: uuid.UUID | None = None) -> dict:
        """Type-Dependent Brand Pricing (migration 120): brand rows are now
        scoped by service_type_id. For a type-based service, callers must
        pass service_type_id to see/set that type's brand overrides —
        omitting it returns only the service-level (NULL service_type_id)
        rows, which only exist for fixed (non-type-based) services."""
        ts = await self._load_tenant_service(tenant_service_id)
        self._assert_tenant_owns_ts(ts)
        stmt = (
            select(TenantServiceBrand, Brand, MasterServiceBrand)
            .join(Brand, Brand.id == TenantServiceBrand.brand_id)
            .join(MasterServiceBrand, (MasterServiceBrand.master_service_id == ts.master_service_id) &
                  (MasterServiceBrand.brand_id == TenantServiceBrand.brand_id))
            .where(TenantServiceBrand.tenant_service_id == tenant_service_id,
                   TenantServiceBrand.is_enabled == True)
        )
        stmt = stmt.where(TenantServiceBrand.service_type_id == service_type_id) if service_type_id \
            else stmt.where(TenantServiceBrand.service_type_id.is_(None))
        rows = (await self.db.execute(stmt)).all()
        out = []
        for tsb, b, msb in rows:
            rule = await self._find_admin_pricing_rule(ts.master_service_id, service_type_id, tsb.brand_id)
            admin_floor = float(rule.min_price) if rule and rule.min_price is not None else None
            admin_ceiling = float(rule.max_price) if rule and rule.max_price is not None else None
            fee_pct = float(rule.platform_fee_percent) if rule and rule.platform_fee_percent is not None else 10.0
            tenant_min = float(tsb.tenant_min_price) if tsb.tenant_min_price is not None else None
            tenant_max = float(tsb.tenant_max_price) if tsb.tenant_max_price is not None else None
            preview = None
            if msb.can_override_price and tenant_min is not None and tenant_max is not None:
                try:
                    preview = compute_symmetric_customer_price_tiers(tenant_min, tenant_max, fee_pct)
                except BargainValidationError:
                    preview = None
            out.append({
                "tenant_service_brand_id": str(tsb.id), "brand_id": str(tsb.brand_id), "name": b.name,
                "service_type_id": str(tsb.service_type_id) if tsb.service_type_id else None,
                "can_override_price": msb.can_override_price, "is_routing_only": msb.is_routing_only,
                "admin_floor_price": admin_floor, "admin_ceiling_price": admin_ceiling,
                "platform_fee_percent": fee_pct,
                "tenant_min_price": tenant_min, "tenant_max_price": tenant_max,
                "customer_price_preview": preview,
            })
        return {"brands": out}

    async def set_brand_pricing(self, tenant_service_id: uuid.UUID, brand_id: uuid.UUID,
                                 tenant_min_price, tenant_max_price,
                                 service_type_id: uuid.UUID | None = None) -> dict:
        ts = await self._load_tenant_service(tenant_service_id)
        self._assert_tenant_owns_ts(ts)

        # Rule 1/2: type-based services require service_type_id for brand pricing.
        if ts.requires_type and service_type_id is None:
            raise ServiceOSException("SERVICE_TYPE_REQUIRED_FOR_BRAND_PRICING",
                "Service type is required when adding brand pricing for a type-based service.",
                status_code=422)

        if service_type_id is not None:
            # Rule 3: the type must actually be enabled for this tenant_service.
            tst_res = await self.db.execute(
                select(TenantServiceType).where(
                    TenantServiceType.tenant_service_id == tenant_service_id,
                    TenantServiceType.service_type_id == service_type_id,
                    TenantServiceType.is_enabled == True))
            if tst_res.scalar_one_or_none() is None:
                raise ServiceOSException("SERVICE_TYPE_NOT_SUPPORTED",
                    "This type is not selected for this service.", status_code=422)

        msb_res = await self.db.execute(
            select(MasterServiceBrand).where(
                MasterServiceBrand.master_service_id == ts.master_service_id,
                MasterServiceBrand.brand_id == brand_id,
                MasterServiceBrand.is_active == True))
        msb = msb_res.scalar_one_or_none()
        if msb is None:
            raise ServiceOSException("BRAND_NOT_SUPPORTED",
                "This brand is not selected for this service.", status_code=422)
        if not msb.can_override_price:
            raise ServiceOSException("BRAND_OVERRIDE_NOT_ALLOWED",
                "This brand is not configured for price override by admin.", status_code=422)

        rule = await self._find_admin_pricing_rule(ts.master_service_id, service_type_id, brand_id)
        admin_floor = rule.min_price if rule else None
        admin_ceiling = rule.max_price if rule else None
        if admin_floor is None or admin_ceiling is None:
            raise ServiceOSException("ADMIN_PRICE_RANGE_NOT_CONFIGURED",
                "Admin has not configured a price range for this brand yet.", status_code=422)

        tmin = _decimal_or_none(tenant_min_price)
        tmax = _decimal_or_none(tenant_max_price)
        if tmin is None or tmax is None:
            raise ServiceOSException("PRICE_RANGE_REQUIRED",
                "Both minimum and maximum price are required.", status_code=422)
        if tmin > tmax:
            raise ServiceOSException("INVALID_PRICE_RANGE",
                "Minimum price cannot exceed maximum price.", status_code=422)
        if tmin < admin_floor:
            raise ServiceOSException("TENANT_PRICE_BELOW_ADMIN_MIN",
                f"Your minimum price cannot be below the admin floor (Rs. {admin_floor}).", status_code=422)
        if tmax > admin_ceiling:
            raise ServiceOSException("TENANT_PRICE_ABOVE_ADMIN_MAX",
                f"Your maximum price cannot exceed the admin ceiling (Rs. {admin_ceiling}).", status_code=422)

        # Upsert scoped by (tenant_service_id, service_type_id, brand_id) —
        # this is the actual fix: previously this looked up by
        # (tenant_service_id, brand_id) only, so Window AC's LG price and
        # Split AC's LG price silently overwrote the same row.
        existing_res = await self.db.execute(
            select(TenantServiceBrand).where(
                TenantServiceBrand.tenant_service_id == tenant_service_id,
                TenantServiceBrand.brand_id == brand_id,
                TenantServiceBrand.service_type_id == service_type_id
                if service_type_id is not None else TenantServiceBrand.service_type_id.is_(None)))
        tsb = existing_res.scalar_one_or_none()
        if tsb is None:
            tsb = TenantServiceBrand(
                tenant_id=ts.tenant_id, tenant_service_id=tenant_service_id,
                service_type_id=service_type_id, brand_id=brand_id, is_enabled=True)
            self.db.add(tsb)

        tsb.tenant_min_price = tmin
        tsb.tenant_max_price = tmax
        await self.db.flush()
        return await self.get_brand_pricing_for_setup(tenant_service_id, service_type_id)

    # ── Coverage modes (migration 152) ──────────────────────────────────────
    # ALL / SELECTED_ONLY / ALL_EXCEPT for the Type and Brand dimensions.
    # "selected"/"all_except" both read the SAME TenantServiceType/
    # TenantServiceBrand rows -- only the coverage_mode flag changes whether
    # those rows mean "the supported set" or "the excluded set".
    COVERAGE_MODES = ("all", "selected", "all_except")

    async def set_type_coverage_mode(self, tenant_service_id: uuid.UUID, mode: str) -> dict:
        if mode not in self.COVERAGE_MODES:
            raise ServiceOSException("INVALID_COVERAGE_MODE",
                f"mode must be one of {self.COVERAGE_MODES}.", status_code=422)
        ts = await self._load_tenant_service(tenant_service_id)
        self._assert_tenant_owns_ts(ts)
        ts.type_coverage_mode = mode
        await self.db.flush()
        return self._ts_dict(ts)

    async def set_brand_coverage_mode(self, tenant_service_id: uuid.UUID, mode: str) -> dict:
        if mode not in self.COVERAGE_MODES:
            raise ServiceOSException("INVALID_COVERAGE_MODE",
                f"mode must be one of {self.COVERAGE_MODES}.", status_code=422)
        ts = await self._load_tenant_service(tenant_service_id)
        self._assert_tenant_owns_ts(ts)
        ts.brand_coverage_mode = mode
        await self.db.flush()
        return self._ts_dict(ts)

    async def is_type_supported(self, ts: TenantService, service_type_id: uuid.UUID) -> bool:
        if ts.type_coverage_mode == "all":
            return True
        r = await self.db.execute(select(TenantServiceType.id).where(
            TenantServiceType.tenant_service_id == ts.id,
            TenantServiceType.service_type_id == service_type_id,
            TenantServiceType.is_enabled == True))
        row_exists = r.scalar_one_or_none() is not None
        return (not row_exists) if ts.type_coverage_mode == "all_except" else row_exists

    async def is_brand_supported(self, ts: TenantService, brand_id: uuid.UUID) -> bool:
        if ts.brand_coverage_mode == "all":
            return True
        r = await self.db.execute(select(TenantServiceBrand.id).where(
            TenantServiceBrand.tenant_service_id == ts.id,
            TenantServiceBrand.brand_id == brand_id,
            TenantServiceBrand.is_enabled == True))
        row_exists = r.scalar_one_or_none() is not None
        return (not row_exists) if ts.brand_coverage_mode == "all_except" else row_exists

    async def update_last_active_step(self, tenant_service_id: uuid.UUID, step: str) -> dict:
        """Minimal draft/resume pointer: remembers which wizard step the
        tenant was last on, so Save-and-Exit -> resume lands them back
        where they left off."""
        ts = await self._load_tenant_service(tenant_service_id)
        self._assert_tenant_owns_ts(ts)
        ts.last_active_step = step
        await self.db.flush()
        return {"tenant_service_id": str(ts.id), "last_active_step": ts.last_active_step}

    async def validate_for_publish(self, tenant_service_id: uuid.UUID) -> dict:
        """Field-level publish validation (spec section 16 contract). Checks
        every type/brand combination the tenant has marked as SUPPORTED
        (via coverage mode) resolves to a real tenant price -- never invents
        one, never silently allows publishing an unresolvable combination."""
        ts = await self._load_tenant_service(tenant_service_id)
        self._assert_tenant_owns_ts(ts)
        errors: list[dict] = []

        if not ts.requires_type and not ts.requires_brand:
            # Simple job type: only the tenant default price (or, for
            # inspection-workflow services, the visit fee) is required.
            if ts.tenant_min_price is None or ts.tenant_max_price is None:
                if ts.tenant_visit_fee is None:
                    errors.append({
                        "step": "pricing", "job_type_id": str(ts.job_type_id) if ts.job_type_id else ts.job_type,
                        "dimension_path": {}, "code": "MISSING_TENANT_PRICE",
                        "message": "No default price or visit fee configured for this service.",
                    })
        else:
            types_r = await self.db.execute(select(ServiceType.id, ServiceType.name).join(
                MasterServiceType, MasterServiceType.service_type_id == ServiceType.id
            ).where(MasterServiceType.master_service_id == ts.master_service_id,
                    MasterServiceType.is_active == True)) if ts.requires_type else None
            candidate_types = types_r.all() if types_r else [(None, None)]

            brands_r = await self.db.execute(select(Brand.id, Brand.name).join(
                MasterServiceBrand, MasterServiceBrand.brand_id == Brand.id
            ).where(MasterServiceBrand.master_service_id == ts.master_service_id,
                    MasterServiceBrand.is_active == True)) if ts.requires_brand else None
            candidate_brands = brands_r.all() if brands_r else [(None, None)]

            # A required dimension with zero admin-configured values is
            # itself unpublishable (found live: an empty candidate list made
            # the loops below never execute, vacuously reporting "valid" for
            # a service that literally cannot be priced for anything).
            job_type_label = str(ts.job_type_id) if ts.job_type_id else ts.job_type
            if ts.requires_type and not candidate_types:
                errors.append({
                    "step": "coverage", "job_type_id": job_type_label, "dimension_path": {},
                    "code": "NO_TYPES_CONFIGURED",
                    "message": "This service requires a Type, but no types are configured for it yet.",
                })
            if ts.requires_brand and not candidate_brands:
                errors.append({
                    "step": "coverage", "job_type_id": job_type_label, "dimension_path": {},
                    "code": "NO_BRANDS_CONFIGURED",
                    "message": "This service requires a Brand, but no brands are configured for it yet.",
                })

            for type_id, type_name in candidate_types:
                if type_id is not None and not await self.is_type_supported(ts, type_id):
                    continue
                for brand_id, brand_name in candidate_brands:
                    if brand_id is not None and not await self.is_brand_supported(ts, brand_id):
                        continue
                    result = await self.resolve_tenant_price(tenant_service_id, type_id, brand_id)
                    if not result["resolved"]:
                        errors.append({
                            "step": "pricing", "job_type_id": str(ts.job_type_id) if ts.job_type_id else ts.job_type,
                            "dimension_path": {k: v for k, v in
                                (("type", type_name), ("brand", brand_name)) if v is not None},
                            "code": "MISSING_TENANT_PRICE",
                            "message": f"No tenant price resolves for "
                                       f"{' + '.join(v for v in (type_name, brand_name) if v) or 'this service'}.",
                        })

        return {"valid": len(errors) == 0, "errors": errors}

    async def get_blueprint_update_status(self, tenant_service_id: uuid.UUID) -> dict:
        """Spec section 19: 'Service configuration update required' detection.
        Fails closed -- a tenant setup with no recorded blueprint_version_id
        (pre-versioning legacy row) is reported as update_required=True with
        a null diff, never silently treated as up to date."""
        ts = await self._load_tenant_service(tenant_service_id)
        self._assert_tenant_owns_ts(ts)

        latest_r = await self.db.execute(
            select(ServiceBlueprintVersion).where(
                ServiceBlueprintVersion.master_service_id == ts.master_service_id,
                ServiceBlueprintVersion.status == "published",
            ).order_by(ServiceBlueprintVersion.version_number.desc()).limit(1))
        latest = latest_r.scalar_one_or_none()

        if not latest:
            return {"update_required": False, "current_version": None, "latest_version": None, "changes": []}

        if ts.blueprint_version_id is None:
            return {
                "update_required": True, "current_version": None,
                "latest_version": latest.version_number, "changes": ["No recorded blueprint version for this setup."],
            }

        if ts.blueprint_version_id == latest.id:
            return {
                "update_required": False, "current_version": latest.version_number,
                "latest_version": latest.version_number, "changes": [],
            }

        current_r = await self.db.execute(
            select(ServiceBlueprintVersion).where(ServiceBlueprintVersion.id == ts.blueprint_version_id))
        current = current_r.scalar_one_or_none()

        # Every superseded version between the tenant's version (exclusive)
        # and latest (inclusive), oldest first, so change_summary reads as a
        # chronological changelog rather than just the single latest diff.
        chain_r = await self.db.execute(
            select(ServiceBlueprintVersion.change_summary).where(
                ServiceBlueprintVersion.master_service_id == ts.master_service_id,
                ServiceBlueprintVersion.version_number > (current.version_number if current else 0),
            ).order_by(ServiceBlueprintVersion.version_number))
        changes = [c for c, in chain_r if c]

        return {
            "update_required": True,
            "current_version": current.version_number if current else None,
            "latest_version": latest.version_number,
            "changes": changes,
        }

    async def resolve_tenant_price(self, tenant_service_id: uuid.UUID,
                                    service_type_id: uuid.UUID | None = None,
                                    brand_id: uuid.UUID | None = None) -> dict:
        """Deterministic tenant price resolution -- the single source of
        truth every customer-facing quote must go through. Never invents a
        price, never falls back to another tenant's or the admin's price,
        never silently resolves across tenants. Precedence (most specific
        wins): exact type+brand override -> type-only override -> brand-only
        override (fixed/non-type-based services) -> tenant default -> none.

        Returns the exact contract shape the future wizard/pricing-preview
        API needs (resolved / pricing_model / minimum_price / maximum_price
        / currency / source_rule_id / source / inherited_from_rule_id), or
        {"resolved": False, "reason": "NO_TENANT_PRICE_FOR_COMBINATION"}.
        """
        ts = await self._load_tenant_service(tenant_service_id)
        self._assert_tenant_owns_ts(ts)

        # Coverage gate: an unsupported type/brand (per coverage_mode) must
        # never resolve to a price, regardless of any override row that
        # might technically exist -- "unsupported combinations are never
        # available to customers."
        if service_type_id is not None and not await self.is_type_supported(ts, service_type_id):
            return {"resolved": False, "reason": "COMBINATION_NOT_SUPPORTED"}
        if brand_id is not None and not await self.is_brand_supported(ts, brand_id):
            return {"resolved": False, "reason": "COMBINATION_NOT_SUPPORTED"}

        def _found(rule_id, source: str, min_price, max_price) -> dict:
            return {
                "resolved": True,
                "pricing_model": "FIXED" if min_price == max_price else "RANGE",
                "minimum_price": float(min_price),
                "maximum_price": float(max_price),
                "currency": "INR",
                "source_rule_id": str(rule_id),
                "source": source,
                "inherited_from_rule_id": None,
            }

        # 1. Exact type + brand override.
        if service_type_id is not None and brand_id is not None:
            r = await self.db.execute(select(TenantServiceBrand).where(
                TenantServiceBrand.tenant_service_id == tenant_service_id,
                TenantServiceBrand.service_type_id == service_type_id,
                TenantServiceBrand.brand_id == brand_id,
                TenantServiceBrand.is_enabled == True))
            tsb = r.scalar_one_or_none()
            if tsb and tsb.tenant_min_price is not None and tsb.tenant_max_price is not None:
                return _found(tsb.id, "type_brand_override", tsb.tenant_min_price, tsb.tenant_max_price)

        # 2. Type-only override.
        if service_type_id is not None:
            r = await self.db.execute(select(TenantServiceType).where(
                TenantServiceType.tenant_service_id == tenant_service_id,
                TenantServiceType.service_type_id == service_type_id,
                TenantServiceType.is_enabled == True))
            tst = r.scalar_one_or_none()
            if tst and tst.tenant_min_price is not None and tst.tenant_max_price is not None:
                return _found(tst.id, "type_override", tst.tenant_min_price, tst.tenant_max_price)

        # 3. Brand-only override (service_type_id NULL row -- fixed/non-type-based services).
        if brand_id is not None:
            r = await self.db.execute(select(TenantServiceBrand).where(
                TenantServiceBrand.tenant_service_id == tenant_service_id,
                TenantServiceBrand.service_type_id.is_(None),
                TenantServiceBrand.brand_id == brand_id,
                TenantServiceBrand.is_enabled == True))
            tsb = r.scalar_one_or_none()
            if tsb and tsb.tenant_min_price is not None and tsb.tenant_max_price is not None:
                return _found(tsb.id, "brand_override", tsb.tenant_min_price, tsb.tenant_max_price)

        # 4. Tenant default job-type rule.
        if ts.tenant_min_price is not None and ts.tenant_max_price is not None:
            return _found(ts.id, "tenant_default", ts.tenant_min_price, ts.tenant_max_price)

        # 5. No price resolves -- never invent, never fall back to admin/another tenant.
        return {"resolved": False, "reason": "NO_TENANT_PRICE_FOR_COMBINATION"}

    def price_options_preview(self, data: dict) -> dict:
        try:
            return compute_symmetric_customer_price_tiers(
                provider_min_price=data.get("tenant_min_price"),
                provider_max_price=data.get("tenant_max_price"),
                platform_fee_percent=data.get("platform_fee_percent", 0),
                platform_fee_fixed_amount=data.get("platform_fee_fixed_amount", 0),
            )
        except BargainValidationError as e:
            raise ServiceOSException(e.code, e.message, status_code=422) from e

    async def publish_service(self, tenant_service_id: uuid.UUID) -> dict:
        ts = await self._load_tenant_service(tenant_service_id)
        self._assert_tenant_owns_ts(ts)

        missing: list[dict] = []

        types_res = await self.db.execute(
            select(TenantServiceType).where(
                TenantServiceType.tenant_service_id == tenant_service_id,
                TenantServiceType.is_enabled == True))
        types = types_res.scalars().all()
        if ts.requires_type and not types:
            missing.append({"field": "types", "message": "Select at least one type."})
        # Any type the tenant selected — required or not — must be priced
        # before publish (ticket rule: "Price range set for every selected type").
        for t in types:
            if t.tenant_min_price is None or t.tenant_max_price is None:
                missing.append({"field": f"type_pricing:{t.service_type_id}",
                                "message": "Set a price range for every selected type."})

        brands_res = await self.db.execute(
            select(TenantServiceBrand).where(
                TenantServiceBrand.tenant_service_id == tenant_service_id,
                TenantServiceBrand.is_enabled == True))
        for b in brands_res.scalars().all():
            has_partial = (b.tenant_min_price is None) != (b.tenant_max_price is None)
            if has_partial:
                missing.append({"field": f"brand_pricing:{b.brand_id}",
                                 "message": "Brand override price range is incomplete."})

        areas_res = await self.db.execute(
            select(func.count()).select_from(TenantServiceArea).where(
                TenantServiceArea.tenant_id == ts.tenant_id, TenantServiceArea.is_active.is_(True)))
        active_areas = areas_res.scalar_one()
        if active_areas == 0:
            missing.append({"field": "service_areas",
                             "message": "At least one active service area is required to publish."})

        if missing:
            raise ServiceOSException("SERVICE_SETUP_INCOMPLETE",
                f"You must complete {len(missing)} item(s) before publishing.",
                status_code=422, context={"missing": missing, "missing_count": len(missing)})

        ts.setup_status = "published"
        ts.published_at = utcnow()
        ts.is_enabled = True
        await self.db.flush()
        return self._ts_dict(ts)

    async def save_draft(self, tenant_service_id: uuid.UUID) -> dict:
        ts = await self._load_tenant_service(tenant_service_id)
        self._assert_tenant_owns_ts(ts)
        if ts.setup_status != "published":
            ts.setup_status = "draft"
            await self.db.flush()
        return self._ts_dict(ts)

    # ═══════════════════════════════════════════════════════════
    # Helpers
    # ═══════════════════════════════════════════════════════════

    async def _load_tenant_service(self, tenant_service_id: uuid.UUID) -> TenantService:
        res = await self.db.execute(
            select(TenantService).where(
                TenantService.id == tenant_service_id,
                TenantService.deleted_at.is_(None)))
        ts = res.scalar_one_or_none()
        if not ts:
            raise NotFoundException("TenantService", str(tenant_service_id))
        return ts

    # Platform roles carry no tenant_id (super_admin / admin_* have tenant_id=None
    # per the 01D-R canonical model) and legitimately operate cross-tenant.
    PLATFORM_ROLES = ("super_admin", "admin_operations", "admin_finance", "admin_security", "admin_readonly")

    def _assert_tenant_owns_ts(self, ts: TenantService) -> None:
        # MODULE-L5-03 hardening: enforce for EVERY tenant-scoped actor, not a
        # fragile allowlist. The old check only covered ("tenant_owner","staff"),
        # so any other tenant role (e.g. technician, or a future tenant role)
        # would bypass the ownership check and fail open. Platform roles have
        # actor_tenant_id=None and are correctly skipped.
        if self.actor_tenant_id and self.actor_role not in self.PLATFORM_ROLES:
            if ts.tenant_id != self.actor_tenant_id:
                raise NotFoundException("TenantService", str(ts.id))

    def _ts_dict(self, ts: TenantService) -> dict:
        return {
            "tenant_service_id": str(ts.id),
            "tenant_id": str(ts.tenant_id),
            "master_service_id": str(ts.master_service_id),
            "category_id": str(ts.category_id),
            "job_type": ts.job_type,
            "is_enabled": ts.is_enabled,
            "tenant_display_name": ts.tenant_display_name,
            "tenant_description": ts.tenant_description,
            "tenant_base_price": float(ts.tenant_base_price) if ts.tenant_base_price else None,
            "tenant_min_price": float(ts.tenant_min_price) if ts.tenant_min_price else None,
            "tenant_max_price": float(ts.tenant_max_price) if ts.tenant_max_price else None,
            "tenant_visit_fee": float(ts.tenant_visit_fee) if ts.tenant_visit_fee else None,
            "override_allowed": ts.override_allowed,
            "requires_brand": ts.requires_brand,
            "requires_type": ts.requires_type,
            "is_active": ts.is_active,
            "setup_status": ts.setup_status,
            "published_at": ts.published_at.isoformat() if ts.published_at else None,
            "created_at": ts.created_at.isoformat() if ts.created_at else None,
            "type_coverage_mode": ts.type_coverage_mode,
            "brand_coverage_mode": ts.brand_coverage_mode,
            "last_active_step": ts.last_active_step,
        }


def _decimal_or_none(val) -> Decimal | None:
    if val is None:
        return None
    try:
        return Decimal(str(val))
    except Exception:
        return None
