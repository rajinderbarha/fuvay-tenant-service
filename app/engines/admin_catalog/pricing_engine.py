"""Admin Catalog — Pricing Engine.

resolve_service_price() is the single source of truth for price resolution.
It is called by: booking preflight, tenant catalog preview, admin pricing preview.

Priority (highest → lowest):
  1. zipcode + service + type + brand
  2. zipcode + service + type
  3. zipcode + service + brand
  4. zipcode + service
  5. city   + service + type + brand
  6. city   + service + type
  7. city   + service + brand
  8. city   + service
  9. tier   + service + type + brand
 10. tier   + service + type
 11. tier   + service + brand
 12. tier   + service
 13. global service base price (MasterService defaults)
"""
from __future__ import annotations
import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.admin_catalog.models import (
    MasterService, ServicePricingRule, PricingTier, TierLocation,
    ServiceType, Brand,
)
from app.exceptions import ServiceOSException, NotFoundException

utcnow = lambda: datetime.now(timezone.utc)


async def resolve_service_price(
    db: AsyncSession,
    master_service_id: uuid.UUID,
    job_type: str | None = None,
    city: str | None = None,
    zipcode: str | None = None,
    state: str | None = None,
    country: str | None = None,
    service_type_id: uuid.UUID | None = None,
    brand_id: uuid.UUID | None = None,
    tenant_id: uuid.UUID | None = None,
) -> dict:
    """Resolve the most-specific active pricing rule for given inputs.
    Falls back to master service base price when no rule matches.
    Returns a full pricing breakdown dict."""

    now = utcnow()

    # 1. Load and validate master service
    svc_res = await db.execute(
        select(MasterService).where(MasterService.id == master_service_id, MasterService.deleted_at.is_(None)))
    svc = svc_res.scalar_one_or_none()
    if not svc:
        raise NotFoundException("MasterService", str(master_service_id))
    if not svc.is_active:
        raise ServiceOSException("MASTER_SERVICE_INACTIVE", "Service is not active.", status_code=422)

    # 2. Validate job_type matches service (if provided)
    effective_job_type = job_type or svc.job_type
    if effective_job_type != svc.job_type:
        raise ServiceOSException("INVALID_JOB_TYPE",
            f"job_type '{effective_job_type}' does not match service job_type '{svc.job_type}'.", status_code=422)

    # 3. Validate required type/brand
    if svc.is_type_required and not service_type_id:
        raise ServiceOSException("SERVICE_TYPE_REQUIRED", "This service requires a service type selection.", status_code=422)
    if svc.is_brand_required and not brand_id:
        raise ServiceOSException("BRAND_REQUIRED", "This service requires a brand selection.", status_code=422)

    # 4. Resolve tier from city / zipcode
    tier_id: uuid.UUID | None = None
    tier_info: dict | None = None
    tier_match_level: str | None = None

    city_norm  = (city or "").strip().lower() or None
    zip_norm   = (zipcode or "").strip() or None

    if zip_norm:
        loc_res = await db.execute(
            select(TierLocation).where(
                TierLocation.zipcode == zip_norm,
                TierLocation.is_active == True,
                TierLocation.deleted_at.is_(None),
            ).order_by(TierLocation.priority.desc()).limit(1))
        loc = loc_res.scalar_one_or_none()
        if loc:
            t_res = await db.execute(
                select(PricingTier).where(PricingTier.id == loc.tier_id, PricingTier.is_active == True))
            t = t_res.scalar_one_or_none()
            if t:
                tier_id = t.id
                tier_match_level = "zipcode"
                tier_info = {"tier_id": str(t.id), "name": t.name, "code": t.code,
                             "match_level": "zipcode", "multiplier": float(t.base_multiplier)}

    if not tier_id and city_norm:
        loc_res = await db.execute(
            select(TierLocation).where(
                TierLocation.city == city_norm,
                TierLocation.zipcode.is_(None),
                TierLocation.is_active == True,
                TierLocation.deleted_at.is_(None),
            ).order_by(TierLocation.priority.desc()).limit(1))
        loc = loc_res.scalar_one_or_none()
        if loc:
            t_res = await db.execute(
                select(PricingTier).where(PricingTier.id == loc.tier_id, PricingTier.is_active == True))
            t = t_res.scalar_one_or_none()
            if t:
                tier_id = t.id
                tier_match_level = "city"
                tier_info = {"tier_id": str(t.id), "name": t.name, "code": t.code,
                             "match_level": "city", "multiplier": float(t.base_multiplier)}

    # 5. Build rule candidates in priority order
    #    Each candidate = (conditions_dict, specificity_score)
    #    Higher score = more specific.
    candidates = _build_rule_candidates(
        master_service_id, effective_job_type, tier_id, zip_norm, city_norm,
        service_type_id, brand_id)

    resolution_path: list[str] = []
    if tier_match_level:
        resolution_path.append(f"Resolved location tier via {tier_match_level} match: '{tier_info['name']}'.")
    elif zip_norm or city_norm:
        resolution_path.append("No tier matched for the given location.")

    # 6. Find most-specific active non-expired rule
    matched_rule: ServicePricingRule | None = None
    warnings: list[str] = []
    for level, cond_filters in candidates:
        stmt = select(ServicePricingRule).where(
            ServicePricingRule.master_service_id == master_service_id,
            ServicePricingRule.is_active == True,
            ServicePricingRule.deleted_at.is_(None),
            or_(ServicePricingRule.effective_from.is_(None), ServicePricingRule.effective_from <= now),
            or_(ServicePricingRule.effective_to.is_(None), ServicePricingRule.effective_to >= now),
            *cond_filters,
        ).order_by(ServicePricingRule.priority.desc()).limit(1)
        res = await db.execute(stmt)
        rule = res.scalar_one_or_none()
        if rule:
            matched_rule = rule
            resolution_path.append(f"Matched rule at specificity level '{level}' (priority {rule.priority}).")
            break

    if matched_rule:
        if matched_rule.tier_id:
            t_res = await db.execute(select(PricingTier).where(PricingTier.id == matched_rule.tier_id))
            t_obj = t_res.scalar_one_or_none()
            if not t_obj or not t_obj.is_active:
                warnings.append("Matched rule references a tier that is inactive or missing.")
        if matched_rule.effective_to and matched_rule.effective_to < now:
            warnings.append("Matched rule is past its effective_to date but is still marked active.")
    else:
        resolution_path.append("No pricing rule matched — using master service default price.")

    # 7. Resolve type / brand names for response
    type_name: str | None = None
    brand_name: str | None = None
    if service_type_id:
        t_res = await db.execute(select(ServiceType).where(ServiceType.id == service_type_id))
        t_obj = t_res.scalar_one_or_none()
        type_name = t_obj.name if t_obj else None
    if brand_id:
        b_res = await db.execute(select(Brand).where(Brand.id == brand_id))
        b_obj = b_res.scalar_one_or_none()
        brand_name = b_obj.name if b_obj else None

    # 8. Build response
    if matched_rule:
        base_price    = float(matched_rule.base_price)
        visit_fee     = float(matched_rule.visit_fee)
        min_price     = float(matched_rule.min_price) if matched_rule.min_price else None
        max_price     = float(matched_rule.max_price) if matched_rule.max_price else None
        comm_pct      = float(matched_rule.commission_percent)
        platform_pct  = float(matched_rule.platform_fee_percent)
        tax_pct       = float(matched_rule.tax_percent)
        pricing_model = matched_rule.pricing_model
        source        = "pricing_rule"
        matched_rule_id = str(matched_rule.id)
        matched_rule_name = matched_rule.rule_name or matched_rule.rule_code or f"Rule for {svc.service_name}"
        bargain_floor = float(matched_rule.bargain_floor) if matched_rule.bargain_floor is not None else None
        completed_job_deduction_credits = matched_rule.completed_job_deduction_credits
    else:
        base_price    = float(svc.base_price)
        visit_fee     = float(svc.visit_fee)
        min_price     = float(svc.min_price) if svc.min_price else None
        max_price     = float(svc.max_price) if svc.max_price else None
        comm_pct      = 0.0
        platform_pct  = 0.0
        tax_pct       = 0.0
        pricing_model = svc.pricing_model
        source        = "master_service_default"
        matched_rule_id = None
        matched_rule_name = None
        bargain_floor = None
        completed_job_deduction_credits = 0

    customer_estimate = _compute_customer_estimate(
        pricing_model, base_price, visit_fee, min_price)
    message = _price_message(pricing_model, customer_estimate, visit_fee)

    return {
        "master_service_id": str(svc.id),
        "service_name": svc.service_name,
        "job_type": svc.job_type,
        "pricing_model": pricing_model,
        "tier": tier_info,
        "selected_type": type_name,
        "selected_brand": brand_name,
        "matched_rule_id": matched_rule_id,
        "matched_rule_name": matched_rule_name,
        "source": source,
        "base_price": base_price,
        "visit_fee": visit_fee,
        "min_price": min_price,
        "max_price": max_price,
        "platform_fee_percent": platform_pct,
        "commission_percent": comm_pct,
        "tax_percent": tax_pct,
        "bargain_floor": bargain_floor,
        "completed_job_deduction_credits": completed_job_deduction_credits,
        "payment_collection_mode": "customer_pays_provider_directly",
        "final_customer_estimate": customer_estimate,
        "message": message,
        "tier_matched": {"matched_by": tier_match_level, "tier": tier_info},
        "resolution_path": resolution_path,
        "warnings": warnings,
    }


def _build_rule_candidates(
    service_id: uuid.UUID, job_type: str,
    tier_id: uuid.UUID | None, zipcode: str | None, city: str | None,
    type_id: uuid.UUID | None, brand_id: uuid.UUID | None,
) -> list[tuple[str, list]]:
    """Return (level_label, filter_conditions) tuples from most-specific to least-specific."""
    def _zip_cond():    return ServicePricingRule.zipcode == zipcode
    def _city_cond():   return ServicePricingRule.city == city
    def _tier_cond():   return ServicePricingRule.tier_id == tier_id
    def _type_cond():   return ServicePricingRule.service_type_id == type_id
    def _brand_cond():  return ServicePricingRule.brand_id == brand_id
    def _no_zip():      return ServicePricingRule.zipcode.is_(None)
    def _no_city():     return ServicePricingRule.city.is_(None)
    def _no_tier():     return ServicePricingRule.tier_id.is_(None)
    def _no_type():     return ServicePricingRule.service_type_id.is_(None)
    def _no_brand():    return ServicePricingRule.brand_id.is_(None)

    jt = ServicePricingRule.job_type == job_type
    candidates: list[tuple[str, list]] = []

    if zipcode:
        if type_id and brand_id:
            candidates.append(("zipcode+type+brand", [jt, _zip_cond(), _type_cond(), _brand_cond()]))
        if type_id:
            candidates.append(("zipcode+type", [jt, _zip_cond(), _type_cond(), _no_brand()]))
        if brand_id:
            candidates.append(("zipcode+brand", [jt, _zip_cond(), _no_type(), _brand_cond()]))
        candidates.append(("zipcode", [jt, _zip_cond(), _no_type(), _no_brand()]))

    if city:
        if type_id and brand_id:
            candidates.append(("city+type+brand", [jt, _no_zip(), _city_cond(), _type_cond(), _brand_cond()]))
        if type_id:
            candidates.append(("city+type", [jt, _no_zip(), _city_cond(), _type_cond(), _no_brand()]))
        if brand_id:
            candidates.append(("city+brand", [jt, _no_zip(), _city_cond(), _no_type(), _brand_cond()]))
        candidates.append(("city", [jt, _no_zip(), _city_cond(), _no_type(), _no_brand()]))

    if tier_id:
        if type_id and brand_id:
            candidates.append(("tier+type+brand", [jt, _no_zip(), _no_city(), _tier_cond(), _type_cond(), _brand_cond()]))
        if type_id:
            candidates.append(("tier+type", [jt, _no_zip(), _no_city(), _tier_cond(), _type_cond(), _no_brand()]))
        if brand_id:
            candidates.append(("tier+brand", [jt, _no_zip(), _no_city(), _tier_cond(), _no_type(), _brand_cond()]))
        candidates.append(("tier", [jt, _no_zip(), _no_city(), _tier_cond(), _no_type(), _no_brand()]))

    # Global rule (no location / tier constraints)
    candidates.append(("global", [jt, _no_zip(), _no_city(), _no_tier(), _no_type(), _no_brand()]))

    return candidates


def _compute_customer_estimate(
    pricing_model: str, base_price: float, visit_fee: float, min_price: float | None,
) -> float:
    if pricing_model == "post_assessment":
        return visit_fee  # Customer pays visit fee; repair quote follows
    if pricing_model == "range":
        return min_price if min_price is not None else base_price
    return base_price  # fixed / hourly


def _price_message(pricing_model: str, estimate: float, visit_fee: float) -> str:
    if pricing_model == "post_assessment":
        return f"Visit fee ₹{estimate:.0f} is fixed. Final repair quote will be provided after assessment."
    if pricing_model == "range":
        return f"Starting from ₹{estimate:.0f}. Final price depends on scope of work."
    if pricing_model == "hourly":
        return f"₹{estimate:.0f} per hour. Billed on actual time spent."
    return f"Fixed price ₹{estimate:.0f}."
