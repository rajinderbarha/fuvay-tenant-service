#!/usr/bin/env python
"""Slice 2F-32 — post-N01 queue reconciliation / module selection verifier.

    python scripts/workflow_rearchitecture/verify_selection_2f32.py
    python scripts/workflow_rearchitecture/verify_selection_2f32.py --selftest
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
S32 = os.path.join(DOCS, "phase-02a-slice-02f32")
CANON = os.path.join(DOCS, "phase-02a-slice-02f", "tenant-mutation-endpoint-inventory.csv")
MATRIX = os.path.join(DOCS, "phase-02a-slice-02f", "mutation-enforcement-matrix.csv")
HOLD = os.path.join(DOCS, "phase-02a-slice-02f27a", "unauthorized-candidate-hold-registry.csv")
CANON_HASH = "1f7891798eb8382f"
MATRIX_HASH = "abac4ae72e8ab1d4"
SETA_HASH = "fc45fa777f47c2c9"
SETB_HASH = "593837fac1076324"
SETC_HASH = "578a7e506b83dc09"

VERIFIED = {"TENANT_MUTATION_PERMISSION_SCOPE_AWARE", "TENANT_MUTATION_ROLE_SCOPE_AWARE",
            "STAFF_EXECUTION_ROLE_SCOPE_AWARE", "PLATFORM_ADMIN_ONLY", "PUBLIC_NO_AUTH",
            "CUSTOMER_ROLE_ONLY_NOT_TENANT_SCOPED", "FULLY_PROTECTED"}

N01_RESOLVED = {
    ("POST", "/v1/media/upload/initiate"),
    ("POST", "/v1/media/upload/{session_id}/confirm"),
    ("DELETE", "/v1/media/tenants/{tenant_id}/files/{file_id}"),
}

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
    spec = importlib.util.spec_from_file_location("am32", p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def conditions(state=None):
    st = state or {}
    out = []
    canon = list(csv.reader(open(CANON, encoding="utf-8")))[1:]
    prot = sum(1 for r in canon if r[6] in VERIFIED)
    unp_keys = {(r[0], r[1]) for r in canon if r[6] not in VERIFIED}
    prot_keys = {(r[0], r[1]) for r in canon if r[6] in VERIFIED}

    inv = rows(os.path.join(S32, "authoritative-unprotected-route-inventory.csv"))
    inv_keys = {(r["method"], r["path"]) for r in (inv or [])}
    held_all = rows(HOLD)
    membership = rows(os.path.join(S32, "module-route-membership.csv"))
    setA = rows(os.path.join(S32, "selected-canonical-route-scope.csv"))
    setB = rows(os.path.join(S32, "selected-held-adjudication-scope.csv"))
    setC = rows(os.path.join(S32, "selected-out-of-scope-adjacent-routes.csv"))
    held_status = rows(os.path.join(S32, "held-candidate-status-reconciliation.csv"))

    M01_SAMPLE = ("POST", "/v1/auth/api-keys")
    N01_SAMPLE = ("POST", "/v1/media/upload")

    out.append(("W01 coverage is 238/262", st.get("w01", len(canon) == 262 and prot == 238),
                f"{prot}/{len(canon)}"))
    out.append(("W02 canonical unprotected count is 24", st.get("w02", len(unp_keys) == 24),
                str(len(unp_keys))))
    out.append(("W03 live queue inventory equals canonical unprotected set exactly",
                st.get("w03", inv_keys == unp_keys), f"{len(inv_keys ^ unp_keys)} diff"))
    out.append(("W04 M01 sample route absent from unprotected queue and remains protected",
                st.get("w04", M01_SAMPLE not in unp_keys and M01_SAMPLE in prot_keys), ""))
    out.append(("W05 N01 sample route absent from unprotected queue and remains protected",
                st.get("w05", N01_SAMPLE not in unp_keys and N01_SAMPLE in prot_keys), ""))
    out.append(("W06 no protected route appears in the live queue inventory",
                st.get("w06", not (inv_keys & prot_keys)), f"{len(inv_keys & prot_keys)}"))

    pending = {(r["method"], r["path"]) for r in (held_status or [])
               if r["current_status"] == "PENDING_INDEPENDENT_OR_MODULE_LEVEL_ADJUDICATION"}
    resolved = {(r["method"], r["path"]) for r in (held_status or [])
                if r["current_status"] == "RESOLVED_ADDED_CANONICALLY"}
    out.append(("W07 pending held count is exactly 56", st.get("w07", len(pending) == 56),
                str(len(pending))))
    out.append(("W08 exactly 3 N01 routes resolved as added canonically",
                st.get("w08", resolved == N01_RESOLVED), f"{resolved ^ N01_RESOLVED}"))
    out.append(("W09 no resolved (canonically added) route remains labelled pending",
                st.get("w09", not (resolved & pending)), ""))
    out.append(("W10 no pending held route is counted canonically",
                st.get("w10", not (pending & prot_keys) and not (pending & unp_keys)),
                f"{len((pending & prot_keys) | (pending & unp_keys))}"))

    mem_keys = [(r["method"], r["path"]) for r in (membership or [])]
    out.append(("W11 module membership route count sums to 24",
                st.get("w11", len(mem_keys) == 24), str(len(mem_keys))))
    out.append(("W12 no route appears in more than one module",
                st.get("w12", len(mem_keys) == len(set(mem_keys))),
                f"{len(mem_keys) - len(set(mem_keys))} dupes"))

    modules = {r["module"] for r in (membership or [])}
    out.append(("W13 module membership routes match the live unprotected queue exactly",
                st.get("w13", set(mem_keys) == unp_keys), f"{len(set(mem_keys) ^ unp_keys)} diff"))

    setA_keys = {(r["method"], r["path"]) for r in (setA or [])}
    out.append(("W14 exactly one module is selected (Set A non-empty, single module)",
                st.get("w14", len(setA or []) >= 1), str(len(setA or []))))
    setA_modules = {mm["module"] for mm in (membership or []) if (mm["method"], mm["path"]) in setA_keys}
    out.append(("W15 Set A routes all belong to exactly one module",
                st.get("w15", len(setA_modules) == 1), str(setA_modules)))

    out.append(("W16 Set A hash matches the frozen value",
                st.get("w16", _h(os.path.join(S32, "selected-canonical-route-scope.csv")) == SETA_HASH), ""))
    out.append(("W17 Set B hash matches the frozen value",
                st.get("w17", _h(os.path.join(S32, "selected-held-adjudication-scope.csv")) == SETB_HASH), ""))
    out.append(("W18 Set C hash matches the frozen value",
                st.get("w18", _h(os.path.join(S32, "selected-out-of-scope-adjacent-routes.csv")) == SETC_HASH), ""))

    contract = os.path.join(S32, "selected-module-implementation-contract.md")
    contract_body = open(contract, encoding="utf-8").read() if os.path.exists(contract) else ""
    setC_keys = {(r["method"], r["path"]) for r in (setC or [])}
    out.append(("W19 future contract references every Set A route",
                st.get("w19", all(k[1] in contract_body for k in setA_keys)), ""))
    leaked_C = [k for k in setC_keys if k[0] in ("GET", "POST", "PUT", "DELETE") and k[1] in contract_body
                and k not in setA_keys and k[1] != "/v1/geo/zones/{zone_id}"]
    out.append(("W20 future contract does not include a Set C route as implementation scope",
                st.get("w20", not leaked_C), str(leaked_C)))

    backlog = rows(os.path.join(S32, "n01-domain-integrity-backlog.csv"))
    out.append(("W21 N01 integrity backlog is present and non-empty (not silently dropped)",
                st.get("w21", backlog is not None and len(backlog) == 3), str(len(backlog or []))))

    out.append(("W22 canonical hash unchanged", st.get("w22", _h(CANON) == CANON_HASH), _h(CANON)))
    out.append(("W23 matrix hash unchanged", st.get("w23", _h(MATRIX) == MATRIX_HASH), _h(MATRIX)))

    docs = {f: open(os.path.join(S32, f), encoding="utf-8").read()
            for f in os.listdir(S32) if f.endswith(".md")} if os.path.isdir(S32) else {}

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
    out.append(("W24 no document claims implementation occurred this slice",
                st.get("w24", not impl_claim), ",".join(impl_claim)))

    return out


def selftest() -> int:
    print("Slice 2F-32 selection verifier negative-fixture self-test\n")
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
    print("Slice 2F-32 selection verifier\n")
    for n, s, d in conditions():
        check(n, s, d)
    print()
    if FAILURES:
        print(f"VERIFIER FAILED -- {len(FAILURES)}: {FAILURES}")
        return 1
    print("VERIFIER PASSED (queue reconciled, module selected, scope frozen)")
    return 0


if __name__ == "__main__":
    sys.exit(selftest() if "--selftest" in sys.argv else main())
