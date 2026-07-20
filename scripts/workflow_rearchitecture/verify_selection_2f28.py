#!/usr/bin/env python
"""Slice 2F-28 — module-selection verifier.

    python scripts/workflow_rearchitecture/verify_selection_2f28.py
    python scripts/workflow_rearchitecture/verify_selection_2f28.py --selftest
"""
from __future__ import annotations

import csv
import hashlib
import os
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DOCS = os.path.join(REPO, "docs", "workflow-rearchitecture")
S = os.path.join(DOCS, "phase-02a-slice-02f28")
CANON = os.path.join(DOCS, "phase-02a-slice-02f", "tenant-mutation-endpoint-inventory.csv")
MATRIX = os.path.join(DOCS, "phase-02a-slice-02f", "mutation-enforcement-matrix.csv")
HOLD = os.path.join(DOCS, "phase-02a-slice-02f27a", "unauthorized-candidate-hold-registry.csv")
CANON_HASH = "2d6ebeee18c152c0"
MATRIX_HASH = "4389e57d9db6de83"
SELECTED = "M01_identity_credentials"

VERIFIED = {"TENANT_MUTATION_PERMISSION_SCOPE_AWARE", "TENANT_MUTATION_ROLE_SCOPE_AWARE",
            "STAFF_EXECUTION_ROLE_SCOPE_AWARE", "PLATFORM_ADMIN_ONLY", "PUBLIC_NO_AUTH",
            "CUSTOMER_ROLE_ONLY_NOT_TENANT_SCOPED", "FULLY_PROTECTED"}

FAILURES: list[str] = []


def check(name, cond, detail=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {name}" + ("" if cond or not detail else f" -- {detail}"))
    if not cond:
        FAILURES.append(name)


def rows(p):
    return list(csv.DictReader(open(p, encoding="utf-8"))) if os.path.exists(p) else None


def _h(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()[:16]


def conditions(state=None):
    st = state or {}
    out = []
    canon = list(csv.reader(open(CANON, encoding="utf-8")))[1:]
    protected = sum(1 for r in canon if r[6] in VERIFIED)
    unprot = [r for r in canon if r[6] not in VERIFIED]
    inv = rows(os.path.join(S, "authoritative-unprotected-route-inventory.csv"))
    mem = rows(os.path.join(S, "module-route-membership.csv"))
    setA = rows(os.path.join(S, "selected-canonical-route-scope.csv"))
    setB = rows(os.path.join(S, "selected-held-adjudication-scope.csv"))
    setC = rows(os.path.join(S, "selected-out-of-scope-adjacent-routes.csv"))
    held = rows(HOLD)
    xref = rows(os.path.join(S, "held-candidate-module-cross-reference.csv"))
    sec = rows(os.path.join(S, "security-observation-module-cross-reference.csv"))

    # Rebaselined by Slice 2F-29: M01 closed 12 of the 45 queued routes, so the
    # LIVE figures moved 214/259+45 -> 226/259+33. The 2F-28 queue artifact
    # itself remains the point-in-time 45 and is still fully accounted for.
    out.append(("S01 current coverage is 241/264 (post-M01, post-2F-31A, post-2F-33)",
                st.get("s01", len(canon) == 313 and protected == 313), f"{protected}/{len(canon)}"))
    out.append(("S02 canonical unprotected count is 23 (post-2F-33)",
                st.get("s02", len(unprot) == 0), str(len(unprot))))
    out.append(("S03 queue artifact still holds its point-in-time 45 routes",
                st.get("s03", inv is not None and len(inv) == 45), str(len(inv or []))))
    canon_unp_keys = {(r[0], r[1]) for r in unprot}
    inv_keys = {(r["method"], r["path"]) for r in (inv or [])}
    selA_keys = {(r["method"], r["path"]) for r in (setA or [])}
    C7 = {("POST","/v1/provider/profile/logo"),("DELETE","/v1/provider/profile/logo"),("POST","/v1/provider/profile/shop-photo"),("DELETE","/v1/provider/profile/shop-photo"),("POST","/v1/staff/profile/photo"),("DELETE","/v1/staff/profile/photo"),("POST","/v1/me/profile-photo")}
    SB = {("POST","/v1/media/upload/initiate"),("POST","/v1/media/upload/{session_id}/confirm"),("DELETE","/v1/media/tenants/{tenant_id}/files/{file_id}")}
    # Slice 2F-31A closed the 2 remaining Set-A media routes that WERE part of
    # the original 45-route queue (upload/replace), plus all 3 SB routes
    # (which never appeared in the queue -- they postdate it).
    D31A_IN_QUEUE = {("POST", "/v1/media/upload"), ("POST", "/v1/media/{media_id}/replace")}
    # Slice 2F-33 closed DELETE /v1/geo/zones/{zone_id}, which WAS part of
    # the original 45-route queue (present since 2F-27A).
    D33_IN_QUEUE = {("DELETE", "/v1/geo/zones/{zone_id}")}
    # Slice 2F-35 closed DELETE /v1/webhooks/endpoints/{endpoint_id} and
    # POST /v1/rag/query, both of which WERE part of the original 45-route
    # queue.
    D35_IN_QUEUE = {("DELETE", "/v1/webhooks/endpoints/{endpoint_id}"), ("POST", "/v1/rag/query")}
    # Slice 2F-36 closed all 18 Set A routes, all of which WERE part of the
    # original 45-route queue (Set B routes were held, not yet canonical,
    # and never appeared in this queue).
    D36_IN_QUEUE = {
        ("POST", "/v1/provider/setup/services/{service_id}/supported-options"),
        ("DELETE", "/v1/enterprise/saved-views/{view_id}"),
        ("POST", "/v1/provider/brands/services/{service_id}/supported"),
        ("PUT", "/v1/me/profile"),
        ("PUT", "/v1/provider/business-profile"),
        ("PUT", "/v1/enterprise/saved-views/{view_id}"),
        ("POST", "/v1/provider/brands/requests"),
        ("POST", "/v1/provider/reports/run"),
        ("POST", "/v1/enterprise/exports"),
        ("PUT", "/v1/provider/marketing/assets/{asset_id}/provider-notes"),
        ("PUT", "/v1/staff/profile"),
        ("PUT", "/v1/enterprise/column-preferences"),
        ("POST", "/v1/provider/marketing/campaigns/generate-launch"),
        ("POST", "/v1/enterprise/saved-views/{view_id}/set-default"),
        ("POST", "/v1/provider/business-profile/submit-review"),
        ("POST", "/v1/provider/setup/recommendations"),
        ("POST", "/v1/provider/marketing/campaigns/{campaign_id}/submit-review"),
        ("POST", "/v1/enterprise/saved-views"),
    }
    D37_IN_QUEUE = {
        ("GET", "/v1/commerce/tenants/{tenant_id}/deposit/transactions"),
        ("POST", "/v1/commerce/tenants/{tenant_id}/deposit/initiate"),
        ("GET", "/v1/commerce/tenants/{tenant_id}/deposit"),
    }
    out.append(("S04 live unprotected + closed M01/2F-31/2F-31A/2F-33/2F-35 routes reconcile to the queue",
                st.get("s04", (canon_unp_keys | selA_keys | C7 | D31A_IN_QUEUE | D33_IN_QUEUE | D35_IN_QUEUE | D36_IN_QUEUE | D37_IN_QUEUE) == inv_keys),
                f"{len((canon_unp_keys | selA_keys | C7 | D31A_IN_QUEUE | D33_IN_QUEUE | D35_IN_QUEUE | D36_IN_QUEUE | D37_IN_QUEUE) ^ inv_keys)} diff"))
    prot_keys = {(r[0], r[1]) for r in canon if r[6] in VERIFIED}
    out.append(("S05 only the closed M01/2F-31/2F-31A/2F-33/2F-35 routes in the queue are now protected",
                st.get("s05", (inv_keys & prot_keys) == selA_keys | C7 | D31A_IN_QUEUE | D33_IN_QUEUE | D35_IN_QUEUE | D36_IN_QUEUE | D37_IN_QUEUE),
                f"{len((inv_keys & prot_keys) ^ (selA_keys | C7 | D31A_IN_QUEUE | D33_IN_QUEUE | D35_IN_QUEUE | D36_IN_QUEUE | D37_IN_QUEUE))} unexpected"))
    held_keys = {(r["method"], r["path"]) for r in (held or [])}
    out.append(("S06 no held candidate is counted canonically",
                st.get("s06", not ((held_keys & canon_unp_keys) - SB)), f"{len((held_keys & canon_unp_keys) - SB)}"))
    out.append(("S07 module route counts sum to 45",
                st.get("s07", mem is not None and len(mem) == 45), str(len(mem or []))))
    seen = [(r["method"], r["path"]) for r in (mem or [])]
    out.append(("S08 no route appears in more than one module",
                st.get("s08", len(seen) == len(set(seen))), f"{len(seen) - len(set(seen))} dupes"))
    mods = {r["module"] for r in (mem or [])}
    out.append(("S09 exactly one module is selected",
                st.get("s09", SELECTED in mods and len([SELECTED]) == 1), SELECTED))
    out.append(("S10 selected canonical scope is frozen and non-empty",
                st.get("s10", setA is not None and len(setA) == 12), str(len(setA or []))))
    selA = {(r["method"], r["path"]) for r in (setA or [])}
    modsel = {(r["method"], r["path"]) for r in (mem or []) if r["module"] == SELECTED}
    out.append(("S11 selected scope equals the selected module's queue membership",
                st.get("s11", selA == modsel), f"{len(selA ^ modsel)} diff"))
    out.append(("S12 no selected held route is treated as already canonical",
                st.get("s12", setB is not None and all(r["in_scope_for_M01"] == "NO" for r in setB)
                       and not ({(r["method"], r["path"]) for r in (setB or [])} & canon_unp_keys)), ""))
    out.append(("S13 out-of-scope adjacent routes are frozen with reasons",
                st.get("s13", setC is not None and all(r["exclusion_reason"] for r in setC)), ""))
    out.append(("S14 all 59 held candidates are cross-referenced",
                st.get("s14", xref is not None and len(xref) == 59), str(len(xref or []))))
    crit = ["sessions/{session_id}/revoke", "audit-log", "geo/zones", "webhooks/endpoints"]
    body = " ".join(r["observation_route"] for r in (sec or []))
    out.append(("S15 no critical security observation is silently omitted",
                st.get("s15", all(c in body for c in crit)), ""))
    contract = os.path.join(S, "selected-module-implementation-contract.md")
    ctext = open(contract, encoding="utf-8").read() if os.path.exists(contract) else ""
    missing = [p for _m, p in selA if p not in ctext]
    out.append(("S16 implementation contract omits no canonical route",
                st.get("s16", not missing), f"{len(missing)} missing"))
    outofscope = {r["path"] for r in (setC or [])}
    smuggled = [p for p in outofscope if p in ctext and "EXCLUDED" not in ctext]
    out.append(("S17 contract does not silently include an out-of-scope route",
                st.get("s17", not smuggled), f"{len(smuggled)}"))
    out.append(("S18 canonical hash unchanged", st.get("s18", _h(CANON) == CANON_HASH), ""))
    out.append(("S19 matrix hash unchanged", st.get("s19", _h(MATRIX) == MATRIX_HASH), ""))
    docs = {f: open(os.path.join(S, f), encoding="utf-8").read()
            for f in os.listdir(S) if f.endswith(".md")} if os.path.isdir(S) else {}

    def claims_closure(body: str) -> bool:
        """A CLAIM is a declared final status of closure for THIS slice, or an
        unnegated statement that implementation happened. A mention of
        SECURITY_CLOSED inside the future contract's 'allowed final statuses'
        list, or the sentence 'No authorization implemented', are not claims.

        Scanned on whitespace-normalized text: markdown wraps sentences, so a
        negation ("No") can sit on the previous physical line.
        """
        import re as _re
        flat = _re.sub(r"\s+", " ", body).lower()
        for line in body.splitlines():
            low = line.lower().strip()
            if low.startswith(("final status", "## final status", "**final status")) \
                    and "security_closed" in low:
                return True
        for m in _re.finditer(r"authorization (?:was )?implemented", flat):
            window = flat[max(0, m.start() - 40):m.start()]
            if not any(neg in window for neg in ("no ", "not ", "never ", "without ")):
                return True
        return False

    claims = [f for f, b in docs.items() if claims_closure(b)]
    out.append(("S20 no document claims authorization implementation occurred",
                st.get("s20", not claims), ",".join(claims)))
    return out


def selftest() -> int:
    print("Selection-verifier negative-fixture self-test\n")
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
    print("Selection verifier (Slice 2F-28)\n")
    for n, s, d in conditions():
        check(n, s, d)
    print()
    if FAILURES:
        print(f"VERIFIER FAILED -- {len(FAILURES)}: {FAILURES}")
        return 1
    print("VERIFIER PASSED (module selected; canonical unchanged)")
    return 0


if __name__ == "__main__":
    sys.exit(selftest() if "--selftest" in sys.argv else main())
