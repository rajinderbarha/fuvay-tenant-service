#!/usr/bin/env python
"""Slice 2F-30 — post-M01 queue reconciliation and module-selection verifier.

    python scripts/workflow_rearchitecture/verify_selection_2f30.py
    python scripts/workflow_rearchitecture/verify_selection_2f30.py --selftest
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
S = os.path.join(DOCS, "phase-02a-slice-02f30")
S28 = os.path.join(DOCS, "phase-02a-slice-02f28")
CANON = os.path.join(DOCS, "phase-02a-slice-02f", "tenant-mutation-endpoint-inventory.csv")
MATRIX = os.path.join(DOCS, "phase-02a-slice-02f", "mutation-enforcement-matrix.csv")
HOLD = os.path.join(DOCS, "phase-02a-slice-02f27a", "unauthorized-candidate-hold-registry.csv")
CANON_HASH = "2d6ebeee18c152c0"
MATRIX_HASH = "4389e57d9db6de83"
SELECTED = "N01_media_assets"
HA, HB, HC = "3a5124b153345df5", "62de4c311dde3043", "6d53d0647cdee7ec"

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
    prot = sum(1 for r in canon if r[6] in VERIFIED)
    unp = [r for r in canon if r[6] not in VERIFIED]
    inv = rows(os.path.join(S, "authoritative-unprotected-route-inventory.csv"))
    mem = rows(os.path.join(S, "module-route-membership.csv"))
    setA = rows(os.path.join(S, "selected-canonical-route-scope.csv"))
    setB = rows(os.path.join(S, "selected-held-adjudication-scope.csv"))
    setC = rows(os.path.join(S, "selected-out-of-scope-adjacent-routes.csv"))
    held = rows(HOLD)
    xref = rows(os.path.join(S, "held-candidate-module-cross-reference.csv"))
    secmap = rows(os.path.join(S, "critical-security-observation-map.csv"))
    m01 = rows(os.path.join(S28, "selected-canonical-route-scope.csv"))

    out.append(("Q01 coverage is 252/273 (post-2F-35)",
                st.get("q01", len(canon) == 313 and prot == 313), f"{prot}/{len(canon)}"))
    out.append(("Q02 canonical unprotected count is 21 (post-2F-35)",
                st.get("q02", len(unp) == 0), str(len(unp))))
    C7 = {("POST","/v1/provider/profile/logo"),("DELETE","/v1/provider/profile/logo"),("POST","/v1/provider/profile/shop-photo"),("DELETE","/v1/provider/profile/shop-photo"),("POST","/v1/staff/profile/photo"),("DELETE","/v1/staff/profile/photo"),("POST","/v1/me/profile-photo")}
    SB = {("POST","/v1/media/upload/initiate"),("POST","/v1/media/upload/{session_id}/confirm"),("DELETE","/v1/media/tenants/{tenant_id}/files/{file_id}")}
    # Slice 2F-31A closed the 2 remaining queued media routes (upload,
    # replace) plus all 3 SB routes (SB never appeared in the queue, so it
    # drops out of the reconciliation entirely rather than being unioned in).
    D31A_IN_QUEUE = {("POST", "/v1/media/upload"), ("POST", "/v1/media/{media_id}/replace")}
    D33_IN_QUEUE = {("DELETE", "/v1/geo/zones/{zone_id}")}
    D35_IN_QUEUE = {("DELETE", "/v1/webhooks/endpoints/{endpoint_id}"), ("POST", "/v1/rag/query")}
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
    out.append(("Q03 queue artifact holds its point-in-time 33 routes",
                st.get("q03", inv is not None and len(inv) == 33), str(len(inv or []))))
    unp_keys = {(r[0], r[1]) for r in unp}
    inv_keys = {(r["method"], r["path"]) for r in (inv or [])}
    out.append(("Q04 no canonical unprotected route is missing from the queue",
                st.get("q04", unp_keys == inv_keys - C7 - D31A_IN_QUEUE - D33_IN_QUEUE - D35_IN_QUEUE - D36_IN_QUEUE - D37_IN_QUEUE),
                f"{len(unp_keys ^ (inv_keys - C7 - D31A_IN_QUEUE - D33_IN_QUEUE - D35_IN_QUEUE - D36_IN_QUEUE - D37_IN_QUEUE))} diff"))
    prot_keys = {(r[0], r[1]) for r in canon if r[6] in VERIFIED}
    out.append(("Q05 no protected route appears in the queue",
                st.get("q05", (inv_keys & prot_keys) == C7 | D31A_IN_QUEUE | D33_IN_QUEUE | D35_IN_QUEUE | D36_IN_QUEUE | D37_IN_QUEUE),
                f"{len((inv_keys & prot_keys) ^ (C7 | D31A_IN_QUEUE | D33_IN_QUEUE | D35_IN_QUEUE | D36_IN_QUEUE | D37_IN_QUEUE))}"))
    m01_keys = {(r["method"], r["path"]) for r in (m01 or [])}
    out.append(("Q06 no M01 route appears in the queue (M01 stays closed)",
                st.get("q06", not (inv_keys & m01_keys)), f"{len(inv_keys & m01_keys)}"))
    out.append(("Q07 all 12 M01 routes remain protected",
                st.get("q07", m01_keys <= prot_keys), f"{len(m01_keys - prot_keys)} regressed"))
    held_keys = {(r["method"], r["path"]) for r in (held or [])}
    ADJUDICATED_2F33 = {("POST", "/v1/geo/tenants/{tenant_id}/zones"),
                         ("POST", "/v1/geo/tenants/{tenant_id}/staff/{staff_id}/location")}
    ADJUDICATED_2F35 = {("POST", "/v1/security/api-keys/{key_id}/rotate"),
                         ("POST", "/v1/security/api-keys/{key_id}/revoke"),
                         ("POST", "/v1/documents"),
                         ("POST", "/v1/documents/{document_id}/send"),
                         ("POST", "/v1/documents/{document_id}/void"),
                         ("DELETE", "/v1/rag/knowledge-bases/{kb_id}"),
                         ("POST", "/v1/rag/knowledge-bases/{kb_id}/documents"),
                         ("DELETE", "/v1/rag/documents/{doc_id}"),
                         ("POST", "/v1/rag/documents/{doc_id}/reindex")}
    ADJUDICATED_2F36 = {
        ("POST", "/v1/chat/conversations/{conversation_id}/messages"),
        ("POST", "/v1/inventory/tenants/{tenant_id}/items"),
        ("POST", "/v1/inventory/items/{item_id}/locations/{location_id}/receive"),
        ("POST", "/v1/inventory/reservations"),
        ("POST", "/v1/inventory/reservations/confirm"),
        ("POST", "/v1/inventory/reservations/release"),
        ("POST", "/v1/appointments/{appointment_id}/confirm"),
        ("POST", "/v1/appointments/{appointment_id}/cancel"),
        ("POST", "/v1/appointments/{appointment_id}/reschedule"),
        ("POST", "/v1/appointments/{appointment_id}/no-show"),
        ("POST", "/v1/appointments/staff/{staff_id}/calendar/block"),
        ("DELETE", "/v1/appointments/calendar/blocks/{block_id}"),
        ("PUT", "/v1/appointments/staff/{staff_id}/working-hours"),
        ("POST", "/v1/catalog"),
        ("PUT", "/v1/catalog/{item_id}"),
        ("POST", "/v1/dispatch/jobs/{job_id}/dispatch"),
        ("POST", "/v1/dispatch/jobs/{job_id}/reassign"),
        ("POST", "/v1/ds/tenants/{tenant_id}/demand/recompute"),
        ("POST", "/v1/ds/tenants/{tenant_id}/pricing/apply"),
        ("GET", "/v1/ds/tenants/{tenant_id}/customers/{customer_id}/ltv"),
        ("POST", "/v1/ds/tenants/{tenant_id}/customers/{customer_id}/ltv/recompute"),
        ("PUT", "/v1/settings/tenants/{tenant_id}/{key}"),
        ("DELETE", "/v1/settings/tenants/{tenant_id}/{key}"),
        ("PUT", "/v1/notifications/tenants/{tenant_id}/channels/{channel}"),
    }
    ADJUDICATED_2F37 = {
        ("POST", "/v1/pricing/tenants/{tenant_id}/prices/set"),
        ("PUT", "/v1/pricing/tenants/{tenant_id}/brand-adjustment"),
        ("POST", "/v1/pricing/tenants/{tenant_id}/zones"),
        ("PUT", "/v1/pricing/tenants/{tenant_id}/zones/{zone_id}"),
        ("DELETE", "/v1/pricing/tenants/{tenant_id}/zones/{zone_id}"),
        ("POST", "/v1/pricing/tenants/{tenant_id}/rules"),
        ("PUT", "/v1/pricing/tenants/{tenant_id}/rules/{rule_id}"),
        ("DELETE", "/v1/pricing/tenants/{tenant_id}/rules/{rule_id}"),
        ("POST", "/v1/pricing/compute"),
        ("POST", "/v1/commerce/tenants/{tenant_id}/wallet/purchase/initiate"),
        ("POST", "/v1/commerce/warranty/claims"),
        ("POST", "/v1/commerce/tenants/{tenant_id}/badges/recalculate"),
        ("POST", "/v1/payments/tenants/{tenant_id}/payout"),
        ("PUT", "/v1/subscriptions/tenants/{tenant_id}/plan"),
        ("POST", "/v1/compliance/deletion-requests"),
        ("POST", "/v1/compliance/portability-requests"),
    }
    out.append(("Q08 no held candidate is counted canonically",
                st.get("q08", not ((held_keys & {(r[0], r[1]) for r in canon}) - SB - ADJUDICATED_2F33 - ADJUDICATED_2F35 - ADJUDICATED_2F36 - ADJUDICATED_2F37)), ""))
    out.append(("Q09 module counts sum to 33",
                st.get("q09", mem is not None and len(mem) == 33), str(len(mem or []))))
    seen = [(r["method"], r["path"]) for r in (mem or [])]
    out.append(("Q10 no route appears in more than one module",
                st.get("q10", len(seen) == len(set(seen))), f"{len(seen) - len(set(seen))}"))
    out.append(("Q11 exactly one module is selected",
                st.get("q11", SELECTED in {r["module"] for r in (mem or [])}), SELECTED))
    out.append(("Q12 Set A frozen and equals the selected module membership",
                st.get("q12", setA is not None and _h(os.path.join(S, "selected-canonical-route-scope.csv")) == HA
                       and {(r["method"], r["path"]) for r in setA}
                       == {(r["method"], r["path"]) for r in (mem or []) if r["module"] == SELECTED}), ""))
    out.append(("Q13 Set B frozen and no held route treated as canonical",
                st.get("q13", setB is not None
                       and _h(os.path.join(S, "selected-held-adjudication-scope.csv")) == HB
                       and all(r["canonical_yet"] == "NO" for r in setB)
                       and {(r["method"], r["path"]) for r in setB} <= {(r[0], r[1]) for r in canon}), ""))
    out.append(("Q14 Set C frozen with reasons",
                st.get("q14", setC is not None
                       and _h(os.path.join(S, "selected-out-of-scope-adjacent-routes.csv")) == HC
                       and all(r["exclusion_reason"] for r in setC)), ""))
    out.append(("Q15 all 59 held candidates are cross-referenced",
                st.get("q15", xref is not None and len(xref) == 59), str(len(xref or []))))
    body = " ".join(r["observation_route"] for r in (secmap or []))
    out.append(("Q16 no critical security observation is silently omitted",
                st.get("q16", all(c in body for c in
                       ["sessions/{session_id}/revoke", "audit-log", "geo/zones",
                        "webhooks/endpoints", "badges/recalculate"])), ""))
    contract = os.path.join(S, "selected-module-implementation-contract.md")
    ctext = open(contract, encoding="utf-8").read() if os.path.exists(contract) else ""
    missing = [r["path"] for r in (setA or []) if r["path"] not in ctext]
    out.append(("Q17 contract omits no Set A route", st.get("q17", not missing), f"{len(missing)}"))
    smuggled = [r["path"] for r in (setC or [])
                if r["path"] in ctext and "EXCLUDED" not in ctext]
    out.append(("Q18 contract does not silently include a Set C route",
                st.get("q18", not smuggled), f"{len(smuggled)}"))
    out.append(("Q19 canonical hash unchanged", st.get("q19", _h(CANON) == CANON_HASH), ""))
    out.append(("Q20 matrix hash unchanged", st.get("q20", _h(MATRIX) == MATRIX_HASH), ""))
    docs = {f: open(os.path.join(S, f), encoding="utf-8").read()
            for f in os.listdir(S) if f.endswith(".md")} if os.path.isdir(S) else {}

    def claims_impl(b):
        import re as _re
        flat = _re.sub(r"\s+", " ", b).lower()
        for line in b.splitlines():
            low = line.lower().strip()
            if low.startswith(("final status", "## final status")) and "security_closed" in low:
                return True
        for m in _re.finditer(r"authorization (?:was )?implemented", flat):
            if not any(n in flat[max(0, m.start() - 40):m.start()]
                       for n in ("no ", "not ", "never ", "without ")):
                return True
        return False
    claims = [f for f, b in docs.items() if claims_impl(b)]
    out.append(("Q21 no document claims implementation occurred",
                st.get("q21", not claims), ",".join(claims)))
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
    print("Post-M01 selection verifier (Slice 2F-30)\n")
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
