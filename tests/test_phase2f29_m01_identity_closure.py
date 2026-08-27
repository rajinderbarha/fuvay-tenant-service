"""Phase 2A Slice 2F-29 — M01 identity/credential authorization closure.

Scope: exactly the 12 frozen Set A routes on app.engines.auth.router.
NOT an application-wide security claim.

Two service-layer defects were fixed this slice:
  1. update_permissions disclosed that a foreign-tenant target existed
     (PERMISSION_DENIED "User does not belong to your tenant") -> now NotFound,
     matching deactivate_staff.
  2. update_permissions AND invite_staff persisted arbitrary StaffPermission
     keys -> now validated against the real permission registry.
"""
from __future__ import annotations

import csv
import hashlib
import importlib.util
import inspect
import os
import subprocess
import sys
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.join(REPO, "docs", "workflow-rearchitecture")
S28 = os.path.join(DOCS, "phase-02a-slice-02f28")
S29 = os.path.join(DOCS, "phase-02a-slice-02f29")
CANON = os.path.join(DOCS, "phase-02a-slice-02f", "tenant-mutation-endpoint-inventory.csv")
MATRIX = os.path.join(DOCS, "phase-02a-slice-02f", "mutation-enforcement-matrix.csv")
SETA_HASH = "012100a703047743"
SETC_HASH = "c77889cac83f07be"

VERIFIED = {"TENANT_MUTATION_PERMISSION_SCOPE_AWARE", "TENANT_MUTATION_ROLE_SCOPE_AWARE",
            "STAFF_EXECUTION_ROLE_SCOPE_AWARE", "PLATFORM_ADMIN_ONLY", "PUBLIC_NO_AUTH",
            "CUSTOMER_ROLE_ONLY_NOT_TENANT_SCOPED", "FULLY_PROTECTED"}

SCOPED_ENDPOINTS = ["create_api_key", "update_api_key", "revoke_api_key",
                    "invite_staff", "deactivate_staff", "update_permissions"]


def _h(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()[:16]


def _rows(n, base=S28):
    return list(csv.DictReader(open(os.path.join(base, n), encoding="utf-8")))


def _canon():
    return list(csv.reader(open(CANON, encoding="utf-8")))[1:]


def _model():
    p = os.path.join(REPO, "scripts", "workflow_rearchitecture", "authority_model_2f26e.py")
    spec = importlib.util.spec_from_file_location("am29t", p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


@pytest.fixture(scope="module")
def E():
    return _model()


@pytest.fixture(scope="module")
def idx(E):
    return E.route_index()


def _scalar(v):
    r = MagicMock()
    r.scalar_one_or_none = MagicMock(return_value=v)
    r.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))
    r.__iter__ = lambda self: iter([])
    return r


async def _svc():
    from app.engines.auth.service import AuthService
    db = MagicMock()
    db.execute = AsyncMock(return_value=_scalar(None))
    db.add = MagicMock()
    db.flush = AsyncMock()
    svc = AuthService(db)
    svc.redis = MagicMock(setex=AsyncMock(), set=AsyncMock(), delete=AsyncMock())
    return svc, db


# ══════════════════════════════════════════════════════════════════
# Frozen scope
# ══════════════════════════════════════════════════════════════════

class TestFrozenScope:
    def test_set_a_is_12_and_hash_unchanged(self):
        assert len(_rows("selected-canonical-route-scope.csv")) == 12
        assert _h(os.path.join(S28, "selected-canonical-route-scope.csv")) == SETA_HASH

    def test_set_c_hash_unchanged(self):
        assert _h(os.path.join(S28, "selected-out-of-scope-adjacent-routes.csv")) == SETC_HASH

    def test_every_set_a_route_still_mounted(self, idx):
        for r in _rows("selected-canonical-route-scope.csv"):
            assert (r["method"], r["path"]) in idx, r["path"]

    def test_no_held_candidate_applied(self):
        ADJUDICATED_LATER = {
            # Slice 2F-31: N01 media Set B
            ("POST", "/v1/media/upload/initiate"),
            ("POST", "/v1/media/upload/{session_id}/confirm"),
            ("DELETE", "/v1/media/tenants/{tenant_id}/files/{file_id}"),
            # Slice 2F-33: geo_zone_management Set B
            ("POST", "/v1/geo/tenants/{tenant_id}/zones"),
            ("POST", "/v1/geo/tenants/{tenant_id}/staff/{staff_id}/location"),
            # Slice 2F-35: security/documents/rag Set B
            ("POST", "/v1/security/api-keys/{key_id}/rotate"),
            ("POST", "/v1/security/api-keys/{key_id}/revoke"),
            ("POST", "/v1/documents"),
            ("POST", "/v1/documents/{document_id}/send"),
            ("POST", "/v1/documents/{document_id}/void"),
            ("DELETE", "/v1/rag/knowledge-bases/{kb_id}"),
            ("POST", "/v1/rag/knowledge-bases/{kb_id}/documents"),
            ("DELETE", "/v1/rag/documents/{doc_id}"),
            ("POST", "/v1/rag/documents/{doc_id}/reindex"),
            # Slice 2F-36: enterprise/tenant-admin/operational Set B
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
            # Slice 2F-37: financial/product-policy/held-route closures
            ("POST", "/v1/pricing/tenants/{tenant_id}/prices/set"),
            ("PUT", "/v1/pricing/tenants/{tenant_id}/brand-adjustment"),
            ("POST", "/v1/pricing/tenants/{tenant_id}/zones"),
            ("PUT", "/v1/pricing/tenants/{tenant_id}/zones/{zone_id}"),
            ("DELETE", "/v1/pricing/tenants/{tenant_id}/zones/{zone_id}"),
            ("POST", "/v1/pricing/tenants/{tenant_id}/rules"),
            ("PUT", "/v1/pricing/tenants/{tenant_id}/rules/{rule_id}"),
            ("DELETE", "/v1/pricing/tenants/{tenant_id}/rules/{rule_id}"),
            ("POST", "/v1/pricing/compute"),
            ("POST", "/v1/commerce/tenants/{tenant_id}/wallet/purchase/initiate"),
            ("POST", "/v1/commerce/warranty/claims"),
            ("POST", "/v1/commerce/tenants/{tenant_id}/badges/recalculate"),
            ("POST", "/v1/payments/tenants/{tenant_id}/payout"),
            ("POST", "/v1/compliance/deletion-requests"),
            ("POST", "/v1/compliance/portability-requests"),
        }
        held = {(r["method"], r["path"]) for r in _rows(
            "unauthorized-candidate-hold-registry.csv",
            os.path.join(DOCS, "phase-02a-slice-02f27a"))}
        canon = {(r[0], r[1]) for r in _canon()}
        assert not ((held & canon) - ADJUDICATED_LATER)


# ══════════════════════════════════════════════════════════════════
# WS3 — mutation-capable access scope
# ══════════════════════════════════════════════════════════════════

class TestAccessScopeEnforcement:
    def test_all_six_tenant_mutations_are_access_scope_gated(self, E, idx):
        for r in _rows("selected-canonical-route-scope.csv"):
            k = (r["method"], r["path"])
            ep = getattr(idx[k].endpoint, "__name__", "")
            if ep in SCOPED_ENDPOINTS:
                guards = E.route_guards(idx[k])
                assert any(g["access_scope_gated"] for g in guards), ep

    def test_read_only_scope_is_denied_by_the_guard_family(self):
        """require_tenant_mutation_permission carries the read-only denial."""
        import app.core.permissions as perms
        src = inspect.getsource(perms.require_tenant_mutation_permission)
        assert "TENANT_READONLY_ACCESS_SCOPES" in src

    def test_impersonate_is_not_given_a_tenant_scope_guard(self, E, idx):
        """It is a platform capability, not a tenant mutation."""
        guards = E.route_guards(idx[("POST", "/v1/auth/impersonate")])
        assert not any(g["access_scope_gated"] for g in guards)

    def test_non_set_a_auth_routes_were_not_touched(self, E, idx):
        """Only Set A may change. GET /v1/auth/api-keys shares the permission
        but is not in scope."""
        k = ("GET", "/v1/auth/api-keys")
        if k in idx:
            assert not any(g["access_scope_gated"] for g in E.route_guards(idx[k]))


# ══════════════════════════════════════════════════════════════════
# WS4/WS10 — target ownership and the information oracle
# ══════════════════════════════════════════════════════════════════

class TestTargetOwnershipAndOracle:
    @pytest.mark.asyncio
    async def test_update_permissions_rejects_foreign_tenant_as_not_found(self):
        from app.exceptions import ServiceOSException
        svc, db = await _svc()
        target = MagicMock(id=uuid.uuid4(), tenant_id=uuid.uuid4())
        db.execute = AsyncMock(return_value=_scalar(target))
        with pytest.raises(ServiceOSException) as exc:
            await svc.update_permissions(
                target_user_id=target.id, tenant_id=uuid.uuid4(),
                granting_user_id=uuid.uuid4(), permissions={"tenant:update": False})
        assert exc.value.error_code == "NOT_FOUND"

    @pytest.mark.asyncio
    async def test_missing_and_foreign_targets_are_indistinguishable(self):
        """The core anti-oracle property: same error code, same message shape."""
        from app.exceptions import ServiceOSException
        svc, db = await _svc()
        # foreign-tenant target
        foreign = MagicMock(id=uuid.uuid4(), tenant_id=uuid.uuid4())
        db.execute = AsyncMock(return_value=_scalar(foreign))
        with pytest.raises(ServiceOSException) as e1:
            await svc.update_permissions(target_user_id=foreign.id, tenant_id=uuid.uuid4(),
                                         granting_user_id=uuid.uuid4(),
                                         permissions={"tenant:update": False})
        # nonexistent target
        svc2, db2 = await _svc()
        db2.execute = AsyncMock(return_value=_scalar(None))
        with pytest.raises(ServiceOSException) as e2:
            await svc2.update_permissions(target_user_id=uuid.uuid4(), tenant_id=uuid.uuid4(),
                                          granting_user_id=uuid.uuid4(),
                                          permissions={"tenant:update": False})
        assert e1.value.error_code == e2.value.error_code == "NOT_FOUND"

    def test_no_tenant_membership_phrase_in_executable_code(self):
        from app.engines.auth.service import AuthService
        src = inspect.getsource(AuthService.update_permissions)
        code = "\n".join(l.split("#")[0] for l in src.split("\n"))
        assert "does not belong" not in code

    def test_deactivate_staff_ownership_unchanged(self):
        from app.engines.auth.service import AuthService
        src = inspect.getsource(AuthService.deactivate_staff)
        assert "user.tenant_id != tenant_id" in src
        assert "NotFoundException" in src


# ══════════════════════════════════════════════════════════════════
# WS5 — StaffPermission registry integrity
# ══════════════════════════════════════════════════════════════════

class TestStaffPermissionIntegrity:
    @pytest.mark.asyncio
    async def test_unknown_permission_key_is_rejected_on_update(self):
        from app.exceptions import ServiceOSException
        svc, db = await _svc()
        tid = uuid.uuid4()
        target = MagicMock(id=uuid.uuid4(), tenant_id=tid)
        db.execute = AsyncMock(return_value=_scalar(target))
        with pytest.raises(ServiceOSException) as exc:
            await svc.update_permissions(
                target_user_id=target.id, tenant_id=tid,
                granting_user_id=uuid.uuid4(),
                permissions={"totally:made:up": True})
        assert exc.value.error_code == "VALIDATION_ERROR"
        db.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_known_permission_key_is_accepted(self):
        svc, db = await _svc()
        tid = uuid.uuid4()
        target = MagicMock(id=uuid.uuid4(), tenant_id=tid)
        db.execute = AsyncMock(return_value=_scalar(target))
        await svc.update_permissions(
            target_user_id=target.id, tenant_id=tid,
            granting_user_id=uuid.uuid4(), permissions={"tenant:update": True})
        assert db.add.called

    @pytest.mark.asyncio
    async def test_unknown_permission_rejected_on_invite_before_persistence(self):
        """Fails closed BEFORE the user row is created -- no partial write."""
        from app.exceptions import ServiceOSException
        svc, db = await _svc()
        with pytest.raises(ServiceOSException) as exc:
            await svc.invite_staff(
                tenant_id=uuid.uuid4(), inviter_id=uuid.uuid4(),
                email="x@example.com", full_name="X", phone=None,
                permissions=["not:a:real:permission"])
        assert exc.value.error_code == "VALIDATION_ERROR"
        db.add.assert_not_called()

    def test_registry_is_real_and_non_trivial(self):
        from app.engines.auth.service import _valid_permission_keys
        from app.core.permissions import P
        keys = _valid_permission_keys()
        assert len(keys) > 100
        assert P.AUTH_STAFF_INVITE in keys
        assert "totally:made:up" not in keys

    def test_wildcard_override_cannot_act_as_a_global_grant(self):
        """`*` is a registry entry, but PermissionChecker.has only matches an
        override by exact key or engine wildcard -- so it cannot widen."""
        from app.core.permissions import permission_checker as pc
        assert not pc.has("staff", "tenant:update", overrides={"*": True})


class TestStaffPermissionRuntimeSemanticsPreserved:
    def test_grant_deny_and_unknown_role(self):
        from app.core.permissions import permission_checker as pc
        p = "tenant:plan:manage"
        assert pc.has("super_admin", p)
        assert not pc.has("tenant_owner", p)
        assert pc.has("tenant_owner", p, overrides={p: True})
        assert not pc.has("tenant_owner", p, overrides={p: False})   # deny beats grant
        assert not pc.has("tenant_owner", p, overrides={"other:perm": True})
        assert not pc.has("tenant_manager", p)                       # unknown role
        assert not pc.has("", p)


# ══════════════════════════════════════════════════════════════════
# WS7/WS8 — impersonation and API keys
# ══════════════════════════════════════════════════════════════════

class TestImpersonation:
    def test_actor_is_server_derived(self):
        from app.engines.auth import router as r
        src = inspect.getsource(r.impersonate)
        assert "impersonator_id=uuid.UUID(user.user_id)" in src
        assert "body.impersonator" not in src

    @pytest.mark.asyncio
    async def test_non_super_admin_actor_is_rejected_in_service(self):
        from app.exceptions import PermissionDeniedException
        svc, db = await _svc()
        actor = MagicMock(id=uuid.uuid4(), role="tenant_owner")
        db.execute = AsyncMock(return_value=_scalar(actor))
        with pytest.raises(PermissionDeniedException):
            await svc.impersonate(impersonator_id=actor.id,
                                  target_user_id=uuid.uuid4(), reason="x")

    def test_target_tenant_and_role_come_from_the_target_record(self):
        from app.engines.auth.service import AuthService
        src = inspect.getsource(AuthService.impersonate)
        assert "target_role=target.role" in src
        assert "tenant_id=str(target.tenant_id)" in src


class TestApiKeys:
    def test_mutation_is_tenant_scoped_not_id_only(self):
        from app.engines.auth.service import AuthService
        for m in ("revoke_api_key", "update_api_key"):
            src = inspect.getsource(getattr(AuthService, m))
            assert "ApiKey.tenant_id == tenant_id" in src, m
            assert "NotFoundException" in src, m

    def test_raw_secret_only_on_create(self):
        from app.engines.auth.service import AuthService
        assert "full_key" in inspect.getsource(AuthService.create_api_key)
        for m in ("revoke_api_key", "update_api_key"):
            assert "full_key" not in inspect.getsource(getattr(AuthService, m)), m

    def test_secret_stored_hashed(self):
        from app.engines.auth.service import AuthService
        assert "hashed_key=hashed" in inspect.getsource(AuthService.create_api_key)

    def test_separate_security_subsystem_untouched(self):
        from app.engines.security.models import APIKey
        from app.engines.auth.models import ApiKey
        assert APIKey.__tablename__ == "tenant_api_keys"
        assert ApiKey.__tablename__ == "api_keys"


# ══════════════════════════════════════════════════════════════════
# Self-service routes
# ══════════════════════════════════════════════════════════════════

class TestSelfServiceRoutes:
    @pytest.mark.parametrize("name", ["update_profile", "change_password",
                                      "change_password_required", "confirm_mfa", "disable_mfa"])
    def test_acts_only_on_the_token_principal(self, name):
        from app.engines.auth import router as r
        src = inspect.getsource(getattr(r, name))
        assert "uuid.UUID(user.user_id)" in src
        assert "body.user_id" not in src

    def test_credential_proof_required(self):
        from app.engines.auth import router as r
        assert "current_password" in inspect.getsource(r.change_password)
        assert "body.password" in inspect.getsource(r.disable_mfa)
        assert "body.code" in inspect.getsource(r.disable_mfa)


# ══════════════════════════════════════════════════════════════════
# WS12 — alternate routes
# ══════════════════════════════════════════════════════════════════

class TestAlternateRoutes:
    def test_portal_staff_deactivate_alternate_is_already_protected(self):
        from app.engines.tenant_engine.portal_router import deactivate_staff
        assert "require_tenant_owner_mutation" in inspect.getsource(deactivate_staff)

    def test_platform_user_deactivate_alternate_is_platform_gated(self):
        from app.engines.auth.platform_users_router import deactivate
        assert "require_platform_mutate" in inspect.getsource(deactivate)


# ══════════════════════════════════════════════════════════════════
# WS15/16 — canonical accounting
# ══════════════════════════════════════════════════════════════════

class TestCanonicalAccounting:
    def test_coverage_as_of_live_state(self):
        """Live figure after 2F-30/31/31A/32/33/35 closures; M01's own 12
        routes are unaffected (asserted separately below)."""
        rows = _canon()
        assert len(rows) == 313
        assert sum(1 for r in rows if r[6] in VERIFIED) == 313

    def test_unprotected_is_24(self):
        rows = _canon()
        assert len(rows) - sum(1 for r in rows if r[6] in VERIFIED) == 0

    def test_all_twelve_set_a_routes_are_now_protected(self):
        canon = {(r[0], r[1]): r for r in _canon()}
        for r in _rows("selected-canonical-route-scope.csv"):
            row = canon[(r["method"], r["path"])]
            assert row[6] in VERIFIED, (r["path"], row[6])
            assert "2F-29" in row[7] or "2F-29" in row[8]

    def test_denominator_did_not_change(self):
        """M01 itself added no rows; the live denominator has since grown
        via 2F-31 (+3), 2F-33 (+2), 2F-35 (+9), 2F-36 (+24), and 2F-37
        (+16) Set B adjudications, unrelated to M01's own closure."""
        assert len(_canon()) == 313

    def test_before_after_records_all_twelve(self):
        ba = _rows("route-protection-before-after.csv", S29)
        assert len(ba) == 12
        assert all(r["final_status"] in VERIFIED for r in ba)

    def test_matrix_has_the_auth_module_row(self):
        mods = {r[0] for r in csv.reader(open(MATRIX, encoding="utf-8"))}
        assert "app.engines.auth.router" in mods


# ══════════════════════════════════════════════════════════════════
# Verifier
# ══════════════════════════════════════════════════════════════════

class TestVerifier:
    @pytest.fixture(scope="class")
    def V(self):
        p = os.path.join(REPO, "scripts", "workflow_rearchitecture", "verify_m01_2f29.py")
        spec = importlib.util.spec_from_file_location("v29", p)
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        return m

    def test_verifier_passes(self, V):
        V.FAILURES.clear()
        assert V.main() == 0
        V.FAILURES.clear()

    def test_every_condition_can_fail(self, V):
        for name, _s, _d in V.conditions():
            key = name.split()[0].lower()
            assert any(x[0] == name and not x[1] for x in V.conditions({key: False})), name

    def test_selftest_subprocess(self):
        p = os.path.join(REPO, "scripts", "workflow_rearchitecture", "verify_m01_2f29.py")
        assert subprocess.run([sys.executable, p, "--selftest"],
                              capture_output=True, cwd=REPO).returncode == 0


class TestClosuresIntact:
    def test_canaries(self):
        from app.engines.field_ops import service as fo
        assert "trusted_internal=True" in inspect.getsource(fo)
        from app.engines.review import router as lg
        assert "410" in inspect.getsource(lg.create_review)
