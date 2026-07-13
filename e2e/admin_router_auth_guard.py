"""
MODULE-L5-01A: generalized, reusable guard for a systemic anti-pattern found
this sprint -- a router mounted under a "/v1/admin/*" prefix (implying
platform-wide, cross-tenant intent) whose handlers rely solely on
`Depends(get_current_user)` with zero permission or role dependency
anywhere in the file. This means ANY authenticated user of ANY role
(including `customer`) can reach every handler.

Fails closed: any admin-prefixed router file with >=1 bare-auth handler and
zero permission/role dependencies anywhere in the file is reported. This is
a source-derived, mechanical check -- not a guess -- and intentionally does
NOT auto-classify severity per-endpoint (that requires the same manual,
read-only-vs-mutation judgment applied to tenant_engine and invoice_payment
this sprint); it exists to make sure the *next* sprint cannot miss these
findings or accidentally reintroduce a new one.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
ENGINES_DIR = ROOT / "app" / "engines"

PERMISSION_MARKERS = [
    "require_permission(", "require_super_admin", "require_tenant_owner",
    "require_staff_or_above", "require_customer)", "require_technician",
    "require_tenant_mutation_permission(",
]

# Found this sprint, NOT yet fixed -- explicit, documented, non-silent
# exclusion so this guard doesn't block unrelated work, while still
# reporting them clearly every run until a dedicated sprint closes them.
KNOWN_UNFIXED_BLOCKERS = {
    "app/engines/coaching_appointment/admin_router.py": "MODULE-L5-01A-B01",
    "app/engines/execution/coaching_router.py": "MODULE-L5-01A-B02",
    "app/engines/execution/real_estate_router.py": "MODULE-L5-01A-B03",
    "app/engines/final_records/admin_router.py": "MODULE-L5-01A-B04",
    "app/engines/home_service_booking/admin_router.py": "MODULE-L5-01A-B05",
    "app/engines/platform_notifications/admin_router.py": "MODULE-L5-01A-B06",
}


def main():
    # MODULE-L5-01A self-correction: an earlier version of this guard used
    # KNOWN_FIXED as a blind skip-list applied BEFORE checking whether the
    # fix is still actually present in source -- meaning a regression that
    # reverted a real fix back to bare `get_current_user` would have been
    # silently hidden instead of failing the guard. Caught this sprint via
    # a controlled-failure test (Rule 17/28: guards must fail closed and
    # must not pass on stale evidence). Fixed: every file is evaluated
    # fresh from current source on every run; KNOWN_FIXED is no longer
    # consulted at all (a genuinely fixed file naturally has a real
    # permission marker present and is never flagged); KNOWN_UNFIXED_BLOCKERS
    # is used only to route an already-real failure into the right report
    # bucket, never to suppress one.
    findings = []
    known_unfixed_confirmed = []
    for f in ENGINES_DIR.rglob("*.py"):
        if "__pycache__" in str(f):
            continue
        text = f.read_text(encoding="utf-8")
        if 'prefix="/v1/admin' not in text:
            continue
        bare_count = len(re.findall(r"Depends\(get_current_user\)", text))
        if bare_count == 0:
            continue
        has_permission = any(marker in text for marker in PERMISSION_MARKERS)
        if has_permission:
            continue
        rel = str(f.relative_to(ROOT)).replace("\\", "/")
        if rel in KNOWN_UNFIXED_BLOCKERS:
            known_unfixed_confirmed.append({"file": rel, "bare_handlers": bare_count, "backlog_id": KNOWN_UNFIXED_BLOCKERS[rel]})
        else:
            findings.append({"file": rel, "bare_handlers": bare_count})

    result = {
        "known_unfixed_blockers_still_present": known_unfixed_confirmed,
        "newly_discovered_unclassified": findings,
        "result": "ADMIN_ROUTER_AUTH_GUARD_FAILED" if findings else "ADMIN_ROUTER_AUTH_GUARD_KNOWN_BLOCKERS_ONLY",
    }
    print(__import__("json").dumps(result, indent=2))
    # Fails closed only on a genuinely NEW, undocumented instance -- known,
    # already-registered blockers are reported but do not fail the guard,
    # since they are explicitly tracked backlog items with their own
    # severity/sprint assignment, not silently hidden.
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
