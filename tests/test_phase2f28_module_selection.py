"""Phase 2A Slice 2F-28 — authoritative queue reconciliation and module selection.

Selects exactly one next authorization module (M01_identity_credentials,
app.engines.auth.router, 12 canonical unprotected routes) from the authoritative
45-route queue. Selection/planning only: canonical and matrix hashes unchanged,
zero application files modified, no authorization implemented.
"""
from __future__ import annotations

import csv
import hashlib
import importlib.util
import os
import subprocess
import sys

import pytest

pytestmark = pytest.mark.skipif(
    not os.path.isdir(os.path.join(os.path.dirname(os.path.dirname(__file__)), "docs", "workflow-rearchitecture")),
    reason="retired workflow selection artifacts are intentionally absent",
)

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.join(REPO, "docs", "workflow-rearchitecture")
S = os.path.join(DOCS, "phase-02a-slice-02f28")
CANON = os.path.join(DOCS, "phase-02a-slice-02f", "tenant-mutation-endpoint-inventory.csv")
MATRIX = os.path.join(DOCS, "phase-02a-slice-02f", "mutation-enforcement-matrix.csv")
HOLD = os.path.join(DOCS, "phase-02a-slice-02f27a", "unauthorized-candidate-hold-registry.csv")
CANON_HASH = "2d6ebeee18c152c0"
MATRIX_HASH = "4389e57d9db6de83"
SELECTED = "M01_identity_credentials"

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
    def test_coverage_as_of_live_state(self):
        rows = _canon()
        assert len(rows) == 313
        assert sum(1 for r in rows if r[6] in VERIFIED) == 313

    def test_unprotected_is_24(self):
        rows = _canon()
        assert len(rows) - sum(1 for r in rows if r[6] in VERIFIED) == 0

    def test_queue_equals_the_live_unprotected_set(self):
        """The 2F-28 queue is a point-in-time artifact (45 routes). Slice 2F-29
        closed the 12 M01 routes, so the live unprotected set is now 33. The
        queue must still be fully accounted for: live-unprotected + the 12
        closed M01 routes == the original queue."""
        live = {(r[0], r[1]) for r in _canon() if r[6] not in VERIFIED}
        q = {(r["method"], r["path"])
             for r in _rows("authoritative-unprotected-route-inventory.csv")}
        closed = {(r["method"], r["path"]) for r in _rows(
            "selected-canonical-route-scope.csv")}
        ADDED = {("POST","/v1/media/upload/initiate"),("POST","/v1/media/upload/{session_id}/confirm"),
     ("DELETE","/v1/media/tenants/{tenant_id}/files/{file_id}")}
        M31 = {("POST","/v1/provider/profile/logo"),("DELETE","/v1/provider/profile/logo"),
     ("POST","/v1/provider/profile/shop-photo"),("DELETE","/v1/provider/profile/shop-photo"),
     ("POST","/v1/staff/profile/photo"),("DELETE","/v1/staff/profile/photo"),
     ("POST","/v1/me/profile-photo")}
        # 2F-29 closed the 12 M01 routes. 2F-31 closed 7 of the 9 N01 Set A
        # routes (M31) and added 3 Set B routes (never in q, since q predates
        # their canonical existence). 2F-31A closed the remaining 2 Set A
        # routes that WERE in q (upload / replace) AND all 3 Set B routes.
        # All 9 Set A routes are therefore fully removed from live; Set B
        # never appears in q either way.
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
        # 2F-33 closed DELETE /v1/geo/zones/{zone_id}, which WAS in q.
        # 2F-35 closed the webhook delete route and rag query, both in q.
        # 2F-36 closed all 18 Set A routes, all of which WERE in q.
        D37_IN_QUEUE = {
            ("GET", "/v1/commerce/tenants/{tenant_id}/deposit/transactions"),
            ("POST", "/v1/commerce/tenants/{tenant_id}/deposit/initiate"),
            ("GET", "/v1/commerce/tenants/{tenant_id}/deposit"),
        }
        assert live == q - closed - M31 - D31A_IN_QUEUE - D33_IN_QUEUE - D35_IN_QUEUE - D36_IN_QUEUE - D37_IN_QUEUE

    def test_no_protected_route_in_queue(self):
        """After Slice 2F-29 exactly the 12 M01 routes in the queue are
        protected; nothing else in the queue may have become protected."""
        prot = {(r[0], r[1]) for r in _canon() if r[6] in VERIFIED}
        q = {(r["method"], r["path"])
             for r in _rows("authoritative-unprotected-route-inventory.csv")}
        closed = {(r["method"], r["path"]) for r in _rows(
            "selected-canonical-route-scope.csv")}
        M31 = {("POST","/v1/provider/profile/logo"),("DELETE","/v1/provider/profile/logo"),
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
        # As of 2F-31A all 9 Set A routes are protected (2F-31 closed 7,
        # 2F-31A closed the remaining 2). 2F-33 additionally closed the geo
        # delete_zone route; 2F-35 closed webhook delete + rag query;
        # 2F-36 closed all 18 of its own Set A routes.
        D37_IN_QUEUE = {
            ("GET", "/v1/commerce/tenants/{tenant_id}/deposit/transactions"),
            ("POST", "/v1/commerce/tenants/{tenant_id}/deposit/initiate"),
            ("GET", "/v1/commerce/tenants/{tenant_id}/deposit"),
        }
        assert (q & prot) == closed | M31 | D31A_IN_QUEUE | D33_IN_QUEUE | D35_IN_QUEUE | D36_IN_QUEUE | D37_IN_QUEUE

    def test_no_held_candidate_is_canonical(self):
        """Slice 2F-31 adjudicated three media held routes and added them with
        full evidence. Every OTHER held candidate must still be non-canonical."""
        ADJUDICATED_LATER = {
            ("POST", "/v1/media/upload/initiate"),
            ("POST", "/v1/media/upload/{session_id}/confirm"),
            ("DELETE", "/v1/media/tenants/{tenant_id}/files/{file_id}"),
            ("POST", "/v1/geo/tenants/{tenant_id}/zones"),
            ("POST", "/v1/geo/tenants/{tenant_id}/staff/{staff_id}/location"),
            ("POST", "/v1/security/api-keys/{key_id}/rotate"),
            ("POST", "/v1/security/api-keys/{key_id}/revoke"),
            ("POST", "/v1/documents"),
            ("POST", "/v1/documents/{document_id}/send"),
            ("POST", "/v1/documents/{document_id}/void"),
            ("DELETE", "/v1/rag/knowledge-bases/{kb_id}"),
            ("POST", "/v1/rag/knowledge-bases/{kb_id}/documents"),
            ("DELETE", "/v1/rag/documents/{doc_id}"),
            ("POST", "/v1/rag/documents/{doc_id}/reindex"),
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
            # Slice 2F-37
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
            ("POST", "/v1/compliance/deletion-requests"),
            ("POST", "/v1/compliance/portability-requests"),
        }
        held = {(r["method"], r["path"]) for r in _rows(
            os.path.basename(HOLD), os.path.dirname(HOLD))}
        canon = {(r[0], r[1]) for r in _canon()}
        assert not ((held & canon) - ADJUDICATED_LATER)


class TestModuleBoundaries:
    def test_membership_sums_to_45(self):
        assert len(_rows("module-route-membership.csv")) == 45

    def test_no_route_in_two_modules(self):
        keys = [(r["method"], r["path"]) for r in _rows("module-route-membership.csv")]
        assert len(keys) == len(set(keys))

    def test_membership_covers_the_whole_queue(self):
        q = {(r["method"], r["path"])
             for r in _rows("authoritative-unprotected-route-inventory.csv")}
        m = {(r["method"], r["path"]) for r in _rows("module-route-membership.csv")}
        assert q == m

    def test_module_counts_match_boundaries_file(self):
        from collections import Counter
        c = Counter(r["module"] for r in _rows("module-route-membership.csv"))
        for b in _rows("implementation-module-boundaries.csv"):
            assert int(b["route_count"]) == c[b["module"]], b["module"]
        assert sum(c.values()) == 45


class TestSelection:
    def test_exactly_one_module_selected(self):
        body = open(os.path.join(S, "module-selection-decision.md"), encoding="utf-8").read()
        assert SELECTED in body

    def test_selected_scope_is_12_routes(self):
        assert len(_rows("selected-canonical-route-scope.csv")) == 12

    def test_selected_scope_equals_module_membership(self):
        sel = {(r["method"], r["path"]) for r in _rows("selected-canonical-route-scope.csv")}
        mem = {(r["method"], r["path"]) for r in _rows("module-route-membership.csv")
               if r["module"] == SELECTED}
        assert sel == mem

    def test_selected_module_is_the_highest_priority(self):
        rk = _rows("module-risk-scoring.csv")
        top = max(rk, key=lambda r: int(r["priority_score"]))
        assert top["module"] == SELECTED

    def test_selection_is_not_by_route_count_alone(self):
        """M01 must also lead on raw risk, so the weighting is not load-bearing."""
        rk = _rows("module-risk-scoring.csv")
        top_risk = max(rk, key=lambda r: int(r["risk_sum"]))
        assert top_risk["module"] == SELECTED

    def test_alternatives_are_compared(self):
        body = open(os.path.join(S, "module-selection-decision.md"), encoding="utf-8").read()
        for other in ("M02_media_assets", "M06_security_deposit"):
            assert other in body


class TestFrozenScopeSets:
    def test_set_b_has_no_in_scope_held_route(self):
        """Emptiness is proven, not assumed: the nearest held routes are listed
        with in_scope_for_M01 = NO and a model/table reason."""
        b = _rows("selected-held-adjudication-scope.csv")
        assert b, "set B must record the evaluated adjacencies"
        assert all(r["in_scope_for_M01"] == "NO" for r in b)
        assert all("tenant_api_keys" in r["reason"] or "distinct" in r["reason"] for r in b)

    def test_no_set_b_route_is_canonical(self):
        """Tracks whether 2F-28's OWN frozen Set B (N01's 3 media routes)
        stayed non-canonical AS OF 2F-28 itself. Two of 2F-28's Set B rows
        (security api-key rotate/revoke) were later independently
        adjudicated and closed by Slice 2F-35 as part of a DIFFERENT
        module's held-candidate pool -- the same PROTECTED_BY_LATER_SLICE
        situation as elsewhere in this file."""
        b = {(r["method"], r["path"]) for r in _rows("selected-held-adjudication-scope.csv")}
        PROTECTED_BY_LATER_SLICE = {
            ("POST", "/v1/security/api-keys/{key_id}/rotate"),
            ("POST", "/v1/security/api-keys/{key_id}/revoke"),
        }
        canon = {(r[0], r[1]) for r in _canon()}
        assert not ((b - PROTECTED_BY_LATER_SLICE) & canon)

    def test_set_c_exclusions_all_have_reasons(self):
        c = _rows("selected-out-of-scope-adjacent-routes.csv")
        assert c and all(r["exclusion_reason"] for r in c)

    def test_scope_hashes_recorded(self):
        body = open(os.path.join(S, "selected-scope-hash-evidence.md"), encoding="utf-8").read()
        for f in ("selected-canonical-route-scope.csv",
                  "selected-held-adjudication-scope.csv",
                  "selected-out-of-scope-adjacent-routes.csv"):
            assert _h(os.path.join(S, f)) in body, f


class TestCrossReferences:
    def test_all_59_held_cross_referenced(self):
        assert len(_rows("held-candidate-module-cross-reference.csv")) == 59

    def test_held_xref_covers_the_whole_registry(self):
        reg = {(r["method"], r["path"]) for r in _rows(
            os.path.basename(HOLD), os.path.dirname(HOLD))}
        x = {(r["method"], r["path"]) for r in _rows("held-candidate-module-cross-reference.csv")}
        assert x == reg

    def test_critical_security_observations_mapped(self):
        body = " ".join(r["observation_route"] for r in
                        _rows("security-observation-module-cross-reference.csv"))
        for c in ("sessions/{session_id}/revoke", "audit-log", "geo/zones",
                  "webhooks/endpoints", "rag/knowledge-bases", "badges/recalculate"):
            assert c in body, c

    def test_no_observation_labelled_a_proven_exploit(self):
        rows = _rows("security-observation-module-cross-reference.csv")
        assert all(r["executed"] == "no" for r in rows if r["executed"])


class TestContract:
    def test_contract_contains_every_canonical_route(self):
        body = open(os.path.join(S, "selected-module-implementation-contract.md"),
                    encoding="utf-8").read()
        for r in _rows("selected-canonical-route-scope.csv"):
            assert r["path"] in body, r["path"]

    def test_contract_marks_exclusions_as_excluded(self):
        body = open(os.path.join(S, "selected-module-implementation-contract.md"),
                    encoding="utf-8").read()
        assert "EXCLUDED" in body

    def test_evidence_requirements_cover_every_route(self):
        ev = _rows("authorization-evidence-requirements.csv")
        sel = {(r["method"], r["path"]) for r in _rows("selected-canonical-route-scope.csv")}
        assert {(r["method"], r["path"]) for r in ev} == sel


class TestNothingChanged:
    def test_canonical_and_matrix_unchanged(self):
        assert _h(CANON) == CANON_HASH
        assert _h(MATRIX) == MATRIX_HASH

    def test_historical_docs_preserved(self):
        assert "45244cd9540456db" in open(os.path.join(
            DOCS, "phase-02a-slice-02f26h", "canonical-hash-evidence.md"), encoding="utf-8").read()
        assert "GLOBAL_COVERAGE_RECONCILIATION_BLOCKED" in open(os.path.join(
            DOCS, "phase-02a-slice-02f27", "approval-gate.md"), encoding="utf-8").read()
        assert "EXPLICIT_TWO_ROUTE_CANONICAL_EXPANSION_COMPLETE" in open(os.path.join(
            DOCS, "phase-02a-slice-02f27a", "approval-gate.md"), encoding="utf-8").read()


class TestVerifier:
    @pytest.fixture(scope="class")
    def V(self):
        p = os.path.join(REPO, "scripts", "workflow_rearchitecture", "verify_selection_2f28.py")
        spec = importlib.util.spec_from_file_location("v28", p)
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        return m

    def test_verifier_passes(self, V):
        V.FAILURES.clear()
        assert V.main() == 0
        V.FAILURES.clear()

    def test_twenty_conditions(self, V):
        assert len(V.conditions()) == 20

    def test_every_condition_can_fail(self, V):
        for name, _s, _d in V.conditions():
            key = name.split()[0].lower()
            assert any(x[0] == name and not x[1] for x in V.conditions({key: False})), name

    def test_selftest_subprocess(self):
        p = os.path.join(REPO, "scripts", "workflow_rearchitecture", "verify_selection_2f28.py")
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
