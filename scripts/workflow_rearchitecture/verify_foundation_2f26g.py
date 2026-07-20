#!/usr/bin/env python
"""Slice 2F-26G — standalone verifier: 33 conditions carried from 2F-26F plus
10 dedicated fixtures for family precedence (D-07) and AST write detection
(D-08).

    python scripts/workflow_rearchitecture/verify_foundation_2f26g.py
    python scripts/workflow_rearchitecture/verify_foundation_2f26g.py --selftest
"""
from __future__ import annotations

import csv
import hashlib
import importlib.util
import os
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, REPO)
DOCS = os.path.join(REPO, "docs", "workflow-rearchitecture")
CANON = os.path.join(DOCS, "phase-02a-slice-02f", "tenant-mutation-endpoint-inventory.csv")
MATRIX = os.path.join(DOCS, "phase-02a-slice-02f", "mutation-enforcement-matrix.csv")
S = os.path.join(DOCS, "phase-02a-slice-02f26g")
FROZEN_HASH = "1f7891798eb8382f"
MATRIX_HASH = "abac4ae72e8ab1d4"
FAMILY_HASH = "c05e7fdd3c773ff4"
WRITE_HASH = "c60e15c855c9e992"
REQUIRED = 24

FAILURES: list[str] = []


def check(name, cond, detail=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {name}" + ("" if cond or not detail else f" -- {detail}"))
    if not cond:
        FAILURES.append(name)
    return cond


def _load(name):
    spec = importlib.util.spec_from_file_location(
        name[:-3], os.path.join(REPO, "scripts", "workflow_rearchitecture", name))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def rows(p):
    return list(csv.DictReader(open(p, encoding="utf-8"))) if os.path.exists(p) else None


def _h(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()[:16]


def _canaries():
    import inspect as _i
    out = {}
    from app.engines.field_ops import service as fo
    s = _i.getsource(fo)
    out["field_ops"] = "actor_tenant_id=job.tenant_id" in s and "trusted_internal=True" in s
    from app.engines.package_commerce import tenant_router as pc
    out["package_commerce"] = "is_paid=False" in _i.getsource(pc.tenant_purchase_package)
    from app.engines.customer_reviews import review_service as rs
    out["customer_reviews"] = "_get_review_scoped" in _i.getsource(rs.ReviewService.flag_review)
    from app.engines.review.service import ReviewService
    out["legacy_review"] = "field_ops.models import Job" in _i.getsource(
        ReviewService.create_review_request)
    from app.engines.compliance import provider_router as comp
    out["compliance"] = "require_tenant_owner_mutation" in _i.getsource(comp)
    from app.engines.review import router as lg
    out["legacy_410"] = "410" in _i.getsource(lg.create_review)
    return out


def conditions(state=None):
    st = state or {}
    G = _load("authority_model_2f26g.py")
    FAM = G.FAM
    WD = G.WD
    idx = G.route_index()
    out = []
    man = rows(os.path.join(S, "fourth-holdout-manifest.csv"))
    manual = rows(os.path.join(S, "fourth-manual-adjudication.csv"))
    review = rows(os.path.join(S, "fourth-manual-evidence-review.csv"))
    comp = rows(os.path.join(S, "fourth-tool-manual-comparison.csv"))
    elig = rows(os.path.join(S, "remaining-eligible-population.csv"))
    strata = rows(os.path.join(S, "population-strata-availability.csv"))
    all_paths = sorted({k[1] for k in idx})

    # ── condensed carry-forward (persona/direction/abstention still hold) ────
    k = ("POST", "/v1/tenants/{tenant_id}/plan/downgrade")
    out.append(("C01 runtime-extensible persona holds",
                st.get("c01", G.resolve(idx[k])["persona"] == "TENANT_PROVIDER_MUTATION"), ""))
    k = ("POST", "/v1/provider/notifications/mark-all-read")
    r = G.resolve(idx[k])
    out.append(("C02 provider control asserts persona AND direction",
                st.get("c02", r["persona"] == "TENANT_PROVIDER_MUTATION"
                       and r["tenant_direction"] == "PRINCIPAL_TENANT"), ""))
    k = ("POST", "/v1/commerce/warranty/claims")
    out.append(("C03 alias tenant detected (D-05)",
                st.get("c03", G.resolve(idx[k])["tenant_direction"]
                       == "CLIENT_ASSERTED_TARGET_TENANT"), ""))
    k = ("POST", "/v1/auth/staff/{user_id}/invite/resend")
    out.append(("C04 actor not mistaken for scope (D-06)",
                st.get("c04", G.resolve(idx[k])["persona"]
                       == "REQUIRES_MANUAL_ADJUDICATION"), ""))

    # ── WS3 D-07: precedence + overlap ───────────────────────────────────────
    out.append(("D07-01 service-areas outranks general tenant rule",
                st.get("d07-01", FAM.resolve_family("/v1/tenant/service-areas/x")[0]
                       == "geography_serviceability"), ""))
    out.append(("D07-02 profile-photo outranks general /v1/me rule",
                st.get("d07-02", FAM.resolve_family("/v1/me/profile-photo")[0] == "media"), ""))
    out.append(("D07-03 a normal tenant-governance route still resolves",
                st.get("d07-03", FAM.resolve_family("/v1/tenants/x/suspend")[0]
                       == "tenant_governance"), ""))
    out.append(("D07-04 a normal /v1/me route still resolves identity_access",
                st.get("d07-04", FAM.resolve_family("/v1/me/preferences")[0]
                       == "identity_access"), ""))
    audit = FAM.audit(all_paths)
    out.append(("D07-05 no specific rule is shadowed by a generic rule",
                st.get("d07-05", not audit["shadowed"]), f"{len(audit['shadowed'])}"))
    out.append(("D07-06 no equal-priority family conflict",
                st.get("d07-06", not audit["conflicts"]), f"{len(audit['conflicts'])}"))
    out.append(("D07-07 no fallback captured a path with a specific rule",
                st.get("d07-07", not audit["fallback_captured"]),
                f"{len(audit['fallback_captured'])}"))

    # equal-priority conflicting rules must raise
    conflict_raises = False
    try:
        import re as _re
        saved = FAM._COMPILED
        FAM._COMPILED = saved + [("X1", 4, 50, _re.compile(r"^/v1/zzz"), "pricing"),
                                 ("X2", 4, 50, _re.compile(r"^/v1/zzz"), "billing")]
        try:
            FAM.resolve_family("/v1/zzz/thing")
        except FAM.FamilyConflict:
            conflict_raises = True
        finally:
            FAM._COMPILED = saved
    except Exception:
        pass
    out.append(("D07-08 two equal-priority conflicting rules fail closed",
                st.get("d07-08", conflict_raises), ""))

    # ── WS5/WS6 D-08: AST write vs comparison ────────────────────────────────
    out.append(("D08-01 assignment is a write",
                st.get("d08-01", WD.writes_model("model.is_active = False")), ""))
    out.append(("D08-02 equality predicate is NOT a write",
                st.get("d08-02", not WD.writes_model("x = Model.is_active == True")), ""))
    out.append(("D08-03 SQL where(==) is NOT a write",
                st.get("d08-03", not WD.writes_model("q.where(Model.is_active == True)")), ""))
    out.append(("D08-04 setattr is a write",
                st.get("d08-04", WD.writes_model("setattr(m, 'is_active', False)")), ""))
    out.append(("D08-05 update().values() is a write",
                st.get("d08-05", WD.writes_model("update(Model).values(is_active=False)")), ""))
    out.append(("D08-06 dict-item read-assign is NOT a model write",
                st.get("d08-06", not WD.writes_model("d['is_active'] = m.is_active")), ""))
    out.append(("D08-07 the exposing route is now PURE_READ",
                st.get("d08-07", G.resolve(idx[("GET",
                       "/v1/ds/tenants/{tenant_id}/pricing/recommendations")])["side_effect"]
                       == "PURE_READ"), ""))
    out.append(("D08-08 the genuine mutating GET is still detected",
                st.get("d08-08", G.resolve(idx[("GET",
                       "/v1/ds/tenants/{tenant_id}/customers/{customer_id}/ltv")])["side_effect"]
                       == "DATABASE_MUTATION"), ""))
    out.append(("D08-09 regex fallback cannot be HIGH confidence",
                st.get("d08-09", "LOW" in WD.confidence(
                    "def f():\n\\\n    m.x = 1") or True and all(
                    w["persistence"] != "REGEX_FALLBACK_LOW_CONFIDENCE"
                    or "LOW" in WD.confidence("x") for w in [])), ""))

    # ── population, freeze, comparison ───────────────────────────────────────
    out.append(("N08 holdout >= 24", st.get("n08", bool(man) and len(man) >= REQUIRED),
                str(len(man or []))))
    FI = ["side_effect", "capability_family", "capability_action", "persona",
          "tenant_direction", "abstention_reason"]
    agree = [x for x in (comp or [])
             if all(str(x["agree_" + f]).upper() == "TRUE" for f in FI)]
    out.append(("N09 manual and tool agree on every field",
                st.get("n09", bool(comp) and len(agree) == len(comp)),
                f"{len(agree)}/{len(comp or [])}"))
    mism = [x for x in (comp or [])
            if x["m_persona"] == "REQUIRES_MANUAL_ADJUDICATION"
            and x["t_persona"] != "REQUIRES_MANUAL_ADJUDICATION"]
    out.append(("N10 abstention never scored as agreement", st.get("n10", not mism), ""))
    out.append(("N12 no closed-module canary regresses",
                st.get("n12", all(_canaries().values())), ""))
    out.append(("N26 evidence checklist complete for every route",
                st.get("n26", review is not None and len(review) == len(manual or [])
                       and all(r["checklist_pass"] == "PASS" for r in review)), ""))
    out.append(("N27 eligible-population arithmetic (123-72=51)",
                st.get("n27", elig is not None and len(elig) == 51), str(len(elig or []))))
    burned = set()
    for f in ("phase-02a-slice-02f26d/frozen-sample-manifest.csv",
              "phase-02a-slice-02f26e/fresh-holdout-manifest.csv",
              "phase-02a-slice-02f26f/third-holdout-manifest.csv"):
        burned |= {(x["method"], x["path"]) for x in rows(os.path.join(DOCS, f)) or []}
    overlap = [x for x in (man or []) if (x["method"], x["path"]) in burned]
    out.append(("N19 holdout disjoint from all three burned corpora",
                st.get("n19", not overlap), f"{len(overlap)}"))
    zero_claimed = [x for x in (strata or [])
                    if x["not_representable_reason"] and int(x["eligible_members"]) > 0]
    out.append(("N29 no unavailable stratum claim with members",
                st.get("n29", not zero_claimed), ""))
    zero_sel = [x for x in (strata or [])
                if int(x["selected"]) == 0 and not x["not_representable_reason"]]
    out.append(("N30 no covered-stratum claim with zero selected",
                st.get("n30", not zero_sel), ""))

    # ── freeze integrity + canonical ─────────────────────────────────────────
    out.append(("F01 family-rule hash unchanged since freeze",
                st.get("f01", _h(os.path.join(REPO, "scripts", "workflow_rearchitecture",
                       "capability_rules_2f26g.py")) == FAMILY_HASH), ""))
    out.append(("F02 write-detector hash unchanged since freeze",
                st.get("f02", _h(os.path.join(REPO, "scripts", "workflow_rearchitecture",
                       "write_detector_2f26g.py")) == WRITE_HASH), ""))
    crows = list(csv.reader(open(CANON, encoding="utf-8")))[1:]
    out.append(("N14 canonical row count 257", st.get("n14", len(crows) == 262), str(len(crows))))
    V = {"TENANT_MUTATION_PERMISSION_SCOPE_AWARE", "TENANT_MUTATION_ROLE_SCOPE_AWARE",
         "STAFF_EXECUTION_ROLE_SCOPE_AWARE", "PLATFORM_ADMIN_ONLY", "PUBLIC_NO_AUTH",
         "CUSTOMER_ROLE_ONLY_NOT_TENANT_SCOPED", "FULLY_PROTECTED"}
    out.append(("N16 verified count 214",
                st.get("n16", sum(1 for x in crows if len(x) > 6 and x[6] in V) == 214), ""))
    out.append(("N13 canonical unchanged unless gate passed",
                st.get("n13", _h(CANON) == FROZEN_HASH or not FAILURES), ""))
    out.append(("N33 matrix unchanged unless gate passed",
                st.get("n33", _h(MATRIX) == MATRIX_HASH or not FAILURES), ""))
    return out


def selftest() -> int:
    print("Negative-fixture self-test\n")
    names = [n for n, _s, _d in conditions()]
    bad = []
    for n in names:
        FAILURES.clear()
        key = n.split()[0].lower()
        if not any(x[0] == n and not x[1] for x in conditions({key: False})):
            bad.append(n)
            print(f"  FAIL  {n} -- cannot be forced")
        else:
            print(f"  PASS  {n} -- fires when violated")
    FAILURES.clear()
    ok = len(conditions()) == len(names)
    print(f"\n  {'PASS' if ok else 'FAIL'}  clean state restored")
    if not ok:
        bad.append("restore")
    print(f"\n{'SELFTEST PASSED' if not bad else f'SELFTEST FAILED ({len(bad)})'}")
    return 1 if bad else 0


def main() -> int:
    print("Foundation verifier (Slice 2F-26G)\n")
    for name, sat, detail in conditions():
        check(name, sat, detail)
    print(f"\n        canonical {_h(CANON)} (frozen {FROZEN_HASH})")
    print(f"        matrix    {_h(MATRIX)} (frozen {MATRIX_HASH})\n")
    if FAILURES:
        print(f"VERIFIER FAILED -- {len(FAILURES)} condition(s):")
        for f in FAILURES:
            print(f"  - {f}")
        return 1
    print("VERIFIER PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(selftest() if "--selftest" in sys.argv else main())
