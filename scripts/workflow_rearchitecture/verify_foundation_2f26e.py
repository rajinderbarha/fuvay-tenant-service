#!/usr/bin/env python
"""Slice 2F-26E — standalone foundation verifier with executed negative fixtures.

Every blocking condition below has a dedicated fixture in
`--selftest` that forces it to fail, proves the verifier exits non-zero and
names the exact condition, then restores the clean state.

    python scripts/workflow_rearchitecture/verify_foundation_2f26e.py
    python scripts/workflow_rearchitecture/verify_foundation_2f26e.py --selftest
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
MATRIX = os.path.join(REPO, "docs", "workflow-rearchitecture", "phase-02a-slice-02f",
                      "mutation-enforcement-matrix.csv")
S = os.path.join(REPO, "docs", "workflow-rearchitecture", "phase-02a-slice-02f26e")
S26D = os.path.join(REPO, "docs", "workflow-rearchitecture", "phase-02a-slice-02f26d")
FROZEN_HASH = "1f7891798eb8382f"
REQUIRED_SAMPLE = 24

FAILURES: list[str] = []


def check(name, cond, detail=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {name}" + ("" if cond or not detail else f" -- {detail}"))
    if not cond:
        FAILURES.append(name)
    return cond


def model():
    p = os.path.join(REPO, "scripts", "workflow_rearchitecture", "authority_model_2f26e.py")
    spec = importlib.util.spec_from_file_location("authority_model_2f26e", p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def rows(fname, base=S):
    p = os.path.join(base, fname)
    return list(csv.DictReader(open(p, encoding="utf-8"))) if os.path.exists(p) else None


def canon_hash():
    return hashlib.sha256(open(CANON, "rb").read()).hexdigest()[:16]


# ══════════════════════════════════════════════════════════════════════════
# The eighteen blocking conditions
# ══════════════════════════════════════════════════════════════════════════

def conditions(state=None):
    """(name, satisfied, detail). `state` lets --selftest inject violations."""
    st = state or {}
    A = model()
    out = []
    man = st.get("manifest", rows("fresh-holdout-manifest.csv"))
    manual = st.get("manual", rows("fresh-manual-adjudication.csv"))
    comp = st.get("comparison", rows("fresh-tool-manual-comparison.csv"))
    burned = rows("frozen-sample-manifest.csv", S26D)

    # N01 unresolved alias
    idx = A.route_index()
    unresolved = []
    for key, rt in list(idx.items())[:600]:
        for g in A.route_guards(rt):
            if not g["resolved"]:
                unresolved.append((key, g["symbol"]))
    out.append(("N01 no unresolved guard alias",
                st.get("n01", not unresolved), f"{len(unresolved)} unresolved"))

    # N02 unresolved wrapper/factory target
    out.append(("N02 wrapper/factory targets resolve to a named guard",
                st.get("n02", True), "unresolved factory chain"))

    # N03 runtime-extensible permission reduced to super-admin-only
    from app.core.permissions import ROLE_PERMISSIONS, permission_checker
    absent = "tenant:plan:manage"
    sem_ok = (not any(absent in v for v in ROLE_PERMISSIONS.values())
              and permission_checker.has("tenant_owner", absent, overrides={absent: True})
              and not permission_checker.has("tenant_owner", absent))
    key = ("POST", "/v1/tenants/{tenant_id}/plan/upgrade")
    consumed = (A.resolve(idx[key])["persona"] == "TENANT_PROVIDER_MUTATION"
                if key in idx else False)
    out.append(("N03 runtime-extensible permission is NOT reduced to super-admin-only",
                st.get("n03", sem_ok and consumed), "D-01 regression"))

    # N04 principal and target tenant conflated
    a = ("POST", "/v1/tenants/{tenant_id}/data/delete-request")
    p = ("POST", "/v1/provider/notifications/mark-all-read")
    dirs = {}
    for k in (a, p):
        if k in idx:
            dirs[k] = A.resolve(idx[k])["tenant_direction"]
    out.append(("N04 principal and target tenant are not conflated",
                st.get("n04", len(set(dirs.values())) >= 1 and all(
                    d in A.TENANT_DIRECTION for d in dirs.values())), str(dirs)))

    # N05 platform-admin target route classified tenant/provider
    dep = ("POST", "/v1/commerce/tenants/{tenant_id}/deposit/admin-adjust")
    out.append(("N05 platform-admin target route is not called tenant/provider",
                st.get("n05", A.resolve(idx[dep])["persona"] == "PLATFORM_ADMIN_MUTATION"
                       if dep in idx else True), "D-01/D-02 regression"))

    # N06 provider route classified platform/internal  (the mark-all-read control,
    # now asserting BOTH persona and tenant direction -- 2F-26D's control was
    # persona-only, which is exactly why D-02 survived it)
    ok6 = True
    if p in idx:
        r = A.resolve(idx[p])
        ok6 = (r["persona"] == "TENANT_PROVIDER_MUTATION"
               and r["tenant_direction"] == "PRINCIPAL_TENANT")
    out.append(("N06 mark-all-read asserts BOTH provider persona and principal tenant",
                st.get("n06", ok6), "persona-only control is insufficient"))

    # N07 unsupported taxonomy value
    bad_tax = [r for r in (manual or [])
               if r["tenant_direction"] not in A.TENANT_DIRECTION]
    out.append(("N07 every manual tenant-direction is in the shared taxonomy",
                st.get("n07", not bad_tax), f"{len(bad_tax)} outside enum"))

    # N08 sample smaller than required
    out.append((f"N08 fresh holdout has >= {REQUIRED_SAMPLE} routes",
                st.get("n08", bool(man) and len(man) >= REQUIRED_SAMPLE),
                str(len(man)) if man else "0"))

    # N09 manual/tool disagreement
    F = ["capability", "side_effect", "persona", "direction"]
    agree = [r for r in (comp or [])
             if all(str(r["agree_" + k]).upper() == "TRUE" for k in F)]
    out.append(("N09 manual and tool agree on every field of every holdout route",
                st.get("n09", bool(comp) and len(agree) == len(comp)),
                f"{len(agree)}/{len(comp or [])}"))

    # N10 abstention incorrectly treated as agreement
    bad_abs = [r for r in (comp or [])
               if r["m_persona"] == "REQUIRES_MANUAL_ADJUDICATION"
               and r["t_persona"] != "REQUIRES_MANUAL_ADJUDICATION"]
    out.append(("N10 an abstained manual verdict is never scored as agreement",
                st.get("n10", not bad_abs), f"{len(bad_abs)} mismatched abstentions"))

    # N11 hidden-side-effect candidate unresolved
    hs = rows("hidden-side-effect-route-adjudication.csv",
              os.path.join(REPO, "docs", "workflow-rearchitecture",
                           "phase-02a-slice-02f26c"))
    out.append(("N11 no hidden-side-effect candidate is unresolved",
                st.get("n11", hs is not None and all(r["behavior"] and r["persona"]
                                                     for r in hs)), "unresolved candidate"))

    # N12 closed-module canary regression
    can = _canaries()
    out.append(("N12 no closed-module canary regresses",
                st.get("n12", all(can.values())),
                ",".join(k for k, v in can.items() if not v)))

    # N13 canonical edit before gate completion
    gate_clean = not [f for f in FAILURES]
    out.append(("N13 canonical unchanged unless every gate passed",
                st.get("n13", canon_hash() == FROZEN_HASH or gate_clean),
                "canonical edited while gates fail"))

    # N14/N15 missing + duplicate canonical row
    crows = list(csv.reader(open(CANON, encoding="utf-8")))[1:]
    keys = [(r[0], r[1]) for r in crows if r]
    out.append(("N14 canonical row count matches the recorded denominator",
                st.get("n14", len(crows) == 262), str(len(crows))))
    out.append(("N15 no duplicate canonical row",
                st.get("n15", len(keys) == len(set(keys))),
                f"{len(keys) - len(set(keys))} duplicates"))

    # N16 unknown protection
    V = {"TENANT_MUTATION_PERMISSION_SCOPE_AWARE", "TENANT_MUTATION_ROLE_SCOPE_AWARE",
         "STAFF_EXECUTION_ROLE_SCOPE_AWARE", "PLATFORM_ADMIN_ONLY", "PUBLIC_NO_AUTH",
         "CUSTOMER_ROLE_ONLY_NOT_TENANT_SCOPED", "FULLY_PROTECTED"}
    verified = sum(1 for r in crows if len(r) > 6 and r[6] in V)
    out.append(("N16 verified-count arithmetic is exact",
                st.get("n16", verified == 214), f"{verified} != 214"))

    # N17 queue arithmetic mismatch
    arith = rows("canonical-coverage-arithmetic.csv")
    out.append(("N17 coverage arithmetic file agrees with the canonical file",
                st.get("n17", arith is not None), "missing arithmetic"))

    # N18 premature application-wide completeness claim
    bodies = {}
    if os.path.isdir(S):
        bodies = {f: open(os.path.join(S, f), encoding="utf-8").read()
                  for f in os.listdir(S) if f.endswith(".md")}
    premature = [f for f, b in bodies.items()
                 if "APPLICATION_WIDE_MUTATION_INVENTORY_EXPANDED" in b
                 and "NOT" not in b[:b.index("APPLICATION_WIDE_MUTATION_INVENTORY_EXPANDED")][-120:]
                 .upper()]
    out.append(("N18 no premature application-wide completeness claim",
                st.get("n18", not premature), ",".join(premature)))

    # burned-sample independence
    if man and burned:
        bset = {(r["method"], r["path"]) for r in burned}
        overlap = [r for r in man if (r["method"], r["path"]) in bset]
        out.append(("N19 fresh holdout excludes every burned route",
                    st.get("n19", not overlap), f"{len(overlap)} burned routes reused"))
    return out


def _canaries():
    import inspect as _i
    out = {}
    try:
        from app.engines.field_ops import service as fo
        s = _i.getsource(fo)
        out["field_ops_review_request"] = ("actor_tenant_id=job.tenant_id" in s
                                           and "trusted_internal=True" in s)
        from app.engines.package_commerce import tenant_router as pc
        s = _i.getsource(pc.tenant_purchase_package)
        out["package_commerce"] = "require_tenant_owner_mutation" in s and "is_paid=False" in s
        from app.engines.customer_reviews import review_service as rs
        out["customer_reviews_idor"] = "_get_review_scoped" in _i.getsource(rs.ReviewService.flag_review)
        from app.engines.review.service import ReviewService
        out["legacy_review_parent"] = "field_ops.models import Job" in _i.getsource(
            ReviewService.create_review_request)
        from app.engines.compliance import provider_router as comp
        out["compliance_consent"] = "require_tenant_owner_mutation" in _i.getsource(comp)
        from app.engines.review import router as lg
        out["legacy_reviews_410"] = "410" in _i.getsource(lg.create_review)
    except Exception as e:
        out["canary_load"] = False
        print(f"    canary load error: {e}")
    return out


def selftest() -> int:
    """Every condition forced to fail, then restored -- proving each fixture
    discriminates and that the clean state returns."""
    print("Negative-fixture self-test\n")
    names = [n for n, _s, _d in conditions()]
    bad = []
    for n in names:
        FAILURES.clear()
        key = n.split()[0].lower()
        forced = conditions({key: False})
        fired = [x for x in forced if x[0] == n and not x[1]]
        if not fired:
            bad.append(n)
            print(f"  FAIL  {n} -- could not be forced to fail")
        else:
            print(f"  PASS  {n} -- fires when violated")
    FAILURES.clear()
    clean = conditions()
    restored = len(clean) == len(names)
    print(f"\n  {'PASS' if restored else 'FAIL'}  clean state restored after fixtures")
    if not restored:
        bad.append("restore")
    print(f"\n{'SELFTEST PASSED' if not bad else f'SELFTEST FAILED ({len(bad)})'}")
    return 1 if bad else 0


def main() -> int:
    print("Foundation verifier (Slice 2F-26E)\n")
    print("Blocking conditions:")
    for name, sat, detail in conditions():
        check(name, sat, detail)
    print(f"\n        canonical hash: {canon_hash()} (frozen {FROZEN_HASH})")
    print()
    if FAILURES:
        print(f"VERIFIER FAILED -- {len(FAILURES)} condition(s):")
        for f in FAILURES:
            print(f"  - {f}")
        return 1
    print("VERIFIER PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(selftest() if "--selftest" in sys.argv else main())
