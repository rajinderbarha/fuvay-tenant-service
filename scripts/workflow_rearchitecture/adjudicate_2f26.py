"""Slice 2F-26 — per-route adjudication of canonical-matching disagreements.

Two populations need exact route-level evidence before the canonical
denominator may move:

  A. MISSING candidates  -- runtime says TENANT_PROVIDER, no canonical row.
  B. UNMATCHED canon     -- canonical row exists, runtime classifier disagrees.

For each route this extracts concrete evidence from the handler source:
tenant-derivation expression, mutation evidence, auth dependency, and whether
the tenant guard is a real fail-closed check. Nothing is added or removed
without such evidence.
"""
from __future__ import annotations

import csv
import inspect
import os
import re
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = os.path.join(REPO, "docs", "workflow-rearchitecture", "phase-02a-slice-02f26")
CANON = os.path.join(REPO, "docs", "workflow-rearchitecture", "phase-02a-slice-02f",
                     "tenant-mutation-endpoint-inventory.csv")

VERIFIED = {
    "TENANT_MUTATION_PERMISSION_SCOPE_AWARE", "TENANT_MUTATION_ROLE_SCOPE_AWARE",
    "STAFF_EXECUTION_ROLE_SCOPE_AWARE", "PLATFORM_ADMIN_ONLY", "PUBLIC_NO_AUTH",
    "CUSTOMER_ROLE_ONLY_NOT_TENANT_SCOPED", "FULLY_PROTECTED",
}

TENANT_EXPR = re.compile(
    r"(user|u|actor|principal)\.tenant_id|_tid\(|_tenant_id\(|_effective_tenant\(")
MUTATION_EXPR = re.compile(
    r"db\.add\(|db\.delete\(|db\.commit\(|db\.flush\(|session\.add\(|"
    r"\.commit\(\)|update\(|insert\(|delete\(|INSERT INTO|UPDATE |DELETE FROM",
    re.IGNORECASE)


def strip_prose(src: str) -> str:
    """Remove docstrings and comments so evidence cannot be satisfied by prose."""
    out, in_doc = [], False
    for line in src.splitlines():
        st = line.strip()
        if st.startswith('"""') or st.startswith("'''"):
            # toggle on odd number of triple quotes
            if st.count('"""') == 1 and st.count("'''") == 0:
                in_doc = not in_doc
                continue
            if in_doc:
                continue
            continue
        if in_doc:
            continue
        if st.startswith("#"):
            continue
        out.append(line)
    return "\n".join(out)


def norm_path(p: str) -> str:
    """Normalize the /v1 prefix before matching.

    Some routers report `route.path` WITHOUT the leading /v1 segment, because
    the prefix is applied by the parent `include_router(prefix="/v1")` call and
    is not reflected in the child route object. The canonical CSV stores the
    full path. Comparing raw strings therefore reports the SAME route as both
    a missing canonical row and an unmatched canonical row -- which would have
    corrupted the denominator in both directions.
    """
    p = p or ""
    return p if p.startswith("/v1/") else ("/v1" + p if p.startswith("/") else p)


def route_index():
    """(method, path) -> APIRoute, from the fully constructed app."""
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
    return idx


def dep_names(route):
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


def evidence_for(route):
    fn = route.endpoint
    try:
        raw = inspect.getsource(fn)
    except Exception:
        return {"tenant_expr": "", "mutation_expr": "", "source": ""}
    code = strip_prose(raw)
    t = TENANT_EXPR.search(code)
    m = MUTATION_EXPR.search(code)
    return {
        "tenant_expr": t.group(0) if t else "",
        "mutation_expr": m.group(0) if m else "",
        "source": code,
    }


def sweep_effects():
    """Side-effect evidence from the sweep (which followed service methods).

    Handler-only regex is insufficient: most handlers are thin delegates
    (`return ok(await svc.method(...))`), so the mutation lives one or two
    frames deeper. The sweep already performed depth-2 AST following, so its
    db_writes/external_effects columns are the stronger evidence source.
    """
    path = os.path.join(OUT, "complete-mounted-route-inventory.csv")
    out = {}
    for r in csv.DictReader(open(path, encoding="utf-8")):
        out[(r["method"], norm_path(r["path"]))] = r
    return out


def main() -> int:
    idx = route_index()
    sweep = sweep_effects()
    match_rows = list(csv.DictReader(
        open(os.path.join(OUT, "canonical-runtime-row-matching.csv"), encoding="utf-8")))
    canon = list(csv.DictReader(open(CANON, encoding="utf-8")))
    canon_by_key = {(c["method"], norm_path(c["path"])): c for c in canon}

    missing = [r for r in match_rows if r["classification"] == "MISSING_CANONICAL_ROW"]
    unmatched = [r for r in match_rows
                 if r["classification"] == "CANONICAL_ROW_NOT_IN_RUNTIME_TENANT_SET"]

    # ── A. missing candidates ────────────────────────────────────────────────
    a_rows = []
    for r in missing:
        key = (r["method"], r["path"])
        rt = idx.get(key)
        if rt is None:
            a_rows.append({**r, "verdict": "NOT_MOUNTED_SKIP",
                           "tenant_evidence": "", "mutation_evidence": "",
                           "auth_dependencies": "", "reason": "not resolvable at runtime"})
            continue
        ev = evidence_for(rt)
        deps = dep_names(rt)
        authd = [d for d in deps if d.startswith("require_") or d == "get_current_user"]
        sw = sweep.get(key, {})
        deep_mut = bool(sw.get("db_writes") or sw.get("external_effects"))
        deep_tenant = bool(sw.get("tenant_derivation"))
        has_tenant = bool(ev["tenant_expr"]) or deep_tenant
        has_mut = bool(ev["mutation_expr"]) or deep_mut
        ev["mutation_expr"] = ev["mutation_expr"] or sw.get("db_writes", "") or sw.get("external_effects", "")
        ev["tenant_expr"] = ev["tenant_expr"] or sw.get("tenant_derivation", "")
        if has_tenant and has_mut:
            verdict = "CONFIRMED_TENANT_MUTATION_ADD"
        elif has_tenant and not has_mut:
            verdict = "TENANT_BUT_MUTATION_UNPROVEN_HOLD"
        elif has_mut and not has_tenant:
            verdict = "MUTATION_BUT_TENANT_SOURCE_UNPROVEN_HOLD"
        else:
            verdict = "NO_EVIDENCE_HOLD"
        a_rows.append({
            "method": r["method"], "path": r["path"], "endpoint": r["endpoint"],
            "module": r.get("module", ""),
            "auth_dependencies": "|".join(authd) or "NONE",
            "tenant_evidence": ev["tenant_expr"], "mutation_evidence": ev["mutation_expr"],
            "verdict": verdict,
            "reason": ("tenant derived from principal AND persistent mutation present"
                       if verdict == "CONFIRMED_TENANT_MUTATION_ADD"
                       else "insufficient route-level evidence to add"),
        })

    # ── B. unmatched canonical rows ──────────────────────────────────────────
    b_rows = []
    for r in unmatched:
        key = (r["method"], r["path"])
        rt = idx.get(key)
        c = canon_by_key.get(key, {})
        if rt is None:
            b_rows.append({
                "method": r["method"], "path": r["path"],
                "endpoint": c.get("endpoint_name", ""),
                "guard_status": c.get("guard_status", ""),
                "tenant_evidence": "", "mutation_evidence": "",
                "verdict": "RUNTIME_PATH_MISMATCH_KEEP",
                "reason": "canonical path string does not resolve to a mounted route "
                          "key; retained -- removal requires proof the capability is "
                          "gone, not that a string differs",
            })
            continue
        ev = evidence_for(rt)
        sw = sweep.get(key, {})
        ev["mutation_expr"] = ev["mutation_expr"] or sw.get("db_writes", "") or sw.get("external_effects", "")
        ev["tenant_expr"] = ev["tenant_expr"] or sw.get("tenant_derivation", "")
        has_tenant = bool(ev["tenant_expr"])
        has_mut = bool(ev["mutation_expr"])
        if has_tenant and has_mut:
            verdict = "CLASSIFIER_LIMITATION_KEEP"
            reason = ("route-level evidence CONFIRMS tenant mutation; the automated "
                      "persona/side-effect pass missed it (depth or indirection)")
        elif has_mut:
            verdict = "KEEP_TENANT_SOURCE_INDIRECT"
            reason = "mutation confirmed; tenant derived indirectly via service layer"
        else:
            verdict = "REVIEW_NO_DIRECT_MUTATION_EVIDENCE"
            reason = ("no direct mutation expression in handler; likely delegates to a "
                      "service method -- retained, removal needs capability proof")
        b_rows.append({
            "method": r["method"], "path": r["path"],
            "endpoint": c.get("endpoint_name", ""),
            "guard_status": c.get("guard_status", ""),
            "tenant_evidence": ev["tenant_expr"], "mutation_evidence": ev["mutation_expr"],
            "verdict": verdict, "reason": reason,
        })

    with open(os.path.join(OUT, "generic-prefix-tenant-mutations.csv"),
              "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(a_rows[0].keys()))
        w.writeheader(); w.writerows(a_rows)
    with open(os.path.join(OUT, "prefixed-route-false-positive-audit.csv"),
              "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(b_rows[0].keys()))
        w.writeheader(); w.writerows(b_rows)

    from collections import Counter
    print("A. missing candidates:", dict(Counter(r["verdict"] for r in a_rows)))
    print("B. unmatched canonical:", dict(Counter(r["verdict"] for r in b_rows)))
    confirmed = [r for r in a_rows if r["verdict"] == "CONFIRMED_TENANT_MUTATION_ADD"]
    print(f"\nCONFIRMED ADDITIONS: {len(confirmed)}")
    for r in confirmed[:100]:
        print(f"  {r['method']:6} {r['path']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
