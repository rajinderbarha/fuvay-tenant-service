"""Phase 2A Slice 2F — mutation-enforcement closure tests.

Covers:
- Session revocation on permission reduction (Workstream 9, the real fix
  this slice makes) -- both the DB user_sessions.revoked_at update AND the
  Redis serviceos:session:revoked:{id} flag get_current_user actually
  checks (Slice 2D found the remediation script only did the former; this
  closes that gap for update_permissions specifically).
- No revocation for pure grants (avoiding unnecessary churn per the brief's
  "avoid unnecessary revocation for harmless metadata changes").
- The runtime mutation-route inventory script's exhaustiveness and its
  auto-classification counts (regression guard on the real, live numbers
  found this slice).
"""
from __future__ import annotations

import importlib.util
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _mock_staff_permission(user_id, tenant_id, perm_key, is_granted):
    p = MagicMock()
    p.user_id = user_id
    p.tenant_id = tenant_id
    p.permission_key = perm_key
    p.is_granted = is_granted
    return p


def _scalar_result(value):
    r = MagicMock()
    r.scalar_one_or_none = MagicMock(return_value=value)
    return r


def _rows_result(values):
    r = MagicMock()
    r.__iter__ = lambda self: iter([(v,) for v in values])
    return r


@pytest.mark.asyncio
class TestPermissionReductionSessionRevocation:
    async def _make_service(self):
        from app.engines.auth.service import AuthService
        db = AsyncMock()
        db.add = MagicMock()
        with patch("app.engines.auth.service.get_redis") as mock_get_redis:
            redis_mock = AsyncMock()
            mock_get_redis.return_value = redis_mock
            svc = AuthService(db=db, request_id="test")
        return svc, db, redis_mock

    async def test_pure_grant_does_not_revoke_sessions(self):
        svc, db, redis_mock = await self._make_service()
        user_id = uuid.uuid4()
        tenant_id = uuid.uuid4()
        target_user = MagicMock(id=user_id, tenant_id=tenant_id)

        db.execute = AsyncMock(side_effect=[
            _scalar_result(target_user),   # _get_user_by_id
            _scalar_result(None),           # existing StaffPermission lookup -> none, new grant
        ])

        result = await svc.update_permissions(
            target_user_id=user_id, tenant_id=tenant_id,
            granting_user_id=uuid.uuid4(), permissions={"staff:manage": True},
        )
        assert result["reduced_permission_keys"] == []
        assert result["sessions_revoked"] == 0
        assert "next token refresh" in result["message"]
        redis_mock.setex.assert_not_called()

    async def test_grant_to_deny_revokes_sessions_and_writes_redis_flags(self):
        svc, db, redis_mock = await self._make_service()
        user_id = uuid.uuid4()
        tenant_id = uuid.uuid4()
        target_user = MagicMock(id=user_id, tenant_id=tenant_id)
        existing_perm = _mock_staff_permission(user_id, tenant_id, "staff:manage", True)
        session_id_1, session_id_2 = uuid.uuid4(), uuid.uuid4()

        db.execute = AsyncMock(side_effect=[
            _scalar_result(target_user),          # _get_user_by_id
            _scalar_result(existing_perm),         # existing StaffPermission -> True, now denying
            _rows_result([session_id_1, session_id_2]),  # active sessions lookup
            MagicMock(),                            # the UPDATE user_sessions statement
        ])

        result = await svc.update_permissions(
            target_user_id=user_id, tenant_id=tenant_id,
            granting_user_id=uuid.uuid4(), permissions={"staff:manage": False},
        )
        assert existing_perm.is_granted is False
        assert result["reduced_permission_keys"] == ["staff:manage"]
        assert result["sessions_revoked"] == 2
        assert "revoked immediately" in result["message"]
        assert "reauthentication required" in result["message"]
        # The Redis flag get_current_user actually checks must be set for BOTH sessions.
        assert redis_mock.setex.call_count == 2
        called_keys = {call.args[0] for call in redis_mock.setex.call_args_list}
        assert called_keys == {
            f"serviceos:session:revoked:{session_id_1}",
            f"serviceos:session:revoked:{session_id_2}",
        }

    async def test_new_explicit_deny_also_counts_as_reduction(self):
        """A brand-new StaffPermission row created with is_granted=False
        (no prior grant existed) is still a reduction relative to the base
        role bundle, and must revoke sessions -- not just grant-to-deny
        transitions on an existing row."""
        svc, db, redis_mock = await self._make_service()
        user_id = uuid.uuid4()
        tenant_id = uuid.uuid4()
        target_user = MagicMock(id=user_id, tenant_id=tenant_id)

        db.execute = AsyncMock(side_effect=[
            _scalar_result(target_user),
            _scalar_result(None),           # no existing row
            _rows_result([uuid.uuid4()]),    # one active session
            MagicMock(),
        ])

        result = await svc.update_permissions(
            target_user_id=user_id, tenant_id=tenant_id,
            granting_user_id=uuid.uuid4(), permissions={"field_ops:jobs:update": False},
        )
        assert result["reduced_permission_keys"] == ["field_ops:jobs:update"]
        assert result["sessions_revoked"] == 1

    async def test_cross_tenant_target_still_rejected(self):
        """Regression guard: the pre-existing tenant-ownership check must
        remain intact after this slice's changes."""
        svc, db, redis_mock = await self._make_service()
        from app.exceptions import ServiceOSException
        user_id = uuid.uuid4()
        wrong_tenant = uuid.uuid4()
        other_tenant = uuid.uuid4()
        target_user = MagicMock(id=user_id, tenant_id=wrong_tenant)
        db.execute = AsyncMock(return_value=_scalar_result(target_user))

        with pytest.raises(ServiceOSException) as exc:
            await svc.update_permissions(
                target_user_id=user_id, tenant_id=other_tenant,
                granting_user_id=uuid.uuid4(), permissions={"staff:manage": False},
            )
        # Slice 2F-29 (M01): the cross-tenant rejection is UNCHANGED -- what
        # changed is that it no longer discloses that the id exists in another
        # tenant. PERMISSION_DENIED("User does not belong to your tenant") was
        # an account-existence oracle; a foreign target is now indistinguishable
        # from a nonexistent one, matching deactivate_staff's pre-existing
        # behaviour.
        assert exc.value.error_code == "NOT_FOUND"
        assert "belong" not in str(exc.value).lower()
        assert str(other_tenant) not in str(exc.value)


class TestMutationRouteInventoryScript:
    def _load(self):
        spec = importlib.util.spec_from_file_location(
            "inventory_mutation_routes",
            Path(__file__).parent.parent / "scripts" / "workflow_rearchitecture" / "inventory_mutation_routes.py",
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def test_classify_prefix_covers_expected_domains(self):
        mod = self._load()
        assert mod.classify_prefix("/v1/admin/tenants") == "PLATFORM_ADMIN_MUTATION"
        assert mod.classify_prefix("/v1/staff/service-jobs/x/accept") == "TENANT_TECHNICIAN_MUTATION"
        assert mod.classify_prefix("/v1/provider/service-jobs/x/assign") == "TENANT_USER_MUTATION"
        assert mod.classify_prefix("/v1/tenant/profile") == "TENANT_USER_MUTATION"
        assert mod.classify_prefix("/v1/customer/bookings") == "CUSTOMER_MUTATION"
        assert mod.classify_prefix("/v1/public/signup") == "CALLBACK_OR_WEBHOOK"

    def test_mutation_methods_set_is_the_4_real_http_mutation_verbs(self):
        mod = self._load()
        assert mod.MUTATION_METHODS == {"POST", "PUT", "PATCH", "DELETE"}

    def test_guard_status_distinguishes_scope_aware_from_permission_only(self):
        """Phase 2A Slice 2F-1, Workstream 12: require_tenant_mutation_permission's
        inner check is renamed require_tenant_mutation_{perm}, distinct from
        plain require_permission's require_{perm} -- this must keep working
        so module-scoped verification can tell the two apart without parsing
        source."""
        mod = self._load()
        assert mod.guard_status(["require_tenant_mutation_tenant_update", "get_current_user"]) == \
            "TENANT_MUTATION_PERMISSION_SCOPE_AWARE"
        assert mod.guard_status(["require_tenant_update", "get_current_user"]) == \
            "PERMISSION_ONLY_NOT_SCOPE_AWARE"
        assert mod.guard_status(["require_super_admin", "get_current_user"]) == "PLATFORM_ADMIN_ONLY"
        assert mod.guard_status(["get_current_user"]) == "AUTHENTICATED_ONLY_NO_PERMISSION_CHECK"
        assert mod.guard_status(["_svc", "get_db"]) == "PUBLIC_NO_AUTH"

    def test_tenant_engine_router_module_has_zero_unverified_mutation_endpoints(self):
        """Regression guard for Slice 2F-1's closure claim: re-running the
        live route walk against app.engines.tenant_engine.router must show
        0 unverified endpoints out of its 27 mutation routes (19 scope-aware,
        7 platform-admin-only, 1 public signup) -- if this count changes,
        the module gained/lost an endpoint or lost its guard; either way
        this test should be revisited, not silently left stale."""
        mod = self._load()
        from app.main import app
        routes = [r for r in mod.walk(app.router if hasattr(app, "router") else app)
                  if r["module"] == "app.engines.tenant_engine.router"]
        assert len(routes) == 27
        unverified = [r for r in routes if r["guard_status"] not in mod.ACCEPTED_GUARD_STATUSES]
        assert unverified == [], f"tenant_engine.router regressed, now has unverified routes: {unverified}"

    def test_execution_assignment_overlap_is_fully_resolved(self):
        """Phase 2A Slice 2F-3A found exactly 2 (method, path) pairs mounted
        from more than one of the 3 overlap-adjudicated modules (POST
        .../accept and .../reject, both shadowed by
        home_service_assignment.staff_router over execution.home_service_router).
        Slice 2F-3B closed this by removing the shadowed route decorators
        from execution.home_service_router (Workstream 2) -- so the live
        route walk must now find ZERO overlaps between these 3 modules. If
        a NEW overlap appears (e.g. from a future change re-adding a
        decorator or a different collision), this test fails, signaling
        that overlap needs its own adjudication."""
        mod = self._load()
        from app.main import app
        modules = {
            "app.engines.execution.home_service_router",
            "app.engines.home_service_assignment.staff_router",
            "app.engines.home_service_assignment.provider_router",
        }
        routes = [r for r in mod.walk(app.router if hasattr(app, "router") else app)
                  if r["module"] in modules]
        by_key: dict[tuple, list] = {}
        for r in routes:
            for m in r["methods"]:
                by_key.setdefault((m, r["path"]), []).append(r)
        overlaps = {k: v for k, v in by_key.items() if len(v) > 1}
        assert overlaps == {}, (
            f"Expected zero route overlaps between these 3 modules after Slice 2F-3B's "
            f"decorator removal, found: {sorted(overlaps.keys())}"
        )

    def test_execution_router_has_22_reachable_mutation_routes(self):
        """Phase 2A Slice 2F-3B regression guard: execution.home_service_router
        must have exactly 22 mutation routes (23 mounted - 2 shadowed
        accept/reject decorators = 21, plus the auto-acceptance flow's
        `POST /{job_id}/customer-contacted`, which records the provider's
        first task -- calling the customer to confirm requirements -- and is
        guarded by require_staff_or_above_mutation like its siblings).

        The count is deliberately exact: it is what makes an unguarded route
        added later impossible to slip in unnoticed."""
        mod = self._load()
        from app.main import app
        routes = [r for r in mod.walk(app.router if hasattr(app, "router") else app)
                  if r["module"] == "app.engines.execution.home_service_router"]
        assert len(routes) == 22, f"expected 22 mutation routes, found {len(routes)}"

    def test_all_three_execution_assignment_modules_have_zero_unverified_routes(self):
        """Phase 2A Slice 2F-3B closure guard: every reachable mutation route
        across execution.home_service_router,
        home_service_assignment.staff_router, and .provider_router must
        show 0 unverified via guard_status -- proving the access-scope
        guard application (require_staff_or_above_mutation /
        require_tenant_owner_mutation) and the 3 pre-existing
        platform-admin-permission-gated exemptions together close this
        slice's full scope.

        Count raised 27 -> 29. This was ALREADY stale at 28 before the
        auto-acceptance work (a route was added earlier without updating this
        guard, so it was failing on arrival); 29 is that real 28 plus
        `POST /{job_id}/customer-contacted`. The `unverified == []` assertion
        below is the one that actually enforces safety -- it is what proves the
        new route carries require_staff_or_above_mutation like its siblings."""
        mod = self._load()
        from app.main import app
        modules = {
            "app.engines.execution.home_service_router",
            "app.engines.home_service_assignment.staff_router",
            "app.engines.home_service_assignment.provider_router",
        }
        routes = [r for r in mod.walk(app.router if hasattr(app, "router") else app)
                  if r["module"] in modules]
        assert len(routes) == 29, f"expected 29 total reachable mutation routes, found {len(routes)}"
        exempt = mod.CONFIRMED_FALSE_POSITIVE_ROUTES | mod.CONFIRMED_PLATFORM_ADMIN_PERMISSION_ROUTES
        unverified = [
            r for r in routes
            if r["guard_status"] not in mod.ACCEPTED_GUARD_STATUSES
            and (r["module"], r["endpoint_name"]) not in exempt
        ]
        assert unverified == [], f"unverified routes remain: {unverified}"
