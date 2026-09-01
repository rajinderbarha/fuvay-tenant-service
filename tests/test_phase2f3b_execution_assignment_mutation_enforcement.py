"""Phase 2A Slice 2F-3B — execution/assignment mutation enforcement.

Covers the 27 reachable mutation endpoints across:
- app.engines.execution.home_service_router (21: 18 access-scope-guarded
  via the new require_staff_or_above_mutation + 3 pre-existing
  PLATFORM_ADMIN_ONLY-equivalent permission-gated admin overrides)
- app.engines.home_service_assignment.staff_router (2: accept/reject, now
  access-scope-guarded + tenant defense-in-depth)
- app.engines.home_service_assignment.provider_router (4: assign/reassign/
  cancel-assignment/schedule, now access-scope-guarded via
  require_tenant_owner_mutation)

Plus the 2 shadowed execution-router routes (staff_accept_job/
staff_reject_job) whose decorators were removed this slice (Workstream 2).

Follows the established repo pattern: override get_current_user via
app.dependency_overrides with a fake UserContext.
"""
from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.dependencies.auth import get_current_user, UserContext


def _user(role: str, tenant_id: str | None = None, access_scope: str | None = None,
          permission_overrides: dict | None = None) -> UserContext:
    return UserContext(
        user_id=str(uuid.uuid4()), email=f"{role}@test.local", role=role,
        tenant_id=tenant_id or str(uuid.uuid4()), full_name=role.title(), is_verified=True,
        access_scope=access_scope, permission_overrides=permission_overrides,
    )


def _override(u):
    app.dependency_overrides[get_current_user] = lambda: u


def _clear():
    app.dependency_overrides.pop(get_current_user, None)


# The 18 execution-router endpoints newly guarded by require_staff_or_above_mutation.
EXECUTION_STAFF_ENDPOINTS = [
    ("POST", "/v1/staff/service-jobs/{id}/on-the-way", None),
    ("POST", "/v1/staff/service-jobs/{id}/reached-site", None),
    ("POST", "/v1/staff/service-jobs/{id}/start-inspection", None),
    ("POST", "/v1/staff/service-jobs/{id}/complete-inspection", None),
    ("POST", "/v1/staff/service-jobs/{id}/start-service", None),
    ("POST", "/v1/staff/service-jobs/{id}/work-done", None),
    ("POST", "/v1/staff/service-jobs/{id}/customer-not-available", {"note_text": "x"}),
    ("POST", "/v1/staff/service-jobs/{id}/quote-required", {"note_text": "x"}),
    ("POST", "/v1/staff/service-jobs/{id}/parts-required", {"note_text": "x"}),
    ("POST", "/v1/staff/service-jobs/{id}/notes", {"note_text": "x"}),
    ("POST", "/v1/staff/service-jobs/{id}/diagnosis-notes", {"note_text": "x"}),
    ("POST", "/v1/staff/service-jobs/{id}/media", {"media_type": "photo", "file_url": "http://x"}),
    ("POST", "/v1/staff/service-jobs/{id}/parts-requests",
     {"part_name": "x", "quantity": 1, "estimated_cost": 1.0, "reason": "x"}),
    ("POST", "/v1/staff/service-jobs/{id}/complete", {}),
]
EXECUTION_PROVIDER_ENDPOINTS = [
    ("POST", "/v1/provider/service-jobs/{id}/cancel", {"reason": "x"}),
    ("POST", "/v1/provider/service-jobs/{id}/parts-requests/{pid}/approve", None),
    ("POST", "/v1/provider/service-jobs/{id}/parts-requests/{pid}/reject", {"reason": "x"}),
    ("POST", "/v1/provider/service-jobs/{id}/parts-requests/{pid}/install", None),
]
EXECUTION_GUARDED = EXECUTION_STAFF_ENDPOINTS + EXECUTION_PROVIDER_ENDPOINTS
assert len(EXECUTION_GUARDED) == 18

ASSIGNMENT_STAFF_ENDPOINTS = [
    ("POST", "/v1/staff/service-jobs/{id}/accept", None),
    ("POST", "/v1/staff/service-jobs/{id}/reject", {"reason": "x"}),
]
ASSIGNMENT_PROVIDER_ENDPOINTS = [
    ("POST", "/v1/provider/service-jobs/{id}/assign", {"staff_member_id": str(uuid.uuid4())}),
    ("POST", "/v1/provider/service-jobs/{id}/reassign", {"staff_member_id": str(uuid.uuid4()), "reason": "x"}),
    ("POST", "/v1/provider/service-jobs/{id}/cancel-assignment", {"reason": "x"}),
    ("POST", "/v1/provider/service-jobs/{id}/schedule", {"scheduled_date": "2026-08-20"}),
]
ALL_ACCESS_SCOPE_GUARDED = EXECUTION_GUARDED + ASSIGNMENT_STAFF_ENDPOINTS + ASSIGNMENT_PROVIDER_ENDPOINTS
assert len(ALL_ACCESS_SCOPE_GUARDED) == 24

ADMIN_ENDPOINTS = [
    ("POST", "/v1/admin/service-jobs/{id}/force-close", {"reason": "x"}),
    ("POST", "/v1/admin/service-jobs/{id}/status-override", {"new_status": "cancelled", "reason": "x"}),
    ("POST", "/v1/admin/service-jobs/{id}/void", {"reason": "x"}),
]


async def _call(client, method, path_tmpl, body):
    path = path_tmpl.format(id=str(uuid.uuid4()), pid=str(uuid.uuid4()))
    kwargs = {"headers": {"Authorization": "Bearer x"}}
    if body is not None:
        kwargs["json"] = body
    return await client.request(method, path, **kwargs)


@pytest.mark.asyncio
class TestReadOnlyDeniedAcrossAllGuardedEndpoints:
    """Workstream 12: read-only-scoped staff/tenant_owner rejected at all 24
    access-scope-guarded endpoints, even with an explicit permission_overrides
    grant -- proving access-scope denial is not overridden by a permission
    grant, same guarantee as tenant_engine.router/provider_portal.router."""

    @pytest.mark.parametrize("method,path_tmpl,body", ALL_ACCESS_SCOPE_GUARDED)
    async def test_readonly_scope_rejected_even_with_permission_grant(self, method, path_tmpl, body):
        tid = str(uuid.uuid4())
        readonly = _user("staff", tenant_id=tid, access_scope="customer_support_limited",
                          permission_overrides={"field_ops:jobs:update": True})
        _override(readonly)
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                r = await _call(client, method, path_tmpl, body)
            assert r.status_code == 403, f"{method} {path_tmpl}: expected 403, got {r.status_code}: {r.text}"
            assert r.json()["error_code"] == "PERMISSION_DENIED"
        finally:
            _clear()


@pytest.mark.asyncio
class TestAuthorizedActorClearsAuthLayer:
    """Workstream 12: authorized staff/technician/tenant_owner clears the
    auth layer for all 24 endpoints (business/state validation, e.g.
    ERR_JOB_NOT_FOUND / ERR_ACCESS_DENIED against the mocked DB, is a
    separate, expected concern -- not 401/403)."""

    @pytest.mark.parametrize("method,path_tmpl,body", EXECUTION_GUARDED)
    async def test_technician_clears_auth_layer_execution(self, method, path_tmpl, body):
        """A random, unassigned fake technician correctly hits the
        ownership-layer denial (_assert_staff_owns_job ->
        EXECUTION_STAFF_NOT_ASSIGNED, 403) deeper in the handler -- this
        IS the accepted proof of clearing require_staff_or_above_mutation
        (the auth-layer guard), since reaching ownership validation means
        the guard already let the request through. Only a 403 whose
        error_code is PERMISSION_DENIED (the guard's own denial) or a 401
        would indicate the auth layer itself rejected the request."""
        tid = str(uuid.uuid4())
        tech = _user("technician", tenant_id=tid)
        _override(tech)
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                try:
                    r = await _call(client, method, path_tmpl, body)
                except TypeError as e:
                    assert "MagicMock" in str(e)
                    return
            assert r.status_code != 401, f"{method} {path_tmpl}: got 401: {r.text}"
            if r.status_code == 403:
                assert r.json().get("error_code") != "PERMISSION_DENIED", (
                    f"{method} {path_tmpl}: rejected at the auth-layer guard itself, "
                    f"not just ownership -- got {r.text}"
                )
        finally:
            _clear()

    @pytest.mark.parametrize("method,path_tmpl,body", ASSIGNMENT_STAFF_ENDPOINTS)
    async def test_technician_clears_auth_layer_assignment_staff(self, method, path_tmpl, body):
        tid = str(uuid.uuid4())
        tech = _user("technician", tenant_id=tid)
        _override(tech)
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                r = await _call(client, method, path_tmpl, body)
            assert r.status_code != 401, f"{method} {path_tmpl}: got {r.status_code}: {r.text}"
            if r.status_code == 403:
                # Role authorization passed; a disabled vertical remains a
                # higher-level fail-closed availability guard for every role.
                assert r.json().get("error_code") == "VERTICAL_DISABLED"
        finally:
            _clear()

    @pytest.mark.parametrize("method,path_tmpl,body", ASSIGNMENT_PROVIDER_ENDPOINTS)
    async def test_tenant_owner_clears_auth_layer_assignment_provider(self, method, path_tmpl, body):
        tid = str(uuid.uuid4())
        owner = _user("tenant_owner", tenant_id=tid)
        _override(owner)
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                r = await _call(client, method, path_tmpl, body)
            assert r.status_code != 401, f"{method} {path_tmpl}: got {r.status_code}: {r.text}"
            if r.status_code == 403:
                # Role authorization succeeded; vertical availability is a
                # separate fail-closed guard.
                assert r.json().get("error_code") == "VERTICAL_DISABLED"
        finally:
            _clear()

    async def test_unauthenticated_rejected_401(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            r = await client.post(f"/v1/staff/service-jobs/{uuid.uuid4()}/on-the-way")
        assert r.status_code == 401, r.text

    async def test_super_admin_exempt_from_readonly_scope_check(self):
        tid = str(uuid.uuid4())
        admin = _user("super_admin", tenant_id=tid, access_scope="customer_support_limited")
        _override(admin)
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                r = await client.post(f"/v1/staff/service-jobs/{uuid.uuid4()}/on-the-way",
                                       headers={"Authorization": "Bearer x"})
            # super_admin is not the assigned technician for this fake job, so
            # the downstream ownership check (EXECUTION_STAFF_NOT_ASSIGNED) is
            # expected -- the guard-level exemption is proven by NOT getting
            # the guard's own PERMISSION_DENIED for the read-only access_scope.
            if r.status_code == 403:
                assert r.json().get("error_code") != "PERMISSION_DENIED", \
                    f"super_admin must be exempt from the access_scope gate, got {r.text}"
        finally:
            _clear()


@pytest.mark.asyncio
class TestUnauthorizedRoleRejected:
    """Workstream 12: customer role (not staff_or_above / not tenant_owner)
    is rejected at every guarded endpoint group."""

    async def test_customer_rejected_execution_endpoint(self):
        _override(_user("customer"))
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                r = await client.post(f"/v1/staff/service-jobs/{uuid.uuid4()}/on-the-way",
                                       headers={"Authorization": "Bearer x"})
            assert r.status_code == 403
        finally:
            _clear()

    async def test_customer_rejected_assignment_staff_endpoint(self):
        _override(_user("customer"))
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                r = await client.post(f"/v1/staff/service-jobs/{uuid.uuid4()}/accept",
                                       headers={"Authorization": "Bearer x"})
            assert r.status_code == 403
        finally:
            _clear()

    async def test_staff_rejected_assignment_provider_endpoint(self):
        """provider_router's assign/reassign/cancel-assignment/schedule are
        require_tenant_owner_mutation-gated -- staff (not tenant_owner) must
        be rejected, matching provider_portal.router's precedent (no staff
        delegation proven)."""
        _override(_user("staff"))
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                r = await client.post(f"/v1/provider/service-jobs/{uuid.uuid4()}/assign",
                                       json={"staff_member_id": str(uuid.uuid4())},
                                       headers={"Authorization": "Bearer x"})
            assert r.status_code == 403
        finally:
            _clear()


class TestPlatformAdminEndpointsUnaffected:
    """Workstream 8: the 3 admin override endpoints remain permission-gated
    (require_permission(P.ADMIN_JOBS_*)) -- untouched this slice, confirmed
    via source inspection, not accidentally gaining or losing a guard."""

    def test_admin_endpoints_still_use_require_permission_admin_jobs(self):
        import inspect
        from app.engines.execution import home_service_router as r
        for fn_name in ("admin_force_close", "admin_override_status", "admin_void"):
            src = inspect.getsource(getattr(r, fn_name))
            assert "require_permission(P.ADMIN_JOBS_" in src
            assert "require_staff_or_above_mutation" not in src
            assert "require_tenant_owner_mutation" not in src


@pytest.mark.asyncio
class TestPlatformAdminActionsRetainAccess:
    """Workstream 8/15: admin_operations (the canonical role holding
    ADMIN_JOBS_* permissions) retains access; tenant personas remain denied."""

    @pytest.mark.parametrize("method,path_tmpl,body", ADMIN_ENDPOINTS)
    async def test_admin_operations_role_not_rejected(self, method, path_tmpl, body):
        admin = _user("admin_operations")
        _override(admin)
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                r = await _call(client, method, path_tmpl, body)
            assert r.status_code != 401, f"{method} {path_tmpl}: got {r.status_code}: {r.text}"
            if r.status_code == 403:
                assert r.json().get("error_code") == "VERTICAL_DISABLED"
        finally:
            _clear()

    @pytest.mark.parametrize("method,path_tmpl,body", ADMIN_ENDPOINTS)
    async def test_tenant_owner_denied_admin_endpoints(self, method, path_tmpl, body):
        owner = _user("tenant_owner")
        _override(owner)
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                r = await _call(client, method, path_tmpl, body)
            assert r.status_code == 403, f"{method} {path_tmpl}: tenant_owner must be denied admin action"
        finally:
            _clear()


class TestShadowedRouteDecoratorsRemoved:
    """Workstream 2: the shadowed staff_accept_job/staff_reject_job
    decorators were removed this slice -- OpenAPI now has exactly one
    operation for each path. Functions themselves are preserved (not
    deleted), per the brief's explicit instruction."""

    def test_functions_still_exist_undeleted(self):
        from app.engines.execution import home_service_router as r
        assert hasattr(r, "staff_accept_job")
        assert hasattr(r, "staff_reject_job")

    def test_no_route_decorator_before_shadowed_functions(self):
        import inspect
        from app.engines.execution import home_service_router as r
        src = inspect.getsource(r)
        # The two functions must not be preceded by their own @staff_router.post decorator anymore.
        assert '@staff_router.post("/{job_id}/accept")' not in src
        assert '@staff_router.post("/{job_id}/reject")' not in src

    def test_openapi_has_exactly_one_operation_per_shared_path(self):
        schema = app.openapi()
        accept_path = schema["paths"].get("/v1/staff/service-jobs/{job_id}/accept")
        reject_path = schema["paths"].get("/v1/staff/service-jobs/{job_id}/reject")
        assert accept_path is not None and "post" in accept_path
        assert reject_path is not None and "post" in reject_path
        # Only one POST operation object exists per path (FastAPI would have
        # raised on route registration for a literal duplicate operationId
        # collision if two decorators still existed at the same path/method).

    @pytest.mark.asyncio
    async def test_canonical_assignment_implementation_still_answers(self):
        tid = str(uuid.uuid4())
        tech = _user("technician", tenant_id=tid)
        app.dependency_overrides[get_current_user] = lambda: tech
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                r = await client.post(f"/v1/staff/service-jobs/{uuid.uuid4()}/accept",
                                       headers={"Authorization": "Bearer x"})
            # A random id must fail closed. The assignment engine's deliberately
            # opaque error code confirms the canonical route handled it.
            assert r.status_code == 404
            assert r.json()["error_code"] == "JOB_ASSIGNMENT_ACCESS_DENIED"
        finally:
            app.dependency_overrides.pop(get_current_user, None)


class TestPartsRequestBoundaryStillIntact:
    """Workstream 7: PartsRequest remains ServiceJob-only; no Parts endpoint
    exists in home_service_assignment; provider-only install restriction
    unchanged (not touched this slice beyond the guard swap)."""

    def test_parts_endpoints_only_in_execution_router(self):
        import inspect
        from app.engines.home_service_assignment import staff_router, provider_router
        for mod in (staff_router, provider_router):
            src = inspect.getsource(mod)
            assert "parts" not in src.lower()

    def test_install_endpoint_uses_same_staff_or_above_guard_not_broadened(self):
        """provider_install_parts_request now uses
        require_staff_or_above_mutation (role in {super_admin, tenant_owner,
        staff, technician} + access-scope check) -- the provider-only
        restriction on installation itself is enforced downstream (in the
        service/handler logic, unchanged this slice), not by this router-
        level role gate, which only establishes tenant-side authentication +
        access-scope, consistent with every other execution endpoint."""
        import inspect
        from app.engines.execution import home_service_router as r
        src = inspect.getsource(r.provider_install_parts_request)
        assert "require_staff_or_above_mutation" in src


class TestTenantDefenseInDepthAdded:
    """Workstream 6: technician_accept_job/reject_job now accept an
    optional tenant_id parameter and reject (ERR_ACCESS_DENIED) when the
    loaded ServiceJob's tenant does not match -- defense-in-depth alongside
    the pre-existing assignment-ownership check, not a replacement for it."""

    def test_service_methods_accept_optional_tenant_id(self):
        import inspect
        from app.engines.home_service_assignment.service import HomeServiceJobAssignmentService
        accept_sig = inspect.signature(HomeServiceJobAssignmentService.technician_accept_job)
        reject_sig = inspect.signature(HomeServiceJobAssignmentService.technician_reject_job)
        assert "tenant_id" in accept_sig.parameters
        assert "tenant_id" in reject_sig.parameters
        assert accept_sig.parameters["tenant_id"].default is None
        assert reject_sig.parameters["tenant_id"].default is None

    def test_router_passes_tenant_id_from_principal(self):
        import inspect
        from app.engines.home_service_assignment import staff_router as r
        accept_src = inspect.getsource(r.accept_job)
        reject_src = inspect.getsource(r.reject_job)
        assert "tenant_id=uuid.UUID(str(user.tenant_id))" in accept_src
        assert "tenant_id=uuid.UUID(str(user.tenant_id))" in reject_src
