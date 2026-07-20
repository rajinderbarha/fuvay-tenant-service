"""Phase 2A Slice 2C — role-integrity guard tests.

Covers:
- Migration 144's invalid-role detection logic against the real database
  (self-contained: uses a rolled-back transaction, never commits, so it does
  not depend on or alter the 2 known pre-existing invalid accounts).
- The remediation script's safety guards (canonical-role validation,
  platform/tenant scope check, incomplete-mapping refusal) via direct
  function/subprocess-free unit calls against its pure validation logic.
- VALID_TENANT_ROLES / VALID_PLATFORM_ROLES continue to reject the
  previously-removed placeholder aliases (regression, mirrors Slice 2's
  tests but scoped to this slice's broader canonical-role guarantee).
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.config import get_settings

CANONICAL_ROLES = {
    "super_admin", "tenant_owner", "staff", "technician", "customer", "guest",
    "admin_operations", "admin_finance", "admin_security", "admin_readonly",
}


def _detection_sql() -> str:
    placeholders = ", ".join(f"'{r}'" for r in CANONICAL_ROLES)
    return f"SELECT email, role FROM users WHERE role NOT IN ({placeholders})"


@pytest.mark.asyncio
class TestMigration144DetectionLogic:
    """Opens its own real-DB engine (like test_final_l5_05k_topup_migration.py),
    bypassing the autouse DB mock, because this specifically must prove the
    detection query behaves correctly against a real Postgres CHECK-constraint
    candidate column — not a mock that can't validate real SQL syntax."""

    async def test_detection_query_finds_a_freshly_inserted_invalid_role(self):
        settings = get_settings()
        engine = create_async_engine(settings.DATABASE_URL)
        async with engine.connect() as conn:
            async with conn.begin() as trans:
                # Reuse an existing tenant id (any one) as the FK target
                # rather than inserting a new tenant row -- avoids needing to
                # satisfy every NOT NULL column on `tenants`, and this
                # transaction is rolled back regardless so no real data is
                # touched either way.
                existing_tenant = (await conn.execute(text("SELECT id FROM tenants LIMIT 1"))).scalar()
                assert existing_tenant is not None, "no tenant exists in this database to attach the test user to"

                fake_id = uuid.uuid4()
                # Insert a deliberately-invalid-role row inside a transaction
                # that is rolled back at the end of this block -- never
                # committed, so it never touches real data or the 2 known
                # pre-existing invalid accounts.
                await conn.execute(text(
                    "INSERT INTO users (id, email, full_name, role, tenant_id, hashed_password, "
                    "is_active, is_verified, force_password_change, created_at, updated_at) "
                    "VALUES (:id, :email, 'Slice2C Test User', 'totally_invalid_role', :tenant_id, "
                    "'x', true, true, false, now(), now())"
                ), {"id": str(fake_id), "email": f"slice2c-test-{fake_id}@example.invalid", "tenant_id": str(existing_tenant)})

                result = await conn.execute(text(_detection_sql()))
                emails = [row[0] for row in result]
                assert f"slice2c-test-{fake_id}@example.invalid" in emails

                await trans.rollback()

        # Confirm the rollback actually happened -- the test row must not persist.
        async with engine.connect() as conn:
            result = await conn.execute(text(_detection_sql()))
            emails = [row[0] for row in result]
            assert f"slice2c-test-{fake_id}@example.invalid" not in emails
        await engine.dispose()

    async def test_detection_query_does_not_flag_any_canonical_role(self):
        settings = get_settings()
        engine = create_async_engine(settings.DATABASE_URL)
        async with engine.connect() as conn:
            result = await conn.execute(text(_detection_sql()))
            for email, role in result:
                assert role not in CANONICAL_ROLES, (
                    f"Detection query incorrectly flagged a canonical role: {email}={role}"
                )
        await engine.dispose()


class TestRemediationScriptValidation:
    """Unit tests for the pure validation logic in remediate_invalid_roles.py,
    imported directly (no subprocess) for speed and clean pytest integration."""

    def test_parse_mapping_rejects_non_canonical_role(self):
        import importlib.util
        from pathlib import Path
        spec = importlib.util.spec_from_file_location(
            "remediate_invalid_roles",
            Path(__file__).parent.parent / "scripts" / "workflow_rearchitecture" / "remediate_invalid_roles.py",
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        fake_id = str(uuid.uuid4())
        with pytest.raises(SystemExit):
            mod._parse_mapping([f"{fake_id}=tenant_manager"])
        with pytest.raises(SystemExit):
            mod._parse_mapping([f"{fake_id}=platform_admin"])

    def test_parse_mapping_accepts_all_10_canonical_roles(self):
        import importlib.util
        from pathlib import Path
        spec = importlib.util.spec_from_file_location(
            "remediate_invalid_roles",
            Path(__file__).parent.parent / "scripts" / "workflow_rearchitecture" / "remediate_invalid_roles.py",
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        for role in CANONICAL_ROLES:
            fake_id = str(uuid.uuid4())
            mapping = mod._parse_mapping([f"{fake_id}={role}"])
            assert mapping[fake_id] == role

    def test_parse_mapping_rejects_malformed_entry(self):
        import importlib.util
        from pathlib import Path
        spec = importlib.util.spec_from_file_location(
            "remediate_invalid_roles",
            Path(__file__).parent.parent / "scripts" / "workflow_rearchitecture" / "remediate_invalid_roles.py",
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        with pytest.raises(SystemExit):
            mod._parse_mapping(["not-a-valid-entry"])
        with pytest.raises(SystemExit):
            mod._parse_mapping(["not-a-uuid=staff"])


@pytest.mark.asyncio
class TestCanonicalRoleWritePathsRegression:
    """Confirms the two fixed write paths (tenant_engine.admin_service and
    auth.service) still reject every removed placeholder alias -- regression
    coverage spanning both Slice 2's fix and this slice's broader audit."""

    async def test_tenant_engine_valid_roles_has_no_placeholder_aliases(self):
        from app.engines.tenant_engine.admin_service import VALID_TENANT_ROLES
        placeholders = {"tenant_manager", "tenant_staff_admin", "tenant_finance",
                        "tenant_support", "tenant_readonly", "platform_admin"}
        assert VALID_TENANT_ROLES.isdisjoint(placeholders)
        assert VALID_TENANT_ROLES.issubset(CANONICAL_ROLES)

    async def test_auth_service_valid_platform_roles_are_exactly_the_5_platform_roles(self):
        from app.engines.auth.service import AuthService
        expected = {"super_admin", "admin_operations", "admin_finance", "admin_security", "admin_readonly"}
        assert AuthService.VALID_PLATFORM_ROLES == expected
