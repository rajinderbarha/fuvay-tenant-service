"""Cleanup script: remove duplicate Emergency Service preset rules.

Usage:
    python scripts/cleanup_emergency_availability_preset.py --tenant-id <uuid> --dry-run
    python scripts/cleanup_emergency_availability_preset.py --tenant-id <uuid> --apply
    python scripts/cleanup_emergency_availability_preset.py --all-tenants --dry-run
    python scripts/cleanup_emergency_availability_preset.py --all-tenants --apply
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import datetime

try:
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker
except ImportError:
    print("ERROR: sqlalchemy not installed. Run: pip install sqlalchemy asyncpg")
    sys.exit(1)

# ── Emergency preset signature ────────────────────────────────────────────────
EMERGENCY = {
    "start_time": "08:00",
    "end_time":   "22:00",
    "slot_duration_minutes": 30,
    "scope_type": "provider",
}

FIND_SQL = """
SELECT id, tenant_id, day_of_week, start_time, end_time,
       slot_duration_minutes, max_bookings_per_slot, is_active, created_at
FROM provider_availability_rules
WHERE scope_type = 'provider'
  AND scope_id IS NULL
  AND start_time = :start
  AND end_time   = :end
  AND slot_duration_minutes = :slot
  {tenant_clause}
ORDER BY tenant_id, day_of_week, created_at
"""

DELETE_SQL = """
DELETE FROM provider_availability_rules
WHERE id = ANY(:ids)
RETURNING id
"""

NORMAL_CHECK_SQL = """
SELECT COUNT(*) AS cnt
FROM provider_availability_rules
WHERE tenant_id = :tid
  AND NOT (
    scope_type = 'provider'
    AND scope_id IS NULL
    AND start_time = :start
    AND end_time   = :end
    AND slot_duration_minutes = :slot
  )
"""


def get_db_url() -> str:
    import os
    url = os.environ.get("DATABASE_URL", "")
    if not url:
        # Try reading from .env
        try:
            with open(".env") as f:
                for line in f:
                    if line.startswith("DATABASE_URL="):
                        url = line.split("=", 1)[1].strip().strip('"')
        except FileNotFoundError:
            pass
    if not url:
        print("ERROR: DATABASE_URL not set. Set it in the environment or .env file.")
        sys.exit(1)
    # Convert postgresql:// → postgresql+asyncpg://
    if url.startswith("postgresql://") and "+asyncpg" not in url:
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif url.startswith("postgres://") and "+asyncpg" not in url:
        url = url.replace("postgres://", "postgresql+asyncpg://", 1)
    return url


async def run(tenant_id: str | None, dry_run: bool, all_tenants: bool) -> None:
    engine = create_async_engine(get_db_url(), echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as db:
        # ── Find emergency rules ──────────────────────────────────────────────
        tenant_clause = "" if all_tenants else "AND tenant_id = :tenant_id"
        params: dict = {
            "start": EMERGENCY["start_time"],
            "end":   EMERGENCY["end_time"],
            "slot":  EMERGENCY["slot_duration_minutes"],
        }
        if not all_tenants and tenant_id:
            params["tenant_id"] = tenant_id

        result = await db.execute(
            text(FIND_SQL.format(tenant_clause=tenant_clause)), params
        )
        rows = result.fetchall()

        if not rows:
            print("✅ No Emergency preset rules found. Nothing to clean up.")
            await engine.dispose()
            return

        print(f"\n{'DRY RUN — ' if dry_run else ''}Found {len(rows)} Emergency preset rule(s):\n")
        print(f"{'ID':<36}  {'Tenant':<36}  {'Day':>3}  {'Start':>5}  {'End':>5}  {'Slot':>4}  {'Active':>6}  Created")
        print("-" * 130)

        from collections import defaultdict
        by_tenant: dict[str, list] = defaultdict(list)
        for r in rows:
            row_dict = dict(r._mapping) if hasattr(r, "_mapping") else dict(zip(
                ["id","tenant_id","day_of_week","start_time","end_time","slot_duration_minutes","max_bookings_per_slot","is_active","created_at"], r
            ))
            tid = str(row_dict["tenant_id"])
            by_tenant[tid].append(row_dict)
            print(
                f"{str(row_dict['id']):<36}  {tid:<36}  "
                f"{row_dict['day_of_week']:>3}  {row_dict['start_time']:>5}  "
                f"{row_dict['end_time']:>5}  {row_dict['slot_duration_minutes']:>4}  "
                f"{'Yes' if row_dict['is_active'] else 'No':>6}  "
                f"{str(row_dict.get('created_at','—'))[:19]}"
            )

        print(f"\nTotal: {len(rows)} rule(s) across {len(by_tenant)} tenant(s)")

        # ── Duplicate summary per tenant ──────────────────────────────────────
        print("\nPer-tenant summary:")
        for tid, trules in sorted(by_tenant.items()):
            days_seen: dict[int, int] = {}
            for r in trules:
                d = r["day_of_week"]
                days_seen[d] = days_seen.get(d, 0) + 1
            dups = {d: c for d, c in days_seen.items() if c > 1}
            print(f"  Tenant {tid}: {len(trules)} rule(s) | {len(days_seen)} unique day(s) | {sum(dups.values()) - len(dups)} duplicate(s)")

        # ── Check normal rules won't be touched ───────────────────────────────
        print("\nVerifying normal rules will not be affected...")
        for tid in by_tenant:
            res = await db.execute(text(NORMAL_CHECK_SQL), {
                "tid": tid,
                "start": EMERGENCY["start_time"],
                "end": EMERGENCY["end_time"],
                "slot": EMERGENCY["slot_duration_minutes"],
            })
            cnt = res.scalar()
            print(f"  Tenant {tid}: {cnt} non-emergency rule(s) will NOT be touched.")

        if dry_run:
            print(f"\n🟡 DRY RUN complete. {len(rows)} rule(s) would be deleted.")
            print("   Re-run with --apply to delete.\n")
        else:
            ids = [str(r["id"]) if isinstance(r, dict) else str(r[0]) for r in rows]
            del_result = await db.execute(text(DELETE_SQL), {"ids": ids})
            deleted = del_result.fetchall()
            await db.commit()
            print(f"\n✅ Deleted {len(deleted)} Emergency preset rule(s).")
            print(f"   Timestamp: {datetime.utcnow().isoformat()}Z\n")

    await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description="Clean up Emergency Service availability preset rules.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--tenant-id", help="Target a specific tenant UUID")
    group.add_argument("--all-tenants", action="store_true", help="Target all tenants")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--apply",   action="store_true")
    args = parser.parse_args()

    asyncio.run(run(
        tenant_id=args.tenant_id,
        dry_run=args.dry_run,
        all_tenants=args.all_tenants,
    ))


if __name__ == "__main__":
    main()
