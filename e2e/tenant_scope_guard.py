"""
MODULE-L5-01: identity/tenant-scope guard.

Scans app/engines/tenant_engine/router.py for every endpoint whose path
contains "{tenant_id}" and reports whether its handler body calls
_assert_own_tenant_or_super_admin (the fix applied this sprint) before
performing its real work. Fails closed (non-zero exit) if any endpoint
reachable by a tenant-scoped role (tenant_owner/staff/technician) lacks
the check -- this is real, source-derived evidence for the MODULE-L5-01
blocker list, not a guess.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
ROUTER_PATH = ROOT / "app" / "engines" / "tenant_engine" / "router.py"

FIXED_MARKER = "_assert_own_tenant_or_super_admin"

# tenant_owner's real, current permission bundle (app/core/permissions.py
# lines 534-563) -- used to classify severity precisely rather than
# treating every unprotected endpoint as equally exploitable.
TENANT_OWNER_PERMISSIONS = {
    "TENANT_READ", "TENANT_UPDATE", "TENANT_BILLING_READ", "TENANT_BILLING_MANAGE",
    "TENANT_DATA_EXPORT", "TENANT_HEALTH_READ", "TENANT_ENGINES_MANAGE", "TENANT_FLAGS_MANAGE",
    "AUTH_AUDIT_READ",
}


def main():
    text = ROUTER_PATH.read_text(encoding="utf-8")
    # Split into per-endpoint chunks: each starts at a @router.<verb>("/{tenant_id}...
    pattern = re.compile(r'@router\.(get|post|put|patch|delete)\("(/\{tenant_id\}[^"]*)"', re.MULTILINE)
    matches = list(pattern.finditer(text))

    results = []
    for i, m in enumerate(matches):
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        chunk = text[start:end]
        has_check = FIXED_MARKER in chunk
        perm_match = re.search(r"require_permission\(P\.([A-Z0-9_]+)\)", chunk)
        permission = perm_match.group(1) if perm_match else None
        requires_super_admin = "Depends(require_super_admin)" in chunk
        bare_auth = permission is None and not requires_super_admin and "Depends(get_current_user)" in chunk
        if has_check:
            severity = "FIXED"
        elif requires_super_admin:
            # require_super_admin blocks every non-super_admin role outright,
            # including tenant_owner -- safe regardless of the missing
            # tenant-ownership check, since no tenant-scoped role can reach
            # the handler body at all.
            severity = "SAFE_SUPER_ADMIN_ONLY"
        elif bare_auth:
            severity = "CRITICAL_ANY_AUTHENTICATED_ROLE"
        elif permission in TENANT_OWNER_PERMISSIONS:
            severity = "CRITICAL_TENANT_OWNER_EXPLOITABLE"
        elif permission is not None:
            severity = "SAFE_ADMIN_ONLY_PERMISSION"
        else:
            severity = "UNKNOWN_GATING_PATTERN"
        results.append({
            "method": m.group(1).upper(),
            "path": m.group(2),
            "has_ownership_check": has_check,
            "permission": permission,
            "severity": severity,
        })

    unprotected = [r for r in results if not r["has_ownership_check"]]
    by_severity = {}
    for r in unprotected:
        by_severity.setdefault(r["severity"], []).append(f"{r['method']} {r['path']}")

    print(f"Total /{{tenant_id}} endpoints found: {len(results)}")
    print(f"Protected (has ownership check): {len(results) - len(unprotected)}")
    print(f"UNPROTECTED (missing check): {len(unprotected)}")
    for severity, items in sorted(by_severity.items()):
        print(f"\n  [{severity}] ({len(items)}):")
        for item in items:
            print(f"    - {item}")

    unknown_gating = by_severity.get("UNKNOWN_GATING_PATTERN", [])
    if unknown_gating:
        print(f"\nFAIL: {len(unknown_gating)} endpoint(s) use a gating pattern this guard cannot classify -- update the guard before trusting its severity counts.")
        return 1

    return 0 if len(unprotected) == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
