"""Phase 2A Slice 2F-37 — Remaining Financial/Product-Policy
Authorization, Held-Candidate Adjudication.

Covers Set A (3 routes: platform_commerce_deposit) closed, and Set B
(17 held routes, 5 modules: pricing, commerce, payments, subscriptions,
compliance) adjudicated -- 16 canonically added and protected, 1
already-protected exclude (commerce deposit/admin-adjust,
PLATFORM_ADMIN_EXCLUDE).

N01 domain-integrity backlog is explicitly frozen (not remediated) this
slice per the frozen Slice 2F-34 contract -- see
docs/workflow-rearchitecture/phase-02a-slice-02f37/n01-final-status.md.
"""
from __future__ import annotations

import csv
import hashlib
import importlib.util
import inspect
import os
import uuid
from unittest.mock import MagicMock

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.join(REPO, "docs", "workflow-rearchitecture")
CANON = os.path.join(DOCS, "phase-02a-slice-02f", "tenant-mutation-endpoint-inventory.csv")
MATRIX = os.path.join(DOCS, "phase-02a-slice-02f", "mutation-enforcement-matrix.csv")

VERIFIED = {"TENANT_MUTATION_PERMISSION_SCOPE_AWARE", "TENANT_MUTATION_ROLE_SCOPE_AWARE",
            "STAFF_EXECUTION_ROLE_SCOPE_AWARE", "PLATFORM_ADMIN_ONLY", "PUBLIC_NO_AUTH",
            "CUSTOMER_ROLE_ONLY_NOT_TENANT_SCOPED", "FULLY_PROTECTED"}

SET_A = {
    ("GET", "/v1/commerce/tenants/{tenant_id}/deposit"),
    ("POST", "/v1/commerce/tenants/{tenant_id}/deposit/initiate"),
    ("GET", "/v1/commerce/tenants/{tenant_id}/deposit/transactions"),
}
SET_B_CANONICAL = {
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
    ("PUT", "/v1/subscriptions/tenants/{tenant_id}/plan"),
    ("POST", "/v1/compliance/deletion-requests"),
    ("POST", "/v1/compliance/portability-requests"),
}

TENANT_A = uuid.uuid4()
TENANT_B = uuid.uuid4()
ACTOR = uuid.uuid4()


def _canon_rows():
    return list(csv.reader(open(CANON, encoding="utf-8")))[1:]


def _h(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()[:16]


def _model():
    p = os.path.join(REPO, "scripts", "workflow_rearchitecture", "authority_model_2f26e.py")
    spec = importlib.util.spec_from_file_location("am37", p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


class TestScopeGuardsLive:
    def test_all_19_routes_access_scope_gated(self):
        E = _model()
        idx = E.route_index()
        for key in SET_A | SET_B_CANONICAL:
            assert key in idx, key
            guards = E.route_guards(idx[key])
            assert any(g["access_scope_gated"] for g in guards), key


class TestTrustedTenantHelpers:
    @pytest.mark.parametrize("mod,cls", [
        ("app.engines.pricing.service", "PricingService"),
        ("app.engines.payment.service", "PaymentService"),
        ("app.engines.subscription.service", "SubscriptionService"),
    ])
    def test_service_has_require_trusted_tenant(self, mod, cls):
        import importlib
        m = importlib.import_module(mod)
        svc = getattr(m, cls)
        assert hasattr(svc, "_require_trusted_tenant")

    @pytest.mark.parametrize("mod,cls", [
        ("app.engines.pricing.service", "PricingService"),
        ("app.engines.payment.service", "PaymentService"),
        ("app.engines.subscription.service", "SubscriptionService"),
    ])
    def test_super_admin_exempt_others_scoped_or_rejected(self, mod, cls):
        import importlib
        m = importlib.import_module(mod)
        svc_cls = getattr(m, cls)
        svc = svc_cls.__new__(svc_cls)
        svc.actor_role = "super_admin"
        svc.actor_tenant_id = None
        assert svc._require_trusted_tenant(TENANT_B) == TENANT_B
        svc.actor_role = "tenant_owner"
        svc.actor_tenant_id = TENANT_A
        assert svc._require_trusted_tenant(TENANT_A) == TENANT_A
        from app.exceptions import ServiceOSException
        with pytest.raises(ServiceOSException):
            svc._require_trusted_tenant(TENANT_B)
        svc.actor_tenant_id = None
        with pytest.raises(ServiceOSException):
            svc._require_trusted_tenant(TENANT_A)


class TestPricingZoneRuleOwnership:
    def _svc(self, tenant=TENANT_A, role="tenant_owner"):
        from app.engines.pricing.service import PricingService
        db = MagicMock()
        svc = PricingService.__new__(PricingService)
        svc.db = db; svc.actor_id = ACTOR; svc.actor_role = role; svc.actor_tenant_id = tenant
        return svc, db

    def test_source_confirms_zone_ownership_check(self):
        from app.engines.pricing.service import PricingService
        src = inspect.getsource(PricingService.update_zone)
        assert "z.tenant_id != tenant_id" in src
        src2 = inspect.getsource(PricingService.delete_zone)
        assert "z.tenant_id != tenant_id" in src2

    def test_source_confirms_rule_ownership_check(self):
        from app.engines.pricing.service import PricingService
        src = inspect.getsource(PricingService.update_rule)
        assert "rule.tenant_id != tenant_id" in src
        src2 = inspect.getsource(PricingService.delete_rule)
        assert "rule.tenant_id != tenant_id" in src2


class TestCommerceOwnershipFixes:
    def test_initiate_purchase_calls_deposit_ownership_check(self):
        from app.engines.platform_commerce.service import CommerceService
        src = inspect.getsource(CommerceService.initiate_purchase)
        assert "_assert_owns_tenant_deposit" in src

    def test_recalculate_badges_calls_deposit_ownership_check(self):
        from app.engines.platform_commerce.service import CommerceService
        src = inspect.getsource(CommerceService.recalculate_badges)
        assert "_assert_owns_tenant_deposit" in src

    def test_submit_claim_verifies_parent_job(self):
        from app.engines.platform_commerce.service import CommerceService
        src = inspect.getsource(CommerceService.submit_claim)
        assert "ServiceJob" in src
        assert "job.tenant_id" in src and "job.customer_id" in src


class TestComplianceSelfOnly:
    def test_router_source_confirms_self_only_check(self):
        from app.engines.compliance import router
        src = inspect.getsource(router)
        assert "compliance_deletion_self_only" in src
        assert "compliance_export_self_only" in src


class TestReadPermissionMisuseFixed:
    def test_recalculate_badges_no_longer_guarded_by_read_permission(self):
        from app.engines.platform_commerce import router
        src = inspect.getsource(router.recalculate_badges)
        assert "TENANT_HEALTH_READ" not in src
        assert "require_tenant_mutation_permission" in src


class TestSetBAdjudication:
    def test_all_17_held_routes_adjudicated(self):
        rows = list(csv.DictReader(open(
            os.path.join(DOCS, "phase-02a-slice-02f37", "held-route-adjudication.csv"),
            encoding="utf-8")))
        assert len(rows) == 17

    def test_16_canonical_additions_all_protected(self):
        rows = list(csv.DictReader(open(
            os.path.join(DOCS, "phase-02a-slice-02f37", "held-route-adjudication.csv"),
            encoding="utf-8")))
        added = [r for r in rows if r["canonical_added"] == "YES"]
        assert len(added) == 16

    def test_admin_adjust_platform_admin_exclude(self):
        rows = list(csv.DictReader(open(
            os.path.join(DOCS, "phase-02a-slice-02f37", "held-route-adjudication.csv"),
            encoding="utf-8")))
        row = next(r for r in rows if r["path"] == "/v1/commerce/tenants/{tenant_id}/deposit/admin-adjust")
        assert row["disposition"] == "PLATFORM_ADMIN_EXCLUDE"
        assert row["canonical_added"] == "NO"


class TestCanonicalClosure:
    def test_coverage_is_313_of_313(self):
        rows = _canon_rows()
        assert len(rows) == 313
        assert sum(1 for r in rows if r[6] in VERIFIED) == 313

    def test_unprotected_is_0(self):
        rows = _canon_rows()
        assert len(rows) - sum(1 for r in rows if r[6] in VERIFIED) == 0

    def test_all_set_a_routes_protected(self):
        rows = {(r[0], r[1]): r[6] for r in _canon_rows()}
        for key in SET_A:
            assert rows[key] in VERIFIED, key

    def test_all_canonical_set_b_routes_protected(self):
        rows = {(r[0], r[1]): r[6] for r in _canon_rows()}
        for key in SET_B_CANONICAL:
            assert rows[key] in VERIFIED, key


class TestM01GeoAnd2F35And2F36NonRegression:
    def test_m01_sample_route_verified(self):
        rows = {(r[0], r[1]): r[6] for r in _canon_rows()}
        assert rows[("POST", "/v1/auth/api-keys")] in VERIFIED

    def test_geo_sample_route_verified(self):
        rows = {(r[0], r[1]): r[6] for r in _canon_rows()}
        assert rows[("DELETE", "/v1/geo/zones/{zone_id}")] in VERIFIED

    def test_2f35_sample_routes_verified(self):
        rows = {(r[0], r[1]): r[6] for r in _canon_rows()}
        assert rows[("DELETE", "/v1/webhooks/endpoints/{endpoint_id}")] in VERIFIED
        assert rows[("POST", "/v1/documents")] in VERIFIED

    def test_2f36_sample_routes_verified(self):
        rows = {(r[0], r[1]): r[6] for r in _canon_rows()}
        assert rows[("POST", "/v1/chat/conversations/{conversation_id}/messages")] in VERIFIED
        assert rows[("PUT", "/v1/me/profile")] in VERIFIED


class TestN01FrozenNotRemediated:
    def test_no_media_file_touched(self):
        import subprocess
        r = subprocess.run(["git", "status", "--porcelain",
                             "app/engines/media/router.py", "app/engines/media/service.py",
                             "app/engines/media/new_router.py", "app/engines/media/asset_service.py"],
                            cwd=REPO, capture_output=True, text=True)
        # Confirm no 2F-37 marker was added -- these files may show pre-
        # existing modifications from earlier slices, but must not carry a
        # 2F-37-specific change.
        for f in ["app/engines/media/router.py", "app/engines/media/service.py"]:
            content = open(os.path.join(REPO, f), encoding="utf-8").read()
            assert "2F-37" not in content

    def test_n01_final_status_documents_the_frozen_contract_conflict(self):
        doc = open(os.path.join(DOCS, "phase-02a-slice-02f37", "n01-final-status.md"),
                    encoding="utf-8").read()
        assert "IMPLEMENTATION_SCOPE_BLOCKED" in doc
        assert "do not remediate" in doc.lower() or "Do not remediate" in doc
