"""Sprint 18 Hardening — Idempotent seeds for Real Estate category, offerings, and routing rules."""
from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

# ── Seed data ─────────────────────────────────────────────────────────────────

_CATEGORY_DATA: dict = {
    "name":                    "Real Estate",
    "slug":                    "real-estate",
    "category_type":           "marketplace",
    "primary_engine_key":      "real_estate_lead",
    "customer_flow_type":      "chatbot_lead",
    "provider_dashboard_type": "real_estate",
    "is_customer_visible":     True,
    "is_provider_registerable": True,
    "monetization_model":      "lead_fee",
    "is_active":               True,
}

_OFFERINGS_DATA: list[dict] = [
    {
        "name":                  "Buy Property Inquiry",
        "slug":                  "buy-property-inquiry",
        "offering_class":        "lead",
        "customer_flow_type":    "chatbot_lead",
        "primary_engine_key":    "real_estate_lead",
        "default_pricing_model": "lead_fee",
        "default_base_price":    Decimal("0"),
        "default_visit_fee":     Decimal("0"),
        "default_appointment_fee": Decimal("0"),
        "default_lead_fee":      Decimal("500"),
        "currency":              "INR",
        "is_active":             True,
        "display_order":         1,
        "status":                "active",
    },
    {
        "name":                  "Site Visit Request",
        "slug":                  "site-visit-request",
        "offering_class":        "lead",
        "customer_flow_type":    "chatbot_lead",
        "primary_engine_key":    "real_estate_lead",
        "default_pricing_model": "lead_fee",
        "default_base_price":    Decimal("0"),
        "default_visit_fee":     Decimal("0"),
        "default_appointment_fee": Decimal("0"),
        "default_lead_fee":      Decimal("300"),
        "currency":              "INR",
        "is_active":             True,
        "display_order":         2,
        "status":                "active",
        # Site visit preferred_date/time scheduling against agent availability
        # is NOT validated in Sprint 18. TODO: Sprint 19+ must add agent
        # calendar check before confirming a real site visit booking.
    },
]

_ROUTING_RULES_DATA: list[dict] = [
    {
        "rule_key":                  "city_buy_default",
        "rule_name":                 "City-level Buy Intent Default",
        "lead_intent":               "buy",
        "match_scope":               "city",
        "priority":                  10,
        "require_agent_available":   False,
        "require_provider_bookable": True,
        "require_subscription_active": True,
        "require_lead_credit":       False,
        "max_providers":             5,
        "is_active":                 True,
    },
    {
        "rule_key":                  "city_rent_default",
        "rule_name":                 "City-level Rent Intent Default",
        "lead_intent":               "rent",
        "match_scope":               "city",
        "priority":                  10,
        "require_agent_available":   False,
        "require_provider_bookable": True,
        "require_subscription_active": True,
        "require_lead_credit":       False,
        "max_providers":             5,
        "is_active":                 True,
    },
    {
        "rule_key":                  "locality_buy_exact",
        "rule_name":                 "Locality Exact Match — Buy",
        "lead_intent":               "buy",
        "match_scope":               "locality",
        "priority":                  20,
        "require_agent_available":   False,
        "require_provider_bookable": True,
        "require_subscription_active": True,
        "require_lead_credit":       False,
        "max_providers":             3,
        "is_active":                 True,
    },
    {
        "rule_key":                  "site_visit_agent_required",
        "rule_name":                 "Site Visit — Agent Availability Required",
        "lead_intent":               "site_visit",
        "match_scope":               "city",
        "priority":                  30,
        "require_agent_available":   True,
        "require_provider_bookable": True,
        "require_subscription_active": True,
        "require_lead_credit":       True,
        "max_providers":             1,
        "is_active":                 True,
    },
]


# ── Seed functions ─────────────────────────────────────────────────────────────

async def seed_real_estate_category(db: AsyncSession) -> dict:
    """Idempotent upsert of the Real Estate ServiceCategory by slug='real-estate'."""
    from app.engines.admin_catalog.models import ServiceCategory

    q = select(ServiceCategory).where(ServiceCategory.slug == "real-estate")
    existing = (await db.execute(q)).scalars().first()

    if existing:
        for k, v in _CATEGORY_DATA.items():
            if k != "slug" and getattr(existing, k, None) != v:
                setattr(existing, k, v)
        await db.flush()
        return {"action": "updated", "category_id": str(existing.id)}

    cat = ServiceCategory(**_CATEGORY_DATA)
    db.add(cat)
    await db.flush()
    await db.refresh(cat)
    return {"action": "created", "category_id": str(cat.id)}


async def seed_real_estate_offerings(db: AsyncSession, category_id: uuid.UUID) -> list[dict]:
    """Idempotent upsert of MasterOfferings for Real Estate by slug."""
    from app.engines.admin_catalog.models import MasterOffering

    results: list[dict] = []
    for data in _OFFERINGS_DATA:
        q = select(MasterOffering).where(MasterOffering.slug == data["slug"])
        existing = (await db.execute(q)).scalars().first()

        if existing:
            for k, v in data.items():
                if getattr(existing, k, None) != v:
                    setattr(existing, k, v)
            await db.flush()
            results.append({"action": "updated", "slug": data["slug"], "id": str(existing.id)})
        else:
            offering = MasterOffering(**data, category_id=category_id)
            db.add(offering)
            await db.flush()
            await db.refresh(offering)
            results.append({"action": "created", "slug": data["slug"], "id": str(offering.id)})

    return results


async def seed_real_estate_routing_rules(db: AsyncSession, category_id: uuid.UUID) -> list[dict]:
    """Idempotent upsert of routing rules keyed by (category_id, rule_key)."""
    from app.engines.real_estate_lead.models import RealEstateLeadRoutingRule

    results: list[dict] = []
    for data in _ROUTING_RULES_DATA:
        q = select(RealEstateLeadRoutingRule).where(
            and_(
                RealEstateLeadRoutingRule.category_id == category_id,
                RealEstateLeadRoutingRule.rule_key == data["rule_key"],
            )
        )
        existing = (await db.execute(q)).scalars().first()

        if existing:
            for k, v in data.items():
                if k != "rule_key" and getattr(existing, k, None) != v:
                    setattr(existing, k, v)
            await db.flush()
            results.append({"action": "updated", "rule_key": data["rule_key"], "id": str(existing.id)})
        else:
            rule = RealEstateLeadRoutingRule(**data, category_id=category_id)
            db.add(rule)
            await db.flush()
            await db.refresh(rule)
            results.append({"action": "created", "rule_key": data["rule_key"], "id": str(rule.id)})

    return results


async def run_all_seeds(db: AsyncSession) -> dict:
    """Run all Real Estate seeds idempotently and return a summary dict."""
    cat_result  = await seed_real_estate_category(db)
    category_id = uuid.UUID(cat_result["category_id"])

    offerings_result = await seed_real_estate_offerings(db, category_id)
    rules_result     = await seed_real_estate_routing_rules(db, category_id)

    return {
        "category":      cat_result,
        "offerings":     offerings_result,
        "routing_rules": rules_result,
    }
