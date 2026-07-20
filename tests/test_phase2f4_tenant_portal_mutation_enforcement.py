"""Phase 2A Slice 2F-4 — tenant_engine.portal_router mutation enforcement.

Covers the 10 mutation endpoints newly guarded by require_tenant_owner_mutation
(role + access-scope aware), reusing the exact composed dependency built in
Slice 2F-2 for provider_portal.router -- no new authorization framework.

All 10 endpoints already had real tenant/object ownership and role-escalation
protection at the service layer (AdminTenantService._load_tenant_user/
_load_tenant_staff scope by tenant_id; AuthService._can_admin_manage_user
rejects cross-tenant targets and tenant_owner-managing-super_admin) -- this
slice closes the ONE real gap: no access-scope enforcement, so a read-only-
scoped tenant_owner could previously lock/unlock/deactivate/suspend staff and
force-revoke sessions.

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


GUARDED_MUTATION_ENDPOINTS = [
    ("PATCH", "/v1/tenant/profile", {"phone": "1234567890"}),
    ("PATCH", "/v1/tenant/settings", {}),
    ("POST", "/v1/tenant/users", {"name": "Test", "email": "u@example.invalid", "role": "tenant_manager"}),
    ("POST", "/v1/tenant/users/{id}/suspend", None),
    ("POST", "/v1/tenant/staff", {"name": "Test Staff", "email": "s@example.invalid"}),
    ("POST", "/v1/tenant/staff/{id}/deactivate", None),
    ("PATCH", "/v1/tenant/staff/{id}/photo", {"photo_url": "http://example.invalid/x.png"}),
    ("POST", "/v1/tenant/staff/{id}/lock", {"reason": "test"}),
    ("POST", "/v1/tenant/staff/{id}/unlock", {"reason": "test"}),
    ("POST", "/v1/tenant/staff/{id}/sessions/revoke-all", {"reason": "test"}),
]
assert len(GUARDED_MUTATION_ENDPOINTS) == 10


async def _call(client, method, path_tmpl, body):
    path = path_tmpl.format(id=str(uuid.uuid4()))
    kwargs = {"headers": {"Authorization": "Bearer x"}}
    if body is not None:
        kwargs["json"] = body
    return await client.request(method, path, **kwargs)


@pytest.mark.asyncio
class TestReadOnlyDeniedAcrossAllGuardedEndpoints:
    """Workstream 11: read-only-scoped tenant_owner rejected at all 10
    endpoints, even with an explicit permission_overrides grant."""

    @pytest.mark.parametrize("method,path_tmpl,body", GUARDED_MUTATION_ENDPOINTS)
    async def test_readonly_scope_rejected_even_with_permission_grant(self, method, path_tmpl, body):
        tid = str(uuid.uuid4())
        readonly = _user("tenant_owner", tenant_id=tid, access_scope="customer_support_limited",
                          permission_overrides={"tenant:staff:manage": True})
        _override(readonly)
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                r = await _call(client, method, path_tmpl, body)
            assert r.status_code == 403, f"{method} {path_tmpl}: expected 403, got {r.status_code}: {r.text}"
            assert r.json()["error_code"] == "PERMISSION_DENIED"
        finally:
            _clear()


@pytest.mark.asyncio
class TestAuthorizedOwnerClearsAuthLayer:
    """Workstream 11: authorized tenant_owner clears the auth layer for all
    10 endpoints (business/state validation against the mocked DB is a
    separate, expected concern -- not 401/403)."""

    @pytest.mark.parametrize("method,path_tmpl,body", GUARDED_MUTATION_ENDPOINTS)
    async def test_owner_not_rejected_at_auth_layer(self, method, path_tmpl, body):
        tid = str(uuid.uuid4())
        owner = _user("tenant_owner", tenant_id=tid)
        _override(owner)
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                try:
                    r = await _call(client, method, path_tmpl, body)
                except TypeError as e:
                    assert "MagicMock" in str(e)
                    return
            assert r.status_code not in (401, 403), f"{method} {path_tmpl}: got {r.status_code}: {r.text}"
        finally:
            _clear()

    async def test_unauthenticated_rejected_401(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            r = await client.patch("/v1/tenant/settings", json={})
        assert r.status_code == 401, r.text

    async def test_super_admin_exempt_from_readonly_scope_check(self):
        tid = str(uuid.uuid4())
        admin = _user("super_admin", tenant_id=tid, access_scope="customer_support_limited")
        _override(admin)
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                r = await client.patch("/v1/tenant/settings", json={}, headers={"Authorization": "Bearer x"})
            assert r.status_code != 403, f"super_admin must be exempt, got {r.text}"
        finally:
            _clear()


@pytest.mark.asyncio
class TestUnauthorizedRoleRejected:
    """Workstream 11: staff/technician/customer (not tenant_owner/super_admin)
    are rejected -- no staff delegation exists for these 10 endpoints today
    (require_tenant_owner's underlying role check excludes them), matching
    provider_portal.router's precedent."""

    @pytest.mark.parametrize("role", ["staff", "technician", "customer"])
    async def test_non_owner_role_rejected(self, role):
        tid = str(uuid.uuid4())
        u = _user(role, tenant_id=tid)
        _override(u)
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                r = await client.patch("/v1/tenant/settings", json={}, headers={"Authorization": "Bearer x"})
            assert r.status_code == 403, f"role={role} must be rejected, got {r.status_code}: {r.text}"
        finally:
            _clear()


class TestReadsUnaffected:
    """Workstream 12: the 2 GET endpoints (staff_login_history,
    staff_security_status) that also used require_tenant_owner were NOT
    touched this slice -- confirmed via source inspection, since reads
    don't need the access-scope guard (a read-only-scoped owner should
    still be able to view security status/login history)."""

    def test_read_endpoints_still_use_plain_require_tenant_owner(self):
        import inspect
        from app.engines.tenant_engine import portal_router as r
        for fn_name in ("staff_login_history", "staff_security_status"):
            src = inspect.getsource(getattr(r, fn_name))
            assert "Depends(require_tenant_owner)" in src
            assert "require_tenant_owner_mutation" not in src


class TestAlternateAdminRouteUnaffected:
    """Workstream 8: tenant_engine.admin_router exposes the SAME capabilities
    (create_user/suspend_user/create_staff/deactivate_staff) via
    AdminTenantService, but gated by require_super_admin -- a stronger,
    platform-only route, not a bypass. Confirmed unchanged this slice."""

    def test_admin_router_create_user_still_super_admin_gated(self):
        import inspect
        from app.engines.tenant_engine import admin_router as r
        src = inspect.getsource(r.create_user)
        assert "require_super_admin" in src


@pytest.mark.asyncio
class TestServiceLayerOwnershipUnchanged:
    """Workstream 9: confirms (without re-implementing) that
    AdminTenantService._load_tenant_user/_load_tenant_staff still filter by
    tenant_id, and AuthService._can_admin_manage_user still rejects
    cross-tenant targets and tenant_owner-managing-super_admin -- these
    mechanisms were read and confirmed correct, not modified this slice."""

    def test_load_tenant_user_filters_by_tenant_id(self):
        import inspect
        from app.engines.tenant_engine.admin_service import AdminTenantService
        src = inspect.getsource(AdminTenantService._load_tenant_user)
        assert "User.tenant_id == tenant_id" in src

    def test_load_tenant_staff_filters_by_tenant_id(self):
        import inspect
        from app.engines.tenant_engine.admin_service import AdminTenantService
        src = inspect.getsource(AdminTenantService._load_tenant_staff)
        assert "User.tenant_id == tenant_id" in src

    def test_can_admin_manage_user_rejects_cross_tenant_and_super_admin_target(self):
        import inspect
        from app.engines.auth.service import AuthService
        src = inspect.getsource(AuthService._can_admin_manage_user)
        assert "target.tenant_id) != admin.tenant_id" in src
        assert 'target.role == "super_admin"' in src

    def test_revoke_all_user_sessions_does_db_and_redis(self):
        import inspect
        from app.engines.auth.service import AuthService
        src = inspect.getsource(AuthService._revoke_all_user_sessions)
        assert "revoked_at = utcnow()" in src
        assert "serviceos:session:revoked:" in src


@pytest.mark.asyncio
class TestLockUnlockRevokeCrashFixed:
    """Phase 2A Slice 2F-4, real bug found while applying this slice's guard:
    lock_staff/unlock_staff/revoke_staff_sessions (and the 2 GET reads
    staff_login_history/staff_security_status) all constructed
    `AuthService(db=db, request_id=..., actor_id=...)` -- but
    AuthService.__init__ never accepted an `actor_id` keyword argument
    (confirmed: only db, request_id, ip_address). This meant all 5
    endpoints crashed with a hard 500 TypeError on every real call,
    regardless of authorization -- discovered only because this slice's
    guard-clearing test reached far enough into the handler to hit it.
    Fixed by removing the invalid kwarg (AuthService's lock_user/unlock_user/
    admin_revoke_all_sessions/get_audit_log/get_full_security_status methods
    all take `admin`/target explicitly as call arguments -- they never used
    self.actor_id in the first place)."""

    async def test_lock_staff_no_longer_crashes_on_construction(self):
        tid = str(uuid.uuid4())
        owner = _user("tenant_owner", tenant_id=tid)
        _override(owner)
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                r = await client.post(f"/v1/tenant/staff/{uuid.uuid4()}/lock", json={"reason": "test"},
                                       headers={"Authorization": "Bearer x"})
            # Must not be a 500 TypeError from AuthService construction --
            # whatever downstream response occurs (200, 404-equivalent via
            # embedded error, etc.) is fine; the crash itself is the bug.
            assert r.status_code != 500, r.text
        finally:
            _clear()

    def test_no_invalid_actor_id_kwarg_remains_in_source(self):
        import inspect
        from app.engines.tenant_engine import portal_router as r
        src = inspect.getsource(r)
        assert "actor_id=uuid.UUID(user.user_id) if user.user_id else None)" not in src, (
            "portal_router.py must not pass actor_id to AuthService() -- "
            "that keyword argument does not exist on AuthService.__init__"
        )


@pytest.mark.asyncio
class TestAdminTenantServiceDeactivateStaffSessionRevocation:
    """Workstream 8/9: tenant_engine.portal_router's deactivate_staff
    (AdminTenantService.deactivate_staff) previously never revoked
    sessions, unlike the frontend-canonical AuthService.deactivate_staff
    (/v1/auth/staff/{id}/deactivate, fixed in Slice 2F-1) -- a directly-
    connected weaker alternate route for the same capability on the same
    User table. Fixed with the identical DB+Redis pattern."""

    async def test_deactivate_staff_revokes_db_and_redis_sessions(self):
        from unittest.mock import AsyncMock, MagicMock, patch
        from app.engines.tenant_engine.admin_service import AdminTenantService

        tenant_id = uuid.uuid4()
        staff_id = uuid.uuid4()
        staff_row = MagicMock(id=staff_id, tenant_id=tenant_id, role="staff", is_active=True)
        session_id_1, session_id_2 = uuid.uuid4(), uuid.uuid4()

        db = AsyncMock()

        def _scalar(value):
            r = MagicMock()
            r.scalar_one_or_none = MagicMock(return_value=value)
            return r

        def _rows(values):
            r = MagicMock()
            r.__iter__ = lambda self: iter([(v,) for v in values])
            return r

        db.execute = AsyncMock(side_effect=[
            _scalar(staff_row),                          # _load_tenant_staff
            _rows([session_id_1, session_id_2]),          # active sessions lookup
            MagicMock(),                                    # UPDATE user_sessions
        ])

        with patch("app.redis_client.get_redis") as mock_get_redis:
            redis_mock = AsyncMock()
            mock_get_redis.return_value = redis_mock
            svc = AdminTenantService(db=db, request_id="test", actor_id=uuid.uuid4(), actor_role="tenant_owner")
            with patch.object(svc, "_audit", new=AsyncMock()):
                result = await svc.deactivate_staff(tenant_id, staff_id)

        assert result["sessions_revoked"] == 2
        assert redis_mock.setex.call_count == 2
        called_keys = {call.args[0] for call in redis_mock.setex.call_args_list}
        assert called_keys == {
            f"serviceos:session:revoked:{session_id_1}",
            f"serviceos:session:revoked:{session_id_2}",
        }

    def test_source_confirms_db_and_redis_revocation(self):
        import inspect
        from app.engines.tenant_engine.admin_service import AdminTenantService
        src = inspect.getsource(AdminTenantService.deactivate_staff)
        assert "revoked_at=utcnow()" in src or "revoked_at=utcnow" in src
        assert "serviceos:session:revoked:" in src
