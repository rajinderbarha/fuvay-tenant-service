"""Sprint 35 — Admin + Tenant Full Connectivity Tests.

Verifies that all critical admin and tenant pages have functioning backend endpoints.
Tests cover:
  - Category Runtime Router (/v1/admin/categories/*)
  - Tenant Dashboard Runtime (/v1/tenant/dashboard/runtime)
  - Tenant Staff Security (tenant-scoped /v1/tenant/staff/*)
  - Audit Log endpoint corrections
  - Brands deduplication
  - Service-Options/Issue-Types double-unwrap fix
  - Portal summary endpoints
"""
import importlib
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


def _exists(rel: str) -> bool:
    return os.path.isfile(os.path.join(ROOT, rel))


def _read(rel: str) -> str:
    path = os.path.join(ROOT, rel)
    if not os.path.isfile(path):
        return ""
    with open(path, encoding="utf-8") as f:
        return f.read()


class TestCategoryRuntimeRouter(unittest.TestCase):
    """Phase 1 — Category Runtime Router backend file existence and structure."""

    def setUp(self):
        self.src = _read("app/engines/admin_catalog/category_runtime_router.py")

    def test_router_file_exists(self):
        self.assertTrue(_exists("app/engines/admin_catalog/category_runtime_router.py"))

    def test_router_has_correct_prefix(self):
        self.assertIn('prefix="/v1/admin/categories"', self.src)

    def test_list_categories_endpoint(self):
        self.assertIn('async def list_categories', self.src)

    def test_get_category_endpoint(self):
        self.assertIn('async def get_category', self.src)

    def test_activate_category_endpoint(self):
        self.assertIn('async def activate_category', self.src)

    def test_deactivate_category_endpoint(self):
        self.assertIn('async def deactivate_category', self.src)

    def test_get_runtime_endpoint(self):
        self.assertIn('async def get_category_runtime', self.src)

    def test_update_runtime_endpoint(self):
        self.assertIn('async def update_category_runtime', self.src)

    def test_list_engines_endpoint(self):
        self.assertIn('async def list_category_engines', self.src)

    def test_list_dashboard_modules_endpoint(self):
        self.assertIn('async def list_dashboard_modules', self.src)

    def test_enable_engine_endpoint(self):
        self.assertIn('async def enable_category_engine', self.src)

    def test_disable_engine_endpoint(self):
        self.assertIn('async def disable_category_engine', self.src)

    def test_set_primary_engine_endpoint(self):
        self.assertIn('async def set_primary_engine', self.src)

    def test_enable_module_endpoint(self):
        self.assertIn('async def enable_module', self.src)

    def test_disable_module_endpoint(self):
        self.assertIn('async def disable_module', self.src)

    def test_imports_admin_catalog_service(self):
        self.assertIn('from app.engines.admin_catalog.service import AdminCatalogService', self.src)


class TestMainPyCategoryRuntimeRegistration(unittest.TestCase):
    """Phase 2 — category_runtime_router registered in main.py."""

    def setUp(self):
        self.src = _read("app/main.py")

    def test_category_runtime_import(self):
        self.assertIn('category_runtime_router', self.src)

    def test_category_runtime_import_path(self):
        self.assertIn('from app.engines.admin_catalog.category_runtime_router import router as category_runtime_router', self.src)

    def test_category_runtime_included(self):
        self.assertIn('app.include_router(category_runtime_router)', self.src)


class TestTenantDashboardRuntime(unittest.TestCase):
    """Phase 3 — /v1/tenant/dashboard/runtime endpoint exists."""

    def setUp(self):
        self.src = _read("app/engines/tenant_engine/portal_router.py")

    def test_dashboard_runtime_endpoint(self):
        self.assertIn('"/dashboard/runtime"', self.src)

    def test_dashboard_runtime_function(self):
        self.assertIn('async def get_dashboard_runtime', self.src)

    def test_runtime_returns_category_type(self):
        self.assertIn('category_type', self.src)

    def test_runtime_returns_provider_dashboard_type(self):
        self.assertIn('provider_dashboard_type', self.src)

    def test_runtime_returns_customer_flow_type(self):
        self.assertIn('customer_flow_type', self.src)

    def test_runtime_returns_primary_engine_key(self):
        self.assertIn('primary_engine_key', self.src)


class TestTenantStaffSecurityEndpoints(unittest.TestCase):
    """Phase 4 — Tenant-scoped staff security endpoints in portal_router.py."""

    def setUp(self):
        self.src = _read("app/engines/tenant_engine/portal_router.py")

    def test_lock_staff_endpoint(self):
        self.assertIn('"/staff/{user_id}/lock"', self.src)

    def test_unlock_staff_endpoint(self):
        self.assertIn('"/staff/{user_id}/unlock"', self.src)

    def test_revoke_sessions_endpoint(self):
        self.assertIn('"/staff/{user_id}/sessions/revoke-all"', self.src)

    def test_login_history_endpoint(self):
        self.assertIn('"/staff/{user_id}/login-history"', self.src)

    def test_security_status_endpoint(self):
        self.assertIn('"/staff/{user_id}/security"', self.src)

    def test_uses_require_tenant_owner(self):
        self.assertIn('require_tenant_owner', self.src)

    def test_uses_full_security_status(self):
        self.assertIn('get_full_security_status', self.src)

    def test_uses_admin_revoke_all_sessions(self):
        self.assertIn('admin_revoke_all_sessions', self.src)


class TestTenantPortalApiFix(unittest.TestCase):
    """Phase 5 — Tenant portal api.ts updated to use /v1/tenant/staff/* endpoints."""

    def setUp(self):
        self.src = _read("frontend/tenant-portal/lib/api.ts")

    def test_lock_staff_uses_tenant_endpoint(self):
        self.assertIn('/v1/tenant/staff/${userId}/lock', self.src)

    def test_unlock_staff_uses_tenant_endpoint(self):
        self.assertIn('/v1/tenant/staff/${userId}/unlock', self.src)

    def test_revoke_sessions_uses_tenant_endpoint(self):
        self.assertIn('/v1/tenant/staff/${userId}/sessions/revoke-all', self.src)

    def test_login_history_uses_tenant_endpoint(self):
        self.assertIn('/v1/tenant/staff/${userId}/login-history', self.src)

    def test_security_status_uses_tenant_endpoint(self):
        self.assertIn('/v1/tenant/staff/${userId}/security', self.src)

    def test_no_admin_users_lock(self):
        self.assertNotIn('/v1/admin/users/${userId}/lock', self.src)

    def test_no_admin_users_unlock(self):
        self.assertNotIn('/v1/admin/users/${userId}/unlock', self.src)

    def test_no_admin_users_sessions(self):
        self.assertNotIn('/v1/admin/users/${userId}/sessions/revoke-all', self.src)


class TestServiceOptionsDoubleUnwrapFix(unittest.TestCase):
    """Phase 6 — Double-unwrap bug fixed in service-options/page.tsx."""

    def setUp(self):
        self.src = _read("frontend/super-admin/app/admin/service-setup/service-options/page.tsx")

    def test_no_double_unwrap(self):
        self.assertNotIn('.data.items', self.src)

    def test_no_data_wrapper(self):
        self.assertNotIn('}).data;', self.src)

    def test_uses_direct_items(self):
        self.assertIn('result.items', self.src)

    def test_uses_direct_total(self):
        self.assertIn('result.total', self.src)


class TestIssueTypesDoubleUnwrapFix(unittest.TestCase):
    """Phase 7 — Double-unwrap bug fixed in issue-types/page.tsx."""

    def setUp(self):
        self.src = _read("frontend/super-admin/app/admin/service-setup/issue-types/page.tsx")

    def test_no_double_unwrap(self):
        self.assertNotIn('.data.items', self.src)

    def test_no_data_wrapper(self):
        self.assertNotIn('}).data;', self.src)

    def test_uses_direct_items(self):
        self.assertIn('result.items', self.src)

    def test_uses_direct_total(self):
        self.assertIn('result.total', self.src)


class TestAuditLogsEndpointFix(unittest.TestCase):
    """Phase 8 — Audit-logs page uses correct endpoint paths."""

    def setUp(self):
        self.src = _read("frontend/super-admin/app/admin/audit-logs/page.tsx")

    def test_engine_audit_uses_admin_audit_logs(self):
        self.assertIn('/v1/admin/audit-logs', self.src)

    def test_security_audit_uses_correct_path(self):
        self.assertIn('/v1/security/audit-log', self.src)

    def test_auth_audit_uses_correct_path(self):
        self.assertIn('/v1/admin/audit-logs/login-events', self.src)

    def test_no_wrong_engine_audit_path(self):
        self.assertNotIn('/v1/engines/audit-logs', self.src)

    def test_no_wrong_security_path(self):
        self.assertNotIn('/v1/admin/security/audit', self.src)

    def test_no_wrong_auth_path(self):
        self.assertNotIn('/v1/auth/audit"', self.src)


class TestBrandsDuplicateRemoved(unittest.TestCase):
    """Phase 9 — Sprint 3 duplicate brands removed from admin_catalog/admin_router.py."""

    def setUp(self):
        self.src = _read("app/engines/admin_catalog/admin_router.py")

    def test_no_duplicate_list_brands(self):
        # The old Sprint 3 endpoint that competed with Sprint 34D
        self.assertNotIn('@router.get("/brands"', self.src)

    def test_no_duplicate_create_brand(self):
        self.assertNotIn('@router.post("/brands"', self.src)

    def test_no_duplicate_delete_brand(self):
        self.assertNotIn('@router.delete("/brands/{brand_id}"', self.src)

    def test_comment_explains_removal(self):
        self.assertIn('brand_admin_router', self.src)


class TestDashboardSummaryEndpoints(unittest.TestCase):
    """Phase 10 — Dashboard summary endpoints added to portal_router."""

    def setUp(self):
        self.src = _read("app/engines/tenant_engine/portal_router.py")

    def test_home_services_summary(self):
        self.assertIn('"/dashboard/home-services/summary"', self.src)

    def test_coaching_summary(self):
        self.assertIn('"/dashboard/coaching/summary"', self.src)

    def test_real_estate_summary(self):
        self.assertIn('"/dashboard/real-estate/summary"', self.src)


class TestCategoryRuntimeRouterParseable(unittest.TestCase):
    """Phase 11 — category_runtime_router.py is syntactically valid Python."""

    def test_can_be_parsed(self):
        import ast
        src = _read("app/engines/admin_catalog/category_runtime_router.py")
        self.assertTrue(len(src) > 100, "File appears empty")
        try:
            ast.parse(src)
        except SyntaxError as e:
            self.fail(f"Syntax error in category_runtime_router.py: {e}")


class TestPortalRouterParseable(unittest.TestCase):
    """Phase 12 — portal_router.py is syntactically valid Python after additions."""

    def test_can_be_parsed(self):
        import ast
        src = _read("app/engines/tenant_engine/portal_router.py")
        self.assertTrue(len(src) > 100, "File appears empty")
        try:
            ast.parse(src)
        except SyntaxError as e:
            self.fail(f"Syntax error in portal_router.py: {e}")


class TestAdminCatalogRouterParseable(unittest.TestCase):
    """Phase 13 — admin_catalog/admin_router.py is syntactically valid after brand removal."""

    def test_can_be_parsed(self):
        import ast
        src = _read("app/engines/admin_catalog/admin_router.py")
        self.assertTrue(len(src) > 100, "File appears empty")
        try:
            ast.parse(src)
        except SyntaxError as e:
            self.fail(f"Syntax error in admin_router.py: {e}")


class TestMainPyParseable(unittest.TestCase):
    """Phase 14 — main.py is syntactically valid Python after router additions."""

    def test_can_be_parsed(self):
        import ast
        src = _read("app/main.py")
        self.assertTrue(len(src) > 100, "File appears empty")
        try:
            ast.parse(src)
        except SyntaxError as e:
            self.fail(f"Syntax error in main.py: {e}")


class TestCategoryRuntimeApiCalls(unittest.TestCase):
    """Phase 15 — Admin frontend categoryRuntimeApi calls match new backend endpoints."""

    def setUp(self):
        self.src = _read("frontend/super-admin/lib/api.ts")

    def test_list_categories_endpoint(self):
        # Should call /v1/admin/categories not /v1/admin/service-categories for runtime
        self.assertIn('/v1/admin/categories', self.src)

    def test_activate_endpoint(self):
        self.assertIn('/activate', self.src)

    def test_deactivate_endpoint(self):
        self.assertIn('/deactivate', self.src)

    def test_engines_endpoint(self):
        self.assertIn('/engines', self.src)

    def test_dashboard_modules_endpoint(self):
        self.assertIn('/dashboard-modules', self.src)


class TestTenantDashboardApiCalls(unittest.TestCase):
    """Phase 16 — Tenant portal categoryDashboardApi calls correct backend endpoints."""

    def setUp(self):
        self.src = _read("frontend/tenant-portal/lib/api.ts")

    def test_runtime_endpoint_correct(self):
        self.assertIn('/v1/tenant/dashboard/runtime', self.src)

    def test_navigation_endpoint_correct(self):
        self.assertIn('/v1/tenant/navigation', self.src)

    def test_home_services_summary_endpoint(self):
        self.assertIn('/v1/tenant/dashboard/home-services/summary', self.src)

    def test_coaching_summary_endpoint(self):
        self.assertIn('/v1/tenant/dashboard/coaching/summary', self.src)

    def test_real_estate_summary_endpoint(self):
        self.assertIn('/v1/tenant/dashboard/real-estate/summary', self.src)


if __name__ == "__main__":
    unittest.main(verbosity=2)
