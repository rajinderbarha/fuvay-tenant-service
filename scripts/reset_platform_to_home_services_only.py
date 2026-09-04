"""Reset the platform to a clean Home-Services-only state.

Removes ALL provider/tenant business data (providers, jobs, technicians,
complaints, reviews, seat/credit plans, and everything else keyed to a
tenant_id or to a non-Home-Services category_id), while leaving two things
completely untouched:

  * The engine/module registry -- catalog_module_definitions,
    vertical_catalog_modules, verticals. These tables have neither a
    tenant_id nor a category_id column (verified before writing this
    script), so the sweeps below cannot reach them structurally, not just
    by convention.
  * The Home Services catalog itself -- master_services, service_groups,
    service_types, brands, master_issue_types, checklists, etc. for the
    ONE category whose vertical_type = 'home_services'. Everything under
    every OTHER category is removed along with that category row.

What gets deleted, precisely:
  1. Every tenant (provider), and every row in every table that has a
     tenant_id column pointing at one -- jobs, bookings, technicians
     (provider_team_members), complaints, reviews, seat/credit plans
     (tenant_topup_entitlements), the usage credit ledger, audit logs,
     everything tenant-scoped. Same generic sweep technique proven in
     scripts/-adjacent cleanup work this session: iterate every tenant_id
     column, delete matching rows, repeat passes until nothing more can be
     deleted (handles FK ordering without hardcoding table order).
  2. Every service_categories row except vertical_type = 'home_services',
     and every row in every OTHER table with a category_id column that
     points at one of those categories (master_services, service_groups,
     brands, service_types, master_issue_types, checklists, etc. for the
     13 non-Home-Services verticals). Same generic sweep technique, keyed
     on category_id instead of tenant_id.

Idempotent to run twice: the second run finds nothing left to delete.

Safety:
  * DRY RUN BY DEFAULT. Reports exactly what would be deleted and exits.
    Pass --execute to actually delete.
  * No environment/production-URL guard: this script is meant to run
    against production too (it is the platform reset, not test-fixture
    seeding). Take your own backup before --execute -- this is genuinely
    irreversible.

Run:
  python scripts/reset_platform_to_home_services_only.py            # dry run
  python scripts/reset_platform_to_home_services_only.py --execute  # for real
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql+asyncpg://serviceos:serviceos@localhost:5432/serviceos"
)

KEEP_VERTICAL = "home_services"


async def _tables_with_column(db: AsyncSession, column: str, exclude: set[str]) -> list[str]:
    rows = (await db.execute(text(
        "SELECT DISTINCT c.table_name FROM information_schema.columns c "
        "JOIN information_schema.tables t "
        "  ON t.table_name = c.table_name AND t.table_schema = c.table_schema "
        "WHERE c.table_schema = 'public' AND t.table_type = 'BASE TABLE' "
        "  AND c.column_name = :col"
    ), {"col": column})).all()
    return sorted(r[0] for r in rows if r[0] not in exclude)


async def _sweep(
    db: AsyncSession, tables: list[str], column: str, id_source_sql: str, label: str, execute: bool,
) -> dict[str, int]:
    """Repeatedly delete rows in `tables` whose `column` matches `id_source_sql`,
    passing over the list until a full pass deletes nothing (handles FK order
    between the swept tables themselves without hardcoding it)."""
    counts: dict[str, int] = {}
    remaining = list(tables)
    verb = "DELETE FROM" if execute else "SELECT count(*) FROM"
    for _pass in range(8):
        if not remaining:
            break
        still: list[str] = []
        progressed = False
        for table in remaining:
            sql = (
                f"{verb} public.\"{table}\" x WHERE x.{column} IN ({id_source_sql})"
                if execute else
                f"SELECT count(*) FROM public.\"{table}\" x WHERE x.{column} IN ({id_source_sql})"
            )
            try:
                result = await db.execute(text(sql))
                if execute:
                    n = result.rowcount or 0
                else:
                    n = result.scalar() or 0
                if n:
                    counts[table] = counts.get(table, 0) + n
                    progressed = progressed or execute
            except Exception as e:  # FK violation on this pass -- retry later
                if execute:
                    await db.rollback()
                still.append(table)
                continue
        remaining = still if execute else []  # dry run never needs retries (no mutation, no FK errors)
        if execute and not progressed and still:
            # Nothing more will succeed by retrying the same set -- these are
            # genuine constraint issues (RESTRICT with rows we don't know
            # about), not ordering. Report and stop.
            break
    if execute and remaining:
        print(f"  [WARN] {label}: could not clear (constraint?): {', '.join(remaining)}")
    return counts


async def run(execute: bool) -> None:
    engine = create_async_engine(DATABASE_URL, echo=False)
    Session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with Session() as db:
        mode = "EXECUTING" if execute else "DRY RUN"
        print(f"=== {mode} — reset platform to Home-Services-only ===\n")

        tenant_count = (await db.execute(text("SELECT count(*) FROM tenants"))).scalar()
        other_cat_count = (await db.execute(text(
            "SELECT count(*) FROM service_categories WHERE vertical_type <> :k"
        ), {"k": KEEP_VERTICAL})).scalar()
        print(f"Tenants to remove: {tenant_count}")
        print(f"Non-Home-Services categories to remove: {other_cat_count}\n")

        # ── 1. Every tenant-scoped table ────────────────────────────────
        tenant_tables = await _tables_with_column(db, "tenant_id", exclude={"tenants"})
        print(f"-- Sweeping {len(tenant_tables)} tenant-scoped tables (jobs, bookings, "
              f"technicians, complaints, reviews, seat/credit plans, audit logs, ...)")
        counts = await _sweep(
            db, tenant_tables, "tenant_id", "SELECT id FROM tenants", "tenant sweep", execute,
        )
        for table, n in sorted(counts.items()):
            print(f"  {table}: {n}")
        if execute:
            await db.commit()

        # ── 2. The tenants themselves ───────────────────────────────────
        if execute:
            result = await db.execute(text("DELETE FROM tenants"))
            print(f"\ntenants: {result.rowcount}")
            await db.commit()
        else:
            print(f"\ntenants: {tenant_count} (would delete)")

        # ── 3. Every table with a category_id pointing at a removed category ─
        category_tables = await _tables_with_column(db, "category_id", exclude={"service_categories"})
        non_home_cat_sql = f"SELECT id FROM service_categories WHERE vertical_type <> '{KEEP_VERTICAL}'"
        print(f"\n-- Sweeping {len(category_tables)} category-scoped tables for the "
              f"{other_cat_count} non-Home-Services categories (their master_services, "
              f"service_groups, brands, service_types, checklists, ...)")
        counts2 = await _sweep(
            db, category_tables, "category_id", non_home_cat_sql, "category sweep", execute,
        )
        for table, n in sorted(counts2.items()):
            if n:
                print(f"  {table}: {n}")
        if execute:
            await db.commit()

        # ── 4. The non-Home-Services categories themselves ──────────────
        if execute:
            result = await db.execute(text(
                "DELETE FROM service_categories WHERE vertical_type <> :k"
            ), {"k": KEEP_VERTICAL})
            print(f"\nservice_categories (non-home_services): {result.rowcount}")
            await db.commit()
        else:
            print(f"\nservice_categories (non-home_services): {other_cat_count} (would delete)")

        # ── 5. Pre-existing dangling category_id references ─────────────
        # Not caused by this script -- rows already pointing at a category id
        # that does not exist at all, left over from earlier, unrelated
        # cleanup in this codebase's history (e.g. duplicate junk
        # master_services rows named "AC" pointing nowhere). Caught by the
        # same table set, keyed on "no matching category exists" rather than
        # "category is non-home".
        print(f"\n-- Sweeping pre-existing rows whose category_id matches no category at all")
        counts3: dict[str, int] = {}
        for table in category_tables:
            verb = "DELETE FROM" if execute else "SELECT count(*) FROM"
            sql = (
                f'{verb} public."{table}" x WHERE x.category_id IS NOT NULL '
                f'AND NOT EXISTS (SELECT 1 FROM service_categories sc WHERE sc.id = x.category_id)'
            )
            try:
                result = await db.execute(text(sql))
                n = (result.rowcount or 0) if execute else (result.scalar() or 0)
                if n:
                    counts3[table] = n
            except Exception:
                if execute:
                    await db.rollback()
        for table, n in sorted(counts3.items()):
            print(f"  {table}: {n}")
        if execute:
            await db.commit()

        # ── Verify ───────────────────────────────────────────────────────
        remaining_cats = (await db.execute(text(
            "SELECT vertical_type FROM service_categories ORDER BY 1"
        ))).scalars().all()
        remaining_tenants = (await db.execute(text("SELECT count(*) FROM tenants"))).scalar()
        print(f"\n{'=' * 60}")
        print(f"service_categories remaining: {remaining_cats}")
        print(f"tenants remaining: {remaining_tenants}")
        print("Untouched by design: catalog_module_definitions, vertical_catalog_modules, "
              "verticals (the engine/module registry), and every master_services / "
              "service_groups / brands / service_types / master_issue_types / checklists "
              "row still under the home_services category.")

    await engine.dispose()
    if not execute:
        print("\nThis was a DRY RUN. Nothing was deleted. Re-run with --execute to apply.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--execute", action="store_true", help="Actually delete (default is dry run).")
    args = ap.parse_args()
    asyncio.run(run(args.execute))
