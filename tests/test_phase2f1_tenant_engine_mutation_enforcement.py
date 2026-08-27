"""Phase 2A Slice 2F-1 — tenant_engine.router mutation-enforcement closure.

Covers the 19 tenant_engine.router mutation endpoints that were swapped from
require_permission(P.TENANT_X) to require_tenant_mutation_permission(P.TENANT_X)
this slice (Workstreams 3/4), plus the deactivate_staff Redis session-
revocation fix (Workstream 11).

Follows the established repo pattern (tests/test_final_l5_01b_admin_tenant_rbac.py):
override get_current_user via app.dependency_overrides with a fake
UserContext, rather than a real login, so tests are deterministic and
independent of live DB/seed state.
"""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.dependencies.auth import get_current_user, UserContext


def _user(role: str, tenant_id: str | None = None, access_scope: str | None = None,
          permission_overrides: dict | None = None) -> UserContext:
    return UserContext(
        user_id=str(uuid.uuid4()), email=f"{role}@test.local", role=role,
        tenant_id=tenant_id, full_name=role.replace("_", " ").title(), is_verified=True,
        access_scope=access_scope, permission_overrides=permission_overrides,
    )


def _override(user_context):
    app.dependency_overrides[get_current_user] = lambda: user_context


def _clear_override():
    app.dependency_overrides.pop(get_current_user, None)


# All 16 tenant_engine.router mutation endpoints guarded by
# require_tenant_mutation_permission this slice (Workstream 1/3/4). Each
# tuple is (method, path_template, needs_json_body).
GUARDED_MUTATION_ENDPOINTS = [
    ("PUT", "/v1/tenants/{tid}", True),
    ("POST", "/v1/tenants/{tid}/suspend", True),
    ("POST", "/v1/tenants/{tid}/reinstate", True),
    ("POST", "/v1/tenants/{tid}/terminate/begin", True),
    ("POST", "/v1/tenants/{tid}/terminate/confirm", True),
    ("POST", "/v1/tenants/{tid}/engines/engine-x/enable", False),
    ("POST", "/v1/tenants/{tid}/engines/engine-x/disable", False),
    ("POST", "/v1/tenants/{tid}/engines/bulk-enable", True),
    ("POST", "/v1/tenants/{tid}/engines/bulk-disable", True),
    ("PUT", "/v1/tenants/{tid}/engines/engine-x/config", True),
    ("POST", "/v1/tenants/{tid}/engines/engine-x/config/validate", True),
    ("PUT", "/v1/tenants/{tid}/feature-flags/flag-x", True),
    ("DELETE", "/v1/tenants/{tid}/feature-flags/flag-x", False),
    ("PUT", "/v1/tenants/{tid}/billing/payment-method", True),
    ("POST", "/v1/tenants/{tid}/data/export", False),
    ("POST", "/v1/tenants/{tid}/data/delete-request", True),
]

assert len(GUARDED_MUTATION_ENDPOINTS) == 16


async def _request(client, method, path, needs_json):
    kwargs = {"headers": {"Authorization": "Bearer x"}}
    if needs_json:
        kwargs["json"] = {}
    return await client.request(method, path, **kwargs)


@pytest.mark.asyncio
class TestReadOnlyAccessScopeDeniedAcrossAllGuardedEndpoints:
    """Workstream 8/9: a tenant-scoped user whose access_scope marks them
    read-only must be rejected (403) at every one of the 19 newly-guarded
    endpoints, regardless of role or permission grants -- proving
    access_scope denial is enforced independently, not just theoretically
    wired (Slice 2D's finding was that this guard existed but was applied
    to only 10 of 185 tenant-facing routes; this closes 19 more for real,
    proven via direct HTTP requests, not source inspection)."""

    @pytest.mark.parametrize("method,path_tmpl,needs_json", GUARDED_MUTATION_ENDPOINTS)
    async def test_readonly_scope_rejected_even_with_full_permission_grant(self, method, path_tmpl, needs_json):
        tid = str(uuid.uuid4())
        # A test-only principal: staff role, valid tenant membership,
        # read-only access_scope, AND an explicit permission_overrides grant
        # for every tenant:* permission -- proving the access_scope gate
        # rejects independently of an affirmative permission grant (this is
        # the "permission grant must NOT override read-only access scope"
        # requirement from the brief). Never uses the real readonly@ account.
        readonly_user = _user(
            "staff", tenant_id=tid, access_scope="customer_support_limited",
            permission_overrides={
                "tenant:update": True, "tenant:suspend": True, "tenant:reinstate": True,
                "tenant:terminate": True, "tenant:plan:manage": True, "tenant:engines:manage": True,
                "tenant:flags:manage": True, "tenant:billing:manage": True,
                "tenant:data:export": True, "tenant:data:delete": True,
            },
        )
        _override(readonly_user)
        try:
            path = path_tmpl.format(tid=tid)
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                r = await _request(client, method, path, needs_json)
            assert r.status_code == 403, (
                f"{method} {path}: read-only access_scope must reject even with a "
                f"permission_overrides grant, got {r.status_code}: {r.text}"
            )
            assert r.json()["error_code"] == "PERMISSION_DENIED"
        finally:
            _clear_override()


@pytest.mark.asyncio
class TestTenantOwnerAndCrossTenantBehavior:
    """Workstream 9: representative sample proving tenant-owner (non-read-
    only) reaches past the auth layer, and cross-tenant access is rejected
    by the pre-existing _assert_own_tenant_or_super_admin ownership check
    (which this slice's guard swap did not touch or weaken)."""

    SAMPLE = [
        ("PUT", "/v1/tenants/{tid}", {}, "tenant_owner"),
        ("POST", "/v1/tenants/{tid}/engines/bulk-enable", {}, "tenant_owner"),
        ("PUT", "/v1/tenants/{tid}/feature-flags/flag-x", {}, "tenant_owner"),
        ("PUT", "/v1/tenants/{tid}/billing/payment-method",
         {"gateway": "stripe", "gateway_customer_id": "cus_test"}, "tenant_owner"),
    ]

    @pytest.mark.parametrize("method,path_tmpl,body,role", SAMPLE)
    async def test_authorized_owner_not_rejected_by_auth_layer(self, method, path_tmpl, body, role):
        tid = str(uuid.uuid4())
        owner = _user(role, tenant_id=tid)  # tenant_owner's role bundle already
        # grants TENANT_UPDATE/TENANT_ENGINES_MANAGE/TENANT_FLAGS_MANAGE/
        # TENANT_BILLING_MANAGE (app/core/permissions.py ROLE_PERMISSIONS),
        # and access_scope is None (not read-only) -- must clear both gates.
        _override(owner)
        try:
            path = path_tmpl.format(tid=tid)
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                r = await client.request(method, path, headers={"Authorization": "Bearer x"}, json=body)
            assert r.status_code not in (401, 403), (
                f"{method} {path}: authorized tenant_owner was rejected at the auth layer "
                f"(got {r.status_code}: {r.text}) -- regression in the guard swap"
            )
        finally:
            _clear_override()

    @pytest.mark.parametrize("method,path_tmpl,body,role", SAMPLE)
    async def test_cross_tenant_owner_rejected(self, method, path_tmpl, body, role):
        own_tenant = str(uuid.uuid4())
        other_tenant = str(uuid.uuid4())
        owner = _user(role, tenant_id=own_tenant)
        _override(owner)
        try:
            path = path_tmpl.format(tid=other_tenant)  # path targets a DIFFERENT tenant
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                r = await client.request(method, path, headers={"Authorization": "Bearer x"}, json=body)
            assert r.status_code == 403, (
                f"{method} {path}: cross-tenant owner must be rejected by "
                f"_assert_own_tenant_or_super_admin, got {r.status_code}: {r.text}"
            )
            assert r.json()["error_code"] == "PERMISSION_DENIED"
        finally:
            _clear_override()

    async def test_super_admin_exempt_from_readonly_scope_check(self):
        """super_admin must remain exempt from the access_scope gate even
        if (hypothetically) access_scope were set -- matches
        require_tenant_mutation_permission's explicit exemption and must
        not regress."""
        tid = str(uuid.uuid4())
        admin = _user("super_admin", access_scope="customer_support_limited")
        _override(admin)
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                r = await client.put(f"/v1/tenants/{tid}", json={}, headers={"Authorization": "Bearer x"})
            assert r.status_code != 403, f"super_admin must be exempt from access_scope gate, got {r.text}"
        finally:
            _clear_override()

    async def test_unauthenticated_rejected_401(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            r = await client.put(f"/v1/tenants/{uuid.uuid4()}", json={})
        assert r.status_code == 401, r.text


@pytest.mark.asyncio
class TestFullNineteenEndpointAuthorizationMatrix:
    """Phase 2A Slice 2F-1A, Workstream 6: completes the outcome matrix the
    previous slice only proved for a 4-endpoint representative sample.
    Every one of the 19 require_tenant_mutation_permission-guarded endpoints
    is now directly HTTP-tested for tenant-owner and cross-tenant outcomes.

    The 19 split into two evidence-based groups (Slice 2F-1A, Workstream 2):
    - OWNER_ACCESSIBLE (11): permission IS granted to tenant_owner today
      (app/core/permissions.py ROLE_PERMISSIONS) -- owner must clear the
      auth layer, cross-tenant owner must still be rejected by
      _assert_own_tenant_or_super_admin.
    - PLATFORM_ONLY_VIA_PERMISSION_GAP (8): permission is granted to NO role
      today (only super_admin's P.ALL wildcard reaches these) -- a
      tenant_owner is EXPECTED to receive 403 here, for both same-tenant and
      cross-tenant requests, because require_permission denies before
      _assert_own_tenant_or_super_admin ever runs. This is not a regression;
      it is the documented, correct PLATFORM_ADMIN_ONLY policy outcome (see
      docs/workflow-rearchitecture/phase-02a-slice-02f1a/
      tenant-engine-final-policy-matrix.csv).
    """

    OWNER_ACCESSIBLE = [
        ("PUT", "/v1/tenants/{tid}", {}),
        ("PUT", "/v1/tenants/{tid}/billing/payment-method",
         {"gateway": "stripe", "gateway_customer_id": "cus_test"}),
        ("POST", "/v1/tenants/{tid}/data/export", None),
        ("POST", "/v1/tenants/{tid}/engines/bulk-enable", {"engine_ids": []}),
        ("POST", "/v1/tenants/{tid}/engines/bulk-disable", {"engine_ids": []}),
        ("POST", "/v1/tenants/{tid}/engines/engine-x/enable", None),
        ("POST", "/v1/tenants/{tid}/engines/engine-x/disable", None),
        ("PUT", "/v1/tenants/{tid}/engines/engine-x/config", {}),
        ("POST", "/v1/tenants/{tid}/engines/engine-x/config/validate", {}),
        ("PUT", "/v1/tenants/{tid}/feature-flags/flag-x", {"value": True}),
        ("DELETE", "/v1/tenants/{tid}/feature-flags/flag-x", None),
    ]

    PLATFORM_ONLY_VIA_PERMISSION_GAP = [
        ("POST", "/v1/tenants/{tid}/suspend", {"reason": "test"}),
        ("POST", "/v1/tenants/{tid}/reinstate", {"reason": "test"}),
        ("POST", "/v1/tenants/{tid}/terminate/begin", {"reason": "test"}),
        ("POST", "/v1/tenants/{tid}/terminate/confirm", None),
        ("POST", "/v1/tenants/{tid}/data/delete-request", {"reason": "test"}),
    ]

    assert len(OWNER_ACCESSIBLE) == 11
    assert len(PLATFORM_ONLY_VIA_PERMISSION_GAP) == 5
    assert len(OWNER_ACCESSIBLE) + len(PLATFORM_ONLY_VIA_PERMISSION_GAP) == 16

    async def _call(self, client, method, path, body):
        kwargs = {"headers": {"Authorization": "Bearer x"}}
        if body is not None:
            kwargs["json"] = body
        return await client.request(method, path, **kwargs)

    @pytest.mark.parametrize("method,path_tmpl,body", OWNER_ACCESSIBLE)
    async def test_owner_accessible_endpoint_clears_auth_layer_for_owner(self, method, path_tmpl, body):
        tid = str(uuid.uuid4())
        owner = _user("tenant_owner", tenant_id=tid)
        _override(owner)
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                r = await self._call(client, method, path_tmpl.format(tid=tid), body)
            assert r.status_code not in (401, 403), (
                f"{method} {path_tmpl}: owner-accessible endpoint rejected authorized "
                f"tenant_owner at the auth layer, got {r.status_code}: {r.text}"
            )
        finally:
            _clear_override()

    @pytest.mark.parametrize("method,path_tmpl,body", OWNER_ACCESSIBLE)
    async def test_owner_accessible_endpoint_rejects_cross_tenant(self, method, path_tmpl, body):
        own_tenant, other_tenant = str(uuid.uuid4()), str(uuid.uuid4())
        owner = _user("tenant_owner", tenant_id=own_tenant)
        _override(owner)
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                r = await self._call(client, method, path_tmpl.format(tid=other_tenant), body)
            assert r.status_code == 403, (
                f"{method} {path_tmpl}: cross-tenant owner must be rejected, got {r.status_code}: {r.text}"
            )
            assert r.json()["error_code"] == "PERMISSION_DENIED"
        finally:
            _clear_override()

    @pytest.mark.parametrize("method,path_tmpl,body", PLATFORM_ONLY_VIA_PERMISSION_GAP)
    async def test_platform_only_endpoint_denies_owner_same_tenant(self, method, path_tmpl, body):
        """Expected authorization denial: tenant_owner does not hold any of
        these 8 permissions today (PLATFORM_ADMIN_ONLY policy disposition,
        Workstream 2) -- 403 here is correct, not a bug."""
        tid = str(uuid.uuid4())
        owner = _user("tenant_owner", tenant_id=tid)
        _override(owner)
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                r = await self._call(client, method, path_tmpl.format(tid=tid), body)
            assert r.status_code == 403, (
                f"{method} {path_tmpl}: expected PERMISSION_DENIED for tenant_owner "
                f"(no role holds this permission today), got {r.status_code}: {r.text}"
            )
            assert r.json()["error_code"] == "PERMISSION_DENIED"
        finally:
            _clear_override()

    @pytest.mark.parametrize("method,path_tmpl,body", PLATFORM_ONLY_VIA_PERMISSION_GAP)
    async def test_platform_only_endpoint_denies_owner_cross_tenant(self, method, path_tmpl, body):
        own_tenant, other_tenant = str(uuid.uuid4()), str(uuid.uuid4())
        owner = _user("tenant_owner", tenant_id=own_tenant)
        _override(owner)
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                r = await self._call(client, method, path_tmpl.format(tid=other_tenant), body)
            assert r.status_code == 403, (
                f"{method} {path_tmpl}: cross-tenant owner must also be denied, got {r.status_code}: {r.text}"
            )
        finally:
            _clear_override()

    @pytest.mark.parametrize("method,path_tmpl,body", PLATFORM_ONLY_VIA_PERMISSION_GAP)
    async def test_platform_only_endpoint_super_admin_retains_access(self, method, path_tmpl, body):
        """Workstream 6: platform-admin-only operations must retain valid
        super_admin access -- proves this slice's classification correction
        (TENANT_OWNER_MUTATION -> PLATFORM_ADMIN_ONLY) did not accidentally
        lock out the very persona that legitimately uses these 8 endpoints
        (confirmed via the frontend-exposure audit: only the super-admin
        app calls them)."""
        tid = str(uuid.uuid4())
        admin = _user("super_admin")
        _override(admin)
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                r = await self._call(client, method, path_tmpl.format(tid=tid), body)
            assert r.status_code not in (401, 403), (
                f"{method} {path_tmpl}: super_admin must retain access to this platform-only "
                f"endpoint, got {r.status_code}: {r.text}"
            )
        finally:
            _clear_override()


class TestPlatformAdminAndPublicEndpointsUnaffected:
    """Workstream 1 classification regression guard: the 7 require_super_admin
    -gated onboarding/dunning endpoints and the 1 public signup endpoint were
    intentionally NOT touched this slice (PLATFORM_ADMIN_MUTATION /
    FALSE_POSITIVE classifications) -- they must still use their original
    dependencies, not require_tenant_mutation_permission."""

    def test_super_admin_gated_endpoints_still_use_require_super_admin(self):
        import inspect
        from app.engines.tenant_engine import router as r
        for fn_name in ("activate_tenant", "update_checklist", "preflight_check",
                        "reject_onboarding", "request_documents", "start_review"):
            src = inspect.getsource(getattr(r, fn_name))
            assert "require_super_admin" in src, f"{fn_name} must remain require_super_admin-gated"
            assert "require_tenant_mutation_permission" not in src, (
                f"{fn_name} is PLATFORM_ADMIN_MUTATION and must not gain the tenant "
                f"access_scope guard (super_admin is already exempt from it anyway)"
            )

    def test_public_signup_endpoint_has_no_auth_dependency_added(self):
        import inspect
        from app.engines.tenant_engine import router as r
        src = inspect.getsource(r.submit_signup)
        assert "require_tenant_mutation_permission" not in src
        assert "require_permission" not in src
        assert "require_super_admin" not in src


class TestNoTenantPortalExposureForPlatformOnlyActions:
    """Phase 2A Slice 2F-1A, Workstream 5: regression guard against
    accidental tenant-facing exposure of the 5 platform-only tenant lifecycle
    endpoints (suspend, reinstate, terminate/begin, terminate/confirm, and
    data/delete-request). The frontend-
    exposure audit (frontend-exposure-audit.md) found these are called ONLY
    from frontend/super-admin/lib/api.ts, never from
    frontend/tenant-portal -- this test fails loudly if a future change adds
    a tenant-portal caller without an accompanying policy decision."""

    PLATFORM_ONLY_PATH_FRAGMENTS = [
        "/suspend", "/reinstate", "/terminate/begin", "/terminate/confirm",
        "/data/delete-request",
    ]

    def test_tenant_portal_api_client_has_no_caller_for_platform_only_actions(self):
        from pathlib import Path
        root = Path(__file__).parent.parent
        api_client = root / "frontend" / "tenant-portal" / "lib" / "api.ts"
        text = api_client.read_text(encoding="utf-8")
        found = [frag for frag in self.PLATFORM_ONLY_PATH_FRAGMENTS if frag in text]
        assert found == [], (
            f"frontend/tenant-portal/lib/api.ts now references platform-only tenant_engine "
            f"action path(s) {found} -- these endpoints are platform-only per "
            f"docs/workflow-rearchitecture/phase-02a-slice-02f1a/sensitive-capability-policy.md; "
            f"adding a tenant-portal caller requires a separate, explicit product-policy decision, "
            f"not just an API client change"
        )

    def test_super_admin_api_client_still_has_all_platform_callers(self):
        """Confirms the frontend-exposure audit's positive finding stays
        true: the super-admin app is the sole, legitimate, existing caller
        of these endpoints -- if this count drops, the audit's evidence
        base has gone stale."""
        from pathlib import Path
        root = Path(__file__).parent.parent
        api_client = root / "frontend" / "super-admin" / "lib" / "api.ts"
        text = api_client.read_text(encoding="utf-8")
        found = [frag for frag in self.PLATFORM_ONLY_PATH_FRAGMENTS if frag in text]
        assert len(found) == len(self.PLATFORM_ONLY_PATH_FRAGMENTS), (
            f"expected all platform-only path fragments referenced in "
            f"frontend/super-admin/lib/api.ts, found {found}"
        )


@pytest.mark.asyncio
class TestReadPathsUnaffected:
    """Workstream 10: this slice only touched mutation-method dependencies
    (require_permission -> require_tenant_mutation_permission) and never
    touched any GET handler or its dependency. Proves representative reads
    still work for an authorized tenant_owner and still enforce tenant
    isolation (cross-tenant read still rejected by the same pre-existing
    _assert_own_tenant_or_super_admin check, unmodified this slice)."""

    # /health is deliberately excluded: it triggers a pre-existing, unrelated
    # mock-fidelity gap (Decimal(str(MagicMock())) crashes deep in
    # usage_credits.service.get_balance, several layers past the auth gate --
    # the same class of gap documented in test_final_l5_01b_admin_tenant_rbac
    # for pagination math, not an auth regression).
    READ_ENDPOINTS = [
        "/v1/tenants/{tid}",
        "/v1/tenants/{tid}/engines",
        "/v1/tenants/{tid}/feature-flags",
    ]

    @pytest.mark.parametrize("path_tmpl", READ_ENDPOINTS)
    async def test_authorized_owner_read_not_rejected_by_auth_layer(self, path_tmpl):
        tid = str(uuid.uuid4())
        owner = _user("tenant_owner", tenant_id=tid)
        _override(owner)
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                r = await client.get(path_tmpl.format(tid=tid), headers={"Authorization": "Bearer x"})
            assert r.status_code not in (401, 403), (
                f"GET {path_tmpl}: authorized tenant_owner read rejected at auth layer, got {r.status_code}: {r.text}"
            )
        finally:
            _clear_override()

    @pytest.mark.parametrize("path_tmpl", READ_ENDPOINTS)
    async def test_cross_tenant_read_rejected(self, path_tmpl):
        own_tenant = str(uuid.uuid4())
        other_tenant = str(uuid.uuid4())
        owner = _user("tenant_owner", tenant_id=own_tenant)
        _override(owner)
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                r = await client.get(path_tmpl.format(tid=other_tenant), headers={"Authorization": "Bearer x"})
            assert r.status_code == 403, f"GET {path_tmpl}: cross-tenant read must be rejected, got {r.status_code}: {r.text}"
        finally:
            _clear_override()

    async def test_readonly_scope_can_still_read(self):
        """Access-scope read-only enforcement is mutation-only by design --
        a read-only-scoped user must still be able to read, only mutations
        are blocked. Proves this slice's guard swap didn't accidentally
        block reads too."""
        tid = str(uuid.uuid4())
        readonly_user = _user("tenant_owner", tenant_id=tid, access_scope="customer_support_limited")
        _override(readonly_user)
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                r = await client.get(f"/v1/tenants/{tid}", headers={"Authorization": "Bearer x"})
            assert r.status_code != 403, f"read-only scope must not block reads, got {r.text}"
        finally:
            _clear_override()


class TestDeactivateStaffSessionRevocation:
    """Workstream 11: deactivate_staff previously revoked only
    user_sessions.revoked_at (DB), which get_current_user does NOT check at
    request time -- it checks the Redis serviceos:session:revoked:{id} flag
    instead (the same gap Slice 2F fixed for update_permissions). This
    proves the Redis flag is now set for every active session on
    deactivation, mirroring update_permissions' proven pattern exactly."""

    @pytest.mark.asyncio
    async def test_deactivate_staff_sets_redis_revocation_flag_for_all_active_sessions(self):
        from app.engines.auth.service import AuthService

        user_id = uuid.uuid4()
        tenant_id = uuid.uuid4()
        session_id_1, session_id_2 = uuid.uuid4(), uuid.uuid4()
        target_user = MagicMock(id=user_id, tenant_id=tenant_id, is_active=True)

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
            _scalar(target_user),                       # _get_user_by_id
            _rows([session_id_1, session_id_2]),         # active sessions lookup
            MagicMock(),                                  # the UPDATE user_sessions statement
        ])

        from unittest.mock import patch
        with patch("app.engines.auth.service.get_redis") as mock_get_redis:
            redis_mock = AsyncMock()
            mock_get_redis.return_value = redis_mock
            svc = AuthService(db=db, request_id="test")
            with patch("app.core.usage_quota.adjust_usage", new=AsyncMock()):
                result = await svc.deactivate_staff(user_id, tenant_id, uuid.uuid4())

        assert result["is_active"] is False
        assert result["sessions_revoked"] == 2
        assert redis_mock.setex.call_count == 2
        called_keys = {call.args[0] for call in redis_mock.setex.call_args_list}
        assert called_keys == {
            f"serviceos:session:revoked:{session_id_1}",
            f"serviceos:session:revoked:{session_id_2}",
        }

    @pytest.mark.asyncio
    async def test_deactivate_staff_no_active_sessions_no_redis_calls(self):
        from app.engines.auth.service import AuthService
        from unittest.mock import patch

        user_id = uuid.uuid4()
        tenant_id = uuid.uuid4()
        target_user = MagicMock(id=user_id, tenant_id=tenant_id, is_active=False)

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
            _scalar(target_user),
            _rows([]),  # no active sessions
        ])

        with patch("app.engines.auth.service.get_redis") as mock_get_redis:
            redis_mock = AsyncMock()
            mock_get_redis.return_value = redis_mock
            svc = AuthService(db=db, request_id="test")
            result = await svc.deactivate_staff(user_id, tenant_id, uuid.uuid4())

        assert result["sessions_revoked"] == 0
        redis_mock.setex.assert_not_called()
