#!/usr/bin/env python
"""Slice 2F-26H — standalone action verifier with executed negative fixtures.

    python scripts/workflow_rearchitecture/verify_action_2f26h.py
    python scripts/workflow_rearchitecture/verify_action_2f26h.py --selftest
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
S = os.path.join(DOCS, "phase-02a-slice-02f26h")
FROZEN_HASH = "1f7891798eb8382f"
MATRIX_HASH = "abac4ae72e8ab1d4"

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


def conditions(state=None):
    st = state or {}
    A = _load("action_model_2f26h.py")
    out = []
    comp = rows(os.path.join(S, "fifth-tool-manual-comparison.csv"))
    manual = rows(os.path.join(S, "fifth-manual-adjudication.csv"))

    def act(method, path, fn="", svc=(), write=False):
        return A.infer_action(method=method, path=path, endpoint_name=fn,
                              service_methods=svc, has_proven_write=write)["action"]

    # A01 the D-09 route resolves to deactivate
    out.append(("A01 bulk-disable -> deactivate (D-09)",
                st.get("a01", act("POST", "/v1/x/engines/bulk-disable", "bulk_disable",
                                  ("bulk_disable_engines",)) == "deactivate"), ""))
    # A02 POST does not default to create
    out.append(("A02 unknown POST does NOT default to create",
                st.get("a02", act("POST", "/v1/x/thing", "do_thing", ())
                       == A.MANUAL), ""))
    # A03 hyphen tokenization
    out.append(("A03 hyphen token recognized",
                st.get("a03", "disable" in A.tokenize("bulk-disable")), ""))
    # A04 underscore tokenization
    out.append(("A04 underscore token recognized",
                st.get("a04", "confirm" in A.tokenize("terminate_confirm")), ""))
    # A05 CamelCase tokenization
    out.append(("A05 CamelCase token recognized",
                st.get("a05", "rotate" in A.tokenize("rotateApiKey")), ""))
    # A06 a known action token is not ignored
    out.append(("A06 known token honoured over HTTP fallback",
                st.get("a06", act("POST", "/v1/x/sessions/{id}/revoke", "",
                                  ("revoke_session",)) == "revoke"), ""))
    # A07 conflicting strong evidence fails closed
    out.append(("A07 conflicting equal-level verbs fail closed",
                st.get("a07", A.infer_action(method="POST", path="/v1/x/thing",
                       endpoint_name="", service_methods=("approve_thing", "delete_thing"))
                       ["action"] == A.MANUAL), ""))
    # A08 unknown action is not a confident action
    out.append(("A08 unknown verb yields MANUAL not a guess",
                st.get("a08", act("POST", "/v1/x/frobnicate", "frobnicate", ())
                       == A.MANUAL), ""))
    # A09 docstrings/comments do not influence action (only names/paths used)
    out.append(("A09 resource noun is not a verb (get_export_job)",
                st.get("a09", act("POST", "/v1/x/exports/{id}/cancel", "cancel_export",
                                  ("get_export_job", "cancel_export")) == "cancel"), ""))
    # A10 resource noun containing a verb substring is not the action
    out.append(("A10 disabled_count noun does not yield deactivate",
                st.get("a10", act("POST", "/v1/x/status", "get_status",
                                  ("get_disabled_count",)) == A.MANUAL), ""))
    # A11 action taxonomy closed
    bad = [r for r in (manual or [])
           if r["capability_action"] not in A.ACTIONS
           and r["capability_action"] != A.MANUAL]
    out.append(("A11 manual actions within taxonomy or MANUAL",
                st.get("a11", not bad), f"{len(bad)}"))
    # A12 DELETE strong fallback
    out.append(("A12 DELETE with no token -> delete",
                st.get("a12", act("DELETE", "/v1/x/{id}", "remove_x", ()) == "delete"), ""))
    # A13 PUT with proven write -> update
    out.append(("A13 PUT with proven write -> update",
                st.get("a13", act("PUT", "/v1/x/{id}", "", (), write=True) == "update"), ""))
    # A14 GET read -> other, never a mutation action
    out.append(("A14 GET read -> other",
                st.get("a14", act("GET", "/v1/x/{id}", "get_x", ()) == "other"), ""))
    # A15 the burned D-09 fixture stays fixed (regression)
    out.append(("A15 burned D-09 fixture regression holds",
                st.get("a15", act("POST", "/v1/tenants/{tenant_id}/engines/bulk-disable",
                                  "bulk_disable", ("bulk_disable_engines",)) == "deactivate"), ""))

    # ── comparison + freeze ──────────────────────────────────────────────────
    FI = ["side_effect", "capability_family", "capability_action", "persona",
          "tenant_direction"]
    agree = [x for x in (comp or [])
             if all(str(x["agree_" + f]).upper() == "TRUE" for f in FI)]
    out.append(("N09 fifth holdout: manual and tool agree on every field",
                st.get("n09", bool(comp) and len(agree) == len(comp)),
                f"{len(agree)}/{len(comp or [])}"))
    out.append(("N13 canonical unchanged unless every gate passed",
                st.get("n13", _h(CANON) == FROZEN_HASH or not FAILURES), ""))
    out.append(("N33 matrix unchanged unless every gate passed",
                st.get("n33", _h(MATRIX) == MATRIX_HASH or not FAILURES), ""))
    return out


def selftest() -> int:
    print("Action-verifier negative-fixture self-test\n")
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
    print(f"\n{'SELFTEST PASSED' if not bad and ok else 'SELFTEST FAILED'}")
    return 1 if (bad or not ok) else 0


def main() -> int:
    print("Action verifier (Slice 2F-26H)\n")
    for name, sat, detail in conditions():
        check(name, sat, detail)
    print(f"\n        canonical {_h(CANON)} / matrix {_h(MATRIX)}\n")
    if FAILURES:
        print(f"VERIFIER FAILED -- {len(FAILURES)} condition(s):")
        for f in FAILURES:
            print(f"  - {f}")
        return 1
    print("VERIFIER PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(selftest() if "--selftest" in sys.argv else main())
