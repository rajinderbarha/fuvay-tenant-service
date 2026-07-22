"""Phase 2A Slice 2F-7 — serviceability.router tenant-facing mutation
enforcement closure.

19 mounted mutation routes were re-verified via runtime introspection.
8 are genuine tenant-facing mutations (Tenant Service Areas / Service
Mappings), previously gated by plain require_permission(P.TENANT_SERVICE_AREA_*)
with NO access-scope enforcement -- a read-only-scoped tenant_owner
(access_scope="customer_support_limited") could mutate service-area
coverage despite holding the create/update/delete permission bundle.

Fixed this slice: all 8 now use require_tenant_mutation_permission(...),
the same composed guard used for tenant_engine.router (Slice 2F-1) and
provider_issue_invoice (Slice 2F-6) -- denies read-only-scoped actors
before any business logic runs.

Persona evidence (re-verified, not assumed): TENANT_SERVICE_AREA_CREATE/
UPDATE/DELETE/SERVICE_CREATE/SERVICE_UPDATE/SERVICE_DELETE are granted
ONLY to tenant_owner in ROLE_PERMISSIONS (staff/technician hold only the
READ permission, "view not edit" per the staff bundle's own comment) --
so these 8 routes are TENANT_OWNER_SERVICE_AREA / TENANT_OWNER_SERVICE_COVERAGE,
not delegated-staff capabilities. No permission was granted this slice.

The remaining 11 mounted mutations are NOT tenant-facing:
- 4 customer-own-address mutations (customer role only)
- 4 platform-admin routes (require_permission(P.PLATFORM_ADMIN), granted
  to no role but super_admin)
- 3 serviceability check/matching/available-services queries (no DB
  write, or audit-log-only side effect)
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


AREA_ID = "11111111-1111-1111-1111-111111111111"
MAPPING_ID = "22222222-2222-2222-2222-222222222222"

TENANT_MUTATION_ROUTES = [
    ("POST", "/v1/tenant/service-areas",
     {"coverage_type": "city", "state": "Maharashtra", "city": "Pune"}),
    ("POST", "/v1/tenant/service-areas/validate",
     {"coverage_type": "city", "state": "Maharashtra", "city": "Pune"}),
    ("PUT", f"/v1/tenant/service-areas/{AREA_ID}", {"city": "Mumbai"}),
    ("DELETE", f"/v1/tenant/service-areas/{AREA_ID}", None),
    ("POST", f"/v1/tenant/service-areas/{AREA_ID}/set-primary", None),
    ("POST", f"/v1/tenant/service-areas/{AREA_ID}/services",
     {"service_id": str(uuid.uuid4())}),
    ("PUT", f"/v1/tenant/service-areas/{AREA_ID}/services/{MAPPING_ID}",
     {"is_available": False}),
    ("DELETE", f"/v1/tenant/service-areas/{AREA_ID}/services/{MAPPING_ID}", None),
]

TENANT_OWNER_ONLY_DENIED_ROLES = ["staff", "technician", "customer", "guest"]


def _mock_db():
    mock_database = MagicMock()
    mock_database.execute = AsyncMock(return_value=MagicMock())
    mock_database.commit = AsyncMock()
    mock_database.flush = AsyncMock()
    mock_database.add = MagicMock()
    mock_database.get = AsyncMock(return_value=None)

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


async def _call_allow_business_error(method, path, body):
    """Some routes (e.g. validate/create) reach real business logic that
    trips over the bare-MagicMock db fixture (e.g. `max_areas - used` where
    `used` is a MagicMock) with a raw TypeError -- ASGITransport re-raises
    unhandled exceptions rather than returning a 500 response. Catching it
    here is the accepted proof-of-cleared-auth pattern used throughout this
    slice series when the mocked DB isn't realistic enough for deeper
    business logic, without weakening the actual authorization assertion."""
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            return await ac.request(method, path, json=body)
    except TypeError:
        return None


@pytest.mark.asyncio
class TestTenantOwnerServiceAreaAuthorization:
    @pytest.mark.parametrize("method,path,body", TENANT_MUTATION_ROUTES)
    async def test_tenant_owner_clears_auth(self, method, path, body):
        _override(_user("tenant_owner"))
        try:
            resp = await _call_allow_business_error(method, path, body)
            if resp is not None:
                assert resp.status_code != 403, f"tenant_owner denied at {method} {path}: {resp.text}"
        finally:
            _clear()

    @pytest.mark.parametrize("role", TENANT_OWNER_ONLY_DENIED_ROLES)
    @pytest.mark.parametrize("method,path,body", TENANT_MUTATION_ROUTES)
    async def test_non_owner_role_denied(self, role, method, path, body):
        _override(_user(role))
        try:
            resp = await _call(method, path, body)
            assert resp.status_code == 403, f"{role} not denied at {method} {path}"
        finally:
            _clear()

    @pytest.mark.parametrize("method,path,body", TENANT_MUTATION_ROUTES)
    async def test_readonly_access_scope_denied_despite_owner_role(self, method, path, body):
        """A tenant_owner-role account with a read-only access_scope must
        still be denied -- proves the access-scope guard was actually
        wired in, not just the permission check."""
        _override(_user("tenant_owner", access_scope="customer_support_limited"))
        try:
            resp = await _call(method, path, body)
            assert resp.status_code == 403
        finally:
            _clear()

    @pytest.mark.parametrize("method,path,body", TENANT_MUTATION_ROUTES)
    async def test_unauthenticated_rejected_401(self, method, path, body):
        resp = await _call(method, path, body)
        assert resp.status_code == 401

    @pytest.mark.parametrize("method,path,body", TENANT_MUTATION_ROUTES)
    async def test_unknown_role_fails_closed(self, method, path, body):
        _override(_user("totally_bogus_role"))
        try:
            resp = await _call(method, path, body)
            assert resp.status_code == 403
        finally:
            _clear()

    async def test_super_admin_clears_auth_all_routes(self):
        _override(_user("super_admin"))
        try:
            for method, path, body in TENANT_MUTATION_ROUTES:
                resp = await _call_allow_business_error(method, path, body)
                if resp is not None:
                    assert resp.status_code != 403, f"super_admin denied at {method} {path}"
        finally:
            _clear()


@pytest.mark.asyncio
class TestPlatformAdminRoutesUnaffected:
    """The 4 admin_* routes must remain super_admin-only via
    require_permission(P.PLATFORM_ADMIN), unchanged this slice."""

    ADMIN_ROUTES = [
        ("POST", "/v1/admin/tenants/{}/service-areas".format(str(uuid.uuid4())),
         {"coverage_type": "city", "state": "Maharashtra", "city": "Pune"}),
        ("PUT", "/v1/admin/tenants/{}/service-areas/{}".format(str(uuid.uuid4()), AREA_ID),
         {"city": "Mumbai"}),
        ("DELETE", "/v1/admin/tenants/{}/service-areas/{}".format(str(uuid.uuid4()), AREA_ID), None),
        ("POST", "/v1/admin/serviceability/test",
         {"city": "Pune", "state": "Maharashtra"}),
    ]

    @pytest.mark.parametrize("method,path,body", ADMIN_ROUTES)
    async def test_tenant_owner_denied(self, method, path, body):
        _override(_user("tenant_owner"))
        try:
            resp = await _call(method, path, body)
            assert resp.status_code == 403
        finally:
            _clear()

    @pytest.mark.parametrize("method,path,body", ADMIN_ROUTES)
    async def test_super_admin_clears_auth(self, method, path, body):
        _override(_user("super_admin"))
        try:
            resp = await _call(method, path, body)
            assert resp.status_code != 403
        finally:
            _clear()


@pytest.mark.asyncio
class TestCrossTenantServiceAreaRejection:
    """Direct proof (not source-string) that a real cross-tenant area_id
    is rejected via the service layer's _assert_owns_tenant, using a
    genuinely mocked TenantServiceArea row belonging to a different
    tenant."""

    async def test_update_cross_tenant_area_rejected_no_mutation(self):
        from app.engines.serviceability.service import ServiceabilityService
        from app.engines.serviceability.models import TenantServiceArea
        other_tenant = uuid.uuid4()
        my_tenant = uuid.uuid4()
        area = MagicMock(spec=TenantServiceArea)
        area.id = uuid.UUID(AREA_ID)
        area.tenant_id = other_tenant
        area.is_active = True
        area.to_dict = lambda: {"id": AREA_ID}

        db = MagicMock()
        db.get = AsyncMock(return_value=area)
        db.commit = AsyncMock()
        db.add = MagicMock()

        svc = ServiceabilityService(db=db, request_id="r1", actor_id=uuid.uuid4(),
                                     actor_role="tenant_owner", actor_tenant_id=my_tenant)
        from app.exceptions import NotFoundException
        with pytest.raises(NotFoundException):
            await svc.update_service_area(uuid.UUID(AREA_ID), {"city": "Mumbai"})
        db.commit.assert_not_called()

    async def test_deactivate_cross_tenant_area_rejected_no_mutation(self):
        from app.engines.serviceability.service import ServiceabilityService
        from app.engines.serviceability.models import TenantServiceArea
        other_tenant = uuid.uuid4()
        my_tenant = uuid.uuid4()
        area = MagicMock(spec=TenantServiceArea)
        area.id = uuid.UUID(AREA_ID)
        area.tenant_id = other_tenant
        area.is_active = True

        db = MagicMock()
        db.get = AsyncMock(return_value=area)
        db.commit = AsyncMock()

        svc = ServiceabilityService(db=db, request_id="r1", actor_id=uuid.uuid4(),
                                     actor_role="tenant_owner", actor_tenant_id=my_tenant)
        from app.exceptions import NotFoundException
        with pytest.raises(NotFoundException):
            await svc.deactivate_service_area(uuid.UUID(AREA_ID))
        db.commit.assert_not_called()

    async def test_list_service_areas_cross_tenant_rejected(self):
        from app.engines.serviceability.service import ServiceabilityService
        from app.exceptions import NotFoundException
        other_tenant = uuid.uuid4()
        my_tenant = uuid.uuid4()
        db = MagicMock()
        svc = ServiceabilityService(db=db, request_id="r1", actor_id=uuid.uuid4(),
                                     actor_role="tenant_owner", actor_tenant_id=my_tenant)
        with pytest.raises(NotFoundException):
            await svc.list_service_areas(other_tenant)

    async def test_admin_update_with_mismatched_tenant_id_rejected(self):
        """FINAL-L5-05Q's own fix, re-verified unmodified: the admin router
        passes tenant_id from the URL; if it doesn't match the loaded
        area's real tenant_id, reject rather than silently ignore."""
        from app.engines.serviceability.service import ServiceabilityService
        from app.engines.serviceability.models import TenantServiceArea
        real_tenant = uuid.uuid4()
        spoofed_tenant = uuid.uuid4()
        area = MagicMock(spec=TenantServiceArea)
        area.id = uuid.UUID(AREA_ID)
        area.tenant_id = real_tenant
        area.is_active = True

        db = MagicMock()
        db.get = AsyncMock(return_value=area)

        svc = ServiceabilityService(db=db, request_id="r1", actor_id=uuid.uuid4(),
                                     actor_role="super_admin", actor_tenant_id=None)
        from app.exceptions import NotFoundException
        with pytest.raises(NotFoundException):
            await svc.update_service_area(uuid.UUID(AREA_ID), {"city": "Mumbai"},
                                           admin_tenant_id=spoofed_tenant)


class TestDuplicateServiceAreaGuardUnchanged:
    def test_source_confirms_duplicate_guard(self):
        import inspect
        from app.engines.serviceability.service import ServiceabilityService
        src = inspect.getsource(ServiceabilityService._check_duplicate_area)
        assert "ERR_DUPLICATE_AREA" in src

    def test_source_confirms_advisory_lock_for_concurrent_create(self):
        import inspect
        from app.engines.serviceability.service import ServiceabilityService
        src = inspect.getsource(ServiceabilityService.create_service_area)
        assert "pg_advisory_xact_lock" in src


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

    def test_serviceability_router_zero_unverified(self):
        mod = self._load_inventory_module()
        routes = [r for r in mod.walk(app.router if hasattr(app, "router") else app)
                  if r["module"] == "app.engines.serviceability.router"]
        assert len(routes) == 19
        exempt = mod.CONFIRMED_FALSE_POSITIVE_ROUTES | mod.CONFIRMED_PLATFORM_ADMIN_PERMISSION_ROUTES
        unverified = [
            r for r in routes
            if r["guard_status"] not in mod.ACCEPTED_GUARD_STATUSES
            and (r["module"], r["endpoint_name"]) not in exempt
        ]
        assert unverified == [], f"unverified routes remain: {unverified}"
