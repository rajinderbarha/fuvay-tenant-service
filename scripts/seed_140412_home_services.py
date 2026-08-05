"""Seed 5-6 realistic, fully bookable home services at zipcode 140412.

Adds new sibling categories to the existing "Air Conditioning" category
(Plumbing, Electrical, Painting, Pest Control, Home Cleaning), each wired
the exact same way AC already works end-to-end for tenant "Guramrit":
  service_categories -> service_groups -> master_services
    -> tenant_services (Guramrit enablement, published)
    -> tenant_service_area_services (linked to Guramrit's existing
       140412 tenant_service_area, so it's actually serviceable there)

Idempotent — safe to re-run. Skips anything that already exists.
Run: python scripts/seed_140412_home_services.py
"""
import asyncio
import os
import sys
import uuid
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.engines.admin_catalog.models import (
    ServiceCategory, ServiceGroup, MasterService, TenantService,
)
from app.engines.serviceability.models import TenantServiceArea, TenantServiceAreaService

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://serviceos:serviceos@localhost:5432/serviceos")

TENANT_ID = uuid.UUID("244beeec-fedc-452e-8054-317e45557d4d")  # Guramrit
ZIPCODE = "140412"

CATEGORIES = [
    {
        "name": "Plumbing", "slug": "plumbing",
        "group": {"code": "plumbing_services", "name": "Plumbing Services", "slug": "plumbing_services"},
        "services": [
            {"name": "Pipe Repair", "slug": "pipe-repair", "job_type": "repair", "base_price": 60.0,
             "min_price": 400.0, "max_price": 900.0, "requires_issue_type": True},
            {"name": "Drain Unblocking", "slug": "drain-unblocking", "job_type": "service", "base_price": 45.0,
             "min_price": 300.0, "max_price": 700.0, "requires_issue_type": False},
        ],
    },
    {
        "name": "Electrical", "slug": "electrical",
        "group": {"code": "electrical_services", "name": "Electrical Services", "slug": "electrical_services"},
        "services": [
            {"name": "Electrical Fault Fix", "slug": "electrical-fault-fix", "job_type": "repair", "base_price": 70.0,
             "min_price": 350, "max_price": 800, "requires_issue_type": True},
            {"name": "Fan & Light Installation", "slug": "fan-light-installation", "job_type": "installation", "base_price": 40.0,
             "min_price": 250, "max_price": 600, "requires_issue_type": False},
        ],
    },
    {
        "name": "Painting", "slug": "painting",
        "group": {"code": "painting_services", "name": "Painting Services", "slug": "painting_services"},
        "services": [
            {"name": "Interior Wall Painting", "slug": "interior-wall-painting", "job_type": "service", "base_price": 200.0,
             "min_price": 3000, "max_price": 8000, "requires_issue_type": False},
        ],
    },
    {
        "name": "Pest Control", "slug": "pest-control",
        "group": {"code": "pest_control_services", "name": "Pest Control Services", "slug": "pest_control_services"},
        "services": [
            {"name": "General Pest Control", "slug": "general-pest-control", "job_type": "service", "base_price": 90.0,
             "min_price": 800, "max_price": 1800, "requires_issue_type": False},
        ],
    },
    {
        "name": "Home Cleaning", "slug": "home-cleaning",
        "group": {"code": "home_cleaning_services", "name": "Home Cleaning Services", "slug": "home_cleaning_services"},
        "services": [
            {"name": "Regular Home Cleaning", "slug": "regular-home-cleaning", "job_type": "service", "base_price": 50.0,
             "min_price": 500, "max_price": 1200, "requires_issue_type": False},
            {"name": "Full Home Deep Clean", "slug": "full-home-deep-clean", "job_type": "service", "base_price": 120.0,
             "min_price": 1500, "max_price": 3500, "requires_issue_type": False},
        ],
    },
]


async def run():
    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as db:
        area = (await db.execute(
            select(TenantServiceArea).where(
                TenantServiceArea.tenant_id == TENANT_ID,
                TenantServiceArea.zipcode == ZIPCODE,
            )
        )).scalars().first()
        if not area:
            print(f"[FAIL] No tenant_service_area for tenant={TENANT_ID} zipcode={ZIPCODE} — aborting.")
            return
        print(f"[OK] Using tenant_service_area {area.id} (zipcode={area.zipcode})")

        cat_created = cat_skipped = 0
        grp_created = grp_skipped = 0
        ms_created = ms_skipped = 0
        ts_created = ts_skipped = 0
        tsas_created = tsas_skipped = 0

        for idx, cdata in enumerate(CATEGORIES):
            cat = (await db.execute(select(ServiceCategory).where(ServiceCategory.slug == cdata["slug"]))).scalar_one_or_none()
            if not cat:
                cat = ServiceCategory(
                    name=cdata["name"], slug=cdata["slug"], description=f"{cdata['name']} services",
                    display_order=idx + 1, is_active=True, customer_flow_type="service_booking",
                    is_provider_registerable=True, is_customer_visible=True,
                    vertical_type="home_services", finance_model="security_deposit_plus_credit_wallet",
                    provider_business_model="service_provider",
                    requires_location=True, requires_schedule=False, requires_brand=False,
                    requires_service_option=False, requires_issue_type=False,
                    tenant_selectable=True, pricing_supported=True,
                )
                db.add(cat)
                await db.flush()
                print(f"[CREATE] category: {cdata['name']}")
                cat_created += 1
            else:
                print(f"[SKIP]   category: {cdata['name']} (already exists)")
                cat_skipped += 1

            gdata = cdata["group"]
            grp = (await db.execute(select(ServiceGroup).where(ServiceGroup.code == gdata["code"]))).scalar_one_or_none()
            if not grp:
                grp = ServiceGroup(
                    category_id=cat.id, code=gdata["code"], name=gdata["name"], slug=gdata["slug"],
                    display_order=0, status="active",
                )
                db.add(grp)
                await db.flush()
                print(f"[CREATE] group: {gdata['name']}")
                grp_created += 1
            else:
                print(f"[SKIP]   group: {gdata['name']} (already exists)")
                grp_skipped += 1

            for sdata in cdata["services"]:
                ms = (await db.execute(select(MasterService).where(MasterService.slug == sdata["slug"]))).scalar_one_or_none()
                if not ms:
                    ms = MasterService(
                        category_id=cat.id, service_group_id=grp.id,
                        service_name=sdata["name"], slug=sdata["slug"],
                        job_type=sdata["job_type"], pricing_model="fixed",
                        base_price=sdata["base_price"],
                        requires_address=True, is_brand_required=False, is_type_required=False,
                        requires_issue_type=sdata["requires_issue_type"], requires_schedule=False,
                        is_active=True,
                    )
                    db.add(ms)
                    await db.flush()
                    print(f"  [CREATE] master_service: {sdata['name']}")
                    ms_created += 1
                else:
                    print(f"  [SKIP]   master_service: {sdata['name']} (already exists)")
                    ms_skipped += 1

                ts = (await db.execute(select(TenantService).where(
                    TenantService.tenant_id == TENANT_ID, TenantService.master_service_id == ms.id,
                ))).scalar_one_or_none()
                if not ts:
                    ts = TenantService(
                        tenant_id=TENANT_ID, master_service_id=ms.id, category_id=cat.id,
                        job_type=sdata["job_type"], is_enabled=True,
                        tenant_min_price=sdata["min_price"], tenant_max_price=sdata["max_price"],
                        override_allowed=True, requires_brand=False, requires_type=False,
                        is_active=True, setup_status="published",
                        published_at=datetime.now(timezone.utc),
                        type_coverage_mode="all", brand_coverage_mode="all",
                    )
                    db.add(ts)
                    await db.flush()
                    print(f"  [CREATE] tenant_service (Guramrit): {sdata['name']}")
                    ts_created += 1
                else:
                    print(f"  [SKIP]   tenant_service (Guramrit): {sdata['name']} (already exists)")
                    ts_skipped += 1

                tsas = (await db.execute(select(TenantServiceAreaService).where(
                    TenantServiceAreaService.tenant_service_area_id == area.id,
                    TenantServiceAreaService.service_id == ms.id,
                    TenantServiceAreaService.job_type == sdata["job_type"],
                ))).scalar_one_or_none()
                if not tsas:
                    tsas = TenantServiceAreaService(
                        tenant_service_area_id=area.id, tenant_id=TENANT_ID,
                        service_id=ms.id, job_type=sdata["job_type"], is_available=True,
                        min_price=sdata["min_price"], max_price=sdata["max_price"],
                        base_price=sdata["base_price"], status="ACTIVE",
                    )
                    db.add(tsas)
                    print(f"  [CREATE] tenant_service_area_service (140412): {sdata['name']}")
                    tsas_created += 1
                else:
                    print(f"  [SKIP]   tenant_service_area_service (140412): {sdata['name']} (already exists)")
                    tsas_skipped += 1

        await db.commit()

    await engine.dispose()
    print(
        f"\nDone — categories(created={cat_created},skipped={cat_skipped}) "
        f"groups(created={grp_created},skipped={grp_skipped}) "
        f"master_services(created={ms_created},skipped={ms_skipped}) "
        f"tenant_services(created={ts_created},skipped={ts_skipped}) "
        f"tenant_service_area_services(created={tsas_created},skipped={tsas_skipped})"
    )


if __name__ == "__main__":
    asyncio.run(run())
