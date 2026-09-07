"""One-off consolidation: merge the 4 separately-created "AC ..." service
families (AC Repair, AC Installation, AC Maintenance / Servicing, AC Gas
Refill) into a single "Air Conditioner" family with 4 job types attached,
matching the new Job-Type Blueprint model (one family, many job types)
instead of the old one-family-per-job-type convention.

Confirmed before writing this script (see chat transcript):
  - Zero tenant_services rows reference any of the 4 source families --
    this is pure unused admin catalog configuration, no live tenant/booking
    impact either way.
  - AC Installation already carries 3 job types (Installation, Repair,
    Maintenance); the Repair and Maintenance links are EMPTY STUBS (0
    checklist mappings, 0 issue types beyond none, 0 option mappings) while
    the real content lives on the separate "AC Repair" and "AC Maintenance /
    Servicing" families.
  - "AC Maintenance / Servicing" and "AC Gas Refill" both use the generic
    "service" job type key. Per explicit user decision, they are merged into
    one "Service" job type on the survivor, using the pre-existing generic
    "AC Service - Job Completion" checklist template (not either family's
    task-specific one -- those are real, different technician tasks and
    forcing both onto every job would be wrong) as that job type's checklist.
  - Type/brand mappings (Cassette/Split/Tower/Window AC; the same 11 brand
    IDs) are IDENTICAL across all 4 families -- confirmed by exact ID-set
    comparison, not just counts. The survivor's own copies are kept; the
    source families' copies are left to die with them (no unique data).

Dry-run by default; pass --execute to apply. Always take a fresh pg_dump
backup before running with --execute.
"""
from __future__ import annotations

import argparse
import asyncio
import logging

from sqlalchemy import text

logging.disable(logging.INFO)

SURVIVOR_ID = "8d1d88ee-9c23-47cf-90e8-85a88555a09b"          # AC Installation -> "Air Conditioner"
AC_REPAIR_ID = "4ec8428f-9c0e-4f65-8464-714244ed19b3"
AC_MAINTENANCE_ID = "b829d93f-f172-45fe-9688-63c60cfc771c"
AC_GAS_REFILL_ID = "0da454db-6511-4e1d-8154-dbc392bb780b"

SURVIVOR_STUB_REPAIR_LINK = "0084f17b-3045-4298-be3e-0a1a7f7787a0"       # empty, to delete
SURVIVOR_STUB_MAINTENANCE_LINK = "4a5b89f7-3f27-4dc8-badb-bb4b787db6d9"  # empty, to delete

AC_REPAIR_LINK = "90bf596a-ca5a-4fa8-b546-8c227689ac03"          # rich, repoint onto survivor
AC_GAS_REFILL_LINK = "4e4c31ea-94d3-41f7-9a0e-a11c006cb77f"      # rich, repoint onto survivor (stays "service")
AC_MAINTENANCE_LINK = "3ab1ddbf-63cb-4762-9bf7-650fa55a8e6f"     # rich, content moves then link is deleted

# The pre-existing, currently-inactive generic checklist mapping row already
# sitting on the Gas Refill link, referencing "AC Service - Job Completion".
GENERIC_CHECKLIST_MAPPING_ON_GAS_REFILL_LINK = "55bc953d-10e7-4043-bb31-bc8d3ea7df8b"
GAS_REFILL_SPECIFIC_ACTIVE_MAPPING = "1af27ffd-82db-4cc8-ab70-4a5ac0cac612"

OVERLAPPING_QUESTION_KEYS = {"ac_type", "brand"}


async def run(execute: bool) -> None:
    from app.database import init_db, get_session_factory
    await init_db()
    factory = get_session_factory()
    async with factory() as db:
        report: list[str] = []

        # ── 1. Rename survivor ──────────────────────────────────────────
        report.append("Rename AC Installation -> 'Air Conditioner'")
        if execute:
            await db.execute(text(
                "UPDATE master_services SET service_name='Air Conditioner', updated_at=now() WHERE id=:sid"
            ), {"sid": SURVIVOR_ID})

        # ── 2. Delete the two empty stub job-type links on the survivor ─
        for label, link_id in [("repair", SURVIVOR_STUB_REPAIR_LINK), ("maintenance", SURVIVOR_STUB_MAINTENANCE_LINK)]:
            count = (await db.execute(text(
                "SELECT count(*) FROM job_type_checklist_mappings WHERE master_service_job_type_id=:lid"
            ), {"lid": link_id})).scalar()
            report.append(f"Delete empty stub '{label}' link {link_id} (checklist_mappings on it: {count}, expected 0)")
            assert count == 0, f"Stub link {link_id} is not actually empty -- aborting, re-investigate."
            if execute:
                await db.execute(text("DELETE FROM master_service_job_types WHERE id=:lid"), {"lid": link_id})

        # ── 3. Repoint AC Repair's rich 'repair' link onto the survivor ──
        report.append(f"Repoint AC Repair job-type link {AC_REPAIR_LINK} -> master_service_id=survivor")
        if execute:
            await db.execute(text(
                "UPDATE master_service_job_types SET master_service_id=:sid WHERE id=:lid"
            ), {"sid": SURVIVOR_ID, "lid": AC_REPAIR_LINK})

        # Move AC Repair's master_service-scoped config onto the survivor.
        for table in ["master_issue_types", "service_option_mappings", "catalog_questions", "service_pricing_rules"]:
            count = (await db.execute(text(
                f"SELECT count(*) FROM {table} WHERE master_service_id=:sid"
            ), {"sid": AC_REPAIR_ID})).scalar()
            report.append(f"Move {count} row(s) from {table} (AC Repair) -> survivor")
            if execute and count:
                await db.execute(text(
                    f"UPDATE {table} SET master_service_id=:new WHERE master_service_id=:old"
                ), {"new": SURVIVOR_ID, "old": AC_REPAIR_ID})

        # ── 4. Repoint AC Gas Refill's rich 'service' link onto survivor ─
        report.append(f"Repoint AC Gas Refill job-type link {AC_GAS_REFILL_LINK} -> master_service_id=survivor (job_type stays 'service')")
        if execute:
            await db.execute(text(
                "UPDATE master_service_job_types SET master_service_id=:sid WHERE id=:lid"
            ), {"sid": SURVIVOR_ID, "lid": AC_GAS_REFILL_LINK})

        # Move AC Gas Refill's questions/issue types onto the survivor first
        # (it has no overlapping question_keys with anything already there).
        for table in ["master_issue_types", "catalog_questions", "service_option_mappings", "service_pricing_rules"]:
            count = (await db.execute(text(
                f"SELECT count(*) FROM {table} WHERE master_service_id=:sid"
            ), {"sid": AC_GAS_REFILL_ID})).scalar()
            report.append(f"Move {count} row(s) from {table} (AC Gas Refill) -> survivor")
            if execute and count:
                await db.execute(text(
                    f"UPDATE {table} SET master_service_id=:new WHERE master_service_id=:old"
                ), {"new": SURVIVOR_ID, "old": AC_GAS_REFILL_ID})

        # ── 5. Merge AC Maintenance / Servicing's content into the survivor,
        #        then delete its now-redundant job-type link ──────────────
        maint_issue_types = (await db.execute(text(
            "SELECT count(*) FROM master_issue_types WHERE master_service_id=:sid"
        ), {"sid": AC_MAINTENANCE_ID})).scalar()
        report.append(f"Move {maint_issue_types} issue type(s) from AC Maintenance/Servicing -> survivor (no key conflicts)")
        if execute and maint_issue_types:
            await db.execute(text(
                "UPDATE master_issue_types SET master_service_id=:new WHERE master_service_id=:old"
            ), {"new": SURVIVOR_ID, "old": AC_MAINTENANCE_ID})

        maint_questions = (await db.execute(text(
            "SELECT question_key FROM catalog_questions WHERE master_service_id=:sid"
        ), {"sid": AC_MAINTENANCE_ID})).fetchall()
        for (qkey,) in maint_questions:
            if qkey in OVERLAPPING_QUESTION_KEYS:
                report.append(f"Delete AC Maintenance/Servicing's duplicate question '{qkey}' (survivor already has one from Gas Refill)")
                if execute:
                    await db.execute(text(
                        "DELETE FROM catalog_questions WHERE master_service_id=:sid AND question_key=:qkey"
                    ), {"sid": AC_MAINTENANCE_ID, "qkey": qkey})
            else:
                report.append(f"Move AC Maintenance/Servicing's unique question '{qkey}' -> survivor")
                if execute:
                    await db.execute(text(
                        "UPDATE catalog_questions SET master_service_id=:new WHERE master_service_id=:old AND question_key=:qkey"
                    ), {"new": SURVIVOR_ID, "old": AC_MAINTENANCE_ID, "qkey": qkey})

        report.append(f"Delete AC Maintenance/Servicing's now-redundant job-type link {AC_MAINTENANCE_LINK} "
                       "(its content is now on the survivor's Gas-Refill-turned-'Service' link; its own "
                       "checklist mappings and blueprint version are left with the archived family)")
        if execute:
            await db.execute(text(
                "DELETE FROM job_type_checklist_mappings WHERE master_service_job_type_id=:lid"
            ), {"lid": AC_MAINTENANCE_LINK})
            await db.execute(text("DELETE FROM master_service_job_types WHERE id=:lid"), {"lid": AC_MAINTENANCE_LINK})

        # ── 6. Checklist for the merged 'Service' job type: use the
        #        pre-existing generic template, per explicit user decision ─
        report.append("Deactivate Gas Refill's task-specific active checklist mapping "
                       f"{GAS_REFILL_SPECIFIC_ACTIVE_MAPPING} ('AC Gas Refill - Job Completion')")
        if execute:
            await db.execute(text(
                "UPDATE job_type_checklist_mappings SET status='inactive', updated_at=now() WHERE id=:mid"
            ), {"mid": GAS_REFILL_SPECIFIC_ACTIVE_MAPPING})

        report.append("Activate the pre-existing generic checklist mapping "
                       f"{GENERIC_CHECKLIST_MAPPING_ON_GAS_REFILL_LINK} ('AC Service - Job Completion'), "
                       "phase EXECUTION to match the platform's active-mapping convention")
        if execute:
            await db.execute(text(
                "UPDATE job_type_checklist_mappings SET status='active', phase='EXECUTION', updated_at=now() WHERE id=:mid"
            ), {"mid": GENERIC_CHECKLIST_MAPPING_ON_GAS_REFILL_LINK})

        # ── 7. Archive the 3 now-empty source families (soft delete) ─────
        for name, sid in [("AC Repair", AC_REPAIR_ID), ("AC Maintenance / Servicing", AC_MAINTENANCE_ID),
                           ("AC Gas Refill", AC_GAS_REFILL_ID)]:
            report.append(f"Archive '{name}' ({sid}): is_active=false, name suffixed '[Merged into Air Conditioner]'")
            if execute:
                await db.execute(text(
                    "UPDATE master_services SET is_active=false, "
                    "service_name = service_name || ' [Merged into Air Conditioner]', updated_at=now() "
                    "WHERE id=:sid"
                ), {"sid": sid})

        for line in report:
            print(("[EXECUTE] " if execute else "[DRY RUN] ") + line)

        if execute:
            await db.commit()
            print("\nCommitted.")
        else:
            await db.rollback()
            print("\nDry run only -- nothing written. Re-run with --execute to apply.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true", help="Actually apply the changes (default: dry run)")
    args = parser.parse_args()
    asyncio.run(run(execute=args.execute))
