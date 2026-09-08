"""Admin Catalog Service â€” CRUD for tiers, locations, categories, master services,
service types, brands, type/brand mappings, pricing rules, and pricing preview.

All write operations are super-admin only (enforced at router layer).
Reads are available to authenticated users where noted.
"""
from __future__ import annotations
import csv
import io
import re
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import structlog
from sqlalchemy import select, and_, or_, func, text, update as sa_update, exists
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.admin_catalog.models import (
    PricingTier, TierLocation, ServiceCategory, ServiceGroup, MasterService,
    ServiceType, Brand, MasterServiceType, MasterServiceBrand, ServiceTypeMapping, BrandMapping,
    ServicePricingRule, MasterOffering, CustomerFlowConfig,
    MasterIssueType, MasterServiceOption, MasterWorkflowTemplate, MasterDataAuditLog,
    TenantService, LocationImportBatch, WorkflowServiceMapping,
    ServiceIssueMapping, ServiceOptionMapping,
    TenantServiceType, ServiceBlueprintVersion, MasterServiceJobType, ServiceJobWorkflow,
)
from app.engines.tenant_engine.models import Tenant
from app.exceptions import ServiceOSException, NotFoundException

logger = structlog.get_logger("admin_catalog.service")
utcnow = lambda: datetime.now(timezone.utc)

VALID_JOB_TYPES    = {
    "repair", "installation", "uninstallation", "inspection",
    "maintenance", "cleaning", "consultation", "service", "custom",
}
# MODULE-L5-03: canonical pricing-model registry — the single source of truth
# for the models the backend validates (_validate_pricing_config) AND for what
# clients should render. Exposed via GET /v1/admin/pricing-models so frontend/
# mobile dropdowns load from the API instead of hardcoding a list that can drift.
# VALID_PRICING_MODELS is derived from this so the two cannot disagree; the
# pricing_model_registry_guard fails closed if the endpoint stops matching it or
# if _validate_pricing_config gains/loses a model.
PRICING_MODEL_REGISTRY = {
    "fixed": {
        "label": "Fixed Price",
        "description": "A single fixed amount for the service.",
        "required_fields": ["base_price"],
        "optional_fields": ["visit_fee"],
    },
    "range": {
        "label": "Price Range (Min/Max)",
        "description": "A minimum and maximum price; final price set later.",
        "required_fields": ["min_price", "max_price"],
        "optional_fields": ["default_estimate"],
    },
    "post_assessment": {
        "label": "Quote After Assessment",
        "description": "A visit/diagnostic fee; final price quoted after inspection.",
        "required_fields": ["visit_fee", "customer_note"],
        "optional_fields": ["assessment_label"],
    },
    "hourly": {
        "label": "Hourly Rate",
        "description": "Billed per hour with a minimum billable time.",
        "required_fields": ["hourly_rate", "minimum_billable_hours"],
        "optional_fields": ["visit_fee"],
    },
}
VALID_PRICING_MODELS = set(PRICING_MODEL_REGISTRY)
VALID_TIER_TYPES   = {"metro", "large_city", "mid_city", "small_city", "rural", "premium_zone"}

# Sprint 38 — universal category constants
VALID_VERTICAL_TYPES = {
    "home_services", "coaching", "real_estate", "restaurant", "salon",
    "automotive", "professional_services", "pharmacy", "hardware",
    "repair_services", "cleaning_services", "laundry", "marketplace_products", "other",
}
VALID_FINANCE_MODELS = {
    "credit_wallet_only", "monthly_subscription", "lead_credit",
    "commission_wallet", "product_order_commission", "free_listing", "hybrid",
}
VALID_CUSTOMER_FLOW_TYPES = {
    "service_booking", "appointment_booking", "lead_capture",
    "product_purchase", "subscription_only", "quote_request", "inspection_first",
}
VALID_PROVIDER_BUSINESS_MODELS = {
    "service_provider", "product_seller", "marketplace_lister", "subscription_member",
}


def _err(field: str, msg: str) -> dict:
    return {"field": field, "message": msg}


def _validate_pricing_config(model: str, data: dict) -> None:
    """Raise ServiceOSException with field-level detail if pricing payload is invalid."""
    def _num(key) -> float | None:
        v = data.get(key)
        try:
            return float(v) if v is not None else None
        except (TypeError, ValueError):
            return None

    if model == "fixed":
        bp = _num("base_price")
        if bp is None or bp <= 0:
            raise ServiceOSException("VALIDATION_ERROR",
                "base_price is required and must be > 0 for fixed pricing.",
                status_code=422, context=_err("base_price", "Required and must be > 0."))
        vf = _num("visit_fee")
        if vf is not None and vf < 0:
            raise ServiceOSException("VALIDATION_ERROR",
                "visit_fee cannot be negative.",
                status_code=422, context=_err("visit_fee", "Cannot be negative."))

    elif model == "range":
        mn = _num("min_price")
        mx = _num("max_price")
        if mn is None or mn <= 0:
            raise ServiceOSException("VALIDATION_ERROR",
                "min_price is required and must be > 0 for range pricing.",
                status_code=422, context=_err("min_price", "Required and must be > 0."))
        if mx is None or mx <= 0:
            raise ServiceOSException("VALIDATION_ERROR",
                "max_price is required and must be > 0 for range pricing.",
                status_code=422, context=_err("max_price", "Required and must be > 0."))
        if mx < mn:
            raise ServiceOSException("INVALID_PRICE_RANGE",
                "max_price must be >= min_price.",
                status_code=422, context=_err("max_price", "Must be >= min_price."))
        de = _num("default_estimate")
        if de is not None and not (mn <= de <= mx):
            raise ServiceOSException("VALIDATION_ERROR",
                "default_estimate must be between min_price and max_price.",
                status_code=422, context=_err("default_estimate", f"Must be between {mn} and {mx}."))

    elif model == "post_assessment":
        vf = _num("visit_fee")
        if vf is None or vf < 0:
            raise ServiceOSException("VALIDATION_ERROR",
                "visit_fee is required and must be >= 0 for post-assessment pricing.",
                status_code=422, context=_err("visit_fee", "Required and must be >= 0."))
        note = (data.get("customer_note") or "").strip()
        if not note:
            raise ServiceOSException("VALIDATION_ERROR",
                "customer_note is required for post-assessment pricing.",
                status_code=422, context=_err("customer_note", "Required."))
        if data.get("show_estimated_range"):
            emn = _num("estimated_min") or _num("min_price")
            emx = _num("estimated_max") or _num("max_price")
            if emn is None:
                raise ServiceOSException("VALIDATION_ERROR",
                    "estimated_min is required when show_estimated_range=true.",
                    status_code=422, context=_err("estimated_min", "Required."))
            if emx is None:
                raise ServiceOSException("VALIDATION_ERROR",
                    "estimated_max is required when show_estimated_range=true.",
                    status_code=422, context=_err("estimated_max", "Required."))
            if emx < emn:
                raise ServiceOSException("VALIDATION_ERROR",
                    "estimated_max must be >= estimated_min.",
                    status_code=422, context=_err("estimated_max", "Must be >= estimated_min."))

    elif model == "hourly":
        hr = _num("hourly_rate")
        if hr is None or hr <= 0:
            raise ServiceOSException("VALIDATION_ERROR",
                "hourly_rate is required and must be > 0 for hourly pricing.",
                status_code=422, context=_err("hourly_rate", "Required and must be > 0."))
        mbh = _num("minimum_billable_hours")
        if mbh is None or mbh < 1:
            raise ServiceOSException("VALIDATION_ERROR",
                "minimum_billable_hours is required and must be >= 1.",
                status_code=422, context=_err("minimum_billable_hours", "Required and must be >= 1."))
        eh = _num("estimated_hours")
        if eh is not None and eh < mbh:
            raise ServiceOSException("VALIDATION_ERROR",
                "estimated_hours must be >= minimum_billable_hours.",
                status_code=422, context=_err("estimated_hours", f"Must be >= {mbh}."))
        mxh = _num("maximum_hours")
        if mxh is not None and mxh < mbh:
            raise ServiceOSException("VALIDATION_ERROR",
                "maximum_hours must be >= minimum_billable_hours.",
                status_code=422, context=_err("maximum_hours", f"Must be >= {mbh}."))
        vf = _num("visit_fee")
        if vf is not None and vf < 0:
            raise ServiceOSException("VALIDATION_ERROR",
                "visit_fee cannot be negative.",
                status_code=422, context=_err("visit_fee", "Cannot be negative."))


def _slugify(text: str) -> str:
    slug = text.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    return slug.strip("-")


def _to_dict(obj) -> dict:
    return obj.to_dict() if hasattr(obj, "to_dict") else {}


# ── Workflow-template readiness, expressed in SQL ────────────────────────────
# Readiness is a pure function of a template's own JSONB plus whether anything
# maps to it, so it can be evaluated in the database. Doing so is what lets the
# list filter and the summary count it under a LIMIT instead of materialising
# every template in Python first. Both fragments assume the templates table is
# aliased `t`.
#
# `IS NOT DISTINCT FROM` rather than `=` / `IN` on the step-code comparison:
# a step or transition with a null code must compare the way Python's
# `code not in {…}` does, and SQL `NOT IN` yields NULL (not true) against a
# null, which would silently mark a broken workflow as ready.
_HAS_MAPPING_SQL = """EXISTS (
    SELECT 1 FROM workflow_service_mappings m WHERE m.template_id = t.id
)"""

_READINESS_SQL = f"""CASE
    WHEN COALESCE(jsonb_array_length(t.steps), 0) < 2 THEN 'missing_steps'
    WHEN (SELECT count(*) FROM jsonb_array_elements(t.steps) e
           WHERE (e->>'is_start')::boolean IS TRUE) <> 1
      OR (SELECT count(*) FROM jsonb_array_elements(t.steps) e
           WHERE (e->>'is_terminal')::boolean IS TRUE) < 1
      THEN 'invalid_transitions'
    WHEN EXISTS (
        SELECT 1 FROM jsonb_array_elements(t.transitions) tr
         WHERE NOT EXISTS (SELECT 1 FROM jsonb_array_elements(t.steps) e
                            WHERE e->>'step_code' IS NOT DISTINCT FROM tr->>'from_step_code')
            OR NOT EXISTS (SELECT 1 FROM jsonb_array_elements(t.steps) e
                            WHERE e->>'step_code' IS NOT DISTINCT FROM tr->>'to_step_code')
    ) THEN 'invalid_transitions'
    WHEN NOT {_HAS_MAPPING_SQL}
         AND t.category_id IS NULL
         AND t.master_service_id IS NULL THEN 'missing_mapping'
    ELSE 'ready'
END"""


class AdminCatalogService:
    def __init__(self, db: AsyncSession, request_id: str = "â€”",
                 actor_id: uuid.UUID | None = None, actor_role: str | None = None):
        self.db = db
        self.request_id = request_id
        self.actor_id = actor_id
        self.actor_role = actor_role

    @staticmethod
    def _assert_tier_writes_retired() -> None:
        """Business-model change: admin no longer creates pricing tiers, sets
        tier multipliers, or maps cities/zipcodes to a tier. Replaced by the
        tenant service-area request/approval workflow
        (app.engines.serviceability). Existing tier/tier-location rows are
        preserved as read-only historical data — see
        `/v1/admin/tenants/service-area-migration/*` reconciliation tooling
        and TIER_RETIREMENT_REPORT.md. Reads (list/get/summary/export)
        remain available; every write raises this error."""
        raise ServiceOSException(
            "PRICING_TIER_WRITES_RETIRED",
            "Pricing tiers and city/zipcode tier mapping are retired. Tenants now "
            "request service-area coverage for admin approval; see "
            "POST /v1/tenant/service-area-requests.",
            status_code=410,
        )

    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
    # PRICING TIERS
    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

    async def list_tiers(self, is_active: bool | None = None, q: str | None = None,
                          used_in_rules: bool | None = None,
                          has_city_mapping: bool | None = None,
                          has_zipcode_mapping: bool | None = None,
                          date_from: str | None = None, date_to: str | None = None) -> dict:
        stmt = select(PricingTier).where(PricingTier.deleted_at.is_(None))
        if is_active is not None:
            stmt = stmt.where(PricingTier.is_active == is_active)
        if q:
            like = f"%{q.lower()}%"
            stmt = stmt.where(func.lower(PricingTier.name).like(like) | func.lower(PricingTier.code).like(like))
        if date_from:
            stmt = stmt.where(PricingTier.created_at >= date_from)
        if date_to:
            stmt = stmt.where(PricingTier.created_at <= date_to)
        stmt = stmt.order_by(PricingTier.created_at)
        result = await self.db.execute(stmt)
        tiers = result.scalars().all()
        counts = await self._tier_linked_counts([t.id for t in tiers])

        if used_in_rules is not None:
            tiers = [t for t in tiers if (counts.get(str(t.id), {}).get("rules_total", 0) > 0) == used_in_rules]
        if has_city_mapping is not None:
            tiers = [t for t in tiers if (counts.get(str(t.id), {}).get("cities", 0) > 0) == has_city_mapping]
        if has_zipcode_mapping is not None:
            tiers = [t for t in tiers if (counts.get(str(t.id), {}).get("zipcodes", 0) > 0) == has_zipcode_mapping]

        out = []
        for t in tiers:
            d = self._tier_dict(t)
            d["linked_counts"] = counts.get(str(t.id), {
                "cities": 0, "zipcodes": 0, "zones": 0, "rules_total": 0, "rules_active": 0,
            })
            out.append(d)
        return {"tiers": out}

    async def _tier_linked_counts(self, tier_ids: list[uuid.UUID]) -> dict[str, dict]:
        """Batch-count mapped cities/zipcodes/zones and pricing rules per tier."""
        if not tier_ids:
            return {}
        loc_result = await self.db.execute(
            select(TierLocation).where(
                TierLocation.tier_id.in_(tier_ids),
                TierLocation.deleted_at.is_(None),
                TierLocation.is_active == True,
            )
        )
        cities: dict[str, set] = {}
        zips: dict[str, set] = {}
        zones: dict[str, set] = {}
        for l in loc_result.scalars().all():
            tid = str(l.tier_id)
            if l.city:
                cities.setdefault(tid, set()).add(l.city)
            if l.zipcode:
                zips.setdefault(tid, set()).add(l.zipcode)
            if l.zone_name:
                zones.setdefault(tid, set()).add(l.zone_name)

        rules_result = await self.db.execute(
            select(ServicePricingRule.tier_id, ServicePricingRule.is_active, func.count())
            .where(ServicePricingRule.tier_id.in_(tier_ids), ServicePricingRule.deleted_at.is_(None))
            .group_by(ServicePricingRule.tier_id, ServicePricingRule.is_active)
        )
        rules_total: dict[str, int] = {}
        rules_active: dict[str, int] = {}
        for tid, is_active, cnt in rules_result.all():
            tid = str(tid)
            rules_total[tid] = rules_total.get(tid, 0) + cnt
            if is_active:
                rules_active[tid] = rules_active.get(tid, 0) + cnt

        out: dict[str, dict] = {}
        for tid in [str(t) for t in tier_ids]:
            out[tid] = {
                "cities": len(cities.get(tid, set())),
                "zipcodes": len(zips.get(tid, set())),
                "zones": len(zones.get(tid, set())),
                "rules_total": rules_total.get(tid, 0),
                "rules_active": rules_active.get(tid, 0),
            }
        return out

    async def get_tiers_summary(self) -> dict:
        result = await self.db.execute(select(PricingTier).where(PricingTier.deleted_at.is_(None)))
        tiers = result.scalars().all()
        counts = await self._tier_linked_counts([t.id for t in tiers])
        total = len(tiers)
        active = sum(1 for t in tiers if t.is_active)
        mapped_cities = sum(counts.get(str(t.id), {}).get("cities", 0) for t in tiers)
        mapped_zipcodes = sum(counts.get(str(t.id), {}).get("zipcodes", 0) for t in tiers)
        rules_using_tiers = sum(1 for t in tiers if counts.get(str(t.id), {}).get("rules_total", 0) > 0)
        unmapped_tiers = sum(
            1 for t in tiers
            if counts.get(str(t.id), {}).get("cities", 0) == 0
            and counts.get(str(t.id), {}).get("zipcodes", 0) == 0
        )
        return {
            "total_tiers": total,
            "active_tiers": active,
            "inactive_tiers": total - active,
            "mapped_cities": mapped_cities,
            "mapped_zipcodes": mapped_zipcodes,
            "rules_using_tiers": rules_using_tiers,
            "unmapped_tiers": unmapped_tiers,
        }

    async def export_tiers(self, is_active: bool | None = None) -> list[dict]:
        data = await self.list_tiers(is_active=is_active)
        return data["tiers"]

    async def get_tier_detail(self, tier_id: uuid.UUID) -> dict:
        tier = await self._load_tier(tier_id)
        loc_result = await self.db.execute(
            select(TierLocation).where(TierLocation.tier_id == tier_id, TierLocation.deleted_at.is_(None))
            .order_by(TierLocation.priority, TierLocation.created_at)
        )
        locs = loc_result.scalars().all()
        rules_result = await self.db.execute(
            select(ServicePricingRule).where(
                ServicePricingRule.tier_id == tier_id, ServicePricingRule.deleted_at.is_(None)
            ).order_by(ServicePricingRule.priority.desc())
        )
        rules = rules_result.scalars().all()
        audit = await self.list_master_data_audit(entity_type="pricing_tier", entity_id=tier_id, limit=20)
        return {
            "tier": self._tier_dict(tier),
            "mapped_cities": sorted({l.city for l in locs if l.city}),
            "mapped_zipcodes": sorted({l.zipcode for l in locs if l.zipcode}),
            "zones": sorted({l.zone_name for l in locs if l.zone_name}),
            "pricing_rules": [self._rule_dict(r) for r in rules],
            "audit_log": audit["audit_log"],
        }

    async def get_tier(self, tier_id: uuid.UUID) -> dict:
        tier = await self._load_tier(tier_id)
        return self._tier_dict(tier)

    async def create_tier(self, data: dict) -> dict:
        self._assert_tier_writes_retired()
        name = (data.get("name") or "").strip()
        code = (data.get("code") or "").strip().lower()
        tier_type = (data.get("tier_type") or "").strip()
        if not name:
            raise ServiceOSException("TIER_NAME_REQUIRED", "Tier name is required.", status_code=422)
        if not code:
            raise ServiceOSException("TIER_CODE_REQUIRED", "Tier code is required.", status_code=422)
        if tier_type not in VALID_TIER_TYPES:
            raise ServiceOSException("TIER_INVALID_TYPE", f"tier_type must be one of {sorted(VALID_TIER_TYPES)}.", status_code=422)

        # unique code check
        existing = await self.db.execute(
            select(PricingTier).where(PricingTier.code == code, PricingTier.deleted_at.is_(None)))
        if existing.scalar_one_or_none():
            raise ServiceOSException("TIER_CODE_DUPLICATE", f"Tier code '{code}' already exists.", status_code=409)

        mult = Decimal(str(data.get("base_multiplier", 1) or 1))
        if mult < 0:
            raise ServiceOSException("TIER_INVALID_MULTIPLIER", "base_multiplier cannot be negative.", status_code=422)

        tier = PricingTier(
            name=name, code=code, tier_type=tier_type,
            description=data.get("description"),
            base_multiplier=mult,
            platform_fee_percent=Decimal(str(data.get("platform_fee_percent", 0) or 0)),
            default_commission_percent=Decimal(str(data.get("default_commission_percent", 0) or 0)),
            default_sla_minutes=int(data.get("default_sla_minutes", 60) or 60),
            is_active=True,
        )
        self.db.add(tier)
        await self.db.flush()
        await self._audit("pricing_tier", tier.id, "create", None, self._tier_dict(tier), f"Created tier '{name}'")
        logger.info("tier.created", tier_id=str(tier.id), code=code)
        return self._tier_dict(tier)

    async def update_tier(self, tier_id: uuid.UUID, data: dict) -> dict:
        self._assert_tier_writes_retired()
        tier = await self._load_tier(tier_id)
        old = self._tier_dict(tier)
        for field in ("name", "description", "platform_fee_percent",
                      "default_commission_percent", "default_sla_minutes", "is_active"):
            if field in data and data[field] is not None:
                val = data[field]
                if field in ("platform_fee_percent", "default_commission_percent"):
                    val = Decimal(str(val))
                setattr(tier, field, val)
        if "base_multiplier" in data and data["base_multiplier"] is not None:
            mult = Decimal(str(data["base_multiplier"]))
            if mult < 0:
                raise ServiceOSException("TIER_INVALID_MULTIPLIER", "base_multiplier cannot be negative.", status_code=422)
            tier.base_multiplier = mult
        await self.db.flush()
        await self._audit("pricing_tier", tier.id, "update", old, self._tier_dict(tier), f"Updated tier '{tier.name}'")
        return self._tier_dict(tier)

    async def delete_tier(self, tier_id: uuid.UUID) -> dict:
        self._assert_tier_writes_retired()
        tier = await self._load_tier(tier_id)
        old = self._tier_dict(tier)
        tier.is_active = False
        tier.deleted_at = utcnow()
        # Free the code so a new tier with the same code can be created
        tier.code = f"__del_{tier.code[:40]}_{str(uuid.uuid4())[:8]}"
        await self.db.flush()
        await self._audit("pricing_tier", tier.id, "deactivate", old, self._tier_dict(tier), f"Deactivated tier '{old['name']}'")
        return {"deleted": True, "tier_id": str(tier_id)}

    async def hard_delete_tier(self, tier_id: uuid.UUID) -> dict:
        # Load the tier regardless of soft-delete state (deactivated tiers can be hard-deleted)
        result = await self.db.execute(select(PricingTier).where(PricingTier.id == tier_id))
        tier = result.scalar_one_or_none()
        if not tier:
            raise NotFoundException("PricingTier", str(tier_id))
        # Block if any active pricing rules reference this tier
        rules_check = await self.db.execute(
            select(ServicePricingRule).where(
                ServicePricingRule.tier_id == tier_id,
                ServicePricingRule.deleted_at.is_(None),
            ).limit(1)
        )
        if rules_check.scalar_one_or_none():
            raise ServiceOSException(
                "TIER_HAS_PRICING_RULES",
                "Cannot delete this tier â€” pricing rules reference it. Remove all pricing rules first.",
                status_code=409,
            )
        # Block if any active city/zipcode location mappings exist
        locs_check = await self.db.execute(
            select(TierLocation).where(
                TierLocation.tier_id == tier_id,
                TierLocation.deleted_at.is_(None),
            ).limit(1)
        )
        if locs_check.scalar_one_or_none():
            raise ServiceOSException(
                "TIER_HAS_LOCATIONS",
                "Cannot delete this tier â€” city/zipcode location mappings exist. Remove all location mappings first.",
                status_code=409,
            )
        # Hard-delete the tier row
        await self.db.delete(tier)
        await self.db.flush()
        return {"deleted": True, "tier_id": str(tier_id), "hard_delete": True}

    async def _load_tier(self, tier_id: uuid.UUID) -> PricingTier:
        result = await self.db.execute(
            select(PricingTier).where(PricingTier.id == tier_id, PricingTier.deleted_at.is_(None)))
        tier = result.scalar_one_or_none()
        if not tier:
            raise NotFoundException("PricingTier", str(tier_id))
        return tier

    def _tier_dict(self, t: PricingTier) -> dict:
        return {
            "tier_id": str(t.id), "name": t.name, "code": t.code, "tier_type": t.tier_type,
            "description": t.description,
            "base_multiplier": float(t.base_multiplier),
            "platform_fee_percent": float(t.platform_fee_percent),
            "default_commission_percent": float(t.default_commission_percent),
            "default_sla_minutes": t.default_sla_minutes,
            "is_active": t.is_active,
            "created_at": t.created_at.isoformat() if t.created_at else None,
        }

    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
    # TIER LOCATIONS
    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

    async def list_tier_locations(self, tier_id: uuid.UUID | None = None,
                                   q: str | None = None, state: str | None = None,
                                   district: str | None = None, city: str | None = None,
                                   zipcode: str | None = None, is_active: bool | None = None,
                                   has_conflict: bool | None = None,
                                   page: int = 1, page_size: int = 50,
                                   sort_by: str = "created_at", sort_dir: str = "desc") -> dict:
        conflict_zip_subq = (
            select(TierLocation.zipcode)
            .where(TierLocation.deleted_at.is_(None), TierLocation.is_active == True,
                   TierLocation.zipcode.isnot(None))
            .group_by(TierLocation.zipcode)
            .having(func.count() > 1)
        )

        stmt = select(TierLocation).where(TierLocation.deleted_at.is_(None))
        if tier_id:
            stmt = stmt.where(TierLocation.tier_id == tier_id)
        if is_active is not None:
            stmt = stmt.where(TierLocation.is_active == is_active)
        if state:
            stmt = stmt.where(func.lower(TierLocation.state) == state.lower())
        if district:
            stmt = stmt.where(func.lower(TierLocation.district) == district.lower())
        if city:
            stmt = stmt.where(func.lower(TierLocation.city) == city.lower())
        if zipcode:
            stmt = stmt.where(TierLocation.zipcode == zipcode)
        if q:
            like = f"%{q.lower()}%"
            stmt = stmt.where(
                func.lower(func.coalesce(TierLocation.city, "")).like(like) |
                func.coalesce(TierLocation.zipcode, "").like(f"%{q}%") |
                func.lower(func.coalesce(TierLocation.state, "")).like(like) |
                func.lower(func.coalesce(TierLocation.district, "")).like(like)
            )
        if has_conflict is True:
            stmt = stmt.where(TierLocation.zipcode.in_(conflict_zip_subq))
        elif has_conflict is False:
            stmt = stmt.where(
                TierLocation.zipcode.is_(None) | TierLocation.zipcode.notin_(conflict_zip_subq)
            )

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await self.db.execute(count_stmt)).scalar_one()

        sort_col_map = {
            "created_at": TierLocation.created_at, "updated_at": TierLocation.updated_at,
            "city": TierLocation.city, "zipcode": TierLocation.zipcode, "priority": TierLocation.priority,
        }
        sort_col = sort_col_map.get(sort_by, TierLocation.created_at)
        stmt = stmt.order_by(sort_col.desc() if sort_dir == "desc" else sort_col.asc())
        stmt = stmt.limit(page_size).offset((page - 1) * page_size)

        result = await self.db.execute(stmt)
        locs = result.scalars().all()

        tier_ids = {l.tier_id for l in locs}
        tier_map: dict = {}
        if tier_ids:
            tres = await self.db.execute(select(PricingTier).where(PricingTier.id.in_(tier_ids)))
            tier_map = {t.id: t for t in tres.scalars().all()}

        conflicts = await self.find_zipcode_conflicts()
        items = []
        for l in locs:
            d = self._loc_dict(l)
            t = tier_map.get(l.tier_id)
            d["tier_name"] = t.name if t else None
            d["tier_code"] = t.code if t else None
            is_conflict = bool(l.zipcode) and l.zipcode in conflicts and l.is_active
            d["has_conflict"] = is_conflict
            d["conflict_status"] = "Duplicate Zipcode" if is_conflict else "Clean"
            items.append(d)

        return {
            "items": items,
            "locations": items,  # backward-compat alias
            "pagination": {
                "page": page, "page_size": page_size, "total": total,
                "total_pages": max(1, (total + page_size - 1) // page_size),
            },
            "sort": {"sort_by": sort_by, "sort_dir": sort_dir},
            "filters_applied": {
                "tier_id": str(tier_id) if tier_id else None, "q": q, "state": state,
                "district": district, "city": city, "zipcode": zipcode,
                "is_active": is_active, "has_conflict": has_conflict,
            },
        }

    async def find_zipcode_conflicts(self) -> set[str]:
        """Zipcodes with more than one active, non-deleted tier-location mapping."""
        stmt = (
            select(TierLocation.zipcode)
            .where(TierLocation.deleted_at.is_(None), TierLocation.is_active == True,
                   TierLocation.zipcode.isnot(None))
            .group_by(TierLocation.zipcode)
            .having(func.count() > 1)
        )
        result = await self.db.execute(stmt)
        return {row[0] for row in result.all()}

    async def get_tier_location_summary(self) -> dict:
        total = (await self.db.execute(
            select(func.count()).select_from(TierLocation).where(TierLocation.deleted_at.is_(None))
        )).scalar_one()
        mapped_cities = (await self.db.execute(
            select(func.count(func.distinct(TierLocation.city))).where(
                TierLocation.deleted_at.is_(None), TierLocation.city.isnot(None))
        )).scalar_one()
        mapped_zipcodes = (await self.db.execute(
            select(func.count(func.distinct(TierLocation.zipcode))).where(
                TierLocation.deleted_at.is_(None), TierLocation.zipcode.isnot(None))
        )).scalar_one()
        mapped_districts = (await self.db.execute(
            select(func.count(func.distinct(TierLocation.district))).where(
                TierLocation.deleted_at.is_(None), TierLocation.district.isnot(None))
        )).scalar_one()
        mapped_states = (await self.db.execute(
            select(func.count(func.distinct(TierLocation.state))).where(
                TierLocation.deleted_at.is_(None), TierLocation.state.isnot(None))
        )).scalar_one()
        inactive = (await self.db.execute(
            select(func.count()).select_from(TierLocation).where(
                TierLocation.deleted_at.is_(None), TierLocation.is_active == False)
        )).scalar_one()
        conflicts = await self.find_zipcode_conflicts()
        recently_imported = (await self.db.execute(
            select(func.count()).select_from(LocationImportBatch).where(
                LocationImportBatch.status == "completed")
        )).scalar_one()
        return {
            "total_mappings": total,
            "mapped_cities": mapped_cities,
            "mapped_zipcodes": mapped_zipcodes,
            "mapped_districts": mapped_districts,
            "mapped_states": mapped_states,
            "duplicate_zipcodes": len(conflicts),
            "inactive_mappings": inactive,
            "recently_imported": recently_imported,
        }

    async def export_tier_locations(self, **filters) -> list[dict]:
        filters.setdefault("page", 1)
        filters["page_size"] = 5000
        data = await self.list_tier_locations(**filters)
        return data["items"]

    # ── CSV Import Wizard ────────────────────────────────────────────────────────

    async def import_tier_locations_preview(self, file_name: str, csv_text: str) -> dict:
        reader = csv.DictReader(io.StringIO(csv_text))
        rows = list(reader)

        tier_codes = {(r.get("tier_code") or "").strip().lower() for r in rows if r.get("tier_code")}
        tier_by_code: dict[str, PricingTier] = {}
        if tier_codes:
            tres = await self.db.execute(
                select(PricingTier).where(func.lower(PricingTier.code).in_(tier_codes),
                                           PricingTier.deleted_at.is_(None)))
            tier_by_code = {t.code.lower(): t for t in tres.scalars().all()}

        existing_zips_result = await self.db.execute(
            select(TierLocation.zipcode).where(
                TierLocation.deleted_at.is_(None), TierLocation.is_active == True,
                TierLocation.zipcode.isnot(None)))
        existing_zips = {r[0] for r in existing_zips_result.all()}

        validated = []
        valid_count = invalid_count = conflict_count = 0
        for i, row in enumerate(rows, start=1):
            errors: list[str] = []
            country   = (row.get("country") or "").strip()
            state     = (row.get("state") or "").strip()
            city      = (row.get("city") or "").strip()
            zipcode   = (row.get("zipcode") or "").strip()
            tier_code = (row.get("tier_code") or "").strip().lower()

            if not country:
                errors.append("country is required")
            if not city:
                errors.append("city is required")
            if not tier_code or tier_code not in tier_by_code:
                errors.append(f"tier_code '{row.get('tier_code')}' does not resolve to an existing tier")

            is_conflict = bool(zipcode) and zipcode in existing_zips
            if is_conflict:
                conflict_count += 1
            if errors:
                invalid_count += 1
            else:
                valid_count += 1

            validated.append({
                "row_no": i, "country": country, "state": state or None,
                "district": (row.get("district") or "").strip() or None,
                "city": city, "zipcode": zipcode or None,
                "tier_code": tier_code, "zone_code": (row.get("zone_code") or "").strip() or None,
                "status": (row.get("status") or "active").strip(),
                "errors": errors, "conflict": is_conflict,
            })

        batch = LocationImportBatch(
            status="preview", file_name=file_name, uploaded_by_user_id=self.actor_id,
            total_rows=len(rows), valid_rows=valid_count, invalid_rows=invalid_count,
            conflict_rows=conflict_count, preview_payload={"rows": validated},
        )
        self.db.add(batch)
        await self.db.flush()

        return {
            "batch_id": str(batch.id), "total_rows": len(rows),
            "valid_rows": valid_count, "invalid_rows": invalid_count, "conflict_rows": conflict_count,
            "sample_rows": validated[:20],
        }

    async def import_tier_locations_confirm(self, batch_id: uuid.UUID,
                                             conflict_resolution: str = "skip") -> dict:
        self._assert_tier_writes_retired()
        batch = await self._load_import_batch(batch_id)
        if batch.status != "preview":
            raise ServiceOSException("IMPORT_BATCH_ALREADY_PROCESSED",
                f"Import batch is already '{batch.status}'.", status_code=409)
        if conflict_resolution not in ("skip", "override"):
            raise ServiceOSException("INVALID_CONFLICT_RESOLUTION",
                "conflict_resolution must be 'skip' or 'override'.", status_code=422)

        rows = (batch.preview_payload or {}).get("rows", [])
        tier_codes = {r["tier_code"] for r in rows if r.get("tier_code")}
        tier_by_code: dict[str, PricingTier] = {}
        if tier_codes:
            tres = await self.db.execute(
                select(PricingTier).where(func.lower(PricingTier.code).in_(tier_codes),
                                           PricingTier.deleted_at.is_(None)))
            tier_by_code = {t.code.lower(): t for t in tres.scalars().all()}

        created = skipped = 0
        report_rows = []
        for row in rows:
            if row.get("errors"):
                skipped += 1
                report_rows.append({**row, "action": "skipped", "reason": "validation_error"})
                continue
            if row.get("conflict") and conflict_resolution == "skip":
                skipped += 1
                report_rows.append({**row, "action": "skipped", "reason": "zipcode_conflict"})
                continue

            tier = tier_by_code.get(row["tier_code"])
            if not tier:
                skipped += 1
                report_rows.append({**row, "action": "skipped", "reason": "tier_not_found"})
                continue

            if row.get("conflict") and conflict_resolution == "override" and row.get("zipcode"):
                existing_result = await self.db.execute(
                    select(TierLocation).where(TierLocation.zipcode == row["zipcode"],
                                                TierLocation.is_active == True,
                                                TierLocation.deleted_at.is_(None)))
                for existing in existing_result.scalars().all():
                    existing.is_active = False
                    existing.deleted_at = utcnow()

            loc = TierLocation(
                tier_id=tier.id, country=row.get("country") or "India",
                state=row.get("state"), district=row.get("district"),
                city=(row.get("city") or "").strip().lower() or None, zipcode=row.get("zipcode"),
                zone_name=row.get("zone_code"), priority=100,
                is_active=(row.get("status", "active") == "active"),
            )
            self.db.add(loc)
            created += 1
            report_rows.append({**row, "action": "created"})

        batch.status = "completed"
        batch.created_rows = created
        batch.skipped_rows = skipped
        batch.conflict_resolution = conflict_resolution
        batch.report_payload = {"rows": report_rows}
        await self.db.flush()
        await self._audit("location_import_batch", batch.id, "import_confirm", None, batch.to_dict(),
                           f"Imported {created} tier-location mappings ({skipped} skipped)")
        return batch.to_dict()

    async def get_import_batch(self, batch_id: uuid.UUID) -> dict:
        return (await self._load_import_batch(batch_id)).to_dict()

    async def _load_import_batch(self, batch_id: uuid.UUID) -> LocationImportBatch:
        result = await self.db.execute(
            select(LocationImportBatch).where(LocationImportBatch.id == batch_id))
        batch = result.scalar_one_or_none()
        if not batch:
            raise NotFoundException("LocationImportBatch", str(batch_id))
        return batch

    async def create_tier_location(self, data: dict) -> dict:
        self._assert_tier_writes_retired()
        tier_id_raw = data.get("tier_id")
        if not tier_id_raw:
            raise ServiceOSException("TIER_NOT_FOUND", "tier_id is required.", status_code=422)
        tier_id = uuid.UUID(str(tier_id_raw))
        await self._load_tier(tier_id)  # validates tier exists

        city    = (data.get("city") or "").strip().lower() or None
        zipcode = (data.get("zipcode") or "").strip() or None
        if not city and not zipcode:
            raise ServiceOSException("TIER_LOCATION_CITY_OR_ZIP", "At least city or zipcode is required.", status_code=422)

        loc = TierLocation(
            tier_id=tier_id,
            country=data.get("country", "India") or "India",
            state=data.get("state") or None,
            district=data.get("district") or None,
            city=city,
            zipcode=zipcode,
            zone_name=data.get("zone_name") or None,
            priority=int(data.get("priority", 100) or 100),
            is_active=True,
        )
        self.db.add(loc)
        await self.db.flush()
        await self._audit("tier_location", loc.id, "create", None, self._loc_dict(loc),
                           f"Mapped {city or zipcode} to tier")
        return self._loc_dict(loc)

    async def update_tier_location(self, location_id: uuid.UUID, data: dict) -> dict:
        self._assert_tier_writes_retired()
        loc = await self._load_tier_location(location_id)
        old = self._loc_dict(loc)
        for field in ("city", "zipcode", "state", "district", "zone_name", "priority", "is_active", "tier_id"):
            if field in data and data[field] is not None:
                setattr(loc, field, data[field])
        await self.db.flush()
        await self._audit("tier_location", loc.id, "update", old, self._loc_dict(loc), "Updated tier location")
        return self._loc_dict(loc)

    async def delete_tier_location(self, location_id: uuid.UUID) -> dict:
        self._assert_tier_writes_retired()
        loc = await self._load_tier_location(location_id)
        old = self._loc_dict(loc)
        loc.is_active = False
        loc.deleted_at = utcnow()
        await self.db.flush()
        await self._audit("tier_location", loc.id, "deactivate", old, self._loc_dict(loc), "Deactivated tier location")
        return {"deleted": True, "location_id": str(location_id)}

    async def bulk_change_tier_locations(self, location_ids: list[str], new_tier_id: str) -> dict:
        self._assert_tier_writes_retired()
        if not location_ids:
            raise ServiceOSException("BULK_EMPTY", "location_ids is required.", status_code=422)
        tier_uuid = uuid.UUID(str(new_tier_id))
        await self._load_tier(tier_uuid)
        ids = [uuid.UUID(i) for i in location_ids]
        await self.db.execute(
            sa_update(TierLocation)
            .where(TierLocation.id.in_(ids), TierLocation.deleted_at.is_(None))
            .values(tier_id=tier_uuid)
        )
        await self.db.commit()
        return {"updated": len(ids), "new_tier_id": str(tier_uuid)}

    async def bulk_deactivate_tier_locations(self, location_ids: list[str]) -> dict:
        self._assert_tier_writes_retired()
        if not location_ids:
            raise ServiceOSException("BULK_EMPTY", "location_ids is required.", status_code=422)
        ids = [uuid.UUID(i) for i in location_ids]
        await self.db.execute(
            sa_update(TierLocation)
            .where(TierLocation.id.in_(ids), TierLocation.deleted_at.is_(None))
            .values(is_active=False)
        )
        await self.db.commit()
        return {"deactivated": len(ids)}

    async def list_import_batches(self, page: int = 1, page_size: int = 20) -> dict:
        count_total = (await self.db.execute(select(func.count()).select_from(LocationImportBatch))).scalar_one()
        stmt = (select(LocationImportBatch)
                .order_by(LocationImportBatch.created_at.desc())
                .limit(page_size).offset((page - 1) * page_size))
        result = await self.db.execute(stmt)
        batches = result.scalars().all()
        return {
            "batches": [b.to_dict() for b in batches],
            "pagination": {
                "page": page, "page_size": page_size, "total": count_total,
                "total_pages": max(1, (count_total + page_size - 1) // page_size),
            },
        }

    async def resolve_conflict_location(self, location_id: uuid.UUID,
                                         resolution_type: str,
                                         override_tier_id: str | None = None) -> dict:
        loc = await self._load_tier_location(location_id)
        if resolution_type == "keep_this":
            if loc.zipcode:
                conflicts = await self.db.execute(
                    select(TierLocation).where(
                        TierLocation.zipcode == loc.zipcode,
                        TierLocation.id != loc.id,
                        TierLocation.is_active == True,
                        TierLocation.deleted_at.is_(None),
                    )
                )
                for other in conflicts.scalars().all():
                    other.is_active = False
        elif resolution_type == "override_tier" and override_tier_id:
            tier_uuid = uuid.UUID(str(override_tier_id))
            await self._load_tier(tier_uuid)
            loc.tier_id = tier_uuid
        elif resolution_type == "deactivate":
            loc.is_active = False
        await self.db.commit()
        return {"resolved": True, "location_id": str(location_id), "resolution_type": resolution_type}

    async def resolve_location(self, city: str | None, zipcode: str | None,
                                state: str | None = None, country: str | None = None,
                                district: str | None = None, zone: str | None = None) -> dict:
        """Return the most specific tier for a given location.
        Priority: zipcode > city > state. Inactive tiers ignored."""
        city_norm = (city or "").strip().lower() or None
        zip_norm  = (zipcode or "").strip() or None
        path: list[str] = []

        # Try zipcode first
        if zip_norm:
            path.append(f"Checked zipcode '{zip_norm}' for an active mapping.")
            result = await self.db.execute(
                select(TierLocation).where(
                    TierLocation.zipcode == zip_norm,
                    TierLocation.is_active == True,
                    TierLocation.deleted_at.is_(None),
                ).order_by(TierLocation.priority.desc()).limit(1)
            )
            loc = result.scalar_one_or_none()
            if loc:
                tier_res = await self.db.execute(
                    select(PricingTier).where(PricingTier.id == loc.tier_id, PricingTier.is_active == True))
                tier = tier_res.scalar_one_or_none()
                if tier:
                    path.append(f"Found active zipcode mapping — applied tier '{tier.name}' (priority {loc.priority}).")
                    if city_norm:
                        path.append("Skipped city fallback because a zipcode match exists.")
                    return {"matched_by": "zipcode", "tier": self._tier_dict(tier), "resolution_path": path}
                path.append("Zipcode mapping found but its tier is inactive — ignoring.")
            else:
                path.append("No active zipcode mapping found.")

        # Try city
        if city_norm:
            path.append(f"Checked city '{city_norm}' for an active mapping (no zipcode override).")
            result = await self.db.execute(
                select(TierLocation).where(
                    TierLocation.city == city_norm,
                    TierLocation.zipcode.is_(None),
                    TierLocation.is_active == True,
                    TierLocation.deleted_at.is_(None),
                ).order_by(TierLocation.priority.desc()).limit(1)
            )
            loc = result.scalar_one_or_none()
            if loc:
                tier_res = await self.db.execute(
                    select(PricingTier).where(PricingTier.id == loc.tier_id, PricingTier.is_active == True))
                tier = tier_res.scalar_one_or_none()
                if tier:
                    path.append(f"Found active city mapping — applied tier '{tier.name}' (priority {loc.priority}).")
                    return {"matched_by": "city", "tier": self._tier_dict(tier), "resolution_path": path}
                path.append("City mapping found but its tier is inactive — ignoring.")
            else:
                path.append("No active city mapping found.")

        # Try district
        dist_norm = (district or "").strip().lower() or None
        if dist_norm:
            path.append(f"Checked district '{dist_norm}' for an active mapping.")
            result = await self.db.execute(
                select(TierLocation).where(
                    func.lower(TierLocation.district) == dist_norm,
                    TierLocation.city.is_(None), TierLocation.zipcode.is_(None),
                    TierLocation.is_active == True, TierLocation.deleted_at.is_(None),
                ).order_by(TierLocation.priority.desc()).limit(1)
            )
            loc = result.scalar_one_or_none()
            if loc:
                tier_res = await self.db.execute(
                    select(PricingTier).where(PricingTier.id == loc.tier_id, PricingTier.is_active == True))
                tier = tier_res.scalar_one_or_none()
                if tier:
                    path.append(f"Found active district mapping — applied tier '{tier.name}'.")
                    return {"matched_by": "district", "tier": self._tier_dict(tier), "resolution_path": path}
                path.append("District mapping found but its tier is inactive — ignoring.")
            else:
                path.append("No active district mapping found.")

        # Try zone
        zone_norm = (zone or "").strip().lower() or None
        if zone_norm:
            path.append(f"Checked zone '{zone_norm}' for an active mapping.")
            result = await self.db.execute(
                select(TierLocation).where(
                    func.lower(TierLocation.zone_name) == zone_norm,
                    TierLocation.city.is_(None), TierLocation.zipcode.is_(None),
                    TierLocation.is_active == True, TierLocation.deleted_at.is_(None),
                ).order_by(TierLocation.priority.desc()).limit(1)
            )
            loc = result.scalar_one_or_none()
            if loc:
                tier_res = await self.db.execute(
                    select(PricingTier).where(PricingTier.id == loc.tier_id, PricingTier.is_active == True))
                tier = tier_res.scalar_one_or_none()
                if tier:
                    path.append(f"Found active zone mapping — applied tier '{tier.name}'.")
                    return {"matched_by": "zone", "tier": self._tier_dict(tier), "resolution_path": path}
                path.append("Zone mapping found but its tier is inactive — ignoring.")
            else:
                path.append("No active zone mapping found.")

        path.append("No tier matched for the given location — platform default applies.")
        return {"matched_by": None, "tier": None, "resolution_path": path}

    async def _load_tier_location(self, location_id: uuid.UUID) -> TierLocation:
        result = await self.db.execute(
            select(TierLocation).where(TierLocation.id == location_id, TierLocation.deleted_at.is_(None)))
        loc = result.scalar_one_or_none()
        if not loc:
            raise NotFoundException("TierLocation", str(location_id))
        return loc

    def _loc_dict(self, l: TierLocation) -> dict:
        if l.zipcode:
            mt = "Zipcode"
        elif l.city:
            mt = "City"
        elif l.district:
            mt = "District"
        elif l.zone_name:
            mt = "Zone"
        elif l.state:
            mt = "State"
        else:
            mt = "Country"
        return {
            "location_id": str(l.id), "tier_id": str(l.tier_id),
            "country": l.country, "state": l.state, "district": l.district,
            "city": l.city, "zipcode": l.zipcode, "zone_name": l.zone_name,
            "priority": l.priority, "is_active": l.is_active,
            "mapping_type": mt, "source": "manual",
            "created_at": l.created_at.isoformat() if getattr(l, "created_at", None) else None,
            "updated_at": l.updated_at.isoformat() if getattr(l, "updated_at", None) else None,
        }

    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
    # SERVICE CATEGORIES
    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

    async def list_categories(self, is_active: bool | None = None) -> dict:
        stmt = select(ServiceCategory)
        if is_active is not None:
            stmt = stmt.where(ServiceCategory.is_active == is_active)
        stmt = stmt.order_by(ServiceCategory.display_order, ServiceCategory.name)
        result = await self.db.execute(stmt)
        cats = result.scalars().all()
        return {"categories": [self._cat_dict(c) for c in cats]}

    async def get_category(self, category_id: uuid.UUID) -> dict:
        cat = await self._load_category(category_id)
        return self._cat_dict(cat)

    # DEPRECATED entry point (kept for backward compatibility with existing
    # callers/tests that still pass requires_brand/requires_schedule/etc).
    # NOT the path the corrected "New Business Vertical" form uses; see
    # create_category_canonical below.
    async def create_category(self, data: dict) -> dict:
        name = (data.get("name") or "").strip()
        if not name:
            raise ServiceOSException("SERVICE_CATEGORY_NAME_REQUIRED", "Category name is required.", status_code=422)
        slug = _slugify(name)
        existing = await self.db.execute(
            select(ServiceCategory).where(ServiceCategory.slug == slug))
        if existing.scalar_one_or_none():
            raise ServiceOSException("SERVICE_CATEGORY_SLUG_DUPLICATE", f"Category slug '{slug}' already exists.", status_code=409)
        # Validate optional universal fields
        vt = data.get("vertical_type")
        if vt and vt not in VALID_VERTICAL_TYPES:
            raise ServiceOSException("INVALID_VERTICAL_TYPE",
                f"vertical_type '{vt}' is not valid. Choose from: {sorted(VALID_VERTICAL_TYPES)}",
                status_code=422)
        fm = data.get("finance_model")
        if fm and fm not in VALID_FINANCE_MODELS:
            raise ServiceOSException("INVALID_FINANCE_MODEL",
                f"finance_model '{fm}' is not valid. Choose from: {sorted(VALID_FINANCE_MODELS)}",
                status_code=422)
        cft = data.get("customer_flow_type")
        if cft and cft not in VALID_CUSTOMER_FLOW_TYPES:
            raise ServiceOSException("INVALID_CUSTOMER_FLOW_TYPE",
                f"customer_flow_type '{cft}' is not valid. Choose from: {sorted(VALID_CUSTOMER_FLOW_TYPES)}",
                status_code=422)
        pbm = data.get("provider_business_model")
        if pbm and pbm not in VALID_PROVIDER_BUSINESS_MODELS:
            raise ServiceOSException("INVALID_PROVIDER_BUSINESS_MODEL",
                f"provider_business_model '{pbm}' is not valid.",
                status_code=422)
        cat = ServiceCategory(
            name=name, slug=slug,
            description=data.get("description"),
            icon_url=data.get("icon_url"),
            image_url=data.get("image_url"),
            display_order=int(data.get("display_order", 0) or 0),
            is_active=True,
            vertical_type=vt,
            finance_model=fm,
            customer_flow_type=cft,
            provider_business_model=pbm,
            requires_location=bool(data.get("requires_location", True)),
            requires_schedule=bool(data.get("requires_schedule", False)),
            requires_brand=bool(data.get("requires_brand", False)),
            requires_service_option=bool(data.get("requires_service_option", False)),
            requires_issue_type=bool(data.get("requires_issue_type", False)),
            tenant_selectable=bool(data.get("tenant_selectable", True)),
            pricing_supported=bool(data.get("pricing_supported", True)),
        )
        self.db.add(cat)
        await self.db.flush()
        return self._cat_dict(cat)

    # Ownership correction (migration 160) -- the CANONICAL creation path.
    # This is what the corrected "New Business Vertical" form calls.
    # requires_location/requires_schedule/requires_brand/
    # requires_service_option/requires_issue_type/pricing_supported vary by
    # Master Service and Job Type and must never be set globally for an
    # entire vertical -- rejected outright, not silently dropped.
    CATEGORY_FORBIDDEN_CREATE_FIELDS = {
        "requires_location", "requires_schedule", "requires_brand",
        "requires_service_option", "requires_issue_type", "pricing_supported",
    }

    async def create_category_canonical(self, data: dict) -> dict:
        forbidden = set(data) & self.CATEGORY_FORBIDDEN_CREATE_FIELDS
        if forbidden:
            raise ServiceOSException(
                "FIELD_OWNED_BY_JOB_TYPE_BLUEPRINT",
                f"{sorted(forbidden)} vary by Master Service and Job Type and cannot be set on a "
                "Business Vertical. Configure them per service in its Job-Type Blueprint.",
                status_code=422)

        name = (data.get("name") or "").strip()
        if not name:
            raise ServiceOSException("SERVICE_CATEGORY_NAME_REQUIRED", "Category name is required.", status_code=422)
        slug = _slugify(name)
        existing = await self.db.execute(select(ServiceCategory).where(ServiceCategory.slug == slug))
        if existing.scalar_one_or_none():
            raise ServiceOSException("SERVICE_CATEGORY_SLUG_DUPLICATE", f"Category slug '{slug}' already exists.", status_code=409)

        # Validate optional universal fields. Bug fix: this canonical create
        # path (migration 160's "New Business Vertical") validated and set
        # finance_model but silently dropped vertical_type/customer_flow_type/
        # provider_business_model -- all three are NOT in
        # CATEGORY_FORBIDDEN_CREATE_FIELDS (they aren't Job-Type Blueprint
        # fields, unlike requires_location etc.) and update_category has
        # always accepted them; they were just never wired into this
        # constructor. A vertical created here landed with all three null
        # even though the edit form marks Vertical Type/Customer Flow Type as
        # required, leaving every newly-created vertical in a half-configured
        # state (e.g. never matching FIELD_OPS_VERTICALS/vertical_type
        # filters) until an admin remembered to open Edit and fill them in.
        vt = data.get("vertical_type")
        if vt and vt not in VALID_VERTICAL_TYPES:
            raise ServiceOSException("INVALID_VERTICAL_TYPE",
                f"vertical_type '{vt}' is not valid. Choose from: {sorted(VALID_VERTICAL_TYPES)}",
                status_code=422)
        fm = data.get("finance_model")
        if fm and fm not in VALID_FINANCE_MODELS:
            raise ServiceOSException("INVALID_FINANCE_MODEL",
                f"finance_model '{fm}' is not valid. Choose from: {sorted(VALID_FINANCE_MODELS)}",
                status_code=422)
        cft = data.get("customer_flow_type")
        if cft and cft not in VALID_CUSTOMER_FLOW_TYPES:
            raise ServiceOSException("INVALID_CUSTOMER_FLOW_TYPE",
                f"customer_flow_type '{cft}' is not valid. Choose from: {sorted(VALID_CUSTOMER_FLOW_TYPES)}",
                status_code=422)
        pbm = data.get("provider_business_model")
        if pbm and pbm not in VALID_PROVIDER_BUSINESS_MODELS:
            raise ServiceOSException("INVALID_PROVIDER_BUSINESS_MODEL",
                f"provider_business_model '{pbm}' is not valid.",
                status_code=422)

        cat = ServiceCategory(
            name=name, slug=slug,
            description=data.get("description"),
            icon_url=data.get("icon_url"),
            image_url=data.get("image_url"),
            display_order=int(data.get("display_order", 0) or 0),
            is_active=bool(data.get("is_active", True)),
            vertical_type=vt,
            finance_model=fm,
            customer_flow_type=cft,
            provider_business_model=pbm,
            tenant_selectable=bool(data.get("tenant_selectable", True)),
            is_customer_visible=bool(data.get("is_customer_visible", True)),
            is_provider_registerable=bool(data.get("registration_available", True)),
            # Legacy columns get honest, non-restrictive defaults -- they no
            # longer gate anything for a canonically-created vertical.
            requires_location=False, requires_schedule=False, requires_brand=False,
            requires_service_option=False, requires_issue_type=False, pricing_supported=False,
        )
        self.db.add(cat)
        await self.db.flush()
        return self._cat_dict(cat)

    # DEPRECATED (migration 160): requires_location/requires_schedule/
    # requires_brand/requires_service_option/requires_issue_type/
    # pricing_supported still accept writes here ONLY for backward
    # compatibility with existing callers -- NOT authoritative once a
    # service has its own Job-Type Blueprint. The corrected "New Business
    # Vertical" (formerly "New Service Category") create path rejects them.
    async def update_category(self, category_id: uuid.UUID, data: dict) -> dict:
        cat = await self._load_category(category_id)
        updatable = (
            "name", "description", "icon_url", "image_url", "banner_url",
            "display_order", "is_active", "category_type", "primary_engine_key",
            "customer_flow_type", "frontend_component_key", "provider_dashboard_type",
            "is_provider_registerable", "is_customer_visible", "monetization_model",
            # Sprint 38 universal fields
            "vertical_type", "finance_model", "provider_business_model",
            "requires_location", "requires_schedule", "requires_brand",
            "requires_service_option", "requires_issue_type",
            "tenant_selectable", "pricing_supported",
        )
        vt = data.get("vertical_type")
        if vt and vt not in VALID_VERTICAL_TYPES:
            raise ServiceOSException("INVALID_VERTICAL_TYPE",
                f"vertical_type '{vt}' is not valid.", status_code=422)
        fm = data.get("finance_model")
        if fm and fm not in VALID_FINANCE_MODELS:
            raise ServiceOSException("INVALID_FINANCE_MODEL",
                f"finance_model '{fm}' is not valid.", status_code=422)
        cft = data.get("customer_flow_type")
        if cft and cft not in VALID_CUSTOMER_FLOW_TYPES:
            raise ServiceOSException("INVALID_CUSTOMER_FLOW_TYPE",
                f"customer_flow_type '{cft}' is not valid.", status_code=422)
        for field in updatable:
            if field in data and data[field] is not None:
                setattr(cat, field, data[field])
        await self.db.flush()
        return self._cat_dict(cat)

    async def delete_category(self, category_id: uuid.UUID) -> dict:
        cat = await self._load_category(category_id)
        # Check if any active master services exist
        svc_res = await self.db.execute(
            select(MasterService).where(
                MasterService.category_id == category_id,
                MasterService.is_active == True,
                MasterService.deleted_at.is_(None),
            ).limit(1))
        if svc_res.scalar_one_or_none():
            raise ServiceOSException(
                "SERVICE_CATEGORY_HAS_ACTIVE_SERVICES",
                "Cannot delete a category that has active services. Deactivate services first.",
                status_code=409)
        cat.is_active = False
        await self.db.flush()
        return {"deleted": True, "category_id": str(category_id)}

    async def hard_delete_category(self, category_id: uuid.UUID) -> dict:
        cat = await self._load_category(category_id)
        svc_res = await self.db.execute(
            select(MasterService).where(
                MasterService.category_id == category_id,
                MasterService.deleted_at.is_(None),
            ).limit(1))
        if svc_res.scalar_one_or_none():
            raise ServiceOSException(
                "SERVICE_CATEGORY_HAS_SERVICES",
                "Cannot permanently delete a category that has master services. Remove all services first.",
                status_code=409)
        await self.db.delete(cat)
        await self.db.flush()
        return {"deleted": True, "category_id": str(category_id), "hard_delete": True}

    async def _load_category(self, category_id: uuid.UUID) -> ServiceCategory:
        result = await self.db.execute(
            select(ServiceCategory).where(ServiceCategory.id == category_id))
        cat = result.scalar_one_or_none()
        if not cat:
            raise NotFoundException("ServiceCategory", str(category_id))
        return cat

    def _cat_dict(self, c: ServiceCategory) -> dict:
        return {
            "category_id": str(c.id), "name": c.name, "slug": c.slug,
            "description": c.description, "icon_url": c.icon_url, "image_url": c.image_url,
            "banner_url": c.banner_url,
            "display_order": c.display_order, "is_active": c.is_active,
            "category_type": c.category_type,
            "primary_engine_id": str(c.primary_engine_id) if c.primary_engine_id else None,
            "primary_engine_key": c.primary_engine_key,
            "customer_flow_type": c.customer_flow_type,
            "frontend_component_key": c.frontend_component_key,
            "provider_dashboard_type": c.provider_dashboard_type,
            "is_provider_registerable": c.is_provider_registerable,
            "is_customer_visible": c.is_customer_visible,
            "monetization_model": c.monetization_model,
            # Sprint 38 universal fields
            "vertical_type": c.vertical_type,
            "finance_model": c.finance_model,
            "provider_business_model": c.provider_business_model,
            "requires_location": c.requires_location,
            "requires_schedule": c.requires_schedule,
            "requires_brand": c.requires_brand,
            "requires_service_option": c.requires_service_option,
            "requires_issue_type": c.requires_issue_type,
            "tenant_selectable": c.tenant_selectable,
            "pricing_supported": c.pricing_supported,
            "created_at": c.created_at.isoformat() if c.created_at else None,
            "updated_at": c.updated_at.isoformat() if c.updated_at else None,
        }

    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
    # MASTER SERVICES
    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

    # ----- SERVICE GROUPS (Sprint 38) ----------------------------------------

    async def list_service_groups(
        self,
        category_id: uuid.UUID | None = None,
        status: str | None = None,
        limit: int = 200,
    ) -> dict:
        stmt = select(ServiceGroup).where(ServiceGroup.deleted_at.is_(None))
        if category_id:
            stmt = stmt.where(ServiceGroup.category_id == category_id)
        if status:
            stmt = stmt.where(ServiceGroup.status == status)
        stmt = stmt.order_by(ServiceGroup.display_order, ServiceGroup.name).limit(limit)
        result = await self.db.execute(stmt)
        groups = result.scalars().all()
        return {"groups": [g.to_dict() for g in groups], "total": len(groups)}

    async def get_service_group(self, group_id: uuid.UUID) -> dict:
        return await self.get_service_group_enterprise(group_id)

    async def create_service_group(self, data: dict) -> dict:
        name = (data.get("name") or "").strip()
        if not name:
            raise ServiceOSException("SERVICE_GROUP_NAME_REQUIRED", "Service group name is required.", status_code=422)
        category_id = data.get("category_id")
        if not category_id:
            raise ServiceOSException("SERVICE_GROUP_CATEGORY_REQUIRED", "category_id is required.", status_code=422)
        category = await self._load_category(uuid.UUID(str(category_id)))
        if not category.is_active:
            raise ServiceOSException("SERVICE_CATEGORY_INACTIVE", "A service group cannot be created in an inactive category.", status_code=422)
        code = (data.get("code") or "").strip() or re.sub(r"[^a-z0-9_]", "_", name.lower())[:100]
        slug = _slugify(name)
        existing_code = await self.db.execute(select(ServiceGroup).where(ServiceGroup.code == code))
        if existing_code.scalar_one_or_none():
            raise ServiceOSException("SERVICE_GROUP_CODE_DUPLICATE",
                f"Service group code '{code}' already exists.", status_code=409)
        existing_slug = await self.db.execute(select(ServiceGroup).where(ServiceGroup.slug == slug))
        if existing_slug.scalar_one_or_none():
            raise ServiceOSException("SERVICE_GROUP_SLUG_DUPLICATE",
                f"Service group slug '{slug}' already exists.", status_code=409)
        g = ServiceGroup(
            category_id=uuid.UUID(str(category_id)),
            code=code, name=name, slug=slug,
            description=data.get("description"),
            status=data.get("status", "active"),
            display_order=int(data.get("display_order", 0) or 0),
            icon_url=data.get("icon_url"),
            created_by_user_id=data.get("created_by_user_id"),
        )
        self.db.add(g)
        await self.db.flush()
        await self._audit("service_group", g.id, "create", None, g.to_dict(), f"Created service group '{g.name}'")
        return g.to_dict()

    async def update_service_group(self, group_id: uuid.UUID, data: dict) -> dict:
        g = await self._load_service_group(group_id)
        old = g.to_dict()
        expected_updated_at = data.get("expected_updated_at")
        if expected_updated_at and g.updated_at and g.updated_at.isoformat() != expected_updated_at:
            raise ServiceOSException(
                "SERVICE_GROUP_CONFLICT",
                "This service group changed after you opened it. Refresh and review the latest values.",
                status_code=409,
            )
        if "name" in data:
            name = (data.get("name") or "").strip()
            if not name:
                raise ServiceOSException("SERVICE_GROUP_NAME_REQUIRED", "Service group name is required.", status_code=422)
            g.name = name
        # Lifecycle is intentionally excluded: activate/deactivate are audited
        # commands and must not be smuggled through a generic metadata update.
        for field in ("name", "description", "icon_url", "display_order"):
            if field != "name" and field in data and data[field] is not None:
                setattr(g, field, data[field])
        if data.get("updated_by_user_id"):
            g.updated_by_user_id = data["updated_by_user_id"]
        await self.db.flush()
        await self._audit("service_group", g.id, "update", old, g.to_dict(), f"Updated service group '{g.name}'")
        return g.to_dict()

    async def _load_service_group(self, group_id: uuid.UUID) -> ServiceGroup:
        result = await self.db.execute(
            select(ServiceGroup).where(
                ServiceGroup.id == group_id,
                ServiceGroup.deleted_at.is_(None),
            ))
        g = result.scalar_one_or_none()
        if not g:
            raise NotFoundException("ServiceGroup", str(group_id))
        return g

    async def list_master_services(self, category_id: uuid.UUID | None = None,
                                    service_group_id: uuid.UUID | None = None,
                                    job_type: str | None = None,
                                    is_active: bool | None = None) -> dict:
        stmt = select(MasterService).where(MasterService.deleted_at.is_(None))
        if category_id:
            stmt = stmt.where(MasterService.category_id == category_id)
        if service_group_id:
            stmt = stmt.where(MasterService.service_group_id == service_group_id)
        if job_type:
            stmt = stmt.where(MasterService.job_type == job_type)
        if is_active is not None:
            stmt = stmt.where(MasterService.is_active == is_active)
        stmt = stmt.order_by(MasterService.display_order, MasterService.service_name)
        result = await self.db.execute(stmt)
        svcs = result.scalars().all()
        return {"services": [self._svc_dict(s) for s in svcs]}

    async def get_master_service(self, service_id: uuid.UUID) -> dict:
        svc = await self._load_master_service(service_id)
        return self._svc_dict(svc)

    async def _load_master_service_any(self, service_id: uuid.UUID) -> MasterService:
        result = await self.db.execute(select(MasterService).where(MasterService.id == service_id))
        svc = result.scalar_one_or_none()
        if not svc:
            raise NotFoundException("MasterService", str(service_id))
        return svc

    # DEPRECATED entry point (kept for backward compatibility -- the Home
    # Services Catalog Console, bulk setup wizard, and existing tests still
    # call this with a scalar job_type/pricing_model/price/requirement
    # payload). NOT the path the corrected "New Master Service" form uses;
    # see create_master_service_canonical below, which is what migration 160
    # actually adds. Left functionally unchanged -- see section 11's
    # instruction to preserve compatibility rather than break live callers.
    async def _inherit_directory_mappings(self, svc: MasterService) -> None:
        """Expand category/group directory rules into the canonical runtime tables."""
        type_ids = (await self.db.execute(select(ServiceTypeMapping.type_id).where(
            ServiceTypeMapping.status == "active",
            or_(ServiceTypeMapping.service_id == svc.id,
                and_(ServiceTypeMapping.service_id.is_(None), ServiceTypeMapping.service_group_id == svc.service_group_id),
                and_(ServiceTypeMapping.service_id.is_(None), ServiceTypeMapping.service_group_id.is_(None),
                     ServiceTypeMapping.category_id == svc.category_id)),
        ).distinct())).scalars().all()
        brand_ids = (await self.db.execute(select(BrandMapping.brand_id).where(
            BrandMapping.status == "active",
            or_(BrandMapping.service_id == svc.id,
                and_(BrandMapping.service_id.is_(None), BrandMapping.service_group_id == svc.service_group_id),
                and_(BrandMapping.service_id.is_(None), BrandMapping.service_group_id.is_(None),
                     BrandMapping.category_id == svc.category_id)),
        ).distinct())).scalars().all()
        for type_id in type_ids:
            self.db.add(MasterServiceType(master_service_id=svc.id, service_type_id=type_id, is_active=True))
        for brand_id in brand_ids:
            self.db.add(MasterServiceBrand(master_service_id=svc.id, brand_id=brand_id,
                is_active=True, status="active", created_by_user_id=self.actor_id))
        await self.db.flush()

    async def create_master_service(self, data: dict) -> dict:
        name     = (data.get("service_name") or "").strip()
        job_type = (data.get("job_type") or "").strip()
        model    = (data.get("pricing_model") or "").strip()
        cat_id_raw = data.get("category_id")

        if not name:
            raise ServiceOSException("MASTER_SERVICE_NAME_REQUIRED", "service_name is required.", status_code=422)
        if not job_type or job_type not in VALID_JOB_TYPES:
            raise ServiceOSException("INVALID_JOB_TYPE", f"job_type must be one of {sorted(VALID_JOB_TYPES)}.", status_code=422)
        if not model or model not in VALID_PRICING_MODELS:
            raise ServiceOSException("INVALID_PRICING_MODEL", f"pricing_model must be one of {sorted(VALID_PRICING_MODELS)}.", status_code=422)
        if not cat_id_raw:
            raise ServiceOSException("SERVICE_CATEGORY_NOT_FOUND", "category_id is required.", status_code=422)

        cat_id = uuid.UUID(str(cat_id_raw))
        cat = await self._load_category(cat_id)
        if not cat.is_active:
            raise ServiceOSException("SERVICE_CATEGORY_INACTIVE", "The selected category is inactive.", status_code=422)

        group_id = None
        if data.get("service_group_id"):
            group_id = uuid.UUID(str(data["service_group_id"]))
            group = await self._load_service_group(group_id)
            if group.category_id != cat_id:
                raise ServiceOSException(
                    "SERVICE_GROUP_CATEGORY_MISMATCH",
                    "The selected service group does not belong to the selected category.",
                    status_code=422,
                )

        _validate_pricing_config(model, data)

        slug = _slugify(name)
        existing = await self.db.execute(
            select(MasterService).where(MasterService.slug == slug, MasterService.deleted_at.is_(None)))
        if existing.scalar_one_or_none():
            slug = f"{slug}-{str(uuid.uuid4())[:8]}"

        def _d(key, default=None):
            v = data.get(key)
            return Decimal(str(v)) if v is not None else default

        svc = MasterService(
            category_id=cat_id, service_name=name, slug=slug,
            description=data.get("description"),
            image_url=data.get("image_url"),
            icon_url=data.get("icon_url"),
            job_type=job_type, pricing_model=model,
            # flat price fields (nulled for irrelevant models)
            base_price=_d("base_price", Decimal("0")),
            min_price=_d("min_price"),
            max_price=_d("max_price"),
            visit_fee=_d("visit_fee", Decimal("0")),
            pre_approval_limit=_d("pre_approval_limit"),
            default_estimate=_d("default_estimate"),
            # hourly fields
            hourly_rate=_d("hourly_rate"),
            minimum_billable_hours=_d("minimum_billable_hours"),
            estimated_hours=_d("estimated_hours"),
            maximum_hours=_d("maximum_hours"),
            # post-assessment fields
            assessment_label=data.get("assessment_label"),
            show_estimated_range=bool(data.get("show_estimated_range", False)),
            customer_note=data.get("customer_note"),
            # requirement flags
            estimated_duration_minutes=data.get("estimated_duration_minutes"),
            requires_checklist=bool(data.get("requires_checklist", False)),
            is_brand_required=bool(data.get("is_brand_required", False)),
            is_type_required=bool(data.get("is_type_required", False)),
            requires_issue_type=bool(data.get("requires_issue_type", False)),
            requires_schedule=bool(data.get("requires_schedule", False)),
            requires_address=bool(data.get("requires_address", False)),
            tenant_override_allowed=bool(data.get("tenant_override_allowed", False)),
            tenant_custom_name_allowed=bool(data.get("tenant_custom_name_allowed", True)),
            service_group_id=group_id,
            display_order=int(data.get("display_order", 0) or 0),
            is_active=True,
        )
        self.db.add(svc)
        await self.db.flush()
        await self._inherit_directory_mappings(svc)
        return self._svc_dict(svc)

    # Ownership correction (migration 160) -- the CANONICAL creation path.
    # This is what the corrected "New Master Service" form calls. Job-type-
    # agnostic: no job_type, pricing_model, prices, or Brand/Type/workflow
    # requirement flags. Submitting any of them is rejected outright (fail
    # closed, not silently dropped) since a real form should never send
    # them, not just because the current one shouldn't render them.
    MASTER_SERVICE_FORBIDDEN_CREATE_FIELDS = {
        "job_type", "pricing_model", "base_price", "min_price", "max_price", "visit_fee",
        "is_brand_required", "is_type_required", "requires_issue_type",
        "requires_checklist", "requires_schedule", "requires_address",
    }

    async def create_master_service_canonical(self, data: dict) -> dict:
        forbidden = set(data) & self.MASTER_SERVICE_FORBIDDEN_CREATE_FIELDS
        if forbidden:
            raise ServiceOSException(
                "FIELD_OWNED_BY_JOB_TYPE_BLUEPRINT",
                f"{sorted(forbidden)} belong to the Job-Type Blueprint (workflow/pricing behavior) "
                "or the tenant (actual prices), not Master Service creation. Add job types and "
                "configure their blueprint after creating the service.",
                status_code=422)

        name = (data.get("service_name") or "").strip()
        cat_id_raw = data.get("category_id")

        if not name:
            raise ServiceOSException("MASTER_SERVICE_NAME_REQUIRED", "service_name is required.", status_code=422)
        if not cat_id_raw:
            raise ServiceOSException("SERVICE_CATEGORY_NOT_FOUND", "category_id is required.", status_code=422)
        if not data.get("service_group_id"):
            raise ServiceOSException("SERVICE_GROUP_REQUIRED",
                "service_group_id is required -- Master Services belong to a Service Group.", status_code=422)

        cat_id = uuid.UUID(str(cat_id_raw))
        cat = await self._load_category(cat_id)
        if not cat.is_active:
            raise ServiceOSException("SERVICE_CATEGORY_INACTIVE", "The selected category is inactive.", status_code=422)

        group_id = uuid.UUID(str(data["service_group_id"]))
        group = await self._load_service_group(group_id)
        if group.category_id != cat_id:
            raise ServiceOSException(
                "SERVICE_GROUP_CATEGORY_MISMATCH",
                "The selected service group does not belong to the selected category.",
                status_code=422,
            )
        if group.status != "active":
            raise ServiceOSException(
                "SERVICE_GROUP_INACTIVE",
                "A master service can only be created inside an active service group.",
                status_code=422,
            )

        slug = _slugify(name)
        existing = await self.db.execute(
            select(MasterService).where(MasterService.slug == slug, MasterService.deleted_at.is_(None)))
        if existing.scalar_one_or_none():
            slug = f"{slug}-{str(uuid.uuid4())[:8]}"

        svc = MasterService(
            category_id=cat_id, service_name=name, slug=slug,
            description=data.get("description"),
            image_url=data.get("image_url"),
            icon_url=data.get("icon_url"),
            # job_type/pricing_model intentionally left NULL -- job-type-
            # agnostic at creation; job types are added afterward as child
            # records (master_service_job_types) with their own blueprint.
            base_price=Decimal("0"), visit_fee=Decimal("0"),
            tenant_override_allowed=bool(data.get("tenant_override_allowed", False)),
            tenant_custom_name_allowed=bool(data.get("tenant_custom_name_allowed", True)),
            service_group_id=group_id,
            display_order=int(data.get("display_order", 0) or 0),
            is_active=True,
        )
        self.db.add(svc)
        await self.db.flush()
        await self._inherit_directory_mappings(svc)
        result = self._svc_dict(svc)
        await self._audit("master_service", svc.id, "create", None, result,
                          f"Created master service '{svc.service_name}'")
        return result

    # Structural fields that define the shape of the tenant setup wizard --
    # changing any of these means existing tenant setups may need review
    # (spec: "service configuration update required"), unlike cosmetic
    # fields (name/description/icons) which never trigger a new version.
    BLUEPRINT_STRUCTURAL_FIELDS = ("job_type", "is_type_required", "is_brand_required", "pricing_model", "is_active")

    def _blueprint_snapshot(self, svc: MasterService) -> dict:
        return {
            "job_type": svc.job_type, "requires_type": svc.is_type_required,
            "requires_brand": svc.is_brand_required, "pricing_model": svc.pricing_model,
            "is_active": svc.is_active,
        }

    async def _publish_new_blueprint_version_if_structural_change(
        self, svc: MasterService, before: dict, actor_id: uuid.UUID | None = None,
    ) -> ServiceBlueprintVersion | None:
        after = self._blueprint_snapshot(svc)
        if before == after:
            return None
        changed = [k for k in before if before[k] != after[k]]
        summary = "; ".join(f"{k}: {before[k]!r} -> {after[k]!r}" for k in changed)

        latest_r = await self.db.execute(
            select(ServiceBlueprintVersion).where(
                ServiceBlueprintVersion.master_service_id == svc.id,
                ServiceBlueprintVersion.status == "published",
            ).order_by(ServiceBlueprintVersion.version_number.desc()).limit(1))
        latest = latest_r.scalar_one_or_none()
        next_version = (latest.version_number + 1) if latest else 1
        if latest:
            latest.status = "superseded"

        new_version = ServiceBlueprintVersion(
            master_service_id=svc.id, version_number=next_version, status="published",
            snapshot=after, change_summary=summary, published_at=utcnow(),
            published_by_user_id=actor_id,
        )
        self.db.add(new_version)
        await self.db.flush()
        return new_version

    # DEPRECATED (migration 160): requires_checklist/is_brand_required/
    # is_type_required/requires_issue_type/requires_schedule/requires_address
    # still accept writes here ONLY for backward compatibility with existing
    # callers (e.g. the Home Services Catalog Console) that predate the
    # Job-Type Blueprint -- they are NOT authoritative at runtime once a
    # master_service_job_types + service_job_workflow blueprint exists for a
    # service (see get_flow_config's canonical-first resolution). The
    # corrected "New Master Service" create path rejects them outright;
    # removal from this update path is the next step once the Catalog
    # Console is migrated to the Job-Type Blueprint UI.
    # MODULE-L5-56: base_price/min_price/max_price/visit_fee are now
    # tenant-owned only. TenantCatalogService.resolve_tenant_price already
    # implements exact, precedence-based tenant pricing (type+brand override
    # -> type -> brand -> tenant default -> none, "never falls back to
    # admin's price") and home_service_booking's estimator now prefers it
    # whenever a tenant is already selected on the draft. Admin can no
    # longer WRITE these four fields going forward; existing values remain
    # readable as the pre-assignment estimate fallback only (no historical
    # data deleted, no existing booking broken).
    _FORBIDDEN_ADMIN_PRICE_FIELDS = ("base_price", "min_price", "max_price", "visit_fee")

    def _reject_admin_price_fields(self, data: dict) -> None:
        present = [f for f in self._FORBIDDEN_ADMIN_PRICE_FIELDS if data.get(f) is not None]
        if present:
            raise ServiceOSException(
                "ADMIN_PRICING_NOT_ALLOWED",
                f"Admin cannot set pricing fields on a Master Service: {present}. "
                "Price is tenant-owned (Tenant Setup > Pricing).",
                status_code=422,
            )

    async def update_master_service(self, service_id: uuid.UUID, data: dict, actor_id: uuid.UUID | None = None) -> dict:
        self._reject_admin_price_fields(data)
        svc = await self._load_master_service(service_id)
        old = self._svc_dict(svc)
        expected_updated_at = data.get("expected_updated_at")
        if expected_updated_at and svc.updated_at and svc.updated_at.isoformat() != expected_updated_at:
            raise ServiceOSException(
                "MASTER_SERVICE_CONFLICT",
                "This master service changed after you opened it. Refresh and review the latest values.",
                status_code=409,
            )
        if "service_name" in data:
            name = (data.get("service_name") or "").strip()
            if not name:
                raise ServiceOSException("MASTER_SERVICE_NAME_REQUIRED", "service_name is required.", status_code=422)
            svc.service_name = name
        if data.get("service_group_id"):
            group_id = uuid.UUID(str(data["service_group_id"]))
            group = await self._load_service_group(group_id)
            if group.category_id != svc.category_id:
                raise ServiceOSException(
                    "SERVICE_GROUP_CATEGORY_MISMATCH",
                    "The selected service group does not belong to this service's category.",
                    status_code=422,
                )
            svc.service_group_id = group_id
        # Cosmetic assets are nullable. The old non-None guard made the
        # admin's explicit "Remove icon" action a successful no-op because
        # JSON null was silently discarded.
        for field in ("description", "image_url", "icon_url"):
            if field in data:
                setattr(svc, field, data[field])
        for field in ("service_name", "display_order",
                      "requires_checklist", "is_brand_required", "is_type_required",
                      "requires_issue_type", "requires_schedule", "requires_address",
                      "tenant_override_allowed", "tenant_custom_name_allowed",
                      "assessment_label", "show_estimated_range", "customer_note",
                      "estimated_duration_minutes"):
            if field != "service_name" and field in data and data[field] is not None:
                setattr(svc, field, data[field])
        for field in ("pre_approval_limit", "default_estimate", "hourly_rate",
                      "minimum_billable_hours", "estimated_hours", "maximum_hours"):
            if field in data and data[field] is not None:
                setattr(svc, field, Decimal(str(data[field])))
        if "job_type" in data and data["job_type"]:
            if data["job_type"] not in VALID_JOB_TYPES:
                raise ServiceOSException("INVALID_JOB_TYPE", "Invalid job_type.", status_code=422)
            svc.job_type = data["job_type"]
        if "pricing_model" in data and data["pricing_model"]:
            if data["pricing_model"] not in VALID_PRICING_MODELS:
                raise ServiceOSException("INVALID_PRICING_MODEL", "Invalid pricing_model.", status_code=422)
            svc.pricing_model = data["pricing_model"]
        # Build merged context for validation (ORM state + incoming changes)
        merged: dict = {
            "base_price":             float(svc.base_price) if svc.base_price else 0,
            "min_price":              float(svc.min_price) if svc.min_price else None,
            "max_price":              float(svc.max_price) if svc.max_price else None,
            "hourly_rate":            float(svc.hourly_rate) if svc.hourly_rate else None,
            "minimum_billable_hours": float(svc.minimum_billable_hours) if svc.minimum_billable_hours else None,
            "visit_fee":              float(svc.visit_fee) if svc.visit_fee else 0,
            "customer_note":          svc.customer_note,
        }
        merged.update(data)
        _validate_pricing_config(svc.pricing_model, merged)
        await self.db.flush()
        # NOTE: structural edits are no longer auto-published to a new
        # ServiceBlueprintVersion here -- they accumulate as a real "draft"
        # (see BlueprintImpactService.get_draft_status, which diffs this live
        # row against the latest PUBLISHED snapshot) until an admin calls the
        # explicit POST /v1/admin/catalog/blueprint/publish endpoint
        # (BlueprintImpactService.publish_draft).
        return self._svc_dict(svc)

    async def _load_master_service(self, service_id: uuid.UUID) -> MasterService:
        result = await self.db.execute(
            select(MasterService).where(MasterService.id == service_id, MasterService.deleted_at.is_(None)))
        svc = result.scalar_one_or_none()
        if not svc:
            raise NotFoundException("MasterService", str(service_id))
        return svc

    def _svc_dict(self, s: MasterService) -> dict:
        def _f(v): return float(v) if v is not None else None
        return {
            "service_id": str(s.id), "category_id": str(s.category_id),
            "service_name": s.service_name, "slug": s.slug, "description": s.description,
            "image_url": s.image_url, "icon_url": s.icon_url,
            "job_type": s.job_type, "pricing_model": s.pricing_model,
            # flat price fields
            "base_price": _f(s.base_price), "min_price": _f(s.min_price),
            "max_price": _f(s.max_price), "visit_fee": _f(s.visit_fee),
            "pre_approval_limit": _f(s.pre_approval_limit),
            "default_estimate": _f(s.default_estimate),
            # hourly fields
            "hourly_rate": _f(s.hourly_rate),
            "minimum_billable_hours": _f(s.minimum_billable_hours),
            "estimated_hours": _f(s.estimated_hours),
            "maximum_hours": _f(s.maximum_hours),
            # post-assessment fields
            "assessment_label": s.assessment_label,
            "show_estimated_range": s.show_estimated_range,
            "customer_note": s.customer_note,
            # timing
            "estimated_duration_minutes": s.estimated_duration_minutes,
            # requirement flags
            "requires_checklist": s.requires_checklist,
            "is_brand_required": s.is_brand_required,
            "is_type_required": s.is_type_required,
            "requires_issue_type": getattr(s, "requires_issue_type", False),
            "requires_schedule": getattr(s, "requires_schedule", False),
            "requires_address": getattr(s, "requires_address", False),
            "tenant_override_allowed": s.tenant_override_allowed,
            "tenant_custom_name_allowed": s.tenant_custom_name_allowed,
            "service_group_id": str(s.service_group_id) if s.service_group_id else None,
            "display_order": s.display_order, "is_active": s.is_active,
            "created_at": s.created_at.isoformat() if s.created_at else None,
            "updated_at": s.updated_at.isoformat() if s.updated_at else None,
            "deleted_at": s.deleted_at.isoformat() if s.deleted_at else None,
        }

    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
    # SERVICE TYPES
    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

    async def list_service_types(self, category_id: uuid.UUID | None = None,
                                   is_active: bool | None = None,
                                   master_service_id: uuid.UUID | None = None) -> dict:
        stmt = select(ServiceType).where(ServiceType.deleted_at.is_(None))
        if category_id:
            stmt = stmt.where(ServiceType.category_id == category_id)
        if is_active is not None:
            stmt = stmt.where(ServiceType.is_active == is_active)
        if master_service_id:
            # A service's Type picker shouldn't offer choices that only make
            # sense for a different service (e.g. "Split AC" while
            # configuring a Microwave) -- see cross_scoped_ids.
            from app.engines.admin_catalog.cross_scope import cross_scoped_ids
            excluded = await cross_scoped_ids(self.db, MasterServiceType, MasterServiceType.service_type_id, master_service_id)
            if excluded:
                stmt = stmt.where(ServiceType.id.notin_(excluded))
        stmt = stmt.order_by(ServiceType.name)
        result = await self.db.execute(stmt)
        types = result.scalars().all()
        return {"types": [self._type_dict(t) for t in types]}

    async def create_service_type(self, data: dict) -> dict:
        name = (data.get("name") or "").strip()
        if not name:
            raise ServiceOSException("SERVICE_TYPE_NAME_REQUIRED", "Service type name is required.", status_code=422)
        cat_id = uuid.UUID(str(data["category_id"])) if data.get("category_id") else None
        slug = _slugify(name)
        # Check uniqueness per-category (constraint is on category_id + slug)
        dup_stmt = select(ServiceType).where(ServiceType.slug == slug, ServiceType.deleted_at.is_(None))
        if cat_id:
            dup_stmt = dup_stmt.where(ServiceType.category_id == cat_id)
        if (await self.db.execute(dup_stmt)).scalar_one_or_none():
            raise ServiceOSException(
                "SERVICE_TYPE_DUPLICATE",
                f"A service type named '{name}' already exists in this category.",
                status_code=409,
            )
        st = ServiceType(
            category_id=cat_id, name=name, slug=slug,
            description=data.get("description"),
            icon_url=data.get("icon_url"),
            is_active=True,
        )
        self.db.add(st)
        await self.db.flush()
        return self._type_dict(st)

    async def update_service_type(self, type_id: uuid.UUID, data: dict) -> dict:
        result = await self.db.execute(
            select(ServiceType).where(ServiceType.id == type_id, ServiceType.deleted_at.is_(None)))
        st = result.scalar_one_or_none()
        if not st:
            raise NotFoundException("ServiceType", str(type_id))
        if "name" in data and data["name"]:
            st.name = data["name"].strip()
            st.slug = _slugify(st.name)
        if "description" in data:
            st.description = data["description"]
        await self.db.flush()
        return self._type_dict(st)

    async def delete_service_type(self, type_id: uuid.UUID) -> dict:
        result = await self.db.execute(
            select(ServiceType).where(ServiceType.id == type_id, ServiceType.deleted_at.is_(None)))
        st = result.scalar_one_or_none()
        if not st:
            raise NotFoundException("ServiceType", str(type_id))
        st.is_active = False
        st.deleted_at = utcnow()
        await self.db.flush()
        return {"deleted": True, "type_id": str(type_id)}

    async def hard_delete_service_type(self, type_id: uuid.UUID) -> dict:
        result = await self.db.execute(select(ServiceType).where(ServiceType.id == type_id))
        st = result.scalar_one_or_none()
        if not st:
            raise NotFoundException("ServiceType", str(type_id))
        # HS2B delete-safety fix: previously deleted unconditionally even if
        # a tenant had enabled this type or an admin pricing rule referenced
        # it. Block hard delete if used, matching the pattern already used
        # by hard_delete_master_service (pricing-rule check).
        rule_check = await self.db.execute(
            select(ServicePricingRule).where(
                ServicePricingRule.service_type_id == type_id,
                ServicePricingRule.deleted_at.is_(None),
            ).limit(1))
        if rule_check.scalar_one_or_none():
            raise ServiceOSException(
                "SERVICE_TYPE_IN_USE",
                "This catalog item is already used. Deactivate it instead to keep history safe.",
                status_code=409)
        tenant_check = await self.db.execute(
            select(TenantServiceType).where(TenantServiceType.service_type_id == type_id).limit(1))
        if tenant_check.scalar_one_or_none():
            raise ServiceOSException(
                "SERVICE_TYPE_IN_USE",
                "This catalog item is already used. Deactivate it instead to keep history safe.",
                status_code=409)
        await self.db.delete(st)
        await self.db.flush()
        return {"deleted": True, "type_id": str(type_id), "hard_delete": True}

    def _type_dict(self, t: ServiceType) -> dict:
        return {
            "type_id": str(t.id), "category_id": str(t.category_id) if t.category_id else None,
            "name": t.name, "slug": t.slug, "description": t.description,
            "icon_url": t.icon_url, "is_active": t.is_active,
        }

    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
    # BRANDS
    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

    async def list_brands(self, category_id: uuid.UUID | None = None,
                           is_active: bool | None = None) -> dict:
        stmt = select(Brand).where(Brand.deleted_at.is_(None))
        if category_id:
            stmt = stmt.where(Brand.category_id == category_id)
        if is_active is not None:
            stmt = stmt.where(Brand.is_active == is_active)
        stmt = stmt.order_by(Brand.name)
        result = await self.db.execute(stmt)
        brands = result.scalars().all()
        return {"brands": [self._brand_dict(b) for b in brands]}

    async def create_brand(self, data: dict) -> dict:
        name = (data.get("name") or "").strip()
        if not name:
            raise ServiceOSException("BRAND_NAME_REQUIRED", "Brand name is required.", status_code=422)
        slug = _slugify(name)
        existing = await self.db.execute(
            select(Brand).where(Brand.slug == slug, Brand.deleted_at.is_(None)))
        if existing.scalar_one_or_none():
            slug = f"{slug}-{str(uuid.uuid4())[:8]}"
        cat_id = uuid.UUID(str(data["category_id"])) if data.get("category_id") else None
        brand = Brand(
            category_id=cat_id, name=name, slug=slug,
            logo_url=data.get("logo_url"),
            description=data.get("description"),
            is_active=True,
        )
        self.db.add(brand)
        await self.db.flush()
        return self._brand_dict(brand)

    async def delete_brand(self, brand_id: uuid.UUID) -> dict:
        result = await self.db.execute(
            select(Brand).where(Brand.id == brand_id, Brand.deleted_at.is_(None)))
        brand = result.scalar_one_or_none()
        if not brand:
            raise NotFoundException("Brand", str(brand_id))
        brand.is_active = False
        brand.deleted_at = utcnow()
        await self.db.flush()
        return {"deleted": True, "brand_id": str(brand_id)}

    def _brand_dict(self, b: Brand) -> dict:
        return {
            "brand_id": str(b.id), "category_id": str(b.category_id) if b.category_id else None,
            "name": b.name, "slug": b.slug, "logo_url": b.logo_url,
            "description": b.description, "is_active": b.is_active,
        }

    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
    # TYPE / BRAND MAPPINGS
    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

    async def list_service_type_mappings(self, service_id: uuid.UUID) -> dict:
        await self._load_master_service(service_id)
        result = await self.db.execute(
            select(MasterServiceType, ServiceType)
            .join(ServiceType, ServiceType.id == MasterServiceType.service_type_id)
            .where(MasterServiceType.master_service_id == service_id,
                   MasterServiceType.is_active.is_(True),
                   ServiceType.is_active.is_(True),
                   ServiceType.deleted_at.is_(None)))
        rows = result.all()
        return {"types": [
            {"mapping_id": str(m.id), "service_type_id": str(m.service_type_id),
             "name": st.name, "is_required": m.is_required, "is_default": m.is_default}
            for m, st in rows
        ]}

    async def list_service_issue_mappings(self, service_id: uuid.UUID) -> dict:
        """Real, working equivalent of list_service_type_mappings for issue-type
        coverage. Added for the Tenant My Offerings enterprise upgrade —
        no tenant-readable endpoint previously existed for this M2M table
        (service_issue_mappings), even though the mapping data itself is real
        and already seeded. See TENANT_MY_OFFERINGS_CATALOG_DIAGNOSTIC_REPORT.md.
        """
        await self._load_master_service(service_id)
        result = await self.db.execute(
            select(ServiceIssueMapping, MasterIssueType)
            .join(MasterIssueType, MasterIssueType.id == ServiceIssueMapping.issue_type_id)
            .where(ServiceIssueMapping.master_service_id == service_id,
                   ServiceIssueMapping.status == "active"))
        rows = result.all()
        return {"issues": [
            {"mapping_id": str(m.id), "issue_type_id": str(m.issue_type_id),
             "name": it.name, "is_common": m.is_common, "is_default": m.is_default,
             "customer_visible": m.customer_visible}
            for m, it in rows
        ]}

    async def map_service_type(self, service_id: uuid.UUID, data: dict) -> dict:
        await self._load_master_service(service_id)
        type_id = uuid.UUID(str(data["service_type_id"]))
        # validate type exists and is active
        type_res = await self.db.execute(
            select(ServiceType).where(ServiceType.id == type_id, ServiceType.is_active == True, ServiceType.deleted_at.is_(None)))
        if not type_res.scalar_one_or_none():
            raise ServiceOSException("SERVICE_TYPE_INACTIVE", "Service type not found or inactive.", status_code=422)
        # The mapping pair is unique even after a soft delete. Reactivate the
        # existing row so an Admin can safely uncheck and later re-check it.
        existing = (await self.db.execute(
            select(MasterServiceType).where(
                MasterServiceType.master_service_id == service_id,
                MasterServiceType.service_type_id == type_id)
        )).scalar_one_or_none()
        if existing and existing.is_active:
            raise ServiceOSException("MAPPING_DUPLICATE", "This type is already mapped to the service.", status_code=409)
        if existing:
            mapping = existing
            mapping.is_active = True
            mapping.is_required = bool(data.get("is_required", False))
            mapping.is_default = bool(data.get("is_default", False))
        else:
            mapping = MasterServiceType(
                master_service_id=service_id, service_type_id=type_id,
                is_required=bool(data.get("is_required", False)),
                is_default=bool(data.get("is_default", False)),
                is_active=True,
            )
            self.db.add(mapping)
        from app.engines.admin_catalog.tenant_setup_revision import bump_tenant_setup_revision
        await bump_tenant_setup_revision(self.db, service_id)
        await self.db.flush()
        return {"mapping_id": str(mapping.id), "service_type_id": str(type_id)}

    async def remove_service_type_mapping(self, service_id: uuid.UUID, mapping_id: uuid.UUID) -> dict:
        result = await self.db.execute(
            select(MasterServiceType).where(
                MasterServiceType.id == mapping_id,
                MasterServiceType.master_service_id == service_id))
        mapping = result.scalar_one_or_none()
        if not mapping:
            raise NotFoundException("MasterServiceType", str(mapping_id))
        mapping.is_active = False
        from app.engines.admin_catalog.tenant_setup_revision import bump_tenant_setup_revision
        await bump_tenant_setup_revision(self.db, service_id)
        await self.db.flush()
        return {"deleted": True, "mapping_id": str(mapping_id)}

    async def list_service_brand_mappings(self, service_id: uuid.UUID) -> dict:
        await self._load_master_service(service_id)
        result = await self.db.execute(
            select(MasterServiceBrand, Brand)
            .join(Brand, Brand.id == MasterServiceBrand.brand_id)
            .where(MasterServiceBrand.master_service_id == service_id,
                   MasterServiceBrand.is_active.is_(True),
                   MasterServiceBrand.status == "active",
                   Brand.is_active.is_(True),
                   Brand.deleted_at.is_(None)))
        rows = result.all()
        return {"brands": [
            {"mapping_id": str(m.id), "brand_id": str(m.brand_id),
             "name": b.name, "is_required": m.is_required, "is_default": m.is_default}
            for m, b in rows
        ]}

    async def map_service_brand(self, service_id: uuid.UUID, data: dict) -> dict:
        await self._load_master_service(service_id)
        brand_id = uuid.UUID(str(data["brand_id"]))
        brand_res = await self.db.execute(
            select(Brand).where(Brand.id == brand_id, Brand.is_active == True, Brand.deleted_at.is_(None)))
        if not brand_res.scalar_one_or_none():
            raise ServiceOSException("BRAND_INACTIVE", "Brand not found or inactive.", status_code=422)
        # Reactivate a soft-deleted unique pair instead of attempting an
        # insert that would violate uq_msb_service_brand.
        existing = (await self.db.execute(
            select(MasterServiceBrand).where(
                MasterServiceBrand.master_service_id == service_id,
                MasterServiceBrand.brand_id == brand_id)
        )).scalar_one_or_none()
        if existing and existing.is_active and existing.status == "active":
            raise ServiceOSException("MAPPING_DUPLICATE", "This brand is already mapped to the service.", status_code=409)
        if existing:
            mapping = existing
            mapping.is_active = True
            mapping.status = "active"
            mapping.is_required = bool(data.get("is_required", False))
            mapping.is_default = bool(data.get("is_default", False))
        else:
            mapping = MasterServiceBrand(
                master_service_id=service_id, brand_id=brand_id,
                is_required=bool(data.get("is_required", False)),
                is_default=bool(data.get("is_default", False)),
                is_active=True,
                status="active",
            )
            self.db.add(mapping)
        from app.engines.admin_catalog.tenant_setup_revision import bump_tenant_setup_revision
        await bump_tenant_setup_revision(self.db, service_id)
        await self.db.flush()
        return {"mapping_id": str(mapping.id), "brand_id": str(brand_id)}

    async def remove_service_brand_mapping(self, service_id: uuid.UUID, mapping_id: uuid.UUID) -> dict:
        result = await self.db.execute(
            select(MasterServiceBrand).where(
                MasterServiceBrand.id == mapping_id,
                MasterServiceBrand.master_service_id == service_id))
        mapping = result.scalar_one_or_none()
        if not mapping:
            raise NotFoundException("MasterServiceBrand", str(mapping_id))
        mapping.is_active = False
        mapping.status = "inactive"
        from app.engines.admin_catalog.tenant_setup_revision import bump_tenant_setup_revision
        await bump_tenant_setup_revision(self.db, service_id)
        await self.db.flush()
        return {"deleted": True, "mapping_id": str(mapping_id)}

    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
    # PRICING RULES
    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

    async def list_pricing_rules(self, master_service_id: uuid.UUID | None = None,
                                  is_active: bool | None = None, q: str | None = None,
                                  brand_id: uuid.UUID | None = None,
                                  service_type_id: uuid.UUID | None = None,
                                  tier_id: uuid.UUID | None = None,
                                  city: str | None = None, zipcode: str | None = None,
                                  pricing_model: str | None = None,
                                  expiring_within_days: int | None = None,
                                  rule_status: str | None = None,
                                  page: int = 1, page_size: int = 50,
                                  sort_by: str = "priority", sort_dir: str = "desc") -> dict:
        stmt = select(ServicePricingRule).where(ServicePricingRule.deleted_at.is_(None))
        if master_service_id:
            stmt = stmt.where(ServicePricingRule.master_service_id == master_service_id)
        if is_active is not None:
            stmt = stmt.where(ServicePricingRule.is_active == is_active)
        if brand_id:
            stmt = stmt.where(ServicePricingRule.brand_id == brand_id)
        if service_type_id:
            stmt = stmt.where(ServicePricingRule.service_type_id == service_type_id)
        if tier_id:
            stmt = stmt.where(ServicePricingRule.tier_id == tier_id)
        if city:
            stmt = stmt.where(func.lower(ServicePricingRule.city) == city.lower())
        if zipcode:
            stmt = stmt.where(ServicePricingRule.zipcode == zipcode)
        if pricing_model:
            stmt = stmt.where(ServicePricingRule.pricing_model == pricing_model)
        if q:
            like = f"%{q.lower()}%"
            stmt = stmt.where(
                func.lower(func.coalesce(ServicePricingRule.rule_name, "")).like(like) |
                func.lower(func.coalesce(ServicePricingRule.rule_code, "")).like(like)
            )
        now = utcnow()
        if expiring_within_days is not None:
            horizon = now + timedelta(days=expiring_within_days)
            stmt = stmt.where(
                ServicePricingRule.effective_to.isnot(None),
                ServicePricingRule.effective_to >= now,
                ServicePricingRule.effective_to <= horizon,
            )
        if rule_status == "expired":
            stmt = stmt.where(ServicePricingRule.effective_to.isnot(None), ServicePricingRule.effective_to < now)
        elif rule_status == "active":
            stmt = stmt.where(
                ServicePricingRule.is_active == True,
                or_(ServicePricingRule.effective_to.is_(None), ServicePricingRule.effective_to >= now),
            )

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await self.db.execute(count_stmt)).scalar_one()

        sort_col_map = {
            "priority": ServicePricingRule.priority, "created_at": ServicePricingRule.created_at,
            "updated_at": ServicePricingRule.updated_at, "base_price": ServicePricingRule.base_price,
        }
        sort_col = sort_col_map.get(sort_by, ServicePricingRule.priority)
        stmt = stmt.order_by(sort_col.desc() if sort_dir == "desc" else sort_col.asc())
        stmt = stmt.limit(page_size).offset((page - 1) * page_size)

        result = await self.db.execute(stmt)
        rules = result.scalars().all()
        conflict_ids = await self.find_pricing_rule_conflicts()

        items = []
        for r in rules:
            d = self._rule_dict(r)
            d["has_conflict"] = r.id in conflict_ids
            d["validity_status"] = self._rule_validity_status(r, now)
            items.append(d)

        return {
            "items": items,
            "rules": items,  # backward-compat alias
            "pagination": {
                "page": page, "page_size": page_size, "total": total,
                "total_pages": max(1, (total + page_size - 1) // page_size),
            },
            "sort": {"sort_by": sort_by, "sort_dir": sort_dir},
        }

    async def find_pricing_rule_conflicts(self) -> set[uuid.UUID]:
        """Rule IDs sharing (service, tier, type, brand, city, zipcode, priority) with another active rule."""
        stmt = (
            select(
                ServicePricingRule.master_service_id, ServicePricingRule.tier_id,
                ServicePricingRule.service_type_id, ServicePricingRule.brand_id,
                ServicePricingRule.city, ServicePricingRule.zipcode, ServicePricingRule.priority,
                func.array_agg(ServicePricingRule.id).label("ids"),
            )
            .where(ServicePricingRule.deleted_at.is_(None), ServicePricingRule.is_active == True)
            .group_by(ServicePricingRule.master_service_id, ServicePricingRule.tier_id,
                      ServicePricingRule.service_type_id, ServicePricingRule.brand_id,
                      ServicePricingRule.city, ServicePricingRule.zipcode, ServicePricingRule.priority)
            .having(func.count() > 1)
        )
        result = await self.db.execute(stmt)
        conflict_ids: set[uuid.UUID] = set()
        for row in result.all():
            conflict_ids.update(row.ids)
        return conflict_ids

    def _rule_validity_status(self, r: ServicePricingRule, now: datetime | None = None) -> str:
        now = now or utcnow()
        if r.effective_from and r.effective_from > now:
            return "starts_later"
        if r.effective_to and r.effective_to < now:
            return "expired"
        if not r.effective_from and not r.effective_to:
            return "always_active"
        return "active"

    async def get_pricing_rules_summary(self) -> dict:
        result = await self.db.execute(select(ServicePricingRule).where(ServicePricingRule.deleted_at.is_(None)))
        rules = result.scalars().all()
        now = utcnow()
        conflict_ids = await self.find_pricing_rule_conflicts()
        total = len(rules)
        active = sum(1 for r in rules if r.is_active)
        return {
            "total_rules": total,
            "active_rules": active,
            "inactive_rules": total - active,
            "service_rules": sum(1 for r in rules if not r.brand_id and not r.service_type_id and not r.zipcode),
            "brand_rules": sum(1 for r in rules if r.brand_id),
            "type_option_rules": sum(1 for r in rules if r.service_type_id),
            "zipcode_rules": sum(1 for r in rules if r.zipcode),
            "tier_rules": sum(1 for r in rules if r.tier_id),
            "conflicting_rules": len(conflict_ids),
            "expiring_soon": sum(
                1 for r in rules
                if r.effective_to and now <= r.effective_to <= now + timedelta(days=7)
            ),
            "expired_rules": sum(1 for r in rules if r.effective_to and r.effective_to < now),
        }

    async def export_pricing_rules(self, **filters) -> list[dict]:
        filters.setdefault("page", 1)
        filters["page_size"] = 5000
        data = await self.list_pricing_rules(**filters)
        return data["items"]

    async def get_pricing_rule_conflicts(self, rule_id: uuid.UUID) -> dict:
        rule = await self._load_pricing_rule(rule_id)
        stmt = select(ServicePricingRule).where(
            ServicePricingRule.id != rule_id,
            ServicePricingRule.deleted_at.is_(None),
            ServicePricingRule.is_active == True,
            ServicePricingRule.master_service_id == rule.master_service_id,
            ServicePricingRule.tier_id.is_(rule.tier_id) if rule.tier_id is None else ServicePricingRule.tier_id == rule.tier_id,
            ServicePricingRule.service_type_id.is_(rule.service_type_id) if rule.service_type_id is None else ServicePricingRule.service_type_id == rule.service_type_id,
            ServicePricingRule.brand_id.is_(rule.brand_id) if rule.brand_id is None else ServicePricingRule.brand_id == rule.brand_id,
            ServicePricingRule.city.is_(rule.city) if rule.city is None else ServicePricingRule.city == rule.city,
            ServicePricingRule.zipcode.is_(rule.zipcode) if rule.zipcode is None else ServicePricingRule.zipcode == rule.zipcode,
            ServicePricingRule.priority == rule.priority,
        )
        result = await self.db.execute(stmt)
        conflicts = result.scalars().all()
        return {"rule_id": str(rule_id), "conflicts": [self._rule_dict(c) for c in conflicts]}

    async def get_pricing_rule(self, rule_id: uuid.UUID) -> dict:
        rule = await self._load_pricing_rule(rule_id)
        return self._rule_dict(rule)

    def _generate_rule_code(self, service_slug: str) -> str:
        prefix = re.sub(r"[^A-Z0-9]", "", (service_slug or "SVC").upper())[:6] or "SVC"
        return f"PR-{prefix}-{str(uuid.uuid4())[:6].upper()}"

    async def create_pricing_rule(self, data: dict) -> dict:
        svc_id_raw = data.get("master_service_id")
        if not svc_id_raw:
            raise ServiceOSException("PRICING_RULE_SERVICE_REQUIRED", "master_service_id is required.", status_code=422)
        svc_id = uuid.UUID(str(svc_id_raw))
        svc = await self._load_master_service(svc_id)

        job_type = (data.get("job_type") or "").strip()
        if not job_type or job_type not in VALID_JOB_TYPES:
            raise ServiceOSException("INVALID_JOB_TYPE", "Valid job_type is required.", status_code=422)
        model = (data.get("pricing_model") or "").strip()
        if not model or model not in VALID_PRICING_MODELS:
            raise ServiceOSException("INVALID_PRICING_MODEL", "Valid pricing_model is required.", status_code=422)

        base_price = Decimal(str(data.get("base_price", 0) or 0))
        min_price  = Decimal(str(data["min_price"])) if data.get("min_price") is not None else None
        max_price  = Decimal(str(data["max_price"])) if data.get("max_price") is not None else None
        if min_price and max_price and min_price > max_price:
            raise ServiceOSException("INVALID_PRICE_RANGE", "min_price cannot exceed max_price.", status_code=422)


        deduction_credits = int(data.get("completed_job_deduction_credits", 0) or 0)
        if deduction_credits < 0:
            raise ServiceOSException("INVALID_DEDUCTION_CREDITS",
                "completed_job_deduction_credits cannot be negative.", status_code=422)

        # HS3 — Type-Dependent Brand Pricing: a brand override on a type-based
        # service (pricing_model == "range") must be scoped to a specific
        # service_type_id — otherwise the brand price is wrongly global
        # across every type (e.g. one LG price for both Window AC and Split
        # AC). Fixed/consultation services have no types, so this only
        # applies when pricing_model == "range".
        if data.get("brand_id") and model == "range" and not data.get("service_type_id"):
            raise ServiceOSException(
                "SERVICE_TYPE_REQUIRED_FOR_BRAND_PRICING",
                "Service type is required when adding brand pricing for a type-based service.",
                status_code=422)

        rule_code = (data.get("rule_code") or "").strip() or self._generate_rule_code(svc.slug)

        # Application-level duplicate check: the DB unique constraint
        # (uq_spr_service_type_brand_tier) does not catch duplicates when
        # tier_id is NULL (Postgres treats multiple NULLs as distinct), which
        # is the common case for "global, no tier" rules — check explicitly
        # here so DUPLICATE_TYPE_BRAND_PRICING_RULE is reliably returned.
        tier_id_val = uuid.UUID(str(data["tier_id"])) if data.get("tier_id") else None
        type_id_val = uuid.UUID(str(data["service_type_id"])) if data.get("service_type_id") else None
        brand_id_val = uuid.UUID(str(data["brand_id"])) if data.get("brand_id") else None
        dup_stmt = select(ServicePricingRule).where(
            ServicePricingRule.master_service_id == svc_id,
            ServicePricingRule.deleted_at.is_(None),
            ServicePricingRule.service_type_id == type_id_val if type_id_val else ServicePricingRule.service_type_id.is_(None),
            ServicePricingRule.brand_id == brand_id_val if brand_id_val else ServicePricingRule.brand_id.is_(None),
            ServicePricingRule.tier_id == tier_id_val if tier_id_val else ServicePricingRule.tier_id.is_(None),
        )
        if (await self.db.execute(dup_stmt)).scalars().first():
            raise ServiceOSException(
                "DUPLICATE_TYPE_BRAND_PRICING_RULE",
                "A pricing rule already exists for this service, type, brand, and tier.",
                status_code=409)

        rule = ServicePricingRule(
            master_service_id=svc_id,
            category_id=svc.category_id,
            job_type=job_type,
            tier_id=uuid.UUID(str(data["tier_id"])) if data.get("tier_id") else None,
            service_type_id=uuid.UUID(str(data["service_type_id"])) if data.get("service_type_id") else None,
            brand_id=uuid.UUID(str(data["brand_id"])) if data.get("brand_id") else None,
            service_option_id=uuid.UUID(str(data["service_option_id"])) if data.get("service_option_id") else None,
            city=(data.get("city") or "").strip().lower() or None,
            zipcode=(data.get("zipcode") or "").strip() or None,
            district=data.get("district") or None,
            state=data.get("state") or None,
            zone=data.get("zone") or None,
            pricing_model=model,
            base_price=base_price, min_price=min_price, max_price=max_price,
            visit_fee=Decimal(str(data.get("visit_fee", 0) or 0)),
            platform_fee_percent=Decimal(str(data.get("platform_fee_percent", 0) or 0)),
            commission_percent=Decimal(str(data.get("commission_percent", 0) or 0)),
            tax_percent=Decimal(str(data.get("tax_percent", 0) or 0)),
            completed_job_deduction_credits=deduction_credits,
            rule_name=(data.get("rule_name") or "").strip() or None,
            rule_code=rule_code,
            source=data.get("source") or "admin",
            effective_from=data.get("effective_from"),
            effective_to=data.get("effective_to"),
            priority=int(data.get("priority", 100) or 100),
            is_active=True,
        )
        self.db.add(rule)
        try:
            await self.db.flush()
        except IntegrityError as e:
            await self.db.rollback()
            if "uq_spr_service_type_brand_tier" in str(e.orig):
                raise ServiceOSException(
                    "DUPLICATE_TYPE_BRAND_PRICING_RULE",
                    "A pricing rule already exists for this service, type, brand, and tier.",
                    status_code=409) from e
            raise
        await self._audit("pricing_rule", rule.id, "create", None, self._rule_dict(rule),
                           f"Created pricing rule '{rule.rule_name or rule.rule_code}'")
        return self._rule_dict(rule)

    async def update_pricing_rule(self, rule_id: uuid.UUID, data: dict) -> dict:
        rule = await self._load_pricing_rule(rule_id)
        old = self._rule_dict(rule)
        for field in ("job_type", "pricing_model", "city", "zipcode", "priority", "district", "state", "zone",
                      "is_active", "effective_from", "effective_to", "rule_name", "rule_code"):
            if field in data and data[field] is not None:
                setattr(rule, field, data[field])
        for field in ("base_price", "min_price", "max_price", "visit_fee",
                      "platform_fee_percent", "commission_percent", "tax_percent"):
            if field in data and data[field] is not None:
                setattr(rule, field, Decimal(str(data[field])))
        if "completed_job_deduction_credits" in data and data["completed_job_deduction_credits"] is not None:
            deduction_credits = int(data["completed_job_deduction_credits"])
            if deduction_credits < 0:
                raise ServiceOSException("INVALID_DEDUCTION_CREDITS",
                    "completed_job_deduction_credits cannot be negative.", status_code=422)
            rule.completed_job_deduction_credits = deduction_credits
        await self.db.flush()
        await self._audit("pricing_rule", rule.id, "update", old, self._rule_dict(rule),
                           f"Updated pricing rule '{rule.rule_name or rule.rule_code}'")
        return self._rule_dict(rule)

    async def delete_pricing_rule(self, rule_id: uuid.UUID) -> dict:
        rule = await self._load_pricing_rule(rule_id)
        old = self._rule_dict(rule)
        rule.is_active = False
        rule.deleted_at = utcnow()
        await self.db.flush()
        await self._audit("pricing_rule", rule.id, "deactivate", old, self._rule_dict(rule), "Deactivated pricing rule")
        return {"deleted": True, "rule_id": str(rule_id)}

    async def hard_delete_pricing_rule(self, rule_id: uuid.UUID) -> dict:
        result = await self.db.execute(select(ServicePricingRule).where(ServicePricingRule.id == rule_id))
        rule = result.scalar_one_or_none()
        if not rule:
            raise NotFoundException("ServicePricingRule", str(rule_id))
        await self.db.delete(rule)
        await self.db.flush()
        return {"deleted": True, "rule_id": str(rule_id), "hard_delete": True}

    async def preview_pricing(self, data: dict) -> dict:
        """Run the pricing engine and return the matched rule + price breakdown."""
        from app.engines.admin_catalog.pricing_engine import resolve_service_price
        return await resolve_service_price(
            db=self.db,
            master_service_id=uuid.UUID(str(data["master_service_id"])),
            job_type=data.get("job_type"),
            city=data.get("city"),
            zipcode=data.get("zipcode"),
            state=data.get("state"),
            country=data.get("country"),
            service_type_id=uuid.UUID(str(data["service_type_id"])) if data.get("service_type_id") else None,
            brand_id=uuid.UUID(str(data["brand_id"])) if data.get("brand_id") else None,
        )

    # ═══════════════════════════════════════════════════════════
    # HOME SERVICES CATALOG CONSOLE — consolidated admin console
    # (composes existing master-service/type/brand/pricing-rule data;
    # exposes catalog dimensions and workflow metadata. Price amounts remain
    # provider-owned and customer charges come from Home Services Finance.)
    # ═══════════════════════════════════════════════════════════

    async def get_home_services_category_id(self) -> uuid.UUID:
        res = await self.db.execute(
            select(ServiceCategory).where(
                ServiceCategory.vertical_type == "home_services",
                ServiceCategory.deleted_at.is_(None) if hasattr(ServiceCategory, "deleted_at") else True,
            ))
        cat = res.scalars().first()
        if not cat:
            raise ServiceOSException("HOME_SERVICES_CATEGORY_NOT_FOUND",
                "No Home Services category is configured.", status_code=422)
        return cat.id

    async def list_home_services_catalog_console(
        self,
        q: str | None = None,
        service_id: uuid.UUID | None = None,
        service_group_id: uuid.UUID | None = None,
        is_active: bool | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> dict:
        """Grouped service list for the console's left panel — Home Services
        category only (hard scope boundary: never returns other verticals)."""
        cat_id = await self.get_home_services_category_id()
        groups_res = await self.db.execute(
            select(ServiceGroup).where(
                ServiceGroup.category_id == cat_id, ServiceGroup.deleted_at.is_(None),
            ).order_by(ServiceGroup.display_order, ServiceGroup.name))
        groups = groups_res.scalars().all()

        service_stmt = select(MasterService).where(
            MasterService.category_id == cat_id, MasterService.deleted_at.is_(None),
        )
        if service_id:
            service_stmt = service_stmt.where(MasterService.id == service_id)
        if q and q.strip():
            term = f"%{q.strip().lower()}%"
            service_stmt = service_stmt.where(or_(
                func.lower(MasterService.service_name).like(term),
                func.lower(MasterService.slug).like(term),
            ))
        if service_group_id:
            service_stmt = service_stmt.where(MasterService.service_group_id == service_group_id)
        if is_active is not None:
            service_stmt = service_stmt.where(MasterService.is_active == is_active)
        total = int(await self.db.scalar(select(func.count()).select_from(service_stmt.subquery())) or 0)
        svcs_res = await self.db.execute(
            service_stmt.order_by(MasterService.display_order, MasterService.service_name)
            .offset(offset).limit(limit))
        svcs = svcs_res.scalars().all()

        # Only aggregate the current page. The previous global GROUP BY scanned
        # every service mapping even though the console can display at most 100
        # services at once.
        service_ids = [service.id for service in svcs]
        type_counts: dict = {}
        brand_counts: dict = {}
        if service_ids:
            type_counts = dict((await self.db.execute(
                select(MasterServiceType.master_service_id, func.count())
                .where(
                    MasterServiceType.is_active == True,
                    MasterServiceType.master_service_id.in_(service_ids),
                )
                .group_by(MasterServiceType.master_service_id)
            )).all())
            brand_counts = dict((await self.db.execute(
                select(MasterServiceBrand.master_service_id, func.count())
                .where(
                    MasterServiceBrand.is_active == True,
                    MasterServiceBrand.master_service_id.in_(service_ids),
                )
                .group_by(MasterServiceBrand.master_service_id)
            )).all())

        service_rows = []
        for s in svcs:
            d = self._svc_dict(s)
            d["types_count"] = type_counts.get(s.id, 0)
            d["brands_count"] = brand_counts.get(s.id, 0)
            service_rows.append(d)

        return {
            "category_id": str(cat_id),
            "groups": [{"group_id": str(g.id), "name": g.name} for g in groups],
            "services": service_rows,
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    async def get_home_services_service_console_detail(self, service_id: uuid.UUID) -> dict:
        cat_id = await self.get_home_services_category_id()
        svc = await self._load_master_service(service_id)
        if svc.category_id != cat_id:
            raise ServiceOSException("NOT_HOME_SERVICES_CATEGORY",
                "This service does not belong to the Home Services category.", status_code=422)
        detail = self._svc_dict(svc)
        detail["types"] = (await self.get_home_services_type_pricing(service_id))["types"]
        detail["brands"] = (await self.get_home_services_brand_pricing(service_id))["brands"]
        return detail

    async def _find_scoped_pricing_rule(self, master_service_id: uuid.UUID,
                                         service_type_id: uuid.UUID | None,
                                         brand_id: uuid.UUID | None) -> ServicePricingRule | None:
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

    async def get_home_services_type_pricing(self, service_id: uuid.UUID) -> dict:
        svc = await self._load_master_service(service_id)
        types = (await self.list_service_type_mappings(service_id))["types"]
        out = []
        for t in types:
            type_uuid = uuid.UUID(t["service_type_id"])
            rule = await self._find_scoped_pricing_rule(service_id, type_uuid, None)
            floor = float(rule.min_price) if rule and rule.min_price is not None else (
                float(svc.min_price) if svc.min_price is not None else None)
            ceiling = float(rule.max_price) if rule and rule.max_price is not None else (
                float(svc.max_price) if svc.max_price is not None else None)
            fee_pct = float(rule.platform_fee_percent) if rule and rule.platform_fee_percent is not None else 0.0
            deduction = rule.completed_job_deduction_credits if rule else 0
            preview = (
                {
                    "provider_min_price": floor,
                    "provider_max_price": ceiling,
                    "payment_mode": "customer_pays_provider_directly",
                }
                if floor is not None and ceiling is not None else None
            )
            out.append({
                **t,
                "pricing_rule_id": str(rule.id) if rule else None,
                "admin_floor_price": floor,
                "admin_ceiling_price": ceiling,
                "platform_fee_percent": fee_pct,
                "completed_job_deduction_credits": deduction,
                "customer_price_preview": preview,
            })
        return {"types": out}

    async def upsert_home_services_type_limits(self, service_id: uuid.UUID,
                                                 service_type_id: uuid.UUID, data: dict) -> dict:
        svc = await self._load_master_service(service_id)
        floor = Decimal(str(data["admin_floor_price"])) if data.get("admin_floor_price") is not None else None
        ceiling = Decimal(str(data["admin_ceiling_price"])) if data.get("admin_ceiling_price") is not None else None
        if floor is None or ceiling is None:
            raise ServiceOSException("PRICE_RANGE_REQUIRED",
                "admin_floor_price and admin_ceiling_price are required.", status_code=422)
        if floor > ceiling:
            raise ServiceOSException("INVALID_PRICE_RANGE",
                "admin_floor_price cannot exceed admin_ceiling_price.", status_code=422)
        fee_pct = Decimal(str(data.get("platform_fee_percent", 10) or 0))
        if fee_pct < 0:
            raise ServiceOSException("INVALID_PLATFORM_FEE", "Platform fee cannot be negative.", status_code=422)
        deduction = int(data.get("completed_job_deduction_credits", 0) or 0)
        if deduction < 0:
            raise ServiceOSException("INVALID_DEDUCTION_CREDITS",
                "completed_job_deduction_credits cannot be negative.", status_code=422)

        existing = await self._find_scoped_pricing_rule(service_id, service_type_id, None)
        if existing:
            existing.min_price = floor
            existing.max_price = ceiling
            existing.platform_fee_percent = fee_pct
            existing.completed_job_deduction_credits = deduction
            await self.db.flush()
            await self._audit("pricing_rule", existing.id, "update", None, self._rule_dict(existing),
                               f"Updated type pricing limits for {svc.service_name}")
        else:
            rule = ServicePricingRule(
                master_service_id=service_id, category_id=svc.category_id,
                job_type=svc.job_type, service_type_id=service_type_id,
                pricing_model=svc.pricing_model or "range",
                base_price=floor, min_price=floor, max_price=ceiling,
                visit_fee=Decimal("0"), platform_fee_percent=fee_pct,
                completed_job_deduction_credits=deduction,
                rule_code=self._generate_rule_code(svc.slug),
                rule_name=f"{svc.service_name} — type default range",
                source="admin", priority=100, is_active=True,
            )
            self.db.add(rule)
            await self.db.flush()
            await self._audit("pricing_rule", rule.id, "create", None, self._rule_dict(rule),
                               f"Created type pricing limits for {svc.service_name}")
        return await self.get_home_services_type_pricing(service_id)

    async def get_home_services_brand_pricing(self, service_id: uuid.UUID, service_type_id: uuid.UUID | None = None) -> dict:
        svc = await self._load_master_service(service_id)
        res = await self.db.execute(
            select(MasterServiceBrand, Brand)
            .join(Brand, Brand.id == MasterServiceBrand.brand_id)
            .where(MasterServiceBrand.master_service_id == service_id,
                   MasterServiceBrand.is_active == True))
        rows = res.all()
        out = []
        for m, b in rows:
            rule = await self._find_scoped_pricing_rule(service_id, service_type_id, m.brand_id)
            floor = float(rule.min_price) if rule and rule.min_price is not None else None
            ceiling = float(rule.max_price) if rule and rule.max_price is not None else None
            fee_pct = float(rule.platform_fee_percent) if rule and rule.platform_fee_percent is not None else 0.0
            preview = (
                {
                    "provider_min_price": floor,
                    "provider_max_price": ceiling,
                    "payment_mode": "customer_pays_provider_directly",
                }
                if m.can_override_price and floor is not None and ceiling is not None else None
            )
            out.append({
                "mapping_id": str(m.id), "brand_id": str(m.brand_id), "name": b.name,
                "is_required": m.is_required, "is_default": m.is_default,
                "can_override_price": m.can_override_price, "is_routing_only": m.is_routing_only,
                "pricing_rule_id": str(rule.id) if rule else None,
                "admin_floor_price": floor, "admin_ceiling_price": ceiling,
                "platform_fee_percent": fee_pct if rule else None,
                "customer_price_preview": preview,
            })
        return {"brands": out}

    async def set_home_services_brand_behavior(self, service_id: uuid.UUID, mapping_id: uuid.UUID, data: dict) -> dict:
        res = await self.db.execute(
            select(MasterServiceBrand).where(
                MasterServiceBrand.id == mapping_id, MasterServiceBrand.master_service_id == service_id))
        mapping = res.scalar_one_or_none()
        if not mapping:
            raise NotFoundException("MasterServiceBrand", str(mapping_id))
        if "can_override_price" in data:
            mapping.can_override_price = bool(data["can_override_price"])
        if "is_routing_only" in data:
            mapping.is_routing_only = bool(data["is_routing_only"])
        await self.db.flush()
        return (await self.get_home_services_brand_pricing(service_id))["brands"]

    async def upsert_home_services_brand_limits(self, service_id: uuid.UUID, brand_id: uuid.UUID,
                                                  service_type_id: uuid.UUID | None, data: dict) -> dict:
        svc = await self._load_master_service(service_id)
        mapping_res = await self.db.execute(
            select(MasterServiceBrand).where(
                MasterServiceBrand.master_service_id == service_id,
                MasterServiceBrand.brand_id == brand_id, MasterServiceBrand.is_active == True))
        mapping = mapping_res.scalar_one_or_none()
        if not mapping:
            raise ServiceOSException("BRAND_NOT_SUPPORTED",
                "Brand is not mapped to this service.", status_code=422)
        if not mapping.can_override_price:
            raise ServiceOSException("BRAND_OVERRIDE_NOT_ALLOWED",
                "This brand is not configured for price override.", status_code=422)

        floor = Decimal(str(data["admin_floor_price"])) if data.get("admin_floor_price") is not None else None
        ceiling = Decimal(str(data["admin_ceiling_price"])) if data.get("admin_ceiling_price") is not None else None
        if floor is None or ceiling is None:
            raise ServiceOSException("PRICE_RANGE_REQUIRED",
                "admin_floor_price and admin_ceiling_price are required.", status_code=422)
        if floor > ceiling:
            raise ServiceOSException("INVALID_PRICE_RANGE",
                "admin_floor_price cannot exceed admin_ceiling_price.", status_code=422)
        fee_pct = Decimal(str(data.get("platform_fee_percent", 10) or 0))

        existing = await self._find_scoped_pricing_rule(service_id, service_type_id, brand_id)
        if existing:
            existing.min_price = floor
            existing.max_price = ceiling
            existing.platform_fee_percent = fee_pct
            await self.db.flush()
        else:
            rule = ServicePricingRule(
                master_service_id=service_id, category_id=svc.category_id,
                job_type=svc.job_type, service_type_id=service_type_id, brand_id=brand_id,
                pricing_model=svc.pricing_model or "range",
                base_price=floor, min_price=floor, max_price=ceiling,
                visit_fee=Decimal("0"), platform_fee_percent=fee_pct,
                rule_code=self._generate_rule_code(svc.slug),
                rule_name=f"{svc.service_name} — brand override",
                source="admin", priority=200, is_active=True,
            )
            self.db.add(rule)
            await self.db.flush()
        return await self.get_home_services_brand_pricing(service_id, service_type_id)

    async def get_home_services_service_audit(self, service_id: uuid.UUID, limit: int = 30) -> dict:
        rule_ids_res = await self.db.execute(
            select(ServicePricingRule.id).where(ServicePricingRule.master_service_id == service_id))
        rule_ids = [r for (r,) in rule_ids_res.all()]

        stmt = select(MasterDataAuditLog).where(
            or_(
                and_(MasterDataAuditLog.entity_type == "master_service", MasterDataAuditLog.entity_id == service_id),
                and_(MasterDataAuditLog.entity_type == "pricing_rule", MasterDataAuditLog.entity_id.in_(rule_ids))
                if rule_ids else False,
            )
        ).order_by(MasterDataAuditLog.created_at.desc()).limit(limit)
        rows = (await self.db.execute(stmt)).scalars().all()
        out = [
            {
                "entity_type": r.entity_type, "entity_id": str(r.entity_id), "action": r.action,
                "change_summary": r.change_summary, "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ]
        return {"events": out}

    async def _load_pricing_rule(self, rule_id: uuid.UUID) -> ServicePricingRule:
        result = await self.db.execute(
            select(ServicePricingRule).where(ServicePricingRule.id == rule_id, ServicePricingRule.deleted_at.is_(None)))
        rule = result.scalar_one_or_none()
        if not rule:
            raise NotFoundException("ServicePricingRule", str(rule_id))
        return rule

    def _rule_dict(self, r: ServicePricingRule) -> dict:
        return {
            "rule_id": str(r.id),
            "master_service_id": str(r.master_service_id),
            "category_id": str(r.category_id) if r.category_id else None,
            "job_type": r.job_type,
            "tier_id": str(r.tier_id) if r.tier_id else None,
            "service_type_id": str(r.service_type_id) if r.service_type_id else None,
            "brand_id": str(r.brand_id) if r.brand_id else None,
            "service_option_id": str(r.service_option_id) if r.service_option_id else None,
            "city": r.city, "zipcode": r.zipcode,
            "district": r.district, "state": r.state, "zone": r.zone,
            "pricing_model": r.pricing_model,
            "base_price": float(r.base_price),
            "min_price": float(r.min_price) if r.min_price else None,
            "max_price": float(r.max_price) if r.max_price else None,
            "visit_fee": float(r.visit_fee),
            "platform_fee_percent": float(r.platform_fee_percent),
            "commission_percent": float(r.commission_percent),
            "tax_percent": float(r.tax_percent),
            "completed_job_deduction_credits": r.completed_job_deduction_credits,
            "rule_name": r.rule_name,
            "rule_code": r.rule_code,
            "source": r.source,
            "effective_from": r.effective_from.isoformat() if r.effective_from else None,
            "effective_to": r.effective_to.isoformat() if r.effective_to else None,
            "priority": r.priority, "is_active": r.is_active,
        }

    # ═════════════════════════════════════════════════════════
    # MASTER ISSUE TYPES  (Sprint 34C)
    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

    VALID_SEVERITIES   = {"low", "medium", "high", "critical"}

    async def list_issue_types(self, category_id: uuid.UUID | None = None,
                               master_service_id: uuid.UUID | None = None,
                               is_active: bool | None = None) -> dict:
        stmt = select(MasterIssueType)
        if category_id is not None:
            stmt = stmt.where(MasterIssueType.category_id == category_id)
        if master_service_id is not None:
            stmt = stmt.where(MasterIssueType.master_service_id == master_service_id)
        if is_active is not None:
            stmt = stmt.where(MasterIssueType.is_active == is_active)
        stmt = stmt.order_by(MasterIssueType.display_order, MasterIssueType.name)
        result = await self.db.execute(stmt)
        rows = result.scalars().all()
        issue_types = []
        for row in rows:
            payload = row.to_dict()
            payload.pop("icon_url", None)
            issue_types.append(payload)
        return {"issue_types": issue_types, "total": len(rows)}

    async def get_issue_type(self, issue_type_id: uuid.UUID) -> dict:
        row = await self._load_issue_type(issue_type_id)
        payload = row.to_dict()
        payload.pop("icon_url", None)
        return payload

    async def create_issue_type(self, data: dict) -> dict:
        name = (data.get("name") or "").strip()
        code = (data.get("code") or "").strip().upper()
        if not name:
            raise ServiceOSException("ISSUE_TYPE_NAME_REQUIRED", "name is required.", status_code=422)
        if not code:
            raise ServiceOSException("ISSUE_TYPE_CODE_REQUIRED", "code is required.", status_code=422)
        severity = (data.get("severity") or "medium").strip()
        if severity not in self.VALID_SEVERITIES:
            raise ServiceOSException("ISSUE_TYPE_INVALID_SEVERITY",
                                     f"severity must be one of {sorted(self.VALID_SEVERITIES)}.", status_code=422)
        slug = _slugify(data.get("slug") or name)
        # unique slug check
        existing = await self.db.execute(select(MasterIssueType).where(MasterIssueType.slug == slug))
        if existing.scalar_one_or_none():
            slug = f"{slug}-{code.lower()}"

        cat_id = uuid.UUID(str(data["category_id"])) if data.get("category_id") else None
        svc_id = uuid.UUID(str(data["master_service_id"])) if data.get("master_service_id") else None

        row = MasterIssueType(
            category_id=cat_id, master_service_id=svc_id,
            code=code, name=name, slug=slug,
            description=data.get("description"),
            severity=severity,
            is_active=bool(data.get("is_active", True)),
            display_order=int(data.get("display_order", 0) or 0),
        )
        self.db.add(row)
        await self.db.flush()
        await self._audit("master_issue_type", row.id, "create", None, row.to_dict(), f"Created issue type '{name}'")
        logger.info("issue_type.created", id=str(row.id), name=name)
        payload = row.to_dict()
        payload.pop("icon_url", None)
        return payload

    async def update_issue_type(self, issue_type_id: uuid.UUID, data: dict) -> dict:
        row = await self._load_issue_type(issue_type_id)
        old = row.to_dict()
        for field in ("name", "description", "severity", "is_active", "display_order"):
            if field in data and data[field] is not None:
                setattr(row, field, data[field])
        if "code" in data and data["code"]:
            row.code = str(data["code"]).strip().upper()
        await self.db.flush()
        await self._audit("master_issue_type", row.id, "update", old, row.to_dict(), f"Updated issue type '{row.name}'")
        payload = row.to_dict()
        payload.pop("icon_url", None)
        return payload

    async def delete_issue_type(self, issue_type_id: uuid.UUID) -> dict:
        row = await self._load_issue_type(issue_type_id)
        old = row.to_dict()
        row.is_active = False
        await self.db.flush()
        await self._audit("master_issue_type", row.id, "deactivate", old, row.to_dict(), f"Deactivated issue type '{row.name}'")
        return {"deleted": True, "id": str(issue_type_id)}

    async def _load_issue_type(self, issue_type_id: uuid.UUID) -> MasterIssueType:
        result = await self.db.execute(select(MasterIssueType).where(MasterIssueType.id == issue_type_id))
        row = result.scalar_one_or_none()
        if not row:
            raise NotFoundException("MasterIssueType", str(issue_type_id))
        return row

    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
    # MASTER SERVICE OPTIONS  (Sprint 34C)
    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

    VALID_OPTION_TYPES = {"add_on", "upgrade", "material", "tool", "visit_fee"}
    VALID_UNITS        = {"per_unit", "per_hour", "flat", "per_sqft", "per_kg"}

    async def list_service_options(self, category_id: uuid.UUID | None = None,
                                   master_service_id: uuid.UUID | None = None,
                                   is_active: bool | None = None) -> dict:
        stmt = select(MasterServiceOption)
        if category_id is not None:
            stmt = stmt.where(MasterServiceOption.category_id == category_id)
        if master_service_id is not None:
            stmt = stmt.where(MasterServiceOption.master_service_id == master_service_id)
        if is_active is not None:
            stmt = stmt.where(MasterServiceOption.is_active == is_active)
        stmt = stmt.order_by(MasterServiceOption.display_order, MasterServiceOption.name)
        result = await self.db.execute(stmt)
        rows = result.scalars().all()
        return {"service_options": [r.to_dict() for r in rows], "total": len(rows)}

    async def get_service_option(self, option_id: uuid.UUID) -> dict:
        row = await self._load_service_option(option_id)
        return row.to_dict()

    async def create_service_option(self, data: dict) -> dict:
        name = (data.get("name") or "").strip()
        code = (data.get("code") or "").strip().upper()
        if not name:
            raise ServiceOSException("SERVICE_OPTION_NAME_REQUIRED", "name is required.", status_code=422)
        if not code:
            raise ServiceOSException("SERVICE_OPTION_CODE_REQUIRED", "code is required.", status_code=422)
        option_type = (data.get("option_type") or "add_on").strip()
        if option_type not in self.VALID_OPTION_TYPES:
            raise ServiceOSException("SERVICE_OPTION_INVALID_TYPE",
                                     f"option_type must be one of {sorted(self.VALID_OPTION_TYPES)}.", status_code=422)
        unit = (data.get("unit") or "per_unit").strip()
        if unit not in self.VALID_UNITS:
            raise ServiceOSException("SERVICE_OPTION_INVALID_UNIT",
                                     f"unit must be one of {sorted(self.VALID_UNITS)}.", status_code=422)
        slug = _slugify(data.get("slug") or name)
        existing = await self.db.execute(select(MasterServiceOption).where(MasterServiceOption.slug == slug))
        if existing.scalar_one_or_none():
            slug = f"{slug}-{code.lower()}"

        default_price = Decimal(str(data.get("default_price", 0) or 0))
        min_price = Decimal(str(data["min_price"])) if data.get("min_price") is not None else None
        max_price = Decimal(str(data["max_price"])) if data.get("max_price") is not None else None
        if min_price and max_price and min_price > max_price:
            raise ServiceOSException("INVALID_PRICE_RANGE", "min_price cannot exceed max_price.", status_code=422)

        cat_id = uuid.UUID(str(data["category_id"])) if data.get("category_id") else None
        svc_id = uuid.UUID(str(data["master_service_id"])) if data.get("master_service_id") else None

        row = MasterServiceOption(
            category_id=cat_id, master_service_id=svc_id,
            code=code, name=name, slug=slug,
            description=data.get("description"),
            option_type=option_type, unit=unit,
            default_price=default_price, min_price=min_price, max_price=max_price,
            is_customer_selectable=bool(data.get("is_customer_selectable", True)),
            is_active=bool(data.get("is_active", True)),
            display_order=int(data.get("display_order", 0) or 0),
        )
        self.db.add(row)
        await self.db.flush()
        await self._audit("master_service_option", row.id, "create", None, row.to_dict(), f"Created service option '{name}'")
        logger.info("service_option.created", id=str(row.id), name=name)
        return row.to_dict()

    async def update_service_option(self, option_id: uuid.UUID, data: dict) -> dict:
        row = await self._load_service_option(option_id)
        old = row.to_dict()
        for field in ("name", "description", "option_type", "unit",
                      "is_customer_selectable", "is_active", "display_order"):
            if field in data and data[field] is not None:
                setattr(row, field, data[field])
        if "code" in data and data["code"]:
            row.code = str(data["code"]).strip().upper()
        for price_field in ("default_price", "min_price", "max_price"):
            if price_field in data and data[price_field] is not None:
                setattr(row, price_field, Decimal(str(data[price_field])))
        await self.db.flush()
        await self._audit("master_service_option", row.id, "update", old, row.to_dict(), f"Updated service option '{row.name}'")
        return row.to_dict()

    async def delete_service_option(self, option_id: uuid.UUID) -> dict:
        row = await self._load_service_option(option_id)
        old = row.to_dict()
        row.is_active = False
        await self.db.flush()
        await self._audit("master_service_option", row.id, "deactivate", old, row.to_dict(), f"Deactivated service option '{row.name}'")
        return {"deleted": True, "id": str(option_id)}

    async def _load_service_option(self, option_id: uuid.UUID) -> MasterServiceOption:
        result = await self.db.execute(select(MasterServiceOption).where(MasterServiceOption.id == option_id))
        row = result.scalar_one_or_none()
        if not row:
            raise NotFoundException("MasterServiceOption", str(option_id))
        return row

    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
    # MASTER WORKFLOW TEMPLATES  (Sprint 34C)
    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

    VALID_WORKFLOW_TYPES = {
        "repair", "service", "consultation", "appointment", "lead", "inspection",
        "installation", "uninstallation", "maintenance", "cleaning", "delivery",
        "lead_followup", "custom",
    }
    VALID_TEMPLATE_STATUSES = {"draft", "active", "inactive", "deprecated", "archived"}
    VALID_STEP_TYPES = {
        "system", "customer_action", "tenant_action", "technician_action",
        "admin_action", "approval", "notification", "automation", "condition",
    }
    VALID_ACTORS = {
        "system", "customer", "tenant_owner", "tenant_manager", "technician",
        "platform_admin", "support_admin", "finance_admin",
    }
    VALID_EVIDENCE_TYPES = {
        "photo_before", "photo_after", "video_optional", "invoice_photo", "part_photo",
        "customer_signature", "technician_note", "customer_note", "document_upload",
        "location_checkin",
    }
    VALID_APPROVAL_TYPES = {
        "customer_estimate_approval", "customer_parts_approval", "tenant_manager_approval",
        "admin_exception_approval", "payment_confirmation", "completion_confirmation",
    }
    VALID_AUTOMATION_TRIGGERS = {
        "on_step_enter", "on_step_exit", "on_sla_warning", "on_sla_breach",
        "on_customer_approval", "on_customer_rejection", "on_job_completed", "on_dispute_opened",
    }
    VALID_AUTOMATION_ACTIONS = {
        "send_notification", "create_task", "assign_technician", "deduct_job_credit",
        "request_customer_review", "open_dispute_window", "escalate_to_admin",
    }

    async def get_workflow_templates_summary(self) -> dict:
        """The eight KPI tiles, as one aggregate query.

        This used to load every `is_latest` template row — each carrying its full
        steps and transitions JSONB — plus the entire mappings table, and count
        in Python. Measured at 50k templates that took 4.3s, on a request the
        page makes every time it opens. Counting in the database instead keeps
        the work proportional to what is being counted rather than to what has
        to be shipped to the API process first.
        """
        row = (await self.db.execute(text(f"""
            SELECT
              count(*)                                                        AS total_templates,
              count(*) FILTER (WHERE status = 'active')                       AS active_templates,
              count(*) FILTER (WHERE status = 'draft')                        AS draft_templates,
              count(*) FILTER (WHERE category_id IS NOT NULL
                                  OR master_service_id IS NOT NULL)           AS used_by_services,
              count(*) FILTER (WHERE COALESCE(jsonb_array_length(steps), 0) < 2)
                                                                              AS templates_missing_steps,
              count(*) FILTER (WHERE max_sla_hours IS NOT NULL
                                 AND max_sla_hours > 0)                       AS sla_enabled,
              count(*) FILTER (WHERE EXISTS (
                    SELECT 1 FROM jsonb_array_elements(t.steps) e
                     WHERE e ? 'approval_rule'
                       AND e->'approval_rule' NOT IN ('null'::jsonb, 'false'::jsonb)))
                                                                              AS approval_enabled,
              count(*) FILTER (WHERE NOT {_HAS_MAPPING_SQL})                  AS unmapped_templates,
              count(*) FILTER (WHERE {_READINESS_SQL} = 'ready')              AS runtime_ready
            FROM master_workflow_templates t
            WHERE is_latest IS TRUE
        """))).mappings().one()
        return {k: int(v or 0) for k, v in row.items()}

    # `_compute_readiness` below is the Python definition, used when a single
    # template is being inspected. `_READINESS_SQL` (module level, above) is the
    # same rules expressed over the row's JSONB so the list can filter and the
    # summary can count without pulling every template into the API process.
    # The two must agree; `test_readiness_sql_matches_python` pins that.
    def _compute_readiness(self, row: MasterWorkflowTemplate, has_mapping: bool) -> str:
        steps = row.steps or []
        if len(steps) < 2:
            return "missing_steps"
        starts = [s for s in steps if s.get("is_start")]
        terminals = [s for s in steps if s.get("is_terminal")]
        if len(starts) != 1 or len(terminals) < 1:
            return "invalid_transitions"
        codes = {s.get("step_code") for s in steps}
        for t in (row.transitions or []):
            if t.get("from_step_code") not in codes or t.get("to_step_code") not in codes:
                return "invalid_transitions"
        if not has_mapping and not (row.category_id or row.master_service_id):
            return "missing_mapping"
        return "ready"

    async def list_workflow_templates(self, category_id: uuid.UUID | None = None,
                                      master_service_id: uuid.UUID | None = None,
                                      workflow_type: str | None = None,
                                      is_active: bool | None = None,
                                      status: str | None = None,
                                      q: str | None = None,
                                      readiness: str | None = None,
                                      page: int = 1, limit: int = 50) -> dict:
        """One page of templates, filtered, counted and sliced in the database.

        This previously ran the filter query with no LIMIT, materialised every
        matching template as an ORM object — each carrying its whole steps and
        transitions JSONB — and then took a Python slice for the page. Asking
        for 50 rows therefore cost the whole table: measured at 50k templates,
        4.2s to return one page, and the readiness filter additionally loaded
        the entire mappings table to filter in Python.

        Now: one COUNT, one id-page query with ORDER BY/LIMIT/OFFSET, and one
        fetch of just that page's rows. Cost is proportional to the page, not to
        the table.
        """
        where = ["t.is_latest IS TRUE"]
        params: dict = {}
        if category_id is not None:
            where.append("t.category_id = :category_id"); params["category_id"] = str(category_id)
        if master_service_id is not None:
            where.append("t.master_service_id = :master_service_id")
            params["master_service_id"] = str(master_service_id)
        if workflow_type is not None:
            where.append("t.workflow_type = :workflow_type"); params["workflow_type"] = workflow_type
        if is_active is not None:
            where.append("t.is_active = :is_active"); params["is_active"] = is_active
        if status is not None:
            where.append("t.status = :status"); params["status"] = status
        if q:
            where.append("(lower(t.name) LIKE :q OR lower(t.slug) LIKE :q)")
            params["q"] = f"%{q.lower()}%"
        if readiness:
            where.append(f"({_READINESS_SQL}) = :readiness")
            params["readiness"] = readiness
        clause = " AND ".join(where)

        total = int(await self.db.scalar(
            text(f"SELECT count(*) FROM master_workflow_templates t WHERE {clause}"), params) or 0)

        # Order by the same keys as before. `id` is appended so the ordering is
        # total — without it, rows sharing a display_order and name could be
        # returned in a different order per page and appear twice or not at all.
        id_rows = (await self.db.execute(text(
            f"""SELECT t.id FROM master_workflow_templates t
                 WHERE {clause}
                 ORDER BY t.display_order, t.name, t.id
                 LIMIT :limit OFFSET :offset"""),
            {**params, "limit": limit, "offset": max(0, (page - 1) * limit)})).scalars().all()

        page_rows: list = []
        derived: dict = {}
        if id_rows:
            found = {r.id: r for r in (await self.db.execute(
                select(MasterWorkflowTemplate).where(MasterWorkflowTemplate.id.in_(id_rows))
            )).scalars().all()}
            page_rows = [found[i] for i in id_rows if i in found]

            # Readiness is computed here, for this page only, and returned with
            # the row. The console used to re-derive it in the browser from the
            # row's steps — but its copy of the rule could not see
            # workflow_service_mappings, so a template mapped to a service but
            # carrying no category_id showed "Missing Mapping" while the server
            # counted it ready and the readiness filter returned it. The badge
            # and the filter disagreed on screen.
            derived = {
                r["id"]: r for r in (await self.db.execute(text(
                    f"""SELECT t.id,
                               {_READINESS_SQL} AS readiness,
                               COALESCE(jsonb_array_length(t.steps), 0)       AS step_count,
                               COALESCE(jsonb_array_length(t.transitions), 0) AS transition_count,
                               {_HAS_MAPPING_SQL}                            AS has_mapping
                          FROM master_workflow_templates t
                         WHERE t.id = ANY(CAST(:ids AS uuid[]))"""),
                    {"ids": [str(i) for i in id_rows]})).mappings().all()
            }

        def _row(r) -> dict:
            d = r.to_dict()
            extra = derived.get(r.id)
            if extra is not None:
                d["readiness"] = extra["readiness"]
                d["step_count"] = int(extra["step_count"] or 0)
                d["transition_count"] = int(extra["transition_count"] or 0)
                d["has_mapping"] = bool(extra["has_mapping"])
            return d

        return {
            "workflow_templates": [_row(r) for r in page_rows],
            "total": total,
            "meta": {"total": total, "page": page, "limit": limit,
                     "total_pages": max(1, (total + limit - 1) // limit)},
        }

    async def get_workflow_template(self, template_id: uuid.UUID) -> dict:
        row = await self._load_workflow_template(template_id)
        return row.to_dict()

    async def _allocate_workflow_slug(self, base: str, workflow_type: str) -> str:
        """Pick a free slug for a new template.

        `master_workflow_templates.slug` is UNIQUE (uq_mwt_slug). The previous
        code tried exactly two candidates — the slug, then `slug-{type}` — and
        then inserted regardless, so creating a third template with the same
        name violated the constraint and surfaced as a 500. Naming two things
        the same is ordinary admin behaviour, not an error worth a stack trace.

        All colliding slugs are read in one query and the first free candidate
        is chosen in Python, so the cost does not grow with the number of
        collisions.
        """
        taken = set((await self.db.execute(
            select(MasterWorkflowTemplate.slug)
            .where(MasterWorkflowTemplate.slug.like(f"{base}%"))
        )).scalars().all())
        if base not in taken:
            return base
        typed = f"{base}-{workflow_type}"
        if typed not in taken:
            return typed
        for n in range(2, 1000):
            candidate = f"{typed}-{n}"
            if candidate not in taken:
                return candidate
        # Beyond a thousand identically-named templates, stop guessing and make
        # the suffix unique outright rather than looping forever.
        return f"{typed}-{uuid.uuid4().hex[:8]}"

    @staticmethod
    def _require_uuid(value, field: str, *, optional: bool = False) -> uuid.UUID | None:
        """Parse an id from an unschema'd body, reporting the field on failure."""
        if value in (None, ""):
            if optional:
                return None
            raise ServiceOSException("WORKFLOW_TEMPLATE_INVALID_ID",
                                     f"{field} is required.", status_code=422)
        try:
            return uuid.UUID(str(value))
        except (ValueError, AttributeError, TypeError):
            raise ServiceOSException("WORKFLOW_TEMPLATE_INVALID_ID",
                                     f"{field} must be a valid UUID.", status_code=422) from None

    async def _require_exists(self, table: str, value: uuid.UUID, field: str) -> None:
        """Reject an id that parses but references nothing.

        `table` is never caller-supplied — only the fixed literals below — so
        interpolating it is safe; the id itself is bound.
        """
        found = await self.db.scalar(
            text(f"SELECT 1 FROM {table} WHERE id = :id LIMIT 1"), {"id": str(value)})
        if not found:
            raise ServiceOSException("WORKFLOW_TEMPLATE_INVALID_ID",
                                     f"{field} does not reference an existing record.",
                                     status_code=422)

    async def create_workflow_template(self, data: dict) -> dict:
        name = (data.get("name") or "").strip()
        workflow_type = (data.get("workflow_type") or "").strip()
        if not name:
            raise ServiceOSException("WORKFLOW_TEMPLATE_NAME_REQUIRED", "name is required.", status_code=422)
        if not workflow_type or workflow_type not in self.VALID_WORKFLOW_TYPES:
            raise ServiceOSException("WORKFLOW_TEMPLATE_INVALID_TYPE",
                                     f"workflow_type must be one of {sorted(self.VALID_WORKFLOW_TYPES)}.", status_code=422)
        if not data.get("category_id"):
            raise ServiceOSException("WORKFLOW_TEMPLATE_CATEGORY_REQUIRED",
                                     "At least one category mapping (category_id) is required.", status_code=422)
        status_val = data.get("status", "draft")
        if status_val not in self.VALID_TEMPLATE_STATUSES:
            raise ServiceOSException("WORKFLOW_TEMPLATE_INVALID_STATUS",
                                     f"status must be one of {sorted(self.VALID_TEMPLATE_STATUSES)}.", status_code=422)

        slug = await self._allocate_workflow_slug(
            _slugify(data.get("template_code") or data.get("slug") or name), workflow_type)

        # These four arrive from a raw dict body with no request schema, so a
        # malformed id used to reach uuid.UUID() unguarded and surface as a 500
        # ("an unexpected error occurred") rather than telling the caller which
        # field was wrong.
        cat_id = self._require_uuid(data.get("category_id"), "category_id")
        svc_id = self._require_uuid(data.get("master_service_id"), "master_service_id", optional=True)
        grp_id = self._require_uuid(data.get("service_group_id"), "service_group_id", optional=True)
        type_id = self._require_uuid(data.get("service_type_id"), "service_type_id", optional=True)

        # A well-formed id for a category that does not exist was accepted with
        # 201, producing a template permanently mapped to nothing — it can never
        # resolve at runtime and shows as ready because it has a category_id.
        await self._require_exists("service_categories", cat_id, "category_id")
        if svc_id is not None:
            await self._require_exists("master_services", svc_id, "master_service_id")
        steps = data.get("steps") or []
        if not isinstance(steps, list):
            raise ServiceOSException("WORKFLOW_TEMPLATE_INVALID_STEPS", "steps must be a list.", status_code=422)

        row = MasterWorkflowTemplate(
            category_id=cat_id, master_service_id=svc_id,
            service_group_id=grp_id, service_type_id=type_id,
            name=name, slug=slug,
            description=data.get("description"),
            workflow_type=workflow_type,
            steps=steps,
            transitions=data.get("transitions") or [],
            estimated_duration_minutes=int(data["estimated_duration_minutes"]) if data.get("estimated_duration_minutes") else None,
            max_sla_hours=int(data["max_sla_hours"]) if data.get("max_sla_hours") else None,
            is_active=status_val == "active",
            status=status_val,
            display_order=int(data.get("display_order", 0) or 0),
            requires_technician_assignment=bool(data.get("requires_technician_assignment", True)),
            requires_customer_confirmation=bool(data.get("requires_customer_confirmation", False)),
            requires_photo_proof=bool(data.get("requires_photo_proof", False)),
            requires_part_approval=bool(data.get("requires_part_approval", False)),
            requires_estimate_approval=bool(data.get("requires_estimate_approval", False)),
            requires_direct_payment_confirmation=bool(data.get("requires_direct_payment_confirmation", False)),
            allows_reschedule=bool(data.get("allows_reschedule", True)),
            allows_cancellation=bool(data.get("allows_cancellation", True)),
            allows_dispute_after_completion=bool(data.get("allows_dispute_after_completion", True)),
            created_by_user_id=self.actor_id,
        )
        self.db.add(row)
        await self.db.flush()
        await self._audit("master_workflow_template", row.id, "create", None, row.to_dict(), f"Created workflow template '{name}'")
        logger.info("workflow_template.created", id=str(row.id), name=name)
        return row.to_dict()

    _EDITABLE_FIELDS = (
        "name", "description", "workflow_type", "steps", "transitions",
        "estimated_duration_minutes", "max_sla_hours", "display_order",
        "category_id", "master_service_id", "service_group_id", "service_type_id",
        "requires_technician_assignment", "requires_customer_confirmation",
        "requires_photo_proof", "requires_part_approval", "requires_estimate_approval",
        "requires_direct_payment_confirmation", "allows_reschedule", "allows_cancellation",
        "allows_dispute_after_completion",
    )

    def _apply_editable_fields(self, row: MasterWorkflowTemplate, data: dict) -> None:
        for field in self._EDITABLE_FIELDS:
            if field not in data or data[field] is None:
                continue
            if field in ("category_id", "master_service_id", "service_group_id", "service_type_id"):
                setattr(row, field, uuid.UUID(str(data[field])) if data[field] else None)
            else:
                setattr(row, field, data[field])

    async def update_workflow_template(self, template_id: uuid.UUID, data: dict) -> dict:
        """Editing a draft template updates it in place. Editing an ACTIVE template
        creates a new draft version instead — existing jobs keep referencing the old,
        unmodified row (versioning rule: no destructive edits to live workflows)."""
        row = await self._load_workflow_template(template_id)

        if row.status == "active":
            new_row = MasterWorkflowTemplate(
                category_id=row.category_id, master_service_id=row.master_service_id,
                service_group_id=row.service_group_id, service_type_id=row.service_type_id,
                name=row.name, slug=f"{row.slug}-v{row.version_number + 1}",
                description=row.description, workflow_type=row.workflow_type,
                steps=row.steps, transitions=row.transitions,
                estimated_duration_minutes=row.estimated_duration_minutes,
                max_sla_hours=row.max_sla_hours,
                is_active=False, status="draft", display_order=row.display_order,
                requires_technician_assignment=row.requires_technician_assignment,
                requires_customer_confirmation=row.requires_customer_confirmation,
                requires_photo_proof=row.requires_photo_proof,
                requires_part_approval=row.requires_part_approval,
                requires_estimate_approval=row.requires_estimate_approval,
                requires_direct_payment_confirmation=row.requires_direct_payment_confirmation,
                allows_reschedule=row.allows_reschedule, allows_cancellation=row.allows_cancellation,
                allows_dispute_after_completion=row.allows_dispute_after_completion,
                version_number=row.version_number + 1, parent_template_id=row.parent_template_id or row.id,
                is_latest=True, created_by_user_id=self.actor_id,
            )
            self._apply_editable_fields(new_row, data)
            row.is_latest = False
            self.db.add(new_row)
            await self.db.flush()
            await self._audit("master_workflow_template", new_row.id, "new_version_from_edit",
                              row.to_dict(), new_row.to_dict(),
                              f"Editing active workflow '{row.name}' created draft v{new_row.version_number}")
            return new_row.to_dict()

        old = row.to_dict()
        self._apply_editable_fields(row, data)
        await self.db.flush()
        await self._audit("master_workflow_template", row.id, "update", old, row.to_dict(), f"Updated workflow template '{row.name}'")
        return row.to_dict()

    async def delete_workflow_template(self, template_id: uuid.UUID) -> dict:
        row = await self._load_workflow_template(template_id)
        old = row.to_dict()
        row.is_active = False
        row.status = "inactive"
        await self.db.flush()
        await self._audit("master_workflow_template", row.id, "deactivate", old, row.to_dict(), f"Deactivated workflow template '{row.name}'")
        return {"deleted": True, "id": str(template_id)}

    async def clone_workflow_template(self, template_id: uuid.UUID) -> dict:
        row = await self._load_workflow_template(template_id)
        base_slug = _slugify(f"{row.name}-copy")
        slug = base_slug
        i = 1
        while (await self.db.execute(select(MasterWorkflowTemplate).where(MasterWorkflowTemplate.slug == slug))).scalar_one_or_none():
            i += 1
            slug = f"{base_slug}-{i}"
        new_row = MasterWorkflowTemplate(
            category_id=row.category_id, master_service_id=row.master_service_id,
            service_group_id=row.service_group_id, service_type_id=row.service_type_id,
            name=f"{row.name} (Copy)", slug=slug, description=row.description,
            workflow_type=row.workflow_type, steps=row.steps, transitions=row.transitions,
            estimated_duration_minutes=row.estimated_duration_minutes, max_sla_hours=row.max_sla_hours,
            is_active=False, status="draft", display_order=row.display_order,
            requires_technician_assignment=row.requires_technician_assignment,
            requires_customer_confirmation=row.requires_customer_confirmation,
            requires_photo_proof=row.requires_photo_proof,
            requires_part_approval=row.requires_part_approval,
            requires_estimate_approval=row.requires_estimate_approval,
            requires_direct_payment_confirmation=row.requires_direct_payment_confirmation,
            allows_reschedule=row.allows_reschedule, allows_cancellation=row.allows_cancellation,
            allows_dispute_after_completion=row.allows_dispute_after_completion,
            version_number=1, parent_template_id=None, is_latest=True,
            created_by_user_id=self.actor_id,
        )
        self.db.add(new_row)
        await self.db.flush()
        await self._audit("master_workflow_template", new_row.id, "clone", None, new_row.to_dict(), f"Cloned from '{row.name}'")
        return new_row.to_dict()

    async def create_new_version(self, template_id: uuid.UUID) -> dict:
        row = await self._load_workflow_template(template_id)
        new_row = MasterWorkflowTemplate(
            category_id=row.category_id, master_service_id=row.master_service_id,
            service_group_id=row.service_group_id, service_type_id=row.service_type_id,
            name=row.name, slug=f"{row.slug}-v{row.version_number + 1}",
            description=row.description, workflow_type=row.workflow_type,
            steps=row.steps, transitions=row.transitions,
            estimated_duration_minutes=row.estimated_duration_minutes, max_sla_hours=row.max_sla_hours,
            is_active=False, status="draft", display_order=row.display_order,
            requires_technician_assignment=row.requires_technician_assignment,
            requires_customer_confirmation=row.requires_customer_confirmation,
            requires_photo_proof=row.requires_photo_proof,
            requires_part_approval=row.requires_part_approval,
            requires_estimate_approval=row.requires_estimate_approval,
            requires_direct_payment_confirmation=row.requires_direct_payment_confirmation,
            allows_reschedule=row.allows_reschedule, allows_cancellation=row.allows_cancellation,
            allows_dispute_after_completion=row.allows_dispute_after_completion,
            version_number=row.version_number + 1, parent_template_id=row.parent_template_id or row.id,
            is_latest=True, created_by_user_id=self.actor_id,
        )
        row.is_latest = False
        self.db.add(new_row)
        await self.db.flush()
        await self._audit("master_workflow_template", new_row.id, "new_version", row.to_dict(), new_row.to_dict(),
                          f"Created draft v{new_row.version_number} of '{row.name}'")
        return new_row.to_dict()

    async def validate_workflow_template(self, template_id: uuid.UUID) -> dict:
        row = await self._load_workflow_template(template_id)
        errors, warnings = [], []
        steps = row.steps or []
        if len(steps) < 2:
            errors.append("Active template must have at least 2 steps.")
        starts = [s for s in steps if s.get("is_start")]
        terminals = [s for s in steps if s.get("is_terminal")]
        if len(starts) != 1:
            errors.append(f"Exactly one start step is required (found {len(starts)}).")
        if len(terminals) < 1:
            errors.append("At least one terminal step is required.")
        codes = {s.get("step_code") for s in steps}
        reached = {t.get("to_step_code") for t in (row.transitions or [])}
        for t in (row.transitions or []):
            if t.get("from_step_code") not in codes:
                errors.append(f"Transition references unknown from_step_code '{t.get('from_step_code')}'.")
            if t.get("to_step_code") not in codes:
                errors.append(f"Transition references unknown to_step_code '{t.get('to_step_code')}'.")
        for s in steps:
            code = s.get("step_code")
            if not s.get("is_start") and code not in reached:
                errors.append(f"Step '{code}' is orphaned — no transition leads to it.")
        has_mapping = bool((await self.db.execute(
            select(WorkflowServiceMapping.id).where(WorkflowServiceMapping.template_id == template_id)
        )).scalar_one_or_none())
        if not has_mapping and not (row.category_id or row.master_service_id):
            warnings.append("Template has no service mapping and no direct category/service assignment.")
        return {"template_id": str(template_id), "valid": len(errors) == 0, "errors": errors, "warnings": warnings}

    async def get_workflow_readiness(self, template_id: uuid.UUID) -> dict:
        row = await self._load_workflow_template(template_id)
        has_mapping = bool((await self.db.execute(
            select(WorkflowServiceMapping.id).where(WorkflowServiceMapping.template_id == template_id)
        )).scalar_one_or_none())
        return {"template_id": str(template_id), "readiness": self._compute_readiness(row, has_mapping)}

    async def activate_workflow_template(self, template_id: uuid.UUID) -> dict:
        validation = await self.validate_workflow_template(template_id)
        if not validation["valid"]:
            raise ServiceOSException("WORKFLOW_TEMPLATE_INVALID",
                "This workflow cannot be activated because required steps or transitions are missing.",
                status_code=422, context={"errors": validation["errors"]})
        row = await self._load_workflow_template(template_id)
        old = row.to_dict()

        # Deprecate the previous active version in the same parent chain, if any.
        chain_root = row.parent_template_id or row.id
        prev_active = (await self.db.execute(
            select(MasterWorkflowTemplate).where(
                MasterWorkflowTemplate.status == "active",
                MasterWorkflowTemplate.id != row.id,
                (MasterWorkflowTemplate.id == chain_root) | (MasterWorkflowTemplate.parent_template_id == chain_root),
            )
        )).scalars().all()
        for prev in prev_active:
            prev.status = "deprecated"
            prev.is_active = False
            prev.deprecated_at = utcnow()

        row.status = "active"
        row.is_active = True
        row.is_latest = True
        row.activated_at = utcnow()
        await self.db.flush()
        await self._audit("master_workflow_template", row.id, "activate", old, row.to_dict(), f"Activated workflow template '{row.name}'")
        return row.to_dict()

    async def deactivate_workflow_template(self, template_id: uuid.UUID) -> dict:
        row = await self._load_workflow_template(template_id)
        old = row.to_dict()
        row.status = "inactive"
        row.is_active = False
        await self.db.flush()
        await self._audit("master_workflow_template", row.id, "deactivate", old, row.to_dict(), f"Deactivated workflow template '{row.name}'")
        return row.to_dict()

    # ── Steps CRUD (JSONB list mutation) ──────────────────────────────────────

    def _validate_step(self, step: dict) -> None:
        if not step.get("step_name"):
            raise ServiceOSException("WORKFLOW_STEP_NAME_REQUIRED", "step_name is required.", status_code=422)
        if step.get("step_type") not in self.VALID_STEP_TYPES:
            raise ServiceOSException("WORKFLOW_STEP_INVALID_TYPE",
                f"step_type must be one of {sorted(self.VALID_STEP_TYPES)}.", status_code=422)
        if step.get("actor") not in self.VALID_ACTORS:
            raise ServiceOSException("WORKFLOW_STEP_INVALID_ACTOR",
                f"actor must be one of {sorted(self.VALID_ACTORS)}.", status_code=422)

    async def add_step(self, template_id: uuid.UUID, data: dict) -> dict:
        row = await self._load_workflow_template(template_id)
        self._validate_step(data)
        steps = list(row.steps or [])
        step_code = data.get("step_code") or _slugify(data["step_name"])
        if any(s.get("step_code") == step_code for s in steps):
            step_code = f"{step_code}-{len(steps) + 1}"
        step = {
            "id": str(uuid.uuid4()), "step_code": step_code,
            "step_name": data["step_name"], "step_type": data["step_type"], "actor": data["actor"],
            "description": data.get("description"),
            "status_before": data.get("status_before"), "status_after": data.get("status_after"),
            "is_start": bool(data.get("is_start", False)), "is_terminal": bool(data.get("is_terminal", False)),
            "is_required": bool(data.get("is_required", True)), "can_skip": bool(data.get("can_skip", False)),
            "display_order": int(data.get("display_order", len(steps))),
            "estimated_duration_minutes": data.get("estimated_duration_minutes"),
            "sla_minutes": data.get("sla_minutes"),
            "warning_before_minutes": data.get("warning_before_minutes"),
            "escalation_target": data.get("escalation_target"),
            "auto_notify": bool(data.get("auto_notify", False)), "auto_escalate": bool(data.get("auto_escalate", False)),
            "requires_note": bool(data.get("requires_note", False)),
            "requires_photo": bool(data.get("requires_photo", False)),
            "requires_document": bool(data.get("requires_document", False)),
            "requires_customer_signature": bool(data.get("requires_customer_signature", False)),
            "requires_customer_approval": bool(data.get("requires_customer_approval", False)),
            "requires_admin_approval": bool(data.get("requires_admin_approval", False)),
            "notification_trigger": bool(data.get("notification_trigger", False)),
            "evidence_rules": data.get("evidence_rules") or [],
            "approval_rule": data.get("approval_rule"),
            "automation_triggers": data.get("automation_triggers") or [],
        }
        steps.append(step)
        old = row.to_dict()
        row.steps = steps
        await self.db.flush()
        await self._audit("master_workflow_template", row.id, "step_added", old, row.to_dict(), f"Added step '{step['step_name']}'")
        return step

    async def update_step(self, template_id: uuid.UUID, step_id: str, data: dict) -> dict:
        row = await self._load_workflow_template(template_id)
        steps = list(row.steps or [])
        idx = next((i for i, s in enumerate(steps) if s.get("id") == step_id), None)
        if idx is None:
            raise NotFoundException("WorkflowStep", step_id)
        old = row.to_dict()
        merged = {**steps[idx], **{k: v for k, v in data.items() if v is not None}}
        steps[idx] = merged
        row.steps = steps
        await self.db.flush()
        await self._audit("master_workflow_template", row.id, "step_updated", old, row.to_dict(), f"Updated step '{merged.get('step_name')}'")
        return merged

    async def delete_step(self, template_id: uuid.UUID, step_id: str) -> dict:
        row = await self._load_workflow_template(template_id)
        steps = list(row.steps or [])
        target = next((s for s in steps if s.get("id") == step_id), None)
        if not target:
            raise NotFoundException("WorkflowStep", step_id)
        old = row.to_dict()
        row.steps = [s for s in steps if s.get("id") != step_id]
        row.transitions = [t for t in (row.transitions or [])
                           if t.get("from_step_code") != target.get("step_code")
                           and t.get("to_step_code") != target.get("step_code")]
        await self.db.flush()
        await self._audit("master_workflow_template", row.id, "step_deleted", old, row.to_dict(), f"Deleted step '{target.get('step_name')}'")
        return {"deleted": True, "id": step_id}

    async def reorder_steps(self, template_id: uuid.UUID, step_ids: list[str]) -> dict:
        row = await self._load_workflow_template(template_id)
        steps = list(row.steps or [])
        by_id = {s["id"]: s for s in steps}
        reordered = []
        for i, sid in enumerate(step_ids):
            if sid in by_id:
                by_id[sid]["display_order"] = i
                reordered.append(by_id[sid])
        remaining = [s for s in steps if s["id"] not in step_ids]
        row.steps = reordered + remaining
        await self.db.flush()
        return {"steps": row.steps}

    # ── Transitions CRUD (JSONB list mutation) ────────────────────────────────

    async def list_transitions(self, template_id: uuid.UUID) -> dict:
        row = await self._load_workflow_template(template_id)
        return {"transitions": row.transitions or [], "total": len(row.transitions or [])}

    async def add_transition(self, template_id: uuid.UUID, data: dict) -> dict:
        row = await self._load_workflow_template(template_id)
        steps = row.steps or []
        codes = {s.get("step_code") for s in steps}
        if data.get("from_step_code") not in codes or data.get("to_step_code") not in codes:
            raise ServiceOSException("WORKFLOW_TRANSITION_INVALID_STEP",
                "from_step_code and to_step_code must reference existing steps.", status_code=422)
        if data.get("allowed_actor") not in self.VALID_ACTORS:
            raise ServiceOSException("WORKFLOW_TRANSITION_INVALID_ACTOR",
                f"allowed_actor must be one of {sorted(self.VALID_ACTORS)}.", status_code=422)
        transition = {
            "id": str(uuid.uuid4()),
            "from_step_code": data["from_step_code"], "to_step_code": data["to_step_code"],
            "from_status": data.get("from_status"), "to_status": data.get("to_status"),
            "allowed_actor": data["allowed_actor"], "required_permission": data.get("required_permission"),
            "condition": data.get("condition"),
            "requires_reason": bool(data.get("requires_reason", False)),
            "requires_note": bool(data.get("requires_note", False)),
            "auto_transition": bool(data.get("auto_transition", False)),
        }
        old = row.to_dict()
        row.transitions = list(row.transitions or []) + [transition]
        await self.db.flush()
        await self._audit("master_workflow_template", row.id, "transition_added", old, row.to_dict(), "Added transition")
        return transition

    async def update_transition(self, template_id: uuid.UUID, transition_id: str, data: dict) -> dict:
        row = await self._load_workflow_template(template_id)
        transitions = list(row.transitions or [])
        idx = next((i for i, t in enumerate(transitions) if t.get("id") == transition_id), None)
        if idx is None:
            raise NotFoundException("WorkflowTransition", transition_id)
        merged = {**transitions[idx], **{k: v for k, v in data.items() if v is not None}}
        transitions[idx] = merged
        row.transitions = transitions
        await self.db.flush()
        return merged

    async def delete_transition(self, template_id: uuid.UUID, transition_id: str) -> dict:
        row = await self._load_workflow_template(template_id)
        row.transitions = [t for t in (row.transitions or []) if t.get("id") != transition_id]
        await self.db.flush()
        return {"deleted": True, "id": transition_id}

    # ── Service mappings ───────────────────────────────────────────────────────

    async def list_workflow_mappings(self, template_id: uuid.UUID) -> dict:
        rows = (await self.db.execute(
            select(WorkflowServiceMapping).where(WorkflowServiceMapping.template_id == template_id)
            .order_by(WorkflowServiceMapping.priority.desc())
        )).scalars().all()
        return {"mappings": [r.to_dict() for r in rows], "total": len(rows)}

    async def create_workflow_mapping(self, template_id: uuid.UUID, data: dict) -> dict:
        if not data.get("category_id"):
            raise ServiceOSException("WORKFLOW_MAPPING_CATEGORY_REQUIRED", "category_id is required.", status_code=422)
        mapping = WorkflowServiceMapping(
            template_id=template_id, category_id=uuid.UUID(str(data["category_id"])),
            service_group_id=uuid.UUID(str(data["service_group_id"])) if data.get("service_group_id") else None,
            master_service_id=uuid.UUID(str(data["master_service_id"])) if data.get("master_service_id") else None,
            service_type_id=uuid.UUID(str(data["service_type_id"])) if data.get("service_type_id") else None,
            brand_id=uuid.UUID(str(data["brand_id"])) if data.get("brand_id") else None,
            tenant_id=uuid.UUID(str(data["tenant_id"])) if data.get("tenant_id") else None,
            priority=int(data.get("priority", 0)),
        )
        self.db.add(mapping)
        await self.db.flush()
        await self._audit("workflow_service_mapping", mapping.id, "create", None, mapping.to_dict(), "Created workflow mapping")
        return mapping.to_dict()

    async def delete_workflow_mapping(self, template_id: uuid.UUID, mapping_id: uuid.UUID) -> dict:
        mapping = await self.db.scalar(
            select(WorkflowServiceMapping).where(
                WorkflowServiceMapping.id == mapping_id, WorkflowServiceMapping.template_id == template_id))
        if not mapping:
            raise NotFoundException("WorkflowServiceMapping", str(mapping_id))
        await self.db.delete(mapping)
        await self.db.flush()
        return {"deleted": True, "id": str(mapping_id)}

    async def preview_workflow_runtime(self, category_id: uuid.UUID | None = None,
                                       master_service_id: uuid.UUID | None = None,
                                       service_type_id: uuid.UUID | None = None,
                                       tenant_id: uuid.UUID | None = None) -> dict:
        stmt = select(WorkflowServiceMapping).where(WorkflowServiceMapping.status == "active")
        if category_id:
            stmt = stmt.where(WorkflowServiceMapping.category_id == category_id)
        candidates = (await self.db.execute(stmt)).scalars().all()

        def specificity(m: WorkflowServiceMapping) -> int:
            score = 0
            if tenant_id and m.tenant_id == tenant_id: score += 8
            if service_type_id and m.service_type_id == service_type_id: score += 4
            if master_service_id and m.master_service_id == master_service_id: score += 2
            return score

        best = None
        if candidates:
            matching = [m for m in candidates if
                        (not m.tenant_id or m.tenant_id == tenant_id) and
                        (not m.service_type_id or m.service_type_id == service_type_id) and
                        (not m.master_service_id or m.master_service_id == master_service_id)]
            if matching:
                best = max(matching, key=specificity)

        template = None
        if best:
            template = await self.db.scalar(
                select(MasterWorkflowTemplate).where(MasterWorkflowTemplate.id == best.template_id))
        if not template and category_id:
            template = await self.db.scalar(
                select(MasterWorkflowTemplate).where(
                    MasterWorkflowTemplate.category_id == category_id,
                    MasterWorkflowTemplate.status == "active",
                    MasterWorkflowTemplate.is_latest == True,
                ).order_by(MasterWorkflowTemplate.display_order))

        if not template:
            return {"resolved": False, "message": "No active workflow template resolved for the given scope."}

        has_mapping = bool(best)
        readiness = self._compute_readiness(template, has_mapping)
        return {"resolved": True, "template": template.to_dict(), "readiness": readiness,
                "matched_mapping": best.to_dict() if best else None}

    # ── Seed Home Services defaults ───────────────────────────────────────────

    def _home_services_seed_specs(self) -> list[dict]:
        def step(code, name, stype, actor, **kw):
            return {"step_code": code, "step_name": name, "step_type": stype, "actor": actor, **kw}

        common_tail = [
            step("work_completed", "Work Completed", "technician_action", "technician",
                 requires_photo=True, requires_note=True),
            step("customer_confirmed", "Customer Confirms Completion", "customer_action", "customer",
                 requires_customer_approval=True),
            step("payment_recorded", "Payment Collected Directly by Tenant", "tenant_action", "tenant_owner",
                 automation_triggers=[{"trigger_type": "on_step_enter", "action": "send_notification"}]),
            step("completed", "Job Completed", "system", "system", is_terminal=True,
                 automation_triggers=[
                     {"trigger_type": "on_job_completed", "action": "deduct_job_credit"},
                     {"trigger_type": "on_job_completed", "action": "request_customer_review"},
                     {"trigger_type": "on_job_completed", "action": "open_dispute_window"},
                 ]),
        ]

        def transitions_for(steps: list[dict]) -> list[dict]:
            out = []
            for a, b in zip(steps, steps[1:]):
                out.append({"from_step_code": a["step_code"], "to_step_code": b["step_code"],
                            "allowed_actor": b["actor"], "auto_transition": b["step_type"] == "system"})
            return out

        specs = []

        repair_steps = [
            step("booking_created", "Customer Booking Created", "system", "system", is_start=True),
            step("provider_assigned", "Provider Assigned", "system", "system"),
            step("technician_accepted", "Technician Accepted", "technician_action", "technician"),
            step("on_the_way", "Technician On The Way", "technician_action", "technician"),
            step("arrived", "Technician Arrived", "technician_action", "technician",
                 evidence_rules=[{"evidence_type": "location_checkin", "required": True}]),
            step("diagnosis_started", "Diagnosis Started", "technician_action", "technician"),
            step("diagnosis_completed", "Diagnosis Completed", "technician_action", "technician", requires_note=True),
            step("estimate_pending_approval", "Customer Approves Estimate/Parts", "approval", "customer",
                 requires_customer_approval=True,
                 approval_rule={"approval_type": "customer_parts_approval", "approval_actor": "customer",
                               "required": True, "timeout_minutes": 1440}),
            step("work_started", "Work Started", "technician_action", "technician"),
        ] + common_tail
        specs.append({
            "name": "Standard Repair Workflow", "workflow_type": "repair",
            "description": "End-to-end repair job flow with diagnosis, parts approval, and direct payment.",
            "requires_photo_proof": True, "requires_part_approval": True,
            "requires_estimate_approval": True, "requires_direct_payment_confirmation": True,
            "steps": repair_steps, "transitions": transitions_for(repair_steps),
        })

        install_steps = [
            step("booking_created", "Customer Booking Created", "system", "system", is_start=True),
            step("provider_assigned", "Provider Assigned", "system", "system"),
            step("technician_accepted", "Technician Accepted", "technician_action", "technician"),
            step("on_the_way", "Technician On The Way", "technician_action", "technician"),
            step("arrived", "Technician Arrived", "technician_action", "technician",
                 evidence_rules=[{"evidence_type": "location_checkin", "required": True}]),
            step("installation_started", "Installation Started", "technician_action", "technician"),
            step("work_started", "Work Started", "technician_action", "technician"),
        ] + common_tail
        specs.append({
            "name": "Standard Installation Workflow", "workflow_type": "installation",
            "description": "New unit/equipment installation flow with direct payment confirmation.",
            "requires_photo_proof": True, "requires_direct_payment_confirmation": True,
            "steps": install_steps, "transitions": transitions_for(install_steps),
        })

        uninstall_steps = [
            step("booking_created", "Customer Booking Created", "system", "system", is_start=True),
            step("provider_assigned", "Provider Assigned", "system", "system"),
            step("technician_accepted", "Technician Accepted", "technician_action", "technician"),
            step("arrived", "Technician Arrived", "technician_action", "technician"),
            step("work_started", "Work Started", "technician_action", "technician"),
        ] + common_tail
        specs.append({
            "name": "Standard Uninstallation Workflow", "workflow_type": "uninstallation",
            "description": "Equipment removal/uninstallation flow.",
            "requires_photo_proof": True, "requires_direct_payment_confirmation": True,
            "steps": uninstall_steps, "transitions": transitions_for(uninstall_steps),
        })

        inspection_steps = [
            step("booking_created", "Customer Booking Created", "system", "system", is_start=True),
            step("provider_assigned", "Provider Assigned", "system", "system"),
            step("technician_accepted", "Technician Accepted", "technician_action", "technician"),
            step("arrived", "Technician Arrived", "technician_action", "technician"),
            step("inspection_completed", "Inspection Completed", "technician_action", "technician",
                 requires_note=True, requires_photo=True),
            step("customer_confirmed", "Customer Confirms Visit", "customer_action", "customer"),
            step("completed", "Visit Completed", "system", "system", is_terminal=True,
                 automation_triggers=[{"trigger_type": "on_job_completed", "action": "request_customer_review"}]),
        ]
        specs.append({
            "name": "Inspection / Visit Workflow", "workflow_type": "inspection",
            "description": "Site visit / inspection-only flow with no direct payment step.",
            "requires_photo_proof": True,
            "steps": inspection_steps, "transitions": transitions_for(inspection_steps),
        })

        cleaning_steps = [
            step("booking_created", "Customer Booking Created", "system", "system", is_start=True),
            step("provider_assigned", "Provider Assigned", "system", "system"),
            step("technician_accepted", "Technician Accepted", "technician_action", "technician"),
            step("on_the_way", "Technician On The Way", "technician_action", "technician"),
            step("arrived", "Technician Arrived", "technician_action", "technician"),
            step("work_started", "Cleaning Started", "technician_action", "technician"),
        ] + common_tail
        specs.append({
            "name": "Cleaning Workflow", "workflow_type": "cleaning",
            "description": "Standard cleaning service flow with direct payment confirmation.",
            "requires_photo_proof": True, "requires_direct_payment_confirmation": True,
            "steps": cleaning_steps, "transitions": transitions_for(cleaning_steps),
        })

        emergency_steps = [
            step("booking_created", "Emergency Booking Created", "system", "system", is_start=True),
            step("provider_assigned", "Provider Assigned (Priority)", "system", "system",
                 sla_minutes=15, auto_escalate=True, escalation_target="tenant_owner"),
            step("technician_accepted", "Technician Accepted", "technician_action", "technician", sla_minutes=10),
            step("on_the_way", "Technician On The Way", "technician_action", "technician"),
            step("arrived", "Technician Arrived", "technician_action", "technician", sla_minutes=45,
                 evidence_rules=[{"evidence_type": "location_checkin", "required": True}]),
            step("work_started", "Emergency Work Started", "technician_action", "technician"),
        ] + common_tail
        specs.append({
            "name": "Emergency Repair Workflow", "workflow_type": "repair",
            "description": "Priority/emergency repair flow with tight assignment and arrival SLAs.",
            "requires_photo_proof": True, "requires_direct_payment_confirmation": True,
            "max_sla_hours": 4,
            "steps": emergency_steps, "transitions": transitions_for(emergency_steps),
        })

        for spec in specs:
            for s in spec["steps"]:
                s.setdefault("id", str(uuid.uuid4()))
                s.setdefault("is_required", True)
            for t in spec["transitions"]:
                t.setdefault("id", str(uuid.uuid4()))
        return specs

    async def seed_workflow_defaults_preview(self) -> dict:
        specs = self._home_services_seed_specs()
        existing_names = set((await self.db.execute(select(MasterWorkflowTemplate.name))).scalars().all())
        will_create = [s["name"] for s in specs if s["name"] not in existing_names]
        return {"templates": [{"name": s["name"], "workflow_type": s["workflow_type"],
                                "steps": len(s["steps"]), "description": s["description"]} for s in specs],
                "will_create": len(will_create), "already_exist": sorted(existing_names & {s["name"] for s in specs})}

    async def seed_workflow_defaults(self) -> dict:
        specs = self._home_services_seed_specs()
        existing_names = set((await self.db.execute(select(MasterWorkflowTemplate.name))).scalars().all())
        created = []
        for i, spec in enumerate(specs):
            if spec["name"] in existing_names:
                continue
            slug = _slugify(spec["name"])
            row = MasterWorkflowTemplate(
                name=spec["name"], slug=slug, description=spec["description"],
                workflow_type=spec["workflow_type"], steps=spec["steps"], transitions=spec["transitions"],
                status="draft", is_active=False, display_order=i,
                requires_photo_proof=spec.get("requires_photo_proof", False),
                requires_part_approval=spec.get("requires_part_approval", False),
                requires_estimate_approval=spec.get("requires_estimate_approval", False),
                requires_direct_payment_confirmation=spec.get("requires_direct_payment_confirmation", False),
                max_sla_hours=spec.get("max_sla_hours"),
                created_by_user_id=self.actor_id,
            )
            self.db.add(row)
            await self.db.flush()
            await self._audit("master_workflow_template", row.id, "seeded", None, row.to_dict(),
                              f"Seeded Home Services default '{spec['name']}'")
            created.append(row.to_dict())
        return {"created": created, "count": len(created)}

    async def _load_workflow_template(self, template_id: uuid.UUID) -> MasterWorkflowTemplate:
        result = await self.db.execute(select(MasterWorkflowTemplate).where(MasterWorkflowTemplate.id == template_id))
        row = result.scalar_one_or_none()
        if not row:
            raise NotFoundException("MasterWorkflowTemplate", str(template_id))
        return row

    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
    # MASTER DATA AUDIT LOG  (Sprint 34C)
    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

    async def list_master_data_audit(self, entity_type: str | None = None,
                                     entity_id: uuid.UUID | None = None,
                                     limit: int = 50) -> dict:
        stmt = select(MasterDataAuditLog).order_by(MasterDataAuditLog.created_at.desc())
        if entity_type:
            stmt = stmt.where(MasterDataAuditLog.entity_type == entity_type)
        if entity_id:
            stmt = stmt.where(MasterDataAuditLog.entity_id == entity_id)
        stmt = stmt.limit(min(limit, 200))
        result = await self.db.execute(stmt)
        rows = result.scalars().all()
        return {"audit_log": [r.to_dict() for r in rows], "total": len(rows)}

    async def _audit(self, entity_type: str, entity_id: uuid.UUID, action: str,
                     old_value: dict | None, new_value: dict | None,
                     change_summary: str) -> None:
        entry = MasterDataAuditLog(
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            actor_user_id=self.actor_id,
            actor_role=self.actor_role,
            old_value=old_value,
            new_value=new_value,
            change_summary=change_summary,
            request_id=self.request_id,
        )
        self.db.add(entry)
        await self.db.flush()

    # ═══════════════════════════════════════════════════════════
    # SERVICE GROUPS — Enterprise (P0 Upgrade)
    # ═══════════════════════════════════════════════════════════

    async def _sg_linked_counts(self, group_ids: list[uuid.UUID]) -> dict[str, dict]:
        """Batch-count linked services and providers per service group."""
        if not group_ids:
            return {}
        # Services per group
        svc_stmt = (
            select(MasterService.service_group_id, func.count().label("cnt"))
            .where(MasterService.service_group_id.in_(group_ids), MasterService.deleted_at.is_(None))
            .group_by(MasterService.service_group_id)
        )
        svc_result = await self.db.execute(svc_stmt)
        svc_counts = {str(r[0]): r[1] for r in svc_result.all()}

        active_svc_result = await self.db.execute(
            select(MasterService.service_group_id, func.count().label("cnt"))
            .where(
                MasterService.service_group_id.in_(group_ids),
                MasterService.deleted_at.is_(None),
                MasterService.is_active == True,
            )
            .group_by(MasterService.service_group_id)
        )
        active_svc_counts = {str(row[0]): int(row[1]) for row in active_svc_result.all()}

        # Count distinct providers entirely in PostgreSQL.  The previous
        # implementation materialised every tenant/service pair into Python
        # sets, which grows with tenants rather than the 100-row directory page.
        provider_result = await self.db.execute(
            select(
                MasterService.service_group_id,
                func.count(func.distinct(TenantService.tenant_id)).label("cnt"),
            )
            .join(TenantService, TenantService.master_service_id == MasterService.id)
            .where(
                MasterService.service_group_id.in_(group_ids),
                MasterService.deleted_at.is_(None),
                MasterService.is_active == True,
                TenantService.is_enabled == True,
                TenantService.deleted_at.is_(None),
            )
            .group_by(MasterService.service_group_id)
        )
        provider_counts = {str(row[0]): int(row[1]) for row in provider_result.all()}

        out: dict[str, dict] = {}
        for gid in [str(g) for g in group_ids]:
            out[gid] = {
                "services": svc_counts.get(gid, 0),
                "active_services": active_svc_counts.get(gid, 0),
                "providers": provider_counts.get(gid, 0),
            }
        return out

    def _sg_readiness(self, group: ServiceGroup, services_count: int) -> str:
        if group.status in ("deleted", "archived"):
            return "archived"
        if group.status == "inactive":
            return "inactive"
        if services_count == 0:
            return "empty_group"
        return "ready"

    async def get_service_groups_summary(self) -> dict:
        has_services = exists(select(MasterService.id).where(
            MasterService.service_group_id == ServiceGroup.id,
            MasterService.deleted_at.is_(None),
        ))
        live = ServiceGroup.deleted_at.is_(None)
        summary = (await self.db.execute(select(
            func.count(ServiceGroup.id).filter(live),
            func.count(ServiceGroup.id).filter(live, ServiceGroup.status == "active"),
            func.count(ServiceGroup.id).filter(live, ServiceGroup.status == "inactive"),
            func.count(ServiceGroup.id).filter(live, has_services),
            func.count(ServiceGroup.id).filter(live, ~has_services),
            func.count(ServiceGroup.id).filter(live, ServiceGroup.status == "active", has_services),
            func.count(ServiceGroup.id).filter(ServiceGroup.deleted_at.isnot(None)),
        ))).one()
        total, active, inactive, with_services, empty, runtime_ready, retired = map(int, summary)
        return {
            "total": total,
            "active": active,
            "inactive": inactive,
            "groups_with_services": with_services,
            "empty_groups": empty,
            "runtime_ready": runtime_ready,
            "retired": retired,
        }

    async def list_service_groups_enterprise(
        self,
        q: str | None = None,
        category_id: uuid.UUID | None = None,
        status: str | None = None,
        has_services: bool | None = None,
        retired: bool = False,
        sort_by: str = "display_order",
        sort_dir: str = "asc",
        limit: int = 200,
        offset: int = 0,
    ) -> dict:
        stmt = (
            select(ServiceGroup, ServiceCategory.name, ServiceCategory.is_active)
            .join(ServiceCategory, ServiceCategory.id == ServiceGroup.category_id)
            .where(ServiceGroup.deleted_at.isnot(None) if retired else ServiceGroup.deleted_at.is_(None))
        )
        if category_id:
            stmt = stmt.where(ServiceGroup.category_id == category_id)
        if status:
            stmt = stmt.where(ServiceGroup.status == status)
        if q:
            like = f"%{q.lower()}%"
            stmt = stmt.where(
                func.lower(ServiceGroup.name).like(like) |
                func.lower(ServiceGroup.code).like(like) |
                func.lower(ServiceGroup.slug).like(like)
            )
        if has_services is not None:
            service_count = (
                select(func.count(MasterService.id))
                .where(
                    MasterService.service_group_id == ServiceGroup.id,
                    MasterService.deleted_at.is_(None),
                )
                .correlate(ServiceGroup)
                .scalar_subquery()
            )
            stmt = stmt.where(service_count > 0 if has_services else service_count == 0)
        total = int(await self.db.scalar(select(func.count()).select_from(stmt.subquery())) or 0)
        sort_columns = {
            "name": ServiceGroup.name,
            "category": ServiceCategory.name,
            "status": ServiceGroup.status,
            "display_order": ServiceGroup.display_order,
            "updated_at": ServiceGroup.updated_at,
        }
        sort_column = sort_columns.get(sort_by, ServiceGroup.display_order)
        order = sort_column.desc() if sort_dir.lower() == "desc" else sort_column.asc()
        stmt = stmt.order_by(order, ServiceGroup.id).limit(limit).offset(offset)
        result = await self.db.execute(stmt)
        group_rows = result.all()
        groups = [row[0] for row in group_rows]
        group_ids = [g.id for g in groups]
        counts = await self._sg_linked_counts(group_ids)

        out = []
        for g, category_name, category_active in group_rows:
            d = g.to_dict()
            lc = counts.get(str(g.id), {"services": 0, "providers": 0})
            d["category_name"] = category_name
            d["category_active"] = bool(category_active)
            d["deleted_at"] = g.deleted_at.isoformat() if g.deleted_at else None
            d["linked_counts"] = lc
            d["runtime_readiness"] = "category_inactive" if not category_active and not retired else self._sg_readiness(g, lc.get("services", 0))
            out.append(d)
        return {"groups": out, "total": total, "limit": limit, "offset": offset, "retired": retired}

    async def get_service_group_enterprise(self, group_id: uuid.UUID, include_retired: bool = False) -> dict:
        row = (await self.db.execute(
            select(ServiceGroup, ServiceCategory.name, ServiceCategory.is_active)
            .join(ServiceCategory, ServiceCategory.id == ServiceGroup.category_id)
            .where(ServiceGroup.id == group_id)
        )).one_or_none()
        if not row or (row[0].deleted_at is not None and not include_retired):
            raise NotFoundException("ServiceGroup", str(group_id))
        group, category_name, category_active = row
        counts = (await self._sg_linked_counts([group.id])).get(str(group.id), {
            "services": 0, "active_services": 0, "providers": 0,
        })
        data = group.to_dict()
        data.update({
            "category_name": category_name,
            "category_active": bool(category_active),
            "deleted_at": group.deleted_at.isoformat() if group.deleted_at else None,
            "linked_counts": counts,
            "runtime_readiness": "category_inactive" if not category_active and group.deleted_at is None
                else self._sg_readiness(group, counts["services"]),
        })
        return data

    async def get_service_group_audit(self, group_id: uuid.UUID, limit: int = 50) -> dict:
        await self.get_service_group_enterprise(group_id, include_retired=True)
        return await self.list_master_data_audit("service_group", group_id, limit)

    async def activate_service_group(self, group_id: uuid.UUID) -> dict:
        g = await self._load_service_group(group_id)
        category = await self._load_category(g.category_id)
        if not category.is_active:
            raise ServiceOSException("SERVICE_CATEGORY_INACTIVE", "Activate the parent category before this service group.", status_code=422)
        old = g.to_dict()
        g.status = "active"
        await self.db.flush()
        await self._audit("service_group", g.id, "activate", old, g.to_dict(), f"Activated service group '{g.name}'")
        return g.to_dict()

    async def deactivate_service_group(self, group_id: uuid.UUID) -> dict:
        g = await self._load_service_group(group_id)
        old = g.to_dict()
        g.status = "inactive"
        await self.db.flush()
        await self._audit("service_group", g.id, "deactivate", old, g.to_dict(), f"Deactivated service group '{g.name}'")
        return g.to_dict()

    async def archive_service_group(self, group_id: uuid.UUID, reason: str) -> dict:
        reason = (reason or "").strip()
        if len(reason) < 10:
            raise ServiceOSException("RETIRE_REASON_REQUIRED", "A retirement reason of at least 10 characters is required.", status_code=422)
        g = await self._load_service_group(group_id)
        old = g.to_dict()
        svc_check = await self.db.execute(
            select(MasterService).where(
                MasterService.service_group_id == group_id,
                MasterService.deleted_at.is_(None),
            ).limit(1)
        )
        if svc_check.scalar_one_or_none():
            raise ServiceOSException(
                "SERVICE_GROUP_HAS_SERVICES",
                "Cannot archive a service group with active master services linked to it.",
                status_code=409,
            )
        g.status = "deleted"
        g.deleted_at = utcnow()
        await self.db.flush()
        await self._audit("service_group", g.id, "retire", old, g.to_dict(), reason)
        return {"archived": True, "group_id": str(group_id)}

    async def restore_service_group(self, group_id: uuid.UUID, reason: str) -> dict:
        reason = (reason or "").strip()
        if len(reason) < 10:
            raise ServiceOSException("RESTORE_REASON_REQUIRED", "A restore reason of at least 10 characters is required.", status_code=422)
        g = await self.db.get(ServiceGroup, group_id)
        if not g or g.deleted_at is None:
            raise NotFoundException("RetiredServiceGroup", str(group_id))
        old = g.to_dict()
        g.deleted_at = None
        g.status = "inactive"
        await self.db.flush()
        await self._audit("service_group", g.id, "restore", old, g.to_dict(), reason)
        return g.to_dict()

    async def bulk_service_group_status(self, ids: list[uuid.UUID], action: str, reason: str | None = None) -> dict:
        if not ids or len(ids) > 100:
            raise ServiceOSException("INVALID_BULK_SELECTION", "Select between 1 and 100 service groups.", status_code=422)
        if action not in {"activate", "deactivate"}:
            raise ServiceOSException("INVALID_BULK_ACTION", "Bulk action must be activate or deactivate.", status_code=422)
        updated, errors = [], []
        for group_id in ids:
            try:
                result = await (self.activate_service_group(group_id) if action == "activate" else self.deactivate_service_group(group_id))
                updated.append(result["id"])
            except (ServiceOSException, NotFoundException) as exc:
                errors.append({"id": str(group_id), "error": str(exc)})
        return {"action": action, "updated": updated, "updated_count": len(updated), "errors": errors}

    async def export_service_groups(
        self, category_id: uuid.UUID | None = None, status: str | None = None,
        retired: bool = False,
    ) -> list[dict]:
        data = await self.list_service_groups_enterprise(
            category_id=category_id, status=status, retired=retired, limit=100
        )
        rows = list(data["groups"])
        while len(rows) < data["total"] and len(rows) < 10000:
            page = await self.list_service_groups_enterprise(
                category_id=category_id, status=status, retired=retired,
                limit=100, offset=len(rows),
            )
            if not page["groups"]:
                break
            rows.extend(page["groups"])
        if data["total"] > 10000:
            raise ServiceOSException(
                "EXPORT_TOO_LARGE",
                "This export exceeds 10,000 rows. Narrow the filters before exporting.",
                status_code=422,
            )
        return rows

    # ═══════════════════════════════════════════════════════════
    # MASTER SERVICES — Enterprise (P0 Upgrade)
    # ═══════════════════════════════════════════════════════════

    async def _ms_linked_counts(self, service_ids: list[uuid.UUID]) -> dict[str, dict]:
        """Batch-count linked brands/options/issues/pricing/providers per master service."""
        if not service_ids:
            return {}

        # Brands
        brand_r = await self.db.execute(
            select(MasterServiceBrand.master_service_id, func.count().label("cnt"))
            .where(MasterServiceBrand.master_service_id.in_(service_ids),
                   MasterServiceBrand.is_active == True)
            .group_by(MasterServiceBrand.master_service_id)
        )
        brand_counts = {str(r[0]): r[1] for r in brand_r.all()}

        # Canonical service-option mappings.  MasterServiceOption is the
        # reusable option definition and its legacy master_service_id is not
        # authoritative for the live job-type blueprint.
        opt_r = await self.db.execute(
            select(ServiceOptionMapping.master_service_id, func.count().label("cnt"))
            .where(ServiceOptionMapping.master_service_id.in_(service_ids),
                   ServiceOptionMapping.status == "active",
                   ServiceOptionMapping.deleted_at.is_(None))
            .group_by(ServiceOptionMapping.master_service_id)
        )
        option_counts = {str(r[0]): r[1] for r in opt_r.all()}

        # Canonical problem/issue mappings for the same reason.
        issue_r = await self.db.execute(
            select(ServiceIssueMapping.master_service_id, func.count().label("cnt"))
            .where(ServiceIssueMapping.master_service_id.in_(service_ids),
                   ServiceIssueMapping.status == "active",
                   ServiceIssueMapping.deleted_at.is_(None))
            .group_by(ServiceIssueMapping.master_service_id)
        )
        issue_counts = {str(r[0]): r[1] for r in issue_r.all()}

        # Pricing rules
        pr_r = await self.db.execute(
            select(ServicePricingRule.master_service_id, func.count().label("cnt"))
            .where(ServicePricingRule.master_service_id.in_(service_ids),
                   ServicePricingRule.is_active == True,
                   ServicePricingRule.deleted_at.is_(None))
            .group_by(ServicePricingRule.master_service_id)
        )
        pricing_counts = {str(r[0]): r[1] for r in pr_r.all()}

        # Providers (TenantService)
        prov_r = await self.db.execute(
            select(TenantService.master_service_id, func.count().label("cnt"))
            .where(TenantService.master_service_id.in_(service_ids),
                   TenantService.is_enabled == True, TenantService.deleted_at.is_(None))
            .group_by(TenantService.master_service_id)
        )
        provider_counts = {str(r[0]): r[1] for r in prov_r.all()}

        # Service types (MasterServiceType) used as proxy for "types configured"
        stype_r = await self.db.execute(
            select(MasterServiceType.master_service_id, func.count().label("cnt"))
            .where(MasterServiceType.master_service_id.in_(service_ids),
                   MasterServiceType.is_active == True)
            .group_by(MasterServiceType.master_service_id)
        )
        stype_counts = {str(r[0]): r[1] for r in stype_r.all()}

        job_type_r = await self.db.execute(
            select(
                MasterServiceJobType.master_service_id,
                func.count(func.distinct(MasterServiceJobType.id)).label("cnt"),
            )
            .where(MasterServiceJobType.master_service_id.in_(service_ids),
                   MasterServiceJobType.is_active == True)
            .group_by(MasterServiceJobType.master_service_id)
        )
        job_type_counts = {str(r[0]): r[1] for r in job_type_r.all()}

        workflow_r = await self.db.execute(
            select(
                ServiceJobWorkflow.master_service_id,
                func.count(func.distinct(ServiceJobWorkflow.job_type_id)).label("cnt"),
            )
            .where(ServiceJobWorkflow.master_service_id.in_(service_ids),
                   ServiceJobWorkflow.is_current == True,
                   ServiceJobWorkflow.status == "published")
            .group_by(ServiceJobWorkflow.master_service_id)
        )
        workflow_counts = {str(r[0]): r[1] for r in workflow_r.all()}

        out: dict[str, dict] = {}
        for sid in [str(s) for s in service_ids]:
            out[sid] = {
                "brands":        brand_counts.get(sid, 0),
                "options":       option_counts.get(sid, 0),
                "issues":        issue_counts.get(sid, 0),
                "pricing_rules": pricing_counts.get(sid, 0),
                "providers":     provider_counts.get(sid, 0),
                "service_types": stype_counts.get(sid, 0),
                "job_types":     job_type_counts.get(sid, 0),
                "workflows":     workflow_counts.get(sid, 0),
                "checklists":    0,  # No master-level checklist count yet
            }
        return out

    def _ms_pricing_readiness(self, svc: MasterService, pricing_rules: int) -> str:
        if not svc.is_active:
            return "inactive"
        if pricing_rules > 0:
            return "ready"
        if svc.base_price and float(svc.base_price) > 0:
            return "fallback_only"
        return "missing_rules"

    def _ms_runtime_readiness(self, svc: MasterService, counts: dict) -> str:
        if not svc.is_active:
            return "inactive"
        if counts.get("job_types", 0) == 0:
            return "missing_job_types"
        if counts.get("workflows", 0) < counts.get("job_types", 0):
            return "missing_workflows"
        if svc.is_brand_required and counts.get("brands", 0) == 0:
            return "missing_brand_mapping"
        if svc.is_type_required and counts.get("service_types", 0) == 0:
            return "missing_service_options"
        if getattr(svc, "requires_issue_type", False) and counts.get("issues", 0) == 0:
            return "missing_issue_types"
        return "ready"

    async def get_master_services_summary(self) -> dict:
        live = MasterService.deleted_at.is_(None)
        aggregate = (await self.db.execute(select(
            func.count().filter(live).label("total"),
            func.count().filter(and_(live, MasterService.is_active == True)).label("active"),
            func.count().filter(and_(live, MasterService.is_active == False)).label("inactive"),
            func.count().filter(MasterService.deleted_at.isnot(None)).label("retired"),
        ).select_from(MasterService))).one()
        pricing_exists = exists().where(
            ServicePricingRule.master_service_id == MasterService.id,
            ServicePricingRule.is_active == True,
            ServicePricingRule.deleted_at.is_(None),
        )
        provider_exists = exists().where(
            TenantService.master_service_id == MasterService.id,
            TenantService.is_enabled == True,
            TenantService.deleted_at.is_(None),
        )
        pricing_ready = int(await self.db.scalar(
            select(func.count()).select_from(MasterService).where(live, pricing_exists)
        ) or 0)
        provider_enabled = int(await self.db.scalar(
            select(func.count()).select_from(MasterService).where(live, provider_exists)
        ) or 0)
        job_type_exists = exists().where(
            MasterServiceJobType.master_service_id == MasterService.id,
            MasterServiceJobType.is_active == True,
        )
        missing_workflow_exists = exists().where(
            MasterServiceJobType.master_service_id == MasterService.id,
            MasterServiceJobType.is_active == True,
            ~exists().where(
                ServiceJobWorkflow.master_service_id == MasterServiceJobType.master_service_id,
                ServiceJobWorkflow.job_type_id == MasterServiceJobType.job_type_id,
                ServiceJobWorkflow.is_current == True,
                ServiceJobWorkflow.status == "published",
            ),
        )
        blueprint_ready = int(await self.db.scalar(
            select(func.count()).select_from(MasterService)
            .join(ServiceCategory, ServiceCategory.id == MasterService.category_id)
            .join(ServiceGroup, ServiceGroup.id == MasterService.service_group_id)
            .where(
                live, MasterService.is_active == True,
                ServiceCategory.is_active == True,
                ServiceGroup.status == "active", ServiceGroup.deleted_at.is_(None),
                job_type_exists, ~missing_workflow_exists,
            )
        ) or 0)
        type_rows = (await self.db.execute(
            select(MasterService.job_type, func.count()).where(live)
            .group_by(MasterService.job_type)
        )).all()
        by_type = {str(job_type): int(count) for job_type, count in type_rows if job_type}
        total = int(aggregate.total or 0)
        return {
            "total": total, "active": int(aggregate.active or 0),
            "inactive": int(aggregate.inactive or 0), "retired": int(aggregate.retired or 0),
            "by_job_type": by_type,
            "pricing_ready": pricing_ready,
            "missing_pricing": total - pricing_ready,
            "provider_enabled": provider_enabled,
            "blueprint_ready": blueprint_ready,
            "blueprint_attention": total - blueprint_ready,
        }

    async def list_master_services_enterprise(
        self,
        q: str | None = None,
        category_id: uuid.UUID | None = None,
        service_group_id: uuid.UUID | None = None,
        job_type: str | None = None,
        pricing_model: str | None = None,
        is_active: bool | None = None,
        retired: bool = False,
        readiness: str | None = None,
        has_providers: bool | None = None,
        sort_by: str = "display_order",
        sort_dir: str = "asc",
        limit: int = 100,
        offset: int = 0,
    ) -> dict:
        stmt = (
            select(MasterService, ServiceCategory.name, ServiceCategory.is_active,
                   ServiceGroup.name, ServiceGroup.status, ServiceGroup.deleted_at)
            .outerjoin(ServiceCategory, ServiceCategory.id == MasterService.category_id)
            .outerjoin(ServiceGroup, ServiceGroup.id == MasterService.service_group_id)
            .where(MasterService.deleted_at.isnot(None) if retired else MasterService.deleted_at.is_(None))
        )
        if category_id:
            stmt = stmt.where(MasterService.category_id == category_id)
        if service_group_id:
            stmt = stmt.where(MasterService.service_group_id == service_group_id)
        if job_type:
            stmt = stmt.where(MasterService.job_type == job_type)
        if pricing_model:
            stmt = stmt.where(MasterService.pricing_model == pricing_model)
        if is_active is not None:
            stmt = stmt.where(MasterService.is_active == is_active)
        provider_exists = exists().where(
            TenantService.master_service_id == MasterService.id,
            TenantService.is_enabled == True,
            TenantService.deleted_at.is_(None),
        )
        if has_providers is not None:
            stmt = stmt.where(provider_exists if has_providers else ~provider_exists)
        job_type_exists = exists().where(
            MasterServiceJobType.master_service_id == MasterService.id,
            MasterServiceJobType.is_active == True,
        )
        workflow_exists = exists().where(
            ServiceJobWorkflow.master_service_id == MasterService.id,
            ServiceJobWorkflow.is_current == True,
            ServiceJobWorkflow.status == "published",
        )
        missing_workflow_exists = exists().where(
            MasterServiceJobType.master_service_id == MasterService.id,
            MasterServiceJobType.is_active == True,
            ~exists().where(
                ServiceJobWorkflow.master_service_id == MasterServiceJobType.master_service_id,
                ServiceJobWorkflow.job_type_id == MasterServiceJobType.job_type_id,
                ServiceJobWorkflow.is_current == True,
                ServiceJobWorkflow.status == "published",
            ),
        )
        if readiness == "ready":
            stmt = stmt.where(
                MasterService.is_active == True,
                ServiceCategory.is_active == True,
                ServiceGroup.status == "active",
                ServiceGroup.deleted_at.is_(None),
                job_type_exists,
                workflow_exists, ~missing_workflow_exists,
            )
        elif readiness == "inactive":
            stmt = stmt.where(MasterService.is_active == False)
        elif readiness == "missing_job_types":
            stmt = stmt.where(MasterService.is_active == True, ~job_type_exists)
        elif readiness == "missing_workflows":
            stmt = stmt.where(MasterService.is_active == True, job_type_exists, missing_workflow_exists)
        elif readiness == "category_inactive":
            stmt = stmt.where(ServiceCategory.is_active == False)
        elif readiness == "group_unavailable":
            stmt = stmt.where(or_(ServiceGroup.status != "active", ServiceGroup.deleted_at.isnot(None)))
        if q:
            like = f"%{q.lower()}%"
            stmt = stmt.where(
                func.lower(MasterService.service_name).like(like) |
                func.lower(MasterService.slug).like(like)
            )
        total = int(await self.db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0)
        sort_columns = {
            "name": MasterService.service_name,
            "category_name": ServiceCategory.name,
            "group_name": ServiceGroup.name,
            "job_type": MasterService.job_type,
            "pricing_model": MasterService.pricing_model,
            "status": MasterService.is_active,
            "display_order": MasterService.display_order,
            "created_at": MasterService.created_at,
            "updated_at": MasterService.updated_at,
            "deleted_at": MasterService.deleted_at,
        }
        sort_column = sort_columns.get(sort_by, MasterService.display_order)
        direction = sort_column.desc() if sort_dir.lower() == "desc" else sort_column.asc()
        stmt = stmt.order_by(direction.nulls_last(), MasterService.service_name.asc(), MasterService.id.asc()).limit(limit).offset(offset)
        result = await self.db.execute(stmt)
        rows = result.all()
        svcs = [row[0] for row in rows]
        service_ids = [s.id for s in svcs]
        counts_map = await self._ms_linked_counts(service_ids)

        out = []
        for s, category_name, category_active, group_name, group_status, group_deleted_at in rows:
            d = self._svc_dict(s)
            sid = str(s.id)
            lc = counts_map.get(sid, {})
            d["id"] = sid
            d["category_name"] = category_name or "Missing category"
            d["category_active"] = bool(category_active)
            d["group_name"] = group_name
            d["group_status"] = group_status
            d["group_retired"] = group_deleted_at is not None
            d["linked_counts"] = lc
            d["pricing_readiness"] = self._ms_pricing_readiness(s, lc.get("pricing_rules", 0))
            d["runtime_readiness"] = self._ms_runtime_readiness(s, lc)
            if not category_active:
                d["runtime_readiness"] = "category_inactive"
            elif s.service_group_id and (group_deleted_at is not None or group_status != "active"):
                d["runtime_readiness"] = "group_unavailable"
            out.append(d)
        return {"services": out, "total": total, "limit": limit, "offset": offset}

    async def get_master_service_enterprise(self, service_id: uuid.UUID, include_retired: bool = False) -> dict:
        svc = await self._load_master_service_any(service_id)
        if svc.deleted_at and not include_retired:
            raise NotFoundException("MasterService", str(service_id))
        category = await self.db.get(ServiceCategory, svc.category_id)
        group = await self.db.get(ServiceGroup, svc.service_group_id) if svc.service_group_id else None
        counts = (await self._ms_linked_counts([svc.id])).get(str(svc.id), {})
        row = self._svc_dict(svc)
        row.update({
            "id": str(svc.id), "category_name": category.name if category else "Unknown",
            "category_active": bool(category and category.is_active),
            "group_name": group.name if group else None,
            "group_status": group.status if group else None,
            "group_retired": bool(group and group.deleted_at), "linked_counts": counts,
            "pricing_readiness": self._ms_pricing_readiness(svc, counts.get("pricing_rules", 0)),
            "runtime_readiness": self._ms_runtime_readiness(svc, counts),
        })
        if not category or not category.is_active:
            row["runtime_readiness"] = "category_inactive"
        elif svc.service_group_id and (not group or group.deleted_at is not None or group.status != "active"):
            row["runtime_readiness"] = "group_unavailable"
        return row

    async def get_master_service_audit(self, service_id: uuid.UUID, limit: int = 100) -> dict:
        await self._load_master_service_any(service_id)
        return await self.list_master_data_audit("master_service", service_id, limit)

    async def activate_master_service(self, service_id: uuid.UUID) -> dict:
        svc = await self._load_master_service(service_id)
        category = await self._load_category(svc.category_id)
        if not category.is_active:
            raise ServiceOSException("SERVICE_CATEGORY_INACTIVE", "Activate the parent category first.", status_code=409)
        if not svc.service_group_id:
            raise ServiceOSException("SERVICE_GROUP_REQUIRED", "Assign an active service group before activation.", status_code=409)
        group = await self._load_service_group(svc.service_group_id)
        if group.status != "active":
            raise ServiceOSException("SERVICE_GROUP_INACTIVE", "Activate the parent service group first.", status_code=409)
        old = self._svc_dict(svc)
        svc.is_active = True
        await self.db.flush()
        result = self._svc_dict(svc)
        await self._audit("master_service", svc.id, "activate", old, result,
                          f"Activated master service '{svc.service_name}'")
        return result

    async def deactivate_master_service(self, service_id: uuid.UUID) -> dict:
        svc = await self._load_master_service(service_id)
        old = self._svc_dict(svc)
        svc.is_active = False
        await self.db.flush()
        result = self._svc_dict(svc)
        await self._audit("master_service", svc.id, "deactivate", old, result,
                          f"Deactivated master service '{svc.service_name}'")
        return result

    async def archive_master_service(self, service_id: uuid.UUID, reason: str) -> dict:
        if len((reason or "").strip()) < 10:
            raise ServiceOSException("RETIRE_REASON_REQUIRED", "A retirement reason of at least 10 characters is required.", status_code=422)
        svc = await self._load_master_service(service_id)
        enabled = int(await self.db.scalar(select(func.count()).select_from(TenantService).where(
            TenantService.master_service_id == service_id,
            TenantService.deleted_at.is_(None), TenantService.is_enabled == True,
        )) or 0)
        if enabled:
            raise ServiceOSException(
                "MASTER_SERVICE_IN_USE",
                f"This service is enabled by {enabled} provider workspace(s). Deactivate it and migrate providers before retiring it.",
                status_code=409,
            )
        old = self._svc_dict(svc)
        svc.is_active = False
        svc.deleted_at = utcnow()
        await self.db.flush()
        await self._audit("master_service", svc.id, "retire", old, self._svc_dict(svc), reason.strip())
        return {"archived": True, "service_id": str(service_id)}

    async def restore_master_service(self, service_id: uuid.UUID, reason: str) -> dict:
        if len((reason or "").strip()) < 10:
            raise ServiceOSException("RESTORE_REASON_REQUIRED", "A restore reason of at least 10 characters is required.", status_code=422)
        svc = await self._load_master_service_any(service_id)
        if svc.deleted_at is None:
            raise ServiceOSException("MASTER_SERVICE_NOT_RETIRED", "This master service is not retired.", status_code=409)
        old = self._svc_dict(svc)
        svc.deleted_at = None
        svc.is_active = False
        await self.db.flush()
        result = self._svc_dict(svc)
        await self._audit("master_service", svc.id, "restore", old, result, reason.strip())
        return result

    async def bulk_master_service_status(self, ids: list[uuid.UUID], action: str) -> dict:
        if not ids:
            raise ServiceOSException("NO_SERVICES_SELECTED", "Select at least one master service.", status_code=422)
        if len(ids) > 100:
            raise ServiceOSException("BULK_LIMIT_EXCEEDED", "At most 100 services can be changed at once.", status_code=422)
        if action not in {"activate", "deactivate"}:
            raise ServiceOSException("INVALID_BULK_ACTION", "Bulk action must be activate or deactivate.", status_code=422)
        updated, errors = [], []
        for service_id in ids:
            try:
                result = await (self.activate_master_service(service_id) if action == "activate" else self.deactivate_master_service(service_id))
                updated.append(result["service_id"])
            except (ServiceOSException, NotFoundException) as exc:
                errors.append({"id": str(service_id), "error": str(exc)})
        return {"action": action, "updated": updated, "updated_count": len(updated), "errors": errors}

    async def export_master_services(
        self, category_id: uuid.UUID | None = None,
        service_group_id: uuid.UUID | None = None,
        job_type: str | None = None,
        is_active: bool | None = None,
        retired: bool = False,
    ) -> list[dict]:
        data = await self.list_master_services_enterprise(
            category_id=category_id, service_group_id=service_group_id,
            job_type=job_type, is_active=is_active, retired=retired, limit=100,
        )
        rows = list(data["services"])
        while len(rows) < data["total"] and len(rows) < 10000:
            page = await self.list_master_services_enterprise(
                category_id=category_id, service_group_id=service_group_id,
                job_type=job_type, is_active=is_active, retired=retired,
                limit=100, offset=len(rows),
            )
            if not page["services"]:
                break
            rows.extend(page["services"])
        if data["total"] > 10000:
            raise ServiceOSException("EXPORT_TOO_LARGE", "This export exceeds 10,000 rows. Narrow the filters before exporting.", status_code=422)
        return rows
