"""Phase 2A Slice 2F-6 — invoice_payment.provider_router tenant-facing
mutation-coverage closure.

This module's 4 mutation routes (provider_issue_invoice,
provider_record_payment, staff_create_invoice, staff_add_invoice_item)
previously had NO role/permission guard at all -- any authenticated user
of any role could issue/pay/create an invoice for any tenant's job
(tenant_id was always server-derived from the caller's own UserContext,
so cross-tenant targeting was already blocked, but role separation was
completely absent).

Fixed this slice:
1. provider_issue_invoice -> require_tenant_mutation_permission(P.FIELD_OPS_INVOICE_GEN)
   (the existing, previously-unwired permission named for this exact
   capability, granted only to tenant_owner).
2. provider_record_payment, staff_create_invoice, staff_add_invoice_item
   -> require_owner_or_office_staff_mutation (tenant_owner/staff, minus
   read-only access_scope). UPDATED in Slice 2F-6A: originally gated with
   require_staff_or_above_mutation (which also admits technician); on
   investigation, no mobile/staff-app caller was found for any of these
   3 routes (tenant-portal web app only), so technician access was not
   proven and the guard was narrowed via a new, small composed
   dependency that deliberately excludes technician. See
   docs/workflow-rearchitecture/phase-02a-slice-02f6a/technician-persona-decision.md.

These tests verify:
- Customer/guest/cross-tenant-role denial on all 4 routes.
- admin_readonly-equivalent (customer_support_limited access_scope)
  denial despite an otherwise-qualifying role.
- Correct persona clears authorization for each of the 4 routes.
- Explicitly wrong role denied.
- Unknown role fails closed.
"""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.dependencies.auth import get_current_user, UserContext


def _user(role: str, access_scope: str | None = None, tenant_id: str | None = None) -> UserContext:
    return UserContext(
        user_id=str(uuid.uuid4()), email=f"{role}@test.local", role=role,
        tenant_id=tenant_id or str(uuid.uuid4()), full_name=role.title(), is_verified=True,
        access_scope=access_scope,
    )


def _override(u):
    app.dependency_overrides[get_current_user] = lambda: u


def _clear():
    app.dependency_overrides.pop(get_current_user, None)


INVOICE_ID = "11111111-1111-1111-1111-111111111111"

ROUTES = [
    ("POST", f"/v1/provider/service-invoices/{INVOICE_ID}/issue", None),
    ("POST", f"/v1/provider/service-invoices/{INVOICE_ID}/record-payment",
     {"payment_mode": "onsite_cash", "collected_amount": "100"}),
    ("POST", "/v1/staff/service-invoices", {"job_id": "job-1"}),
    ("POST", f"/v1/staff/service-invoices/{INVOICE_ID}/items",
     {"item_name": "part", "unit_price": "10"}),
]
ISSUE, RECORD_PAYMENT, CREATE_INVOICE, ADD_ITEM = ROUTES

# provider_issue_invoice is gated by FIELD_OPS_INVOICE_GEN, granted ONLY
# to tenant_owner (re-verified via permissions.py).
ISSUE_AUTHORIZED_ROLES = ["tenant_owner"]
ISSUE_DENIED_ROLES = ["staff", "technician", "customer", "guest"]

# The other 3 are gated by require_owner_or_office_staff_mutation:
# tenant_owner, staff (minus read-only scope) -- technician EXCLUDED as of
# Slice 2F-6A (no proven actor evidence for this specific module).
STAFF_OR_ABOVE_AUTHORIZED_ROLES = ["tenant_owner", "staff"]
STAFF_OR_ABOVE_DENIED_ROLES = ["technician", "customer", "guest"]


def _mock_db():
    mock_database = MagicMock()
    mock_database.execute = AsyncMock(return_value=MagicMock())
    mock_database.commit = AsyncMock()
    mock_database.flush = AsyncMock()
    mock_database.add = MagicMock()

    from app.dependencies.db import get_db

    async def _fake_get_db():
        yield mock_database

    app.dependency_overrides[get_db] = _fake_get_db
    return mock_database


@pytest.fixture(autouse=True)
def _mock_database():
    yield _mock_db()
    from app.dependencies.db import get_db
    app.dependency_overrides.pop(get_db, None)


async def _call(method, path, body):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        return await ac.request(method, path, json=body)


def _assert_cleared_auth(resp):
    """The mocked-DB fixture makes every loaded row a bare MagicMock, so a
    tenant-ownership comparison against it always mismatches, raising a
    business-logic INVOICE_ACCESS_DENIED (also mapped to HTTP 403) -- this
    is expected and proves the request reached business logic, i.e.
    cleared the role/permission authorization layer. A genuine
    authorization-layer 403 has no JSON body error_code of
    INVOICE_ACCESS_DENIED/INVOICE_NOT_FOUND/VALIDATION_ERROR."""
    if resp.status_code == 403:
        code = resp.json().get("error_code")
        assert code == "INVOICE_ACCESS_DENIED", (
            f"unexpected authorization-layer 403 (error_code={code}): {resp.text}"
        )
    else:
        assert resp.status_code != 403


@pytest.mark.asyncio
class TestProviderIssueInvoicePersonaEnforcement:
    @pytest.mark.parametrize("role", ISSUE_AUTHORIZED_ROLES)
    async def test_authorized_role_clears_auth(self, role):
        _override(_user(role))
        try:
            resp = await _call(*ISSUE)
            _assert_cleared_auth(resp)
        finally:
            _clear()

    @pytest.mark.parametrize("role", ISSUE_DENIED_ROLES)
    async def test_denied_role_rejected(self, role):
        _override(_user(role))
        try:
            resp = await _call(*ISSUE)
            assert resp.status_code == 403
        finally:
            _clear()

    async def test_readonly_access_scope_denied_despite_owner_role(self):
        """A tenant_owner-role account with a read-only access_scope must
        still be denied, per the deny-over-grant / access-scope precedence
        rule -- mirrors the tenant_engine/provider_portal precedent."""
        _override(_user("tenant_owner", access_scope="customer_support_limited"))
        try:
            resp = await _call(*ISSUE)
            assert resp.status_code == 403
        finally:
            _clear()

    async def test_unauthenticated_rejected_401(self):
        resp = await _call(*ISSUE)
        assert resp.status_code == 401

    async def test_unknown_role_fails_closed(self):
        _override(_user("totally_bogus_role"))
        try:
            resp = await _call(*ISSUE)
            assert resp.status_code == 403
        finally:
            _clear()


@pytest.mark.asyncio
class TestStaffOrAboveGatedRoutes:
    @pytest.mark.parametrize("route", [RECORD_PAYMENT, CREATE_INVOICE, ADD_ITEM])
    @pytest.mark.parametrize("role", STAFF_OR_ABOVE_AUTHORIZED_ROLES)
    async def test_authorized_role_clears_auth(self, role, route):
        _override(_user(role))
        try:
            resp = await _call(*route)
            _assert_cleared_auth(resp)
        finally:
            _clear()

    @pytest.mark.parametrize("route", [RECORD_PAYMENT, CREATE_INVOICE, ADD_ITEM])
    @pytest.mark.parametrize("role", STAFF_OR_ABOVE_DENIED_ROLES)
    async def test_denied_role_rejected(self, role, route):
        _override(_user(role))
        try:
            resp = await _call(*route)
            assert resp.status_code == 403, f"{role} not denied at {route[1]}"
        finally:
            _clear()

    @pytest.mark.parametrize("route", [RECORD_PAYMENT, CREATE_INVOICE, ADD_ITEM])
    async def test_readonly_access_scope_denied(self, route):
        _override(_user("staff", access_scope="customer_support_limited"))
        try:
            resp = await _call(*route)
            assert resp.status_code == 403
        finally:
            _clear()

    @pytest.mark.parametrize("route", [RECORD_PAYMENT, CREATE_INVOICE, ADD_ITEM])
    async def test_unauthenticated_rejected_401(self, route):
        resp = await _call(*route)
        assert resp.status_code == 401

    @pytest.mark.parametrize("route", [RECORD_PAYMENT, CREATE_INVOICE, ADD_ITEM])
    async def test_unknown_role_fails_closed(self, route):
        _override(_user("totally_bogus_role"))
        try:
            resp = await _call(*route)
            assert resp.status_code == 403
        finally:
            _clear()

    async def test_super_admin_clears_auth_all_routes(self):
        _override(_user("super_admin"))
        try:
            for route in ROUTES:
                resp = await _call(*route)
                _assert_cleared_auth(resp)
        finally:
            _clear()


class TestTenantOwnershipEnforcedAtServiceLayer:
    """create_invoice/add_item/issue_invoice/record_onsite_payment all
    load the target row and compare its tenant_id against the caller's
    own server-derived tenant_id (never a client-supplied value) --
    confirmed via source inspection, unmodified this slice."""

    def test_create_invoice_checks_tenant_ownership(self):
        import inspect
        from app.engines.invoice_payment.invoice_service import ServiceInvoiceService
        src = inspect.getsource(ServiceInvoiceService.create_invoice)
        assert "job.tenant_id" in src and "tenant_id" in src
        assert "ERR_INVOICE_ACCESS_DENIED" in src

    def test_add_item_checks_tenant_ownership(self):
        import inspect
        from app.engines.invoice_payment.invoice_service import ServiceInvoiceService
        src = inspect.getsource(ServiceInvoiceService.add_item)
        assert "_assert_tenant" in src

    def test_issue_invoice_checks_tenant_ownership(self):
        import inspect
        from app.engines.invoice_payment.invoice_service import ServiceInvoiceService
        src = inspect.getsource(ServiceInvoiceService.issue_invoice)
        assert "_assert_tenant" in src

    def test_record_payment_checks_tenant_ownership(self):
        import inspect
        from app.engines.invoice_payment.payment_service import ServicePaymentService
        src = inspect.getsource(ServicePaymentService.record_onsite_payment)
        assert "inv.tenant_id" in src and "ERR_INVOICE_ACCESS_DENIED" in src

    def test_router_derives_tenant_id_from_caller_not_client(self):
        import inspect
        from app.engines.invoice_payment import provider_router
        src = inspect.getsource(provider_router)
        # Every service call passes str(user.tenant_id) -- never a
        # request-body or path-supplied tenant_id.
        assert "tenant_id=body" not in src
        assert "str(user.tenant_id)" in src


class TestModuleVerificationExitsClean:
    def _load_inventory_module(self):
        import importlib.util
        from pathlib import Path
        spec = importlib.util.spec_from_file_location(
            "inventory_mutation_routes",
            Path(__file__).parent.parent / "scripts" / "workflow_rearchitecture" / "inventory_mutation_routes.py",
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def test_invoice_payment_provider_router_zero_unverified(self):
        mod = self._load_inventory_module()
        routes = [r for r in mod.walk(app.router if hasattr(app, "router") else app)
                  if r["module"] == "app.engines.invoice_payment.provider_router"]
        assert len(routes) == 4
        exempt = mod.CONFIRMED_FALSE_POSITIVE_ROUTES | mod.CONFIRMED_PLATFORM_ADMIN_PERMISSION_ROUTES
        unverified = [
            r for r in routes
            if r["guard_status"] not in mod.ACCEPTED_GUARD_STATUSES
            and (r["module"], r["endpoint_name"]) not in exempt
        ]
        assert unverified == [], f"unverified routes remain: {unverified}"
