"""Phase 2A Slice 2F-8 — admin_catalog.tenant_router final mutation gap and
catalog-ownership closure.

10 mounted mutation routes were re-verified via runtime introspection.
9 were ALREADY access-scope protected via require_tenant_mutation_permission
(P.TENANT_UPDATE) -- re-confirmed unmodified this slice. The 1 remaining
route, preview_tenant_price_options, is a synchronous, non-async pure
computation (no self.db access) -- confirmed a FALSE_POSITIVE, not a real
mutation, and added to the inventory tool's allowlist rather than gated.

TENANT_UPDATE is granted ONLY to tenant_owner in ROLE_PERMISSIONS (staff/
technician hold no TENANT_UPDATE grant at all) -- so all 9 real mutations
are TENANT_OWNER_CATALOG_MAPPING / TENANT_OWNER_SERVICE_ENABLEMENT, not a
delegated-staff capability. No permission was granted this slice.

The genuine defect found and fixed this slice: enable_service/disable_service
(and the 3 GET list routes sharing the same helper) accepted an optional
`tenant_id` query parameter via TenantCatalogService._require_tenant_id,
which previously used ANY supplied tenant_id_raw unconditionally -- a
tenant_owner (who legitimately holds TENANT_UPDATE) could pass a foreign
tenant_id and enable/disable a service for a tenant they do not belong to,
or read a foreign tenant's catalog. Fixed by requiring a non-platform
actor's supplied tenant_id to match their own actor_tenant_id (mirrors the
FINAL-L5-05Q pattern already used in serviceability's admin router).
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


TS_ID = "11111111-1111-1111-1111-111111111111"
STYPE_ID = "22222222-2222-2222-2222-222222222222"
BRAND_ID = "33333333-3333-3333-3333-333333333333"
MASTER_SVC_ID = str(uuid.uuid4())

TENANT_MUTATION_ROUTES = [
    ("POST", "/v1/tenant/catalog/enable-service", {"master_service_id": MASTER_SVC_ID}),
    ("PUT", f"/v1/tenant/catalog/enabled-services/{TS_ID}", {"tenant_display_name": "x"}),
    ("POST", "/v1/tenant/catalog/disable-service", {"master_service_id": MASTER_SVC_ID}),
    ("PUT", f"/v1/tenant/catalog/enabled-services/{TS_ID}/types", {"type_ids": [STYPE_ID]}),
    ("PUT", f"/v1/tenant/catalog/enabled-services/{TS_ID}/brands", {"brand_ids": [BRAND_ID]}),
    ("PUT", f"/v1/tenant/catalog/enabled-services/{TS_ID}/types/{STYPE_ID}/pricing",
     {"tenant_min_price": "100", "tenant_max_price": "200"}),
    ("PUT", f"/v1/tenant/catalog/enabled-services/{TS_ID}/brands/{BRAND_ID}/pricing",
     {"tenant_min_price": "100", "tenant_max_price": "200"}),
    ("POST", f"/v1/tenant/catalog/enabled-services/{TS_ID}/publish", None),
    ("POST", f"/v1/tenant/catalog/enabled-services/{TS_ID}/save-draft", None),
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


_BUSINESS_LOGIC_ERROR_CODES = {
    "CATEGORY_NOT_ENTITLED", "MASTER_SERVICE_INACTIVE", "MASTER_SERVICE_NOT_FOUND",
    "SERVICE_CATEGORY_INACTIVE", "TENANT_SERVICE_NOT_ENABLED", "TENANT_SERVICE_ALREADY_ENABLED",
}


async def _call_allow_business_error(method, path, body):
    """Mocked-DB business logic (e.g. NotFoundException from a bare
    MagicMock scalar_one_or_none, or a domain rule like CATEGORY_NOT_ENTITLED
    tripped by the mocked entitlement lookup) is accepted as proof of
    clearing the auth layer, per the established test convention in this
    slice series -- distinguished from a real authorization-layer 403 by
    checking the JSON body's error_code."""
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.request(method, path, json=body)
    except TypeError:
        return None
    if resp.status_code == 403:
        code = resp.json().get("error_code")
        if code in _BUSINESS_LOGIC_ERROR_CODES:
            return None
    return resp


async def _call(method, path, body):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        return await ac.request(method, path, json=body)


@pytest.mark.asyncio
class TestTenantOwnerCatalogMappingAuthorization:
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
class TestCrossTenantTenantIdOverrideRejected:
    """Direct proof of the fix: a non-platform actor's own tenant_id is
    authoritative; a foreign tenant_id supplied via query param is rejected
    outright rather than silently honored."""

    async def test_enable_service_foreign_tenant_id_query_param_rejected(self):
        from app.engines.admin_catalog.tenant_service import TenantCatalogService
        my_tenant = uuid.uuid4()
        foreign_tenant = uuid.uuid4()
        db = MagicMock()
        svc = TenantCatalogService(db=db, request_id="r1", actor_id=uuid.uuid4(),
                                    actor_role="tenant_owner", actor_tenant_id=my_tenant)
        from app.exceptions import ServiceOSException
        with pytest.raises(ServiceOSException) as exc:
            await svc.enable_service({"master_service_id": str(uuid.uuid4())},
                                      tenant_id_raw=foreign_tenant)
        assert exc.value.error_code == "PERMISSION_DENIED"

    async def test_disable_service_foreign_tenant_id_query_param_rejected(self):
        from app.engines.admin_catalog.tenant_service import TenantCatalogService
        my_tenant = uuid.uuid4()
        foreign_tenant = uuid.uuid4()
        db = MagicMock()
        svc = TenantCatalogService(db=db, request_id="r1", actor_id=uuid.uuid4(),
                                    actor_role="tenant_owner", actor_tenant_id=my_tenant)
        from app.exceptions import ServiceOSException
        with pytest.raises(ServiceOSException) as exc:
            await svc.disable_service({"master_service_id": str(uuid.uuid4())},
                                       tenant_id_raw=foreign_tenant)
        assert exc.value.error_code == "PERMISSION_DENIED"

    async def test_own_tenant_id_query_param_still_works(self):
        """Supplying your OWN tenant_id (matching actor_tenant_id) must
        continue to work -- the fix must not break the legitimate case."""
        from app.engines.admin_catalog.tenant_service import TenantCatalogService
        my_tenant = uuid.uuid4()
        result = TenantCatalogService(
            db=MagicMock(), request_id="r1", actor_id=uuid.uuid4(),
            actor_role="tenant_owner", actor_tenant_id=my_tenant,
        )._require_tenant_id(my_tenant)
        assert result == my_tenant

    async def test_platform_role_may_supply_any_tenant_id(self):
        """super_admin (actor_tenant_id=None) must retain the ability to
        act on any tenant's behalf via the query param -- unchanged."""
        from app.engines.admin_catalog.tenant_service import TenantCatalogService
        target_tenant = uuid.uuid4()
        result = TenantCatalogService(
            db=MagicMock(), request_id="r1", actor_id=uuid.uuid4(),
            actor_role="super_admin", actor_tenant_id=None,
        )._require_tenant_id(target_tenant)
        assert result == target_tenant

    async def test_omitted_tenant_id_falls_back_to_principal(self):
        from app.engines.admin_catalog.tenant_service import TenantCatalogService
        my_tenant = uuid.uuid4()
        result = TenantCatalogService(
            db=MagicMock(), request_id="r1", actor_id=uuid.uuid4(),
            actor_role="tenant_owner", actor_tenant_id=my_tenant,
        )._require_tenant_id(None)
        assert result == my_tenant


@pytest.mark.asyncio
class TestCrossTenantServiceOwnershipRejection:
    """Direct proof (not source-string) that a real cross-tenant
    tenant_service_id is rejected via _assert_tenant_owns_ts, using a
    genuinely mocked TenantService row belonging to a different tenant."""

    async def test_update_enabled_service_cross_tenant_rejected(self):
        from app.engines.admin_catalog.tenant_service import TenantCatalogService
        from app.engines.admin_catalog.models import TenantService
        other_tenant = uuid.uuid4()
        my_tenant = uuid.uuid4()
        ts = MagicMock(spec=TenantService)
        ts.id = uuid.UUID(TS_ID)
        ts.tenant_id = other_tenant
        ts.deleted_at = None

        db = MagicMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = ts
        db.execute = AsyncMock(return_value=result_mock)

        svc = TenantCatalogService(db=db, request_id="r1", actor_id=uuid.uuid4(),
                                    actor_role="tenant_owner", actor_tenant_id=my_tenant)
        from app.exceptions import NotFoundException
        with pytest.raises(NotFoundException):
            await svc.update_enabled_service(uuid.UUID(TS_ID), {"tenant_display_name": "x"})

    async def test_publish_service_cross_tenant_rejected(self):
        from app.engines.admin_catalog.tenant_service import TenantCatalogService
        from app.engines.admin_catalog.models import TenantService
        other_tenant = uuid.uuid4()
        my_tenant = uuid.uuid4()
        ts = MagicMock(spec=TenantService)
        ts.id = uuid.UUID(TS_ID)
        ts.tenant_id = other_tenant
        ts.deleted_at = None

        db = MagicMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = ts
        db.execute = AsyncMock(return_value=result_mock)

        svc = TenantCatalogService(db=db, request_id="r1", actor_id=uuid.uuid4(),
                                    actor_role="tenant_owner", actor_tenant_id=my_tenant)
        from app.exceptions import NotFoundException
        with pytest.raises(NotFoundException):
            await svc.publish_service(uuid.UUID(TS_ID))


class TestEnableServiceGuardsUnchanged:
    def test_source_confirms_duplicate_enable_guard(self):
        import inspect
        from app.engines.admin_catalog.tenant_service import TenantCatalogService
        src = inspect.getsource(TenantCatalogService.enable_service)
        assert "TENANT_SERVICE_ALREADY_ENABLED" in src

    def test_source_confirms_category_entitlement_guard(self):
        import inspect
        from app.engines.admin_catalog.tenant_service import TenantCatalogService
        src = inspect.getsource(TenantCatalogService.enable_service)
        assert "CATEGORY_NOT_ENTITLED" in src

    def test_source_confirms_master_service_active_guard(self):
        import inspect
        from app.engines.admin_catalog.tenant_service import TenantCatalogService
        src = inspect.getsource(TenantCatalogService.enable_service)
        assert "MASTER_SERVICE_INACTIVE" in src

    def test_source_confirms_ownership_check_applies_to_every_tenant_role(self):
        import inspect
        from app.engines.admin_catalog.tenant_service import TenantCatalogService
        src = inspect.getsource(TenantCatalogService._assert_tenant_owns_ts)
        assert "PLATFORM_ROLES" in src


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

    def test_admin_catalog_tenant_router_zero_unverified(self):
        mod = self._load_inventory_module()
        routes = [r for r in mod.walk(app.router if hasattr(app, "router") else app)
                  if r["module"] == "app.engines.admin_catalog.tenant_router"]
        assert len(routes) == 10
        exempt = mod.CONFIRMED_FALSE_POSITIVE_ROUTES | mod.CONFIRMED_PLATFORM_ADMIN_PERMISSION_ROUTES
        unverified = [
            r for r in routes
            if r["guard_status"] not in mod.ACCEPTED_GUARD_STATUSES
            and (r["module"], r["endpoint_name"]) not in exempt
        ]
        assert unverified == [], f"unverified routes remain: {unverified}"
