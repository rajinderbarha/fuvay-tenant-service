"""Seed master services for all verticals.
Idempotent by slug — skips existing rows.
Run: python scripts/seed_master_services.py
"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.engines.admin_catalog.models import ServiceCategory, ServiceGroup, MasterService

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://serviceos:serviceos@localhost:5432/serviceos")

# Services keyed by (category_slug, group_code)
SERVICES: list[dict] = [
    # ─── Home Services ────────────────────────────────────────────────────────
    {"category": "home_services", "group": "ac_services", "name": "AC Installation", "slug": "ac_installation", "job_type": "installation", "base_price": 150.0, "requires_address": True, "is_brand_required": True, "requires_issue_type": False},
    {"category": "home_services", "group": "ac_services", "name": "AC Repair", "slug": "ac_repair", "job_type": "repair", "base_price": 75.0, "requires_address": True, "is_brand_required": True, "requires_issue_type": True},
    {"category": "home_services", "group": "ac_services", "name": "AC Maintenance / Servicing", "slug": "ac_maintenance", "job_type": "service", "base_price": 50.0, "requires_address": True, "is_brand_required": True, "requires_issue_type": False},
    {"category": "home_services", "group": "ac_services", "name": "AC Gas Refill", "slug": "ac_gas_refill", "job_type": "service", "base_price": 40.0, "requires_address": True, "is_brand_required": True, "requires_issue_type": False},

    {"category": "home_services", "group": "plumbing", "name": "Pipe Repair", "slug": "pipe_repair", "job_type": "repair", "base_price": 60.0, "requires_address": True, "is_brand_required": False, "requires_issue_type": True},
    {"category": "home_services", "group": "plumbing", "name": "Drain Unblocking", "slug": "drain_unblocking", "job_type": "service", "base_price": 45.0, "requires_address": True, "is_brand_required": False, "requires_issue_type": False},
    {"category": "home_services", "group": "plumbing", "name": "Tap & Fixture Installation", "slug": "tap_fixture_install", "job_type": "installation", "base_price": 55.0, "requires_address": True, "is_brand_required": False, "requires_issue_type": False},
    {"category": "home_services", "group": "plumbing", "name": "Water Tank Cleaning", "slug": "water_tank_cleaning", "job_type": "service", "base_price": 80.0, "requires_address": True, "is_brand_required": False, "requires_issue_type": False},

    {"category": "home_services", "group": "electrical", "name": "Electrical Fault Fix", "slug": "electrical_fault_fix", "job_type": "repair", "base_price": 70.0, "requires_address": True, "is_brand_required": False, "requires_issue_type": True},
    {"category": "home_services", "group": "electrical", "name": "Fan & Light Installation", "slug": "fan_light_install", "job_type": "installation", "base_price": 40.0, "requires_address": True, "is_brand_required": False, "requires_issue_type": False},
    {"category": "home_services", "group": "electrical", "name": "Circuit Breaker & Fuse", "slug": "circuit_breaker", "job_type": "repair", "base_price": 60.0, "requires_address": True, "is_brand_required": False, "requires_issue_type": False},

    {"category": "home_services", "group": "painting", "name": "Interior Wall Painting", "slug": "interior_painting", "job_type": "service", "base_price": 200.0, "requires_address": True, "is_brand_required": False, "requires_issue_type": False},
    {"category": "home_services", "group": "painting", "name": "Exterior Painting", "slug": "exterior_painting", "job_type": "service", "base_price": 350.0, "requires_address": True, "is_brand_required": False, "requires_issue_type": False},

    {"category": "home_services", "group": "pest_control", "name": "General Pest Control", "slug": "general_pest_control", "job_type": "service", "base_price": 90.0, "requires_address": True, "is_brand_required": False, "requires_issue_type": False},
    {"category": "home_services", "group": "pest_control", "name": "Termite Treatment", "slug": "termite_treatment", "job_type": "service", "base_price": 150.0, "requires_address": True, "is_brand_required": False, "requires_issue_type": False},

    # ─── Salon & Beauty ───────────────────────────────────────────────────────
    {"category": "salon", "group": "hair_services", "name": "Haircut & Styling", "slug": "haircut_styling", "job_type": "consultation", "base_price": 25.0, "requires_address": False, "is_brand_required": False, "requires_issue_type": False},
    {"category": "salon", "group": "hair_services", "name": "Hair Coloring", "slug": "hair_coloring", "job_type": "service", "base_price": 60.0, "requires_address": False, "is_brand_required": True, "requires_issue_type": False},
    {"category": "salon", "group": "hair_services", "name": "Hair Treatment", "slug": "hair_treatment", "job_type": "service", "base_price": 45.0, "requires_address": False, "is_brand_required": True, "requires_issue_type": False},

    {"category": "salon", "group": "nail_services", "name": "Manicure", "slug": "manicure", "job_type": "service", "base_price": 20.0, "requires_address": False, "is_brand_required": False, "requires_issue_type": False},
    {"category": "salon", "group": "nail_services", "name": "Pedicure", "slug": "pedicure", "job_type": "service", "base_price": 25.0, "requires_address": False, "is_brand_required": False, "requires_issue_type": False},
    {"category": "salon", "group": "nail_services", "name": "Nail Extensions", "slug": "nail_extensions", "job_type": "service", "base_price": 40.0, "requires_address": False, "is_brand_required": False, "requires_issue_type": False},

    {"category": "salon", "group": "skincare", "name": "Basic Facial", "slug": "basic_facial", "job_type": "service", "base_price": 35.0, "requires_address": False, "is_brand_required": False, "requires_issue_type": False},
    {"category": "salon", "group": "skincare", "name": "Deep Cleansing Facial", "slug": "deep_cleansing_facial", "job_type": "service", "base_price": 55.0, "requires_address": False, "is_brand_required": False, "requires_issue_type": False},

    {"category": "salon", "group": "massage_spa", "name": "Swedish Massage", "slug": "swedish_massage", "job_type": "service", "base_price": 50.0, "requires_address": False, "is_brand_required": False, "requires_issue_type": False},
    {"category": "salon", "group": "massage_spa", "name": "Deep Tissue Massage", "slug": "deep_tissue_massage", "job_type": "service", "base_price": 65.0, "requires_address": False, "is_brand_required": False, "requires_issue_type": False},

    # ─── Coaching & Education ─────────────────────────────────────────────────
    {"category": "coaching", "group": "ielts_coaching", "name": "IELTS Academic Preparation", "slug": "ielts_academic", "job_type": "consultation", "base_price": 300.0, "requires_address": False, "is_brand_required": False, "requires_issue_type": False},
    {"category": "coaching", "group": "ielts_coaching", "name": "IELTS General Training", "slug": "ielts_general", "job_type": "consultation", "base_price": 280.0, "requires_address": False, "is_brand_required": False, "requires_issue_type": False},
    {"category": "coaching", "group": "ielts_coaching", "name": "IELTS Mock Test + Feedback", "slug": "ielts_mock_test", "job_type": "consultation", "base_price": 50.0, "requires_address": False, "is_brand_required": False, "requires_issue_type": False},

    {"category": "coaching", "group": "language_courses", "name": "English Speaking Course", "slug": "english_speaking", "job_type": "consultation", "base_price": 200.0, "requires_address": False, "is_brand_required": False, "requires_issue_type": False},
    {"category": "coaching", "group": "language_courses", "name": "Arabic Language Course", "slug": "arabic_language", "job_type": "consultation", "base_price": 180.0, "requires_address": False, "is_brand_required": False, "requires_issue_type": False},

    {"category": "coaching", "group": "academic_tutoring", "name": "Math Tutoring", "slug": "math_tutoring", "job_type": "consultation", "base_price": 30.0, "requires_address": False, "is_brand_required": False, "requires_issue_type": False},
    {"category": "coaching", "group": "academic_tutoring", "name": "Science Tutoring", "slug": "science_tutoring", "job_type": "consultation", "base_price": 30.0, "requires_address": False, "is_brand_required": False, "requires_issue_type": False},

    # ─── Real Estate ──────────────────────────────────────────────────────────
    {"category": "real_estate", "group": "residential_sales", "name": "Property Listing for Sale", "slug": "property_sale_listing", "job_type": "consultation", "base_price": 0.0, "requires_address": True, "is_brand_required": False, "requires_issue_type": False},
    {"category": "real_estate", "group": "residential_rental", "name": "Property Listing for Rent", "slug": "property_rent_listing", "job_type": "consultation", "base_price": 0.0, "requires_address": True, "is_brand_required": False, "requires_issue_type": False},
    {"category": "real_estate", "group": "commercial_properties", "name": "Office Space Listing", "slug": "office_listing", "job_type": "consultation", "base_price": 0.0, "requires_address": True, "is_brand_required": False, "requires_issue_type": False},
    {"category": "real_estate", "group": "property_management", "name": "Property Management Service", "slug": "property_management_svc", "job_type": "service", "base_price": 100.0, "requires_address": True, "is_brand_required": False, "requires_issue_type": False},

    # ─── Automotive ───────────────────────────────────────────────────────────
    {"category": "automotive", "group": "car_repair", "name": "Engine Diagnostics", "slug": "engine_diagnostics", "job_type": "consultation", "base_price": 40.0, "requires_address": True, "is_brand_required": True, "requires_issue_type": True},
    {"category": "automotive", "group": "car_repair", "name": "Engine Repair", "slug": "engine_repair", "job_type": "repair", "base_price": 200.0, "requires_address": True, "is_brand_required": True, "requires_issue_type": True},
    {"category": "automotive", "group": "car_repair", "name": "Brake Service", "slug": "brake_service", "job_type": "service", "base_price": 80.0, "requires_address": True, "is_brand_required": True, "requires_issue_type": False},
    {"category": "automotive", "group": "car_wash_detailing", "name": "Basic Car Wash", "slug": "basic_car_wash", "job_type": "service", "base_price": 15.0, "requires_address": True, "is_brand_required": False, "requires_issue_type": False},
    {"category": "automotive", "group": "car_wash_detailing", "name": "Full Car Detailing", "slug": "car_detailing", "job_type": "service", "base_price": 80.0, "requires_address": True, "is_brand_required": False, "requires_issue_type": False},
    {"category": "automotive", "group": "tires_wheels", "name": "Tire Change", "slug": "tire_change", "job_type": "service", "base_price": 30.0, "requires_address": True, "is_brand_required": False, "requires_issue_type": False},
    {"category": "automotive", "group": "battery_electrical", "name": "Battery Replacement", "slug": "battery_replacement", "job_type": "service", "base_price": 60.0, "requires_address": True, "is_brand_required": True, "requires_issue_type": False},
    {"category": "automotive", "group": "roadside_assistance", "name": "Towing Service", "slug": "towing_service", "job_type": "service", "base_price": 50.0, "requires_address": True, "is_brand_required": False, "requires_issue_type": False},

    # ─── Repair Services ──────────────────────────────────────────────────────
    {"category": "repair_services", "group": "phone_repair", "name": "Screen Replacement", "slug": "screen_replacement", "job_type": "repair", "base_price": 60.0, "requires_address": False, "is_brand_required": True, "requires_issue_type": True},
    {"category": "repair_services", "group": "phone_repair", "name": "Battery Replacement (Phone)", "slug": "phone_battery_replacement", "job_type": "repair", "base_price": 30.0, "requires_address": False, "is_brand_required": True, "requires_issue_type": False},
    {"category": "repair_services", "group": "laptop_repair", "name": "Laptop Screen Fix", "slug": "laptop_screen_fix", "job_type": "repair", "base_price": 90.0, "requires_address": False, "is_brand_required": True, "requires_issue_type": True},
    {"category": "repair_services", "group": "laptop_repair", "name": "Laptop Keyboard Replacement", "slug": "laptop_keyboard", "job_type": "repair", "base_price": 70.0, "requires_address": False, "is_brand_required": True, "requires_issue_type": False},
    {"category": "repair_services", "group": "tv_repair", "name": "TV Screen Repair", "slug": "tv_screen_repair", "job_type": "repair", "base_price": 120.0, "requires_address": True, "is_brand_required": True, "requires_issue_type": True},

    # ─── Cleaning Services ────────────────────────────────────────────────────
    {"category": "cleaning_services", "group": "home_cleaning", "name": "Regular Home Cleaning", "slug": "regular_home_cleaning", "job_type": "service", "base_price": 50.0, "requires_address": True, "is_brand_required": False, "requires_issue_type": False},
    {"category": "cleaning_services", "group": "deep_cleaning", "name": "Full Home Deep Clean", "slug": "full_home_deep_clean", "job_type": "service", "base_price": 120.0, "requires_address": True, "is_brand_required": False, "requires_issue_type": False},
    {"category": "cleaning_services", "group": "sofa_carpet", "name": "Sofa Cleaning", "slug": "sofa_cleaning", "job_type": "service", "base_price": 60.0, "requires_address": True, "is_brand_required": False, "requires_issue_type": False},
    {"category": "cleaning_services", "group": "sofa_carpet", "name": "Carpet Cleaning", "slug": "carpet_cleaning", "job_type": "service", "base_price": 70.0, "requires_address": True, "is_brand_required": False, "requires_issue_type": False},
    {"category": "cleaning_services", "group": "move_in_out", "name": "Move-in Cleaning", "slug": "move_in_cleaning", "job_type": "service", "base_price": 150.0, "requires_address": True, "is_brand_required": False, "requires_issue_type": False},

    # ─── Laundry ──────────────────────────────────────────────────────────────
    {"category": "laundry", "group": "wash_fold", "name": "Wash & Fold (per kg)", "slug": "wash_fold_per_kg", "job_type": "service", "base_price": 3.0, "requires_address": True, "is_brand_required": False, "requires_issue_type": False},
    {"category": "laundry", "group": "dry_cleaning", "name": "Dry Cleaning (shirt)", "slug": "dry_clean_shirt", "job_type": "service", "base_price": 5.0, "requires_address": True, "is_brand_required": False, "requires_issue_type": False},
    {"category": "laundry", "group": "dry_cleaning", "name": "Dry Cleaning (suit)", "slug": "dry_clean_suit", "job_type": "service", "base_price": 12.0, "requires_address": True, "is_brand_required": False, "requires_issue_type": False},
    {"category": "laundry", "group": "ironing", "name": "Ironing Service (per item)", "slug": "ironing_per_item", "job_type": "service", "base_price": 1.5, "requires_address": True, "is_brand_required": False, "requires_issue_type": False},
]


async def run():
    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as db:
        # Load categories
        all_slugs = list({s["category"] for s in SERVICES})
        cat_result = await db.execute(select(ServiceCategory).where(ServiceCategory.slug.in_(all_slugs)))
        cats = {c.slug: c for c in cat_result.scalars().all()}

        # Load groups
        all_codes = list({s["group"] for s in SERVICES})
        grp_result = await db.execute(select(ServiceGroup).where(ServiceGroup.code.in_(all_codes)))
        groups = {g.code: g for g in grp_result.scalars().all()}

        created = skipped = warn = 0
        for sdata in SERVICES:
            cat_slug = sdata["category"]
            grp_code = sdata["group"]
            service_slug = sdata["slug"]

            cat = cats.get(cat_slug)
            if not cat:
                print(f"  [WARN] Category '{cat_slug}' missing — run seed_universal_categories.py first")
                warn += 1
                continue

            grp = groups.get(grp_code)
            if not grp:
                print(f"  [WARN] Group '{grp_code}' missing — run seed_service_groups.py first")
                warn += 1
                continue

            exists = await db.execute(select(MasterService).where(MasterService.slug == service_slug))
            if exists.scalar_one_or_none():
                print(f"  [SKIP]   {service_slug}")
                skipped += 1
                continue

            svc = MasterService(
                category_id=cat.id,
                service_group_id=grp.id,
                service_name=sdata["name"],
                slug=service_slug,
                job_type=sdata.get("job_type", "service"),
                pricing_model=sdata.get("pricing_model", "fixed"),
                base_price=sdata.get("base_price", 0.0),
                requires_address=sdata.get("requires_address", True),
                is_brand_required=sdata.get("is_brand_required", False),
                requires_issue_type=sdata.get("requires_issue_type", False),
                is_active=True,
                display_order=SERVICES.index(sdata),
            )
            db.add(svc)
            print(f"  [CREATE] {service_slug}  ({cat_slug}/{grp_code})")
            created += 1

        await db.commit()

    await engine.dispose()
    print(f"\nDone — created={created} skipped={skipped} warnings={warn}")


if __name__ == "__main__":
    asyncio.run(run())
