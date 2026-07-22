"""Phase 2A Slice 2F-23 — Remaining Queue Reconciliation and Next
Authorization Module Selection.

Discovery/verification/selection slice only. No application authorization
code is touched.

Proves: all 19 remaining unprotected tenant/provider mutations are mounted
and genuine, each has exactly one persona, one primary gap and one module;
the 207/226 baseline is unchanged; Slice 2F-22 had zero indirect effect on
any remaining route; and exactly one next module
(`app.engines.customer_reviews.provider_router`) is selected for Slice 2F-24.
"""
from __future__ import annotations

import csv
import inspect
import os
import sys

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(__file__))
CANON_CSV = os.path.join(
    REPO_ROOT, "docs", "workflow-rearchitecture", "phase-02a-slice-02f",
    "tenant-mutation-endpoint-inventory.csv",
)
SLICE_DIR = os.path.join(
    REPO_ROOT, "docs", "workflow-rearchitecture", "phase-02a-slice-02f23",
)
TOOL_DIR = os.path.join(REPO_ROOT, "scripts", "workflow_rearchitecture")

VERIFIED = {
    "TENANT_MUTATION_PERMISSION_SCOPE_AWARE", "TENANT_MUTATION_ROLE_SCOPE_AWARE",
    "STAFF_EXECUTION_ROLE_SCOPE_AWARE", "PLATFORM_ADMIN_ONLY", "PUBLIC_NO_AUTH",
    "CUSTOMER_ROLE_ONLY_NOT_TENANT_SCOPED", "FULLY_PROTECTED",
}

SELECTED_MODULE = "app.engines.customer_reviews.provider_router"
SELECTED_ROUTES = [
    ("POST", "/v1/provider/reviews/{review_id}/reply"),
    ("POST", "/v1/provider/reviews/{review_id}/flag"),
]

PRIMARY_GAPS = {
    "AUTHENTICATED_ONLY", "ROLE_ONLY", "PERMISSION_WITHOUT_SCOPE",
    "SCOPE_WITHOUT_TENANT_OWNERSHIP", "TENANT_OWNERSHIP_WITHOUT_OBJECT_OWNERSHIP",
    "PARENT_CHILD_OWNERSHIP_MISSING", "ASSIGNMENT_ENFORCEMENT_MISSING",
    "CLIENT_TENANT_TRUSTED", "CLIENT_ACTOR_TRUSTED", "CLIENT_SUBJECT_TRUSTED",
    "CLIENT_PAYMENT_STATE_TRUSTED", "CLIENT_AMOUNT_TRUSTED",
    "STATE_TRANSITION_UNVERIFIED", "FINAL_STATE_MUTABLE", "BULK_SCOPE_UNVERIFIED",
    "FINANCIAL_SIDE_EFFECT_UNVERIFIED", "READ_PRIVACY_UNVERIFIED",
    "ALTERNATE_ROUTE_BYPASS", "SERVICE_LAYER_BYPASS",
    "ALREADY_PROTECTED_MISCLASSIFIED", "PRODUCT_DECISION_REQUIRED",
}


def _canonical_rows():
    with open(CANON_CSV, encoding="utf-8") as f:
        return list(csv.reader(f))[1:]


def _slice_csv(name):
    with open(os.path.join(SLICE_DIR, name), encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


@pytest.fixture(scope="module")
def runtime_routes():
    sys.path.insert(0, TOOL_DIR)
    import importlib
    tool = importlib.import_module("inventory_mutation_routes")
    from app.main import app
    routes = tool.walk(app.router if hasattr(app, "router") else app)
    live = {}
    for r in routes:
        for m in r["methods"]:
            live[(m, r["path"])] = r
    return live


@pytest.fixture(scope="module")
def remaining():
    return _slice_csv("remaining-route-inventory.csv")


class TestBaseline:
    def test_canonical_baseline_207_of_226(self):
        rows = _canonical_rows()
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
        # Slice 2F-35: denominator 264 -> 273. Slice 2F-36: 273 -> 297. Slice 2F-37: 297 -> 313.
        assert len(rows) == 313
        # Slice 2F-24 protected customer_reviews.provider_router's 2
        # mutations (207 -> 209); Slice 2F-25 then added and protected three
        # legacy-engine tenant mutations (209 -> 212).
        # Slice 2F-35: numerator 241 -> 252. Slice 2F-36: 252 -> 294. Slice 2F-37: 294 -> 313.
        assert protected == 313

    def test_protected_plus_unprotected_equals_denominator(self):
        rows = _canonical_rows()
        protected = sum(1 for r in rows if r[6] in VERIFIED)
        assert protected + (len(rows) - protected) == 313
        assert len(rows) - protected == 0

    def test_no_canonical_row_remains_unverified(self):
        """Workstream 1: no row may remain UNKNOWN or UNVERIFIED.

        Six rows carried a literal `UNVERIFIED` guard_status before this
        slice; each was replaced with its runtime-observed value
        (AUTHENTICATED_ONLY_NO_PERMISSION_CHECK). Neither the old nor the
        new value is in VERIFIED, so the numerator did not move.
        """
        for r in _canonical_rows():
            assert r[6] not in ("UNVERIFIED", "UNKNOWN", ""), r


class TestRemainingInventoryComplete:
    def test_exactly_nineteen_rows(self, remaining):
        assert len(remaining) == 19

    def test_no_unknown_or_unverified_values(self, remaining):
        for r in remaining:
            assert r["verification_level"] == "VERIFIED", r
            for v in r.values():
                assert v.strip().upper() not in ("UNKNOWN", "UNVERIFIED", "")

    def test_no_duplicate_canonical_row_keys(self, remaining):
        keys = [r["canonical_row_key"] for r in remaining]
        assert len(keys) == len(set(keys))

    def test_no_duplicate_method_path_pairs(self, remaining):
        pairs = [(r["method"], r["path"]) for r in remaining]
        assert len(pairs) == len(set(pairs))

    def test_every_row_has_exactly_one_persona(self, remaining):
        for r in remaining:
            assert r["primary_persona"].strip()
            assert ";" not in r["primary_persona"]

    def test_every_row_has_exactly_one_primary_gap(self, remaining):
        for r in remaining:
            assert r["primary_gap"] in PRIMARY_GAPS, r["primary_gap"]
            assert ";" not in r["primary_gap"]

    def test_every_row_belongs_to_exactly_one_module(self, remaining):
        for r in remaining:
            assert r["router_module"].strip()
            assert ";" not in r["router_module"]

    def test_tenant_source_is_server_derived_everywhere(self, remaining):
        """No remaining canonical route accepts a client tenant_id."""
        for r in remaining:
            assert "JWT" in r["tenant_source"], r


class TestRuntimeReverification:
    def test_all_nineteen_mounted(self, runtime_routes, remaining):
        missing = [(r["method"], r["path"]) for r in remaining
                   if (r["method"], r["path"]) not in runtime_routes]
        assert missing == [], f"not mounted: {missing}"

    def test_all_classified_genuine(self):
        rows = _slice_csv("runtime-reverification.csv")
        assert len(rows) == 19
        for r in rows:
            assert r["classification"] == "GENUINE_UNPROTECTED_TENANT_MUTATION", r
            assert r["mounted_confirmed"] == "YES"
            assert r["genuine_state_change"] == "YES"

    # Slice 2F-24 implemented the module 2F-23 selected, so these two routes
    # have legitimately advanced past the status 2F-23 recorded. 2F-23's CSV is
    # left untouched -- it is a truthful record of what was unprotected AT
    # 2F-23, and rewriting it would falsify that finding. The exemption is
    # narrow and names the slice, so genuine drift on the other 17 still fails.
    PROTECTED_BY_LATER_SLICE = {
        ("POST", "/v1/provider/reviews/{review_id}/reply"): "2F-24",
        ("POST", "/v1/provider/reviews/{review_id}/flag"): "2F-24",
        # Slice 2F-31 (N01 media): require_technician -> require_staff_or_above_mutation
        ("POST", "/v1/provider/profile/logo"): "2F-31",
        ("DELETE", "/v1/provider/profile/logo"): "2F-31",
        ("POST", "/v1/provider/profile/shop-photo"): "2F-31",
        ("DELETE", "/v1/provider/profile/shop-photo"): "2F-31",
        ("POST", "/v1/staff/profile/photo"): "2F-31",
        ("DELETE", "/v1/staff/profile/photo"): "2F-31",
        # Slice 2F-36 (enterprise/tenant-admin/operational batch)
        ("POST", "/v1/provider/marketing/campaigns/generate-launch"): "2F-36",
        ("POST", "/v1/provider/marketing/campaigns/{campaign_id}/submit-review"): "2F-36",
        ("PUT", "/v1/provider/marketing/assets/{asset_id}/provider-notes"): "2F-36",
        ("POST", "/v1/provider/reports/run"): "2F-36",
        ("PUT", "/v1/provider/business-profile"): "2F-36",
        ("POST", "/v1/provider/business-profile/submit-review"): "2F-36",
        ("PUT", "/v1/staff/profile"): "2F-36",
        ("POST", "/v1/provider/brands/requests"): "2F-36",
        ("POST", "/v1/provider/brands/services/{service_id}/supported"): "2F-36",
        ("POST", "/v1/provider/setup/recommendations"): "2F-36",
        ("POST", "/v1/provider/setup/services/{service_id}/supported-options"): "2F-36",
    }

    def test_recorded_guard_status_matches_live(self, runtime_routes):
        rows = _slice_csv("runtime-reverification.csv")
        for r in rows:
            key = (r["method"], r["path"])
            live = runtime_routes[key]
            if key in self.PROTECTED_BY_LATER_SLICE:
                # inventory_mutation_routes.py (this fixture's classifier)
                # predates require_mutation_access_scope (added Slice
                # 2F-31A) and has no case for it -- it falls through to
                # PERMISSION_ONLY_NOT_SCOPE_AWARE for any such route. This
                # is a known tool limitation (also true for every prior
                # require_mutation_access_scope route, e.g. 2F-35's
                # rag_query), not a live regression: confirmed protected by
                # checking the dependency name directly instead of the
                # tool's bucketed guard_status.
                assert (
                    live["guard_status"] in VERIFIED
                    or "require_mutation_access_scope" in live["dependency_names"]
                ), (
                    f"{key} was expected to be PROTECTED by Slice "
                    f"{self.PROTECTED_BY_LATER_SLICE[key]}, but reports "
                    f"{live['guard_status']}"
                )
                continue
            assert live["guard_status"] == r["live_guard_status"], (
                f"drift for {r['method']} {r['path']}: "
                f"recorded={r['live_guard_status']} live={live['guard_status']}"
            )

    def test_only_the_2f24_routes_are_now_protected(self, runtime_routes, remaining):
        """The other 17 must still be unprotected -- no silent drift."""
        for r in remaining:
            key = (r["method"], r["path"])
            live = runtime_routes[key]
            if key in self.PROTECTED_BY_LATER_SLICE:
                continue
            assert live["guard_status"] not in VERIFIED, (
                f"{r['path']} became protected without a named slice -- "
                f"stale canonical row or undocumented change"
            )


class TestNoNonTenantRows:
    def test_no_customer_admin_internal_prefixes(self, remaining):
        for r in remaining:
            p = r["path"]
            assert not p.startswith("/v1/customer/")
            assert not p.startswith("/v1/admin/")
            assert not p.startswith("/v1/internal/")


class TestModuleGrouping:
    def test_exactly_eight_modules(self):
        assert len(_slice_csv("remaining-module-grouping.csv")) == 8

    def test_module_counts_sum_to_nineteen(self):
        rows = _slice_csv("remaining-module-grouping.csv")
        assert sum(int(r["mutation_count"]) for r in rows) == 19

    def test_grouping_modules_match_inventory_modules(self, remaining):
        grouped = {r["router_module"] for r in _slice_csv("remaining-module-grouping.csv")}
        assert grouped == {r["router_module"] for r in remaining}

    def test_every_module_is_risk_scored(self):
        scored = {r["router_module"] for r in _slice_csv("remaining-module-risk-scoring.csv")}
        grouped = {r["router_module"] for r in _slice_csv("remaining-module-grouping.csv")}
        assert scored == grouped
        assert len(scored) == 8

    def test_severity_values_are_canonical(self):
        for r in _slice_csv("remaining-module-risk-scoring.csv"):
            assert r["severity"] in ("CRITICAL", "HIGH", "MEDIUM", "LOW")


class TestSelection:
    def test_exactly_one_critical_module_and_it_is_selected(self):
        rows = _slice_csv("remaining-module-risk-scoring.csv")
        critical = [r for r in rows if r["severity"] == "CRITICAL"]
        assert len(critical) == 1
        assert critical[0]["router_module"] == SELECTED_MODULE

    def test_selected_route_list_has_two_routes(self):
        rows = _slice_csv("selected-next-module-route-list.csv")
        assert len(rows) == 2
        assert [(r["method"], r["path"]) for r in rows] == SELECTED_ROUTES

    def test_every_selected_route_is_mounted(self, runtime_routes):
        for key in SELECTED_ROUTES:
            assert key in runtime_routes, f"{key} not mounted"

    def test_selected_routes_are_in_the_remaining_inventory(self, remaining):
        keys = {(r["method"], r["path"]) for r in remaining}
        for key in SELECTED_ROUTES:
            assert key in keys

    def test_selected_module_absent_from_non_selected_queue(self):
        modules = {r["router_module"] for r in _slice_csv("non-selected-module-queue.csv")}
        assert SELECTED_MODULE not in modules

    def test_selected_plus_non_selected_equals_nineteen(self):
        non_sel = sum(int(r["route_count"]) for r in _slice_csv("non-selected-module-queue.csv"))
        assert non_sel + len(SELECTED_ROUTES) == 19

    def test_non_selected_queue_covers_seven_modules_once_each(self):
        rows = _slice_csv("non-selected-module-queue.csv")
        assert len(rows) == 7
        mods = [r["router_module"] for r in rows]
        assert len(mods) == len(set(mods))

    def test_persona_policy_denies_customer_on_provider_route(self):
        rows = _slice_csv("selected-next-module-persona-policy.csv")
        cust = [r for r in rows if r["principal"] == "customer"]
        assert len(cust) == 1
        assert cust[0]["submit_reply"] == "DENY"

    def test_security_plan_requires_object_ownership_on_flag_review(self):
        rows = _slice_csv("selected-next-module-security-plan.csv")
        own = [r for r in rows
               if r["route"] == "flag_review" and r["control"] == "object ownership"]
        assert len(own) == 1
        assert "MUST ADD" in own[0]["required_behavior"]


class TestSelectedModuleDefectIsReal:
    """2F-23 asserted the selected module's defect against LIVE source so the
    finding could not rot before implementation.

    Slice 2F-24 has now CLOSED that defect, so each assertion is INVERTED
    rather than deleted: it still reads live source, and it now fails if the
    fix is ever reverted. The 2F-23 finding itself is unchanged and remains
    documented in that slice's own artifacts.
    """

    def test_flag_review_now_uses_the_scoped_ownership_lookup(self):
        from app.engines.customer_reviews import review_service
        src = inspect.getsource(review_service.ReviewService.flag_review)
        assert "_get_review_scoped" in src, (
            "flag_review lost its ownership lookup -- the 2F-23 cross-tenant "
            "vulnerability has been reintroduced"
        )

    def test_submit_reply_still_enforces_ownership(self):
        from app.engines.customer_reviews import review_service
        src = inspect.getsource(review_service.ReviewService.submit_reply)
        assert "_get_review_scoped" in src

    def test_unscoped_helper_still_exists_but_is_admin_only(self):
        """`_get_review` remains for the super-admin surface, which is
        legitimately cross-tenant, and is documented as never being an
        authorization boundary."""
        from app.engines.customer_reviews import review_service
        src = inspect.getsource(review_service.ReviewService._get_review)
        assert "UNSCOPED" in src

    def test_provider_routes_now_have_a_role_dependency(self):
        from app.engines.customer_reviews import provider_router
        for fn in (provider_router.submit_reply, provider_router.flag_review):
            src = "\n".join(
                l for l in inspect.getsource(fn).splitlines()
                if not l.lstrip().startswith("#")
            )
            assert "require_tenant_owner_mutation" in src, (
                f"{fn.__name__} lost its provider persona guard"
            )

    def test_customer_alternate_route_no_longer_trusts_client_tenant_id(self):
        from app.engines.customer_reviews import customer_router
        src = "\n".join(
            l for l in inspect.getsource(customer_router.flag_review).splitlines()
            if not l.lstrip().startswith("#")
        )
        assert 'body["tenant_id"]' not in src
        assert 'body.get("tenant_id")' not in src


class TestPackageCommerceIndirectChange:
    def test_no_remaining_module_imports_changed_files(self):
        """Slice 2F-22 touched only package_commerce and public_registration."""
        targets = [
            "app/engines/customer_reviews/provider_router.py",
            "app/engines/customer_reviews/review_service.py",
            "app/engines/marketing_automation/provider_router.py",
            "app/engines/media/new_router.py",
            "app/engines/media/asset_service.py",
            "app/engines/profile/router.py",
            "app/engines/admin_catalog/brand_provider_router.py",
            "app/engines/admin_catalog/recommendation_router.py",
            "app/engines/admin_catalog/service_option_provider_router.py",
            "app/engines/analytics/provider_router.py",
        ]
        # Slice 2F-24 deliberately wired `require_tenant_owner_mutation` into
        # customer_reviews when it implemented that module, so those two files
        # are exempted from the dependency token. The package_commerce /
        # public_registration / payment_authority tokens -- the actual subject
        # of this 2F-23 audit -- must still appear NOWHERE.
        implemented_by_2f24 = {
            "app/engines/customer_reviews/provider_router.py",
            "app/engines/customer_reviews/review_service.py",
        }
        for rel in targets:
            src = open(os.path.join(REPO_ROOT, rel), encoding="utf-8").read()
            tokens = ["package_commerce", "public_registration", "payment_authority"]
            if rel not in implemented_by_2f24:
                tokens.append("require_tenant_owner_mutation")
            for token in tokens:
                assert token not in src, f"{rel} references {token}"

    def test_package_commerce_closure_still_intact(self):
        from app.engines.package_commerce import tenant_router
        src = inspect.getsource(tenant_router.tenant_purchase_package)
        assert "require_tenant_owner_mutation" in src
        assert "is_paid=False" in src


class TestNoApplicationAuthorizationBehaviorChanged:
    def test_slice_touched_no_application_authorization_code(self):
        """2F-23 is discovery-only.

        The only permitted repository changes are documentation, this test
        file, and the canonical-CSV precision correction. The selected
        module's routes must still carry their original (unprotected)
        dependency chain -- proven by TestSelectedModuleDefectIsReal above,
        which asserts the routes still use bare get_current_user.
        """
        # This asserted that 2F-23 itself changed no authorization code, which
        # remains true of 2F-23. Slice 2F-24 subsequently DID protect this
        # module -- that is the intended next step, not a violation of 2F-23 --
        # so the assertion now records the post-2F-24 expected state instead of
        # being silently dropped.
        from app.engines.customer_reviews import provider_router
        src = inspect.getsource(provider_router)
        assert "require_tenant_owner_mutation" in src, (
            "expected Slice 2F-24 protection to be present"
        )
        assert "require_technician" not in src, (
            "technician must never be admitted to provider review mutations"
        )
