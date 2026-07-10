"""Seed universal service categories for all 14 verticals.
Idempotent by slug — skips existing rows, updates if fields differ.
Run: python scripts/seed_universal_categories.py
"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.engines.admin_catalog.models import ServiceCategory

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://serviceos:serviceos@localhost:5432/serviceos")

CATEGORIES = [
    {
        "name": "Home Services",
        "slug": "home_services",
        "description": "Residential repair, maintenance, installation, and cleaning services",
        "vertical_type": "home_services",
        "finance_model": "security_deposit_plus_credit_wallet",
        "provider_business_model": "service_provider",
        "customer_flow_type": "service_booking",
        "requires_location": True,
        "requires_schedule": False,
        "requires_brand": True,
        "requires_service_option": False,
        "requires_issue_type": True,
        "tenant_selectable": True,
        "pricing_supported": True,
    },
    {
        "name": "Salon & Beauty",
        "slug": "salon",
        "description": "Hair, nails, skincare, and personal grooming services",
        "vertical_type": "salon",
        "finance_model": "security_deposit_plus_credit_wallet",
        "provider_business_model": "service_provider",
        "customer_flow_type": "appointment_booking",
        "requires_location": False,
        "requires_schedule": True,
        "requires_brand": False,
        "requires_service_option": True,
        "requires_issue_type": False,
        "tenant_selectable": True,
        "pricing_supported": True,
    },
    {
        "name": "Coaching & Education",
        "slug": "coaching",
        "description": "IELTS, language coaching, tutoring, and professional skills training",
        "vertical_type": "coaching",
        "finance_model": "monthly_subscription",
        "provider_business_model": "subscription_member",
        "customer_flow_type": "appointment_booking",
        "requires_location": False,
        "requires_schedule": True,
        "requires_brand": False,
        "requires_service_option": True,
        "requires_issue_type": False,
        "tenant_selectable": True,
        "pricing_supported": True,
    },
    {
        "name": "Real Estate",
        "slug": "real_estate",
        "description": "Property listing, rental, sales, and real estate lead management",
        "vertical_type": "real_estate",
        "finance_model": "lead_credit",
        "provider_business_model": "marketplace_lister",
        "customer_flow_type": "lead_capture",
        "requires_location": True,
        "requires_schedule": True,
        "requires_brand": False,
        "requires_service_option": False,
        "requires_issue_type": False,
        "tenant_selectable": True,
        "pricing_supported": False,
    },
    {
        "name": "Restaurant & Food",
        "slug": "restaurant",
        "description": "Restaurant ordering, catering, food delivery, and cloud kitchen services",
        "vertical_type": "restaurant",
        "finance_model": "commission_wallet",
        "provider_business_model": "product_seller",
        "customer_flow_type": "product_purchase",
        "requires_location": True,
        "requires_schedule": False,
        "requires_brand": False,
        "requires_service_option": True,
        "requires_issue_type": False,
        "tenant_selectable": True,
        "pricing_supported": True,
    },
    {
        "name": "Automotive",
        "slug": "automotive",
        "description": "Car repair, maintenance, wash, roadside assistance, and parts",
        "vertical_type": "automotive",
        "finance_model": "security_deposit_plus_credit_wallet",
        "provider_business_model": "service_provider",
        "customer_flow_type": "inspection_first",
        "requires_location": True,
        "requires_schedule": True,
        "requires_brand": True,
        "requires_service_option": False,
        "requires_issue_type": True,
        "tenant_selectable": True,
        "pricing_supported": True,
    },
    {
        "name": "Professional Services",
        "slug": "professional_services",
        "description": "Legal, accounting, consulting, IT, and business support services",
        "vertical_type": "professional_services",
        "finance_model": "lead_credit",
        "provider_business_model": "service_provider",
        "customer_flow_type": "quote_request",
        "requires_location": False,
        "requires_schedule": True,
        "requires_brand": False,
        "requires_service_option": True,
        "requires_issue_type": False,
        "tenant_selectable": True,
        "pricing_supported": True,
    },
    {
        "name": "Pharmacy & Healthcare",
        "slug": "pharmacy",
        "description": "Medicine delivery, lab tests, telehealth, and health product orders",
        "vertical_type": "pharmacy",
        "finance_model": "product_order_commission",
        "provider_business_model": "product_seller",
        "customer_flow_type": "product_purchase",
        "requires_location": True,
        "requires_schedule": False,
        "requires_brand": True,
        "requires_service_option": False,
        "requires_issue_type": False,
        "tenant_selectable": True,
        "pricing_supported": True,
    },
    {
        "name": "Hardware & Tools",
        "slug": "hardware",
        "description": "Hardware store, tool rental, construction materials, and equipment",
        "vertical_type": "hardware",
        "finance_model": "product_order_commission",
        "provider_business_model": "product_seller",
        "customer_flow_type": "product_purchase",
        "requires_location": True,
        "requires_schedule": False,
        "requires_brand": True,
        "requires_service_option": False,
        "requires_issue_type": False,
        "tenant_selectable": True,
        "pricing_supported": True,
    },
    {
        "name": "Repair Services",
        "slug": "repair_services",
        "description": "Electronics, appliance, and device repair services",
        "vertical_type": "repair_services",
        "finance_model": "security_deposit_plus_credit_wallet",
        "provider_business_model": "service_provider",
        "customer_flow_type": "inspection_first",
        "requires_location": False,
        "requires_schedule": True,
        "requires_brand": True,
        "requires_service_option": False,
        "requires_issue_type": True,
        "tenant_selectable": True,
        "pricing_supported": True,
    },
    {
        "name": "Cleaning Services",
        "slug": "cleaning_services",
        "description": "Deep cleaning, regular housekeeping, commercial and industrial cleaning",
        "vertical_type": "cleaning_services",
        "finance_model": "security_deposit_plus_credit_wallet",
        "provider_business_model": "service_provider",
        "customer_flow_type": "service_booking",
        "requires_location": True,
        "requires_schedule": True,
        "requires_brand": False,
        "requires_service_option": True,
        "requires_issue_type": False,
        "tenant_selectable": True,
        "pricing_supported": True,
    },
    {
        "name": "Laundry & Dry Cleaning",
        "slug": "laundry",
        "description": "Pickup and delivery laundry, dry cleaning, and garment care",
        "vertical_type": "laundry",
        "finance_model": "security_deposit_plus_credit_wallet",
        "provider_business_model": "service_provider",
        "customer_flow_type": "service_booking",
        "requires_location": True,
        "requires_schedule": True,
        "requires_brand": False,
        "requires_service_option": True,
        "requires_issue_type": False,
        "tenant_selectable": True,
        "pricing_supported": True,
    },
    {
        "name": "Marketplace Products",
        "slug": "marketplace_products",
        "description": "General e-commerce and multi-vendor product marketplace",
        "vertical_type": "marketplace_products",
        "finance_model": "commission_wallet",
        "provider_business_model": "marketplace_lister",
        "customer_flow_type": "product_purchase",
        "requires_location": True,
        "requires_schedule": False,
        "requires_brand": True,
        "requires_service_option": True,
        "requires_issue_type": False,
        "tenant_selectable": True,
        "pricing_supported": True,
    },
    {
        "name": "Other",
        "slug": "other",
        "description": "Generic category for verticals not covered by standard types",
        "vertical_type": "other",
        "finance_model": "free_listing",
        "provider_business_model": "service_provider",
        "customer_flow_type": "service_booking",
        "requires_location": False,
        "requires_schedule": False,
        "requires_brand": False,
        "requires_service_option": False,
        "requires_issue_type": False,
        "tenant_selectable": True,
        "pricing_supported": False,
    },
]

UPDATABLE_FIELDS = [
    "name", "description", "vertical_type", "finance_model", "provider_business_model",
    "customer_flow_type", "requires_location", "requires_schedule", "requires_brand",
    "requires_service_option", "requires_issue_type", "tenant_selectable", "pricing_supported",
]


async def run():
    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as db:
        created = updated = skipped = 0
        for data in CATEGORIES:
            slug = data["slug"]
            result = await db.execute(select(ServiceCategory).where(ServiceCategory.slug == slug))
            existing = result.scalar_one_or_none()

            if existing is None:
                cat = ServiceCategory(
                    name=data["name"],
                    slug=slug,
                    description=data.get("description"),
                    vertical_type=data.get("vertical_type"),
                    finance_model=data.get("finance_model"),
                    provider_business_model=data.get("provider_business_model"),
                    customer_flow_type=data.get("customer_flow_type"),
                    requires_location=data.get("requires_location", True),
                    requires_schedule=data.get("requires_schedule", False),
                    requires_brand=data.get("requires_brand", False),
                    requires_service_option=data.get("requires_service_option", False),
                    requires_issue_type=data.get("requires_issue_type", False),
                    tenant_selectable=data.get("tenant_selectable", True),
                    pricing_supported=data.get("pricing_supported", True),
                    is_active=True,
                    display_order=CATEGORIES.index(data),
                )
                db.add(cat)
                print(f"  [CREATE] {slug}")
                created += 1
            else:
                changed = False
                for field in UPDATABLE_FIELDS:
                    new_val = data.get(field)
                    if new_val is not None and getattr(existing, field, None) != new_val:
                        setattr(existing, field, new_val)
                        changed = True
                if changed:
                    print(f"  [UPDATE] {slug}")
                    updated += 1
                else:
                    print(f"  [SKIP]   {slug}")
                    skipped += 1

        await db.commit()

    await engine.dispose()
    print(f"\nDone — created={created} updated={updated} skipped={skipped}")


if __name__ == "__main__":
    asyncio.run(run())
