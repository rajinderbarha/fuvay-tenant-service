"""Phase 2A Slice 2D/2E — standalone, read-only authorization integrity check.

Reports counts of several authorization-integrity violations, without ever
printing individual account/permission identifiers to normal output -- only
counts, safe for a production health-check log line. Pass --detail (an
explicit opt-in) to see per-record detail, for an operator who has already
decided to investigate. No automatic remediation is ever performed.

Checks:
  - users.role values outside the 10 canonical RBAC roles (Slice 2D)
  - staff_permissions.permission_key values not in the real P.* registry
    (Slice 2E) -- these are inert today (PermissionChecker.has() only ever
    compares against a known P.* constant passed by route code, never
    against override-dict keys), but a typo'd permission_key is still worth
    surfacing since it means a grant an admin thinks they made has no effect.
  - staff_permissions rows whose tenant_id does not match their user's
    actual tenant_id (Slice 2E) -- would indicate a cross-tenant permission
    leak risk if it ever occurred; not expected given the write path always
    sets tenant_id from the target user's own tenant, but checked directly
    rather than assumed.
  - users.access_scope values that are not None and not in the known valid
    set (Slice 2E).

This is deliberately a standalone script, not wired into application
startup: startup-time DB queries add latency/risk to every boot, and a
"platform won't start because of 1 bad demo account" failure mode is worse
than a visible, non-blocking integrity signal an operator can act on. Run
this on a schedule (cron/CI) instead.

Exit code 0 if zero violations found across all checks, 1 if any exist (so
it can gate a CI step or alert without needing to parse output).

Usage:
    python scripts/workflow_rearchitecture/check_role_integrity.py
    python scripts/workflow_rearchitecture/check_role_integrity.py --detail
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.ext.asyncio import create_async_engine

CANONICAL_ROLES = {
    "super_admin", "tenant_owner", "staff", "technician", "customer", "guest",
    "admin_operations", "admin_finance", "admin_security", "admin_readonly",
}

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql+asyncpg://serviceos:serviceos@127.0.0.1:5432/serviceos"
)


def _known_permission_keys() -> set[str]:
    from app.core.permissions import P
    return {v for k, v in vars(P).items() if not k.startswith("_") and isinstance(v, str)}


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--detail", action="store_true", help="Show per-record detail (opt-in; not printed by default).")
    args = parser.parse_args()

    engine = create_async_engine(DATABASE_URL)
    placeholders = ", ".join(f"'{r}'" for r in CANONICAL_ROLES)
    known_perms = _known_permission_keys()
    valid_access_scopes = {
        "global", "operations", "finance", "compliance", "support",
        "tenant_scoped", "customer_support_limited",
    }

    report: dict = {"checks": {}}
    violations = 0

    async with engine.connect() as conn:
        # 1. Invalid users.role
        row = await conn.exec_driver_sql(f"SELECT count(*) FROM users WHERE role NOT IN ({placeholders})")
        c = row.scalar()
        report["checks"]["invalid_role_count"] = c
        violations += c
        if args.detail and c:
            rows = await conn.exec_driver_sql(f"SELECT email, role, is_active FROM users WHERE role NOT IN ({placeholders})")
            report["invalid_role_accounts"] = [{"email": r[0], "role": r[1], "is_active": r[2]} for r in rows]

        # 2. staff_permissions with unknown permission_key
        perm_rows = await conn.exec_driver_sql("SELECT DISTINCT permission_key FROM staff_permissions")
        unknown_perm_keys = [r[0] for r in perm_rows if r[0] not in known_perms]
        report["checks"]["unknown_permission_key_count"] = len(unknown_perm_keys)
        violations += len(unknown_perm_keys)
        if args.detail and unknown_perm_keys:
            report["unknown_permission_keys"] = unknown_perm_keys

        # 3. Cross-tenant staff_permissions (row.tenant_id != owning user's tenant_id)
        cross = await conn.exec_driver_sql(
            "SELECT count(*) FROM staff_permissions sp JOIN users u ON u.id = sp.user_id "
            "WHERE sp.tenant_id IS DISTINCT FROM u.tenant_id"
        )
        c = cross.scalar()
        report["checks"]["cross_tenant_staff_permission_count"] = c
        violations += c

        # 4. staff_permissions for a user_id that doesn't exist
        orphaned = await conn.exec_driver_sql(
            "SELECT count(*) FROM staff_permissions sp LEFT JOIN users u ON u.id = sp.user_id WHERE u.id IS NULL"
        )
        c = orphaned.scalar()
        report["checks"]["orphaned_permission_row_count"] = c
        violations += c

        # 5. Invalid access_scope values
        scope_placeholders = ", ".join(f"'{s}'" for s in valid_access_scopes)
        row = await conn.exec_driver_sql(
            f"SELECT count(*) FROM users WHERE access_scope IS NOT NULL AND access_scope NOT IN ({scope_placeholders})"
        )
        c = row.scalar()
        report["checks"]["invalid_access_scope_count"] = c
        violations += c

    await engine.dispose()
    report["status"] = "ok" if violations == 0 else "integrity_violation"
    report["total_violations"] = violations
    print(json.dumps(report, indent=2))
    sys.exit(0 if violations == 0 else 1)


if __name__ == "__main__":
    asyncio.run(main())
