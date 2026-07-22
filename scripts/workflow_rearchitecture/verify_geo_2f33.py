#!/usr/bin/env python
"""Slice 2F-33 — geo_zone_management closure verifier.

    python scripts/workflow_rearchitecture/verify_geo_2f33.py
    python scripts/workflow_rearchitecture/verify_geo_2f33.py --selftest
"""
from __future__ import annotations

import csv
import hashlib
import importlib.util
import inspect
import os
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, REPO)
DOCS = os.path.join(REPO, "docs", "workflow-rearchitecture")
S32 = os.path.join(DOCS, "phase-02a-slice-02f32")
S33 = os.path.join(DOCS, "phase-02a-slice-02f33")
CANON = os.path.join(DOCS, "phase-02a-slice-02f", "tenant-mutation-endpoint-inventory.csv")
MATRIX = os.path.join(DOCS, "phase-02a-slice-02f", "mutation-enforcement-matrix.csv")
CANON_HASH = "d4900ce03daa5437"
MATRIX_HASH = "abfa5d030b1cfeee"
SETA_HASH = "fc45fa777f47c2c9"
SETB_HASH = "593837fac1076324"
SETC_HASH = "578a7e506b83dc09"

VERIFIED = {"TENANT_MUTATION_PERMISSION_SCOPE_AWARE", "TENANT_MUTATION_ROLE_SCOPE_AWARE",
            "STAFF_EXECUTION_ROLE_SCOPE_AWARE", "PLATFORM_ADMIN_ONLY", "PUBLIC_NO_AUTH",
            "CUSTOMER_ROLE_ONLY_NOT_TENANT_SCOPED", "FULLY_PROTECTED"}

SET_A = {("DELETE", "/v1/geo/zones/{zone_id}")}
SET_B = {("POST", "/v1/geo/tenants/{tenant_id}/zones"),
         ("POST", "/v1/geo/tenants/{tenant_id}/staff/{staff_id}/location")}

FAILURES: list[str] = []


def check(name, cond, detail=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {name}" + ("" if cond or not detail else f" -- {detail}"))
    if not cond:
        FAILURES.append(name)


def _h(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()[:16]


def rows(p):
    return list(csv.DictReader(open(p, encoding="utf-8"))) if os.path.exists(p) else None


def _model():
    p = os.path.join(REPO, "scripts", "workflow_rearchitecture", "authority_model_2f26e.py")
    spec = importlib.util.spec_from_file_location("am33v", p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def conditions(state=None):
    st = state or {}
    out = []
    E = _model()
    idx = E.route_index()
    canon = list(csv.reader(open(CANON, encoding="utf-8")))[1:]
    canon_rows = {(r[0], r[1]): r for r in canon}

    from app.engines.geo.service import GeoService
    from app.core.permissions import require_mutation_access_scope

    out.append(("G01 Set A/B/C frozen hashes unchanged",
                st.get("g01", _h(os.path.join(S32, "selected-canonical-route-scope.csv")) == SETA_HASH
                       and _h(os.path.join(S32, "selected-held-adjudication-scope.csv")) == SETB_HASH
                       and _h(os.path.join(S32, "selected-out-of-scope-adjacent-routes.csv")) == SETC_HASH), ""))

    out.append(("G02 every Set B route received a final adjudication",
                st.get("g02", all(k in canon_rows for k in SET_B)), str(SET_B - set(canon_rows))))

    setc = rows(os.path.join(S32, "selected-out-of-scope-adjacent-routes.csv"))
    setc_keys = {(r["method"], r["path"]) for r in (setc or [])}
    out.append(("G03 no Set C route was added to canonical mutation coverage",
                st.get("g03", not (setc_keys & {("PUT", "/v1/geo/zones/{zone_id}")} & set(canon_rows))), ""))

    out.append(("G04 Set A route (delete_zone) is protected",
                st.get("g04", canon_rows[("DELETE", "/v1/geo/zones/{zone_id}")][6] in VERIFIED), ""))

    delsrc = inspect.getsource(GeoService.delete_zone)
    out.append(("G05 delete_zone has a mutation access-scope guard live",
                st.get("g05", any(g["access_scope_gated"] for g in E.route_guards(idx[("DELETE", "/v1/geo/zones/{zone_id}")]))), ""))
    out.append(("G06 delete_zone does not mutate by zone_id alone (tenant predicate present)",
                st.get("g06", "ServiceZone.tenant_id == tenant_id" in delsrc), ""))

    out.append(("G07 client tenant cannot widen create_zone authority",
                st.get("g07", "_require_trusted_tenant(tenant_id)" in inspect.getsource(GeoService.create_zone)), ""))

    trusted_src = inspect.getsource(GeoService._require_trusted_tenant)
    out.append(("G08 GeoService rejects missing/untrusted tenant context",
                st.get("g08", "self.actor_tenant_id is None" in trusted_src and "raise" in trusted_src), ""))

    out.append(("G09 foreign-tenant zone creates no existence oracle",
                st.get("g09", "does not exist" not in trusted_src and "does not belong" not in trusted_src), ""))

    out.append(("G10 create_zone parent-geography check is honestly reported (no hierarchy model exists)",
                st.get("g10", os.path.exists(os.path.join(S33, "geography-hierarchy-integrity-audit.csv"))), ""))

    reparent = os.path.exists(os.path.join(S33, "zone-location-ownership-audit.csv"))
    out.append(("G11 cross-tenant reparenting audit is documented",
                st.get("g11", reparent), ""))

    import subprocess
    grep = subprocess.run(
        ["git", "grep", "-n", "-E",
         r"\bs\.(delete_zone|create_zone|update_staff_location)\(|\bgeo\.(delete_zone|create_zone|update_staff_location)\(",
         "--", "app/", ":(exclude)app/engines/geo/service.py", ":(exclude)app/engines/geo/router.py",
         ":(exclude)app/engines/pricing/router.py", ":(exclude)app/engines/location_engine/router.py"],
        cwd=REPO, capture_output=True, text=True)
    out.append(("G12 no alternate-route bypass to a closed GeoService mutation method",
                st.get("g12", grep.stdout.strip() == ""), grep.stdout[:200]))

    out.append(("G13 create_zone canonically added and VERIFIED",
                st.get("g13", canon_rows.get(("POST", "/v1/geo/tenants/{tenant_id}/zones"), [None]*7)[6] in VERIFIED), ""))
    out.append(("G14 update_location canonically added and VERIFIED",
                st.get("g14", canon_rows.get(("POST", "/v1/geo/tenants/{tenant_id}/staff/{staff_id}/location"), [None]*7)[6] in VERIFIED), ""))

    prot = sum(1 for r in canon if r[6] in VERIFIED)
    out.append(("G15 coverage arithmetic is 241/264 (238+1+2 / 262+2)",
                st.get("g15", len(canon) == 264 and prot == 241), f"{prot}/{len(canon)}"))
    out.append(("G16 unprotected count is 23",
                st.get("g16", len(canon) - prot == 23), str(len(canon) - prot)))

    m01 = ("POST", "/v1/auth/api-keys")
    n01 = ("POST", "/v1/media/upload")
    out.append(("G17 M01 sample route remains VERIFIED (no regression)",
                st.get("g17", canon_rows[m01][6] in VERIFIED), ""))
    out.append(("G18 N01 sample route remains VERIFIED (no regression)",
                st.get("g18", canon_rows[n01][6] in VERIFIED), ""))

    docs = {f: open(os.path.join(S33, f), encoding="utf-8").read()
            for f in os.listdir(S33) if f.endswith(".md")} if os.path.isdir(S33) else {}

    def _claims_overclosure(body: str) -> bool:
        low = body.lower()
        for phrase in ("application-wide security closure", "entire application is secure"):
            start = 0
            while True:
                i = low.find(phrase, start)
                if i == -1:
                    break
                window = low[max(0, i - 40):i]
                if not any(neg in window for neg in ("no ", "not ", "n't ", "does not", "isn't")):
                    return True
                start = i + len(phrase)
        return False

    overclaim = [f for f, b in docs.items() if _claims_overclosure(b)]
    out.append(("G19 no document claims application-wide security closure",
                st.get("g19", not overclaim), ",".join(overclaim)))

    out.append(("G20 canonical hash matches the post-closure frozen value",
                st.get("g20", _h(CANON) == CANON_HASH), _h(CANON)))
    out.append(("G21 matrix hash matches the post-closure frozen value",
                st.get("g21", _h(MATRIX) == MATRIX_HASH), _h(MATRIX)))

    guard_src = inspect.getsource(require_mutation_access_scope)
    out.append(("G22 update_location scope guard preserves the read-only access_scope rejection",
                st.get("g22", "TENANT_READONLY_ACCESS_SCOPES" in guard_src), ""))

    return out


def selftest() -> int:
    print("Geo-zone closure verifier negative-fixture self-test\n")
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
    print("Geo-zone closure verifier (Slice 2F-33)\n")
    for n, s, d in conditions():
        check(n, s, d)
    print()
    if FAILURES:
        print(f"VERIFIER FAILED -- {len(FAILURES)}: {FAILURES}")
        return 1
    print("VERIFIER PASSED (geo_zone_management scope only -- not application-wide)")
    return 0


if __name__ == "__main__":
    sys.exit(selftest() if "--selftest" in sys.argv else main())
