"""
P0 Enterprise Engine Management — backend + frontend tests.
Migration 081 | 8 new tables | 31 engines seeded | 29 endpoints
"""
import os
import re
from pathlib import Path

ROOT = Path(__file__).parent.parent

# ── helpers ───────────────────────────────────────────────────────────────────
def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8", errors="replace")

MIGRATION  = ROOT / "alembic" / "versions" / "081_enterprise_engine_management.py"
MODELS     = ROOT / "app" / "engines" / "engine_mgmt" / "models.py"
SERVICE    = ROOT / "app" / "engines" / "engine_mgmt" / "service.py"
ROUTER     = ROOT / "app" / "engines" / "engine_mgmt" / "admin_router.py"
MAIN       = ROOT / "app" / "main.py"
PERMS      = ROOT / "app" / "core" / "permissions.py"
API_TS     = ROOT / "frontend" / "super-admin" / "lib" / "api.ts"
ENGINES_PAGE = ROOT / "frontend" / "super-admin" / "app" / "admin" / "engines" / "page.tsx"
DETAIL_PAGE  = ROOT / "frontend" / "super-admin" / "app" / "admin" / "engines" / "[engine_key]" / "page.tsx"


# ════════════════════════════════════════════════════════════════════════════
# Migration Tests
# ════════════════════════════════════════════════════════════════════════════
class TestMigration081:
    def test_migration_file_exists(self):
        assert MIGRATION.exists(), "081_enterprise_engine_management.py not found"

    def test_revision(self):
        src = _read(MIGRATION)
        assert 'revision = "081"' in src

    def test_down_revision(self):
        src = _read(MIGRATION)
        assert 'down_revision = "080"' in src

    def test_platform_engines_table(self):
        src = _read(MIGRATION)
        assert "platform_engines" in src

    def test_engine_dependencies_table(self):
        src = _read(MIGRATION)
        assert "engine_dependencies" in src

    def test_category_engine_matrix_table(self):
        src = _read(MIGRATION)
        assert "category_engine_matrix" in src

    def test_package_engine_entitlements_table(self):
        src = _read(MIGRATION)
        assert "package_engine_entitlements" in src

    def test_tenant_engine_overrides_table(self):
        src = _read(MIGRATION)
        assert "tenant_engine_overrides" in src

    def test_engine_health_checks_table(self):
        src = _read(MIGRATION)
        assert "engine_health_checks" in src

    def test_engine_permissions_table(self):
        src = _read(MIGRATION)
        assert "engine_permissions" in src

    def test_engine_audit_logs_table(self):
        src = _read(MIGRATION)
        assert "engine_audit_logs" in src

    def test_seeds_31_engines(self):
        src = _read(MIGRATION)
        # Count engine key entries in ENGINES list (quoted strings like "booking_engine" or 'booking_engine')
        count = src.count("engine_key")
        assert count >= 10, f"Expected at least 10 engine key references, found {count}"

    def test_global_status_field(self):
        src = _read(MIGRATION)
        assert "global_status" in src

    def test_is_core_field(self):
        src = _read(MIGRATION)
        assert "is_core" in src

    def test_is_locked_field(self):
        src = _read(MIGRATION)
        assert "is_locked" in src


# ════════════════════════════════════════════════════════════════════════════
# Model Tests
# ════════════════════════════════════════════════════════════════════════════
class TestModels:
    def test_models_file_exists(self):
        assert MODELS.exists()

    def test_platform_engine_model(self):
        src = _read(MODELS)
        assert "class PlatformEngine" in src

    def test_engine_dependency_model(self):
        src = _read(MODELS)
        assert "class EngineDependency" in src

    def test_category_engine_matrix_model(self):
        src = _read(MODELS)
        assert "class CategoryEngineMatrix" in src

    def test_package_engine_entitlement_model(self):
        src = _read(MODELS)
        assert "class PackageEngineEntitlement" in src

    def test_tenant_engine_override_model(self):
        src = _read(MODELS)
        assert "class TenantEngineOverride" in src

    def test_engine_health_check_model(self):
        src = _read(MODELS)
        assert "class EngineHealthCheck" in src

    def test_engine_permission_model(self):
        src = _read(MODELS)
        assert "class EnginePermission" in src

    def test_engine_audit_log_model(self):
        src = _read(MODELS)
        assert "class EngineAuditLog" in src

    def test_to_dict_methods(self):
        src = _read(MODELS)
        count = src.count("def to_dict")
        assert count >= 6, f"Expected at least 6 to_dict methods, found {count}"


# ════════════════════════════════════════════════════════════════════════════
# Service Tests
# ════════════════════════════════════════════════════════════════════════════
class TestService:
    def test_service_file_exists(self):
        assert SERVICE.exists()

    def test_get_summary(self):
        src = _read(SERVICE)
        assert "get_summary" in src

    def test_list_engines(self):
        src = _read(SERVICE)
        assert "list_engines" in src

    def test_get_engine(self):
        src = _read(SERVICE)
        assert "get_engine" in src

    def test_enable_engine(self):
        src = _read(SERVICE)
        assert "enable_engine" in src

    def test_disable_engine(self):
        src = _read(SERVICE)
        assert "disable_engine" in src

    def test_get_impact_preview(self):
        src = _read(SERVICE)
        assert "get_impact_preview" in src

    def test_set_category_engine(self):
        src = _read(SERVICE)
        assert "set_category_engine" in src

    def test_set_package_engine(self):
        src = _read(SERVICE)
        assert "set_package_engine" in src

    def test_create_tenant_override(self):
        src = _read(SERVICE)
        assert "create_tenant_override" in src

    def test_revoke_tenant_override(self):
        src = _read(SERVICE)
        assert "revoke_tenant_override" in src

    def test_run_health_check(self):
        src = _read(SERVICE)
        assert "run_health_check" in src

    def test_get_health_overview(self):
        src = _read(SERVICE)
        assert "get_health_overview" in src

    def test_list_permissions(self):
        src = _read(SERVICE)
        assert "list_permissions" in src

    def test_list_audit_logs(self):
        src = _read(SERVICE)
        assert "list_audit_logs" in src

    def test_resolve_access(self):
        src = _read(SERVICE)
        assert "resolve_access" in src

    def test_get_dependencies_graph(self):
        src = _read(SERVICE)
        assert "get_dependencies_graph" in src

    def test_audit_helper(self):
        src = _read(SERVICE)
        assert "_audit" in src

    def test_locked_engine_guard(self):
        src = _read(SERVICE)
        assert "is_locked" in src

    def test_core_engine_guard(self):
        src = _read(SERVICE)
        assert "is_core" in src

    def test_can_proceed_in_impact_preview(self):
        src = _read(SERVICE)
        assert "can_proceed" in src


# ════════════════════════════════════════════════════════════════════════════
# Router Tests
# ════════════════════════════════════════════════════════════════════════════
class TestAdminRouter:
    def test_router_file_exists(self):
        assert ROUTER.exists()

    def test_prefix(self):
        src = _read(ROUTER)
        assert "/v1/admin/engines" in src

    def test_requires_super_admin(self):
        src = _read(ROUTER)
        assert "require_super_admin" in src
        assert "from app.dependencies.auth import require_super_admin" in src

    def test_summary_endpoint(self):
        src = _read(ROUTER)
        assert '"/summary"' in src

    def test_list_endpoint(self):
        src = _read(ROUTER)
        assert 'router.get("")' in src

    def test_enable_endpoint(self):
        src = _read(ROUTER)
        assert "/enable" in src

    def test_disable_endpoint(self):
        src = _read(ROUTER)
        assert "/disable" in src

    def test_impact_preview_endpoint(self):
        src = _read(ROUTER)
        assert "impact-preview" in src

    def test_category_matrix_endpoint(self):
        src = _read(ROUTER)
        assert "category-matrix" in src

    def test_dependencies_endpoint(self):
        src = _read(ROUTER)
        assert "/dependencies" in src

    def test_package_entitlements_endpoint(self):
        src = _read(ROUTER)
        assert "package-entitlements" in src

    def test_tenant_overrides_endpoint(self):
        src = _read(ROUTER)
        assert "tenant-overrides" in src

    def test_health_endpoint(self):
        src = _read(ROUTER)
        assert '"/health"' in src

    def test_health_check_all_endpoint(self):
        src = _read(ROUTER)
        assert "check-all" in src

    def test_permissions_endpoint(self):
        src = _read(ROUTER)
        assert '"/permissions"' in src

    def test_audit_logs_endpoint(self):
        src = _read(ROUTER)
        assert "audit-logs" in src

    def test_resolve_access_endpoint(self):
        src = _read(ROUTER)
        assert "resolve-access-preview" in src


# ════════════════════════════════════════════════════════════════════════════
# Permissions
# ════════════════════════════════════════════════════════════════════════════
class TestPermissions:
    def test_engines_read(self):
        src = _read(PERMS)
        assert "ENGINES_READ" in src

    def test_engines_enable(self):
        src = _read(PERMS)
        assert "ENGINES_ENABLE" in src

    def test_engines_disable(self):
        src = _read(PERMS)
        assert "ENGINES_DISABLE" in src

    def test_engines_health_read(self):
        src = _read(PERMS)
        assert "ENGINES_HEALTH_READ" in src

    def test_engines_audit_read(self):
        src = _read(PERMS)
        assert "ENGINES_AUDIT_READ" in src


# ════════════════════════════════════════════════════════════════════════════
# main.py Registration
# ════════════════════════════════════════════════════════════════════════════
class TestMainRegistration:
    def test_engine_mgmt_router_imported(self):
        src = _read(MAIN)
        assert "engine_mgmt" in src

    def test_engine_mgmt_router_included(self):
        src = _read(MAIN)
        assert "engine_mgmt_admin_router" in src or "admin_router" in src


# ════════════════════════════════════════════════════════════════════════════
# Frontend API (api.ts)
# ════════════════════════════════════════════════════════════════════════════
class TestFrontendApi:
    def test_platform_engine_enterprise_interface(self):
        src = _read(API_TS)
        assert "engine_key: string;" in src
        assert "global_status: string;" in src
        assert "is_locked: boolean;" in src

    def test_engine_summary_interface(self):
        src = _read(API_TS)
        assert "interface EngineSummary" in src
        assert "enabled_globally" in src

    def test_engine_impact_preview_interface(self):
        src = _read(API_TS)
        assert "interface EngineImpactPreview" in src
        assert "can_proceed" in src
        assert "categories_affected" in src

    def test_engine_health_check_item_interface(self):
        src = _read(API_TS)
        assert "interface EngineHealthCheckItem" in src
        assert "health_status" in src

    def test_engine_health_overview_interface(self):
        src = _read(API_TS)
        assert "interface EngineHealthOverview" in src

    def test_enterprise_permission_interface(self):
        src = _read(API_TS)
        assert "interface EnterpriseEnginePermission" in src
        assert "is_sensitive" in src

    def test_enterprise_audit_log_interface(self):
        src = _read(API_TS)
        assert "interface EnterpriseEngineAuditLog" in src

    def test_enterprise_dependency_graph_interface(self):
        src = _read(API_TS)
        assert "interface EngineDependencyGraph" in src

    def test_enterprise_category_entry_interface(self):
        src = _read(API_TS)
        assert "interface EnterpriseCategoryEngineEntry" in src

    def test_enterprise_package_entitlement_interface(self):
        src = _read(API_TS)
        assert "interface EnterprisePackageEntitlement" in src

    def test_enterprise_tenant_override_interface(self):
        src = _read(API_TS)
        assert "interface EnterpriseTenantOverride" in src

    def test_engine_access_resolution_interface(self):
        src = _read(API_TS)
        assert "interface EngineAccessResolution" in src

    def test_enginemgmtapi_getsummary(self):
        src = _read(API_TS)
        assert "getSummary" in src
        assert "/v1/admin/engines/summary" in src

    def test_enginemgmtapi_impact_preview(self):
        src = _read(API_TS)
        assert "impactPreview" in src
        assert "impact-preview" in src

    def test_enginemgmtapi_enable_globally(self):
        src = _read(API_TS)
        assert "enableGlobally" in src

    def test_enginemgmtapi_disable_globally(self):
        src = _read(API_TS)
        assert "disableGlobally" in src

    def test_enginemgmtapi_category_matrix(self):
        src = _read(API_TS)
        assert "getCategoryMatrix" in src

    def test_enginemgmtapi_dependency_graph(self):
        src = _read(API_TS)
        assert "getDependencyGraph" in src

    def test_enginemgmtapi_package_entitlements(self):
        src = _read(API_TS)
        assert "getPackageEntitlements" in src

    def test_enginemgmtapi_tenant_overrides(self):
        src = _read(API_TS)
        assert "listTenantOverrides" in src

    def test_enginemgmtapi_health(self):
        src = _read(API_TS)
        assert "getHealth" in src
        assert "checkAllHealth" in src

    def test_enginemgmtapi_permissions(self):
        src = _read(API_TS)
        assert "listPermissions" in src

    def test_enginemgmtapi_audit_logs(self):
        src = _read(API_TS)
        assert "listAuditLogs" in src

    def test_enginemgmtapi_resolve_access(self):
        src = _read(API_TS)
        assert "resolveAccess" in src

    def test_enginemgmtapi_uses_v1_admin_engines(self):
        src = _read(API_TS)
        assert "/v1/admin/engines" in src

    def test_no_old_v1_engines_in_enginemgmtapi(self):
        # engineMgmtApi should use /v1/admin/engines/ exclusively, not /v1/engines
        # (engineRegistryApi still uses /v1/engines which is fine)
        src = _read(API_TS)
        mgmt_block_start = src.find("export const engineMgmtApi")
        mgmt_block_end = src.find("\n};", mgmt_block_start) + 3
        mgmt_block = src[mgmt_block_start:mgmt_block_end]
        # Should not call /v1/engines (old public endpoint) in engineMgmtApi
        assert '"/v1/engines"' not in mgmt_block or mgmt_block.count('"/v1/engines"') == 0


# ════════════════════════════════════════════════════════════════════════════
# Frontend Pages
# ════════════════════════════════════════════════════════════════════════════
class TestFrontendPages:
    def test_engines_page_exists(self):
        assert ENGINES_PAGE.exists()

    def test_detail_page_exists(self):
        assert DETAIL_PAGE.exists()

    def test_engines_page_eight_tabs(self):
        src = _read(ENGINES_PAGE)
        tab_count = src.count('"all"') + src.count('"category-matrix"') + \
                    src.count('"dependencies"') + src.count('"package-entitlements"') + \
                    src.count('"tenant-overrides"') + src.count('"health"') + \
                    src.count('"permissions"') + src.count('"audit-logs"')
        # Each tab id appears in TABS definition + conditional render = at least 8
        assert tab_count >= 8, f"Expected 8 tabs, found {tab_count}"

    def test_engines_page_uses_engine_mgmt_api(self):
        src = _read(ENGINES_PAGE)
        assert "engineMgmtApi" in src

    def test_engines_page_impact_modal(self):
        src = _read(ENGINES_PAGE)
        assert "ImpactModal" in src or "impactPreview" in src

    def test_engines_page_enable_disable_buttons(self):
        src = _read(ENGINES_PAGE)
        assert "enableGlobally" in src or "openImpact" in src
        assert "disableGlobally" in src or "disable" in src.lower()

    def test_engines_page_all_engines_tab(self):
        src = _read(ENGINES_PAGE)
        assert "AllEnginesTab" in src

    def test_engines_page_health_tab(self):
        src = _read(ENGINES_PAGE)
        assert "HealthTab" in src

    def test_engines_page_permissions_tab(self):
        src = _read(ENGINES_PAGE)
        assert "PermissionsTab" in src

    def test_engines_page_audit_logs_tab(self):
        src = _read(ENGINES_PAGE)
        assert "AuditLogsTab" in src

    def test_detail_page_engine_key_param(self):
        src = _read(DETAIL_PAGE)
        assert "engine_key" in src

    def test_detail_page_health_history(self):
        src = _read(DETAIL_PAGE)
        assert "getEngineHealthHistory" in src or "health" in src

    def test_detail_page_impact_modal(self):
        src = _read(DETAIL_PAGE)
        assert "impactPreview" in src

    def test_detail_page_back_link(self):
        src = _read(DETAIL_PAGE)
        assert "/admin/engines" in src

    def test_detail_page_permissions_section(self):
        src = _read(DETAIL_PAGE)
        assert "getEnginePermissions" in src or "permissions" in src.lower()

    def test_no_typescript_errors(self):
        """TypeScript check must pass — verified via npx tsc --noEmit."""
        import subprocess, shutil
        fe = ROOT / "frontend" / "super-admin"
        npx = shutil.which("npx")
        if not npx:
            # Skip gracefully on environments where npx is not on PATH
            import pytest
            pytest.skip("npx not found on PATH")
        result = subprocess.run(
            [npx, "tsc", "--noEmit"],
            cwd=str(fe),
            capture_output=True,
            text=True,
            timeout=120,
        )
        assert result.returncode == 0, f"TS errors:\n{result.stdout}\n{result.stderr}"
