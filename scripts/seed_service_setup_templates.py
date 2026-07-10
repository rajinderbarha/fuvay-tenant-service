"""Sprint 34F — Seed 6 service setup starter pack templates.

Idempotent: checks code uniqueness before inserting.
Run: python -m scripts.seed_service_setup_templates
"""
from __future__ import annotations

import asyncio
from sqlalchemy import select

from app.models.database import AsyncSessionLocal
from app.engines.admin_catalog.models import (
    ServiceSetupTemplate,
    ServiceSetupTemplateItem,
)


TEMPLATES = [
    {
        "code": "home_ac_repair_starter",
        "name": "AC Repair — Starter Pack",
        "slug": "home_ac_repair_starter",
        "description": "Full setup for AC Repair service: service definition, issue types, options, pricing tiers, and workflow.",
        "vertical_type": "home_service",
        "template_type": "starter_pack",
        "is_system_template": True,
        "items": [
            {"item_type": "master_service",      "reference_code": "ac_repair",          "apply_mode": "create_if_missing", "is_required": True,  "display_order": 1},
            {"item_type": "master_issue_type",   "reference_code": "not_cooling",         "apply_mode": "map_existing",      "is_required": True,  "display_order": 2},
            {"item_type": "master_issue_type",   "reference_code": "water_leakage_ac",    "apply_mode": "map_existing",      "is_required": False, "display_order": 3},
            {"item_type": "master_issue_type",   "reference_code": "gas_refill_needed",   "apply_mode": "map_existing",      "is_required": False, "display_order": 4},
            {"item_type": "master_service_option","reference_code": "split_ac",           "apply_mode": "map_existing",      "is_required": True,  "display_order": 5},
            {"item_type": "master_service_option","reference_code": "window_ac",          "apply_mode": "map_existing",      "is_required": False, "display_order": 6},
            {"item_type": "pricing_tier",        "reference_code": "ac_repair_basic",     "apply_mode": "create_if_missing", "is_required": False, "display_order": 7},
            {"item_type": "checklist_template",  "reference_code": "ac_repair_checklist", "apply_mode": "create_if_missing", "is_required": False, "display_order": 8},
        ],
    },
    {
        "code": "home_plumbing_starter",
        "name": "Plumbing — Starter Pack",
        "slug": "home_plumbing_starter",
        "description": "Complete plumbing service setup including leakage, blockage, and installation issue types.",
        "vertical_type": "home_service",
        "template_type": "starter_pack",
        "is_system_template": True,
        "items": [
            {"item_type": "master_service",      "reference_code": "plumbing_repair",     "apply_mode": "create_if_missing", "is_required": True,  "display_order": 1},
            {"item_type": "master_issue_type",   "reference_code": "leakage_plumbing",    "apply_mode": "map_existing",      "is_required": True,  "display_order": 2},
            {"item_type": "master_issue_type",   "reference_code": "blockage",            "apply_mode": "map_existing",      "is_required": False, "display_order": 3},
            {"item_type": "master_issue_type",   "reference_code": "installation_req",    "apply_mode": "map_existing",      "is_required": False, "display_order": 4},
            {"item_type": "master_service_option","reference_code": "tap",                "apply_mode": "map_existing",      "is_required": False, "display_order": 5},
            {"item_type": "master_service_option","reference_code": "pipe",               "apply_mode": "map_existing",      "is_required": False, "display_order": 6},
        ],
    },
    {
        "code": "home_electrical_starter",
        "name": "Electrical Repairs — Starter Pack",
        "slug": "home_electrical_starter",
        "description": "Electrical service starter: no-power, short circuit, wiring issue types pre-mapped.",
        "vertical_type": "home_service",
        "template_type": "starter_pack",
        "is_system_template": True,
        "items": [
            {"item_type": "master_service",      "reference_code": "electrical_repair",   "apply_mode": "create_if_missing", "is_required": True,  "display_order": 1},
            {"item_type": "master_issue_type",   "reference_code": "no_power",            "apply_mode": "map_existing",      "is_required": True,  "display_order": 2},
            {"item_type": "master_issue_type",   "reference_code": "short_circuit",       "apply_mode": "map_existing",      "is_required": True,  "display_order": 3},
            {"item_type": "master_issue_type",   "reference_code": "wiring_issue",        "apply_mode": "map_existing",      "is_required": False, "display_order": 4},
            {"item_type": "master_issue_type",   "reference_code": "switch_socket_issue", "apply_mode": "map_existing",      "is_required": False, "display_order": 5},
        ],
    },
    {
        "code": "home_cleaning_starter",
        "name": "Home Cleaning — Starter Pack",
        "slug": "home_cleaning_starter",
        "description": "Cleaning service bundle with deep/basic/bathroom/kitchen package options.",
        "vertical_type": "home_service",
        "template_type": "service_bundle",
        "is_system_template": True,
        "items": [
            {"item_type": "master_service",       "reference_code": "home_cleaning",      "apply_mode": "create_if_missing", "is_required": True,  "display_order": 1},
            {"item_type": "master_service_option", "reference_code": "basic_cleaning",    "apply_mode": "map_existing",      "is_required": True,  "display_order": 2},
            {"item_type": "master_service_option", "reference_code": "deep_cleaning",     "apply_mode": "map_existing",      "is_required": False, "display_order": 3},
            {"item_type": "master_service_option", "reference_code": "bathroom_clean",    "apply_mode": "map_existing",      "is_required": False, "display_order": 4},
            {"item_type": "master_service_option", "reference_code": "kitchen_clean",     "apply_mode": "map_existing",      "is_required": False, "display_order": 5},
        ],
    },
    {
        "code": "coaching_ielts_starter",
        "name": "IELTS Coaching — Starter Pack",
        "slug": "coaching_ielts_starter",
        "description": "IELTS coaching category launch: service, appointment flow, coach profile checklist.",
        "vertical_type": "coaching",
        "template_type": "category_launch",
        "is_system_template": True,
        "items": [
            {"item_type": "master_service",      "reference_code": "ielts_coaching",      "apply_mode": "create_if_missing", "is_required": True,  "display_order": 1},
            {"item_type": "checklist_template",  "reference_code": "coach_onboarding",    "apply_mode": "create_if_missing", "is_required": True,  "display_order": 2},
            {"item_type": "workflow_template",   "reference_code": "coaching_appointment","apply_mode": "create_if_missing", "is_required": False, "display_order": 3},
        ],
    },
    {
        "code": "real_estate_lead_starter",
        "name": "Real Estate Lead Capture — Starter Pack",
        "slug": "real_estate_lead_starter",
        "description": "Real estate vertical launch: lead flow, property type options, agent profile checklist.",
        "vertical_type": "real_estate",
        "template_type": "category_launch",
        "is_system_template": True,
        "items": [
            {"item_type": "master_service",       "reference_code": "property_listing",   "apply_mode": "create_if_missing", "is_required": True,  "display_order": 1},
            {"item_type": "master_service_option", "reference_code": "property_type",     "apply_mode": "map_existing",      "is_required": False, "display_order": 2},
            {"item_type": "checklist_template",   "reference_code": "agent_onboarding",   "apply_mode": "create_if_missing", "is_required": False, "display_order": 3},
            {"item_type": "workflow_template",    "reference_code": "lead_capture_flow",  "apply_mode": "create_if_missing", "is_required": False, "display_order": 4},
        ],
    },
]


async def seed() -> None:
    async with AsyncSessionLocal() as db:
        created = skipped = 0
        for tpl in TEMPLATES:
            existing = await db.scalar(
                select(ServiceSetupTemplate).where(ServiceSetupTemplate.code == tpl["code"])
            )
            if existing:
                skipped += 1
                continue

            items_data = tpl.pop("items", [])
            row = ServiceSetupTemplate(
                **{k: v for k, v in tpl.items()},
                status="published",
                version=1,
            )
            db.add(row)
            await db.flush()

            for item in items_data:
                db.add(ServiceSetupTemplateItem(template_id=row.id, **item))

            created += 1

        await db.commit()
        print(f"Setup templates: {created} created, {skipped} skipped")


if __name__ == "__main__":
    asyncio.run(seed())
