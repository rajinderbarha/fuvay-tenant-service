"""Restore the @serviceos.in fixture accounts the admin/tenant Playwright
suite authenticates as (frontend/e2e-admin-tenant/e2e/helpers/api.ts).

WHY THIS EXISTS
---------------
ADMIN_TENANT_E2E_01_TEST_USERS_REPORT.md documents these as pre-existing,
verified-working accounts, with the tenant roles attached to tenant
34b427a7 ("Demo AC Services"). That tenant no longer exists in this
database (it has been reset since that report), so 3 of the 9 Playwright
specs -- tenant-service-setup-e2e09, tenant-rbac-bookability-e2e09b,
tenant-finance-notif-settings-e2e11 -- could not even log in.

scripts/seed_demo_users.py does NOT cover these: it seeds @serviceos.local
addresses, while the E2E helpers hardcode @serviceos.in.

WHAT IT DOES / DOESN'T DO
-------------------------
* Idempotent upsert by email. Never deletes, never touches a user it did
  not create beyond resetting that user's own password to the documented
  E2E value.
* Never creates a tenant. Tenant-scoped fixtures are attached to an
  EXISTING tenant chosen for having real data to assert against (most
  enabled services + jobs + an active home_services enrollment), because
  a fresh empty tenant would fail the specs' data assertions for reasons
  unrelated to the code under test.
* Leaves force_password_change False so the login flow does not divert to
  the change-password screen mid-test.

Run:  python scripts/seed_e2e_admin_tenant_fixtures.py
"""
from __future__ import annotations

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.config import Settings
from app.engines.auth.utils import hash_password

E2E_PASSWORD = "Password123!"

# (email, full_name, role, tenant_scoped)
FIXTURES = [
    ("admin@serviceos.in",           "Super Admin (E2E)",     "super_admin",  False),
    ("admin.operator@serviceos.in",  "Admin Operator (E2E)",  "super_admin",  False),
    ("customer@serviceos.in",        "Customer One (E2E)",    "customer",     False),
    ("provider@serviceos.in",        "Tenant Owner (E2E)",    "tenant_owner", True),
    ("tenant.manager@serviceos.in",  "Tenant Manager (E2E)",  "staff",        True),
    ("tenant.readonly@serviceos.in", "Tenant Readonly (E2E)", "staff",        True),
    ("staff@serviceos.in",           "Staff One (E2E)",       "technician",   True),
]

PICK_TENANT = text("""
    SELECT t.id
    FROM tenants t
    ORDER BY
      (SELECT count(*) FROM tenant_services ts
        WHERE ts.tenant_id = t.id AND ts.is_enabled) DESC,
      (SELECT count(*) FROM service_jobs j WHERE j.tenant_id = t.id) DESC
    LIMIT 1
""")


async def main() -> None:
    settings = Settings()
    engine = create_async_engine(settings.DATABASE_URL)
    pw = hash_password(E2E_PASSWORD)

    async with engine.begin() as conn:
        tenant_id = (await conn.execute(PICK_TENANT)).scalar_one_or_none()
        if tenant_id is None:
            print("ERROR: no tenants exist; cannot attach tenant-scoped fixtures.")
            return
        print(f"tenant-scoped fixtures -> tenant {tenant_id}")

        for email, full_name, role, tenant_scoped in FIXTURES:
            tid = str(tenant_id) if tenant_scoped else None
            existing = (await conn.execute(
                text("SELECT id FROM users WHERE email = :e"), {"e": email}
            )).scalar_one_or_none()

            if existing:
                # Only reset the password/active flags -- never rewrite an
                # existing user's role or tenant, which could re-scope a real
                # account that happens to share the address.
                await conn.execute(text("""
                    UPDATE users
                       SET hashed_password = :pw, is_active = true,
                           force_password_change = false
                     WHERE email = :e
                """), {"pw": pw, "e": email})
                print(f"  updated password  {email}")
            else:
                await conn.execute(text("""
                    INSERT INTO users (email, full_name, role, tenant_id, hashed_password,
                                       is_active, is_verified, force_password_change)
                    VALUES (:e, :n, :r, CAST(:t AS uuid), :pw, true, true, false)
                """), {"e": email, "n": full_name, "r": role, "t": tid, "pw": pw})
                print(f"  created           {email}  role={role}"
                      + (f" tenant={tid}" if tid else ""))

    await engine.dispose()
    print("done.")


if __name__ == "__main__":
    asyncio.run(main())
