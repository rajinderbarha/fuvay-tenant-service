"""Slice 2F-39: negative/positive tests for canonical_seed_final_l5_01.py's
new fail-closed role guard (_require_canonical_role / CANONICAL_ROLES).

2F-38 found scripts/canonical_seed_final_l5_01.py::get_or_create_user() had
zero role validation -- it would insert any string as a user's role,
including "tenant_manager"/"tenant_readonly" (the exact source of this
program's two known invalid-role demo accounts). This file proves the fix:
invalid roles are rejected before any database call, canonical roles are
accepted, existing-user role mismatches are surfaced (not silently
promoted), and the fix is idempotent.
"""
from __future__ import annotations

import importlib.util
import os
import sys
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

pytestmark = pytest.mark.asyncio


def _load_seed_module():
    path = Path(__file__).parent.parent / "scripts" / "canonical_seed_final_l5_01.py"
    spec = importlib.util.spec_from_file_location("canonical_seed_final_l5_01_2f39", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _exploding_db():
    """A db object that raises if touched, to prove rejection happens
    before any query is attempted."""
    db = MagicMock()
    db.execute = AsyncMock(side_effect=AssertionError("must not reach the database"))
    return db


class TestCanonicalRolesRegistry:
    def test_canonical_roles_is_exactly_the_10_role_set(self):
        mod = _load_seed_module()
        assert mod.CANONICAL_ROLES == frozenset({
            "super_admin", "tenant_owner", "staff", "technician", "customer", "guest",
            "admin_operations", "admin_finance", "admin_security", "admin_readonly",
        })

    def test_canonical_roles_is_derived_from_role_permissions_not_a_second_list(self):
        mod = _load_seed_module()
        from app.core.permissions import ROLE_PERMISSIONS
        assert mod.CANONICAL_ROLES == frozenset(ROLE_PERMISSIONS.keys())


class TestRequireCanonicalRoleRejectsBeforeDbCall:
    @pytest.mark.parametrize("invalid_role", [
        "tenant_manager", "tenant_readonly", "manager", "readonly",
        "office_staff", "tenant_finance", "operations_manager",
        "finance_manager", "security_manager", "platform_manager",
    ])
    async def test_alias_rejected_before_any_db_call(self, invalid_role):
        mod = _load_seed_module()
        db = _exploding_db()
        with pytest.raises(ValueError, match="non-canonical role"):
            await mod.get_or_create_user(db, "test@example.invalid", "Test User", invalid_role)
        db.execute.assert_not_awaited()

    async def test_empty_role_rejected(self):
        mod = _load_seed_module()
        db = _exploding_db()
        with pytest.raises(ValueError, match="non-canonical role"):
            await mod.get_or_create_user(db, "test@example.invalid", "Test User", "")
        db.execute.assert_not_awaited()

    async def test_mixed_case_variant_rejected(self):
        """Proves no silent case-normalization exists -- 'Staff' is not
        treated as equivalent to 'staff'."""
        mod = _load_seed_module()
        db = _exploding_db()
        with pytest.raises(ValueError, match="non-canonical role"):
            await mod.get_or_create_user(db, "test@example.invalid", "Test User", "Staff")
        db.execute.assert_not_awaited()

    @pytest.mark.parametrize("valid_role", [
        "super_admin", "tenant_owner", "staff", "technician", "customer", "guest",
        "admin_operations", "admin_finance", "admin_security", "admin_readonly",
    ])
    async def test_every_canonical_role_is_accepted(self, valid_role):
        mod = _load_seed_module()
        db = MagicMock()
        # No existing row -> proceeds to INSERT.
        select_result = MagicMock()
        select_result.first.return_value = None
        insert_result = MagicMock()
        db.execute = AsyncMock(side_effect=[select_result, insert_result])
        uid = await mod.get_or_create_user(db, f"{valid_role}@example.invalid", "Test User", valid_role)
        assert isinstance(uid, uuid.UUID)
        assert db.execute.await_count == 2


class TestExistingUserRoleMismatch:
    async def test_existing_user_with_matching_role_is_skipped_quietly(self, capsys):
        mod = _load_seed_module()
        db = MagicMock()
        existing_id = uuid.uuid4()
        select_result = MagicMock()
        select_result.first.return_value = (existing_id, "staff")
        db.execute = AsyncMock(return_value=select_result)
        uid = await mod.get_or_create_user(db, "existing@example.invalid", "Existing User", "staff")
        assert uid == existing_id
        assert db.execute.await_count == 1  # SELECT only, no INSERT
        assert "role mismatch" not in capsys.readouterr().out

    async def test_existing_user_with_mismatched_role_is_not_silently_promoted(self, capsys):
        """Proves the function never UPDATEs an existing user's role to
        match a new request -- this would be silent privilege promotion."""
        mod = _load_seed_module()
        db = MagicMock()
        existing_id = uuid.uuid4()
        select_result = MagicMock()
        select_result.first.return_value = (existing_id, "customer")
        db.execute = AsyncMock(return_value=select_result)
        uid = await mod.get_or_create_user(db, "existing@example.invalid", "Existing User", "super_admin")
        assert uid == existing_id
        assert db.execute.await_count == 1  # SELECT only -- no UPDATE/INSERT ever executed
        out = capsys.readouterr().out
        assert "role mismatch" in out
        assert "NOT modified" in out


class TestIdempotency:
    async def test_repeated_call_with_same_canonical_role_is_idempotent(self):
        mod = _load_seed_module()
        db = MagicMock()
        existing_id = uuid.uuid4()
        select_result = MagicMock()
        select_result.first.return_value = (existing_id, "technician")
        db.execute = AsyncMock(return_value=select_result)
        uid1 = await mod.get_or_create_user(db, "tech@example.invalid", "Tech", "technician")
        uid2 = await mod.get_or_create_user(db, "tech@example.invalid", "Tech", "technician")
        assert uid1 == uid2 == existing_id


class TestManagerReadonlyNoLongerSeeded:
    def test_manager_demo_account_literal_removed_from_seed_source(self):
        """Slice 2F-39 removed the two get_or_create_user() call sites that
        hardcoded 'tenant_manager'/'tenant_readonly' as a role argument --
        confirms no live call passes these values, not merely that they're
        unreachable. (Explanatory comments mentioning the strings in prose
        are fine and expected; this checks for the call-site pattern.)"""
        seed_source = (Path(__file__).parent.parent / "scripts" / "canonical_seed_final_l5_01.py").read_text()
        assert 'get_or_create_user(db, "manager@demo-ac-services.local"' not in seed_source
        assert 'get_or_create_user(db, "readonly@demo-ac-services.local"' not in seed_source
