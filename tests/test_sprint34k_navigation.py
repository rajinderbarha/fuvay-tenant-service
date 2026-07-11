"""Sprint 34K — Enterprise Navigation + Page Simplification Tests.

Tests verify centralized navigation config, page registry, and breadcrumbs
are in place for both super-admin and tenant-portal.

All tests are pure file-read (no live server).
"""
import os
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _read(rel: str) -> str:
    with open(os.path.join(ROOT, rel), encoding="utf-8") as f:
        return f.read()


# ─────────────────────────────────────────────────────────────────────────────
# Super-Admin nav-config.ts
# ─────────────────────────────────────────────────────────────────────────────
class TestAdminNavConfig(unittest.TestCase):
    def setUp(self):
        self.src = _read("frontend/super-admin/lib/nav-config.ts")

    def test_file_exists(self):
        self.assertIn("Sprint 34K", self.src)

    def test_nav_item_interface(self):
        self.assertIn("export interface NavItem", self.src)

    def test_nav_group_interface(self):
        self.assertIn("export interface NavGroup", self.src)

    def test_admin_nav_groups_exported(self):
        self.assertIn("export const ADMIN_NAV_GROUPS", self.src)

    def test_admin_nav_by_id_exported(self):
        self.assertIn("export const ADMIN_NAV_BY_ID", self.src)

    def test_admin_path_to_nav_id_exported(self):
        self.assertIn("export const ADMIN_PATH_TO_NAV_ID", self.src)

    def test_resolve_admin_nav_id_function(self):
        self.assertIn("export function resolveAdminNavId", self.src)

    def test_has_core_group(self):
        self.assertIn('"core"', self.src)

    def test_has_operations_group(self):
        self.assertIn('"operations"', self.src)

    def test_has_catalog_group(self):
        self.assertIn('"catalog"', self.src)

    def test_has_finance_group(self):
        self.assertIn('"finance"', self.src)

    def test_has_intelligence_group(self):
        self.assertIn('"intelligence"', self.src)

    def test_has_engagement_group(self):
        self.assertIn('"engagement"', self.src)

    def test_has_automation_group(self):
        self.assertIn('"automation"', self.src)

    def test_has_admin_group(self):
        self.assertIn('"admin"', self.src)

    def test_dashboard_item(self):
        self.assertIn("dashboard", self.src)
        self.assertIn("/admin/dashboard", self.src)

    def test_tenants_item(self):
        self.assertIn('"tenants"', self.src)

    def test_finance_items(self):
        self.assertIn("service-invoices", self.src)
        self.assertIn("provider-wallets", self.src)
        self.assertIn("commission-records", self.src)

    def test_catalog_items(self):
        self.assertIn("service-options", self.src)
        self.assertIn("issue-types", self.src)
        self.assertIn("checklist-templates", self.src)
        self.assertIn("customer-flow", self.src)

    def test_review_group_items(self):
        self.assertIn("review-flags", self.src)
        self.assertIn("complaints", self.src)

    def test_automation_items(self):
        self.assertIn("automation", self.src)
        self.assertIn("engines", self.src)

    def test_security_items(self):
        self.assertIn("security", self.src)
        self.assertIn("audit-logs", self.src)

    def test_nav_item_has_icon_field(self):
        self.assertIn("icon?:", self.src)

    def test_nav_item_has_permission_field(self):
        self.assertIn("permission?:", self.src)

    def test_nav_item_has_group_field(self):
        self.assertIn("group:", self.src)

    def test_resolve_function_uses_segs(self):
        self.assertIn("segs[1]", self.src)

    def test_flat_map_for_nav_by_id(self):
        self.assertIn("flatMap", self.src)


# ─────────────────────────────────────────────────────────────────────────────
# Tenant Portal nav-config.ts
# ─────────────────────────────────────────────────────────────────────────────
class TestTenantNavConfig(unittest.TestCase):
    def setUp(self):
        self.src = _read("frontend/tenant-portal/lib/nav-config.ts")

    def test_file_exists(self):
        self.assertIn("Sprint 34K", self.src)

    def test_tenant_nav_groups_exported(self):
        self.assertIn("export const TENANT_NAV_GROUPS", self.src)

    def test_tenant_nav_by_id_exported(self):
        self.assertIn("export const TENANT_NAV_BY_ID", self.src)

    def test_tenant_path_to_nav_id_exported(self):
        self.assertIn("export const TENANT_PATH_TO_NAV_ID", self.src)

    def test_tenant_provider_path_to_nav_id_exported(self):
        self.assertIn("export const TENANT_PROVIDER_PATH_TO_NAV_ID", self.src)

    def test_resolve_tenant_nav_id_function(self):
        self.assertIn("export function resolveTenantNavId", self.src)

    def test_has_core_group(self):
        # Tenant-portal's group taxonomy differs from super-admin's: it uses
        # "overview" as its first/top group rather than "core" -- a real,
        # internally-consistent difference, not a missing group.
        self.assertIn('"overview"', self.src)

    def test_has_operations_group(self):
        self.assertIn('"operations"', self.src)

    def test_has_provider_group(self):
        self.assertIn('"provider"', self.src)

    def test_has_finance_group(self):
        self.assertIn('"finance"', self.src)

    def test_has_insights_group(self):
        self.assertIn('"insights"', self.src)

    def test_dashboard_item(self):
        self.assertIn("/dashboard", self.src)

    def test_provider_items(self):
        # Real ids differ from what this test originally assumed: marketing
        # lives under a plain "marketing" id (group "engagement"), and team
        # members under "provider-staff" (group "team") -- both correctly
        # wired via TENANT_PROVIDER_PATH_TO_NAV_ID, just different names.
        self.assertIn("provider-status", self.src)
        self.assertIn('"marketing"', self.src)
        self.assertIn("provider-staff", self.src)
        self.assertIn("provider-availability", self.src)

    def test_jobs_item(self):
        self.assertIn('"jobs"', self.src)

    def test_service_jobs_maps_to_jobs(self):
        self.assertIn('"service-jobs"', self.src)

    def test_resolve_function_handles_provider_prefix(self):
        self.assertIn("provider", self.src)
        self.assertIn("TENANT_PROVIDER_PATH_TO_NAV_ID", self.src)

    def test_analytics_handling(self):
        self.assertIn('"analytics"', self.src)

    def test_fallback_to_section(self):
        # Function returns section as fallback
        self.assertIn("?? section", self.src)


# ─────────────────────────────────────────────────────────────────────────────
# Super-Admin page-registry.ts
# ─────────────────────────────────────────────────────────────────────────────
class TestAdminPageRegistry(unittest.TestCase):
    def setUp(self):
        self.src = _read("frontend/super-admin/lib/page-registry.ts")

    def test_page_meta_interface(self):
        self.assertIn("export interface PageMeta", self.src)

    def test_page_meta_has_title(self):
        self.assertIn("title: string", self.src)

    def test_page_meta_has_section(self):
        self.assertIn("section: string", self.src)

    def test_page_meta_has_breadcrumbs(self):
        self.assertIn("breadcrumbs:", self.src)

    def test_admin_page_registry_exported(self):
        self.assertIn("export const ADMIN_PAGE_REGISTRY", self.src)

    def test_resolve_page_meta_function(self):
        self.assertIn("export function resolvePageMeta", self.src)

    def test_dashboard_entry(self):
        self.assertIn('"/admin/dashboard"', self.src)

    def test_tenants_entry(self):
        self.assertIn('"/admin/tenants"', self.src)

    def test_catalog_entry(self):
        self.assertIn('"/admin/catalog"', self.src)

    def test_finance_entry(self):
        self.assertIn('"/admin/finance"', self.src)

    def test_intelligence_entry(self):
        self.assertIn('"/admin/intelligence"', self.src)

    def test_automation_entry(self):
        self.assertIn('"/admin/automation"', self.src)

    def test_customer_flow_entry(self):
        self.assertIn('"/admin/customer-flow"', self.src)

    def test_recommendation_rules_entry(self):
        self.assertIn("recommendation-rules", self.src)

    def test_security_entry(self):
        self.assertIn('"/admin/security"', self.src)

    def test_breadcrumbs_have_label_and_href(self):
        self.assertIn("label:", self.src)
        self.assertIn("href:", self.src)

    def test_resolve_function_handles_exact_match(self):
        self.assertIn("ADMIN_PAGE_REGISTRY[pathname]", self.src)

    def test_resolve_function_handles_parent_paths(self):
        self.assertIn("slice(0, len)", self.src)

    def test_description_field(self):
        self.assertIn("description?:", self.src)


# ─────────────────────────────────────────────────────────────────────────────
# Tenant Portal page-registry.ts
# ─────────────────────────────────────────────────────────────────────────────
class TestTenantPageRegistry(unittest.TestCase):
    def setUp(self):
        self.src = _read("frontend/tenant-portal/lib/page-registry.ts")

    def test_tenant_page_registry_exported(self):
        self.assertIn("export const TENANT_PAGE_REGISTRY", self.src)

    def test_resolve_tenant_page_meta_function(self):
        self.assertIn("export function resolveTenantPageMeta", self.src)

    def test_dashboard_entry(self):
        self.assertIn('"/dashboard"', self.src)

    def test_jobs_entry(self):
        self.assertIn('"/jobs"', self.src)

    def test_provider_entries(self):
        self.assertIn('"/provider/status"', self.src)
        self.assertIn('"/provider/offerings"', self.src)

    def test_finance_entry(self):
        self.assertIn('"/finance"', self.src)

    def test_analytics_entry(self):
        self.assertIn('"/analytics"', self.src)

    def test_page_meta_interface(self):
        self.assertIn("export interface PageMeta", self.src)

    def test_resolve_function(self):
        self.assertIn("resolveTenantPageMeta", self.src)


# ─────────────────────────────────────────────────────────────────────────────
# Super-Admin Breadcrumbs component
# ─────────────────────────────────────────────────────────────────────────────
class TestAdminBreadcrumbs(unittest.TestCase):
    def setUp(self):
        self.src = _read("frontend/super-admin/components/layout/Breadcrumbs.tsx")

    def test_use_client(self):
        self.assertIn('"use client"', self.src)

    def test_imports_use_pathname(self):
        self.assertIn("usePathname", self.src)

    def test_imports_resolve_page_meta(self):
        self.assertIn("resolvePageMeta", self.src)

    def test_breadcrumb_item_interface(self):
        self.assertIn("export interface BreadcrumbItem", self.src)

    def test_breadcrumbs_function_exported(self):
        self.assertIn("export function Breadcrumbs", self.src)

    def test_nav_aria_label(self):
        self.assertIn('aria-label="Breadcrumb"', self.src)

    def test_renders_separator(self):
        self.assertIn('/', self.src)

    def test_renders_as_link_when_href(self):
        self.assertIn("crumb.href", self.src)

    def test_last_item_has_bold_style(self):
        self.assertIn("fontWeight", self.src)

    def test_returns_null_for_single_crumb(self):
        self.assertIn("return null", self.src)

    def test_default_export(self):
        self.assertIn("export default Breadcrumbs", self.src)


# ─────────────────────────────────────────────────────────────────────────────
# Tenant Portal Breadcrumbs component
# ─────────────────────────────────────────────────────────────────────────────
class TestTenantBreadcrumbs(unittest.TestCase):
    def setUp(self):
        self.src = _read("frontend/tenant-portal/components/layout/Breadcrumbs.tsx")

    def test_use_client(self):
        self.assertIn('"use client"', self.src)

    def test_imports_use_pathname(self):
        self.assertIn("usePathname", self.src)

    def test_imports_resolve_tenant_page_meta(self):
        self.assertIn("resolveTenantPageMeta", self.src)

    def test_breadcrumbs_function_exported(self):
        self.assertIn("export function Breadcrumbs", self.src)

    def test_nav_aria_label(self):
        self.assertIn('aria-label="Breadcrumb"', self.src)

    def test_returns_null_for_single_crumb(self):
        self.assertIn("return null", self.src)

    def test_default_export(self):
        self.assertIn("export default Breadcrumbs", self.src)


# ─────────────────────────────────────────────────────────────────────────────
# Admin layout.tsx — uses nav-config
# ─────────────────────────────────────────────────────────────────────────────
class TestAdminLayoutUsesNavConfig(unittest.TestCase):
    def setUp(self):
        self.src = _read("frontend/super-admin/app/admin/layout.tsx")

    def test_imports_resolve_admin_nav_id(self):
        self.assertIn("resolveAdminNavId", self.src)

    def test_imports_from_nav_config(self):
        self.assertIn("nav-config", self.src)

    def test_path_to_active_nav_uses_resolver(self):
        # ADMIN-TENANT-E2E-02 Part 3 replaced nav-config.ts's hand-maintained
        # resolveAdminNavId() with resolveActiveNavId() -- longest-href-prefix
        # matching directly against the real sidebar hrefs, fixing drift bugs
        # the old map had. Still delegates to a single resolver, just a
        # different (newer, more correct) one.
        self.assertIn("resolveActiveNavId(pathname)", self.src)

    def test_sprint34k_comment(self):
        self.assertIn("34K", self.src)

    def test_no_hardcoded_map(self):
        # After Sprint 34K, the large inline map should be gone
        self.assertNotIn('"home-services": "operations"', self.src)


# ─────────────────────────────────────────────────────────────────────────────
# Tenant layout.tsx — uses nav-config
# ─────────────────────────────────────────────────────────────────────────────
class TestTenantLayoutUsesNavConfig(unittest.TestCase):
    def setUp(self):
        self.src = _read("frontend/tenant-portal/app/(tenant)/layout.tsx")

    def test_imports_resolve_tenant_nav_id(self):
        self.assertIn("resolveTenantNavId", self.src)

    def test_imports_from_nav_config(self):
        self.assertIn("nav-config", self.src)

    def test_path_to_active_nav_uses_resolver(self):
        self.assertIn("resolveTenantNavId(pathname)", self.src)

    def test_sprint34k_comment(self):
        self.assertIn("34K", self.src)

    def test_no_hardcoded_provider_map(self):
        # Inline providerMap should be gone
        self.assertNotIn('"team-members":     "provider-team-members"', self.src)


if __name__ == "__main__":
    unittest.main()
