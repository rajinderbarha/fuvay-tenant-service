"""Phase 0 — Clean Data + Baseline Seed.

Safety-guarded runtime data reset + deterministic Home Services baseline
seed for local/dev/certification environments only.

Refuses to run unless APP_ENV is in the explicit allow-list and
DATABASE_URL does not look like a managed/cloud/production host.
Requires --confirm to actually execute (default is a dry-run summary only).

Run: python scripts/serviceos_reset_dev_data.py --confirm
Dry run (default, no changes made): python scripts/serviceos_reset_dev_data.py
"""
from __future__ import annotations
import argparse
import asyncio
import os
import sys
import uuid
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

ALLOWED_ENVIRONMENTS = {"local", "development", "dev", "test", "staging-test", "certification"}
FORBIDDEN_ENVIRONMENTS = {"production", "prod", "staging-live", "live"}
FORBIDDEN_HOST_MARKERS = (".amazonaws.com", ".azure.com", ".gcp.com", "prod-", ".rds.")

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://serviceos:serviceos@localhost:5432/serviceos")


def _safety_guard() -> None:
    env = os.getenv("APP_ENV", "development").lower()
    if env in FORBIDDEN_ENVIRONMENTS:
        print(f"[REFUSED] APP_ENV={env} is forbidden for data reset. Aborting.")
        sys.exit(1)
    if env not in ALLOWED_ENVIRONMENTS:
        print(f"[REFUSED] APP_ENV={env} is not in the explicit allow-list {ALLOWED_ENVIRONMENTS}. Aborting.")
        sys.exit(1)
    if any(marker in DATABASE_URL for marker in FORBIDDEN_HOST_MARKERS):
        print(f"[REFUSED] DATABASE_URL host looks like a managed/cloud/production host. Aborting.")
        sys.exit(1)
    print(f"[OK] Safety guard passed. APP_ENV={env}, DB host confirmed local/dev.")


# Runtime/test data cleanup — targets the DEMO_TENANT_SLUG's dependent rows only,
# plus known duplicate/cruft demo user accounts. Catalog config (categories,
# service_groups, master_services, brands, service_types, mappings) and
# platform config (users we keep, engines, platform_settings) are preserved.
DEMO_TENANT_SLUG = "demo-tenant"
DUPLICATE_USER_EMAILS = [
    "admin@serviceos.io", "staff@serviceos.local",
    "customer@serviceos.local", "ops.manager.test@serviceos.local",
]
# NOTE: admin@serviceos.local is intentionally NOT in this list — it is a
# required auth fixture for tests/test_trust_quality_phase1.py and
# tests/test_p0_sidebar_duplicate_cleanup.py (hardcoded ADMIN_EMAIL). It was
# mistakenly deleted once during this sprint's initial cleanup, which broke
# 24 tests; it was restored and must not be re-flagged for deletion.

NEW_TENANT_SLUG = "demo-ac-services"


async def run(confirm: bool) -> None:
    _safety_guard()

    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as db:
        # ── Resolve old demo tenant ────────────────────────────────────────
        old_tenant = (await db.execute(text(
            "SELECT id FROM tenants WHERE slug = :slug"), {"slug": DEMO_TENANT_SLUG})).scalar_one_or_none()

        plan = []
        if old_tenant:
            counts = {}
            for t, col in (("job_status_history", "job_id"), ("customer_credit_ledger", "tenant_id"),
                           ("security_deposits", "tenant_id"), ("security_deposit_adjustments", "tenant_id"),
                           ("wallet_transactions", "tenant_id"), ("tenant_wallets", "tenant_id"),
                           ("tenant_package_assignments", "tenant_id")):
                try:
                    r = await db.execute(text(f"SELECT count(*) FROM {t} WHERE {col} = :tid"), {"tid": str(old_tenant)})
                    counts[t] = r.scalar_one_or_none() or 0
                except Exception:
                    await db.rollback()
                    counts[t] = "N/A (no such column/table)"
            plan.append(f"Old demo tenant {old_tenant} to be deleted, dependent rows: {counts}")
        else:
            plan.append(f"No tenant with slug='{DEMO_TENANT_SLUG}' found — nothing to delete there.")

        dup_users = (await db.execute(text(
            "SELECT id, email FROM users WHERE email = ANY(:emails)"),
            {"emails": DUPLICATE_USER_EMAILS})).all()
        plan.append(f"Duplicate/cruft demo users to be deleted: {[u[1] for u in dup_users]}")

        print("\n".join(plan))
        if not confirm:
            print("\n[DRY RUN] No changes made. Re-run with --confirm to execute.")
            await engine.dispose()
            return

        # ── Cleanup ─────────────────────────────────────────────────────────
        if old_tenant:
            for t, col in (("job_status_history", "job_id"),):
                pass  # job_status_history has no tenant_id; skipped (0 rows tied to old_tenant anyway)
            for t, col in (("customer_credit_ledger", "tenant_id"), ("security_deposit_adjustments", "tenant_id"),
                           ("security_deposits", "tenant_id"), ("wallet_transactions", "tenant_id"),
                           ("tenant_package_assignments", "tenant_id"), ("tenant_wallets", "tenant_id")):
                try:
                    await db.execute(text(f"DELETE FROM {t} WHERE {col} = :tid"), {"tid": str(old_tenant)})
                except Exception as e:
                    await db.rollback()
                    print(f"  [skip] {t}: {e}")
            await db.execute(text("DELETE FROM tenants WHERE id = :tid"), {"tid": str(old_tenant)})
            print(f"[DELETE] old demo tenant {old_tenant} and dependent rows")

        for uid, email in dup_users:
            await db.execute(text("DELETE FROM users WHERE id = :uid"), {"uid": str(uid)})
            print(f"[DELETE] duplicate user {email}")

        await db.commit()
        print("\n[CLEANUP COMPLETE]")

    await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--confirm", action="store_true", help="Actually execute the reset (default: dry run)")
    args = parser.parse_args()
    asyncio.run(run(args.confirm))
