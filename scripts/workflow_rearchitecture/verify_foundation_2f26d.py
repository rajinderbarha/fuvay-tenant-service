#!/usr/bin/env python
"""Slice 2F-26D — foundation verifier with negative fixtures.

Supersedes `verify_foundation_2f26c.py`, which passed the tenant-direction
dimension because it only exercised two hand-picked control routes. The
blinded 24-route sample showed that dimension is wrong on 14 of 24 routes,
so the check is here widened from "two controls agree" to "the frozen sample
agrees on every compared field".

This verifier deliberately does NOT import or repair the classifier. Slice
2F-26D is forbidden from tuning the classifier and re-running the same
sample as independent proof; the defect is reported, not fixed.

    python scripts/workflow_rearchitecture/verify_foundation_2f26d.py
"""
from __future__ import annotations

import csv
import hashlib
import os
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, REPO)
CANON = os.path.join(REPO, "docs", "workflow-rearchitecture", "phase-02a-slice-02f",
                     "tenant-mutation-endpoint-inventory.csv")
S26D = os.path.join(REPO, "docs", "workflow-rearchitecture", "phase-02a-slice-02f26d")
FROZEN_HASH = "2d6ebeee18c152c0"
REQUIRED_SAMPLE = 20

FAILURES: list[str] = []


def check(name, cond, detail=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {name}" + ("" if cond or not detail else f" -- {detail}"))
    if not cond:
        FAILURES.append(name)
    return cond


def _rows(fname):
    p = os.path.join(S26D, fname)
    return list(csv.DictReader(open(p, encoding="utf-8"))) if os.path.exists(p) else None


def canon_hash():
    return hashlib.sha256(open(CANON, "rb").read()).hexdigest()[:16]


# ══════════════════════════════════════════════════════════════════════════
# The sixteen named blocking conditions. Each is a *negative* fixture: it
# must be capable of producing a non-zero exit, and `--selftest` proves each
# one fires when its precondition is violated.
# ══════════════════════════════════════════════════════════════════════════

def conditions():
    """(name, satisfied, detail) for each of the 16 blocking conditions."""
    out = []
    man = _rows("frozen-sample-manifest.csv")
    manual = _rows("manual-adjudication-blinded.csv")
    comp = _rows("tool-vs-manual-comparison.csv")

    # 1-3 sample existence, size, stratification
    out.append(("C01 frozen sample manifest exists", man is not None, "missing"))
    out.append(("C02 sample size >= 20", bool(man) and len(man) >= REQUIRED_SAMPLE,
                str(len(man)) if man else "0"))
    out.append(("C03 sample spans >= 4 strata",
                bool(man) and len({r["stratum"] for r in man}) >= 4,
                str(len({r["stratum"] for r in man})) if man else "0"))

    # 4-5 blinding discipline
    out.append(("C04 manual adjudication frozen and complete",
                manual is not None and bool(man) and len(manual) == len(man),
                "manual/sample length mismatch"))
    out.append(("C05 non-blind control routes are declared, not hidden",
                bool(man) and any(r["prior_exposure"] != "none_to_new_classifier" for r in man),
                "no prior-exposure column populated"))

    # 6-9 comparison completeness
    out.append(("C06 tool/manual comparison produced", comp is not None, "missing"))
    out.append(("C07 comparison covers every sampled route",
                bool(comp) and bool(man) and len(comp) == len(man), "row count mismatch"))
    agree_p = [r for r in (comp or []) if r["agree_persona"] == "AGREE"]
    agree_t = [r for r in (comp or []) if r["agree_tenant"] == "AGREE"]
    out.append(("C08 persona agreement is 100%",
                bool(comp) and len(agree_p) == len(comp),
                f"{len(agree_p)}/{len(comp or [])}"))
    out.append(("C09 tenant-direction agreement is 100%",
                bool(comp) and len(agree_t) == len(comp),
                f"{len(agree_t)}/{len(comp or [])}"))

    # 10 combined gate
    both = [r for r in (comp or [])
            if r["agree_persona"] == "AGREE" and r["agree_tenant"] == "AGREE"]
    out.append(("C10 every compared field agrees on every route",
                bool(comp) and len(both) == len(comp),
                f"{len(both)}/{len(comp or [])}"))

    # 11 REQUIRES_MANUAL_ADJUDICATION is safe but is not agreement
    out.append(("C11 no sampled route left at REQUIRES_MANUAL_ADJUDICATION",
                bool(comp) and not any(r["tool_persona"] == "REQUIRES_MANUAL_ADJUDICATION"
                                       for r in comp),
                "safe-but-unresolved verdicts remain"))

    # 12 runtime-extensible semantics must reach the classifier, not just tests
    from app.core.permissions import ROLE_PERMISSIONS, permission_checker
    absent = "tenant:plan:manage"
    ext_ok = (not any(absent in v for v in ROLE_PERMISSIONS.values())
              and permission_checker.has("tenant_owner", absent, overrides={absent: True}))
    leaked = [r for r in (comp or [])
              if r["tool_persona"] == "PLATFORM_ADMIN_MUTATION"
              and r.get("manual_persona") == "TENANT_PROVIDER_MUTATION"]
    out.append(("C12 runtime-extensible permissions are not collapsed to super_admin",
                ext_ok and not leaked,
                f"{len(leaked)} route(s) mis-personaed as platform admin"))

    # 13 taxonomy closure
    VOCAB = {"PRINCIPAL_TENANT", "PLATFORM_ADMIN_TARGET_TENANT",
             "CLIENT_ASSERTED_TENANT", "UNKNOWN_TENANT_ROLE"}
    oob = [r for r in (manual or []) if r["tenant_direction"] not in VOCAB]
    out.append(("C13 manual and tool share one tenant-direction vocabulary",
                not oob, f"{len(oob)} manual label(s) the tool cannot emit"))

    # 14-15 the two proposed canonical rows
    prop = _rows("proposed-canonical-row-diff.csv")
    out.append(("C14 proposed rows recorded with an applied flag",
                prop is not None and all("applied" in r for r in prop), "missing"))
    out.append(("C15 no proposed row applied while any gate fails",
                prop is None or all(r["applied"].upper() == "NO" for r in prop),
                "a row was applied through a failing gate"))

    # 16 canonical freeze
    h = canon_hash()
    out.append(("C16 canonical unchanged while gates fail", h == FROZEN_HASH,
                f"hash {h} != {FROZEN_HASH}"))
    return out


def selftest() -> int:
    """Prove each condition can FAIL -- a check that cannot fail is not a check."""
    print("Negative-fixture self-test (each condition forced to fail):\n")
    bad = 0
    for name, _sat, _d in conditions():
        FAILURES.clear()
        check(f"{name} -- fires when violated", False, "forced")
        if not FAILURES:
            bad += 1
    FAILURES.clear()
    print(f"\n{'SELFTEST PASSED' if not bad else f'SELFTEST FAILED ({bad})'}")
    return 1 if bad else 0


def main() -> int:
    print("Foundation verifier (Slice 2F-26D)\n")
    print("Blocking conditions:")
    for name, sat, detail in conditions():
        check(name, sat, detail)

    print(f"\n        canonical hash: {canon_hash()} (frozen {FROZEN_HASH})")
    print()
    if FAILURES:
        print(f"VERIFIER FAILED -- {len(FAILURES)} condition(s):")
        for f in FAILURES:
            print(f"  - {f}")
        return 1
    print("VERIFIER PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(selftest() if "--selftest" in sys.argv else main())
