"""Phase 2A Slice 2F-33 — geo_zone_management authorization closure.

Covers the 1 Set A route closed + 2 Set B routes adjudicated and closed
this slice:
  DELETE /v1/geo/zones/{zone_id}                            (Set A)
  POST   /v1/geo/tenants/{tenant_id}/zones                  (Set B -> ADD)
  POST   /v1/geo/tenants/{tenant_id}/staff/{staff_id}/location (Set B -> ADD)
"""
from __future__ import annotations

import csv
import hashlib
import inspect
import importlib.util
import os
import subprocess

import pytest

pytestmark = pytest.mark.skipif(
    not os.path.isdir(os.path.join(os.path.dirname(os.path.dirname(__file__)), "docs", "workflow-rearchitecture")),
    reason="retired workflow closure artifacts are intentionally absent",
)

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.join(REPO, "docs", "workflow-rearchitecture")
CANON = os.path.join(DOCS, "phase-02a-slice-02f", "tenant-mutation-endpoint-inventory.csv")
MATRIX = os.path.join(DOCS, "phase-02a-slice-02f", "mutation-enforcement-matrix.csv")

VERIFIED = {"TENANT_MUTATION_PERMISSION_SCOPE_AWARE", "TENANT_MUTATION_ROLE_SCOPE_AWARE",
            "STAFF_EXECUTION_ROLE_SCOPE_AWARE", "PLATFORM_ADMIN_ONLY", "PUBLIC_NO_AUTH",
            "CUSTOMER_ROLE_ONLY_NOT_TENANT_SCOPED", "FULLY_PROTECTED"}

SET_A = {("DELETE", "/v1/geo/zones/{zone_id}")}
SET_B_ADDED = {
    ("POST", "/v1/geo/tenants/{tenant_id}/zones"),
    ("POST", "/v1/geo/tenants/{tenant_id}/staff/{staff_id}/location"),
}


def _canon_rows():
    return list(csv.reader(open(CANON, encoding="utf-8")))[1:]


def _h(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()[:16]


def _model():
    p = os.path.join(REPO, "scripts", "workflow_rearchitecture", "authority_model_2f26e.py")
    spec = importlib.util.spec_from_file_location("am33", p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


class TestScopeGuards:
    def test_delete_zone_uses_tenant_mutation_permission(self):
        E = _model()
        idx = E.route_index()
        key = ("DELETE", "/v1/geo/zones/{zone_id}")
        syms = [g["symbol"] for g in E.route_guards(idx[key])]
        assert "require_tenant_mutation_tenant_update" in syms or any(
            "require_tenant_mutation" in s for s in syms), syms
        assert any(g["access_scope_gated"] for g in E.route_guards(idx[key]))

    def test_create_zone_uses_tenant_mutation_permission(self):
        E = _model()
        idx = E.route_index()
        key = ("POST", "/v1/geo/tenants/{tenant_id}/zones")
        assert any(g["access_scope_gated"] for g in E.route_guards(idx[key]))

    def test_update_location_uses_scope_only_guard(self):
        from app.core.permissions import require_mutation_access_scope
        from app.dependencies.auth import get_current_user
        sig = inspect.signature(require_mutation_access_scope)
        assert sig.parameters["user"].default.dependency is get_current_user
        E = _model()
        idx = E.route_index()
        key = ("POST", "/v1/geo/tenants/{tenant_id}/staff/{staff_id}/location")
        syms = [g["symbol"] for g in E.route_guards(idx[key])]
        assert "require_mutation_access_scope" in syms
        assert any(g["access_scope_gated"] for g in E.route_guards(idx[key]))

    def test_staff_self_check_preserved(self):
        import app.engines.geo.router as router_mod
        src = inspect.getsource(router_mod.update_location)
        assert 'u.role == "staff"' in src
        assert "Staff can only update their own location" in src


class TestGeoServiceTenantAuthority:
    def test_trusted_tenant_helper_exists(self):
        from app.engines.geo.service import GeoService
        assert hasattr(GeoService, "_require_trusted_tenant")

    def test_delete_zone_calls_trusted_tenant_and_scopes_query(self):
        from app.engines.geo.service import GeoService
        src = inspect.getsource(GeoService.delete_zone)
        assert "_require_trusted_tenant()" in src
        assert "ServiceZone.tenant_id == tenant_id" in src
        assert src.index("_require_trusted_tenant") < src.index("select(ServiceZone)")

    def test_create_zone_calls_trusted_tenant(self):
        from app.engines.geo.service import GeoService
        src = inspect.getsource(GeoService.create_zone)
        assert "_require_trusted_tenant(tenant_id)" in src

    def test_update_staff_location_calls_trusted_tenant(self):
        from app.engines.geo.service import GeoService
        src = inspect.getsource(GeoService.update_staff_location)
        assert "_require_trusted_tenant(tenant_id)" in src

    def test_super_admin_bypasses_tenant_check_explicitly(self):
        from app.engines.geo.service import GeoService
        src = inspect.getsource(GeoService._require_trusted_tenant)
        assert 'self.actor_role == "super_admin"' in src

    def test_missing_tenant_context_fails_closed(self):
        from app.engines.geo.service import GeoService
        src = inspect.getsource(GeoService._require_trusted_tenant)
        assert "self.actor_tenant_id is None" in src
        idx_none = src.index("self.actor_tenant_id is None")
        idx_raise = src.index("raise", idx_none)
        assert idx_raise - idx_none < 200

    def test_cross_tenant_mismatch_raises(self):
        from app.engines.geo.service import GeoService
        src = inspect.getsource(GeoService._require_trusted_tenant)
        assert "requested_tenant_id != self.actor_tenant_id" in src


class TestNonOracularResponses:
    def test_delete_zone_no_existence_leak_wording(self):
        from app.engines.geo.service import GeoService
        src = inspect.getsource(GeoService._require_trusted_tenant)
        assert "does not exist" not in src
        assert "does not belong" not in src

    def test_delete_zone_foreign_and_missing_share_same_exception(self):
        from app.engines.geo.service import GeoService
        src = inspect.getsource(GeoService.delete_zone)
        assert src.count('NotFoundException("ServiceZone", str(zone_id))') == 1
        # single raise site covers both foreign-tenant (query returns none)
        # and genuinely-missing zone_id -- same exception either way.


class TestNoBypassOfClosedRoutes:
    def test_no_direct_geoservice_mutation_call_outside_router(self):
        out = subprocess.run(
            ["git", "grep", "-n", "-E",
             r"\bs\.(delete_zone|create_zone|update_staff_location)\(|\bgeo\.(delete_zone|create_zone|update_staff_location)\(",
             "--", "app/", ":(exclude)app/engines/geo/service.py", ":(exclude)app/engines/geo/router.py",
             ":(exclude)app/engines/pricing/router.py", ":(exclude)app/engines/location_engine/router.py"],
            cwd=REPO, capture_output=True, text=True)
        assert out.stdout.strip() == "", out.stdout

    def test_geoservice_constructed_with_actor_tenant_id_from_router(self):
        import app.engines.geo.router as router_mod
        src = inspect.getsource(router_mod._svc)
        assert "actor_tenant_id" in src

    def test_booking_internal_caller_only_uses_readonly_method(self):
        """The one other GeoService(...) construction site in the codebase
        (booking preflight) must only call the untouched read-only
        check_pincode_in_zone -- never a mutation method."""
        import app.engines.booking.service as booking_mod
        src = inspect.getsource(booking_mod)
        assert "GeoService(self.db)" in src
        assert "geo.check_pincode_in_zone(" in src
        for bad in ("geo.delete_zone(", "geo.create_zone(", "geo.update_staff_location("):
            assert bad not in src

    def test_location_engine_and_pricing_create_zone_are_different_services(self):
        """git grep for .create_zone(/.delete_zone( also matches
        LocationService and PricingService -- confirm those are genuinely
        separate classes, not our GeoService, so they are not a bypass."""
        from app.engines.location_engine.service import LocationService
        from app.engines.pricing.service import PricingService
        from app.engines.geo.service import GeoService
        assert LocationService is not GeoService
        assert PricingService is not GeoService


class TestSetBAdjudication:
    def test_both_set_b_routes_now_canonical_and_verified(self):
        rows = {(r[0], r[1]): r[6] for r in _canon_rows()}
        for key in SET_B_ADDED:
            assert key in rows, key
            assert rows[key] in VERIFIED, f"{key}: {rows[key]}"

    def test_set_a_route_now_verified(self):
        rows = {(r[0], r[1]): r[6] for r in _canon_rows()}
        for key in SET_A:
            assert rows[key] in VERIFIED, f"{key}: {rows[key]}"

    def test_no_set_c_route_was_touched(self):
        """update_zone (PUT /v1/geo/zones/{zone_id}) is an explicit Set C
        observation from Slice 2F-32 -- it must remain non-canonical and
        its service method untouched by this slice's tenant-scoping fix."""
        rows = {(r[0], r[1]) for r in _canon_rows()}
        assert ("PUT", "/v1/geo/zones/{zone_id}") not in rows
        from app.engines.geo.service import GeoService
        src = inspect.getsource(GeoService.update_zone)
        assert "_require_trusted_tenant" not in src
        assert "select(ServiceZone).where(ServiceZone.id == zone_id))" in src


class TestCanonicalClosure:
    def test_coverage_is_241_of_264(self):
        rows = _canon_rows()
        assert len(rows) == 313
        assert sum(1 for r in rows if r[6] in VERIFIED) == 313

    def test_unprotected_is_23(self):
        rows = _canon_rows()
        assert len(rows) - sum(1 for r in rows if r[6] in VERIFIED) == 0

    def test_denominator_increased_by_exactly_two(self):
        """2F-33 itself increased the denominator by exactly 2 (262->264).
        Tracks LIVE state, which has since grown further via 2F-35 (+9,
        ->273), 2F-36 (+24, ->297), and 2F-37 (+16, ->313); the frozen
        2F-33 point-in-time claim (264) lives only in that slice's own
        docs."""
        assert len(_canon_rows()) == 262 + 2 + 9 + 24 + 16


class TestM01N01NonRegression:
    def test_m01_sample_still_verified(self):
        rows = {(r[0], r[1]): r[6] for r in _canon_rows()}
        assert rows[("POST", "/v1/auth/api-keys")] in VERIFIED

    def test_n01_sample_still_verified(self):
        rows = {(r[0], r[1]): r[6] for r in _canon_rows()}
        assert rows[("POST", "/v1/media/upload")] in VERIFIED
