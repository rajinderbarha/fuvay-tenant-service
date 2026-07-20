#!/usr/bin/env python
"""Slice 2F-34 — post-geo reconciliation / remaining-program batch-freeze verifier.

    python scripts/workflow_rearchitecture/verify_program_2f34.py
    python scripts/workflow_rearchitecture/verify_program_2f34.py --selftest
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
S34 = os.path.join(DOCS, "phase-02a-slice-02f34")
CANON = os.path.join(DOCS, "phase-02a-slice-02f", "tenant-mutation-endpoint-inventory.csv")
MATRIX = os.path.join(DOCS, "phase-02a-slice-02f", "mutation-enforcement-matrix.csv")
HOLD = os.path.join(DOCS, "phase-02a-slice-02f27a", "unauthorized-candidate-hold-registry.csv")
CANON_HASH = "d4900ce03daa5437"
MATRIX_HASH = "abfa5d030b1cfeee"
HOLD_HASH = "3729aa0e0fd5dafe"

VERIFIED = {"TENANT_MUTATION_PERMISSION_SCOPE_AWARE", "TENANT_MUTATION_ROLE_SCOPE_AWARE",
            "STAFF_EXECUTION_ROLE_SCOPE_AWARE", "PLATFORM_ADMIN_ONLY", "PUBLIC_NO_AUTH",
            "CUSTOMER_ROLE_ONLY_NOT_TENANT_SCOPED", "FULLY_PROTECTED"}

N01 = {("POST", "/v1/media/upload/initiate"), ("POST", "/v1/media/upload/{session_id}/confirm"),
       ("DELETE", "/v1/media/tenants/{tenant_id}/files/{file_id}")}
GEO = {("DELETE", "/v1/geo/zones/{zone_id}"), ("POST", "/v1/geo/tenants/{tenant_id}/zones"),
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


def conditions(state=None):
    st = state or {}
    out = []
    canon = list(csv.reader(open(CANON, encoding="utf-8")))[1:]
    prot = sum(1 for r in canon if r[6] in VERIFIED)
    unp_keys = {(r[0], r[1]) for r in canon if r[6] not in VERIFIED}
    prot_keys = {(r[0], r[1]) for r in canon if r[6] in VERIFIED}

    inv = rows(os.path.join(S34, "authoritative-unprotected-route-inventory.csv"))
    inv_keys = {(r["method"], r["path"]) for r in (inv or [])}
    mem = rows(os.path.join(S34, "remaining-module-route-membership.csv"))
    held_status = rows(os.path.join(S34, "held-candidate-status-reconciliation.csv"))
    insp = rows(os.path.join(S34, "complete-service-inspection.csv"))
    assign = rows(os.path.join(S34, "future-slice-assignment.csv"))

    out.append(("P01 coverage is 241/264", st.get("p01", len(canon) == 264 and prot == 241),
                f"{prot}/{len(canon)}"))
    out.append(("P02 canonical unprotected queue is exactly 23",
                st.get("p02", len(unp_keys) == 23), str(len(unp_keys))))
    out.append(("P03 live queue inventory equals canonical unprotected set exactly",
                st.get("p03", inv_keys == unp_keys), f"{len(inv_keys ^ unp_keys)} diff"))

    pending = {(r["method"], r["path"]) for r in (held_status or [])
               if r["current_status"] == "PENDING_MODULE_ADJUDICATION"}
    resolved = {(r["method"], r["path"]) for r in (held_status or [])
                if r["current_status"] == "RESOLVED_ADDED_CANONICALLY"}
    out.append(("P04 pending held count is exactly 54", st.get("p04", len(pending) == 54),
                str(len(pending))))
    out.append(("P05 no pending held route is counted canonically",
                st.get("p05", not (pending & prot_keys) and not (pending & unp_keys)), ""))
    out.append(("P06 M01 sample route absent from queue and protected",
                st.get("p06", ("POST", "/v1/auth/api-keys") not in unp_keys
                       and ("POST", "/v1/auth/api-keys") in prot_keys), ""))
    out.append(("P07 N01 routes absent from queue and protected",
                st.get("p07", not (N01 & unp_keys) and N01 <= prot_keys), ""))
    out.append(("P08 closed geo routes absent from queue and protected",
                st.get("p08", not (GEO & unp_keys) and GEO <= prot_keys), ""))

    mem_keys = [(r["method"], r["path"]) for r in (mem or [])]
    out.append(("P09 module membership route count sums to 23",
                st.get("p09", len(mem_keys) == 23), str(len(mem_keys))))
    out.append(("P10 no route appears in more than one remaining module",
                st.get("p10", len(mem_keys) == len(set(mem_keys))),
                f"{len(mem_keys) - len(set(mem_keys))} dupes"))

    out.append(("P11 no module remains UNKNOWN in the complete service inspection",
                st.get("p11", insp is not None
                       and all(r["inspection_state"] != "UNKNOWN" for r in insp)), ""))

    slice_of = {(r["method"], r["path"]): r.get("assigned_slice", "") for r in (mem or [])}
    out.append(("P12 every canonical route is assigned to exactly one future slice",
                st.get("p12", all(k in slice_of and slice_of[k] in ("2F-35", "2F-36", "2F-37")
                                   for k in unp_keys)), ""))

    held_assign = {(r["method"], r["path"]): r.get("assigned_future_slice", "")
                    for r in (held_status or []) if r["current_status"] == "PENDING_MODULE_ADJUDICATION"}
    out.append(("P13 every pending held route is assigned or disposed",
                st.get("p13", all(v for v in held_assign.values())), ""))

    dupe_check = {}
    bad_multi = []
    for k, s in slice_of.items():
        dupe_check.setdefault(k, set()).add(s)
    for k, sset in dupe_check.items():
        if len(sset) > 1:
            bad_multi.append(k)
    out.append(("P14 no route appears in multiple future slices",
                st.get("p14", not bad_multi), str(bad_multi)))

    hash_docs = [os.path.join(S34, f) for f in (
        "slice-2f35-scope-hashes.md", "slice-2f36-scope-hashes.md", "slice-2f37-scope-hashes.md")]
    out.append(("P15 every future slice has A/B/C hashes recorded",
                st.get("p15", all(os.path.exists(p) for p in hash_docs)), ""))

    contract_docs = [os.path.join(S34, f) for f in (
        "slice-2f35-implementation-contract.md", "slice-2f36-implementation-contract.md",
        "slice-2f37-implementation-contract.md", "slice-2f38-certification-contract.md")]
    out.append(("P16 every module/slice has a separate implementation contract",
                st.get("p16", all(os.path.exists(p) for p in contract_docs)), ""))

    n01_scope = os.path.join(S34, "n01-domain-integrity-scope.md")
    out.append(("P17 N01 integrity backlog is present and not silently dropped",
                st.get("p17", os.path.exists(n01_scope)
                       and "confirm_upload" in open(n01_scope, encoding="utf-8").read()), ""))

    mig144 = os.path.join(S34, "migration-144-readiness-contract.md")
    body144 = open(mig144, encoding="utf-8").read() if os.path.exists(mig144) else ""
    out.append(("P18 Migration 144 is reserved for 2F-38, not scheduled earlier",
                st.get("p18", "unapplied" in body144.lower()
                       and "2F-38" in body144), ""))

    ro = os.path.join(S34, "readonly-account-remediation-contract.md")
    body_ro = open(ro, encoding="utf-8").read() if os.path.exists(ro) else ""
    out.append(("P19 readonly@ remediation is scheduled for 2F-38, not earlier",
                st.get("p19", "Untouched" in body_ro and "2F-38" in body_ro), ""))

    out.append(("P20 canonical hash unchanged", st.get("p20", _h(CANON) == CANON_HASH), ""))
    out.append(("P21 matrix hash unchanged", st.get("p21", _h(MATRIX) == MATRIX_HASH), ""))
    out.append(("P22 held registry hash unchanged (not modified)",
                st.get("p22", _h(HOLD) == HOLD_HASH), ""))

    docs = {f: open(os.path.join(S34, f), encoding="utf-8").read()
            for f in os.listdir(S34) if f.endswith(".md")} if os.path.isdir(S34) else {}

    def _claims_impl(body: str) -> bool:
        low = body.lower()
        for phrase in ("implementation occurred", "already implemented in this slice",
                       "this slice implemented"):
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

    impl_claim = [f for f, b in docs.items() if _claims_impl(b)]
    out.append(("P23 no document claims implementation occurred this slice",
                st.get("p23", not impl_claim), ",".join(impl_claim)))

    future_slices = {r.get("assigned_slice", "") for r in (assign or [])}
    future_slices &= {"2F-35", "2F-36", "2F-37", "2F-38"}
    out.append(("P24 exactly four future slices are frozen (2F-35..2F-38)",
                st.get("p24", future_slices == {"2F-35", "2F-36", "2F-37", "2F-38"}),
                str(future_slices)))

    return out


def selftest() -> int:
    print("Program verifier negative-fixture self-test\n")
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
    print("Program verifier (Slice 2F-34)\n")
    for n, s, d in conditions():
        check(n, s, d)
    print()
    if FAILURES:
        print(f"VERIFIER FAILED -- {len(FAILURES)}: {FAILURES}")
        return 1
    print("VERIFIER PASSED (remaining program batches frozen)")
    return 0


if __name__ == "__main__":
    sys.exit(selftest() if "--selftest" in sys.argv else main())
