"""
MODULE-L5-04: systemic cross-tenant isolation guard (fail-closed).

The audit found the same anti-pattern in multiple engines: a tenant-isolation
control that gates on `actor_role == "tenant_owner"` ONLY, which fails open for
every other tenant-scoped role (staff, technician, ...). Two were actively
exploitable (serviceability service areas, booking customer-PII); others were
defense-in-depth (catalog, deposits).

This guard locks in the fixes: for each known isolation method it asserts the
vulnerable single-role gate is gone and the robust PLATFORM_ROLES-denylist
pattern is present. Fails closed if any regresses.

It is intentionally a fixed registry of the audited methods (not a broad grep),
because legitimate `actor_role == "tenant_owner"` uses exist elsewhere (positive
allowlists with fail-closed defaults, marketplace matching) that must NOT be
flagged.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent

# (file, method, must-not-contain vulnerable gate, must-contain robust marker)
TARGETS = [
    ("app/engines/serviceability/service.py", "_assert_owns_tenant"),
    ("app/engines/admin_catalog/tenant_service.py", "_assert_tenant_owns_ts"),
    ("app/engines/booking/service.py", "_assert_can_access_booking"),
    ("app/engines/platform_commerce/service.py", "_assert_owns_tenant_deposit"),
]
VULN_GATE = re.compile(r'if self\.actor_role == "tenant_owner"')


def _method_body(text: str, name: str) -> str | None:
    m = re.search(r'\n    def ' + re.escape(name) + r'\(.*?(?=\n    (async )?def |\nclass )', text, re.S)
    return m.group(0) if m else None


def _check_booking_mutation_coverage() -> list[str]:
    """Every BookingService method that loads a Booking by id must call
    _assert_can_access_booking (MODULE-L5-05: request/accept/reject_reschedule,
    add_note, void_booking previously loaded a booking and mutated it with no
    tenant/customer scope check)."""
    findings = []
    # create_booking re-fetches only via the actor's OWN Redis idempotency key
    # (inherently the caller's booking) — not an arbitrary-id access.
    ALLOW = {"create_booking"}
    text = (ROOT / "app/engines/booking/service.py").read_text(encoding="utf-8")
    for m in re.finditer(r'\n    async def (\w+)\(.*?(?=\n    (async )?def )', text, re.S):
        name, body = m.group(1), m.group(0)
        if name in ALLOW:
            continue
        loads = re.search(r'select\(Booking\)\.where\(Booking\.id ==|db\.get\(Booking,', body)
        if loads and "_assert_can_access_booking" not in body:
            findings.append(f"booking/service.py:{name} loads a Booking by id but never calls "
                            f"_assert_can_access_booking (cross-tenant mutation/read risk)")
    return findings


def check() -> list[str]:
    findings = _check_booking_mutation_coverage()
    for rel, meth in TARGETS:
        text = (ROOT / rel).read_text(encoding="utf-8")
        body = _method_body(text, meth)
        if body is None:
            findings.append(f"{rel}:{meth} not found (renamed?) — isolation unverifiable")
            continue
        if VULN_GATE.search(body):
            findings.append(f"{rel}:{meth} still uses the vulnerable `actor_role == \"tenant_owner\"` "
                            f"single-role gate (fails open for staff/technician)")
        if "PLATFORM_ROLES" not in body and "_PLATFORM" not in body:
            findings.append(f"{rel}:{meth} does not confine via a PLATFORM_ROLES denylist")
    return findings


def main() -> int:
    findings = check()
    out = {
        "cross_tenant_isolation_findings": findings,
        "audited_methods": len(TARGETS),
        "result": "CROSS_TENANT_ISOLATION_GUARD_FAILED" if findings else "CROSS_TENANT_ISOLATION_GUARD_PASSED",
    }
    print(__import__("json").dumps(out, indent=2))
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
