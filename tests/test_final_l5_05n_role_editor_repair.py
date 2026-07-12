"""FINAL-L5-05N — Platform Users role-editor repair.

Fixes two real, related defects found in FINAL-L5-05M:
1. AuthService.invite_platform_user hardcoded User(role="super_admin", ...)
   for every invited platform user regardless of the platform_role they
   were assigned -- every invite silently granted full super_admin access.
2. AuthService.change_platform_role only wrote User.platform_role (a
   display-only column never consulted by PermissionChecker), never
   User.role (the real, enforced authorization column) -- the role
   dropdown had zero effect on the target's actual backend authorization.

VALID_PLATFORM_ROLES is also corrected from 8 invented labels (only one
of which, "super_admin", matched a real role) down to the 5 real,
enforced role strings from app.core.permissions.ROLE_PERMISSIONS.
"""
from __future__ import annotations

from pathlib import Path

from app.core.permissions import ROLE_PERMISSIONS
from app.engines.auth.service import AuthService

ROOT = Path(__file__).parent.parent


def _read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


class TestValidPlatformRolesMatchRealRoles:
    def test_valid_platform_roles_is_exactly_the_five_real_roles(self):
        assert AuthService.VALID_PLATFORM_ROLES == {
            "super_admin", "admin_operations", "admin_finance",
            "admin_security", "admin_readonly",
        }

    def test_every_valid_platform_role_exists_in_role_permissions(self):
        for role in AuthService.VALID_PLATFORM_ROLES:
            assert role in ROLE_PERMISSIONS, f"{role} is not a real backend role"

    def test_no_invented_role_labels_remain(self):
        src = _read("app/engines/auth/service.py")
        block_start = src.index("VALID_PLATFORM_ROLES = {")
        block_end = src.index("}", block_start)
        block = src[block_start:block_end]
        for invented in ("platform_admin", "compliance_officer", "support_admin",
                          "operations_admin", "finance_admin", "security_admin", "read_only_admin"):
            assert invented not in block, f"invented role label {invented!r} still in VALID_PLATFORM_ROLES"


class TestInvitePlatformUserWritesRealRole:
    def test_invite_sets_role_to_the_selected_platform_role_not_hardcoded_super_admin(self):
        src = _read("app/engines/auth/service.py")
        start = src.index("async def invite_platform_user")
        end = src.index("\n    async def ", start + 10)
        body = src[start:end]
        assert 'role="super_admin"' not in body, "invite still hardcodes role=super_admin"
        assert "role=platform_role" in body


class TestChangePlatformRoleUpdatesRealRole:
    def test_change_platform_role_writes_target_role(self):
        src = _read("app/engines/auth/service.py")
        start = src.index("async def change_platform_role")
        end = src.index("\n    async def ", start + 10)
        body = src[start:end]
        assert "target.role = platform_role" in body
        assert "target.platform_role = platform_role" in body

    def test_change_platform_role_audits_old_and_new_role(self):
        src = _read("app/engines/auth/service.py")
        start = src.index("async def change_platform_role")
        end = src.index("\n    async def ", start + 10)
        body = src[start:end]
        assert '"old_role": old_role' in body
        assert '"new_role": platform_role' in body


class TestRequirePlatformMutateUsesRealRole:
    def test_require_platform_mutate_checks_real_role_column(self):
        src = _read("app/engines/auth/platform_users_router.py")
        start = src.index("async def require_platform_mutate")
        end = src.index("\n\n\n", start)
        body = src[start:end]
        assert 'admin.role == "admin_readonly"' in body
        # The old literal "read_only_admin" comparison (a stale platform_role
        # label) must be gone from the actual executable logic -- only the
        # explanatory docstring prose may still mention it for context.
        docstring_end = body.index('"""', body.index('"""') + 3) + 3
        code_only = body[docstring_end:]
        assert "read_only_admin" not in code_only


class TestPlatformUsersListIncludesAllAdminRoles:
    def test_platform_group_scopes_to_all_five_admin_roles(self):
        src = _read("app/engines/auth/service.py")
        assert '"platform": self.PLATFORM_ADMIN_ROLES' in src

    def test_platform_admin_roles_constant_matches_valid_platform_roles(self):
        assert set(AuthService.PLATFORM_ADMIN_ROLES) == AuthService.VALID_PLATFORM_ROLES

    def test_summary_and_invites_scope_to_all_five_admin_roles(self):
        src = _read("app/engines/auth/service.py")
        assert "User.role.in_(self.PLATFORM_ADMIN_ROLES)" in src


class TestFrontendPlatformRolesDropdownMatchesBackend:
    def test_frontend_platform_roles_match_backend_exactly(self):
        src = _read("frontend/super-admin/app/admin/users/page.tsx")
        start = src.index("const PLATFORM_ROLES")
        end = src.index("];", start)
        block = src[start:end]
        for role in ("super_admin", "admin_operations", "admin_finance", "admin_security", "admin_readonly"):
            assert f'value: "{role}"' in block, f"frontend PLATFORM_ROLES missing {role!r}"
        for invented in ("platform_admin", "compliance_officer", "support_admin",
                          "operations_admin", "finance_admin", "security_admin", "read_only_admin"):
            assert f'value: "{invented}"' not in block, f"frontend PLATFORM_ROLES still has invented label {invented!r}"
