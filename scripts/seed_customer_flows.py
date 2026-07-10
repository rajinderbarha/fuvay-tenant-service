"""Sprint 14 — Seed customer_flow_configs for all real categories.

Idempotent: skips categories that already have a flow config.
Also updates service_categories with is_customer_visible, primary_engine_key,
frontend_component_key based on the category_type / customer_flow_type.
"""
from __future__ import annotations
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy import select, text
from app.database import init_db, close_db, get_db_session
from app.engines.admin_catalog.models import ServiceCategory, CustomerFlowConfig

FLOW_CONFIGS = {
    "home_services": {
        "customer_flow_type": "service_booking",
        "frontend_component_key": "ServiceBookingFlow",
        "primary_engine_key": "booking_engine",
        "required_steps": [
            "select_offering",
            "collect_issue_details",
            "select_type_brand",
            "address",
            "price_estimate",
            "provider_selection_or_auto_match",
            "confirmation",
        ],
        "optional_steps": ["photo_upload", "customer_notes"],
        "is_customer_visible": True,
    },
    "coaching": {
        "customer_flow_type": "appointment_booking",
        "frontend_component_key": "AppointmentBookingFlow",
        "primary_engine_key": "appointment_engine",
        "required_steps": [
            "select_offering",
            "select_mode",
            "select_slot",
            "student_details",
            "confirmation",
        ],
        "optional_steps": ["student_notes"],
        "is_customer_visible": True,
    },
    "real_estate": {
        "customer_flow_type": "lead_capture",
        "frontend_component_key": "LeadCaptureFlow",
        "primary_engine_key": "lead_engine",
        "required_steps": [
            "select_offering",
            "property_intent",
            "location_budget",
            "contact_details",
            "provider_selection_or_auto_assign",
            "confirmation",
        ],
        "optional_steps": ["additional_requirements"],
        "is_customer_visible": True,
    },
}

# For categories without a category_type match, fall back on customer_flow_type
FLOW_FROM_CUSTOMER_FLOW_TYPE = {
    "service_booking":      ("home_services", "ServiceBookingFlow", "booking_engine"),
    "appointment_booking":  ("coaching",      "AppointmentBookingFlow", "appointment_engine"),
    "lead_capture":         ("real_estate",   "LeadCaptureFlow", "lead_engine"),
}


async def seed_master_offerings(db) -> None:
    """Update master_offerings with customer_flow_type + requirement fields based on offering_class."""
    from sqlalchemy import text

    # service offerings → service_booking, requires address + photo
    await db.execute(text("""
        UPDATE master_offerings SET
            customer_flow_type  = 'service_booking',
            primary_engine_key  = 'booking_engine',
            requires_address    = true,
            requires_photo_upload = true
        WHERE offering_class = 'service'
          AND customer_flow_type IS NULL
    """))
    # appointment offerings → appointment_booking, requires slot
    await db.execute(text("""
        UPDATE master_offerings SET
            customer_flow_type  = 'appointment_booking',
            primary_engine_key  = 'appointment_engine',
            requires_slot       = true
        WHERE offering_class = 'appointment'
          AND customer_flow_type IS NULL
    """))
    # lead offerings → lead_capture
    await db.execute(text("""
        UPDATE master_offerings SET
            customer_flow_type  = 'lead_capture',
            primary_engine_key  = 'lead_engine'
        WHERE offering_class = 'lead'
          AND customer_flow_type IS NULL
    """))
    print("  Updated master_offerings customer_flow_type from offering_class")


async def seed() -> None:
    await init_db()
    print("Seeding customer_flow_configs…")

    async with get_db_session() as db:
        await seed_master_offerings(db)

        result = await db.execute(
            select(ServiceCategory).where(ServiceCategory.is_active == True)
        )
        categories = result.scalars().all()

        seeded = 0
        updated = 0
        skipped = 0

        for cat in categories:
            # Determine which flow config to apply
            cfg_data = FLOW_CONFIGS.get(cat.category_type or "")
            if not cfg_data and cat.customer_flow_type:
                match = FLOW_FROM_CUSTOMER_FLOW_TYPE.get(cat.customer_flow_type)
                if match:
                    cat_type_key, comp_key, eng_key = match
                    cfg_data = FLOW_CONFIGS.get(cat_type_key)

            if not cfg_data:
                print(f"  SKIP  '{cat.name}' — no flow config for category_type={cat.category_type!r}")
                skipped += 1
                continue

            # Update service_categories fields
            needs_update = False
            if not cat.is_customer_visible:
                cat.is_customer_visible = cfg_data["is_customer_visible"]
                needs_update = True
            if not cat.frontend_component_key:
                cat.frontend_component_key = cfg_data["frontend_component_key"]
                needs_update = True
            if not cat.primary_engine_key:
                cat.primary_engine_key = cfg_data["primary_engine_key"]
                needs_update = True

            # Check if CustomerFlowConfig already exists
            existing = await db.execute(
                select(CustomerFlowConfig).where(CustomerFlowConfig.category_id == cat.id)
            )
            flow_cfg = existing.scalar_one_or_none()

            if flow_cfg:
                print(f"  EXISTS '{cat.name}' — flow config already present, updating")
                flow_cfg.customer_flow_type     = cfg_data["customer_flow_type"]
                flow_cfg.frontend_component_key = cfg_data["frontend_component_key"]
                flow_cfg.primary_engine_key     = cfg_data["primary_engine_key"]
                flow_cfg.required_steps         = cfg_data["required_steps"]
                flow_cfg.optional_steps         = cfg_data.get("optional_steps")
                flow_cfg.is_active              = True
                updated += 1
            else:
                new_cfg = CustomerFlowConfig(
                    category_id=cat.id,
                    customer_flow_type=cfg_data["customer_flow_type"],
                    frontend_component_key=cfg_data["frontend_component_key"],
                    primary_engine_key=cfg_data["primary_engine_key"],
                    required_steps=cfg_data["required_steps"],
                    optional_steps=cfg_data.get("optional_steps"),
                    is_active=True,
                )
                db.add(new_cfg)
                seeded += 1
                print(f"  SEED  '{cat.name}' → {cfg_data['customer_flow_type']}")

        await db.commit()
        print(f"\nDone. Seeded={seeded}, Updated={updated}, Skipped={skipped}")

    await close_db()


if __name__ == "__main__":
    asyncio.run(seed())
