"""Phase 2 catalog certification — seed baseline master checklist items.

Idempotent — skips existing rows by slug. Seeds the 4 Phase 2 baseline
checklist items and links "Completion Note" + "Technician Diagnosis Note"
to AC Repair, satisfying the Module 8 hard gate: "AC Repair must have at
least one technician completion checklist item."

Run: python scripts/seed_checklists.py
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.engines.admin_catalog.models import ServiceCategory, MasterService, MasterChecklistItem

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://serviceos:serviceos@localhost:5432/serviceos")

ITEMS = [
    {"title": "Technician Diagnosis Note", "slug": "technician_diagnosis_note", "code": "DIAGNOSIS_NOTE",
     "owner_role": "technician", "is_required": True, "customer_visible": False,
     "link_to_ac_repair": True},
    {"title": "Before/After Service Photo", "slug": "before_after_service_photo", "code": "BEFORE_AFTER_PHOTO",
     "owner_role": "technician", "is_required": True, "customer_visible": True,
     "link_to_ac_repair": True},
    {"title": "Payment Collection Confirmation", "slug": "payment_collection_confirmation", "code": "PAYMENT_CONFIRM",
     "owner_role": "technician", "is_required": True, "customer_visible": False,
     "link_to_ac_repair": True},
    {"title": "Completion Note", "slug": "completion_note", "code": "COMPLETION_NOTE",
     "owner_role": "technician", "is_required": True, "customer_visible": False,
     "link_to_ac_repair": True},
]


async def run():
    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as db:
        cat = (await db.execute(
            select(ServiceCategory).where(ServiceCategory.slug == "home_services"))).scalar_one_or_none()
        ac_repair = (await db.execute(
            select(MasterService).where(MasterService.slug == "ac_repair"))).scalar_one_or_none()
        if not cat or not ac_repair:
            print("[FAIL] home_services category or ac_repair service not found — "
                  "run seed_universal_categories.py + seed_master_services.py first")
            return

        for idx, item in enumerate(ITEMS):
            existing = (await db.execute(
                select(MasterChecklistItem).where(MasterChecklistItem.slug == item["slug"]))).scalar_one_or_none()
            if existing:
                print(f"[SKIP]   checklist: {item['title']} (already exists)")
                continue
            row = MasterChecklistItem(
                category_id=cat.id,
                master_service_id=ac_repair.id if item.get("link_to_ac_repair") else None,
                code=item["code"], title=item["title"], slug=item["slug"],
                is_required=item["is_required"], owner_role=item["owner_role"],
                customer_visible=item["customer_visible"], staff_visible=True, tenant_visible=True,
                is_active=True, status="active", display_order=idx,
            )
            db.add(row)
            print(f"[CREATE] checklist: {item['title']} -> AC Repair")

        await db.commit()
        print("\n[DONE] Checklist baseline seed complete.")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(run())
