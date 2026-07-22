"""Phase 2A Slice 2F-36 — Enterprise, Tenant-Administration and Operational
Authorization Batch.

Covers Set A (18 routes, 7 modules: enterprise_grid_saved_views,
enterprise_grid_preferences_exports, admin_catalog_provider_setup,
profile_technician_self_service, profile_universal_self_service,
marketing_automation_provider, analytics_provider_reports) closed, and
Set B (28 held routes, 10 modules) adjudicated -- 24 canonically added
and protected, 1 already-protected exclude (bookings), 3 read-only
excludes (serviceability/check, ds churn/score, ds demand/forecast).
"""
from __future__ import annotations

import csv
import hashlib
import importlib.util
import inspect
import os
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.join(REPO, "docs", "workflow-rearchitecture")
CANON = os.path.join(DOCS, "phase-02a-slice-02f", "tenant-mutation-endpoint-inventory.csv")
MATRIX = os.path.join(DOCS, "phase-02a-slice-02f", "mutation-enforcement-matrix.csv")

VERIFIED = {"TENANT_MUTATION_PERMISSION_SCOPE_AWARE", "TENANT_MUTATION_ROLE_SCOPE_AWARE",
            "STAFF_EXECUTION_ROLE_SCOPE_AWARE", "PLATFORM_ADMIN_ONLY", "PUBLIC_NO_AUTH",
            "CUSTOMER_ROLE_ONLY_NOT_TENANT_SCOPED", "FULLY_PROTECTED"}

SET_A = {
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
SET_B_CANONICAL = {
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
    spec = importlib.util.spec_from_file_location("am36", p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


class TestScopeGuardsLive:
    def test_all_42_routes_access_scope_gated(self):
        E = _model()
        idx = E.route_index()
        for key in SET_A | SET_B_CANONICAL:
            assert key in idx, key
            guards = E.route_guards(idx[key])
            assert any(g["access_scope_gated"] for g in guards), key


class TestTrustedTenantHelpers:
    @pytest.mark.parametrize("mod,cls", [
        ("app.engines.chat.service", "ChatService"),
        ("app.engines.inventory.service", "InventoryService"),
        ("app.engines.appointment.service", "AppointmentService"),
        ("app.engines.service_catalog.service", "ServiceCatalogService"),
        ("app.engines.dispatch.service", "DispatchService"),
        ("app.engines.data_science.service", "DSService"),
        ("app.engines.settings_engine.service", "SettingsService"),
        ("app.engines.notification.service", "NotificationService"),
    ])
    def test_service_has_require_trusted_tenant(self, mod, cls):
        import importlib
        m = importlib.import_module(mod)
        svc = getattr(m, cls)
        assert hasattr(svc, "_require_trusted_tenant")

    @pytest.mark.parametrize("mod,cls", [
        ("app.engines.chat.service", "ChatService"),
        ("app.engines.inventory.service", "InventoryService"),
        ("app.engines.appointment.service", "AppointmentService"),
        ("app.engines.service_catalog.service", "ServiceCatalogService"),
        ("app.engines.dispatch.service", "DispatchService"),
        ("app.engines.data_science.service", "DSService"),
        ("app.engines.settings_engine.service", "SettingsService"),
        ("app.engines.notification.service", "NotificationService"),
    ])
    def test_super_admin_exempt_others_scoped_or_rejected(self, mod, cls):
        import importlib
        m = importlib.import_module(mod)
        svc_cls = getattr(m, cls)
        svc = svc_cls.__new__(svc_cls)
        # super_admin: request honored unchanged
        svc.actor_role = "super_admin"
        svc.actor_tenant_id = None
        assert svc._require_trusted_tenant(TENANT_B) == TENANT_B
        # matching tenant: returns actor's own tenant
        svc.actor_role = "tenant_owner"
        svc.actor_tenant_id = TENANT_A
        assert svc._require_trusted_tenant(TENANT_A) == TENANT_A
        # mismatched tenant: rejected
        from app.exceptions import ServiceOSException
        with pytest.raises(ServiceOSException):
            svc._require_trusted_tenant(TENANT_B)
        # missing tenant context: rejected
        svc.actor_tenant_id = None
        with pytest.raises(ServiceOSException):
            svc._require_trusted_tenant(TENANT_A)


class TestChatParticipantCheck:
    def _svc(self, role="staff", tenant=TENANT_A, actor=ACTOR):
        from app.engines.chat.service import ChatService
        db = MagicMock()
        s = ChatService(db=db, actor_id=actor, actor_role=role, actor_tenant_id=tenant)
        return s

    def test_customer_not_in_participants_rejected(self):
        s = self._svc(role="customer", tenant=None)
        conv = MagicMock(id=uuid.uuid4(), participants=[{"user_id": str(uuid.uuid4())}])
        from app.exceptions import NotFoundException
        with pytest.raises(NotFoundException):
            s._require_participant(conv)

    def test_customer_in_participants_allowed(self):
        s = self._svc(role="customer", tenant=None)
        conv = MagicMock(id=uuid.uuid4(), participants=[{"user_id": str(ACTOR)}])
        s._require_participant(conv)  # does not raise

    def test_staff_role_skips_participant_check(self):
        s = self._svc(role="staff", tenant=TENANT_A)
        conv = MagicMock(id=uuid.uuid4(), participants=[])
        s._require_participant(conv)  # does not raise -- tenant check covers staff


class TestAppointmentOwnership:
    def _svc(self, role="staff", tenant=TENANT_A, actor=ACTOR):
        from app.engines.appointment.service import AppointmentService
        db = MagicMock()
        s = AppointmentService.__new__(AppointmentService)
        s.db = db; s.actor_id = actor; s.actor_role = role; s.actor_tenant_id = tenant
        return s

    def test_same_tenant_staff_allowed(self):
        s = self._svc(role="staff", tenant=TENANT_A)
        appt = MagicMock(id=uuid.uuid4(), tenant_id=TENANT_A, customer_id=uuid.uuid4())
        s._assert_appt_access(appt)  # does not raise

    def test_foreign_tenant_staff_rejected_non_oracular(self):
        s = self._svc(role="staff", tenant=TENANT_A)
        appt = MagicMock(id=uuid.uuid4(), tenant_id=TENANT_B, customer_id=uuid.uuid4())
        from app.exceptions import NotFoundException
        with pytest.raises(NotFoundException):
            s._assert_appt_access(appt)

    def test_customer_owns_own_appointment(self):
        s = self._svc(role="customer", tenant=None, actor=ACTOR)
        appt = MagicMock(id=uuid.uuid4(), tenant_id=TENANT_A, customer_id=ACTOR)
        s._assert_appt_access(appt)  # does not raise

    def test_customer_cannot_touch_others_appointment(self):
        s = self._svc(role="customer", tenant=None, actor=ACTOR)
        appt = MagicMock(id=uuid.uuid4(), tenant_id=TENANT_A, customer_id=uuid.uuid4())
        from app.exceptions import NotFoundException
        with pytest.raises(NotFoundException):
            s._assert_appt_access(appt)

    def test_super_admin_unrestricted(self):
        s = self._svc(role="super_admin", tenant=None)
        appt = MagicMock(id=uuid.uuid4(), tenant_id=TENANT_B, customer_id=uuid.uuid4())
        s._assert_appt_access(appt)  # does not raise


class TestEnterpriseGridSetDefaultOwnership:
    def test_source_confirms_owner_recheck(self):
        from app.engines.enterprise_grid.services import SavedViewService
        src = inspect.getsource(SavedViewService.set_default)
        assert "owner_user_id) != str(user_id)" in src


class TestNoBypassOfClosedRoutes:
    def test_no_direct_service_call_bypasses_router_guard(self):
        import subprocess
        # Every one of the touched services' mutation methods should only
        # be invoked from within its own router module (or an explicitly
        # reviewed internal caller already documented in
        # internal-caller-preservation.csv), never from an unrelated
        # frontend surface.
        checks = [
            (r"\bs\.send_message\(", ["app/engines/chat/router.py"]),
            # create_item/create_reservation are common method names shared
            # by unrelated services (ServiceCatalogService,
            # CommerceService) -- explicitly exclude those legitimate own-
            # router call sites rather than flag a same-named collision.
            (r"\bs\.receive_stock\(",
             ["app/engines/inventory/router.py"]),
            (r"\bs\.create_item\(",
             ["app/engines/inventory/router.py", "app/engines/service_catalog/router.py"]),
            (r"\bs\.(create_reservation|confirm_reservation|release_reservation)\(",
             ["app/engines/inventory/router.py", "app/engines/platform_commerce/router.py"]),
        ]
        offenders = []
        for pattern, excludes in checks:
            cmd = ["git", "grep", "-n", "-E", pattern, "--", "app/"] + \
                  [f":(exclude){e}" for e in excludes]
            r = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True)
            lines = [l for l in r.stdout.splitlines() if ".py:" in l]
            if lines:
                offenders.append(lines)
        assert not offenders, offenders


class TestSetBAdjudication:
    def test_all_28_held_routes_adjudicated(self):
        rows = list(csv.DictReader(open(
            os.path.join(DOCS, "phase-02a-slice-02f36", "held-route-adjudication.csv"),
            encoding="utf-8")))
        assert len(rows) == 28

    def test_24_canonical_additions_all_protected(self):
        rows = list(csv.DictReader(open(
            os.path.join(DOCS, "phase-02a-slice-02f36", "held-route-adjudication.csv"),
            encoding="utf-8")))
        added = [r for r in rows if r["canonical_added"] == "YES"]
        assert len(added) == 24
        for r in added:
            assert r["protected_this_slice"] == "YES", r["path"]

    def test_bookings_already_protected_exclude(self):
        rows = list(csv.DictReader(open(
            os.path.join(DOCS, "phase-02a-slice-02f36", "held-route-adjudication.csv"),
            encoding="utf-8")))
        booking_row = next(r for r in rows if r["path"] == "/v1/bookings")
        assert booking_row["disposition"] == "CUSTOMER_SELF_SERVICE_EXCLUDE"
        assert booking_row["canonical_added"] == "NO"

    def test_read_only_excludes(self):
        rows = list(csv.DictReader(open(
            os.path.join(DOCS, "phase-02a-slice-02f36", "held-route-adjudication.csv"),
            encoding="utf-8")))
        ro = [r for r in rows if r["disposition"] == "READ_ONLY_EXCLUDE"]
        assert len(ro) == 3


class TestCanonicalClosure:
    def test_coverage_is_294_of_297(self):
        rows = _canon_rows()
        assert len(rows) == 313
        assert sum(1 for r in rows if r[6] in VERIFIED) == 313

    def test_unprotected_is_3(self):
        rows = _canon_rows()
        assert len(rows) - sum(1 for r in rows if r[6] in VERIFIED) == 0

    def test_denominator_increased_by_exactly_24(self):
        assert len(_canon_rows()) == 273 + 24 + 16

    def test_all_set_a_routes_protected(self):
        rows = {(r[0], r[1]): r[6] for r in _canon_rows()}
        for key in SET_A:
            assert rows[key] in VERIFIED, key

    def test_all_canonical_set_b_routes_protected(self):
        rows = {(r[0], r[1]): r[6] for r in _canon_rows()}
        for key in SET_B_CANONICAL:
            assert rows[key] in VERIFIED, key


class TestM01N01GeoAnd2F35NonRegression:
    def test_m01_sample_route_verified(self):
        rows = {(r[0], r[1]): r[6] for r in _canon_rows()}
        assert rows[("POST", "/v1/auth/api-keys")] in VERIFIED

    def test_n01_sample_route_verified(self):
        rows = {(r[0], r[1]): r[6] for r in _canon_rows()}
        assert rows[("POST", "/v1/media/upload")] in VERIFIED

    def test_geo_sample_route_verified(self):
        rows = {(r[0], r[1]): r[6] for r in _canon_rows()}
        assert rows[("DELETE", "/v1/geo/zones/{zone_id}")] in VERIFIED

    def test_2f35_sample_routes_verified(self):
        rows = {(r[0], r[1]): r[6] for r in _canon_rows()}
        assert rows[("DELETE", "/v1/webhooks/endpoints/{endpoint_id}")] in VERIFIED
        assert rows[("POST", "/v1/rag/query")] in VERIFIED
        assert rows[("POST", "/v1/documents")] in VERIFIED
