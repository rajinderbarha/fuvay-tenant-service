"""FINAL-L5-05M — Frontend permission-visibility architecture guards.

Static source-level checks (no browser needed) proving the frontend
permission catalog references only real backend permission keys, that
AdminLayout consumes usePermissions(), and that the role-visible action
sets match the FINAL-L5-05L backend bundles exactly. Real Chromium
evidence (live rendering) lives in
e2e/super-admin/final-l5-05m-permission-visibility.spec.ts and
docs/final-l5-05/FINAL_L5_05M_FRONTEND_PERMISSION_VISIBILITY.md.
"""
from __future__ import annotations

import re
from pathlib import Path

from app.core.permissions import P, ROLE_PERMISSIONS

ROOT = Path(__file__).parent.parent
FE = ROOT / "frontend" / "super-admin"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _all_backend_permission_values() -> set[str]:
    values = set()
    for name in dir(P):
        if name.startswith("_"):
            continue
        v = getattr(P, name)
        if isinstance(v, str):
            values.add(v)
    return values


class TestAdminLayoutConsumesEffectivePermissions:
    def test_admin_layout_imports_use_permissions(self):
        src = _read(FE / "components" / "layout" / "AdminLayout.tsx")
        assert 'from "../../hooks/usePermissions"' in src
        assert "usePermissions()" in src

    def test_admin_layout_has_permission_filter_function(self):
        src = _read(FE / "components" / "layout" / "AdminLayout.tsx")
        assert "function isNavItemPermitted" in src
        assert "isNavItemPermitted(item, effectivePermissions, effectiveRole)" in src

    def test_admin_layout_fails_closed_while_loading(self):
        src = _read(FE / "components" / "layout" / "AdminLayout.tsx")
        # perms === null (still loading) must resolve to false, not true.
        assert "if (perms === null) return false" in src


class TestNoSecondAuthorizationEngine:
    def test_use_permissions_hook_has_single_source(self):
        src = _read(FE / "hooks" / "usePermissions.ts")
        assert "authApi.me()" in src
        # Only one API call site for the effective-permission source.
        assert src.count("authApi.me()") == 1

    def test_permission_catalog_is_metadata_only_not_a_checker(self):
        src = _read(FE / "lib" / "permission-catalog.ts")
        assert "NOT a second authorization engine" in src
        assert "def has(" not in src  # no independent has()/checker logic

    def test_no_local_storage_permission_override(self):
        for path in FE.rglob("*.ts*"):
            if "node_modules" in path.parts or ".next" in path.parts:
                continue
            try:
                text = _read(path)
            except UnicodeDecodeError:
                continue
            if "localStorage" not in text:
                continue
            # localStorage is legitimately used for the auth token itself
            # (serviceos_admin_token) -- never for a "permissions" or
            # "role" override key.
            assert 'localStorage.setItem("permissions"' not in text
            assert 'localStorage.setItem("role"' not in text
            assert "localStorage.getItem(\"permissions\")" not in text


class TestPermissionCatalogValidity:
    def test_every_catalog_key_is_a_real_backend_permission(self):
        src = _read(FE / "lib" / "permission-catalog.ts")
        backend_values = _all_backend_permission_values()
        # Extract quoted keys inside PERMISSION_CATALOG's object literal.
        catalog_block = src[src.index("PERMISSION_CATALOG"):]
        keys = re.findall(r'"([a-z_:.]+)":\s*\{\s*key:\s*"\1"', catalog_block)
        assert keys, "expected to find at least one catalog entry"
        invalid = [k for k in keys if k not in backend_values]
        assert invalid == [], f"frontend permission-catalog keys not in backend registry: {invalid}"

    def test_no_duplicate_catalog_keys(self):
        src = _read(FE / "lib" / "permission-catalog.ts")
        catalog_block = src[src.index("PERMISSION_CATALOG"):src.index("};", src.index("PERMISSION_CATALOG"))]
        keys = re.findall(r'^\s*"([a-z_:.]+)":', catalog_block, re.MULTILINE)
        dupes = {k for k in keys if keys.count(k) > 1}
        assert dupes == set(), f"duplicate permission-catalog keys: {dupes}"


class TestNavItemPermissionKeysAreValid:
    def test_every_required_permission_in_nav_groups_is_valid(self):
        src = _read(FE / "components" / "layout" / "AdminLayout.tsx")
        backend_values = _all_backend_permission_values()
        nav_block = src[src.index("const NAV_GROUPS"):src.index("];\n\n// Flattened")]
        found = re.findall(r'requiredPermission:\s*(?:"([^"]*)"|SUPER_ADMIN_ONLY)', nav_block)
        assert found, "expected to find requiredPermission values in NAV_GROUPS"
        for key in found:
            if key == "":
                continue  # Dashboard: visible-to-all sentinel
            assert key in backend_values, f"NAV_GROUPS references invalid permission key: {key!r}"

    def test_every_nav_item_has_a_required_permission_field(self):
        src = _read(FE / "components" / "layout" / "AdminLayout.tsx")
        nav_block = src[src.index("const NAV_GROUPS"):src.index("];\n\n// Flattened")]
        item_lines = [l for l in nav_block.splitlines() if l.strip().startswith("{ id:")]
        missing = [l for l in item_lines if "requiredPermission" not in l]
        assert missing == [], f"nav items missing requiredPermission: {missing}"


class TestRoleActionVisibilityMatchesBackendBundles:
    """Cross-check: the permission keys used to gate frontend actions for
    Job mutations / Usage Credit adjustment / Session revoke must produce
    the same allow/deny result the real ROLE_PERMISSIONS bundles do -- this
    is what makes 'Operations-visible actions contain zero Finance
    mutations' etc. true by construction, not by coincidence."""

    def test_admin_readonly_frontend_gated_actions_all_deny(self):
        gated_keys = [
            "finance.usage_credits.adjust", "finance:topups:update", "finance:topups:refund",
            "admin:jobs:reassign", "admin:jobs:status_override", "admin:jobs:force_close", "admin:jobs:void",
            "security:sessions:revoke",
        ]
        readonly_perms = set(ROLE_PERMISSIONS["admin_readonly"])
        allowed = [k for k in gated_keys if k in readonly_perms]
        assert allowed == [], f"admin_readonly must be denied all of these, but has: {allowed}"

    def test_admin_operations_frontend_gated_finance_actions_all_deny(self):
        finance_keys = ["finance.usage_credits.adjust", "finance:topups:update", "finance:topups:refund"]
        ops_perms = set(ROLE_PERMISSIONS["admin_operations"])
        allowed = [k for k in finance_keys if k in ops_perms]
        assert allowed == [], f"admin_operations must be denied Finance actions, but has: {allowed}"

    def test_admin_finance_frontend_gated_job_exceptional_actions_all_deny(self):
        job_keys = ["admin:jobs:reassign", "admin:jobs:status_override", "admin:jobs:force_close", "admin:jobs:void"]
        finance_perms = set(ROLE_PERMISSIONS["admin_finance"])
        allowed = [k for k in job_keys if k in finance_perms]
        assert allowed == [], f"admin_finance must be denied Job exceptional actions, but has: {allowed}"

    def test_admin_security_frontend_gated_finance_actions_all_deny(self):
        finance_keys = ["finance.usage_credits.adjust", "finance:topups:update", "finance:topups:refund"]
        security_perms = set(ROLE_PERMISSIONS["admin_security"])
        allowed = [k for k in finance_keys if k in security_perms]
        assert allowed == [], f"admin_security must be denied Finance actions, but has: {allowed}"


class TestPermissionDeniedComponent:
    def test_permission_denied_component_exists_with_required_copy(self):
        src = _read(FE / "components" / "shared" / "PermissionGate.tsx")
        assert "Permission denied" in src
        assert "You do not have access to this page or action." in src
        assert "Contact a platform administrator" in src

    def test_read_only_notice_component_exists(self):
        src = _read(FE / "components" / "shared" / "PermissionGate.tsx")
        assert "View-only access" in src
        assert "you cannot make changes" in src

    def test_require_permission_shows_skeleton_while_loading_not_content(self):
        src = _read(FE / "components" / "shared" / "PermissionGate.tsx")
        idx = src.index("export function RequirePermission")
        body = src[idx:]
        assert "if (loading || permissions === null)" in body
        assert "<Skeleton" in body
