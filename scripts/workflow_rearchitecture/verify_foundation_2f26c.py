#!/usr/bin/env python
"""Slice 2F-26C — standalone foundation verifier.

Independently executable (not merely pytest assertions), as required after
2F-26B shipped its foundation without one.

Exits non-zero on any named blocker. Every check has a negative fixture in
`tests/test_phase2f26c_foundation_validation.py`.

    python scripts/workflow_rearchitecture/verify_foundation_2f26c.py
"""
from __future__ import annotations

import csv
import hashlib
import importlib.util
import os
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, REPO)
CANON = os.path.join(REPO, "docs", "workflow-rearchitecture", "phase-02a-slice-02f",
                     "tenant-mutation-endpoint-inventory.csv")
S26C = os.path.join(REPO, "docs", "workflow-rearchitecture", "phase-02a-slice-02f26c")
FROZEN_HASH = "1f7891798eb8382f"
REQUIRED_SAMPLE = 20

FAILURES: list[str] = []


def check(name, cond, detail=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {name}" + ("" if cond or not detail else f" -- {detail}"))
    if not cond:
        FAILURES.append(name)


def resolver():
    p = os.path.join(REPO, "scripts", "workflow_rearchitecture", "resolve_guards_2f26b.py")
    spec = importlib.util.spec_from_file_location("resolve_guards_2f26b", p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def canon_hash():
    return hashlib.sha256(open(CANON, "rb").read()).hexdigest()[:16]


def main() -> int:
    print("Foundation verifier (Slice 2F-26C)\n")
    R = resolver()
    routes = R.route_index()

    # ── guard resolution ─────────────────────────────────────────────────────
    print("Guard resolution:")
    unresolved = []
    for key, rt in routes.items():
        for g in R.route_guards(rt):
            if not g["resolved"]:
                unresolved.append((key, g["symbol"]))
    check("no unresolved authorization symbol", not unresolved,
          f"{len(unresolved)} unresolved")
    check("unresolved input fails closed (returns None, never permissive)",
          R.admitted_roles([{"symbol": "require_x", "resolved_to": "?", "chain": "x",
                             "resolved": False, "permission": "", "roles_resolved": ""}])[0] is None)

    # ── tenant authority direction ───────────────────────────────────────────
    print("\nTenant authority direction:")
    admin_key = ("POST", "/v1/tenants/{tenant_id}/suspend")
    prov_key = ("POST", "/v1/provider/notifications/mark-all-read")
    if admin_key in routes:
        a = R.classify(routes[admin_key])
        check("super-admin route acting upon a tenant is NOT tenant/provider",
              a["persona"] == "PLATFORM_ADMIN_MUTATION", a["persona"])
        check("its tenant value is PLATFORM_ADMIN_TARGET_TENANT",
              a["tenant_authority"] == "PLATFORM_ADMIN_TARGET_TENANT", a["tenant_authority"])
    if prov_key in routes:
        p = R.classify(routes[prov_key])
        check("provider guard alias is NOT platform-internal",
              p["persona"] == "TENANT_PROVIDER_MUTATION", p["persona"])
    if admin_key in routes and prov_key in routes:
        check("principal and target tenant are not conflated",
              R.classify(routes[admin_key])["persona"] != R.classify(routes[prov_key])["persona"])

    # ── runtime-extensible permissions ───────────────────────────────────────
    print("\nRuntime-extensible permission semantics:")
    from app.core.permissions import ROLE_PERMISSIONS, permission_checker
    absent = "catalog:tiers:write"          # verified absent from ROLE_PERMISSIONS
    in_map = any(absent in v for v in ROLE_PERMISSIONS.values())
    check("control permission really is absent from ROLE_PERMISSIONS", not in_map)
    check("super_admin admitted for an absent permission",
          permission_checker.has("super_admin", absent))
    check("staff WITHOUT an override is denied an absent permission",
          not permission_checker.has("staff", absent))
    check("staff WITH a matching grant is admitted (runtime-extensible)",
          permission_checker.has("staff", absent, overrides={absent: True}),
          "StaffPermission override must widen admission")
    check("explicit deny overrides a grant",
          not permission_checker.has("staff", absent, overrides={absent: False}),
          "deny precedence")
    check("a runtime-extensible guard is NOT treated as statically super-admin-only",
          permission_checker.has("staff", absent, overrides={absent: True}) is True)

    # ── mixed persona must not auto-finalize ─────────────────────────────────
    print("\nMixed-persona handling:")
    mixed_key = ("GET", "/v1/commerce/tenants/{tenant_id}/deposit")
    if mixed_key in routes:
        m = R.classify(routes[mixed_key])
        check("mixed-role route with service-side ownership is NOT auto-finalized",
              m["persona"] == "REQUIRES_MANUAL_ADJUDICATION", m["persona"])

    # ── eleven hidden-side-effect candidates ─────────────────────────────────
    print("\nHidden-side-effect candidates:")
    adj = os.path.join(S26C, "hidden-side-effect-route-adjudication.csv")
    if os.path.exists(adj):
        rows = list(csv.DictReader(open(adj, encoding="utf-8")))
        check("all eleven candidates present", len(rows) == 11, str(len(rows)))
        check("no candidate remains unresolved",
              all(r["behavior"] and r["persona"] for r in rows))
        check("every DATABASE_MUTATION verdict has qualified call-path evidence",
              all(r["evidence"] != "" for r in rows if r["behavior"] == "DATABASE_MUTATION"))
    else:
        check("eleven-candidate adjudication exists", False, "file missing")

    # ── validation sample ────────────────────────────────────────────────────
    print("\nValidation sample:")
    samp = os.path.join(S26C, "mixed-persona-validation-sample.csv")
    if os.path.exists(samp):
        rows = list(csv.DictReader(open(samp, encoding="utf-8")))
        check(f"sample size >= {REQUIRED_SAMPLE}", len(rows) >= REQUIRED_SAMPLE, str(len(rows)))
        agree = [r for r in rows if r.get("agreement") == "AGREE"]
        check("tool/manual agreement is 100%", rows and len(agree) == len(rows),
              f"{len(agree)}/{len(rows)}")
    else:
        check(f"validation sample of >= {REQUIRED_SAMPLE} routes exists", False,
              "NOT RUN -- this alone blocks all canonical edits")

    # ── canonical freeze ─────────────────────────────────────────────────────
    print("\nCanonical integrity:")
    h = canon_hash()
    gate_ok = not FAILURES
    check("canonical unchanged unless every gate passed",
          h == FROZEN_HASH or gate_ok,
          f"hash {h} changed while gates failing")
    print(f"        canonical hash: {h} (frozen {FROZEN_HASH})")

    # ── documentation honesty ────────────────────────────────────────────────
    print("\nDocumentation honesty:")
    if os.path.isdir(S26C):
        bodies = {f: open(os.path.join(S26C, f), encoding="utf-8").read()
                  for f in os.listdir(S26C) if f.endswith(".md")}
        check("no document claims application-wide reconciliation",
              not any("APPLICATION_WIDE_MUTATION_INVENTORY_RECONCILED" in b
                      for b in bodies.values()))
        check("no document claims all 123 routes were adjudicated",
              not any("all 123" in b.lower() and "adjudicated" in b.lower()
                      for b in bodies.values()))
    else:
        print("  SKIP  no documentation yet")

    print()
    if FAILURES:
        print(f"VERIFIER FAILED -- {len(FAILURES)} check(s):")
        for f in FAILURES:
            print(f"  - {f}")
        return 1
    print("VERIFIER PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
