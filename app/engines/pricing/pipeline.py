"""Pricing Engine — 5-step pipeline. Pure computation, no DB writes."""
from __future__ import annotations
from datetime import datetime, timezone
from decimal import Decimal

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.pricing.constants import (
    MIN_PRICE_INR, PipelineStep, RuleType,
    REDIS_CITY_TIER, REDIS_TENANT_PRICE, REDIS_BRAND_ADJ,
    REDIS_ZONE_CONFIG, REDIS_DYNAMIC_RULES,
)
from app.engines.pricing.models import (
    CityTierConfig, ServiceTypePrice, BrandAdjustment,
    ZoneSurcharge, DynamicPricingRule,
)

logger = structlog.get_logger("pricing.pipeline")
utcnow = lambda: datetime.now(timezone.utc)


async def compute_price(
    db: AsyncSession,
    tenant_id: str,
    service_type_id: str,
    service_category: str,
    city_name: str,
    pincode: str | None = None,
    requested_at: datetime | None = None,
) -> dict:
    """
    5-step pricing pipeline. Each step records its contribution.
    Returns full trace for PriceSnapshot storage.
    """
    at = requested_at or utcnow()
    trace = {}

    # ── Step 1: City tier floor ────────────────────────────────────────────
    floor_result = await db.execute(
        select(CityTierConfig).where(
            CityTierConfig.city_name == city_name,
            CityTierConfig.service_category == service_category,
            CityTierConfig.is_active == True,
        )
    )
    city_config = floor_result.scalar_one_or_none()
    floor_price = city_config.floor_price if city_config else MIN_PRICE_INR
    tier = city_config.tier if city_config else "tier_3"

    trace[PipelineStep.CITY_FLOOR] = {
        "tier": tier, "city": city_name,
        "floor_price": float(floor_price),
        "source": "city_config" if city_config else "platform_minimum",
    }
    running_price = floor_price

    # ── Step 2: Tenant service type price ─────────────────────────────────
    stp_result = await db.execute(
        select(ServiceTypePrice).where(
            ServiceTypePrice.tenant_id == tenant_id,
            ServiceTypePrice.service_type_id == service_type_id,
            ServiceTypePrice.valid_until == None,
        )
    )
    stp = stp_result.scalar_one_or_none()
    if stp and stp.base_price >= floor_price:
        tenant_price = stp.base_price
        source = "tenant_set"
    elif stp and stp.base_price < floor_price:
        tenant_price = floor_price  # enforce floor
        source = "floor_enforced"
    else:
        tenant_price = floor_price
        source = "default_floor"

    trace[PipelineStep.TENANT_PRICE] = {
        "tenant_price_set": float(stp.base_price) if stp else None,
        "applied_price": float(tenant_price),
        "floor_enforced": stp is not None and stp.base_price < floor_price,
        "source": source,
    }
    running_price = tenant_price

    # ── Step 3: Brand adjustment ──────────────────────────────────────────
    ba_result = await db.execute(
        select(BrandAdjustment).where(
            BrandAdjustment.tenant_id == tenant_id,
            BrandAdjustment.valid_until == None,
        )
    )
    brand_adj = ba_result.scalar_one_or_none()
    brand_pct = brand_adj.adjustment_pct if brand_adj else Decimal("0.00")
    brand_amount = (running_price * brand_pct / Decimal("100")).quantize(Decimal("0.01"))
    price_after_brand = running_price + brand_amount

    trace[PipelineStep.BRAND_ADJ] = {
        "adjustment_pct": float(brand_pct),
        "adjustment_amount": float(brand_amount),
        "label": brand_adj.label if brand_adj else None,
        "price_before": float(running_price),
        "price_after": float(price_after_brand),
    }
    running_price = price_after_brand

    # ── Step 4: Zone surcharge ─────────────────────────────────────────────
    zone_applied = None
    zone_amount = Decimal("0.00")
    if pincode:
        zones_result = await db.execute(
            select(ZoneSurcharge).where(
                ZoneSurcharge.tenant_id == tenant_id,
                ZoneSurcharge.is_active == True,
            )
        )
        zones = zones_result.scalars().all()
        for zone in zones:
            identifiers = zone.zone_identifiers or []
            if pincode in identifiers:
                zone_amount = (running_price * zone.surcharge_pct / Decimal("100")).quantize(Decimal("0.01"))
                zone_applied = zone
                break

    price_after_zone = running_price + zone_amount
    trace[PipelineStep.ZONE_SURCHARGE] = {
        "zone_matched": zone_applied.zone_name if zone_applied else None,
        "surcharge_pct": float(zone_applied.surcharge_pct) if zone_applied else 0.0,
        "surcharge_amount": float(zone_amount),
        "price_before": float(running_price),
        "price_after": float(price_after_zone),
    }
    running_price = price_after_zone

    # ── Step 5: Dynamic rules (first matching active rule wins) ────────────
    rules_result = await db.execute(
        select(DynamicPricingRule).where(
            DynamicPricingRule.tenant_id == tenant_id,
            DynamicPricingRule.is_active == True,
        ).order_by(DynamicPricingRule.priority)
    )
    rules = rules_result.scalars().all()
    matched_rule = None
    rule_amount = Decimal("0.00")

    for rule in rules:
        if _rule_matches(rule, at, service_type_id):
            rule_amount = (running_price * rule.adjustment_pct / Decimal("100")).quantize(Decimal("0.01"))
            matched_rule = rule
            break

    price_after_rule = running_price + rule_amount
    # Enforce platform minimum
    final_price = max(MIN_PRICE_INR, price_after_rule).quantize(Decimal("0.01"))

    trace[PipelineStep.DYNAMIC_RULE] = {
        "rule_matched": matched_rule.rule_name if matched_rule else None,
        "rule_type": matched_rule.rule_type if matched_rule else None,
        "adjustment_pct": float(matched_rule.adjustment_pct) if matched_rule else 0.0,
        "adjustment_amount": float(rule_amount),
        "price_before": float(running_price),
        "price_after": float(price_after_rule),
        "minimum_enforced": price_after_rule < MIN_PRICE_INR,
    }

    return {
        "final_price": final_price,
        "currency": "INR",
        "pipeline_inputs": {
            "tenant_id": str(tenant_id), "service_type_id": service_type_id,
            "service_category": service_category, "city_name": city_name,
            "pincode": pincode, "requested_at": at.isoformat(),
        },
        "step_city_floor":   trace[PipelineStep.CITY_FLOOR],
        "step_tenant_price": trace[PipelineStep.TENANT_PRICE],
        "step_brand_adj":    trace[PipelineStep.BRAND_ADJ],
        "step_zone_surge":   trace[PipelineStep.ZONE_SURCHARGE],
        "step_dynamic_rule": trace[PipelineStep.DYNAMIC_RULE],
        "steps_summary": {
            "1_city_floor":   float(floor_price),
            "2_tenant_price": float(tenant_price),
            "3_brand_adj":    float(price_after_brand),
            "4_zone_surge":   float(price_after_zone),
            "5_dynamic_rule": float(final_price),
        },
    }


def _rule_matches(rule: DynamicPricingRule, at: datetime, service_type_id: str) -> bool:
    """Check if a dynamic rule conditions match the current request."""
    applies_to = rule.applies_to or []
    if applies_to and service_type_id not in applies_to:
        return False

    conditions = rule.conditions or {}

    if rule.rule_type == RuleType.DAY_OF_WEEK:
        dow = at.strftime("%A").lower()
        return dow in conditions.get("days", [])

    if rule.rule_type == RuleType.TIME_OF_DAY:
        hour = at.hour
        start = conditions.get("start_hour", 0)
        end   = conditions.get("end_hour", 24)
        return start <= hour < end

    if rule.rule_type == RuleType.DATE_RANGE:
        try:
            start = datetime.fromisoformat(conditions["start_date"]).replace(tzinfo=timezone.utc)
            end   = datetime.fromisoformat(conditions["end_date"]).replace(tzinfo=timezone.utc)
            return start <= at <= end
        except Exception:
            return False

    if rule.rule_type == RuleType.FLAT_OVERRIDE:
        return True

    return False
