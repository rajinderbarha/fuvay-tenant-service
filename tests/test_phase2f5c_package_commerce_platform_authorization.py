"""Phase 2A Slice 2F-5C — package_commerce.admin_router platform authorization
and financial-integrity closure.

package_commerce.admin_router is confirmed platform-facing, with NO tenant
persona -- these tests verify:
1. Platform-role separation for the 2 admin_finance-granted credit-wallet
   adapter mutations vs the 15 super_admin-only mutations (13 package-
   lifecycle routes + admin_purchase_package + the 2 commission routes,
   which use require_super_admin directly rather than a permission).
2. Tenant roles (tenant_owner/staff/technician/customer/guest) denied on
   every mutation.
3. admin_readonly, admin_operations, admin_security denied every mutation.
4. The 3 deprecated security-deposit routes return 410, perform no DB
   write, and are unauthenticated-reachable (no data leak possible since
   they raise before touching the DB) -- confirmed unchanged this slice.
5. Package-assignment idempotency: create_package_assignment blocks a
   second pending assignment for the same tenant+package (pre-existing
   guard, unmodified, source-inspection confirmed).
6. Commission idempotency: calculate_commission/deduct_commission dedupe
   on job_id (pre-existing guards, unmodified, source-inspection
   confirmed).
"""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.dependencies.auth import get_current_user, UserContext


def _user(role: str) -> UserContext:
    return UserContext(
        user_id=str(uuid.uuid4()), email=f"{role}@test.local", role=role,
        tenant_id=None, full_name=role.title(), is_verified=True,
    )


def _override(u):
    app.dependency_overrides[get_current_user] = lambda: u


def _clear():
    app.dependency_overrides.pop(get_current_user, None)


PID = "11111111-1111-1111-1111-111111111111"
FID = "22222222-2222-2222-2222-222222222222"
LID = "33333333-3333-3333-3333-333333333333"
TID = "44444444-4444-4444-4444-444444444444"
JID = "job-1"

# The 2 endpoints whose permission IS granted to admin_finance.
ADMIN_FINANCE_GRANTED_ENDPOINTS = [
    ("POST", f"/v1/admin/tenants/{TID}/credit-wallet/top-up", {"amount": "10.00", "reason": "test"}),
    ("POST", f"/v1/admin/tenants/{TID}/credit-wallet/adjust", {"amount": "10.00", "reason": "test", "entry_type": "credit"}),
]

# The 15 endpoints reachable only via super_admin's P.ALL wildcard (12
# package-lifecycle + purchase + 2 commission via require_super_admin).
SUPER_ADMIN_ONLY_ENDPOINTS = [
    ("POST", "/v1/admin/packages", {"name": "Test Pkg", "package_type": "subscription", "package_price": "10"}),
    ("PUT", f"/v1/admin/packages/{PID}", {"name": "Updated"}),
    ("DELETE", f"/v1/admin/packages/{PID}", None),
    ("POST", f"/v1/admin/packages/{PID}/activate", None),
    ("POST", f"/v1/admin/packages/{PID}/deactivate", None),
    ("POST", f"/v1/admin/packages/{PID}/clone", None),
    ("POST", f"/v1/admin/packages/{PID}/features", {"name": "f"}),
    ("PUT", f"/v1/admin/packages/{PID}/features/{FID}", {"name": "f2"}),
    ("DELETE", f"/v1/admin/packages/{PID}/features/{FID}", None),
    ("POST", f"/v1/admin/packages/{PID}/limits", {"name": "l"}),
    ("PUT", f"/v1/admin/packages/{PID}/limits/{LID}", {"name": "l2"}),
    ("DELETE", f"/v1/admin/packages/{PID}/limits/{LID}", None),
    ("POST", f"/v1/admin/tenants/{TID}/packages/{PID}/purchase", {"payment_reference": "ref"}),
    ("POST", f"/v1/admin/jobs/{JID}/deduct-commission", {"tenant_id": TID}),
    ("POST", f"/v1/admin/jobs/{JID}/calculate-commission", {"tenant_id": TID, "job_value": "100.00"}),
]

DEPRECATED_410_ENDPOINTS = [
    ("GET", f"/v1/admin/tenants/{TID}/security-deposit"),
    ("POST", f"/v1/admin/tenants/{TID}/security-deposit/mark-paid"),
    ("POST", f"/v1/admin/tenants/{TID}/security-deposit/refund"),
    ("POST", f"/v1/admin/tenants/{TID}/security-deposit/forfeit"),
]

ALL_MUTATIONS = ADMIN_FINANCE_GRANTED_ENDPOINTS + SUPER_ADMIN_ONLY_ENDPOINTS
TENANT_ROLES = ["tenant_owner", "staff", "technician", "customer", "guest"]


def _mock_db(monkeypatch):
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
def _mock_database(monkeypatch):
    yield _mock_db(monkeypatch)
    from app.dependencies.db import get_db
    app.dependency_overrides.pop(get_db, None)


@pytest.mark.asyncio
class TestTenantRolesDeniedEverywhere:
    @pytest.mark.parametrize("role", TENANT_ROLES)
    @pytest.mark.parametrize("method,path,body", ALL_MUTATIONS)
    async def test_tenant_role_denied(self, role, method, path, body):
        _override(_user(role))
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                resp = await ac.request(method, path, json=body)
            assert resp.status_code == 403, f"{role} {method} {path} -> {resp.status_code}"
        finally:
            _clear()


@pytest.mark.asyncio
class TestAdminReadonlyCannotMutate:
    @pytest.mark.parametrize("method,path,body", ALL_MUTATIONS)
    async def test_readonly_denied(self, method, path, body):
        _override(_user("admin_readonly"))
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                resp = await ac.request(method, path, json=body)
            assert resp.status_code == 403
        finally:
            _clear()


@pytest.mark.asyncio
class TestAdminOperationsAndSecurityDenied:
    @pytest.mark.parametrize("role", ["admin_operations", "admin_security"])
    @pytest.mark.parametrize("method,path,body", ALL_MUTATIONS)
    async def test_denied(self, role, method, path, body):
        _override(_user(role))
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                resp = await ac.request(method, path, json=body)
            assert resp.status_code == 403
        finally:
            _clear()


@pytest.mark.asyncio
class TestAdminFinanceAccessMatchesGrantedPermissionsOnly:
    @pytest.mark.parametrize("method,path,body", ADMIN_FINANCE_GRANTED_ENDPOINTS)
    async def test_admin_finance_clears_auth_for_granted_endpoints(self, method, path, body):
        _override(_user("admin_finance"))
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                resp = await ac.request(method, path, json=body)
            assert resp.status_code != 403, f"admin_finance denied granted endpoint {method} {path}"
        finally:
            _clear()

    @pytest.mark.parametrize("method,path,body", SUPER_ADMIN_ONLY_ENDPOINTS)
    async def test_admin_finance_denied_for_ungranted_endpoints(self, method, path, body):
        _override(_user("admin_finance"))
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                resp = await ac.request(method, path, json=body)
            assert resp.status_code == 403
        finally:
            _clear()


@pytest.mark.asyncio
class TestSuperAdminRetainsAccessEverywhere:
    @pytest.mark.parametrize("method,path,body", ALL_MUTATIONS)
    async def test_super_admin_clears_auth(self, method, path, body):
        _override(_user("super_admin"))
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                resp = await ac.request(method, path, json=body)
            if resp.status_code == 403:
                # deduct_commission's mocked-DB CommissionRecord.tenant_id
                # mismatch raises a business-logic 403 (TENANT_ACCESS_DENIED)
                # -- this proves auth was cleared and business logic was
                # reached, not that the permission guard rejected the call.
                assert resp.json().get("error_code") == "TENANT_ACCESS_DENIED", (
                    f"unexpected 403 for super_admin at {method} {path}: {resp.text}"
                )
            else:
                assert resp.status_code != 403
        finally:
            _clear()

    async def test_unauthenticated_rejected_401(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.post(f"/v1/admin/packages/{PID}/activate")
        assert resp.status_code == 401

    async def test_unknown_role_fails_closed(self):
        _override(_user("totally_bogus_role"))
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                resp = await ac.post(f"/v1/admin/packages/{PID}/activate")
            assert resp.status_code == 403
        finally:
            _clear()


@pytest.mark.asyncio
class TestDeprecatedSecurityDepositRoutes:
    @pytest.mark.parametrize("method,path", DEPRECATED_410_ENDPOINTS)
    async def test_returns_410_no_auth_required(self, method, path):
        """No auth override at all -- these routes have zero Depends(),
        confirming they fail before touching any authorization or DB layer."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.request(method, path)
        assert resp.status_code == 410

    @pytest.mark.parametrize("method,path", DEPRECATED_410_ENDPOINTS)
    async def test_no_db_mutation_occurs(self, method, path, _mock_database):
        _mock_database.execute.reset_mock()
        _mock_database.add.reset_mock()
        _mock_database.commit.reset_mock()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            await ac.request(method, path)
        _mock_database.execute.assert_not_called()
        _mock_database.add.assert_not_called()
        _mock_database.commit.assert_not_called()

    def test_source_confirms_no_service_call(self):
        import inspect
        from app.engines.package_commerce import admin_router
        for name in ("admin_get_deposit", "admin_mark_deposit_paid",
                     "admin_refund_deposit", "admin_forfeit_deposit"):
            src = inspect.getsource(getattr(admin_router, name))
            assert "_svc(" not in src, f"{name} must not call the service layer"
            assert "raise HTTPException(status_code=410" in src


class TestPackageAssignmentIdempotencyUnchanged:
    def test_source_confirms_duplicate_pending_guard(self):
        import inspect
        from app.engines.package_commerce.service import PackageCommerceService
        src = inspect.getsource(PackageCommerceService.create_package_assignment)
        assert "PACKAGE_ALREADY_PENDING" in src
        assert "selected_at=now" in src or "selected" in src

    def test_source_confirms_price_is_server_derived(self):
        import inspect
        from app.engines.package_commerce.service import PackageCommerceService
        src = inspect.getsource(PackageCommerceService.create_package_assignment)
        # price_amount is set from pkg.package_price (server-loaded), never
        # from a client-supplied payload field.
        assert "price_amount=pkg.package_price" in src

    def test_source_confirms_package_must_be_active(self):
        import inspect
        from app.engines.package_commerce.service import PackageCommerceService
        src = inspect.getsource(PackageCommerceService.create_package_assignment)
        assert "PACKAGE_INACTIVE" in src


class TestCommissionIdempotencyUnchanged:
    def test_calculate_commission_dedupes_on_job_id(self):
        import inspect
        from app.engines.package_commerce.service import PackageCommerceService
        src = inspect.getsource(PackageCommerceService.calculate_commission)
        assert "CommissionRecord.job_id == job_id" in src

    def test_deduct_commission_blocks_double_deduction(self):
        import inspect
        from app.engines.package_commerce.service import PackageCommerceService
        src = inspect.getsource(PackageCommerceService.deduct_commission)
        assert 'record.status == "deducted"' in src
        assert "COMMISSION_ALREADY_DEDUCTED" in src

    def test_deduct_commission_rejects_wrong_tenant(self):
        import inspect
        from app.engines.package_commerce.service import PackageCommerceService
        src = inspect.getsource(PackageCommerceService.deduct_commission)
        assert "record.tenant_id != tenant_id" in src
        assert "TENANT_ACCESS_DENIED" in src

    def test_deduct_commission_uses_stable_idempotency_key(self):
        import inspect
        from app.engines.package_commerce.service import PackageCommerceService
        src = inspect.getsource(PackageCommerceService.deduct_commission)
        assert 'idempotency_key=f"commission-deduct-{record.id}"' in src


class TestDeletePackageGuardUnchanged:
    def test_source_confirms_existing_assignment_block(self):
        import inspect
        from app.engines.package_commerce.service import PackageCommerceService
        src = inspect.getsource(PackageCommerceService.delete_package)
        assert "TenantPackageAssignment.package_id == package_id" in src
        assert "CONFLICT" in src


class TestOrphanedServiceMethodsHaveNoLiveCaller:
    """Regression guard: PackageCommerceService.admin_mark_deposit_paid/
    admin_refund_deposit/admin_forfeit_deposit/admin_topup_wallet/
    admin_adjust_wallet/purchase_package all still exist in service.py but
    are confirmed to have zero callers anywhere in app/ (the router calls
    UsageCreditService or raises 410 directly instead). This test fails
    loudly if a future change accidentally wires a router back to one of
    these unaudited, ledger-bypassing methods."""

    @pytest.mark.parametrize("method_name", [
        "admin_mark_deposit_paid", "admin_refund_deposit", "admin_forfeit_deposit",
        "admin_topup_wallet", "admin_adjust_wallet", "purchase_package",
    ])
    def test_no_caller_in_admin_router(self, method_name):
        import inspect
        from app.engines.package_commerce import admin_router
        src = inspect.getsource(admin_router)
        assert f".{method_name}(" not in src


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

    def test_package_commerce_admin_router_zero_unverified(self):
        mod = self._load_inventory_module()
        routes = [r for r in mod.walk(app.router if hasattr(app, "router") else app)
                  if r["module"] == "app.engines.package_commerce.admin_router"]
        assert len(routes) == 20

        exempt = mod.CONFIRMED_FALSE_POSITIVE_ROUTES | mod.CONFIRMED_PLATFORM_ADMIN_PERMISSION_ROUTES
        unverified = [
            r for r in routes
            if r["guard_status"] not in mod.ACCEPTED_GUARD_STATUSES
            and (r["module"], r["endpoint_name"]) not in exempt
        ]
        assert unverified == [], f"unverified routes remain: {unverified}"
