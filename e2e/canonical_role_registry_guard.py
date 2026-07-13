"""
MODULE-L5-01D: canonical-role-registry guard (fail-closed).

BLK-01D-1 was resolved by architectural decision (Option A): ServiceOS's
single authoritative role registry is app/core/permissions.py::ROLE_PERMISSIONS,
and the canonical system-role set is the product's real, audited least-privilege
model:

    super_admin, admin_operations, admin_finance, admin_security, admin_readonly,
    tenant_owner, staff, technician, customer, guest

(The generic MODULE-L5 template names platform_admin/support_admin/tenant_admin/
manager are deliberately NOT adopted: the four admin_* roles are a more-granular,
audited least-privilege realization built across FINAL-L5-05L..05U, and
tenant_admin/manager have no product-defined authority. See
docs/module-l5/MODULE_L5_01D_FINAL_REPORT.md and CANONICAL_ROLE_MODEL.md.)

This guard fails closed if:
  * the enforced ROLE_PERMISSIONS keys drift from the canonical set (an 11th role
    is added, or a canonical role is removed);
  * the auth/constants.py::ROLES convenience mirror drifts from the canonical set;
  * any role carries no permissions (empty grant) -- except `guest`, which is
    intentionally minimal but must still be present;
  * the roles_permissions display catalog surfaces a role as implemented that is
    not in the canonical set.

Controlled-failure coverage lives in tests/test_module_l5_01d_canonical_roles.py.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

# The one canonical system-role set (Option A — the product's real enforced model).
CANONICAL_ROLES = frozenset({
    "super_admin",
    "admin_operations",
    "admin_finance",
    "admin_security",
    "admin_readonly",
    "tenant_owner",
    "staff",
    "technician",
    "customer",
    "guest",
})


def check() -> list[str]:
    findings: list[str] = []

    from app.core.permissions import ROLE_PERMISSIONS
    from app.engines.auth.constants import ROLES as CONSTANTS_ROLES

    enforced = set(ROLE_PERMISSIONS.keys())
    if enforced != set(CANONICAL_ROLES):
        extra = enforced - CANONICAL_ROLES
        missing = CANONICAL_ROLES - enforced
        if extra:
            findings.append(f"ROLE_PERMISSIONS has non-canonical role(s): {sorted(extra)}")
        if missing:
            findings.append(f"ROLE_PERMISSIONS is missing canonical role(s): {sorted(missing)}")

    mirror = set(CONSTANTS_ROLES)
    if mirror != set(CANONICAL_ROLES):
        findings.append(
            f"auth/constants.py::ROLES drifted from canonical set: "
            f"extra={sorted(mirror - CANONICAL_ROLES)} missing={sorted(CANONICAL_ROLES - mirror)}"
        )

    for role in CANONICAL_ROLES:
        grants = ROLE_PERMISSIONS.get(role, [])
        if not grants:
            findings.append(f"canonical role '{role}' has an empty permission grant")

    # Display catalog must not present a non-canonical role as implemented.
    try:
        from app.engines.roles_permissions.service import REQUIRED_ROLE_ORDER
        for role in REQUIRED_ROLE_ORDER:
            if role in ROLE_PERMISSIONS and role not in CANONICAL_ROLES:
                findings.append(f"display catalog enforces non-canonical role '{role}'")
    except Exception as exc:  # pragma: no cover - catalog is optional
        findings.append(f"could not inspect roles_permissions display catalog: {exc!r}")

    return findings


def main() -> int:
    findings = check()
    result = {
        "canonical_role_findings": findings,
        "canonical_role_count": len(CANONICAL_ROLES),
        "result": "CANONICAL_ROLE_REGISTRY_GUARD_FAILED" if findings
                  else "CANONICAL_ROLE_REGISTRY_GUARD_PASSED",
    }
    print(__import__("json").dumps(result, indent=2))
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
