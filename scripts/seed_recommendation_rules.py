"""Sprint 34I — Seed default recommendation rules.

Seeds idempotently by `code`. Does not fail if referenced entity codes are missing.
Run: python scripts/seed_recommendation_rules.py
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from app.database import get_async_session
from app.engines.admin_catalog.models import RecommendationRule

RULES = [
    # ── Home Appliances / AC ──────────────────────────────────────────────────
    {
        "code": "ac_brand_recommendations",
        "name": "Recommend AC Brands for AC Services",
        "description": "Recommends top AC brands when AC Repair or Installation is selected",
        "rule_type": "brand",
        "scope": "vertical",
        "vertical_type": "home_services",
        "priority": 10,
        "status": "active",
        "condition_json": {
            "vertical_type": "home_services",
            "service_codes_any": ["ac_repair", "ac_installation", "ac_service"],
        },
        "recommendation_json": {
            "entity_type": "brand",
            "entity_codes": ["voltas", "blue_star", "daikin", "hitachi", "carrier",
                             "lloyd", "o_general", "samsung", "lg"],
            "apply_to": "selected_services",
            "require_active_mapping": True,
        },
        "explanation_template": "Recommended because {service_code} commonly uses Home Appliance brand defaults.",
    },
    {
        "code": "ac_option_recommendations",
        "name": "Recommend AC Service Options",
        "description": "Recommends common AC types when AC service is selected",
        "rule_type": "service_option",
        "scope": "vertical",
        "vertical_type": "home_services",
        "priority": 11,
        "status": "active",
        "condition_json": {
            "vertical_type": "home_services",
            "service_codes_any": ["ac_repair", "ac_installation", "ac_service"],
        },
        "recommendation_json": {
            "entity_type": "service_option",
            "entity_codes": ["split_ac", "window_ac", "inverter_ac", "cassette_ac"],
            "apply_to": "service",
            "mark_required": False,
        },
        "explanation_template": "Common AC types for this service.",
    },
    {
        "code": "ac_issue_recommendations",
        "name": "Recommend Common AC Issues",
        "description": "Recommends common customer-facing AC issues",
        "rule_type": "issue_type",
        "scope": "vertical",
        "vertical_type": "home_services",
        "priority": 12,
        "status": "active",
        "condition_json": {
            "vertical_type": "home_services",
            "service_codes_any": ["ac_repair", "ac_service"],
        },
        "recommendation_json": {
            "entity_type": "issue_type",
            "entity_codes": ["not_cooling", "water_leakage", "noise_issue", "gas_refill_needed"],
            "mark_common": True,
            "requires_photo_for": ["water_leakage"],
        },
        "explanation_template": "Common issues reported for AC services.",
    },
    {
        "code": "ac_document_recommendations",
        "name": "Recommend AC Provider Documents",
        "description": "Recommends required documents for AC service providers",
        "rule_type": "document_requirement",
        "scope": "vertical",
        "vertical_type": "home_services",
        "priority": 13,
        "status": "active",
        "condition_json": {
            "vertical_type": "home_services",
            "service_codes_any": ["ac_repair", "ac_installation", "ac_service"],
        },
        "recommendation_json": {
            "entity_type": "document_requirement",
            "entity_codes": ["business_registration", "owner_id_proof", "shop_photo", "technician_id_proof"],
            "is_required": True,
        },
        "explanation_template": "Standard compliance documents for AC service providers.",
    },
    {
        "code": "ac_checklist_recommendation",
        "name": "Recommend AC Repair Checklist",
        "description": "Recommends the standard AC repair checklist template",
        "rule_type": "checklist_template",
        "scope": "vertical",
        "vertical_type": "home_services",
        "priority": 14,
        "status": "active",
        "condition_json": {
            "vertical_type": "home_services",
            "service_codes_any": ["ac_repair", "ac_service"],
        },
        "recommendation_json": {
            "entity_type": "checklist_template",
            "entity_codes": ["ac_repair_checklist", "ac_service_checklist"],
        },
        "explanation_template": "Standard AC service quality checklist.",
    },

    # ── Plumbing ──────────────────────────────────────────────────────────────
    {
        "code": "plumbing_issue_recommendations",
        "name": "Recommend Common Plumbing Issues",
        "description": "Recommends common plumbing customer issues",
        "rule_type": "issue_type",
        "scope": "vertical",
        "vertical_type": "home_services",
        "priority": 20,
        "status": "active",
        "condition_json": {
            "vertical_type": "home_services",
            "service_codes_any": ["plumbing_repair", "pipe_repair", "tap_repair"],
        },
        "recommendation_json": {
            "entity_type": "issue_type",
            "entity_codes": ["leakage", "blockage", "low_water_pressure", "installation_required", "pipe_repair"],
            "mark_common": True,
        },
        "explanation_template": "Common issues reported for plumbing services.",
    },
    {
        "code": "plumbing_option_recommendations",
        "name": "Recommend Plumbing Service Options",
        "description": "Recommends common plumbing types/fixtures",
        "rule_type": "service_option",
        "scope": "vertical",
        "vertical_type": "home_services",
        "priority": 21,
        "status": "active",
        "condition_json": {
            "vertical_type": "home_services",
            "service_codes_any": ["plumbing_repair", "pipe_repair"],
        },
        "recommendation_json": {
            "entity_type": "service_option",
            "entity_codes": ["tap", "pipe", "sink", "toilet", "water_tank"],
            "apply_to": "service",
        },
        "explanation_template": "Common fixture types for plumbing services.",
    },

    # ── Provider setup defaults ───────────────────────────────────────────────
    {
        "code": "schedule_availability_default",
        "name": "Recommend Weekly Availability Setup",
        "description": "Services requiring scheduling should suggest weekly availability setup",
        "rule_type": "provider_default",
        "scope": "platform",
        "priority": 50,
        "status": "active",
        "condition_json": {
            "requires_schedule": True,
        },
        "recommendation_json": {
            "entity_type": "provider_default",
            "entity_codes": ["weekly_availability_setup"],
            "apply_to": "provider_onboarding",
        },
        "explanation_template": "This service requires scheduling — set up weekly availability.",
    },
    {
        "code": "staff_assignment_default",
        "name": "Recommend Staff Assignment Setup",
        "description": "Services requiring staff should prompt staff assignment during setup",
        "rule_type": "provider_default",
        "scope": "platform",
        "priority": 51,
        "status": "active",
        "condition_json": {
            "requires_staff_assignment": True,
        },
        "recommendation_json": {
            "entity_type": "provider_default",
            "entity_codes": ["staff_assignment_setup"],
            "apply_to": "provider_onboarding",
        },
        "explanation_template": "This service requires staff assignment — configure your team.",
    },
    {
        "code": "photo_upload_for_water_leakage",
        "name": "Recommend Photo Upload for Water Leakage",
        "description": "When customer selects water leakage issue, recommend photo upload",
        "rule_type": "customer_next_step",
        "scope": "platform",
        "priority": 30,
        "status": "active",
        "condition_json": {
            "requires_issue_type": True,
        },
        "recommendation_json": {
            "entity_type": "customer_next_step",
            "entity_codes": ["upload_photo"],
            "apply_to": "customer_booking",
            "trigger_issue_codes": ["water_leakage"],
        },
        "explanation_template": "Photo helps technician assess water leakage before visit.",
    },

    # ── Coaching ──────────────────────────────────────────────────────────────
    {
        "code": "ielts_document_recommendations",
        "name": "Recommend IELTS Provider Documents",
        "description": "Recommends standard documents for coaching/IELTS providers",
        "rule_type": "document_requirement",
        "scope": "vertical",
        "vertical_type": "coaching",
        "priority": 40,
        "status": "active",
        "condition_json": {
            "vertical_type": "coaching",
        },
        "recommendation_json": {
            "entity_type": "document_requirement",
            "entity_codes": ["teaching_certificate", "institute_registration", "trainer_id_proof"],
            "is_required": True,
        },
        "explanation_template": "Standard compliance documents for coaching providers.",
    },
]


async def seed() -> None:
    async for db in get_async_session():
        created = 0
        skipped = 0
        for rule_data in RULES:
            existing = await db.scalar(
                select(RecommendationRule).where(
                    RecommendationRule.code == rule_data["code"],
                    RecommendationRule.deleted_at.is_(None),
                )
            )
            if existing:
                skipped += 1
                continue

            rule = RecommendationRule(**rule_data)
            db.add(rule)
            created += 1

        await db.commit()
        print(f"Seed complete: {created} created, {skipped} skipped (idempotent)")
        break


if __name__ == "__main__":
    asyncio.run(seed())
