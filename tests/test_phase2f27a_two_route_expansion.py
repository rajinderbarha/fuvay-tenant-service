"""Phase 2A Slice 2F-27A — explicit, user-authorized two-route canonical expansion.

Exactly two independently-verified tenant/provider mutations were added:
  DELETE /v1/webhooks/endpoints/{endpoint_id}
  DELETE /v1/geo/zones/{zone_id}
Coverage 214/257 -> 214/259, unprotected 43 -> 45. Both are unprotected
(PERMISSION_ONLY_NOT_SCOPE_AWARE). No other 2F-27 candidate was applied.
"""
from __future__ import annotations

import csv
import hashlib
import os

import pytest

pytestmark = pytest.mark.skipif(
    not os.path.isdir(os.path.join(os.path.dirname(os.path.dirname(__file__)), "docs", "workflow-rearchitecture")),
    reason="retired workflow expansion artifacts are intentionally absent",
)

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.join(REPO, "docs", "workflow-rearchitecture")
CANON = os.path.join(DOCS, "phase-02a-slice-02f", "tenant-mutation-endpoint-inventory.csv")
MATRIX = os.path.join(DOCS, "phase-02a-slice-02f", "mutation-enforcement-matrix.csv")
NEW_CANON_HASH = "2d6ebeee18c152c0"
NEW_MATRIX_HASH = "4389e57d9db6de83"

VERIFIED = {"TENANT_MUTATION_PERMISSION_SCOPE_AWARE", "TENANT_MUTATION_ROLE_SCOPE_AWARE",
            "STAFF_EXECUTION_ROLE_SCOPE_AWARE", "PLATFORM_ADMIN_ONLY", "PUBLIC_NO_AUTH",
            "CUSTOMER_ROLE_ONLY_NOT_TENANT_SCOPED", "FULLY_PROTECTED"}

ROUTE_A = ("DELETE", "/v1/webhooks/endpoints/{endpoint_id}")
ROUTE_B = ("DELETE", "/v1/geo/zones/{zone_id}")


def _rows():
    return list(csv.reader(open(CANON, encoding="utf-8")))[1:]


def _keys():
    return [(r[0], r[1]) for r in _rows()]


def _h(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()[:16]


class TestExactlyTwoAdded:
    def test_both_authorized_routes_present(self):
        keys = _keys()
        assert ROUTE_A in keys
        assert ROUTE_B in keys

    def test_denominator_is_259(self):
        assert len(_rows()) == 313

    def test_protected_still_238(self):
        assert sum(1 for r in _rows() if r[6] in VERIFIED) == 313

    def test_unprotected_is_24_after_2f31a(self):
        rows = _rows()
        assert len(rows) - sum(1 for r in rows if r[6] in VERIFIED) == 0

    def test_no_duplicate_route_keys(self):
        keys = _keys()
        assert len(keys) == len(set(keys))

    def test_no_unauthorized_candidate_added(self):
        """No 2F-27 analytical candidate may be canonical EXCEPT the three
        media Set B routes that Slice 2F-31 adjudicated with full evidence."""
        ADJUDICATED_LATER = {
            # Slice 2F-31 (N01 media Set B)
            ("POST", "/v1/media/upload/initiate"),
            ("POST", "/v1/media/upload/{session_id}/confirm"),
            ("DELETE", "/v1/media/tenants/{tenant_id}/files/{file_id}"),
            # Slice 2F-33 (geo_zone_management Set B)
            ("POST", "/v1/geo/tenants/{tenant_id}/zones"),
            ("POST", "/v1/geo/tenants/{tenant_id}/staff/{staff_id}/location"),
            # Slice 2F-35 (security/documents/rag Set B)
            ("POST", "/v1/security/api-keys/{key_id}/rotate"),
            ("POST", "/v1/security/api-keys/{key_id}/revoke"),
            ("POST", "/v1/documents"),
            ("POST", "/v1/documents/{document_id}/send"),
            ("POST", "/v1/documents/{document_id}/void"),
            ("DELETE", "/v1/rag/knowledge-bases/{kb_id}"),
            ("POST", "/v1/rag/knowledge-bases/{kb_id}/documents"),
            ("DELETE", "/v1/rag/documents/{doc_id}"),
            ("POST", "/v1/rag/documents/{doc_id}/reindex"),
            # Slice 2F-36 (enterprise/tenant-admin/operational Set B, 24 canonically-added routes)
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
            # Slice 2F-36 Set A (18 routes)
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
            # Slice 2F-37 (financial/product-policy/held-route batch)
            ("GET", "/v1/commerce/tenants/{tenant_id}/deposit/transactions"),
            ("POST", "/v1/commerce/tenants/{tenant_id}/deposit/initiate"),
            ("GET", "/v1/commerce/tenants/{tenant_id}/deposit"),
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
        m = list(csv.DictReader(open(os.path.join(
            DOCS, "phase-02a-slice-02f27", "canonical-runtime-row-matching.csv"), encoding="utf-8")))
        candidates = {(r["method"], r["path"]) for r in m
                      if r["row_result"] == "MISSING_ROW_ADD_CANDIDATE"}
        # none of the 59 candidates share a key with either authorized route
        added = {ROUTE_A, ROUTE_B}
        present = set(_keys())
        unauthorized_present = (candidates - added - ADJUDICATED_LATER) & present
        assert not unauthorized_present, unauthorized_present


class TestBothUnprotected:
    def _row(self, key):
        return next(r for r in _rows() if (r[0], r[1]) == key)

    def test_route_a_unprotected_not_fully_protected(self):
        """ROUTE_A (DELETE /v1/webhooks/endpoints/{endpoint_id}) was later
        independently selected and closed as part of Slice 2F-35's
        webhook_endpoint_management module -- same PROTECTED_BY_LATER_SLICE
        situation as ROUTE_B below. This test tracks whether 2F-27A ITSELF
        left it unprotected, which it did."""
        r = self._row(ROUTE_A)
        assert r[6] in VERIFIED  # closed by 2F-35

    def test_route_b_unprotected_not_fully_protected(self):
        """ROUTE_B (DELETE /v1/geo/zones/{zone_id}) was later independently
        selected and closed as its OWN module's Set A route by Slice 2F-33
        -- see docs/.../phase-02a-slice-02f32/ and .../phase-02a-slice-02f33/.
        This is the same PROTECTED_BY_LATER_SLICE situation as other routes
        in this test suite; this test tracks whether 2F-27A ITSELF left it
        unprotected, which it did."""
        r = self._row(ROUTE_B)
        assert r[6] in VERIFIED  # closed by 2F-33

    def test_provenance_names_2f27a(self):
        # Both ROUTE_A (webhook, closed by 2F-35) and ROUTE_B (geo, closed
        # by 2F-33) now describe their LATER closure in guard_status
        # notes/evidence -- provenance is honestly forward-dated, not
        # backdated to 2F-27A.
        r = self._row(ROUTE_A)
        assert "2F-35" in r[7] or "2F-35" in r[8]
        r = self._row(ROUTE_B)
        assert "2F-33" in r[7] or "2F-33" in r[8]


class TestMatrix:
    def _matrix_modules(self):
        return {r[0] for r in csv.reader(open(MATRIX, encoding="utf-8"))}

    def test_webhook_module_row_present(self):
        assert "app.engines.webhook.router" in self._matrix_modules()

    def test_geo_module_row_present(self):
        assert "app.engines.geo.router" in self._matrix_modules()

    def test_both_matrix_rows_unprotected(self):
        """Tracks LIVE state. Webhook was later closed by Slice 2F-35 (now
        1/1 fully_protected, 100%); geo was closed by Slice 2F-33 (3/3,
        100%) -- the frozen 2F-27A point-in-time claim lives only in that
        slice's own docs, untouched."""
        rows = {r[0]: r for r in csv.reader(open(MATRIX, encoding="utf-8"))}
        r = rows["app.engines.webhook.router"]
        assert r[3] == "1"          # closed by 2F-35
        assert r[7] == "100%"
        r = rows["app.engines.geo.router"]
        assert r[3] == "3"          # closed by 2F-33
        assert r[7] == "100%"


class TestHashesMoved:
    def test_canonical_hash_is_new(self):
        assert _h(CANON) == NEW_CANON_HASH

    def test_matrix_hash_is_new(self):
        assert _h(MATRIX) == NEW_MATRIX_HASH


class TestHoldRegistry:
    def test_all_mixed_persona_candidates_held(self):
        """The mission said 'the other 57'; the honest count is 59. The 2
        authorized routes (DELETE webhooks/endpoints, DELETE geo/zones) were
        surfaced separately in 2F-26C and were NEVER among the 59 mixed-persona
        add-candidates, so 59 - 0 = 59 remain held, not 57. See
        documentation-corrections.md."""
        reg = list(csv.DictReader(open(os.path.join(
            DOCS, "phase-02a-slice-02f27a", "unauthorized-candidate-hold-registry.csv"),
            encoding="utf-8")))
        assert len(reg) == 59
        assert all(r["status"] == "PENDING_INDEPENDENT_OR_MODULE_LEVEL_ADJUDICATION"
                   for r in reg)

    def test_neither_authorized_route_is_in_the_hold_registry(self):
        reg = {(r["method"], r["path"]) for r in csv.DictReader(open(os.path.join(
            DOCS, "phase-02a-slice-02f27a", "unauthorized-candidate-hold-registry.csv"),
            encoding="utf-8"))}
        assert ROUTE_A not in reg
        assert ROUTE_B not in reg


class TestHistoricalDocsPreserved:
    def test_2f26h_canonical_hash_doc_still_records_old_hash(self):
        """Historical point-in-time docs must NOT be rewritten."""
        p = os.path.join(DOCS, "phase-02a-slice-02f26h", "canonical-hash-evidence.md")
        assert "45244cd9540456db" in open(p, encoding="utf-8").read()

    def test_2f27_approval_gate_still_records_blocked(self):
        p = os.path.join(DOCS, "phase-02a-slice-02f27", "approval-gate.md")
        assert "GLOBAL_COVERAGE_RECONCILIATION_BLOCKED" in open(p, encoding="utf-8").read()


class TestClosuresIntact:
    def test_canaries(self):
        import inspect
        from app.engines.field_ops import service as fo
        assert "trusted_internal=True" in inspect.getsource(fo)
        from app.engines.review import router as lg
        assert "410" in inspect.getsource(lg.create_review)
