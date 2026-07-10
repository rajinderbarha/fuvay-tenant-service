"""HS0 — Home Services stale test-state cleanup script.

Cleans stale demo/test records that confuse a clean Home Services E2E test
pass, without touching real production-like data (this dev DB has exactly
one real tenant, "Demo AC Services", which is intentionally preserved).

Usage:
    python scripts/cleanup_home_services_test_state.py --dry-run
    python scripts/cleanup_home_services_test_state.py --apply

--dry-run (default if no flag given) prints exactly what would be deleted
and does not modify the database. --apply performs the deletion (each
target in its own transaction so one failed target does not block the
rest) and prints before/after counts.
"""
import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import text
from app.database import create_engine as get_engine

REAL_TENANT_ID = "34b427a7-b2be-496c-b826-6d51bb181248"  # "Demo AC Services" — the only real tenant, never deleted

# Each entry: (label, count_sql, delete_sql). Column/table names verified
# against the live dev schema (psql \d), not guessed.
CLEANUP_TARGETS = [
    (
        "duplicate/phantom demo tenants (tenant_name LIKE 'Demo%'/'Test%'/'%Sample%', excluding the one real seeded tenant)",
        f"""
        SELECT count(*) FROM tenants
        WHERE (tenant_name ILIKE 'Demo%' OR tenant_name ILIKE 'Test%' OR tenant_name ILIKE '%Sample%')
          AND id <> '{REAL_TENANT_ID}'
        """,
        f"""
        DELETE FROM tenants
        WHERE (tenant_name ILIKE 'Demo%' OR tenant_name ILIKE 'Test%' OR tenant_name ILIKE '%Sample%')
          AND id <> '{REAL_TENANT_ID}'
        """,
    ),
    (
        "orphan tenant_service_types (tenant_service_id not in tenant_services)",
        """
        SELECT count(*) FROM tenant_service_types tst
        WHERE NOT EXISTS (SELECT 1 FROM tenant_services ts WHERE ts.id = tst.tenant_service_id)
        """,
        """
        DELETE FROM tenant_service_types tst
        WHERE NOT EXISTS (SELECT 1 FROM tenant_services ts WHERE ts.id = tst.tenant_service_id)
        """,
    ),
    (
        "orphan tenant_service_brands (tenant_service_id not in tenant_services)",
        """
        SELECT count(*) FROM tenant_service_brands tsb
        WHERE NOT EXISTS (SELECT 1 FROM tenant_services ts WHERE ts.id = tsb.tenant_service_id)
        """,
        """
        DELETE FROM tenant_service_brands tsb
        WHERE NOT EXISTS (SELECT 1 FROM tenant_services ts WHERE ts.id = tsb.tenant_service_id)
        """,
    ),
    (
        "draft tenant_services stuck in setup_status='draft' for >30 days, excluding the real tenant",
        f"""
        SELECT count(*) FROM tenant_services
        WHERE setup_status = 'draft' AND created_at < now() - interval '30 days'
          AND tenant_id <> '{REAL_TENANT_ID}'
        """,
        f"""
        DELETE FROM tenant_services
        WHERE setup_status = 'draft' AND created_at < now() - interval '30 days'
          AND tenant_id <> '{REAL_TENANT_ID}'
        """,
    ),
    (
        "duplicate provider availability rules (exact duplicate tenant_id+day_of_week+start_time+end_time)",
        """
        SELECT count(*) FROM (
          SELECT tenant_id, day_of_week, start_time, end_time, count(*) c
          FROM provider_availability_rules
          GROUP BY tenant_id, day_of_week, start_time, end_time
          HAVING count(*) > 1
        ) dup
        """,
        """
        DELETE FROM provider_availability_rules a
        USING provider_availability_rules b
        WHERE a.id > b.id
          AND a.tenant_id = b.tenant_id
          AND a.day_of_week = b.day_of_week
          AND a.start_time = b.start_time
          AND a.end_time = b.end_time
        """,
    ),
    (
        "old test bookings stuck in draft/failed status blocking clean E2E (older than 7 days, excluding the real tenant)",
        f"""
        SELECT count(*) FROM bookings
        WHERE status IN ('draft', 'failed') AND created_at < now() - interval '7 days'
          AND tenant_id <> '{REAL_TENANT_ID}'
        """,
        f"""
        DELETE FROM bookings
        WHERE status IN ('draft', 'failed') AND created_at < now() - interval '7 days'
          AND tenant_id <> '{REAL_TENANT_ID}'
        """,
    ),
]


async def run(apply: bool) -> None:
    engine = get_engine()
    total_found = 0
    for label, count_sql, delete_sql in CLEANUP_TARGETS:
        async with engine.begin() as conn:
            try:
                result = await conn.execute(text(count_sql))
                count = result.scalar() or 0
            except Exception as e:
                print(f"[SKIP] {label}: table/column not present in this schema ({e.__class__.__name__})")
                continue

            total_found += count
            print(f"[{'APPLY' if apply else 'DRY-RUN'}] {label}: {count} row(s) found")

            if apply and count > 0:
                await conn.execute(text(delete_sql))
                print(f"         -> deleted {count} row(s)")

    print(f"\nTotal stale rows {'deleted' if apply else 'found'}: {total_found}")
    if not apply:
        print("\nDry run only — no changes made. Re-run with --apply to delete.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--dry-run", action="store_true", help="Show what would be deleted (default)")
    group.add_argument("--apply", action="store_true", help="Actually delete stale rows")
    args = parser.parse_args()

    asyncio.run(run(apply=args.apply))


if __name__ == "__main__":
    main()
