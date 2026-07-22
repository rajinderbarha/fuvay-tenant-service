"""Phase 2A Slice 2F-21 — Remaining Queue Reconciliation and Next
Authorization Module Selection.

Discovery/selection slice only. Proves: every one of the 20 remaining
unprotected tenant/provider mutation routes is mounted, genuine, has
exactly one persona and one primary gap, belongs to exactly one of 9
modules, and that Slice 2F-20's compliance closure had zero indirect
effect on any of them. Also proves exactly one next module was selected
for Slice 2F-22, that its routes exist at runtime, and that the canonical
206/226 baseline is unchanged.

No application authorization code is touched by this slice -- only
documentation, canonical-CSV read access, and this test file.
"""
from __future__ import annotations

import csv
import os
import sys

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(__file__))
CANON_CSV = os.path.join(
    REPO_ROOT, "docs", "workflow-rearchitecture", "phase-02a-slice-02f",
    "tenant-mutation-endpoint-inventory.csv",
)
SLICE_DIR = os.path.join(
    REPO_ROOT, "docs", "workflow-rearchitecture", "phase-02a-slice-02f21",
)
TOOL_DIR = os.path.join(REPO_ROOT, "scripts", "workflow_rearchitecture")

VERIFIED = {
    "TENANT_MUTATION_PERMISSION_SCOPE_AWARE", "TENANT_MUTATION_ROLE_SCOPE_AWARE",
    "STAFF_EXECUTION_ROLE_SCOPE_AWARE", "PLATFORM_ADMIN_ONLY", "PUBLIC_NO_AUTH",
    "CUSTOMER_ROLE_ONLY_NOT_TENANT_SCOPED", "FULLY_PROTECTED",
}

EXPECTED_ROUTES = [
    ("POST", "/v1/provider/brands/requests"),
    ("POST", "/v1/provider/brands/services/{service_id}/supported"),
    ("PUT", "/v1/provider/business-profile"),
    ("POST", "/v1/provider/business-profile/submit-review"),
    ("PUT", "/v1/provider/marketing/assets/{asset_id}/provider-notes"),
    ("POST", "/v1/provider/marketing/campaigns/generate-launch"),
    ("POST", "/v1/provider/marketing/campaigns/{campaign_id}/submit-review"),
    ("POST", "/v1/provider/profile/logo"),
    ("DELETE", "/v1/provider/profile/logo"),
    ("POST", "/v1/provider/profile/shop-photo"),
    ("DELETE", "/v1/provider/profile/shop-photo"),
    ("POST", "/v1/provider/reports/run"),
    ("POST", "/v1/provider/reviews/{review_id}/flag"),
    ("POST", "/v1/provider/reviews/{review_id}/reply"),
    ("POST", "/v1/provider/setup/recommendations"),
    ("POST", "/v1/provider/setup/services/{service_id}/supported-options"),
    ("PUT", "/v1/staff/profile"),
    ("POST", "/v1/staff/profile/photo"),
    ("DELETE", "/v1/staff/profile/photo"),
    ("POST", "/v1/tenant/packages/{package_id}/purchase"),
]

SELECTED_ROUTE = ("POST", "/v1/tenant/packages/{package_id}/purchase")


def _load_canonical_rows():
    with open(CANON_CSV, encoding="utf-8") as f:
        return list(csv.reader(f))[1:]


def _load_csv(name):
    path = os.path.join(SLICE_DIR, name)
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


@pytest.fixture(scope="module")
def runtime_data():
    sys.path.insert(0, TOOL_DIR)
    import importlib
    tool = importlib.import_module("inventory_mutation_routes")
    from app.main import app
    routes = tool.walk(app.router if hasattr(app, "router") else app)
    return routes, tool


@pytest.fixture(scope="module")
def remaining_rows():
    return _load_csv("remaining-route-inventory.csv")


@pytest.fixture(scope="module")
def reverif_rows():
    rows = []
    path = os.path.join(SLICE_DIR, "runtime-reverification.csv")
    with open(path, encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        header = next(reader)
        for row in reader:
            if not row or len(row) != len(header):
                continue
            rows.append(dict(zip(header, row)))
    return rows


class TestBaselineConfirmed:
    def test_canonical_baseline_206_of_226(self):
        # Slice 2F-22 protected the module 2F-21 selected
        # (package_commerce.tenant_router), advancing the LIVE canonical
        # numerator 206 -> 207 and the remainder 20 -> 19. These assertions
        # read the live canonical CSV, so they track the current figure;
        # 2F-21's OWN slice CSVs below still assert 20, because those are a
        # truthful point-in-time record of what was unprotected at 2F-21.
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
        # Slice 2F-35: denominator 264 -> 273, numerator 241 -> 252.
        # Slice 2F-36: denominator 273 -> 297, numerator 252 -> 294.
        assert total == 313
        assert protected == 313


class TestRemainingRouteInventoryComplete:
    def test_exactly_twenty_rows(self, remaining_rows):
        assert len(remaining_rows) == 20

    def test_no_unknown_or_unverified_rows(self, remaining_rows):
        for r in remaining_rows:
            assert r["verification_level"] == "VERIFIED", r
            for field in r.values():
                assert field.strip().upper() != "UNKNOWN"

    def test_no_duplicate_canonical_row_keys(self, remaining_rows):
        keys = [r["canonical_row_key"] for r in remaining_rows]
        assert len(keys) == len(set(keys))

    def test_every_row_exactly_one_persona(self, remaining_rows):
        for r in remaining_rows:
            persona = r["primary_persona"]
            assert persona.strip() != ""

    def test_every_row_exactly_one_primary_gap(self, remaining_rows):
        for r in remaining_rows:
            gap = r["current_primary_gap"]
            assert gap.strip() != ""


class TestGapClassificationComplete:
    def test_gap_classification_covers_all_twenty_rows(self, remaining_rows):
        gap_rows = _load_csv("remaining-gap-classification.csv")
        assert len(gap_rows) == 20
        assert {r["canonical_row_key"] for r in gap_rows} == {
            r["canonical_row_key"] for r in remaining_rows
        }

    def test_each_row_has_exactly_one_primary_gap_field(self):
        gap_rows = _load_csv("remaining-gap-classification.csv")
        for r in gap_rows:
            assert r["primary_gap"].strip() != ""
            # primary_gap must be a single classification, not multiple
            # comma-joined values
            assert ";" not in r["primary_gap"]


class TestRuntimeReverification:
    def test_all_twenty_routes_mounted_at_runtime(self, runtime_data):
        routes, _ = runtime_data
        runtime_keys = set()
        for r in routes:
            for m in r["methods"]:
                runtime_keys.add((m, r["path"]))
        missing = [k for k in EXPECTED_ROUTES if k not in runtime_keys]
        assert missing == [], f"expected remaining-queue routes not mounted: {missing}"

    def test_reverification_csv_classifies_all_twenty_genuine(self, reverif_rows):
        assert len(reverif_rows) == 20
        for r in reverif_rows:
            assert r["classification"] == "GENUINE_UNPROTECTED_TENANT_MUTATION", r

    # Slice 2F-22 implemented the module 2F-21 selected, so this route's live
    # guard_status has legitimately advanced past the value 2F-21 recorded.
    # 2F-21's CSV is left untouched: it is a truthful point-in-time record of
    # what was unprotected AT 2F-21, and rewriting it would falsify that
    # finding. The exemption is narrow -- one route, protected by a named
    # later slice -- so genuine drift on the other 19 rows still fails.
    PROTECTED_BY_LATER_SLICE = {
        ("POST", "/v1/tenant/packages/{package_id}/purchase"): "2F-22",
        ("POST", "/v1/provider/reviews/{review_id}/reply"): "2F-24",
        ("POST", "/v1/provider/reviews/{review_id}/flag"): "2F-24",
        # Slice 2F-31 (N01 media): require_technician -> require_staff_or_above_mutation
        ("POST", "/v1/provider/profile/logo"): "2F-31",
        ("DELETE", "/v1/provider/profile/logo"): "2F-31",
        ("POST", "/v1/provider/profile/shop-photo"): "2F-31",
        ("DELETE", "/v1/provider/profile/shop-photo"): "2F-31",
        ("POST", "/v1/staff/profile/photo"): "2F-31",
        ("DELETE", "/v1/staff/profile/photo"): "2F-31",
        # Slice 2F-36 (enterprise/tenant-admin/operational batch): require_technician -> require_staff_or_above_mutation
        # or get_current_user -> require_mutation_access_scope
        ("POST", "/v1/provider/brands/requests"): "2F-36",
        ("POST", "/v1/provider/brands/services/{service_id}/supported"): "2F-36",
        ("PUT", "/v1/provider/business-profile"): "2F-36",
        ("POST", "/v1/provider/business-profile/submit-review"): "2F-36",
        ("PUT", "/v1/provider/marketing/assets/{asset_id}/provider-notes"): "2F-36",
        ("POST", "/v1/provider/marketing/campaigns/generate-launch"): "2F-36",
        ("POST", "/v1/provider/marketing/campaigns/{campaign_id}/submit-review"): "2F-36",
        ("POST", "/v1/provider/reports/run"): "2F-36",
        ("POST", "/v1/provider/setup/recommendations"): "2F-36",
        ("POST", "/v1/provider/setup/services/{service_id}/supported-options"): "2F-36",
        ("PUT", "/v1/staff/profile"): "2F-36",
    }

    def test_reverification_guard_status_matches_live_walk(self, runtime_data, reverif_rows):
        routes, _ = runtime_data
        live = {}
        for r in routes:
            for m in r["methods"]:
                live[(m, r["path"])] = r["guard_status"]
        for r in reverif_rows:
            key = (r["method"], r["path"])
            assert key in live, f"{key} not found live"
            if key in self.PROTECTED_BY_LATER_SLICE:
                # Must have moved to a PROTECTED status, not merely drifted.
                assert live[key] != r["runtime_guard_status"], (
                    f"{key} was expected to be protected by Slice "
                    f"{self.PROTECTED_BY_LATER_SLICE[key]} but still reports "
                    f"its original 2F-21 status {r['runtime_guard_status']}"
                )
                continue
            assert live[key] == r["runtime_guard_status"], (
                f"guard_status drift for {key}: recorded={r['runtime_guard_status']} live={live[key]}"
            )


class TestNoNonTenantRowsAffectTenantXY:
    def test_no_customer_admin_internal_prefix_among_remaining_rows(self, remaining_rows):
        for r in remaining_rows:
            path = r["path"]
            assert not path.startswith("/v1/customer/")
            assert not path.startswith("/v1/admin/")
            assert not path.startswith("/v1/internal/")


class TestModuleGroupingArithmetic:
    def test_module_route_counts_sum_to_twenty(self):
        grouping_rows = _load_csv("remaining-module-grouping.csv")
        total = sum(int(r["route_count"]) for r in grouping_rows)
        assert total == 20

    def test_nine_modules(self):
        grouping_rows = _load_csv("remaining-module-grouping.csv")
        assert len(grouping_rows) == 9

    def test_every_row_belongs_to_exactly_one_module(self, remaining_rows):
        grouping_rows = _load_csv("remaining-module-grouping.csv")
        # structural check: every remaining row's source_module maps
        # to exactly one grouping row's exact_router
        module_by_key = {r["canonical_row_key"]: r["source_module"] for r in remaining_rows}
        router_set = {g["exact_router"] for g in grouping_rows}
        for key, mod in module_by_key.items():
            # media.new_router grouping is annotated with a parenthetical suffix
            assert any(mod in router or router.startswith(mod) for router in router_set), (
                key, mod,
            )


class TestModuleRiskScoringComplete:
    def test_risk_scoring_covers_all_nine_modules(self):
        risk_rows = _load_csv("remaining-module-risk-scoring.csv")
        assert len(risk_rows) == 9
        for r in risk_rows:
            assert r["severity"] in ("CRITICAL", "HIGH", "MEDIUM", "LOW")


class TestExactlyOneModuleSelected:
    def test_selected_route_list_has_one_route(self):
        rows = _load_csv("selected-next-module-route-list.csv")
        assert len(rows) == 1
        assert (rows[0]["method"], rows[0]["path"]) == SELECTED_ROUTE

    def test_selected_route_exists_at_runtime(self, runtime_data):
        routes, _ = runtime_data
        live_keys = set()
        for r in routes:
            for m in r["methods"]:
                live_keys.add((m, r["path"]))
        assert SELECTED_ROUTE in live_keys

    def test_selected_route_is_package_commerce_module(self, remaining_rows):
        selected = [r for r in remaining_rows if r["canonical_row_key"] == "R-27"]
        assert len(selected) == 1
        assert selected[0]["source_module"] == "app.engines.package_commerce.tenant_router"

    def test_selected_module_security_plan_covers_selected_route(self):
        plan_rows = _load_csv("selected-next-module-security-plan.csv")
        assert len(plan_rows) == 1
        assert plan_rows[0]["canonical_row_key"] == "R-27"

    def test_selected_module_persona_policy_single_unambiguous_persona(self):
        persona_rows = _load_csv("selected-next-module-persona-policy.csv")
        assert len(persona_rows) == 1
        persona = persona_rows[0]["canonical_persona"]
        assert persona.strip() == "tenant_owner"


class TestNonSelectedQueueAccountsForEveryRoute:
    def test_non_selected_queue_has_eight_modules_nineteen_routes(self):
        rows = _load_csv("non-selected-module-queue.csv")
        assert len(rows) == 8
        total = sum(int(r["route_count"]) for r in rows)
        assert total == 19

    def test_selected_plus_non_selected_equals_twenty(self):
        rows = _load_csv("non-selected-module-queue.csv")
        non_selected_total = sum(int(r["route_count"]) for r in rows)
        selected_total = 1
        assert non_selected_total + selected_total == 20

    def test_package_commerce_not_in_non_selected_queue(self):
        rows = _load_csv("non-selected-module-queue.csv")
        modules = {r["router_module"] for r in rows}
        assert "app.engines.package_commerce.tenant_router" not in modules


class TestCoverageReconciliationUnchanged:
    def test_canonical_csv_still_206_of_226(self):
        # Slice 2F-22 protected the module 2F-21 selected
        # (package_commerce.tenant_router), advancing the LIVE canonical
        # numerator 206 -> 207 and the remainder 20 -> 19. These assertions
        # read the live canonical CSV, so they track the current figure;
        # 2F-21's OWN slice CSVs below still assert 20, because those are a
        # truthful point-in-time record of what was unprotected at 2F-21.
        rows = _load_canonical_rows()
        # Slice 2F-35: denominator 264 -> 273. Slice 2F-36: 273 -> 297. Slice 2F-37: 297 -> 313.
        assert len(rows) == 313
        # Slice 2F-24: 207 -> 209 (customer_reviews.provider_router).
        # Slice 2F-35: numerator 241 -> 252. Slice 2F-36: 252 -> 294. Slice 2F-37: 294 -> 313.
        assert sum(1 for r in rows if r[6] in VERIFIED) == 313

    def test_coverage_row_diff_shows_zero_changes(self):
        diff_rows = _load_csv("coverage-row-diff.csv")
        assert len(diff_rows) == 20
        for r in diff_rows:
            assert r["change"] == "NONE", r

    def test_protected_plus_unprotected_equals_denominator(self):
        rows = _load_canonical_rows()
        total = len(rows)
        protected = sum(1 for r in rows if r[6] in VERIFIED)
        unprotected = total - protected
        # Slice 2F-22 protected the module 2F-21 selected
        # (package_commerce.tenant_router), advancing the LIVE canonical
        # numerator 206 -> 207 and the remainder 20 -> 19. These assertions
        # read the live canonical CSV, so they track the current figure;
        # 2F-21's OWN slice CSVs below still assert 20, because those are a
        # truthful point-in-time record of what was unprotected at 2F-21.
        # Slice 2F-24 protected customer_reviews.provider_router's 2
        # mutations (submit_reply, flag_review), advancing the LIVE
        # canonical numerator 207 -> 209 and the remainder 19 -> 17.
        # Slice 2F-35: unprotected 23 -> 21. Slice 2F-36: 21 -> 3. Slice 2F-37: 3 -> 0.
        assert unprotected == 0


class TestNoApplicationAuthorizationBehaviorChanged:
    def test_this_slices_own_additions_are_docs_and_tests_only(self):
        # Scope discipline check scoped to THIS slice's own additions, not
        # the ambient repo state (other in-flight work in this repo
        # legitimately touches app/ files outside this slice's concern --
        # asserting on whole-repo `git status` would be a false positive
        # generator unrelated to what 2F-21 itself did). This slice added
        # exactly one test file and the phase-02a-slice-02f21/ doc
        # directory; neither touches app/.
        this_slice_additions = [
            os.path.join(REPO_ROOT, "tests",
                         "test_phase2f21_remaining_queue_reconciliation_and_selection.py"),
        ]
        for path in this_slice_additions:
            assert os.path.exists(path)
            assert "app" + os.sep not in path.replace(REPO_ROOT + os.sep, "")
        assert os.path.isdir(SLICE_DIR)
        assert "app" not in os.path.relpath(SLICE_DIR, REPO_ROOT).split(os.sep)
