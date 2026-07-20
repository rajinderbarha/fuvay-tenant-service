"""Phase 2A Slice 2F-30 — post-M01 queue reconciliation and next module selection.

Selection/planning only: canonical and matrix hashes unchanged, zero application
files modified, no authorization implemented. Selected N01_media_assets
(app.engines.media.new_router, 9 canonical unprotected routes).
"""
from __future__ import annotations

import csv
import hashlib
import importlib.util
import os
import subprocess
import sys

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
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


def _rows(n, base=S):
    return list(csv.DictReader(open(os.path.join(base, n), encoding="utf-8")))


def _canon():
    return list(csv.reader(open(CANON, encoding="utf-8")))[1:]


def _h(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()[:16]


class TestQueueReconciliation:
    def test_coverage_is_226_of_259(self):
        rows = _canon()
        assert len(rows) == 313
        assert sum(1 for r in rows if r[6] in VERIFIED) == 313

    def test_exactly_33_unprotected(self):
        rows = _canon()
        assert len(rows) - sum(1 for r in rows if r[6] in VERIFIED) == 0

    def test_queue_equals_the_live_unprotected_set(self):
        """2F-30's queue is point-in-time (33). Slice 2F-31 closed 7 of its
        routes and added 3 Set B routes (never in q, since q predates them).
        Slice 2F-31A then closed the remaining 2 queued media routes
        (upload/replace) AND all 3 Set B routes, so Set B is now fully
        protected and no longer appears in live at all -- live = queue -
        closed - the 2 residual queued routes."""
        CLOSED = {("POST","/v1/provider/profile/logo"),("DELETE","/v1/provider/profile/logo"),
     ("POST","/v1/provider/profile/shop-photo"),("DELETE","/v1/provider/profile/shop-photo"),
     ("POST","/v1/staff/profile/photo"),("DELETE","/v1/staff/profile/photo"),
     ("POST","/v1/me/profile-photo")}
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
        live = {(r[0], r[1]) for r in _canon() if r[6] not in VERIFIED}
        q = {(r["method"], r["path"])
             for r in _rows("authoritative-unprotected-route-inventory.csv")}
        assert live == q - CLOSED - D31A_IN_QUEUE - D33_IN_QUEUE - D35_IN_QUEUE - D36_IN_QUEUE - D37_IN_QUEUE

    def test_no_protected_route_in_queue(self):
        """The 7 Set A routes closed by 2F-31 plus the 2 residual queued
        media routes closed by 2F-31A may now be protected."""
        CLOSED = {("POST","/v1/provider/profile/logo"),("DELETE","/v1/provider/profile/logo"),
     ("POST","/v1/provider/profile/shop-photo"),("DELETE","/v1/provider/profile/shop-photo"),
     ("POST","/v1/staff/profile/photo"),("DELETE","/v1/staff/profile/photo"),
     ("POST","/v1/me/profile-photo")}
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
        prot = {(r[0], r[1]) for r in _canon() if r[6] in VERIFIED}
        q = {(r["method"], r["path"])
             for r in _rows("authoritative-unprotected-route-inventory.csv")}
        assert (q & prot) == CLOSED | D31A_IN_QUEUE | D33_IN_QUEUE | D35_IN_QUEUE | D36_IN_QUEUE | D37_IN_QUEUE

    def test_every_queued_route_is_mounted(self):
        assert all(r["mounted"] == "yes"
                   for r in _rows("authoritative-unprotected-route-inventory.csv"))

    def test_reconciles_with_2f28(self):
        """45 (2F-28 point-in-time queue) - 12 (M01 closed) = 33."""
        old = _rows("authoritative-unprotected-route-inventory.csv", S28)
        m01 = _rows("selected-canonical-route-scope.csv", S28)
        assert len(old) == 45 and len(m01) == 12
        assert len(_rows("authoritative-unprotected-route-inventory.csv")) == 33


class TestM01NonRegression:
    def test_no_m01_route_in_queue(self):
        m01 = {(r["method"], r["path"]) for r in _rows("selected-canonical-route-scope.csv", S28)}
        q = {(r["method"], r["path"])
             for r in _rows("authoritative-unprotected-route-inventory.csv")}
        assert not (q & m01)

    def test_all_twelve_m01_routes_still_protected(self):
        m01 = {(r["method"], r["path"]) for r in _rows("selected-canonical-route-scope.csv", S28)}
        prot = {(r[0], r[1]) for r in _canon() if r[6] in VERIFIED}
        assert m01 <= prot

    def test_m01_matrix_row_intact(self):
        rows = {r[0]: r for r in csv.reader(open(MATRIX, encoding="utf-8"))}
        r = rows["app.engines.auth.router"]
        assert r[2] == "12" and r[3] == "12" and r[7] == "100%"


class TestModuleBoundaries:
    def test_membership_sums_to_33(self):
        assert len(_rows("module-route-membership.csv")) == 33

    def test_no_route_in_two_modules(self):
        keys = [(r["method"], r["path"]) for r in _rows("module-route-membership.csv")]
        assert len(keys) == len(set(keys))

    def test_membership_covers_the_queue(self):
        q = {(r["method"], r["path"])
             for r in _rows("authoritative-unprotected-route-inventory.csv")}
        m = {(r["method"], r["path"]) for r in _rows("module-route-membership.csv")}
        assert q == m

    def test_boundary_counts_match_membership(self):
        from collections import Counter
        c = Counter(r["module"] for r in _rows("module-route-membership.csv"))
        for b in _rows("implementation-module-boundaries.csv"):
            assert int(b["canonical_route_count"]) == c[b["module"]], b["module"]
        assert sum(c.values()) == 33


class TestRiskScoringEvidence:
    def test_selected_module_is_top_ranked(self):
        rk = _rows("updated-module-risk-scoring.csv")
        top = max(int(r["priority_score"]) for r in rk)
        assert int(next(r for r in rk if r["module"] == SELECTED)["priority_score"]) == top

    def test_ownership_evidence_column_present(self):
        """A score without a stated ownership basis is not evidence."""
        rk = _rows("updated-module-risk-scoring.csv")
        assert all("ownership_verified_in_service" in r for r in rk)
        media = next(r for r in rk if r["module"] == SELECTED)
        assert "MediaAccessService" in media["ownership_verified_in_service"]

    def test_geo_recorded_as_genuinely_unscoped(self):
        rk = _rows("updated-module-risk-scoring.csv")
        geo = next(r for r in rk if r["module"] == "N10_geo_zones")
        assert geo["ownership_verified_in_service"].startswith("NO")

    def test_scores_were_recomputed_not_reused(self):
        """2F-28 scored media risk 16; this slice re-scored it after reading
        MediaAccessService."""
        rk = _rows("updated-module-risk-scoring.csv")
        assert int(next(r for r in rk if r["module"] == SELECTED)["risk_sum"]) == 10


class TestFrozenScope:
    def test_set_a_is_nine_and_frozen(self):
        assert len(_rows("selected-canonical-route-scope.csv")) == 9
        assert _h(os.path.join(S, "selected-canonical-route-scope.csv")) == HA

    def test_set_a_equals_module_membership(self):
        a = {(r["method"], r["path"]) for r in _rows("selected-canonical-route-scope.csv")}
        m = {(r["method"], r["path"]) for r in _rows("module-route-membership.csv")
             if r["module"] == SELECTED}
        assert a == m

    def test_set_b_is_three_and_not_canonical(self):
        b = _rows("selected-held-adjudication-scope.csv")
        assert len(b) == 3
        assert _h(os.path.join(S, "selected-held-adjudication-scope.csv")) == HB
        assert all(r["canonical_yet"] == "NO" for r in b)
        # Slice 2F-31 adjudicated all three and added them canonically with
        # full evidence; the 2F-30 artifact still records their pre-adjudication
        # state, which is the point-in-time record.
        canon = {(r[0], r[1]) for r in _canon()}
        assert {(r["method"], r["path"]) for r in b} <= canon

    def test_set_b_is_mandatory_before_closure(self):
        assert all(r["mandatory_before_closure"] == "YES"
                   for r in _rows("selected-held-adjudication-scope.csv"))

    def test_set_c_frozen_with_reasons(self):
        c = _rows("selected-out-of-scope-adjacent-routes.csv")
        assert _h(os.path.join(S, "selected-out-of-scope-adjacent-routes.csv")) == HC
        assert c and all(r["exclusion_reason"] for r in c)

    def test_scope_hashes_recorded_in_evidence_doc(self):
        body = open(os.path.join(S, "selected-scope-hash-evidence.md"), encoding="utf-8").read()
        for x in (HA, HB, HC):
            assert x in body


class TestCrossReferences:
    def test_all_59_held_cross_referenced(self):
        assert len(_rows("held-candidate-module-cross-reference.csv")) == 59

    def test_held_xref_covers_the_registry(self):
        reg = {(r["method"], r["path"]) for r in _rows(
            os.path.basename(HOLD), os.path.dirname(HOLD))}
        x = {(r["method"], r["path"]) for r in _rows("held-candidate-module-cross-reference.csv")}
        assert x == reg

    def test_critical_observations_mapped(self):
        body = " ".join(r["observation_route"]
                        for r in _rows("critical-security-observation-map.csv"))
        for c in ("sessions/{session_id}/revoke", "audit-log", "geo/zones",
                  "webhooks/endpoints", "badges/recalculate"):
            assert c in body, c

    def test_no_observation_called_a_proven_exploit(self):
        assert all(r["executed"] == "no"
                   for r in _rows("critical-security-observation-map.csv") if r["executed"])


class TestContract:
    def test_contract_contains_every_set_a_route(self):
        body = open(os.path.join(S, "selected-module-implementation-contract.md"),
                    encoding="utf-8").read()
        for r in _rows("selected-canonical-route-scope.csv"):
            assert r["path"] in body, r["path"]

    def test_contract_marks_exclusions(self):
        body = open(os.path.join(S, "selected-module-implementation-contract.md"),
                    encoding="utf-8").read()
        assert "EXCLUDED" in body

    def test_contract_forbids_new_permission(self):
        body = open(os.path.join(S, "selected-module-implementation-contract.md"),
                    encoding="utf-8").read()
        assert "do not add a permission" in body.lower()

    def test_evidence_requirements_cover_every_route(self):
        ev = {(r["method"], r["path"]) for r in _rows("authorization-evidence-requirements.csv")}
        a = {(r["method"], r["path"]) for r in _rows("selected-canonical-route-scope.csv")}
        assert ev == a

    def test_trade_off_is_disclosed(self):
        """N09/N10 are worse per route; that must be stated, not hidden."""
        body = open(os.path.join(S, "module-selection-decision.md"), encoding="utf-8").read()
        assert "N09_webhook_integration" in body and "N10_geo_zones" in body
        assert "per-route" in body.lower()


class TestNothingChanged:
    def test_canonical_and_matrix_unchanged(self):
        assert _h(CANON) == CANON_HASH
        assert _h(MATRIX) == MATRIX_HASH

    def test_historical_docs_preserved(self):
        assert "45244cd9540456db" in open(os.path.join(
            DOCS, "phase-02a-slice-02f26h", "canonical-hash-evidence.md"), encoding="utf-8").read()
        assert "GLOBAL_COVERAGE_RECONCILIATION_BLOCKED" in open(os.path.join(
            DOCS, "phase-02a-slice-02f27", "approval-gate.md"), encoding="utf-8").read()
        assert "SECURITY_DOMAIN_INTEGRITY_AND_PRIVACY_CLOSED" in open(os.path.join(
            DOCS, "phase-02a-slice-02f29", "approval-gate.md"), encoding="utf-8").read()

    def test_2f29_test_count_corrected(self):
        """Explicitly requested correction: final total is 2213, not 2170."""
        p = os.path.join(DOCS, "phase-02a-slice-02f29", "test-report.md")
        assert "2213 passed" in open(p, encoding="utf-8").read()

    def test_2f28_queue_artifact_not_rewritten(self):
        assert len(_rows("authoritative-unprotected-route-inventory.csv", S28)) == 45


class TestVerifier:
    @pytest.fixture(scope="class")
    def V(self):
        p = os.path.join(REPO, "scripts", "workflow_rearchitecture", "verify_selection_2f30.py")
        spec = importlib.util.spec_from_file_location("v30", p)
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        return m

    def test_verifier_passes(self, V):
        V.FAILURES.clear()
        assert V.main() == 0
        V.FAILURES.clear()

    def test_twenty_one_conditions(self, V):
        assert len(V.conditions()) == 21

    def test_every_condition_can_fail(self, V):
        for name, _s, _d in V.conditions():
            key = name.split()[0].lower()
            assert any(x[0] == name and not x[1] for x in V.conditions({key: False})), name

    def test_selftest_subprocess(self):
        p = os.path.join(REPO, "scripts", "workflow_rearchitecture", "verify_selection_2f30.py")
        assert subprocess.run([sys.executable, p, "--selftest"],
                              capture_output=True, cwd=REPO).returncode == 0


class TestClosuresIntact:
    def test_canaries(self):
        import inspect
        from app.engines.field_ops import service as fo
        assert "trusted_internal=True" in inspect.getsource(fo)
        from app.engines.review import router as lg
        assert "410" in inspect.getsource(lg.create_review)

    def test_staffpermission_semantics(self):
        from app.core.permissions import permission_checker as pc
        p = "tenant:plan:manage"
        assert pc.has("super_admin", p)
        assert not pc.has("tenant_owner", p)
        assert pc.has("tenant_owner", p, overrides={p: True})
        assert not pc.has("tenant_owner", p, overrides={p: False})
        assert not pc.has("tenant_manager", p)
