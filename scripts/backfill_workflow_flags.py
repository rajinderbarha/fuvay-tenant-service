"""One-off: the initial seed (scripts/seed_home_services_and_computer_catalog.py,
before this fix) only ever set pricing_behavior on each job type's workflow,
leaving every other flag (technician_required, schedule_required,
address_required, service_area_required, availability_required,
checklist_required, inspection_required, quote_approval_required) at its
False default. Every job type this catalog created is a real on-site
technician visit -- those must be on, or the booking flow never actually
enforces scheduling/address/service-area/technician assignment.

Backfills every job type under the "Home Services" and "Computer & IT
Services" categories using each job type's OWN already-saved
pricing_behavior (read from its current workflow row) to derive
inspection_required / quote_approval_required, exactly matching the logic
in the fixed seed script. Idempotent -- safe to run more than once (a
job type whose flags already match the target is a no-op, per
set_workflow's own change-detection).
"""
from __future__ import annotations

import asyncio
import logging

logging.disable(logging.INFO)


async def run():
    from sqlalchemy import select
    from app.database import init_db, get_session_factory
    from app.engines.admin_catalog.job_type_blueprint_service import JobTypeBlueprintService
    from app.engines.admin_catalog.models import (
        MasterServiceJobType, ServiceJobWorkflow, ServiceCategory, ServiceGroup, MasterService,
    )

    await init_db()
    factory = get_session_factory()
    async with factory() as db:
        jt_svc = JobTypeBlueprintService(db=db)

        links = (await db.execute(
            select(MasterServiceJobType, MasterService.service_name)
            .join(MasterService, MasterService.id == MasterServiceJobType.master_service_id)
            .join(ServiceGroup, ServiceGroup.id == MasterService.service_group_id)
            .join(ServiceCategory, ServiceCategory.id == ServiceGroup.category_id)
            .where(
                MasterServiceJobType.is_active.is_(True),
                ServiceCategory.slug.in_(["home_services", "computer_it_services"]),
            )
        )).all()
        print(f"Found {len(links)} active job-type links to backfill.")

        fixed = 0
        for link, service_name in links:
            current = (await db.execute(select(ServiceJobWorkflow).where(
                ServiceJobWorkflow.master_service_id == link.master_service_id,
                ServiceJobWorkflow.job_type_id == link.job_type_id,
                ServiceJobWorkflow.is_current.is_(True),
            ))).scalar_one_or_none()
            pricing_behavior = current.pricing_behavior if current else "fixed"
            result = await jt_svc.set_workflow(link.master_service_id, link.job_type_id, {
                "pricing_behavior": pricing_behavior,
                "technician_required": True, "schedule_required": True, "address_required": True,
                "service_area_required": True, "availability_required": True,
                "checklist_required": True,
                "inspection_required": pricing_behavior == "inspection_required",
                "quote_approval_required": pricing_behavior in {"inspection_required", "custom_quote"},
            })
            changed = result["version_number"] != (current.version_number if current else None)
            if changed:
                fixed += 1
                print(f"  fixed: {service_name} / {result['job_type_id']}")

        print(f"\nDone. {fixed} of {len(links)} job types needed a fix.")


if __name__ == "__main__":
    asyncio.run(run())
