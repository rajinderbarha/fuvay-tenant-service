"""Delete every provider tenant from a development database.

This preserves platform administrators and global catalog/configuration data.
The command is deliberately dry-run by default and requires an explicit phrase
for the destructive path::

    python scripts/purge_all_providers.py --apply --confirm PURGE_ALL_PROVIDERS
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database import create_engine


CONFIRMATION = "PURGE_ALL_PROVIDERS"


def _quoted_identifier(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


async def run(*, apply: bool) -> None:
    engine = create_engine()
    async with engine.begin() as conn:
        tenant_rows = (await conn.execute(text(
            "SELECT id::text FROM tenants ORDER BY created_at, id"
        ))).fetchall()
        tenant_ids = [row[0] for row in tenant_rows]
        user_rows = (await conn.execute(text(
            "SELECT id::text FROM users WHERE tenant_id IS NOT NULL ORDER BY id"
        ))).fetchall()
        user_ids = [row[0] for row in user_rows]

        print(f"Provider tenants found: {len(tenant_ids)}")
        print(f"Tenant-linked users found: {len(user_ids)}")
        if not apply:
            print("Dry run only; no records changed.")
            return

        # This local setting lets the cleanup remove tenant-owned records from
        # legacy tables whose foreign keys were created without ON DELETE
        # CASCADE. SET LOCAL is automatically restored when the transaction
        # ends, including on rollback.
        await conn.execute(text("SET LOCAL session_replication_role = replica"))

        tenant_tables = [row[0] for row in (await conn.execute(text("""
            SELECT DISTINCT table_name
            FROM information_schema.columns
            WHERE table_schema='public' AND column_name='tenant_id'
              AND table_name NOT IN ('tenants', 'users')
            ORDER BY table_name
        """))).fetchall()]
        user_tables = [row[0] for row in (await conn.execute(text("""
            SELECT DISTINCT table_name
            FROM information_schema.columns
            WHERE table_schema='public' AND column_name='user_id'
              AND table_name != 'users'
            ORDER BY table_name
        """))).fetchall()]

        tenant_rows_deleted = 0
        user_rows_deleted = 0
        if tenant_ids:
            for table_name in tenant_tables:
                result = await conn.execute(
                    text(
                        f"DELETE FROM {_quoted_identifier(table_name)} "
                        "WHERE tenant_id::text = ANY(:ids)"
                    ),
                    {"ids": tenant_ids},
                )
                tenant_rows_deleted += max(result.rowcount or 0, 0)

        if user_ids:
            for table_name in user_tables:
                result = await conn.execute(
                    text(
                        f"DELETE FROM {_quoted_identifier(table_name)} "
                        "WHERE user_id::text = ANY(:ids)"
                    ),
                    {"ids": user_ids},
                )
                user_rows_deleted += max(result.rowcount or 0, 0)

        deleted_tenants = (await conn.execute(text("DELETE FROM tenants"))).rowcount or 0
        deleted_users = (await conn.execute(text(
            "DELETE FROM users WHERE tenant_id IS NOT NULL"
        ))).rowcount or 0

        print(f"Tenant-scoped rows deleted: {tenant_rows_deleted}")
        print(f"User-scoped rows deleted: {user_rows_deleted}")
        print(f"Provider tenants deleted: {deleted_tenants}")
        print(f"Tenant-linked users deleted: {deleted_users}")

    await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--confirm", default="")
    args = parser.parse_args()
    if args.apply and args.confirm != CONFIRMATION:
        parser.error(f"--apply requires --confirm {CONFIRMATION}")
    asyncio.run(run(apply=args.apply))


if __name__ == "__main__":
    main()
