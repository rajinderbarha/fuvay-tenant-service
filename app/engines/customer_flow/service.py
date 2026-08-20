"""Customer Category Flow Service — Sprint 14.

10 core methods:
  1. list_customer_categories
  2. get_customer_category_detail
  3. get_customer_category_runtime
  4. get_customer_flow_config
  5. list_customer_offerings
  6. get_customer_offering_detail
  7. validate_category_customer_access
  8. validate_offering_customer_access
  9. resolve_frontend_flow_component
 10. get_category_provider_availability_summary
"""
from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Optional

import structlog
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.admin_catalog.models import (
    ServiceCategory, MasterOffering, CustomerFlowConfig,
)
from app.engines.customer_flow.constants import (
    VALID_FLOW_TYPES, VALID_COMPONENT_KEYS, FLOW_COMPONENT_MAP, FLOW_ENGINE_MAP,
)
from app.exceptions import ServiceOSException, NotFoundException

logger = structlog.get_logger("customer_flow.service")

# ── Error codes (Phase 16) ────────────────────────────────────────────────────
ERR_CAT_NOT_FOUND        = "CUSTOMER_CATEGORY_NOT_FOUND"
ERR_CAT_NOT_VISIBLE      = "CUSTOMER_CATEGORY_NOT_VISIBLE"
ERR_CAT_INACTIVE         = "CUSTOMER_CATEGORY_INACTIVE"
ERR_CAT_FLOW_MISSING     = "CUSTOMER_CATEGORY_FLOW_NOT_CONFIGURED"
ERR_CAT_FLOW_UNSUPPORTED = "CUSTOMER_CATEGORY_FLOW_UNSUPPORTED"
ERR_OFFERING_NOT_FOUND   = "CUSTOMER_OFFERING_NOT_FOUND"
ERR_OFFERING_INACTIVE    = "CUSTOMER_OFFERING_INACTIVE"
ERR_OFFERING_MISMATCH    = "CUSTOMER_OFFERING_CATEGORY_MISMATCH"
ERR_FLOW_INVALID         = "CUSTOMER_FLOW_TYPE_INVALID"
ERR_FLOW_COMPONENT       = "CUSTOMER_FLOW_COMPONENT_INVALID"
ERR_FLOW_RESOLVE_FAILED  = "CUSTOMER_FLOW_RESOLUTION_FAILED"


class CustomerCategoryFlowService:
    def __init__(self, db: AsyncSession, request_id: str = "—"):
        self.db = db
        self.request_id = request_id

    # ── 1. List customer-visible categories ───────────────────────────────────
    async def list_customer_categories(
        self,
        search: str | None = None,
        category_type: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        stmt = (
            select(ServiceCategory)
            .where(
                ServiceCategory.is_active == True,
                ServiceCategory.is_customer_visible == True,
            )
            .order_by(ServiceCategory.display_order, ServiceCategory.name)
        )
        if search:
            stmt = stmt.where(ServiceCategory.name.ilike(f"%{search}%"))
        if category_type:
            stmt = stmt.where(ServiceCategory.category_type == category_type)

        total_stmt = select(func.count()).select_from(stmt.subquery())
        total: int = (await self.db.execute(total_stmt)).scalar_one()

        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        cats = (await self.db.execute(stmt)).scalars().all()

        items = []
        for cat in cats:
            flow_cfg = await self._load_flow_config_for_cat(cat.id)
            offering_count = await self._count_offerings(cat.id)
            items.append(self._customer_cat_summary(cat, flow_cfg, offering_count))

        return {"items": items, "total": total, "page": page, "page_size": page_size}

    # ── 2. Get customer category detail ───────────────────────────────────────
    async def get_customer_category_detail(self, slug_or_id: str) -> dict:
        cat = await self._load_visible_category(slug_or_id)
        flow_cfg = await self._load_flow_config_for_cat(cat.id)
        if not flow_cfg:
            raise ServiceOSException(
                ERR_CAT_FLOW_MISSING,
                f"Category '{cat.name}' does not have a customer flow config.",
                status_code=404,
            )
        offering_count = await self._count_offerings(cat.id)
        return {
            **self._customer_cat_summary(cat, flow_cfg, offering_count),
            "required_steps": flow_cfg.required_steps or [],
            "optional_steps": flow_cfg.optional_steps or [],
        }

    # ── 3. Get customer category runtime ─────────────────────────────────────
    async def get_customer_category_runtime(self, slug_or_id: str) -> dict:
        cat = await self._load_visible_category(slug_or_id)
        flow_cfg = await self._load_flow_config_for_cat(cat.id)
        if not flow_cfg:
            raise ServiceOSException(
                ERR_CAT_FLOW_MISSING,
                f"Category '{cat.name}' does not have a customer flow config.",
                status_code=404,
            )
        return {
            "category": {"id": str(cat.id), "name": cat.name, "slug": cat.slug},
            "runtime": {
                "customer_flow_type":     flow_cfg.customer_flow_type,
                "frontend_component_key": flow_cfg.frontend_component_key,
                "primary_engine_key":     flow_cfg.primary_engine_key,
                "status": "ready" if flow_cfg.is_active else "inactive",
            },
            "required_steps": flow_cfg.required_steps or [],
            "optional_steps": flow_cfg.optional_steps or [],
        }

    # ── 4. Get customer flow config ───────────────────────────────────────────
    async def get_customer_flow_config(self, category_id: uuid.UUID) -> dict:
        cfg = await self._load_flow_config_for_cat(category_id)
        if not cfg:
            raise ServiceOSException(
                ERR_CAT_FLOW_MISSING,
                f"No customer flow config for category {category_id}.",
                status_code=404,
            )
        return self._flow_config_dict(cfg)

    # ── 5. List customer offerings ────────────────────────────────────────────
    async def list_customer_offerings(
        self,
        slug_or_id: str,
        search: str | None = None,
        page: int = 1,
        page_size: int = 30,
    ) -> dict:
        cat = await self._load_visible_category(slug_or_id)
        stmt = (
            select(MasterOffering)
            .where(
                MasterOffering.category_id == cat.id,
                MasterOffering.is_active == True,
                MasterOffering.status == "active",
            )
            .order_by(MasterOffering.display_order, MasterOffering.name)
        )
        if search:
            stmt = stmt.where(MasterOffering.name.ilike(f"%{search}%"))

        total: int = (await self.db.execute(
            select(func.count()).select_from(stmt.subquery())
        )).scalar_one()

        offerings = (await self.db.execute(
            stmt.offset((page - 1) * page_size).limit(page_size)
        )).scalars().all()

        flow_cfg = await self._load_flow_config_for_cat(cat.id)

        return {
            "category": {
                "id": str(cat.id),
                "name": cat.name,
                "slug": cat.slug,
                "customer_flow_type": cat.customer_flow_type,
            },
            "items": [self._customer_offering_summary(o, flow_cfg) for o in offerings],
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    # ── 6. Get customer offering detail ──────────────────────────────────────
    async def get_customer_offering_detail(
        self, category_slug_or_id: str, offering_slug_or_id: str
    ) -> dict:
        cat = await self._load_visible_category(category_slug_or_id)
        offering = await self._load_active_offering(offering_slug_or_id, cat.id)
        flow_cfg = await self._load_flow_config_for_cat(cat.id)
        return {
            **self._customer_offering_summary(offering, flow_cfg),
            "category": {"id": str(cat.id), "name": cat.name, "slug": cat.slug},
            "required_fields": {
                "requires_type":           offering.is_type_required,
                "requires_brand":          offering.is_brand_required,
                "requires_address":        offering.requires_address,
                "requires_slot":           offering.requires_slot,
                "requires_photo_upload":   offering.requires_photo_upload,
                "requires_customer_notes": offering.requires_customer_notes,
            },
        }

    # ── 7. Validate category customer access ──────────────────────────────────
    async def validate_category_customer_access(self, slug_or_id: str) -> dict:
        try:
            cat = await self._load_visible_category(slug_or_id)
            return {"valid": True, "category_id": str(cat.id), "name": cat.name}
        except ServiceOSException as e:
            return {"valid": False, "error_code": e.error_code, "detail": e.detail}

    # ── 8. Validate offering customer access ──────────────────────────────────
    async def validate_offering_customer_access(
        self, category_slug_or_id: str, offering_slug_or_id: str
    ) -> dict:
        try:
            cat = await self._load_visible_category(category_slug_or_id)
            offering = await self._load_active_offering(offering_slug_or_id, cat.id)
            return {
                "valid": True,
                "offering_id": str(offering.id),
                "name": offering.name,
                "customer_flow_type": offering.customer_flow_type or cat.customer_flow_type,
            }
        except ServiceOSException as e:
            return {"valid": False, "error_code": e.error_code, "detail": e.detail}

    # ── 9. Resolve frontend flow component ───────────────────────────────────
    async def resolve_frontend_flow_component(self, category_id: uuid.UUID) -> str:
        cfg = await self._load_flow_config_for_cat(category_id)
        if cfg and cfg.frontend_component_key in VALID_COMPONENT_KEYS:
            return cfg.frontend_component_key
        cat_res = await self.db.execute(
            select(ServiceCategory.customer_flow_type).where(ServiceCategory.id == category_id)
        )
        flow_type = cat_res.scalar_one_or_none()
        return FLOW_COMPONENT_MAP.get(flow_type or "", "UnsupportedFlow")

    # ── 10. Provider availability summary ─────────────────────────────────────
    async def get_category_provider_availability_summary(
        self,
        category_id: uuid.UUID,
        offering_id: uuid.UUID | None = None,
        city: str | None = None,
    ) -> dict:
        try:
            from sqlalchemy import text
            if offering_id:
                res = await self.db.execute(text(
                    "SELECT COUNT(*) FROM provider_offering_bookable_statuses "
                    "WHERE offering_id = :oid AND is_bookable = true"
                ), {"oid": offering_id})
            else:
                res = await self.db.execute(text(
                    "SELECT COUNT(*) FROM provider_visibility_statuses "
                    "WHERE category_id = :cid AND is_bookable = true"
                ), {"cid": category_id})
            count = res.scalar_one() or 0
        except Exception:
            count = 0
        return {"available_provider_count": count, "is_available": count > 0}

    # ── Flow resolve (Phase 7) ─────────────────────────────────────────────────
    async def resolve_flow(
        self,
        category_slug: str,
        offering_slug: str | None = None,
        city: str | None = None,
        zipcode: str | None = None,
    ) -> dict:
        cat = await self._load_visible_category(category_slug)
        flow_cfg = await self._load_flow_config_for_cat(cat.id)
        if not flow_cfg:
            raise ServiceOSException(
                ERR_CAT_FLOW_MISSING,
                f"Category '{cat.name}' does not have a customer flow configured.",
                status_code=422,
            )

        offering_data: dict | None = None
        if offering_slug:
            offering = await self._load_active_offering(offering_slug, cat.id)
            offering_data = {
                "id": str(offering.id),
                "slug": offering.slug,
                "name": offering.name,
                "customer_flow_type": offering.customer_flow_type or flow_cfg.customer_flow_type,
            }
        availability = await self.get_category_provider_availability_summary(
            cat.id, uuid.UUID(offering_data["id"]) if offering_data else None, city
        )
        return {
            "category": {"id": str(cat.id), "slug": cat.slug, "name": cat.name},
            "offering": offering_data,
            "flow": {
                "customer_flow_type":     flow_cfg.customer_flow_type,
                "frontend_component_key": flow_cfg.frontend_component_key,
                "primary_engine_key":     flow_cfg.primary_engine_key,
                "required_steps":         flow_cfg.required_steps or [],
            },
            "availability": availability,
        }

    # ── Search (Phase 11) ─────────────────────────────────────────────────────
    async def search(
        self, q: str, category_id: uuid.UUID | None = None, page: int = 1, page_size: int = 20
    ) -> dict:
        # Category results
        cat_stmt = (
            select(ServiceCategory)
            .where(
                ServiceCategory.is_active == True,
                ServiceCategory.is_customer_visible == True,
                ServiceCategory.name.ilike(f"%{q}%"),
            )
            .limit(5)
        )
        cat_rows = (await self.db.execute(cat_stmt)).scalars().all()

        # Offering results
        off_stmt = (
            select(MasterOffering)
            .where(
                MasterOffering.is_active == True,
                MasterOffering.status == "active",
                MasterOffering.name.ilike(f"%{q}%"),
            )
        )
        if category_id:
            off_stmt = off_stmt.where(MasterOffering.category_id == category_id)
        off_stmt = off_stmt.limit(page_size)
        off_rows = (await self.db.execute(off_stmt)).scalars().all()

        offerings = [self._customer_offering_summary(o, None) for o in off_rows]

        # Real bug fixed here: this searched ONLY `master_offerings`, which is
        # empty in this deployment (0 rows) -- every bookable service actually
        # lives in `master_services`. So customer search could never return a
        # single service: "gas", "installation", "deep", "repair" all came back
        # with an empty `offerings` array even though AC Gas Refilling, AC
        # Installation, Full Home Deep Clean and Pipe Repair all exist and are
        # bookable. Only whole-category names matched, which is strictly less
        # than the client-side filter the app already had.
        #
        # Both tables are searched and merged rather than swapped, so a
        # deployment that does populate master_offerings keeps working.
        offerings.extend(await self._search_master_services(q, category_id, page_size))

        return {
            "query": q,
            "categories": [self._customer_cat_summary(c, None, 0) for c in cat_rows],
            "offerings": offerings[:page_size],
        }

    async def _search_master_services(
        self, q: str, category_id: uuid.UUID | None, limit: int
    ) -> list[dict]:
        """Search the real service catalog (`master_services`).

        Mapped onto the same customer-facing shape `_customer_offering_summary`
        produces so a caller cannot tell which table a result came from.
        `starting_price` follows the same rule used everywhere else on the
        customer surface: the lowest genuinely-configured amount, treating 0
        as "not configured" rather than free, and null when nothing is set.
        """
        from app.engines.admin_catalog.models import MasterService

        # Joined to the category and gated on the SAME visibility rules the
        # category search above uses. Without this the results included 8
        # orphaned "Air Conditioner" rows whose category_id resolves to no
        # category at all (test leftovers with generated slugs like
        # "ac-623969"), plus services under an inactive E2E test vertical --
        # none of which a customer can book. Every result is now guaranteed to
        # belong to a live, customer-visible category.
        stmt = (
            select(MasterService)
            .join(ServiceCategory, ServiceCategory.id == MasterService.category_id)
            .where(
                MasterService.is_active == True,
                MasterService.service_name.ilike(f"%{q}%"),
                ServiceCategory.is_active == True,
                ServiceCategory.is_customer_visible == True,
            )
        )
        if category_id:
            stmt = stmt.where(MasterService.category_id == category_id)
        rows = (await self.db.execute(stmt.limit(limit))).scalars().all()

        out: list[dict] = []
        for s in rows:
            candidates = [s.min_price, s.base_price, s.visit_fee]
            priced = [float(c) for c in candidates if c is not None and float(c) > 0]
            out.append({
                "id":                    str(s.id),
                "name":                  s.service_name,
                "slug":                  s.slug,
                "description":           s.description,
                "offering_class":        "service",
                "customer_flow_type":    "service_booking",
                "primary_engine_key":    None,
                "pricing_model":         s.pricing_model,
                "starting_price":        min(priced) if priced else None,
                "visit_fee":             float(s.visit_fee or 0),
                "appointment_fee":       0.0,
                "requires_type":         s.is_type_required,
                "requires_brand":        s.is_brand_required,
                "requires_address":      True,
                "requires_slot":         True,
                "requires_photo_upload": False,
                "is_available":          True,
                "display_order":         0,
                "category_id":           str(s.category_id),
            })
        return out

    # ── Admin: CRUD on CustomerFlowConfig ────────────────────────────────────
    async def admin_get_flow_config(self, category_id: uuid.UUID) -> dict:
        cfg = await self._load_any_flow_config_for_cat(category_id)
        if not cfg:
            raise ServiceOSException(
                ERR_CAT_FLOW_MISSING,
                f"No customer flow config for category {category_id}.",
                status_code=404,
            )
        return self._flow_config_dict(cfg)

    async def admin_upsert_flow_config(self, category_id: uuid.UUID, data: dict) -> dict:
        cat = await self._load_category_for_admin(category_id)
        cfg = await self._load_any_flow_config_for_cat(category_id)

        flow_type = data.get("customer_flow_type") or (cfg.customer_flow_type if cfg else None) or cat.customer_flow_type or ""
        if flow_type and flow_type not in VALID_FLOW_TYPES:
            raise ServiceOSException(
                ERR_FLOW_INVALID,
                f"'{flow_type}' is not a valid customer_flow_type.",
                status_code=422,
            )
        if cat.vertical_type == "home_services" and flow_type != "service_booking":
            raise ServiceOSException(
                ERR_FLOW_INVALID,
                "Home Services native customer booking supports only the service_booking flow. "
                "Use ServiceBookingFlow with booking_engine.",
                status_code=422,
            )

        expected_component = FLOW_COMPONENT_MAP.get(flow_type or "unsupported", "UnsupportedFlow")
        expected_engine = FLOW_ENGINE_MAP.get(flow_type or "unsupported", "none")
        component_key = data.get("frontend_component_key") or (cfg.frontend_component_key if cfg else expected_component)
        if component_key and component_key not in VALID_COMPONENT_KEYS:
            raise ServiceOSException(
                ERR_FLOW_COMPONENT,
                f"'{component_key}' is not a valid frontend_component_key.",
                status_code=422,
            )
        if component_key != expected_component:
            raise ServiceOSException(
                ERR_FLOW_COMPONENT,
                f"'{flow_type}' must use frontend_component_key '{expected_component}', not '{component_key}'.",
                status_code=422,
            )
        engine_key = data.get("primary_engine_key") or (cfg.primary_engine_key if cfg else expected_engine)
        if engine_key != expected_engine:
            raise ServiceOSException(
                ERR_FLOW_INVALID,
                f"'{flow_type}' must use primary_engine_key '{expected_engine}', not '{engine_key}'.",
                status_code=422,
            )

        if cfg:
            for field in ("required_steps", "optional_steps", "config", "is_active"):
                if field in data:
                    setattr(cfg, field, data[field])
            cfg.customer_flow_type = flow_type
            cfg.frontend_component_key = component_key
            cfg.primary_engine_key = engine_key
        else:
            cfg = CustomerFlowConfig(
                category_id=category_id,
                customer_flow_type=flow_type or "unsupported",
                frontend_component_key=component_key,
                primary_engine_key=engine_key,
                required_steps=data.get("required_steps"),
                optional_steps=data.get("optional_steps"),
                config=data.get("config"),
                is_active=data.get("is_active", True),
            )
            self.db.add(cfg)

        # Mirror flow fields onto the category row so customer/runtime category
        # lists and native booking resolution read one consistent contract.
        cat.customer_flow_type = flow_type
        cat.frontend_component_key = component_key
        cat.primary_engine_key = engine_key

        await self.db.flush()
        return self._flow_config_dict(cfg)

    async def admin_activate_flow_config(self, category_id: uuid.UUID) -> dict:
        cfg = await self._load_any_flow_config_for_cat(category_id)
        if not cfg:
            raise ServiceOSException(
                ERR_CAT_FLOW_MISSING, f"No flow config for category {category_id}.", status_code=404
            )
        cfg.is_active = True
        await self.db.flush()
        return {"activated": True, "category_id": str(category_id)}

    async def admin_deactivate_flow_config(self, category_id: uuid.UUID) -> dict:
        cfg = await self._load_any_flow_config_for_cat(category_id)
        if not cfg:
            raise ServiceOSException(
                ERR_CAT_FLOW_MISSING, f"No flow config for category {category_id}.", status_code=404
            )
        cfg.is_active = False
        await self.db.flush()
        return {"deactivated": True, "category_id": str(category_id)}

    # ── Private helpers ───────────────────────────────────────────────────────
    async def _load_category_for_admin(self, category_id: uuid.UUID) -> ServiceCategory:
        cat = (await self.db.execute(
            select(ServiceCategory).where(ServiceCategory.id == category_id)
        )).scalar_one_or_none()
        if not cat:
            raise ServiceOSException(
                ERR_CAT_NOT_FOUND, f"Category '{category_id}' not found.", status_code=404
            )
        return cat

    async def _load_visible_category(self, slug_or_id: str) -> ServiceCategory:
        # Try by slug first, then by UUID
        stmt = select(ServiceCategory).where(ServiceCategory.slug == slug_or_id)
        try:
            uid = uuid.UUID(slug_or_id)
            stmt = select(ServiceCategory).where(ServiceCategory.id == uid)
        except ValueError:
            pass

        cat = (await self.db.execute(stmt)).scalar_one_or_none()
        if not cat:
            raise ServiceOSException(
                ERR_CAT_NOT_FOUND, f"Category '{slug_or_id}' not found.", status_code=404
            )
        if not cat.is_active:
            raise ServiceOSException(
                ERR_CAT_INACTIVE, f"Category '{cat.name}' is inactive.", status_code=404
            )
        if not cat.is_customer_visible:
            raise ServiceOSException(
                ERR_CAT_NOT_VISIBLE, f"Category '{cat.name}' is not visible to customers.",
                status_code=404,
            )
        return cat

    async def _load_active_offering(self, slug_or_id: str, category_id: uuid.UUID) -> MasterOffering:
        stmt = select(MasterOffering).where(
            MasterOffering.category_id == category_id,
            MasterOffering.slug == slug_or_id,
        )
        try:
            uid = uuid.UUID(slug_or_id)
            stmt = select(MasterOffering).where(
                MasterOffering.id == uid,
                MasterOffering.category_id == category_id,
            )
        except ValueError:
            pass

        offering = (await self.db.execute(stmt)).scalar_one_or_none()
        if not offering:
            raise ServiceOSException(
                ERR_OFFERING_NOT_FOUND,
                f"Offering '{slug_or_id}' not found in this category.",
                status_code=404,
            )
        if not offering.is_active or offering.status != "active":
            raise ServiceOSException(
                ERR_OFFERING_INACTIVE, f"Offering '{offering.name}' is inactive.", status_code=404
            )
        return offering

    async def _load_flow_config_for_cat(
        self, category_id: uuid.UUID
    ) -> CustomerFlowConfig | None:
        res = await self.db.execute(
            select(CustomerFlowConfig).where(
                CustomerFlowConfig.category_id == category_id,
                CustomerFlowConfig.is_active == True,
            )
        )
        return res.scalar_one_or_none()

    async def _load_any_flow_config_for_cat(
        self, category_id: uuid.UUID
    ) -> CustomerFlowConfig | None:
        res = await self.db.execute(
            select(CustomerFlowConfig)
            .where(CustomerFlowConfig.category_id == category_id)
            .order_by(CustomerFlowConfig.is_active.desc(), CustomerFlowConfig.updated_at.desc().nullslast())
        )
        return res.scalar_one_or_none()

    async def _count_offerings(self, category_id: uuid.UUID) -> int:
        res = await self.db.execute(
            select(func.count()).where(
                MasterOffering.category_id == category_id,
                MasterOffering.is_active == True,
                MasterOffering.status == "active",
            )
        )
        return res.scalar_one() or 0

    def _customer_cat_summary(
        self,
        cat: ServiceCategory,
        flow_cfg: CustomerFlowConfig | None,
        offering_count: int,
    ) -> dict:
        flow_type = (flow_cfg.customer_flow_type if flow_cfg else cat.customer_flow_type) or "unsupported"
        component = (flow_cfg.frontend_component_key if flow_cfg else cat.frontend_component_key)
        engine_key = (flow_cfg.primary_engine_key if flow_cfg else cat.primary_engine_key)
        return {
            "id":                      str(cat.id),
            "name":                    cat.name,
            "slug":                    cat.slug,
            "description":             cat.description,
            "category_type":           cat.category_type,
            "icon_url":                cat.icon_url,
            "banner_url":              cat.banner_url,
            "customer_flow_type":      flow_type,
            "frontend_component_key":  component,
            "primary_engine_key":      engine_key,
            "available_offering_count":offering_count,
            "display_order":           cat.display_order,
        }

    def _customer_offering_summary(
        self,
        o: MasterOffering,
        flow_cfg: CustomerFlowConfig | None,
    ) -> dict:
        flow_type = o.customer_flow_type or (
            flow_cfg.customer_flow_type if flow_cfg else "unsupported"
        )
        starting = float(
            o.default_visit_fee if o.default_visit_fee > 0
            else o.default_appointment_fee if o.default_appointment_fee > 0
            else o.default_base_price
        )
        return {
            "id":                    str(o.id),
            "name":                  o.name,
            "slug":                  o.slug,
            "description":           o.description,
            "offering_class":        o.offering_class,
            "customer_flow_type":    flow_type,
            "primary_engine_key":    o.primary_engine_key,
            "pricing_model":         o.default_pricing_model,
            "starting_price":        starting,
            "visit_fee":             float(o.default_visit_fee),
            "appointment_fee":       float(o.default_appointment_fee),
            "requires_type":         o.is_type_required,
            "requires_brand":        o.is_brand_required,
            "requires_address":      o.requires_address,
            "requires_slot":         o.requires_slot,
            "requires_photo_upload": o.requires_photo_upload,
            "is_available":          True,
            "display_order":         o.display_order,
        }

    def _flow_config_dict(self, cfg: CustomerFlowConfig) -> dict:
        return {
            "id":                      str(cfg.id),
            "category_id":             str(cfg.category_id),
            "customer_flow_type":      cfg.customer_flow_type,
            "frontend_component_key":  cfg.frontend_component_key,
            "primary_engine_key":      cfg.primary_engine_key,
            "required_steps":          cfg.required_steps or [],
            "optional_steps":          cfg.optional_steps or [],
            "config":                  cfg.config or {},
            "is_active":               cfg.is_active,
            "created_at":              cfg.created_at.isoformat() if cfg.created_at else None,
            "updated_at":              cfg.updated_at.isoformat() if cfg.updated_at else None,
        }
