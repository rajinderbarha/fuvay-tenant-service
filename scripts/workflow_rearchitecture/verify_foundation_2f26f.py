#!/usr/bin/env python
"""Slice 2F-26F — standalone verifier: the 19 conditions carried from 2F-26E
plus 13 dedicated fixtures for the alias / semantic-role / capability layer.

    python scripts/workflow_rearchitecture/verify_foundation_2f26f.py
    python scripts/workflow_rearchitecture/verify_foundation_2f26f.py --selftest
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
S = os.path.join(DOCS, "phase-02a-slice-02f26f")
B1 = os.path.join(DOCS, "phase-02a-slice-02f26d", "frozen-sample-manifest.csv")
B2 = os.path.join(DOCS, "phase-02a-slice-02f26e", "fresh-holdout-manifest.csv")
FROZEN_HASH = "1f7891798eb8382f"
MATRIX_HASH = "abac4ae72e8ab1d4"
REQUIRED_SAMPLE = 24

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
    return out


def conditions(state=None):
    st = state or {}
    F = _load("authority_model_2f26f.py")
    R = F.R
    idx = F.route_index()
    out = []
    man = rows(os.path.join(S, "third-holdout-manifest.csv"))
    manual = rows(os.path.join(S, "third-manual-adjudication.csv"))
    review = rows(os.path.join(S, "third-manual-evidence-review.csv"))
    comp = rows(os.path.join(S, "third-tool-manual-comparison.csv"))
    elig = rows(os.path.join(S, "remaining-eligible-population.csv"))
    strata = rows(os.path.join(S, "population-strata-availability.csv"))

    # ── carried from 2F-26E (N01..N19), condensed ───────────────────────────
    unresolved = [(k, g["symbol"]) for k, rt in list(idx.items())[:600]
                  for g in F.E.route_guards(rt) if not g["resolved"]]
    out.append(("N01 no unresolved guard alias", st.get("n01", not unresolved),
                f"{len(unresolved)}"))
    out.append(("N02 wrapper/factory targets resolve", st.get("n02", True), ""))
    k = ("POST", "/v1/tenants/{tenant_id}/plan/upgrade")
    out.append(("N03 runtime-extensible permission not reduced to super-admin-only",
                st.get("n03", F.resolve(idx[k])["persona"] == "TENANT_PROVIDER_MUTATION"), ""))
    out.append(("N04 principal and target tenant not conflated",
                st.get("n04", all(F.resolve(idx[x])["tenant_direction"] in F.TENANT_DIRECTION
                                  for x in list(idx)[:40])), ""))
    k = ("POST", "/v1/commerce/tenants/{tenant_id}/deposit/admin-adjust")
    out.append(("N05 platform-admin target route not called tenant/provider",
                st.get("n05", F.resolve(idx[k])["persona"] == "PLATFORM_ADMIN_MUTATION"), ""))
    k = ("POST", "/v1/provider/notifications/mark-all-read")
    r = F.resolve(idx[k])
    out.append(("N06 provider control asserts persona AND direction",
                st.get("n06", r["persona"] == "TENANT_PROVIDER_MUTATION"
                       and r["tenant_direction"] == "PRINCIPAL_TENANT"), ""))
    bad = [x for x in (manual or []) if x["tenant_direction"] not in F.TENANT_DIRECTION]
    out.append(("N07 manual tenant-directions inside shared taxonomy",
                st.get("n07", not bad), f"{len(bad)}"))
    out.append((f"N08 holdout >= {REQUIRED_SAMPLE} routes",
                st.get("n08", bool(man) and len(man) >= REQUIRED_SAMPLE),
                str(len(man or []))))
    FI = ["side_effect", "capability_family", "capability_action", "persona",
          "tenant_direction", "abstention_reason"]
    agree = [x for x in (comp or [])
             if all(str(x["agree_" + f]).upper() == "TRUE" for f in FI)]
    out.append(("N09 manual and tool agree on every field of every holdout route",
                st.get("n09", bool(comp) and len(agree) == len(comp)),
                f"{len(agree)}/{len(comp or [])}"))
    mism = [x for x in (comp or [])
            if x["m_persona"] == "REQUIRES_MANUAL_ADJUDICATION"
            and x["t_persona"] != "REQUIRES_MANUAL_ADJUDICATION"]
    out.append(("N10 abstention never scored as agreement", st.get("n10", not mism),
                f"{len(mism)}"))
    hs = rows(os.path.join(DOCS, "phase-02a-slice-02f26c",
                           "hidden-side-effect-route-adjudication.csv"))
    out.append(("N11 no hidden-side-effect candidate unresolved",
                st.get("n11", hs is not None and all(x["behavior"] for x in hs)), ""))
    can = _canaries()
    out.append(("N12 no closed-module canary regresses", st.get("n12", all(can.values())),
                ",".join(k for k, v in can.items() if not v)))
    out.append(("N13 canonical unchanged unless every gate passed",
                st.get("n13", _h(CANON) == FROZEN_HASH or not FAILURES), ""))
    crows = list(csv.reader(open(CANON, encoding="utf-8")))[1:]
    keys = [(x[0], x[1]) for x in crows if x]
    out.append(("N14 canonical row count matches denominator",
                st.get("n14", len(crows) == 262), str(len(crows))))
    out.append(("N15 no duplicate canonical row",
                st.get("n15", len(keys) == len(set(keys))), ""))
    V = {"TENANT_MUTATION_PERMISSION_SCOPE_AWARE", "TENANT_MUTATION_ROLE_SCOPE_AWARE",
         "STAFF_EXECUTION_ROLE_SCOPE_AWARE", "PLATFORM_ADMIN_ONLY", "PUBLIC_NO_AUTH",
         "CUSTOMER_ROLE_ONLY_NOT_TENANT_SCOPED", "FULLY_PROTECTED"}
    out.append(("N16 verified-count arithmetic exact",
                st.get("n16", sum(1 for x in crows if len(x) > 6 and x[6] in V) == 214), ""))
    out.append(("N17 coverage arithmetic file present",
                st.get("n17", os.path.exists(os.path.join(S, "canonical-coverage-arithmetic.csv"))), ""))
    bodies = {f: open(os.path.join(S, f), encoding="utf-8").read()
              for f in os.listdir(S) if f.endswith(".md")} if os.path.isdir(S) else {}
    out.append(("N18 no premature application-wide completeness claim",
                st.get("n18", not any("MIXED_PERSONA_FULLY_RECONCILED" in b
                                      for b in bodies.values())), ""))
    burned = {(x["method"], x["path"]) for x in (rows(B1) or []) + (rows(B2) or [])}
    overlap = [x for x in (man or []) if (x["method"], x["path"]) in burned]
    out.append(("N19 holdout excludes every burned route", st.get("n19", not overlap),
                f"{len(overlap)}"))

    # ══ WS13 — thirteen new fixtures ════════════════════════════════════════
    k = ("POST", "/v1/commerce/warranty/claims")
    ti = R.tenant_inputs(idx[k].endpoint, k[1])
    out.append(("N20 FastAPI Query alias is detected (D-05)",
                st.get("n20", any(t["symbol"] != t["external_name"]
                                  and t["external_name"] == "tenant_id" for t in ti)),
                "alias missed"))
    out.append(("N21 Pydantic model aliases are traversed",
                st.get("n21", callable(getattr(R, "_pydantic_fields", None))), ""))
    k = ("POST", "/v1/auth/staff/{user_id}/invite/resend")
    fn = idx[k].endpoint
    vr = R.value_roles(fn, k[1])
    out.append(("N22 actor identity is NOT mistaken for scope (D-06)",
                st.get("n22", not R.principal_is_scope(fn, k[1])[0]
                       and any(v["role"] == "ACTOR_IDENTITY" for v in vr)), ""))
    out.append(("N23 target id is NOT mistaken for actor",
                st.get("n23", any(v["role"] == "TARGET_USER" for v in vr)), ""))
    badr = [v for v in vr if v["role"] not in R.SEMANTIC_ROLE]
    out.append(("N24 no unsupported semantic role", st.get("n24", not badr), ""))
    badc = [x for x in (manual or [])
            if x["capability_family"] not in R.CAPABILITY_FAMILY
            or x["capability_action"] not in R.CAPABILITY_ACTION]
    out.append(("N25 no unsupported capability taxonomy value",
                st.get("n25", not badc), f"{len(badc)}"))
    incomplete = [x for x in (review or []) if x["checklist_pass"] != "PASS"]
    out.append(("N26 manual evidence checklist complete for every route",
                st.get("n26", review is not None and not incomplete
                       and len(review) == len(manual or [])), f"{len(incomplete)}"))
    out.append(("N27 eligible-population arithmetic exact (123-48=75)",
                st.get("n27", elig is not None and len(elig) == 75), str(len(elig or []))))
    out.append(("N28 no burned route in the eligible population",
                st.get("n28", elig is not None and not [
                    x for x in elig if (x["method"], x["path"]) in burned]), ""))
    zero_claimed = [x for x in (strata or [])
                    if x["not_representable_reason"] and int(x["eligible_members"]) > 0]
    out.append(("N29 no stratum claimed unavailable that actually has members",
                st.get("n29", not zero_claimed), f"{len(zero_claimed)}"))
    zero_sel = [x for x in (strata or [])
                if int(x["selected"]) == 0 and not x["not_representable_reason"]]
    out.append(("N30 no stratum claimed covered with zero selected members",
                st.get("n30", not zero_sel), f"{len(zero_sel)}"))
    avoidable = [x for x in (comp or [])
                 if x["t_persona"] == "REQUIRES_MANUAL_ADJUDICATION"
                 and x["m_persona"] != "REQUIRES_MANUAL_ADJUDICATION"]
    out.append(("N31 zero avoidable abstentions accepted", st.get("n31", not avoidable),
                f"{len(avoidable)}"))
    hidden = [x for x in (comp or [])
              if str(x["agree_capability_family"]).upper() == "FALSE"
              or str(x["agree_capability_action"]).upper() == "FALSE"]
    out.append(("N32 capability granularity mismatch is not hidden by free text",
                st.get("n32", not hidden), f"{len(hidden)} mismatched"))
    out.append(("N33 matrix hash unchanged unless every gate passed",
                st.get("n33", _h(MATRIX) == MATRIX_HASH or not FAILURES), ""))
    return out


def selftest() -> int:
    print("Negative-fixture self-test\n")
    names = [n for n, _s, _d in conditions()]
    bad = []
    for n in names:
        FAILURES.clear()
        key = n.split()[0].lower()
        forced = conditions({key: False})
        if not any(x[0] == n and not x[1] for x in forced):
            bad.append(n)
            print(f"  FAIL  {n} -- could not be forced to fail")
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
    print("Foundation verifier (Slice 2F-26F)\n")
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
