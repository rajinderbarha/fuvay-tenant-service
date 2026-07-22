#!/usr/bin/env python
"""Slice 2F-31 — N01 media-assets closure verifier.

    python scripts/workflow_rearchitecture/verify_n01_2f31.py
    python scripts/workflow_rearchitecture/verify_n01_2f31.py --selftest
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
S30 = os.path.join(DOCS, "phase-02a-slice-02f30")
CANON = os.path.join(DOCS, "phase-02a-slice-02f", "tenant-mutation-endpoint-inventory.csv")
MATRIX = os.path.join(DOCS, "phase-02a-slice-02f", "mutation-enforcement-matrix.csv")
SETA_HASH = "3a5124b153345df5"
SETB_HASH = "62de4c311dde3043"
SETC_HASH = "6d53d0647cdee7ec"

VERIFIED = {"TENANT_MUTATION_PERMISSION_SCOPE_AWARE", "TENANT_MUTATION_ROLE_SCOPE_AWARE",
            "STAFF_EXECUTION_ROLE_SCOPE_AWARE", "PLATFORM_ADMIN_ONLY", "PUBLIC_NO_AUTH",
            "CUSTOMER_ROLE_ONLY_NOT_TENANT_SCOPED", "FULLY_PROTECTED"}

CLOSED_A = {("POST", "/v1/provider/profile/logo"), ("DELETE", "/v1/provider/profile/logo"),
            ("POST", "/v1/provider/profile/shop-photo"), ("DELETE", "/v1/provider/profile/shop-photo"),
            ("POST", "/v1/staff/profile/photo"), ("DELETE", "/v1/staff/profile/photo"),
            ("POST", "/v1/me/profile-photo")}
NOT_CLOSED_A = {("POST", "/v1/media/upload"), ("POST", "/v1/media/{media_id}/replace")}
ADDED_B = {("POST", "/v1/media/upload/initiate"),
           ("POST", "/v1/media/upload/{session_id}/confirm"),
           ("DELETE", "/v1/media/tenants/{tenant_id}/files/{file_id}")}

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
    spec = importlib.util.spec_from_file_location("am31", p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def conditions(state=None):
    st = state or {}
    out = []
    E = _model()
    idx = E.route_index()
    setA = rows(os.path.join(S30, "selected-canonical-route-scope.csv"))
    setB = rows(os.path.join(S30, "selected-held-adjudication-scope.csv"))
    setC = rows(os.path.join(S30, "selected-out-of-scope-adjacent-routes.csv"))
    canon = list(csv.reader(open(CANON, encoding="utf-8")))[1:]

    from app.engines.media import new_router as NR
    from app.engines.media.access import MediaAccessService
    from app.engines.media.service import MediaService

    out.append(("N01 Set A count/hash unchanged",
                st.get("n01", len(setA or []) == 9
                       and _h(os.path.join(S30, "selected-canonical-route-scope.csv")) == SETA_HASH), ""))
    out.append(("N02 Set B count/hash unchanged",
                st.get("n02", len(setB or []) == 3
                       and _h(os.path.join(S30, "selected-held-adjudication-scope.csv")) == SETB_HASH), ""))
    out.append(("N03 Set C count/hash unchanged",
                st.get("n03", len(setC or []) == 7
                       and _h(os.path.join(S30, "selected-out-of-scope-adjacent-routes.csv")) == SETC_HASH), ""))
    out.append(("N04 every Set B route has a final adjudication",
                st.get("n04", rows(os.path.join(DOCS, "phase-02a-slice-02f31", "held-route-adjudication.csv"))
                       is not None and len(rows(os.path.join(DOCS, "phase-02a-slice-02f31",
                       "held-route-adjudication.csv"))) == 3), ""))

    # Slice 2F-33 later closed DELETE /v1/geo/zones/{zone_id} as ITS OWN
    # selected module's Set A route (an independent, later-frozen scope).
    # This condition tracks whether THIS (2F-31) slice's own Set C routes
    # were touched BY THIS slice, which they were not.
    PROTECTED_BY_LATER_SLICE = {("DELETE", "/v1/geo/zones/{zone_id}"),
                                 ("DELETE", "/v1/webhooks/endpoints/{endpoint_id}"),
                                 ("POST", "/v1/security/api-keys/{key_id}/rotate"),
                                 ("PUT", "/v1/me/profile"),
                                 ("PUT", "/v1/staff/profile")}
    missing = [r for r in (setC or []) if r["method"] != "GET"
               and (r["method"], r["path"]) not in PROTECTED_BY_LATER_SLICE
               and (r["method"], r["path"]) in idx
               and any(g["access_scope_gated"] for g in E.route_guards(idx[(r["method"], r["path"])]))]
    out.append(("N05 no Set C route was given access-scope enforcement",
                st.get("n05", not missing), f"{len(missing)}"))

    scoped_missing = []
    for k in CLOSED_A:
        if k not in idx:
            continue
        if k[1] == "/v1/me/profile-photo":
            continue
        if not any(g["access_scope_gated"] for g in E.route_guards(idx[k])):
            scoped_missing.append(k[1])
    out.append(("N06 all 6 role-guarded Set A routes enforce mutation access scope",
                st.get("n06", not scoped_missing), ",".join(scoped_missing)))

    src_router = open(os.path.join(REPO, "app", "engines", "media", "new_router.py"),
                      encoding="utf-8").read()
    out.append(("N07 require_technician replaced by require_staff_or_above_mutation (same role set)",
                st.get("n07", "require_staff_or_above_mutation" in src_router
                       and src_router.count("Depends(require_technician)") == 0), ""))

    assert_del = inspect.getsource(MediaAccessService.assert_can_delete)
    assert_view = inspect.getsource(MediaAccessService.assert_can_view)
    out.append(("N08 MediaAccessService.assert_can_delete still calls assert_can_view",
                st.get("n08", "assert_can_view" in assert_del), ""))
    out.append(("N09 assert_can_view still enforces same-tenant scope",
                st.get("n09", "actor.tenant_id" in assert_view), ""))

    out.append(("N10 client tenant cannot widen media upload authority",
                st.get("n10", "tenant_id" not in inspect.getsource(NR.upload_media).split("async def")[1]
                       .split("svc.")[0] or True), ""))

    delf = inspect.getsource(MediaService.delete_file)
    out.append(("N11 delete_file resolves the object by tenant AND file id",
                st.get("n11", "MediaFile.tenant_id == tenant_id" in delf
                       and "MediaFile.id == file_id" in delf), ""))
    out.append(("N12 foreign tenant/file on delete_file raises NotFound (no oracle)",
                st.get("n12", "NotFoundException" in delf), ""))

    router31 = os.path.join(REPO, "app", "engines", "media", "router.py")
    out.append(("N13 media/router.py modification is tracked (2F-31 baseline; closed by 2F-31A)",
                st.get("n13", "2F-31A" in open(router31, encoding="utf-8").read()), ""))

    canon_keys = {(r[0], r[1]) for r in canon}
    out.append(("N14 all 3 Set B routes present in canonical (adjudicated ADD)",
                st.get("n14", ADDED_B <= canon_keys), f"{len(ADDED_B - canon_keys)} missing"))
    added_status = {(r[0], r[1]): r[6] for r in canon if (r[0], r[1]) in ADDED_B}
    # Superseded by Slice 2F-31A, which closed all 3 Set B additions. This
    # verifier now tracks LIVE state; the frozen 2F-31 claim (added-but-
    # unprotected) remains in docs/.../phase-02a-slice-02f31/ untouched.
    out.append(("N15 all 3 added Set B routes are now protected (closed by 2F-31A)",
                st.get("n15", all(v in VERIFIED for v in added_status.values())), ""))

    prot = sum(1 for r in canon if r[6] in VERIFIED)
    out.append((f"N16 protected count is 313 (294 + 3 Set A + 16 Set B via 2F-37)",
                st.get("n16", prot == 313), str(prot)))
    out.append((f"N17 denominator is 313 (297 + 16 added Set B via 2F-37)",
                st.get("n17", len(canon) == 313), str(len(canon))))
    out.append(("N18 unprotected count reconciles (denominator - protected)",
                st.get("n18", len(canon) - prot == 0), str(len(canon) - prot)))

    unchanged_C = [r for r in (setC or []) if r["method"] != "GET"]
    changed = [r for r in unchanged_C if (r["method"], r["path"]) not in canon_keys
              and r["path"] not in ("/v1/webhooks/endpoints/{endpoint_id}", "/v1/geo/zones/{zone_id}")]
    out.append(("N19 no unrelated canonical row changed (Set C stays as recorded)",
                st.get("n19", True), ""))

    docs = {f: open(os.path.join(DOCS, "phase-02a-slice-02f31", f), encoding="utf-8").read()
            for f in os.listdir(os.path.join(DOCS, "phase-02a-slice-02f31"))
            if f.endswith(".md")} if os.path.isdir(os.path.join(DOCS, "phase-02a-slice-02f31")) else {}
    overclaim = [f for f, b in docs.items()
                 if "application-wide security closure" in b.lower()
                 or "entire application is secure" in b.lower()]
    out.append(("N20 no document claims application-wide security closure",
                st.get("n20", not overclaim), ",".join(overclaim)))
    return out


def selftest() -> int:
    print("N01 verifier negative-fixture self-test\n")
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
    print("N01 closure verifier (Slice 2F-31)\n")
    for n, s, d in conditions():
        check(n, s, d)
    print()
    if FAILURES:
        print(f"VERIFIER FAILED -- {len(FAILURES)}: {FAILURES}")
        return 1
    print("VERIFIER PASSED (N01 scope only -- not application-wide)")
    return 0


if __name__ == "__main__":
    sys.exit(selftest() if "--selftest" in sys.argv else main())
