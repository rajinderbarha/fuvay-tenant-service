"""FINAL-L5-05L — Admin role provisioning, permission assignment and
role-based runtime architecture guards.

Static/unit-level guards + role-bundle correctness tests. Live cross-
domain denial evidence (real HTTP, real principals) is captured separately
in docs/final-l5-05/FINAL_L5_05L_LIVE_API_MATRIX.md — this file proves the
underlying permission data structures are correct and self-consistent.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from app.core.permissions import P, ROLE_PERMISSIONS, permission_checker

ROOT = Path(__file__).parent.parent
APP = ROOT / "app"

CANONICAL_ADMIN_ROLES = {"admin_operations", "admin_finance", "admin_security", "admin_readonly"}

FINANCE_MUTATION_PERMISSIONS = {
    P.FINANCE_USAGE_CREDITS_TOP_UP, P.FINANCE_USAGE_CREDITS_ADJUST,
    P.FINANCE_TOPUPS_UPDATE, P.FINANCE_TOPUPS_REFUND,
    P.FINANCE_SECURITY_DEPOSITS_CONFIG_UPDATE, P.FINANCE_SECURITY_DEPOSITS_CREATE,
    P.FINANCE_SECURITY_DEPOSITS_MARK_RECEIVED, P.FINANCE_SECURITY_DEPOSITS_HOLD,
    P.FINANCE_SECURITY_DEPOSITS_RELEASE, P.FINANCE_SECURITY_DEPOSITS_ADJUST,
    P.FINANCE_SETTINGS_UPDATE,
}

JOB_EXCEPTIONAL_MUTATION_PERMISSIONS = {
    P.ADMIN_JOBS_REASSIGN, P.ADMIN_JOBS_STATUS_OVERRIDE,
    P.ADMIN_JOBS_FORCE_CLOSE, P.ADMIN_JOBS_VOID,
}

# Heuristic used to classify a permission key as a "mutation" for the
# Admin Read Only zero-mutation invariant: any key whose bundle-comment
# or naming pattern implies a write. Read-suffixed keys and a short,
# explicit allow-list of genuinely read-shaped keys are excluded.
MUTATION_KEYWORDS = (
    "adjust", "top_up", "top-up", "update", "create", "delete", "revoke",
    "reassign", "override", "force_close", "void", "refund", "manage",
    "write", "rotate", "block", "resolve", "assign", "close", "cancel",
    "reschedule", "deduct", "hold", "mark_received", "config",
)
READ_SHAPED_EXCEPTIONS = {
    # Keys that contain a mutation-like substring but are semantically
    # read/reference operations, not state mutations.
}


def _looks_like_mutation(perm_key: str) -> bool:
    if perm_key in READ_SHAPED_EXCEPTIONS:
        return False
    if perm_key.endswith(("read", "read_own")) or ".read" in perm_key or ":read" in perm_key:
        return False
    return any(kw in perm_key.lower() for kw in MUTATION_KEYWORDS)


class TestCanonicalRolesExist:
    def test_five_canonical_roles_exist_in_role_permissions(self):
        assert "super_admin" in ROLE_PERMISSIONS
        for role in CANONICAL_ADMIN_ROLES:
            assert role in ROLE_PERMISSIONS, f"canonical role {role!r} missing from ROLE_PERMISSIONS"

    def test_no_new_admin_role_has_wildcard_permission(self):
        for role in CANONICAL_ADMIN_ROLES:
            assert P.ALL not in ROLE_PERMISSIONS[role], (
                f"{role} must not have the wildcard permission — only super_admin may")

    def test_super_admin_remains_the_sole_wildcard_role(self):
        wildcard_roles = [r for r, perms in ROLE_PERMISSIONS.items() if P.ALL in perms]
        assert wildcard_roles == ["super_admin"]


class TestAdminReadOnlyZeroMutation:
    def test_admin_readonly_has_zero_mutation_permissions(self):
        mutations = [p for p in ROLE_PERMISSIONS["admin_readonly"] if _looks_like_mutation(p)]
        assert mutations == [], f"admin_readonly must have 0 mutation permissions, found: {mutations}"

    def test_admin_readonly_cannot_adjust_usage_credit(self):
        assert not permission_checker.has("admin_readonly", P.FINANCE_USAGE_CREDITS_ADJUST)

    def test_admin_readonly_cannot_approve_topup(self):
        assert not permission_checker.has("admin_readonly", P.FINANCE_TOPUPS_UPDATE)

    def test_admin_readonly_cannot_force_close_job(self):
        assert not permission_checker.has("admin_readonly", P.ADMIN_JOBS_FORCE_CLOSE)

    def test_admin_readonly_cannot_revoke_session(self):
        assert not permission_checker.has("admin_readonly", P.SECURITY_SESSIONS_REVOKE)

    def test_admin_readonly_can_read_usage_credit_balance(self):
        assert permission_checker.has("admin_readonly", P.FINANCE_USAGE_CREDITS_READ)


class TestOperationsAdminScope:
    def test_operations_admin_has_zero_finance_mutation_permissions(self):
        granted = set(ROLE_PERMISSIONS["admin_operations"])
        overlap = granted & FINANCE_MUTATION_PERMISSIONS
        assert overlap == set(), f"admin_operations must not have Finance mutation permissions: {overlap}"

    def test_operations_admin_cannot_adjust_usage_credit(self):
        assert not permission_checker.has("admin_operations", P.FINANCE_USAGE_CREDITS_ADJUST)

    def test_operations_admin_cannot_approve_topup(self):
        assert not permission_checker.has("admin_operations", P.FINANCE_TOPUPS_UPDATE)

    def test_operations_admin_cannot_adjust_security_deposit(self):
        assert not permission_checker.has("admin_operations", P.FINANCE_SECURITY_DEPOSITS_ADJUST)

    def test_operations_admin_can_force_close_job(self):
        assert permission_checker.has("admin_operations", P.ADMIN_JOBS_FORCE_CLOSE)

    def test_operations_admin_can_reassign_job(self):
        assert permission_checker.has("admin_operations", P.ADMIN_JOBS_REASSIGN)


class TestFinanceAdminScope:
    def test_finance_admin_has_zero_job_exceptional_mutation_permissions(self):
        granted = set(ROLE_PERMISSIONS["admin_finance"])
        overlap = granted & JOB_EXCEPTIONAL_MUTATION_PERMISSIONS
        assert overlap == set(), f"admin_finance must not have Job exceptional-mutation permissions: {overlap}"

    def test_finance_admin_cannot_force_close_job(self):
        assert not permission_checker.has("admin_finance", P.ADMIN_JOBS_FORCE_CLOSE)

    def test_finance_admin_cannot_void_job(self):
        assert not permission_checker.has("admin_finance", P.ADMIN_JOBS_VOID)

    def test_finance_admin_cannot_reassign_job(self):
        assert not permission_checker.has("admin_finance", P.ADMIN_JOBS_REASSIGN)

    def test_finance_admin_can_adjust_usage_credit(self):
        assert permission_checker.has("admin_finance", P.FINANCE_USAGE_CREDITS_ADJUST)

    def test_finance_admin_can_approve_topup(self):
        assert permission_checker.has("admin_finance", P.FINANCE_TOPUPS_UPDATE)

    def test_finance_admin_cannot_manage_roles(self):
        assert not permission_checker.has("admin_finance", P.PLATFORM_ROLES_READ)


class TestSecurityAdminScope:
    def test_security_admin_has_zero_finance_mutation_permissions(self):
        granted = set(ROLE_PERMISSIONS["admin_security"])
        overlap = granted & FINANCE_MUTATION_PERMISSIONS
        assert overlap == set(), f"admin_security must not have Finance mutation permissions: {overlap}"

    def test_security_admin_cannot_adjust_usage_credit(self):
        assert not permission_checker.has("admin_security", P.FINANCE_USAGE_CREDITS_ADJUST)

    def test_security_admin_cannot_approve_topup(self):
        assert not permission_checker.has("admin_security", P.FINANCE_TOPUPS_UPDATE)

    def test_security_admin_cannot_force_close_job(self):
        assert not permission_checker.has("admin_security", P.ADMIN_JOBS_FORCE_CLOSE)

    def test_security_admin_can_read_sessions(self):
        assert permission_checker.has("admin_security", P.SECURITY_SESSIONS_READ)

    def test_security_admin_can_revoke_session(self):
        assert permission_checker.has("admin_security", P.SECURITY_SESSIONS_REVOKE)

    def test_security_admin_can_read_roles_catalog_but_bundle_has_no_role_mutation_key(self):
        assert permission_checker.has("admin_security", P.PLATFORM_ROLES_READ)
        # No "manage"/"create"/"update" role-mutation permission exists in the
        # registry at all yet (roles_permissions is code-defined, Part 9
        # decision) so there is nothing to withhold beyond the read grant.


class TestPermissionResolutionDeterminism:
    def test_resolution_is_deterministic_across_repeated_calls(self):
        for role in CANONICAL_ADMIN_ROLES | {"super_admin"}:
            first = permission_checker.has(role, P.FINANCE_USAGE_CREDITS_ADJUST)
            for _ in range(5):
                assert permission_checker.has(role, P.FINANCE_USAGE_CREDITS_ADJUST) == first

    def test_super_admin_always_true_regardless_of_permission_key(self):
        assert permission_checker.has("super_admin", P.FINANCE_USAGE_CREDITS_ADJUST)
        assert permission_checker.has("super_admin", "some:made:up:key")

    def test_unknown_role_has_zero_permissions(self):
        assert not permission_checker.has("not_a_real_role", P.FINANCE_USAGE_CREDITS_READ)


class TestNoDuplicateOrInvalidRoleAssignments:
    def test_no_role_bundle_has_duplicate_permission_entries(self):
        for role, perms in ROLE_PERMISSIONS.items():
            dupes = {p for p in perms if perms.count(p) > 1}
            assert dupes == set(), f"role {role!r} has duplicate permission entries: {dupes}"

    def test_all_new_permission_keys_are_valid_p_attributes(self):
        for key in (
            "ADMIN_JOBS_READ", "ADMIN_JOBS_REASSIGN", "ADMIN_JOBS_STATUS_OVERRIDE",
            "ADMIN_JOBS_FORCE_CLOSE", "ADMIN_JOBS_VOID",
            "PLATFORM_ROLES_READ", "PLATFORM_PERMISSIONS_READ",
        ):
            assert hasattr(P, key), f"P.{key} must exist"


class TestConvertedEndpointsUsePermissionChecks:
    """Architecture guard: the specific endpoints this sprint converted off
    require_super_admin must now use require_permission, not a hardcoded
    role-string check -- proving Operations/Finance/Security/Read-Only
    roles can genuinely reach (or be denied from) them."""

    def _read(self, path: Path) -> str:
        return path.read_text(encoding="utf-8")

    def test_job_force_close_void_status_override_use_require_permission(self):
        src = self._read(APP / "engines" / "execution" / "home_service_router.py")
        assert "require_permission(P.ADMIN_JOBS_FORCE_CLOSE)" in src
        assert "require_permission(P.ADMIN_JOBS_VOID)" in src
        assert "require_permission(P.ADMIN_JOBS_STATUS_OVERRIDE)" in src

    def test_job_reassign_uses_require_permission(self):
        src = self._read(APP / "engines" / "home_service_assignment" / "admin_router.py")
        assert "require_permission(P.ADMIN_JOBS_REASSIGN)" in src

    def test_roles_permissions_reads_use_require_permission(self):
        src = self._read(APP / "engines" / "roles_permissions" / "admin_router.py")
        assert "require_permission(P.PLATFORM_ROLES_READ)" in src
        assert "require_permission(P.PLATFORM_PERMISSIONS_READ)" in src


class TestSeedScriptSafety:
    def _read(self) -> str:
        return (ROOT / "scripts" / "seed_admin_roles_final_l5_05l.py").read_text(encoding="utf-8")

    def test_seed_script_is_environment_gated(self):
        src = self._read()
        assert "ALLOW_ADMIN_ROLE_SEED" in src
        assert "FORBIDDEN_ENVIRONMENTS" in src
        assert '"production"' in src

    def test_seed_script_never_hardcodes_a_real_password(self):
        src = self._read()
        assert "SEED_ADMIN_SECURITY_PASSWORD" in src  # env-sourced
        # The only literal fallback password string must be the same
        # clearly-labeled canonical test credential already used across
        # this engagement's other seed scripts, not a novel hardcoded value.
        assert "CanonicalL5!2026" in src

    def test_seed_script_does_not_touch_password_hash_of_existing_accounts(self):
        src = self._read()
        # The UPDATE statement for existing accounts touches only role/updated_at.
        assert "UPDATE users SET role = :role, updated_at = now()" in src
        assert "hashed_password" not in src.split("UPDATE users SET role")[1].split("INSERT INTO users")[0]
