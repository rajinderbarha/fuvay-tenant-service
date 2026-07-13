"""
MODULE-L5-03: tenant pricing-floor guard (fail-closed).

The platform floor (a tenant's price may not fall below the admin/master-service
minimum, nor exceed the maximum, nor be negative) is a financial-integrity
invariant. MODULE-L5-03 found it was bypassable:
  * create path used truthiness (`if tenant_min and ...`), so Decimal('0')
    skipped the check;
  * update path (`update_enabled_service`) did NO price validation at all and
    blindly persisted any provided price.

Both are now routed through `_validate_price_overrides`. This guard fails closed
if either mutation path stops calling that validator, or if the validator loses
its floor / ceiling / negative checks.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
TS = ROOT / "app" / "engines" / "admin_catalog" / "tenant_service.py"

MUTATION_METHODS = ("enable_service", "update_enabled_service")


def check() -> list[str]:
    findings = []
    text = TS.read_text(encoding="utf-8")

    # The validator must exist and enforce all three invariants.
    if "_validate_price_overrides" not in text:
        return ["_validate_price_overrides helper missing from tenant_service.py"]
    for marker in ("TENANT_PRICE_BELOW_ADMIN_MIN", "TENANT_PRICE_ABOVE_ADMIN_MAX", "TENANT_PRICE_NEGATIVE"):
        if marker not in text:
            findings.append(f"validator missing invariant: {marker}")

    # Both mutation paths must call the validator.
    for meth in MUTATION_METHODS:
        m = re.search(r'async def ' + meth + r'\(', text)
        if not m:
            findings.append(f"mutation method '{meth}' not found (renamed?) — floor coverage unverifiable")
            continue
        start = m.start()
        nxt = re.search(r'\n    async def ', text[start + 1:])
        body = text[start:start + 1 + (nxt.start() if nxt else len(text))]
        if "_validate_price_overrides" not in body:
            findings.append(f"'{meth}' does not call _validate_price_overrides — platform floor bypassable")

    # The floor check must use `is not None`, not truthiness (the original bug).
    if re.search(r'if tenant_min and svc\.min_price and', text):
        findings.append("floor check uses truthiness (`if tenant_min and ...`) — Decimal('0') bypass")
    return findings


def main() -> int:
    findings = check()
    out = {
        "pricing_floor_findings": findings,
        "result": "PRICING_FLOOR_GUARD_FAILED" if findings else "PRICING_FLOOR_GUARD_PASSED",
    }
    print(__import__("json").dumps(out, indent=2))
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
