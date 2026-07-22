"""Slice 2F-26 — canonical denominator reconciliation.

Adds ONLY routes carrying two-source evidence (tenant derived from the
principal AND a persistent side effect), computes each one's protection status
from its live dependency chain, and writes the arithmetic.

No authorization is implemented in this slice, so an unprotected addition
raises the denominator only.
"""
from __future__ import annotations

import csv
import io
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
sys.path.insert(0, os.path.dirname(__file__))
REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = os.path.join(REPO, "docs", "workflow-rearchitecture", "phase-02a-slice-02f26")
CANON = os.path.join(REPO, "docs", "workflow-rearchitecture", "phase-02a-slice-02f",
                     "tenant-mutation-endpoint-inventory.csv")

VERIFIED = {
    "TENANT_MUTATION_PERMISSION_SCOPE_AWARE", "TENANT_MUTATION_ROLE_SCOPE_AWARE",
    "STAFF_EXECUTION_ROLE_SCOPE_AWARE", "PLATFORM_ADMIN_ONLY", "PUBLIC_NO_AUTH",
    "CUSTOMER_ROLE_ONLY_NOT_TENANT_SCOPED", "FULLY_PROTECTED",
}


def norm_path(p: str) -> str:
    p = p or ""
    return p if p.startswith("/v1/") else ("/v1" + p if p.startswith("/") else p)


def guard_status(dep_names: list[str]) -> str:
    """Reuse the established guard vocabulary from the pre-existing tool."""
    import importlib
    tool = importlib.import_module("inventory_mutation_routes")
    return tool.guard_status(dep_names)


def main() -> int:
    from app.main import app
    from fastapi.routing import APIRoute

    idx = {}

    def collect(r):
        for x in getattr(r, "routes", []) or []:
            if type(x).__name__ == "_IncludedRouter":
                collect(x.original_router)
            elif isinstance(x, APIRoute):
                for m in x.methods or []:
                    idx[(m, norm_path(x.path))] = x
    collect(app)

    def deps_of(route):
        names = []
        d = getattr(route, "dependant", None)

        def rec(x):
            c = getattr(x, "call", None)
            if c is not None:
                names.append(getattr(c, "__name__", str(c)))
            for s in getattr(x, "dependencies", []) or []:
                rec(s)
        if d:
            rec(d)
        return names

    adj = list(csv.DictReader(
        open(os.path.join(OUT, "generic-prefix-tenant-mutations.csv"), encoding="utf-8")))
    confirmed = [r for r in adj if r["verdict"] == "CONFIRMED_TENANT_MUTATION_ADD"]

    rows = list(csv.reader(open(CANON, encoding="utf-8")))
    hdr, data = rows[0], rows[1:]
    existing = {(r[0], norm_path(r[1])) for r in data}

    before_total = len(data)
    before_prot = sum(1 for r in data if r[6] in VERIFIED)

    added, diff = [], []
    for c in confirmed:
        key = (c["method"], norm_path(c["path"]))
        if key in existing:
            continue
        rt = idx.get(key)
        if rt is None:
            continue
        dn = deps_of(rt)
        gs = guard_status(dn)
        endpoint = getattr(rt.endpoint, "__name__", "?")
        module = getattr(rt.endpoint, "__module__", "?")
        newrow = [
            key[0], key[1], endpoint, module, "TENANT_USER_MUTATION",
            "|".join(dn), gs,
            ("NONE -- already protected" if gs in VERIFIED
             else "REQUIRES IMPLEMENTATION -- discovered by the 2F-26 persona sweep"),
            "RUNTIME_VERIFIED + persona/side-effect evidence (Slice 2F-26): "
            f"tenant={c['tenant_evidence'][:40]} mutation={c['mutation_evidence'][:40]}",
        ]
        assert len(newrow) == len(hdr), (len(newrow), len(hdr))
        data.append(newrow)
        existing.add(key)
        added.append((key, gs))
        diff.append({"method": key[0], "path": key[1], "endpoint": endpoint,
                     "change": "ROW_ADDED", "guard_status": gs,
                     "evidence": f"tenant={c['tenant_evidence']} | mutation={c['mutation_evidence']}"})

    buf = io.StringIO()
    csv.writer(buf, lineterminator="\n").writerows([hdr] + data)
    open(CANON, "w", encoding="utf-8", newline="").write(buf.getvalue())

    after_total = len(data)
    after_prot = sum(1 for r in data if r[6] in VERIFIED)

    with open(os.path.join(OUT, "canonical-row-diff.csv"), "w", newline="",
              encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["method", "path", "endpoint", "change",
                                          "guard_status", "evidence"])
        w.writeheader(); w.writerows(diff)

    arith = [
        ["metric", "before", "delta", "after"],
        ["denominator", before_total, f"+{after_total-before_total}", after_total],
        ["numerator (protected)", before_prot, f"+{after_prot-before_prot}", after_prot],
        ["unprotected", before_total-before_prot,
         f"+{(after_total-after_prot)-(before_total-before_prot)}", after_total-after_prot],
        ["rows added", 0, len(added), len(added)],
        ["rows removed", 0, 0, 0],
    ]
    with open(os.path.join(OUT, "canonical-coverage-arithmetic.csv"), "w",
              newline="", encoding="utf-8") as f:
        csv.writer(f).writerows(arith)

    print(f"added {len(added)} rows")
    prot_added = sum(1 for _, g in added if g in VERIFIED)
    print(f"  of which already protected: {prot_added}; unprotected: {len(added)-prot_added}")
    print(f"denominator {before_total} -> {after_total}")
    print(f"numerator   {before_prot} -> {after_prot}")
    print(f"unprotected {before_total-before_prot} -> {after_total-after_prot}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
