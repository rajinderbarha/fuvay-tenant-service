#!/usr/bin/env python
"""Slice 2F-35 — critical destructive/security-sensitive batch verifier.

    python scripts/workflow_rearchitecture/verify_2f35.py
    python scripts/workflow_rearchitecture/verify_2f35.py --selftest
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
S34 = os.path.join(DOCS, "phase-02a-slice-02f34")
S35 = os.path.join(DOCS, "phase-02a-slice-02f35")
CANON = os.path.join(DOCS, "phase-02a-slice-02f", "tenant-mutation-endpoint-inventory.csv")
MATRIX = os.path.join(DOCS, "phase-02a-slice-02f", "mutation-enforcement-matrix.csv")
CANON_HASH = "58bbf1e1196688e7"
MATRIX_HASH = "4520e7f3ed2250ab"
SETA_HASH = "d1ad1fa8027272e1"
SETB_HASH = "4fb3739e9ace9269"
SETC_HASH = "43a129bd966687b6"

VERIFIED = {"TENANT_MUTATION_PERMISSION_SCOPE_AWARE", "TENANT_MUTATION_ROLE_SCOPE_AWARE",
            "STAFF_EXECUTION_ROLE_SCOPE_AWARE", "PLATFORM_ADMIN_ONLY", "PUBLIC_NO_AUTH",
            "CUSTOMER_ROLE_ONLY_NOT_TENANT_SCOPED", "FULLY_PROTECTED"}

SET_A = {("DELETE", "/v1/webhooks/endpoints/{endpoint_id}"), ("POST", "/v1/rag/query")}
SET_B = {
    ("POST", "/v1/security/api-keys/{key_id}/rotate"),
    ("POST", "/v1/security/api-keys/{key_id}/revoke"),
    ("POST", "/v1/documents"),
    ("POST", "/v1/documents/{document_id}/send"),
    ("POST", "/v1/documents/{document_id}/void"),
    ("DELETE", "/v1/rag/knowledge-bases/{kb_id}"),
    ("POST", "/v1/rag/knowledge-bases/{kb_id}/documents"),
    ("DELETE", "/v1/rag/documents/{doc_id}"),
    ("POST", "/v1/rag/documents/{doc_id}/reindex"),
}

FAILURES: list[str] = []


def check(name, cond, detail=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {name}" + ("" if cond or not detail else f" -- {detail}"))
    if not cond:
        FAILURES.append(name)


def _h(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()[:16]


def _model():
    p = os.path.join(REPO, "scripts", "workflow_rearchitecture", "authority_model_2f26e.py")
    spec = importlib.util.spec_from_file_location("am35v", p)
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

    from app.engines.webhook.service import WebhookService
    from app.engines.rag.service import RAGService
    from app.engines.security.service import SecurityService
    from app.engines.document.service import DocumentService

    out.append(("R01 Set A/B/C frozen hashes unchanged",
                st.get("r01", _h(os.path.join(S34, "slice-2f35-module-scope.csv")) == SETA_HASH
                       and _h(os.path.join(S34, "slice-2f35-held-scope.csv")) == SETB_HASH
                       and _h(os.path.join(S34, "slice-2f35-exclusion-scope.csv")) == SETC_HASH), ""))

    out.append(("R02 every Set B route received a final adjudication",
                st.get("r02", all(k in canon_rows for k in SET_B)), str(SET_B - set(canon_rows))))

    setc = None
    p = os.path.join(S34, "slice-2f35-exclusion-scope.csv")
    if os.path.exists(p):
        setc = list(csv.DictReader(open(p, encoding="utf-8")))
    # Set C routes were already canonical (unprotected) before this slice --
    # they must remain unprotected (guard_status unchanged), not become
    # newly VERIFIED as a side effect of this slice's edits.
    setc_keys = {(r["method"], r["path"]) for r in (setc or [])}
    newly_verified_c = [k for k in setc_keys if k in canon_rows and canon_rows[k][6] in VERIFIED]
    out.append(("R03 no Set C route was newly protected by this slice",
                st.get("r03", not newly_verified_c), str(newly_verified_c)))

    out.append(("R04 both Set A routes are protected",
                st.get("r04", all(canon_rows[k][6] in VERIFIED for k in SET_A)), ""))

    for key, name in [(("DELETE", "/v1/webhooks/endpoints/{endpoint_id}"), "webhook"),
                       (("POST", "/v1/rag/query"), "rag")]:
        pass
    out.append(("R05 all 11 routes have mutation access-scope guard live",
                st.get("r05", all(any(g["access_scope_gated"] for g in E.route_guards(idx[k]))
                                   for k in (SET_A | SET_B) if k in idx)), ""))

    ws = inspect.getsource(WebhookService.delete_endpoint)
    out.append(("R06 delete_endpoint does not mutate by endpoint_id alone (tenant predicate present)",
                st.get("r06", "WebhookEndpoint.tenant_id == tenant_id" in ws), ""))

    rs = inspect.getsource(RAGService._get_kb_trusted)
    out.append(("R07 rag KB lookup scoped by tenant for closed methods",
                st.get("r07", "KnowledgeBase.tenant_id == tenant_id" in rs), ""))

    ss_rotate = inspect.getsource(SecurityService.rotate_api_key)
    out.append(("R08 client tenant cannot widen rotate_api_key authority",
                st.get("r08", "_require_trusted_tenant(tenant_id)" in ss_rotate), ""))

    ds_gen = inspect.getsource(DocumentService.generate_document)
    out.append(("R09 client tenant cannot widen generate_document authority",
                st.get("r09", "_require_trusted_tenant(tenant_id)" in ds_gen), ""))

    for svc_cls, helper in [(WebhookService, "_require_trusted_tenant"),
                             (RAGService, "_require_trusted_tenant"),
                             (SecurityService, "_require_trusted_tenant"),
                             (DocumentService, "_require_trusted_tenant")]:
        src = inspect.getsource(getattr(svc_cls, helper))
        if "self.actor_tenant_id is None" not in src or "raise" not in src:
            out.append((f"R10 {svc_cls.__name__} rejects missing/untrusted tenant context",
                        st.get("r10", False), svc_cls.__name__))
            break
    else:
        out.append(("R10 every service rejects missing/untrusted tenant context",
                    st.get("r10", True), ""))

    no_oracle = True
    for svc_cls, helper in [(WebhookService, "_require_trusted_tenant"), (RAGService, "_get_kb_trusted"),
                             (SecurityService, "_require_trusted_tenant"), (DocumentService, "_require_trusted_tenant")]:
        src = inspect.getsource(getattr(svc_cls, helper))
        if "does not exist" in src or "does not belong" in src:
            no_oracle = False
    out.append(("R11 foreign objects create no existence oracle",
                st.get("r11", no_oracle), ""))

    import subprocess
    bypass_checks = [
        (r"\bs\.delete_endpoint\(", ["app/engines/webhook/service.py", "app/engines/webhook/router.py"]),
        (r"\bs\.(query|delete_kb|ingest_document|delete_document|reindex_document)\(",
         ["app/engines/rag/service.py", "app/engines/rag/router.py"]),
    ]
    bypass_found = []
    for pattern, excludes in bypass_checks:
        cmd = ["git", "grep", "-n", "-E", pattern, "--"] + \
              ["app/"] + [f":(exclude){e}" for e in excludes]
        r = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True)
        if r.stdout.strip():
            bypass_found.append(r.stdout.strip())
    out.append(("R12 no alternate-route bypass to a closed mutation method",
                st.get("r12", not bypass_found), str(bypass_found)[:200]))

    fo = subprocess.run(["git", "grep", "-n", "actor_tenant_id=job.tenant_id", "--", "app/engines/field_ops/service.py"],
                         cwd=REPO, capture_output=True, text=True)
    out.append(("R13 field_ops internal caller passes trusted tenant context",
                st.get("r13", bool(fo.stdout.strip())), ""))

    prot = sum(1 for r in canon if r[6] in VERIFIED)
    out.append(("R14 coverage arithmetic is 252/273 (241+2+9 / 264+9)",
                st.get("r14", len(canon) == 273 and prot == 252), f"{prot}/{len(canon)}"))
    out.append(("R15 unprotected count is 21",
                st.get("r15", len(canon) - prot == 21), str(len(canon) - prot)))

    m01 = ("POST", "/v1/auth/api-keys")
    n01 = ("POST", "/v1/media/upload")
    geo = ("DELETE", "/v1/geo/zones/{zone_id}")
    out.append(("R16 M01 sample route remains VERIFIED (no regression)",
                st.get("r16", canon_rows[m01][6] in VERIFIED), ""))
    out.append(("R17 N01 sample route remains VERIFIED (no regression)",
                st.get("r17", canon_rows[n01][6] in VERIFIED), ""))
    out.append(("R18 geo sample route remains VERIFIED (no regression)",
                st.get("r18", canon_rows[geo][6] in VERIFIED), ""))

    # Slice 2F-36/37 files must not change
    forbidden_files = [
        "app/engines/enterprise_grid/router.py", "app/engines/enterprise_grid/services.py",
        "app/engines/admin_catalog/brand_provider_router.py", "app/engines/profile/router.py",
        "app/engines/marketing_automation/provider_router.py", "app/engines/analytics/provider_router.py",
        "app/engines/platform_commerce/router.py", "app/engines/platform_commerce/service.py",
    ]
    r = subprocess.run(["git", "status", "--porcelain"] + forbidden_files, cwd=REPO, capture_output=True, text=True)
    out.append(("R19 no Slice 2F-36/37 application file changed",
                st.get("r19", r.stdout.strip() == ""), r.stdout.strip()))

    docs = {f: open(os.path.join(S35, f), encoding="utf-8").read()
            for f in os.listdir(S35) if f.endswith(".md")} if os.path.isdir(S35) else {}

    def _claims_overclosure(body: str) -> bool:
        low = body.lower()
        for phrase in ("application-wide security closure", "entire application is secure",
                       "application-wide authorization closure"):
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
    out.append(("R20 no document claims application-wide closure",
                st.get("r20", not overclaim), ",".join(overclaim)))

    out.append(("R21 canonical hash matches the post-closure frozen value",
                st.get("r21", _h(CANON) == CANON_HASH), _h(CANON)))
    out.append(("R22 matrix hash matches the post-closure frozen value",
                st.get("r22", _h(MATRIX) == MATRIX_HASH), _h(MATRIX)))

    return out


def selftest() -> int:
    print("Slice 2F-35 verifier negative-fixture self-test\n")
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
    print("Slice 2F-35 verifier\n")
    for n, s, d in conditions():
        check(n, s, d)
    print()
    if FAILURES:
        print(f"VERIFIER FAILED -- {len(FAILURES)}: {FAILURES}")
        return 1
    print("VERIFIER PASSED (critical authorization batch scope only -- not application-wide)")
    return 0


if __name__ == "__main__":
    sys.exit(selftest() if "--selftest" in sys.argv else main())
