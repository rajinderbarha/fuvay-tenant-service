"""Phase 2 — AC Repair baseline chain certification fix.

Seeds the missing relational data that connects the previously-orphaned
catalog entities into a real, queryable AC Repair baseline chain:

  AC Repair (master_services)
    -> Split AC (service_types)            via service_type_mappings
    -> LG       (brands)                   via brand_mappings
    -> Gas Refill      (master_service_options, NEW)  via service_option_mappings
    -> Emergency Visit  (master_service_options, NEW)  via service_option_mappings
    -> Not Cooling (master_issue_types)    already mapped via service_issue_mappings
       (seed_issue_types.py's ac_not_cooling row — left as-is; see
       PHASE_2_CATALOG_DATA_INTEGRITY_REPORT.md for the duplicate-row note
       on seed_service_options_issues.py's separate not_cooling row)

Idempotent — safe to re-run. Skips anything that already exists.
Run: python scripts/seed_ac_repair_baseline_mappings.py
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.engines.admin_catalog.models import (
    ServiceCategory, MasterService, ServiceType, ServiceTypeMapping,
    Brand, BrandMapping, MasterServiceOption, ServiceOptionMapping,
)

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://serviceos:serviceos@localhost:5432/serviceos")


async def run():
    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as db:
        cat = (await db.execute(
            select(ServiceCategory).where(ServiceCategory.slug == "home_services"))).scalar_one_or_none()
        if not cat:
            print("[FAIL] home_services category not found — run seed_universal_categories.py first")
            return

        ac_repair = (await db.execute(
            select(MasterService).where(MasterService.slug == "ac_repair"))).scalar_one_or_none()
        if not ac_repair:
            print("[FAIL] ac_repair master service not found — run seed_master_services.py first")
            return

        # ── 1. Split AC / Window AC service_types + mapping to AC Repair ──────
        for name, slug in (("Split AC", "split_ac"), ("Window AC", "window_ac")):
            st = (await db.execute(select(ServiceType).where(ServiceType.slug == slug))).scalar_one_or_none()
            if not st:
                st = ServiceType(category_id=cat.id, name=name, slug=slug, code=slug,
                                  customer_visible=True, status="active")
                db.add(st)
                await db.flush()
                print(f"[CREATE] service_type: {name}")
            else:
                print(f"[SKIP]   service_type: {name} (already exists)")

            existing_map = (await db.execute(select(ServiceTypeMapping).where(
                ServiceTypeMapping.type_id == st.id,
                ServiceTypeMapping.service_id == ac_repair.id))).scalar_one_or_none()
            if not existing_map:
                db.add(ServiceTypeMapping(
                    type_id=st.id, category_id=cat.id,
                    service_group_id=ac_repair.service_group_id, service_id=ac_repair.id,
                    customer_visible=True, provider_visible=True, status="active"))
                print(f"[CREATE] service_type_mapping: {name} -> AC Repair")
            else:
                print(f"[SKIP]   service_type_mapping: {name} -> AC Repair (already exists)")

        # ── 2. LG / Samsung / Voltas brand mappings to AC Repair ──────────────
        for slug in ("lg", "samsung", "voltas"):
            brand = (await db.execute(select(Brand).where(Brand.slug == slug))).scalar_one_or_none()
            if not brand:
                print(f"[WARN]   brand slug '{slug}' not found — run seed_brands.py first")
                continue
            existing_map = (await db.execute(select(BrandMapping).where(
                BrandMapping.brand_id == brand.id,
                BrandMapping.service_id == ac_repair.id))).scalar_one_or_none()
            if not existing_map:
                db.add(BrandMapping(
                    brand_id=brand.id, category_id=cat.id,
                    service_group_id=ac_repair.service_group_id, service_id=ac_repair.id,
                    customer_visible=True, provider_visible=True, status="active"))
                print(f"[CREATE] brand_mapping: {brand.name} -> AC Repair")
            else:
                print(f"[SKIP]   brand_mapping: {brand.name} -> AC Repair (already exists)")

        # ── 3. Gas Refill / Emergency Visit service options + mapping ─────────
        OPTIONS = [
            {"name": "Gas Refill", "slug": "ac_repair_gas_refill", "code": "GAS_REFILL",
             "option_type": "add_on", "is_required": False},
            {"name": "Emergency Visit", "slug": "ac_repair_emergency_visit", "code": "EMERGENCY_VISIT",
             "option_type": "add_on", "is_required": False},
        ]
        for odata in OPTIONS:
            opt = (await db.execute(
                select(MasterServiceOption).where(MasterServiceOption.slug == odata["slug"])
            )).scalar_one_or_none()
            if not opt:
                opt = MasterServiceOption(
                    category_id=cat.id, master_service_id=ac_repair.id,
                    code=odata["code"], name=odata["name"], slug=odata["slug"],
                    option_type=odata["option_type"], is_customer_selectable=True,
                    is_active=True, status="active")
                db.add(opt)
                await db.flush()
                print(f"[CREATE] master_service_option: {odata['name']}")
            else:
                print(f"[SKIP]   master_service_option: {odata['name']} (already exists)")

            existing_map = (await db.execute(select(ServiceOptionMapping).where(
                ServiceOptionMapping.master_service_id == ac_repair.id,
                ServiceOptionMapping.service_option_id == opt.id))).scalar_one_or_none()
            if not existing_map:
                db.add(ServiceOptionMapping(
                    master_service_id=ac_repair.id, service_option_id=opt.id,
                    status="active", is_required=odata["is_required"]))
                print(f"[CREATE] service_option_mapping: {odata['name']} -> AC Repair")
            else:
                print(f"[SKIP]   service_option_mapping: {odata['name']} -> AC Repair (already exists)")

        await db.commit()
        print("\n[DONE] AC Repair baseline mapping seed complete.")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(run())
