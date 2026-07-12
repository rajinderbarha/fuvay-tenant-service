"""FINAL-L5-05L — Canonical Admin role principal seed.

Idempotent, re-runnable, environment-guarded (reuses the same
ALLOWED_ENVIRONMENTS / FORBIDDEN_ENVIRONMENTS / DATABASE_URL host-marker
safety guard already established in scripts/canonical_seed_final_l5_01.py).

Fixes a real, previously-undiscovered bug from that same seed: it created
admin.ops@serviceos.local / admin.finance@serviceos.local /
admin.readonly@serviceos.local with role="super_admin" and only a
free-text, functionally-dead `platform_role` metadata label ("operations"/
"finance"/"read_only") to distinguish intended purpose — platform_role is
never consulted by PermissionChecker or any require_* dependency, so all
three accounts were, and until this script runs still are, indistinguishable
from the real Platform Super Admin account in terms of actual backend
authorization. This script repoints their `role` column at the real,
enforced, least-privilege role strings added in app/core/permissions.py's
ROLE_PERMISSIONS this sprint, and creates the one role that had no
pre-existing account at all (admin.security@serviceos.local).

Does not touch passwords or any other account field. Existing password
hashes are preserved untouched — only the `role` column is corrected for
the 3 existing accounts, and a new row is inserted only for the account
that does not yet exist.

Run: python scripts/seed_admin_roles_final_l5_05l.py
"""
from __future__ import annotations
import asyncio
import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.engines.auth.utils import hash_password

ALLOWED_ENVIRONMENTS = {"local", "development", "dev", "test", "e2e", "certification"}
FORBIDDEN_ENVIRONMENTS = {"production", "prod", "staging-live", "live"}
FORBIDDEN_HOST_MARKERS = (".amazonaws.com", ".azure.com", ".gcp.com", "prod-", ".rds.")

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://serviceos:serviceos@localhost:5432/serviceos")

# Not the real production password for any account — a dedicated test
# credential for the one net-new principal this script creates. Sourced
# from an env var so it is never hardcoded; falls back to a fixed,
# clearly-labeled test value only for local/dev/test convenience.
SECURITY_ADMIN_PASSWORD = os.getenv("SEED_ADMIN_SECURITY_PASSWORD", "CanonicalL5!2026")

# email -> canonical enforced role string (app.core.permissions.ROLE_PERMISSIONS)
ROLE_FIXUPS = {
    "admin.ops@serviceos.local":      "admin_operations",
    "admin.finance@serviceos.local":  "admin_finance",
    "admin.readonly@serviceos.local": "admin_readonly",
}

NEW_PRINCIPAL = {
    "email": "admin.security@serviceos.local",
    "full_name": "Admin Security User",
    "role": "admin_security",
    "platform_role": "security",
}


def _safety_guard() -> None:
    env = os.getenv("APP_ENV", "development").lower()
    allow_seed = os.getenv("ALLOW_ADMIN_ROLE_SEED", "false").lower() == "true"
    if env in FORBIDDEN_ENVIRONMENTS:
        print(f"[REFUSED] APP_ENV={env} is forbidden. Aborting."); sys.exit(1)
    if env not in ALLOWED_ENVIRONMENTS:
        print(f"[REFUSED] APP_ENV={env} not in allow-list {ALLOWED_ENVIRONMENTS}. Aborting."); sys.exit(1)
    if not allow_seed:
        print("[REFUSED] ALLOW_ADMIN_ROLE_SEED != true. Aborting — this seed is explicitly "
              "opt-in, not run automatically by any other seed script or migration."); sys.exit(1)
    if any(m in DATABASE_URL for m in FORBIDDEN_HOST_MARKERS):
        print("[REFUSED] DATABASE_URL host looks managed/cloud/production. Aborting."); sys.exit(1)
    masked = DATABASE_URL.split("@")[-1]
    print(f"[OK] Safety guard passed. APP_ENV={env}, target=...@{masked}")


async def run() -> None:
    _safety_guard()
    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as db:
        for email, role in ROLE_FIXUPS.items():
            row = (await db.execute(text("SELECT id, role FROM users WHERE email = :e"), {"e": email})).first()
            if not row:
                print(f"[SKIP]   {email} — no existing account found, not creating (out of scope for this fixup)")
                continue
            if row[1] == role:
                print(f"[SKIP]   {email} (role already '{role}')")
                continue
            await db.execute(
                text("UPDATE users SET role = :role, updated_at = now() WHERE id = :id"),
                {"role": role, "id": str(row[0])},
            )
            print(f"[FIX]    {email}: role '{row[1]}' -> '{role}'")

        existing = (await db.execute(
            text("SELECT id FROM users WHERE email = :e"), {"e": NEW_PRINCIPAL["email"]}
        )).first()
        if existing:
            print(f"[SKIP]   {NEW_PRINCIPAL['email']} (exists)")
        else:
            uid = uuid.uuid4()
            await db.execute(text("""
                INSERT INTO users (id, email, full_name, role, tenant_id, hashed_password,
                                    is_active, is_verified, onboarding_complete, platform_role,
                                    account_status, created_at, updated_at)
                VALUES (:id, :email, :name, :role, NULL, :pw, true, true, true, :prole,
                        'active', now(), now())
            """), {
                "id": str(uid), "email": NEW_PRINCIPAL["email"], "name": NEW_PRINCIPAL["full_name"],
                "role": NEW_PRINCIPAL["role"], "pw": hash_password(SECURITY_ADMIN_PASSWORD),
                "prole": NEW_PRINCIPAL["platform_role"],
            })
            print(f"[CREATE] {NEW_PRINCIPAL['email']} ({NEW_PRINCIPAL['role']})")

        await db.commit()

    await engine.dispose()
    print("[DONE] FINAL-L5-05L admin role seed complete.")


if __name__ == "__main__":
    asyncio.run(run())
