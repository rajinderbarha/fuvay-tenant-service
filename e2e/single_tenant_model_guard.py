"""
MODULE-L5-01D-R: single-tenant operational-identity model guard (fail-closed).

BLK-01D-2 was resolved as **Decision A**: a ServiceOS operational tenant user
belongs to one tenant business at a time. Platform users are global (tenant_id
NULL), customers are marketplace identities, and branches/teams live inside one
tenant. Multi-tenant operational membership and tenant switching are NOT current
ServiceOS capabilities (evidence: single `User.tenant_id`; no membership table;
no tenant-switch route anywhere in backend; no tenant/business/organization
switcher anywhere in the frontends). See docs/module-l5/CANONICAL_ROLE_MODEL.md
and MODULE_L5_01D_R_FINAL_REPORT.md.

This guard fails closed if that decision is silently violated by introducing
either (a) a tenant/principal/organization *switch* route, or (b) a
tenant-membership model class — EITHER of which requires the full membership
architecture (a dedicated migration sprint), not an ad-hoc addition. Introducing
one without the other is exactly the unsafe half-migration the mission forbids.

If multi-tenant membership later becomes a confirmed product requirement, this
guard is retired as part of that dedicated migration sprint — not bypassed.

Controlled-failure coverage: tests/test_module_l5_01d_canonical_roles.py.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
ENGINES_DIR = ROOT / "app" / "engines"

# Route-path fragments that would indicate a tenant/principal switch surface.
SWITCH_ROUTE_RE = re.compile(
    r'@\w+\.(get|post|put|patch|delete)\(\s*["\'][^"\']*'
    r'(switch-tenant|tenant-switch|switch-principal|switch-business|switch-workspace|active-tenant/switch)',
    re.IGNORECASE,
)

# A membership model class (SQLAlchemy) would signal a membership table being
# introduced. We look for a class whose name implies tenant membership.
MEMBERSHIP_CLASS_RE = re.compile(
    r'class\s+(TenantMembership|UserTenantMembership|TenantUser|Membership)\b[^\n]*\(\s*Base',
)


def check() -> list[str]:
    findings: list[str] = []
    for f in ENGINES_DIR.rglob("*.py"):
        if "__pycache__" in str(f):
            continue
        text = f.read_text(encoding="utf-8")
        try:
            rel = str(f.relative_to(ROOT)).replace("\\", "/")
        except ValueError:
            rel = f.name
        for m in SWITCH_ROUTE_RE.finditer(text):
            findings.append(f"{rel}: tenant/principal switch route introduced ('{m.group(2)}') "
                            f"without the confirmed multi-membership architecture")
        for m in MEMBERSHIP_CLASS_RE.finditer(text):
            findings.append(f"{rel}: tenant-membership model class '{m.group(1)}' introduced "
                            f"without the confirmed multi-membership migration")
    return findings


def main() -> int:
    findings = check()
    result = {
        "single_tenant_model_findings": findings,
        "result": "SINGLE_TENANT_MODEL_GUARD_FAILED" if findings
                  else "SINGLE_TENANT_MODEL_GUARD_PASSED",
    }
    print(__import__("json").dumps(result, indent=2))
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
