"""Seed service groups for all category verticals.
Idempotent by code — skips existing rows.
Run: python scripts/seed_service_groups.py
"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.engines.admin_catalog.models import ServiceCategory, ServiceGroup

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://serviceos:serviceos@localhost:5432/serviceos")

# Groups keyed by category slug → list of group defs
GROUPS_BY_CATEGORY: dict[str, list[dict]] = {
    "home_services": [
        {"code": "ac_services", "name": "AC & HVAC", "slug": "ac_services", "display_order": 0},
        {"code": "plumbing", "name": "Plumbing", "slug": "plumbing", "display_order": 1},
        {"code": "electrical", "name": "Electrical", "slug": "electrical", "display_order": 2},
        {"code": "carpentry", "name": "Carpentry & Woodwork", "slug": "carpentry", "display_order": 3},
        {"code": "painting", "name": "Painting & Walls", "slug": "painting", "display_order": 4},
        {"code": "appliance_repair", "name": "Appliance Repair", "slug": "appliance_repair", "display_order": 5},
        {"code": "pest_control", "name": "Pest Control", "slug": "pest_control", "display_order": 6},
        {"code": "home_security", "name": "Home Security", "slug": "home_security", "display_order": 7},
    ],
    "salon": [
        {"code": "hair_services", "name": "Hair Services", "slug": "hair_services", "display_order": 0},
        {"code": "nail_services", "name": "Nail Services", "slug": "nail_services", "display_order": 1},
        {"code": "skincare", "name": "Skincare & Facials", "slug": "skincare", "display_order": 2},
        {"code": "makeup", "name": "Makeup & Bridal", "slug": "makeup", "display_order": 3},
        {"code": "massage_spa", "name": "Massage & Spa", "slug": "massage_spa", "display_order": 4},
    ],
    "coaching": [
        {"code": "ielts_coaching", "name": "IELTS Coaching", "slug": "ielts_coaching", "display_order": 0},
        {"code": "language_courses", "name": "Language Courses", "slug": "language_courses", "display_order": 1},
        {"code": "academic_tutoring", "name": "Academic Tutoring", "slug": "academic_tutoring", "display_order": 2},
        {"code": "professional_skills", "name": "Professional Skills", "slug": "professional_skills", "display_order": 3},
        {"code": "kids_programs", "name": "Kids Programs", "slug": "kids_programs", "display_order": 4},
    ],
    "real_estate": [
        {"code": "residential_sales", "name": "Residential Sales", "slug": "residential_sales", "display_order": 0},
        {"code": "residential_rental", "name": "Residential Rental", "slug": "residential_rental", "display_order": 1},
        {"code": "commercial_properties", "name": "Commercial Properties", "slug": "commercial_properties", "display_order": 2},
        {"code": "property_management", "name": "Property Management", "slug": "property_management", "display_order": 3},
    ],
    "restaurant": [
        {"code": "dine_in", "name": "Dine-in", "slug": "dine_in", "display_order": 0},
        {"code": "delivery", "name": "Delivery", "slug": "delivery", "display_order": 1},
        {"code": "catering", "name": "Catering", "slug": "catering", "display_order": 2},
        {"code": "cloud_kitchen", "name": "Cloud Kitchen", "slug": "cloud_kitchen", "display_order": 3},
    ],
    "automotive": [
        {"code": "car_repair", "name": "Car Repair", "slug": "car_repair", "display_order": 0},
        {"code": "car_wash_detailing", "name": "Car Wash & Detailing", "slug": "car_wash_detailing", "display_order": 1},
        {"code": "tires_wheels", "name": "Tires & Wheels", "slug": "tires_wheels", "display_order": 2},
        {"code": "battery_electrical", "name": "Battery & Electrical", "slug": "battery_electrical", "display_order": 3},
        {"code": "roadside_assistance", "name": "Roadside Assistance", "slug": "roadside_assistance", "display_order": 4},
    ],
    "professional_services": [
        {"code": "legal_services", "name": "Legal Services", "slug": "legal_services", "display_order": 0},
        {"code": "accounting_tax", "name": "Accounting & Tax", "slug": "accounting_tax", "display_order": 1},
        {"code": "it_support", "name": "IT Support", "slug": "it_support", "display_order": 2},
        {"code": "business_consulting", "name": "Business Consulting", "slug": "business_consulting", "display_order": 3},
        {"code": "hr_recruitment", "name": "HR & Recruitment", "slug": "hr_recruitment", "display_order": 4},
    ],
    "pharmacy": [
        {"code": "prescription_medicine", "name": "Prescription Medicine", "slug": "prescription_medicine", "display_order": 0},
        {"code": "otc_products", "name": "OTC Products", "slug": "otc_products", "display_order": 1},
        {"code": "lab_tests", "name": "Lab Tests", "slug": "lab_tests", "display_order": 2},
        {"code": "telehealth", "name": "Telehealth", "slug": "telehealth", "display_order": 3},
    ],
    "hardware": [
        {"code": "tools_equipment", "name": "Tools & Equipment", "slug": "tools_equipment", "display_order": 0},
        {"code": "building_materials", "name": "Building Materials", "slug": "building_materials", "display_order": 1},
        {"code": "electrical_supplies", "name": "Electrical Supplies", "slug": "electrical_supplies", "display_order": 2},
        {"code": "plumbing_supplies", "name": "Plumbing Supplies", "slug": "plumbing_supplies", "display_order": 3},
        {"code": "tool_rental", "name": "Tool Rental", "slug": "tool_rental", "display_order": 4},
    ],
    "repair_services": [
        {"code": "phone_repair", "name": "Phone & Tablet Repair", "slug": "phone_repair", "display_order": 0},
        {"code": "laptop_repair", "name": "Laptop & Computer Repair", "slug": "laptop_repair", "display_order": 1},
        {"code": "tv_repair", "name": "TV & Electronics Repair", "slug": "tv_repair", "display_order": 2},
        {"code": "appliance_fix", "name": "Appliance Fix", "slug": "appliance_fix", "display_order": 3},
    ],
    "cleaning_services": [
        {"code": "home_cleaning", "name": "Home Cleaning", "slug": "home_cleaning", "display_order": 0},
        {"code": "deep_cleaning", "name": "Deep Cleaning", "slug": "deep_cleaning", "display_order": 1},
        {"code": "office_cleaning", "name": "Office Cleaning", "slug": "office_cleaning", "display_order": 2},
        {"code": "sofa_carpet", "name": "Sofa & Carpet Cleaning", "slug": "sofa_carpet", "display_order": 3},
        {"code": "move_in_out", "name": "Move-in / Move-out Cleaning", "slug": "move_in_out", "display_order": 4},
    ],
    "laundry": [
        {"code": "wash_fold", "name": "Wash & Fold", "slug": "wash_fold", "display_order": 0},
        {"code": "dry_cleaning", "name": "Dry Cleaning", "slug": "dry_cleaning", "display_order": 1},
        {"code": "ironing", "name": "Ironing & Pressing", "slug": "ironing", "display_order": 2},
        {"code": "specialty_garments", "name": "Specialty Garments", "slug": "specialty_garments", "display_order": 3},
    ],
    "marketplace_products": [
        {"code": "electronics", "name": "Electronics", "slug": "electronics", "display_order": 0},
        {"code": "home_garden", "name": "Home & Garden", "slug": "home_garden", "display_order": 1},
        {"code": "fashion_apparel", "name": "Fashion & Apparel", "slug": "fashion_apparel", "display_order": 2},
        {"code": "sports_outdoors", "name": "Sports & Outdoors", "slug": "sports_outdoors", "display_order": 3},
    ],
}


async def run():
    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as db:
        # Load all categories by slug
        result = await db.execute(select(ServiceCategory).where(ServiceCategory.slug.in_(GROUPS_BY_CATEGORY.keys())))
        cats = {c.slug: c for c in result.scalars().all()}

        created = skipped = 0
        for cat_slug, groups in GROUPS_BY_CATEGORY.items():
            cat = cats.get(cat_slug)
            if not cat:
                print(f"  [WARN] Category '{cat_slug}' not found — run seed_universal_categories.py first")
                continue

            for gdata in groups:
                code = gdata["code"]
                exists_result = await db.execute(
                    select(ServiceGroup).where(ServiceGroup.code == code)
                )
                if exists_result.scalar_one_or_none():
                    print(f"  [SKIP]   {code}")
                    skipped += 1
                    continue

                group = ServiceGroup(
                    category_id=cat.id,
                    code=code,
                    name=gdata["name"],
                    slug=gdata["slug"],
                    description=gdata.get("description"),
                    display_order=gdata.get("display_order", 0),
                    status="active",
                )
                db.add(group)
                print(f"  [CREATE] {code}  ({cat_slug})")
                created += 1

        await db.commit()

    await engine.dispose()
    print(f"\nDone — created={created} skipped={skipped}")


if __name__ == "__main__":
    asyncio.run(run())
