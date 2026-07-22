"""Slice 2F-26 — behaviour, persona and coverage classification.

Consumes complete-mounted-route-inventory.csv and produces the behaviour,
persona, blind-spot, matching and reconciliation CSVs.

Persona is derived from the DEPENDENCY CHAIN and side effects, never from the
URL prefix.
"""
from __future__ import annotations

import csv
import os
import sys
from collections import Counter, defaultdict

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = os.path.join(REPO, "docs", "workflow-rearchitecture", "phase-02a-slice-02f26")
CANON = os.path.join(REPO, "docs", "workflow-rearchitecture", "phase-02a-slice-02f",
                     "tenant-mutation-endpoint-inventory.csv")

MUTATION_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
VERIFIED = {
    "TENANT_MUTATION_PERMISSION_SCOPE_AWARE", "TENANT_MUTATION_ROLE_SCOPE_AWARE",
    "STAFF_EXECUTION_ROLE_SCOPE_AWARE", "PLATFORM_ADMIN_ONLY", "PUBLIC_NO_AUTH",
    "CUSTOMER_ROLE_ONLY_NOT_TENANT_SCOPED", "FULLY_PROTECTED",
}

# Dependencies that positively identify a persona.
PLATFORM_ADMIN_DEPS = {"require_super_admin"}
CUSTOMER_DEPS = {"require_customer"}
TENANT_DEPS = {"require_tenant_owner", "require_tenant_owner_mutation",
               "require_technician", "require_staff_or_technician_only"}
PERMISSION_DEPS = {"require_permission", "require_tenant_mutation_permission", "_check"}


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


def load(path):
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def write(name, rows, header=None):
    if not rows:
        rows = [{}]
    header = header or list(rows[0].keys())
    with open(os.path.join(OUT, name), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=header, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    print(f"  wrote {name} ({len(rows)})")


def has_side_effect(r) -> bool:
    return bool(r["db_writes"] or r["external_effects"] or r["audit_effects"])


def behaviour(r) -> str:
    m, se = r["method"], has_side_effect(r)
    db, ext = bool(r["db_writes"]), bool(r["external_effects"])
    path = r["path"]
    if "/health" in path or "/meta" in path or path.endswith("/ping"):
        return "HEALTH_OR_DIAGNOSTIC"
    if m == "GET":
        # An access-audit row is NOT a business-state mutation. The canonical
        # CSV tracks mutations of business state; logging that someone read
        # something is read-instrumentation. Counting it would sweep most
        # audited reads into the mutation denominator and make the figure
        # meaningless. A GET is only a real mutating GET when it writes
        # something BEYOND audit (export generation, counters, state refresh).
        audit_only = bool(r["audit_effects"]) and not r["db_writes"] and not r["external_effects"]
        if audit_only:
            return "READ_ONLY_WITH_ACCESS_AUDIT"
        return "MUTATING_GET" if se else "READ_ONLY"
    if not se:
        # a declared mutation with no detected persistent effect
        return "READ_ONLY_POST" if m == "POST" else "READ_ONLY_PUT_OR_PATCH_FALSE_POSITIVE"
    if db and ext:
        return "DATABASE_AND_EXTERNAL_MUTATION"
    if ext:
        return "EXTERNAL_SIDE_EFFECT"
    return "DATABASE_MUTATION"


def persona(r) -> str:
    deps = set((r["auth_dependencies"] or "").split("|")) - {"", "NONE"}
    path = r["path"]
    if not deps:
        return "PUBLIC_OR_UNAUTHENTICATED_MUTATION"
    if deps & PLATFORM_ADMIN_DEPS:
        return "PLATFORM_ADMIN_MUTATION"
    if deps & CUSTOMER_DEPS:
        return "CUSTOMER_SELF_SERVICE_MUTATION"
    if deps & TENANT_DEPS:
        return "TENANT_PROVIDER_MUTATION"
    if deps & PERMISSION_DEPS:
        # permission-gated: platform-admin permission surfaces live under
        # /v1/admin, everything else is a tenant capability.
        return ("PLATFORM_ADMIN_MUTATION" if path.startswith("/v1/admin")
                else "TENANT_PROVIDER_MUTATION")
    if deps == {"get_current_user"}:
        # Bare authentication: persona must come from the AUTHORITATIVE TENANT
        # SOURCE, not the URL. A handler that derives its tenant from the
        # authenticated principal (`u.tenant_id`, `_tid(u)`, `_effective_tenant`)
        # and then mutates is a tenant/provider capability -- that is exactly
        # how the legacy review engine hid three tenant mutations behind a
        # generic /v1/reviews prefix.
        tenant_ev = (r.get("tenant_derivation") or "").strip()
        customer_ev = path.startswith("/v1/customer")
        if path.startswith("/v1/admin") or path.startswith("/v1/internal"):
            return "PLATFORM_ADMIN_MUTATION"
        if path.startswith("/v1/public") or path.startswith("/v1/webhook"):
            return "TRUSTED_CALLBACK_OR_WEBHOOK_MUTATION"
        if tenant_ev and not customer_ev:
            return "TENANT_PROVIDER_MUTATION"
        if customer_ev:
            return "CUSTOMER_SELF_SERVICE_MUTATION"
        return "MIXED_PERSONA_MUTATION"
    return "MIXED_PERSONA_MUTATION"


def main() -> int:
    rows = load(os.path.join(OUT, "complete-mounted-route-inventory.csv"))
    print(f"loaded {len(rows)} mounted routes")

    # ── behaviour ────────────────────────────────────────────────────────────
    for r in rows:
        r["behaviour"] = behaviour(r)
    write("route-side-effect-classification.csv",
          [{"method": r["method"], "path": r["path"], "endpoint": r["endpoint"],
            "module": r["module"], "behaviour": r["behaviour"],
            "db_writes": r["db_writes"], "external_effects": r["external_effects"],
            "audit_effects": r["audit_effects"]} for r in rows])

    bc = Counter(r["behaviour"] for r in rows)
    print("  behaviour:", dict(bc))

    # ── genuine mutations ────────────────────────────────────────────────────
    MUT_BEHAVIOURS = {"DATABASE_MUTATION", "EXTERNAL_SIDE_EFFECT",
                      "DATABASE_AND_EXTERNAL_MUTATION", "MUTATING_GET"}
    mutations = [r for r in rows if r["behaviour"] in MUT_BEHAVIOURS]
    for r in mutations:
        r["persona"] = persona(r)
    write("mutation-persona-classification.csv",
          [{"method": r["method"], "path": r["path"], "endpoint": r["endpoint"],
            "module": r["module"], "behaviour": r["behaviour"],
            "persona": r["persona"], "auth_dependencies": r["auth_dependencies"],
            "db_writes": r["db_writes"], "external_effects": r["external_effects"]}
           for r in mutations])
    pc = Counter(r["persona"] for r in mutations)
    print(f"  {len(mutations)} genuine mutations; personas: {dict(pc)}")

    tenant_muts = [r for r in mutations if r["persona"] == "TENANT_PROVIDER_MUTATION"]
    print(f"  TENANT_PROVIDER_MUTATION: {len(tenant_muts)}")

    # ── mutating GET / read-only POST ────────────────────────────────────────
    write("mutating-get-audit.csv",
          [{"path": r["path"], "endpoint": r["endpoint"], "module": r["module"],
            "db_writes": r["db_writes"], "external_effects": r["external_effects"],
            "audit_effects": r["audit_effects"], "persona": r.get("persona", "n/a"),
            "classification": "INTENTIONAL_MUTATING_GET"}
           for r in rows if r["behaviour"] == "MUTATING_GET"])
    write("read-only-post-audit.csv",
          [{"method": r["method"], "path": r["path"], "endpoint": r["endpoint"],
            "module": r["module"], "classification": r["behaviour"],
            "note": "declared mutation method; no persistent side effect detected"}
           for r in rows if r["behaviour"] in
           ("READ_ONLY_POST", "READ_ONLY_PUT_OR_PATCH_FALSE_POSITIVE")])

    # ── canonical matching ───────────────────────────────────────────────────
    canon = load(CANON)
    canon_keys = {(c["method"], norm_path(c["path"])): c for c in canon}
    runtime_keys = {(r["method"], norm_path(r["path"])): r for r in tenant_muts}

    matching, missing, stale = [], [], []
    for k, r in runtime_keys.items():
        if k in canon_keys:
            matching.append({"method": k[0], "path": k[1], "endpoint": r["endpoint"],
                             "classification": "EXISTING_CANONICAL_ROW_MATCH",
                             "guard_status": canon_keys[k]["guard_status"]})
        else:
            missing.append({"method": k[0], "path": k[1], "endpoint": r["endpoint"],
                            "module": r["module"], "behaviour": r["behaviour"],
                            "auth_dependencies": r["auth_dependencies"],
                            "classification": "MISSING_CANONICAL_ROW"})
    for k, c in canon_keys.items():
        if k not in runtime_keys:
            stale.append({"method": k[0], "path": k[1],
                          "endpoint": c["endpoint_name"],
                          "guard_status": c["guard_status"],
                          "classification": "CANONICAL_ROW_NOT_IN_RUNTIME_TENANT_SET"})

    write("canonical-runtime-row-matching.csv", matching + missing + stale)
    print(f"  matched={len(matching)} missing={len(missing)} unmatched_canon={len(stale)}")

    # summary for the reconciliation doc
    summary = {
        "mounted_routes": len(rows),
        "genuine_mutations": len(mutations),
        "tenant_provider": len(tenant_muts),
        "customer": pc.get("CUSTOMER_SELF_SERVICE_MUTATION", 0),
        "platform_admin": pc.get("PLATFORM_ADMIN_MUTATION", 0),
        "public_callback": pc.get("PUBLIC_OR_UNAUTHENTICATED_MUTATION", 0)
                           + pc.get("TRUSTED_CALLBACK_OR_WEBHOOK_MUTATION", 0),
        "mixed": pc.get("MIXED_PERSONA_MUTATION", 0),
        "mutating_get": bc.get("MUTATING_GET", 0),
        "read_only_post": bc.get("READ_ONLY_POST", 0)
                          + bc.get("READ_ONLY_PUT_OR_PATCH_FALSE_POSITIVE", 0),
        "canon_rows": len(canon),
        "canon_protected": sum(1 for c in canon if c["guard_status"] in VERIFIED),
        "matched": len(matching), "missing": len(missing), "unmatched_canon": len(stale),
    }
    with open(os.path.join(OUT, "_summary.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["metric", "value"])
        for k, v in summary.items():
            w.writerow([k, v])
    print("  summary:", summary)
    return 0


if __name__ == "__main__":
    sys.exit(main())
