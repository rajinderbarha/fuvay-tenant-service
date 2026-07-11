"""FINAL-L5-04B — Tenant Module and Category Entitlement Architecture tests.

Covers: migration structure, ORM models, RBAC/auth guards on every
entitlement endpoint (anonymous 401, wrong-role 403, tenant self-scope),
router registration, and service-layer idempotency/conflict logic
(mocked DB, per this repo's default testing convention — see
tests/conftest.py's autouse mock_database fixture). Real-DB proof
(constraint enforcement, live disable/re-enable, cross-tenant isolation)
is documented separately in docs/final-l5-04b/FINAL_L5_04B_LIVE_API_SMOKE_REPORT.md
with real curl transcripts against a live database, since the global
mock fixture here makes true constraint-violation testing impossible
without a real Postgres connection.
"""
from __future__ import annotations

import uuid
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.dependencies.auth import get_current_user, UserContext

ROOT = Path(__file__).parent.parent


def _user(role: str, tenant_id: str | None = None) -> UserContext:
    return UserContext(
        user_id=str(uuid.uuid4()), email=f"{role}@test.local", role=role,
        tenant_id=tenant_id, full_name=role.title(), is_verified=True,
    )


def _override(user_context):
    app.dependency_overrides[get_current_user] = lambda: user_context


def _clear_override():
    app.dependency_overrides.pop(get_current_user, None)


TENANT_ID = str(uuid.uuid4())

ADMIN_ENTITLEMENT_ENDPOINTS = [
    ("GET", f"/v1/admin/tenants/{TENANT_ID}/entitlements"),
    ("GET", f"/v1/admin/tenants/{TENANT_ID}/entitlements/history"),
    ("POST", f"/v1/admin/tenants/{TENANT_ID}/entitlements/modules"),
    ("POST", f"/v1/admin/tenants/{TENANT_ID}/entitlements/modules/home_services/disable"),
    ("POST", f"/v1/admin/tenants/{TENANT_ID}/entitlements/modules/home_services/reenable"),
    ("POST", f"/v1/admin/tenants/{TENANT_ID}/entitlements/categories"),
]

TENANT_SELF_READ_ENDPOINTS = [
    "/v1/tenant/me/modules",
    "/v1/tenant/me/categories",
    "/v1/tenant/me/entitlements",
]


# ── Migration structure ─────────────────────────────────────────────────────

class TestMigrationStructure:
    def test_migration_132_exists_with_correct_chain(self):
        f = ROOT / "alembic" / "versions" / "132_tenant_entitlement_architecture.py"
        assert f.exists()
        src = f.read_text(encoding="utf-8")
        assert 'revision = "132"' in src
        assert 'down_revision = "131"' in src

    def test_migration_creates_all_three_tables(self):
        src = (ROOT / "alembic" / "versions" / "132_tenant_entitlement_architecture.py").read_text(encoding="utf-8")
        for table in ["tenant_module_entitlements", "tenant_category_entitlements", "entitlement_audit_log"]:
            assert f'"{table}"' in src

    def test_migration_has_partial_unique_indexes_preventing_duplicate_active_rows(self):
        src = (ROOT / "alembic" / "versions" / "132_tenant_entitlement_architecture.py").read_text(encoding="utf-8")
        assert "uq_tme_tenant_module_active" in src
        assert "uq_tce_tenant_category_active" in src
        assert "WHERE status = 'ACTIVE'" in src

    def test_migration_has_status_check_constraints(self):
        src = (ROOT / "alembic" / "versions" / "132_tenant_entitlement_architecture.py").read_text(encoding="utf-8")
        assert "ck_tme_status_valid" in src
        assert "ck_tce_status_valid" in src

    def test_migration_has_downgrade(self):
        src = (ROOT / "alembic" / "versions" / "132_tenant_entitlement_architecture.py").read_text(encoding="utf-8")
        assert "def downgrade" in src
        assert "drop_table" in src


# ── ORM models ───────────────────────────────────────────────────────────────

class TestModels:
    def test_models_import_and_have_correct_table_names(self):
        from app.engines.entitlement.models import (
            TenantModuleEntitlement, TenantCategoryEntitlement, EntitlementAuditLog,
        )
        assert TenantModuleEntitlement.__tablename__ == "tenant_module_entitlements"
        assert TenantCategoryEntitlement.__tablename__ == "tenant_category_entitlements"
        assert EntitlementAuditLog.__tablename__ == "entitlement_audit_log"

    def test_module_entitlement_has_required_audit_fields(self):
        from app.engines.entitlement.models import TenantModuleEntitlement
        cols = {c.name for c in TenantModuleEntitlement.__table__.columns}
        for required in ["tenant_id", "module_id", "status", "source", "created_by", "updated_by", "version",
                          "enabled_at", "disabled_at", "effective_from", "effective_until"]:
            assert required in cols, f"missing {required}"

    def test_category_entitlement_references_module_entitlement(self):
        from app.engines.entitlement.models import TenantCategoryEntitlement
        cols = {c.name for c in TenantCategoryEntitlement.__table__.columns}
        assert "module_entitlement_id" in cols
        assert "category_id" in cols

    def test_all_six_entitlement_statuses_supported(self):
        from app.engines.entitlement.models import ENTITLEMENT_STATUSES
        assert set(ENTITLEMENT_STATUSES) == {"ACTIVE", "INACTIVE", "SUSPENDED", "EXPIRED", "PENDING", "ARCHIVED"}


# ── Router registration ─────────────────────────────────────────────────────

class TestRouterRegistration:
    def test_admin_and_tenant_entitlement_routers_registered(self):
        paths = set(app.openapi()["paths"].keys())
        assert "/v1/admin/tenants/{tenant_id}/entitlements" in paths
        assert "/v1/tenant/me/modules" in paths
        assert "/v1/tenant/me/categories" in paths
        assert "/v1/tenant/me/entitlements" in paths


# ── RBAC / Auth guards (dependency-override pattern, per repo convention) ───

@pytest.mark.asyncio
class TestAdminEntitlementRBAC:
    async def test_anonymous_rejected_401_on_all_admin_endpoints(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            for method, path in ADMIN_ENTITLEMENT_ENDPOINTS:
                r = await client.request(method, path, json={} if method == "POST" else None)
                assert r.status_code == 401, f"{method} {path} -> {r.status_code}"

    @pytest.mark.parametrize("role_name", ["customer", "technician", "tenant_owner", "tenant_manager", "tenant_readonly"])
    async def test_non_super_admin_roles_rejected_403(self, role_name):
        _override(_user(role_name, tenant_id=str(uuid.uuid4())))
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                for method, path in ADMIN_ENTITLEMENT_ENDPOINTS:
                    r = await client.request(method, path, headers={"Authorization": "Bearer x"},
                                              json={} if method == "POST" else None)
                    assert r.status_code == 403, f"{role_name} {method} {path} -> {r.status_code}"
        finally:
            _clear_override()

    async def test_cross_tenant_admin_access_also_blocked_for_tenant_owner(self):
        """A tenant_owner cannot reach ANY tenant's admin entitlement endpoint
        (not just other tenants') because the admin API requires super_admin
        outright -- a stronger guarantee than per-tenant scoping alone."""
        _override(_user("tenant_owner", tenant_id=str(uuid.uuid4())))
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                r = await client.get(f"/v1/admin/tenants/{uuid.uuid4()}/entitlements", headers={"Authorization": "Bearer x"})
                assert r.status_code == 403
        finally:
            _clear_override()


@pytest.mark.asyncio
class TestTenantSelfReadRBAC:
    async def test_anonymous_rejected_401(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            for path in TENANT_SELF_READ_ENDPOINTS:
                r = await client.get(path)
                assert r.status_code == 401, f"{path} -> {r.status_code}"

    async def test_customer_role_rejected_403(self):
        """require_staff_or_above excludes plain customers -- self-read
        entitlements are a tenant-operations concern, not a customer one."""
        _override(_user("customer", tenant_id=None))
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                for path in TENANT_SELF_READ_ENDPOINTS:
                    r = await client.get(path, headers={"Authorization": "Bearer x"})
                    assert r.status_code == 403, f"{path} -> {r.status_code}"
        finally:
            _clear_override()

    async def test_tenant_user_without_tenant_membership_rejected_403(self):
        """A staff/tenant_owner-role token with no tenant_id claim cannot
        read entitlements for a tenant it doesn't belong to -- there is no
        tenant_id query param on this endpoint at all, so it structurally
        cannot target another tenant."""
        _override(_user("tenant_owner", tenant_id=None))
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                r = await client.get("/v1/tenant/me/entitlements", headers={"Authorization": "Bearer x"})
                assert r.status_code == 403
        finally:
            _clear_override()


# ── Service-layer logic (mocked DB) ─────────────────────────────────────────

@pytest.mark.asyncio
class TestEntitlementServiceLogic:
    async def test_assign_module_entitlement_is_idempotent(self):
        """Re-assigning an already-ACTIVE module entitlement must return the
        existing row, not attempt a second insert (would violate the DB's
        partial unique index anyway -- this proves the service-layer check
        that avoids ever reaching that constraint in the happy path)."""
        from datetime import datetime, timezone
        from app.engines.entitlement.service import EntitlementService
        from app.engines.entitlement.models import TenantModuleEntitlement
        from app.engines.vertical_catalog.models import Vertical

        svc = EntitlementService()
        tenant_id = uuid.uuid4()
        module_id = uuid.uuid4()
        vertical = Vertical(id=module_id, key="home_services", label="Home Services", is_enabled=True)
        now = datetime.now(timezone.utc)
        existing = TenantModuleEntitlement(
            id=uuid.uuid4(), tenant_id=tenant_id, module_id=module_id, status="ACTIVE",
            created_at=now, updated_at=now, version=1,
        )

        db = AsyncMock()
        vertical_result = MagicMock(); vertical_result.scalar_one_or_none.return_value = vertical
        existing_result = MagicMock(); existing_result.scalar_one_or_none.return_value = existing
        db.execute = AsyncMock(side_effect=[vertical_result, existing_result])

        result = await svc.assign_module_entitlement(
            db, tenant_id=tenant_id, module_key="home_services", actor_id=None, actor_role="super_admin",
        )
        assert result["status"] == "ACTIVE"
        db.add.assert_not_called()   # no duplicate row created
        db.commit.assert_not_called()  # idempotent no-op path doesn't even commit

    async def test_assign_module_entitlement_raises_not_found_for_unknown_module(self):
        from app.engines.entitlement.service import EntitlementService, EntitlementNotFoundError

        svc = EntitlementService()
        db = AsyncMock()
        empty_result = MagicMock(); empty_result.scalar_one_or_none.return_value = None
        db.execute = AsyncMock(return_value=empty_result)

        with pytest.raises(EntitlementNotFoundError):
            await svc.assign_module_entitlement(
                db, tenant_id=uuid.uuid4(), module_key="nonexistent_module",
                actor_id=None, actor_role="super_admin",
            )

    async def test_disable_module_entitlement_raises_not_found_when_no_active_row(self):
        from app.engines.entitlement.service import EntitlementService, EntitlementNotFoundError
        from app.engines.vertical_catalog.models import Vertical

        svc = EntitlementService()
        vertical = Vertical(id=uuid.uuid4(), key="home_services", label="Home Services", is_enabled=True)
        db = AsyncMock()
        vertical_result = MagicMock(); vertical_result.scalar_one_or_none.return_value = vertical
        no_active_result = MagicMock(); no_active_result.scalar_one_or_none.return_value = None
        db.execute = AsyncMock(side_effect=[vertical_result, no_active_result])

        with pytest.raises(EntitlementNotFoundError):
            await svc.disable_module_entitlement(
                db, tenant_id=uuid.uuid4(), module_key="home_services", actor_id=None, actor_role="super_admin",
            )


class TestCascadeAuditColumnLengths:
    """Regression test for a real bug found via browser E2E testing: disabling
    a module with an active child category entitlement raised a real 500
    (asyncpg.StringDataRightTruncationError) because the cascade audit log
    tried to write 'ACTIVE (parent module inactive)' (32 chars) into
    entitlement_audit_log.new_status, a VARCHAR(20) column. Fixed by keeping
    new_status as a plain, valid status value and moving the explanation
    into the `reason` field (a Text column, no length limit)."""

    def test_all_hardcoded_audit_status_values_fit_the_column(self):
        import ast
        import inspect
        from app.engines.entitlement import service as service_module
        from app.engines.entitlement.models import ENTITLEMENT_STATUSES

        src = inspect.getsource(service_module)
        tree = ast.parse(src)
        for node in ast.walk(tree):
            if isinstance(node, ast.keyword) and node.arg in ("new_status", "previous_status"):
                if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                    value = node.value.value
                    assert len(value) <= 20, f"{node.arg}={value!r} ({len(value)} chars) exceeds VARCHAR(20)"
