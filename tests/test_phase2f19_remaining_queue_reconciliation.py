"""Slice 2F-19 — Remaining Queue Reconciliation and Next Authorization
Module Selection.

Discovery/selection slice — no application authorization behavior changes.
This suite proves the reconciliation claims made in this slice's
documentation:
- The 200/226 baseline is unchanged.
- All 26 remaining rows are individually accounted for, each mounted,
  each a genuine tenant mutation, each belonging to exactly one of the
  10 remaining modules.
- No duplicate route keys exist among the 26.
- No non-tenant route affects the canonical CSV.
- The non-selected queue accounts for every remaining route exactly once.
- Exactly one next module (compliance.provider_router) is selected, and
  every one of its 6 routes exists at runtime.
"""
from __future__ import annotations

import csv
import os

import pytest

pytestmark = pytest.mark.skipif(
    not os.path.isdir(os.path.join(os.path.dirname(os.path.dirname(__file__)), "docs", "workflow-rearchitecture", "phase-02a-slice-02f19")),
    reason="retired point-in-time workflow reconciliation artifacts are intentionally absent",
)

DOCS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "docs", "workflow-rearchitecture",
)
CANONICAL_CSV = os.path.join(
    DOCS_DIR, "phase-02a-slice-02f", "tenant-mutation-endpoint-inventory.csv",
)
SLICE_DIR = os.path.join(DOCS_DIR, "phase-02a-slice-02f19")

VERIFIED = {
    "TENANT_MUTATION_PERMISSION_SCOPE_AWARE",
    "TENANT_MUTATION_ROLE_SCOPE_AWARE",
    "STAFF_EXECUTION_ROLE_SCOPE_AWARE",
    "PLATFORM_ADMIN_ONLY",
    "PUBLIC_NO_AUTH",
    "CUSTOMER_ROLE_ONLY_NOT_TENANT_SCOPED",
    "FULLY_PROTECTED",
}


def _load_canonical_rows():
    with open(CANONICAL_CSV, newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f))
    return rows[1:]  # skip header


def _load_slice_csv(name):
    path = os.path.join(SLICE_DIR, name)
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.reader(f))


class TestCanonicalBaseline:
    def test_226_total_200_protected_26_unprotected(self):
        """Baseline recount against the LIVE canonical CSV.

        Slice 2F-21 correction: this assertion still read `protected == 200`
        (2F-19's own point-in-time baseline) after Slice 2F-20 protected
        compliance.provider_router's 6 routes and advanced the numerator to
        206. 2F-20 updated the other two recount assertions
        (test_phase2f14a_field_ops_alternate_route_and_coverage.py and
        test_phase2f17a_global_mutation_inventory.py) but MISSED this third
        one, leaving it failing from 2F-20's merge until now -- a genuine,
        slice-attributable regression that 2F-20's own regression report
        incorrectly described as an unchanged pre-existing baseline. See
        docs/workflow-rearchitecture/phase-02a-slice-02f21/documentation-corrections.md.

        The method name retains its original historical numbers; the
        assertions below track the CURRENT canonical figures, which is what
        this test exists to verify.
        """
        rows = _load_canonical_rows()
        total = len(rows)
        protected = sum(1 for r in rows if r[6] in VERIFIED)
        # Slice 2F-25 discovered three genuine tenant mutations on the
        # legacy review engine (/v1/reviews/*) that the prefix-based
        # sweep never considered, added them to the canonical CSV by
        # exact route evidence, and protected all three in the same
        # slice: denominator 226 -> 229, numerator 209 -> 212.
        # Slice 2F-26 application-wide persona sweep: 28 tenant mutations
        # on generic prefixes (/v1/auth, /v1/media, /v1/me, /v1/bookings,
        # /v1/commerce, /v1/enterprise, /v1/rag) had never been counted --
        # the prefix-based sweep never considered them. Denominator
        # 229 -> 257, numerator 212 -> 214 (26 of the 28 are unprotected),
        # unprotected 17 -> 43.
        # Slice 2F-35: denominator 264 -> 273, numerator 241 -> 252,
        # unprotected 23 -> 21.
        # Slice 2F-36: denominator 273 -> 297, numerator 252 -> 294, unprotected 21 -> 3.
        # Slice 2F-37: denominator 297 -> 313, numerator 294 -> 313, unprotected 3 -> 0.
        assert total == 313
        assert protected == 313
        assert total - protected == 0


class TestRemainingRowCompleteness:
    def test_remaining_route_inventory_has_26_rows(self):
        rows = _load_slice_csv("remaining-route-inventory.csv")
        data_rows = [r for r in rows[1:] if r and r[0]]
        assert len(data_rows) == 26

    def test_no_duplicate_route_keys_among_remaining(self):
        rows = _load_slice_csv("remaining-route-inventory.csv")
        data_rows = [r for r in rows[1:] if r and r[0]]
        keys = [(r[0], r[1]) for r in data_rows]  # (method, path)
        assert len(keys) == len(set(keys))

    def test_runtime_reverification_confirms_all_26_mounted(self):
        rows = _load_slice_csv("runtime-reverification.csv")
        data_rows = [r for r in rows[1:] if r and r[0] and r[0] in ("GET", "POST", "PUT", "DELETE", "PATCH")]
        assert len(data_rows) == 26
        for r in data_rows:
            assert r[2] == "YES"  # mounted_confirmed
            assert r[3] == "YES"  # endpoint_function_confirmed
            assert r[5] == "GENUINE_UNPROTECTED_TENANT_MUTATION"


class TestModuleGrouping:
    def test_remaining_modules_sum_to_26_routes(self):
        rows = _load_slice_csv("remaining-module-grouping.csv")
        data_rows = [r for r in rows[1:] if r and r[0]]
        total = sum(int(r[2]) for r in data_rows)
        assert total == 26

    def test_exactly_ten_remaining_modules(self):
        rows = _load_slice_csv("remaining-module-grouping.csv")
        data_rows = [r for r in rows[1:] if r and r[0]]
        assert len(data_rows) == 10


class TestRiskScoring:
    def test_every_remaining_module_is_scored(self):
        rows = _load_slice_csv("remaining-module-risk-scoring.csv")
        data_rows = [
            r for r in rows[1:]
            if r and r[0] and r[-1] in ("CRITICAL", "HIGH", "MEDIUM", "LOW")
        ]
        assert len(data_rows) == 10

    def test_compliance_is_sole_critical_module(self):
        rows = _load_slice_csv("remaining-module-risk-scoring.csv")
        data_rows = [
            r for r in rows[1:]
            if r and r[0] and r[-1] in ("CRITICAL", "HIGH", "MEDIUM", "LOW")
        ]
        critical = [r for r in data_rows if r[-1] == "CRITICAL"]
        assert len(critical) == 1
        assert critical[0][0] == "compliance"


class TestNonSelectedQueue:
    def test_queue_accounts_for_all_26_routes_exactly_once(self):
        rows = _load_slice_csv("non-selected-module-queue.csv")
        data_rows = [
            r for r in rows[1:]
            if r and r[0] and (r[0].startswith("0") or r[0].isdigit())
        ]
        total = sum(int(r[2]) for r in data_rows)
        assert total == 26

    def test_selected_module_is_compliance_provider_router(self):
        rows = _load_slice_csv("non-selected-module-queue.csv")
        selected = [r for r in rows[1:] if r and r[0].startswith("0")]
        assert len(selected) == 1
        assert selected[0][1] == "app.engines.compliance.provider_router"
        assert selected[0][2] == "6"


class TestSelectedModuleRuntimeExistence:
    def test_all_six_selected_routes_exist_in_canonical_csv(self):
        rows = _load_slice_csv("selected-next-module-route-list.csv")
        data_rows = [r for r in rows[1:] if r and r[0]]
        assert len(data_rows) == 6
        canonical = _load_canonical_rows()
        canonical_keys = {(r[0], r[1]) for r in canonical}
        for r in data_rows:
            method, path = r[0], r[1]
            assert (method, path) in canonical_keys, f"{method} {path} not in canonical CSV"
            assert r[4] == "YES"  # confirmed_mounted

    def test_selected_routes_are_mounted_at_runtime(self):
        import sys
        tool_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "scripts", "workflow_rearchitecture",
        )
        sys.path.insert(0, tool_dir)
        import importlib
        tool = importlib.import_module("inventory_mutation_routes")
        from app.main import app
        routes = tool.walk(app.router if hasattr(app, "router") else app)
        mounted = set()
        for r in routes:
            for m in r["methods"]:
                mounted.add((m, r["path"]))

        rows = _load_slice_csv("selected-next-module-route-list.csv")
        data_rows = [r for r in rows[1:] if r and r[0]]
        for r in data_rows:
            method, path = r[0], r[1]
            assert (method, path) in mounted, f"{method} {path} not mounted at runtime"


class TestCoverageUnchanged:
    def test_coverage_row_diff_shows_zero_corrections(self):
        rows = _load_slice_csv("coverage-row-diff.csv")
        data_rows = [r for r in rows[1:] if r and r[0]]
        assert len(data_rows) == 1
        assert data_rows[0][3] == "NO ROWS CHANGED"
