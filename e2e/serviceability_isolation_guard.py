"""
MODULE-L5-04: tenant service-area isolation guard (fail-closed).

MODULE-L5-04 found an ACTIVE cross-tenant read IDOR: ServiceabilityService.
_assert_owns_tenant confined only `tenant_owner`, but `staff` and `technician`
also hold `tenant_service_area:read` and can reach GET /v1/tenant/service-areas/
{area_id} — so the tenant_owner-only gate let a staff/technician at tenant A
read tenant B's service area by area_id.

The isolation control must confine EVERY tenant-scoped role (denylist the
platform roles that legitimately cross tenants), not allowlist a single role.
This guard fails closed if the vulnerable `actor_role == "tenant_owner"` gate
pattern returns, or if the every-area-method-goes-through-get_service_area
invariant weakens.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
SVC = ROOT / "app" / "engines" / "serviceability" / "service.py"


def check() -> list[str]:
    findings = []
    text = SVC.read_text(encoding="utf-8")

    # Inspect ONLY the _assert_owns_tenant method (other actor_role=="tenant_owner"
    # uses in this file are legitimate positive allowlists with fail-closed
    # defaults — e.g. _assert_admin_can_view_customer — and marketplace matching).
    m = re.search(r'def _assert_owns_tenant\(.*?(?=\n    (async )?def )', text, re.S)
    body = m.group(0) if m else ""
    if not body:
        return ["_assert_owns_tenant method not found (renamed?) — isolation unverifiable"]
    # The vulnerable single-role allowlist gate must be gone from this method.
    if re.search(r'if self\.actor_role == "tenant_owner"', body):
        findings.append("_assert_owns_tenant uses vulnerable single-role gate "
                        "(actor_role == 'tenant_owner') — staff/technician bypass")
    # The fixed control must denylist platform roles and confine the rest.
    if "PLATFORM_ROLES" not in body or "actor_tenant_id" not in body:
        findings.append("_assert_owns_tenant no longer confines by PLATFORM_ROLES/actor_tenant_id")

    # Every {area_id} area/mapping mutation reads through get_service_area /
    # _get_mapping (which assert ownership). Fail if a raw db.get on the area
    # table appears outside those two methods.
    for m2 in re.finditer(r'db\.get\(TenantServiceArea,', text):
        # allowed only inside get_service_area
        ctx = text[max(0, m2.start() - 400):m2.start()]
        if "async def get_service_area(" not in ctx:
            findings.append("raw db.get(TenantServiceArea, ...) outside get_service_area "
                            "(possible unscoped area load)")
            break
    return findings


def main() -> int:
    findings = check()
    out = {
        "serviceability_isolation_findings": findings,
        "result": "SERVICEABILITY_ISOLATION_GUARD_FAILED" if findings else "SERVICEABILITY_ISOLATION_GUARD_PASSED",
    }
    print(__import__("json").dumps(out, indent=2))
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
