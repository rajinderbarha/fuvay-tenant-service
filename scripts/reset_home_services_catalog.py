"""One-off: wipe every Home Services service group / master service / job
type attachment / checklist / question / issue type EXCEPT the "Air
Conditioner" family (already rebuilt and clean), so the catalog can be
re-seeded with real, complete data from scratch. Keeps: the "Home Services"
category itself, the global Types & Brands libraries (Split AC, LG, etc --
legitimate, reusable), the "Air Conditioner" family and its own checklist
templates, and the 9 real runtime-supported job types (repair/installation/
uninstallation/inspection/maintenance/cleaning/consultation/service/custom).
Also deletes the junk duplicate "Repair" job types left over from earlier
ad-hoc testing (repair_<hash> keys, not runtime-supported).

Confirmed before writing this: zero tenant_services rows reference ANY
Home Services master_service_id (checked live), so this has no tenant-
facing impact. Dry-run by default; pass --execute to apply. Always take a
fresh pg_dump backup before running with --execute.
"""
from __future__ import annotations

import argparse
import asyncio
import logging

from sqlalchemy import text

logging.disable(logging.INFO)

KEEP_MASTER_SERVICE_ID = "8d1d88ee-9c23-47cf-90e8-85a88555a09b"  # Air Conditioner


async def run(execute: bool) -> None:
    from app.database import init_db, get_session_factory
    await init_db()
    factory = get_session_factory()
    async with factory() as db:
        report: list[str] = []

        doomed = [r[0] for r in (await db.execute(text(
            "SELECT ms.id FROM master_services ms "
            "JOIN service_groups sg ON sg.id = ms.service_group_id "
            "JOIN service_categories sc ON sc.id = sg.category_id "
            "WHERE sc.slug='home_services' AND ms.id != :keep"
        ), {"keep": KEEP_MASTER_SERVICE_ID})).fetchall()]
        report.append(f"Doomed master_services: {len(doomed)} (keeping Air Conditioner)")

        keep_template_names = [r[0] for r in (await db.execute(text("""
            SELECT DISTINCT ct.name FROM job_type_checklist_mappings jcm
            JOIN master_service_job_types msjt ON msjt.id = jcm.master_service_job_type_id
            JOIN checklist_template_versions ctv ON ctv.id = jcm.checklist_template_version_id
            JOIN checklist_templates ct ON ct.id = ctv.checklist_template_id
            WHERE msjt.master_service_id = :keep
        """), {"keep": KEEP_MASTER_SERVICE_ID})).fetchall()]
        report.append(f"Checklist templates kept (used by Air Conditioner): {keep_template_names}")

        if not doomed:
            report.append("Nothing to delete.")
            for line in report:
                print(("[EXECUTE] " if execute else "[DRY RUN] ") + line)
            return

        # 1. Checklist mappings on doomed services' job-type links.
        count = (await db.execute(text(
            "SELECT count(*) FROM job_type_checklist_mappings WHERE master_service_job_type_id IN "
            "(SELECT id FROM master_service_job_types WHERE master_service_id = ANY(:ids))"
        ), {"ids": doomed})).scalar()
        report.append(f"Delete {count} job_type_checklist_mappings")
        if execute:
            await db.execute(text(
                "DELETE FROM job_type_checklist_mappings WHERE master_service_job_type_id IN "
                "(SELECT id FROM master_service_job_types WHERE master_service_id = ANY(:ids))"
            ), {"ids": doomed})

        # 2. Checklist templates/versions/sections/items not used by Air Conditioner.
        tmpl_count = (await db.execute(text(
            "SELECT count(*) FROM checklist_templates WHERE name != ALL(:keep)"
        ), {"keep": keep_template_names})).scalar()
        report.append(f"Delete {tmpl_count} checklist_templates (and their versions/sections/items)")
        if execute:
            await db.execute(text("""
                DELETE FROM checklist_items WHERE checklist_section_id IN (
                    SELECT cs.id FROM checklist_sections cs
                    JOIN checklist_template_versions ctv ON ctv.id = cs.checklist_template_version_id
                    JOIN checklist_templates ct ON ct.id = ctv.checklist_template_id
                    WHERE ct.name != ALL(:keep))
            """), {"keep": keep_template_names})
            await db.execute(text("""
                DELETE FROM checklist_sections WHERE checklist_template_version_id IN (
                    SELECT ctv.id FROM checklist_template_versions ctv
                    JOIN checklist_templates ct ON ct.id = ctv.checklist_template_id
                    WHERE ct.name != ALL(:keep))
            """), {"keep": keep_template_names})
            await db.execute(text("""
                DELETE FROM checklist_template_versions WHERE checklist_template_id IN (
                    SELECT id FROM checklist_templates WHERE name != ALL(:keep))
            """), {"keep": keep_template_names})
            await db.execute(text("DELETE FROM checklist_templates WHERE name != ALL(:keep)"), {"keep": keep_template_names})

        # 3. Catalog questions + their options/rules for doomed services.
        for table, col in [
            ("catalog_question_options", None), ("catalog_question_rules", None),
        ]:
            pass  # handled via question_id subquery below
        qcount = (await db.execute(text(
            "SELECT count(*) FROM catalog_questions WHERE master_service_id = ANY(:ids)"
        ), {"ids": doomed})).scalar()
        report.append(f"Delete {qcount} catalog_questions (+ their options/rules)")
        if execute:
            await db.execute(text(
                "DELETE FROM catalog_question_options WHERE question_id IN "
                "(SELECT id FROM catalog_questions WHERE master_service_id = ANY(:ids))"
            ), {"ids": doomed})
            await db.execute(text(
                "DELETE FROM catalog_question_rules WHERE question_id IN "
                "(SELECT id FROM catalog_questions WHERE master_service_id = ANY(:ids))"
            ), {"ids": doomed})
            await db.execute(text("DELETE FROM catalog_questions WHERE master_service_id = ANY(:ids)"), {"ids": doomed})

        # 4. Issue type mappings + the global issue type rows they exclusively reference.
        icount = (await db.execute(text(
            "SELECT count(*) FROM service_issue_mappings WHERE master_service_id = ANY(:ids)"
        ), {"ids": doomed})).scalar()
        report.append(f"Delete {icount} service_issue_mappings")
        if execute:
            await db.execute(text("DELETE FROM service_issue_mappings WHERE master_service_id = ANY(:ids)"), {"ids": doomed})
        mcount = (await db.execute(text(
            "SELECT count(*) FROM master_issue_types WHERE master_service_id = ANY(:ids)"
        ), {"ids": doomed})).scalar()
        report.append(f"Delete {mcount} master_issue_types directly scoped to doomed services")
        if execute:
            await db.execute(text("DELETE FROM master_issue_types WHERE master_service_id = ANY(:ids)"), {"ids": doomed})
        # Global (unscoped) issue types no longer referenced by ANY mapping (orphaned by the deletes above).
        orphan_count = (await db.execute(text(
            "SELECT count(*) FROM master_issue_types mit WHERE mit.master_service_id IS NULL "
            "AND NOT EXISTS (SELECT 1 FROM service_issue_mappings sim WHERE sim.issue_type_id = mit.id)"
        ))).scalar()
        report.append(f"Delete {orphan_count} orphaned global issue types (no remaining mapping)")
        if execute:
            await db.execute(text(
                "DELETE FROM master_issue_types mit WHERE mit.master_service_id IS NULL "
                "AND NOT EXISTS (SELECT 1 FROM service_issue_mappings sim WHERE sim.issue_type_id = mit.id)"
            ))

        # 5. Dimension configs, workflows, blueprint versions, type/brand mappings.
        for table, col in [
            ("service_job_dimensions", "master_service_id"),
            ("service_job_workflow", "master_service_id"),
            ("service_blueprint_versions", "master_service_id"),
            ("service_option_mappings", "master_service_id"),
            ("master_service_types", "master_service_id"),
            ("master_service_brands", "master_service_id"),
            ("master_service_job_types", "master_service_id"),
        ]:
            count = (await db.execute(text(f"SELECT count(*) FROM {table} WHERE {col} = ANY(:ids)"), {"ids": doomed})).scalar()
            report.append(f"Delete {count} rows from {table}")
            if execute:
                await db.execute(text(f"DELETE FROM {table} WHERE {col} = ANY(:ids)"), {"ids": doomed})

        # 6. The master services themselves. Service groups (the 13 folder
        # names: Plumbing, Electrical, ...) are kept -- they get repopulated
        # with fresh master services, not recreated.
        report.append(f"Delete {len(doomed)} master_services")
        if execute:
            await db.execute(text("DELETE FROM master_services WHERE id = ANY(:ids)"), {"ids": doomed})

        # 7. Junk duplicate "Repair" job types from earlier ad-hoc testing
        # (not runtime-supported, never legitimately attached to anything real).
        junk_jt = [r[0] for r in (await db.execute(text(
            "SELECT id FROM job_types WHERE \"key\" LIKE 'repair_%' AND \"key\" != 'repair'"
        ))).fetchall()]
        report.append(f"Delete {len(junk_jt)} junk duplicate job_types from earlier testing")
        if execute and junk_jt:
            await db.execute(text("DELETE FROM job_types WHERE id = ANY(:ids)"), {"ids": junk_jt})

        # 8. Stray test dimensions left over from this session's testing (not the 2 legacy ones).
        stray_dims = [r[0] for r in (await db.execute(text(
            "SELECT id FROM catalog_dimensions WHERE legacy_source IS NULL"
        ))).fetchall()]
        report.append(f"Delete {len(stray_dims)} stray test dimensions (non-legacy)")
        if execute and stray_dims:
            await db.execute(text("DELETE FROM catalog_dimension_values WHERE dimension_id = ANY(:ids)"), {"ids": stray_dims})
            await db.execute(text("DELETE FROM catalog_dimensions WHERE id = ANY(:ids)"), {"ids": stray_dims})

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
