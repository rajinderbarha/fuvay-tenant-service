"""
One-time cleanup: remove all test/demo/seed data from the database.

KEEPS:
  Tenants: barha auto store, fuvay, gur amrit (and any future non-test tenants)
  Users:   any user with a real email (not @serviceos.local/.in/@example.com, not null/empty)

DELETES:
  Tenants: Test Biz *, Bright Services, Bright Clean Services *, E2E Test Co,
           Test Home Co, demo-tenant, and any slug like test-biz-* / bright-clean-services*
  Users:   *@serviceos.local, *@serviceos.in, *@example.com, null/blank emails
  Data:    ALL rows in every tenant-scoped table for deleted tenant IDs
           (FK constraints disabled for the session — serviceos is superuser)
"""
from __future__ import annotations
import asyncio, sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

DB = "postgresql+asyncpg://serviceos:serviceos@localhost:5432/serviceos"

TEST_TENANT_COND = """(
    tenant_name LIKE 'Test Biz%'
    OR tenant_name = 'Bright Services'
    OR tenant_name LIKE 'Bright Clean Services%'
    OR tenant_name IN ('E2E Test Co', 'Test Home Co')
    OR (slug IS NOT NULL AND (
        slug LIKE 'test-biz-%'
        OR slug LIKE 'bright-clean-services%'
        OR slug = 'demo-tenant'
    ))
)"""

DEMO_USER_COND = """(
    email LIKE '%@serviceos.local'
    OR email LIKE '%@serviceos.in'
    OR email LIKE '%@example.com'
    OR email IS NULL
    OR email = ''
)"""


async def main(dry_run: bool = False) -> None:
    engine = create_async_engine(DB, echo=False)

    async with engine.begin() as conn:
        # Collect tenant IDs to delete
        r = await conn.execute(text(f"SELECT id FROM tenants WHERE {TEST_TENANT_COND}"))
        tenant_ids = [str(row[0]) for row in r.fetchall()]
        print(f"Tenants to delete: {len(tenant_ids)}")

        # Collect demo user IDs to delete (standalone — not via tenant cascade)
        r2 = await conn.execute(text(f"SELECT id, email FROM users WHERE {DEMO_USER_COND}"))
        demo_users = [(str(row[0]), row[1]) for row in r2.fetchall()]
        print(f"Demo/seed users to delete: {len(demo_users)}")

        if dry_run:
            print("\n[DRY RUN] No changes made.")
            return

        if not tenant_ids and not demo_users:
            print("Nothing to delete.")
            return

        # Disable FK enforcement for this session (superuser required)
        await conn.execute(text("SET session_replication_role = replica"))

        # ── Delete all rows referencing deleted tenant IDs ──────────────────
        # Query information_schema to find every table with a tenant_id FK column
        fk_tables_result = await conn.execute(text("""
            SELECT DISTINCT c.table_name
            FROM information_schema.columns c
            WHERE c.column_name = 'tenant_id'
              AND c.table_schema = 'public'
              AND c.table_name != 'tenants'
            ORDER BY c.table_name
        """))
        fk_tables = [row[0] for row in fk_tables_result.fetchall()]
        print(f"\nClearing {len(fk_tables)} tenant-scoped tables...")

        # Batch tenant IDs for the IN clause
        if tenant_ids:
            ids_literal = ", ".join(f"'{tid}'" for tid in tenant_ids)
            for table in fk_tables:
                try:
                    result = await conn.execute(
                        text(f"DELETE FROM {table} WHERE tenant_id IN ({ids_literal})")
                    )
                    if result.rowcount:
                        print(f"  {table}: deleted {result.rowcount} rows")
                except Exception as e:
                    print(f"  {table}: SKIP ({e})")

            # Delete the tenants themselves
            r_del = await conn.execute(
                text(f"DELETE FROM tenants WHERE {TEST_TENANT_COND}")
            )
            print(f"\nDeleted {r_del.rowcount} tenants.")

        # ── Delete standalone demo/seed users ───────────────────────────────
        if demo_users:
            # Also clean up user-scoped tables first
            user_tables_result = await conn.execute(text("""
                SELECT DISTINCT c.table_name
                FROM information_schema.columns c
                WHERE c.column_name = 'user_id'
                  AND c.table_schema = 'public'
                  AND c.table_name != 'users'
                ORDER BY c.table_name
            """))
            user_tables = [row[0] for row in user_tables_result.fetchall()]
            user_ids_literal = ", ".join(f"'{uid}'" for uid, _ in demo_users)

            for table in user_tables:
                try:
                    result = await conn.execute(
                        text(f"DELETE FROM {table} WHERE user_id IN ({user_ids_literal})")
                    )
                    if result.rowcount:
                        print(f"  {table}: deleted {result.rowcount} user-scoped rows")
                except Exception as e:
                    print(f"  {table}: SKIP ({e})")

            r_del2 = await conn.execute(
                text(f"DELETE FROM users WHERE {DEMO_USER_COND}")
            )
            print(f"Deleted {r_del2.rowcount} demo/seed users.")

        # Re-enable FK enforcement
        await conn.execute(text("SET session_replication_role = DEFAULT"))

    await engine.dispose()
    print("\nCleanup complete.")


if __name__ == "__main__":
    dry = "--dry-run" in sys.argv
    asyncio.run(main(dry_run=dry))
