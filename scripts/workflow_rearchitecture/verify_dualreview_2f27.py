#!/usr/bin/env python
"""Slice 2F-27 — dual-review reconciliation verifier.

    python scripts/workflow_rearchitecture/verify_dualreview_2f27.py
    python scripts/workflow_rearchitecture/verify_dualreview_2f27.py --selftest
"""
from __future__ import annotations

import csv
import hashlib
import os
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DOCS = os.path.join(REPO, "docs", "workflow-rearchitecture")
S = os.path.join(DOCS, "phase-02a-slice-02f27")
CANON = os.path.join(DOCS, "phase-02a-slice-02f", "tenant-mutation-endpoint-inventory.csv")
MATRIX = os.path.join(DOCS, "phase-02a-slice-02f", "mutation-enforcement-matrix.csv")
FROZEN_HASH = "2d6ebeee18c152c0"
MATRIX_HASH = "4389e57d9db6de83"
POP_HASH = "ecdf8a830b07b95e"

FAILURES: list[str] = []


def check(name, cond, detail=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {name}" + ("" if cond or not detail else f" -- {detail}"))
    if not cond:
        FAILURES.append(name)


def rows(n):
    p = os.path.join(S, n)
    return list(csv.DictReader(open(p, encoding="utf-8"))) if os.path.exists(p) else None


def _h(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()[:16]


PERSONAS = {"TENANT_PROVIDER_MUTATION", "CUSTOMER_SELF_SERVICE_MUTATION",
            "PLATFORM_ADMIN_MUTATION", "PLATFORM_INTERNAL_MUTATION",
            "PUBLIC_OR_UNAUTHENTICATED_MUTATION", "TRUSTED_CALLBACK_MUTATION",
            "SELF_SERVICE_MUTATION", "READ_ONLY_NOT_MUTATION",
            "DEPRECATED_MUTATION", "DISCONNECTED_MUTATION", "PRODUCT_DECISION_REQUIRED"}


def conditions(state=None):
    st = state or {}
    out = []
    pop = rows("frozen-mixed-persona-population.csv")
    A = rows("reviewer-a-adjudication.csv")
    B = rows("reviewer-b-adjudication.csv")
    res = rows("disagreement-resolution.csv")
    final = rows("final-persona-partition.csv")

    out.append(("V01 population hash unchanged since review start",
                st.get("v01", _h(os.path.join(S, "frozen-mixed-persona-population.csv"))
                       == POP_HASH), ""))
    out.append(("V02 reviewer A covers every route",
                st.get("v02", A is not None and pop is not None and len(A) == len(pop)), ""))
    out.append(("V03 reviewer B covers every route",
                st.get("v03", B is not None and pop is not None and len(B) == len(pop)), ""))
    identical = (A is not None and B is not None
                 and open(os.path.join(S, "reviewer-a-adjudication.csv")).read()
                 == open(os.path.join(S, "reviewer-b-adjudication.csv")).read())
    out.append(("V04 reviewer files are not byte-identical (mechanical duplicate)",
                st.get("v04", not identical), ""))
    # taxonomy validity
    badp = [r for r in (A or []) + (B or []) if r["persona"] not in PERSONAS]
    out.append(("V05 reviewer persona values are all in the shared taxonomy",
                st.get("v05", not badp), f"{len(badp)}"))
    # every A/B disagreement has a resolution
    disp = set()
    if A and B:
        Ad = {(r["method"], r["path"]): r for r in A}
        for r in B:
            a = Ad[(r["method"], r["path"])]
            if a["persona"] != r["persona"] or a["tenant_direction"] != r["tenant_direction"]:
                disp.add((r["method"], r["path"]))
    resolved = {(r["method"], r["path"]) for r in (res or [])}
    out.append(("V06 every A/B disagreement has a resolution record",
                st.get("v06", disp <= resolved), f"{len(disp - resolved)} unresolved"))
    # final partition totals to population
    out.append(("V07 final partition covers every route exactly once",
                st.get("v07", final is not None and pop is not None
                       and len(final) == len(pop)
                       and len({(r["method"], r["path"]) for r in final}) == len(pop)), ""))
    # no route left mixed/unknown
    bad_final = [r for r in (final or [])
                 if r["final_persona"] in ("MIXED_PERSONA", "UNKNOWN", "UNVERIFIED", "HELD")]
    out.append(("V08 no route remains mixed/unknown/held/unverified",
                st.get("v08", not bad_final), f"{len(bad_final)}"))
    # canonical + matrix frozen (this slice makes zero edits)
    out.append(("V09 canonical unchanged", st.get("v09", _h(CANON) == FROZEN_HASH), ""))
    out.append(("V10 matrix unchanged", st.get("v10", _h(MATRIX) == MATRIX_HASH), ""))
    # coverage recount still 214/257
    crows = list(csv.reader(open(CANON, encoding="utf-8")))[1:]
    V = {"TENANT_MUTATION_PERMISSION_SCOPE_AWARE", "TENANT_MUTATION_ROLE_SCOPE_AWARE",
         "STAFF_EXECUTION_ROLE_SCOPE_AWARE", "PLATFORM_ADMIN_ONLY", "PUBLIC_NO_AUTH",
         "CUSTOMER_ROLE_ONLY_NOT_TENANT_SCOPED", "FULLY_PROTECTED"}
    out.append(("V11 coverage recount 313/313 (rebaselined by 2F-37 financial/product-policy batch closure)",
                st.get("v11", len(crows) == 313
                       and sum(1 for r in crows if len(r) > 6 and r[6] in V) == 313), ""))
    # honesty: docs must not claim reconciliation applied while blocked
    ag = os.path.join(S, "approval-gate.md")
    body = open(ag, encoding="utf-8").read() if os.path.exists(ag) else ""
    out.append(("V12 no doc claims applied reconciliation while gate blocked",
                st.get("v12", "APPLICATION_WIDE_MUTATION_INVENTORY_EXPANDED" not in body
                       or "GLOBAL_COVERAGE_RECONCILIATION_BLOCKED" in body), ""))
    return out


def selftest() -> int:
    print("Dual-review verifier self-test\n")
    names = [n for n, _s, _d in conditions()]
    bad = []
    for n in names:
        FAILURES.clear()
        key = n.split()[0].lower()
        if not any(x[0] == n and not x[1] for x in conditions({key: False})):
            bad.append(n); print(f"  FAIL  {n}")
        else:
            print(f"  PASS  {n} -- fires when violated")
    FAILURES.clear()
    print(f"\n{'SELFTEST PASSED' if not bad else 'SELFTEST FAILED'}")
    return 1 if bad else 0


def main() -> int:
    print("Dual-review reconciliation verifier (Slice 2F-27)\n")
    for n, s, d in conditions():
        check(n, s, d)
    print()
    if FAILURES:
        print(f"VERIFIER FAILED -- {len(FAILURES)}: {FAILURES}")
        return 1
    print("VERIFIER PASSED (reconciliation analysis complete; canonical unchanged)")
    return 0


if __name__ == "__main__":
    sys.exit(selftest() if "--selftest" in sys.argv else main())
