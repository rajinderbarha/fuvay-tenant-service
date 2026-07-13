"""
MODULE-L5-02: tenant-governance fail-closed guards.

Combines three bounded, safe invariants for the canonical tenant lifecycle:

1. tenant-state-registry / illegal-transition guard
   - VALID_TRANSITIONS keys and targets must all be declared TENANT_STATES
     (no state referenced that isn't in the canonical registry);
   - terminal state(s) must have no outgoing transitions;
   - no state may transition to itself.
   This proves there is one authoritative, well-formed state machine
   (tenant_engine/constants.py) rather than ad-hoc status strings.

2. tenant-scope registration guard
   - every path-parameterised `/{tenant_id}` route in tenant_engine/router.py
     (the tenant-admin lifecycle surface) must call
     `_assert_own_tenant_or_super_admin(...)` in its handler body. This
     extends the MODULE-L5-01A tenant_scope_guard invariant into the L5-02
     guard set and fails closed if a new cross-tenant IDOR surface is added.

3. canonical-onboarding guard
   - the tenant lifecycle onboarding routes live on the single canonical
     tenant router (`/v1/tenants/onboarding/*`); this guard records their
     presence so a *second* competing onboarding lifecycle router cannot be
     silently reintroduced under tenant_engine without notice.

Controlled-failure coverage: tests/test_module_l5_02_tenant_governance.py.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
TENANT = ROOT / "app" / "engines" / "tenant_engine"

TERMINAL_STATES = {"terminated"}


def _load_constants():
    import importlib.util
    spec = importlib.util.spec_from_file_location("_tenant_constants", TENANT / "constants.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.TENANT_STATES, mod.VALID_TRANSITIONS


def check_state_machine(states=None, transitions=None) -> list[str]:
    findings = []
    if states is None or transitions is None:
        states, transitions = _load_constants()
    state_set = set(states)
    for src, targets in transitions.items():
        if src not in state_set:
            findings.append(f"transition source '{src}' not in TENANT_STATES")
        for t in targets:
            if t not in state_set:
                findings.append(f"transition target '{t}' (from '{src}') not in TENANT_STATES")
            if t == src:
                findings.append(f"self-transition '{src}'->'{t}' not allowed")
    for term in TERMINAL_STATES:
        if transitions.get(term):
            findings.append(f"terminal state '{term}' has outgoing transitions {transitions[term]}")
    return findings


def check_tenant_scope() -> list[str]:
    findings = []
    text = (TENANT / "router.py").read_text(encoding="utf-8")
    # Find each handler whose decorator path contains "{tenant_id}" and ensure
    # the handler body (up to the next @router decorator) asserts scope.
    lines = text.split("\n")
    dec_idxs = [i for i, l in enumerate(lines) if re.search(r'@router\.(get|post|put|patch|delete)\(', l)]
    for n, i in enumerate(dec_idxs):
        end = dec_idxs[n + 1] if n + 1 < len(dec_idxs) else len(lines)
        block = "\n".join(lines[i:end])
        # Only path-parameterised tenant routes are the cross-tenant surface.
        if "{tenant_id}" not in block:
            continue
        if "_assert_own_tenant_or_super_admin" not in block and "require_super_admin" not in block:
            # capture the path for the message
            m = re.search(r'["\']([^"\']*\{tenant_id\}[^"\']*)["\']', block)
            path = m.group(1) if m else "?"
            findings.append(f"/{{tenant_id}} route '{path}' lacks _assert_own_tenant_or_super_admin")
    return findings


def check_single_onboarding() -> list[str]:
    """The canonical onboarding lifecycle lives on tenant_engine/router.py.
    Fail if a second file under tenant_engine also defines onboarding
    activate/reject lifecycle routes (a competing lifecycle)."""
    findings = []
    canonical = TENANT / "router.py"
    for f in TENANT.glob("*.py"):
        if f.name == "router.py" or f.name.startswith("__"):
            continue
        t = f.read_text(encoding="utf-8")
        if re.search(r'onboarding/\{[^}]+\}/(activate|reject)', t):
            findings.append(f"competing onboarding lifecycle route in {f.name} (should be canonical router.py only)")
    if not re.search(r'onboarding/\{[^}]+\}/activate', canonical.read_text(encoding="utf-8")):
        findings.append("canonical router.py missing onboarding activate route (lifecycle moved unexpectedly)")
    return findings


def check() -> dict:
    return {
        "state_machine": check_state_machine(),
        "tenant_scope": check_tenant_scope(),
        "single_onboarding": check_single_onboarding(),
    }


def main() -> int:
    res = check()
    findings = [f"[{k}] {m}" for k, ms in res.items() for m in ms]
    out = {
        "tenant_governance_findings": findings,
        "result": "TENANT_GOVERNANCE_GUARD_FAILED" if findings else "TENANT_GOVERNANCE_GUARD_PASSED",
    }
    print(__import__("json").dumps(out, indent=2))
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
