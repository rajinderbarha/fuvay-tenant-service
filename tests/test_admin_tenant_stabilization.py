"""
Admin/Tenant Stabilization tests.

Verifies:
- AdminLayout nav includes all required pages (no orphans)
- All nav hrefs have corresponding page.tsx files
- Complaints page is wired into the nav (Sprint 75)
- Service Groups page is wired into the nav
- Key API clients exist for nav-linked pages
- Tenant portal fallback nav routes have corresponding pages
- No duplicate nav items in either portal
"""
import os, re, ast
import pytest

ADMIN_LAYOUT = os.path.join(os.path.dirname(__file__),
    "../frontend/super-admin/components/layout/AdminLayout.tsx")
# Sprint 38 (migration 089) moved per-vertical Service Catalog items out of a
# static AdminLayout NAV_GROUPS block into DB-driven catalog_module_definitions,
# rendered dynamically by VerticalCatalogSection. These hrefs now live in the
# migration's seed data, not as literal strings in AdminLayout.tsx.
CATALOG_MODULES_SEED = os.path.join(os.path.dirname(__file__),
    "../alembic/versions/089_multi_vertical_catalog_architecture.py")
TENANT_LAYOUT = os.path.join(os.path.dirname(__file__),
    "../frontend/tenant-portal/components/layout/TenantLayout.tsx")
ADMIN_APP = os.path.join(os.path.dirname(__file__),
    "../frontend/super-admin/app/admin")
TENANT_APP = os.path.join(os.path.dirname(__file__),
    "../frontend/tenant-portal/app/(tenant)")
ADMIN_API = os.path.join(os.path.dirname(__file__),
    "../frontend/super-admin/lib/api.ts")
TENANT_API = os.path.join(os.path.dirname(__file__),
    "../frontend/tenant-portal/lib/api.ts")


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def admin_layout_src():
    return read(ADMIN_LAYOUT)


def tenant_layout_src():
    return read(TENANT_LAYOUT)


# ── Helper: extract hrefs from AdminLayout NAV_GROUPS ─────────────────────────
def extract_admin_hrefs():
    src = admin_layout_src()
    # Match href: "/admin/..." patterns
    return re.findall(r'href:\s*"(/admin/[^"]+)"', src)


def extract_tenant_fallback_hrefs():
    src = tenant_layout_src()
    # Match href: "/..." patterns inside NAV_GROUPS_FALLBACK block
    idx = src.find("NAV_GROUPS_FALLBACK")
    if idx == -1:
        return []
    # Take next 3000 chars
    block = src[idx: idx + 3000]
    return re.findall(r'href:\s*"(/[^"]+)"', block)


# ── Admin layout nav file existence ───────────────────────────────────────────
def test_admin_layout_exists():
    assert os.path.exists(ADMIN_LAYOUT), "AdminLayout.tsx missing"


def test_tenant_layout_exists():
    assert os.path.exists(TENANT_LAYOUT), "TenantLayout.tsx missing"


def test_admin_nav_complaints_present():
    """Complaints page must appear in admin nav (Sprint 75 enterprise board)."""
    src = admin_layout_src()
    assert '"/admin/complaints"' in src, \
        "Complaints href missing from AdminLayout NAV_GROUPS"


def test_admin_nav_service_groups_present():
    """Service Groups must appear in admin nav -- dynamically, via the
    catalog_module_definitions seed rendered by VerticalCatalogSection
    (migration 089), not as a static AdminLayout NAV_GROUPS entry."""
    assert "VerticalCatalogSection" in admin_layout_src(), \
        "AdminLayout no longer renders dynamic per-vertical catalog modules"
    assert '"/admin/service-groups"' in read(CATALOG_MODULES_SEED), \
        "Service Groups href missing from catalog_module_definitions seed"


def test_admin_nav_categories_present():
    src = admin_layout_src()
    assert '"/admin/categories"' in src


def test_admin_nav_master_services_present():
    """See test_admin_nav_service_groups_present -- dynamic per-vertical nav."""
    assert '"/admin/master-services"' in read(CATALOG_MODULES_SEED)


def test_admin_nav_issue_types_present():
    """See test_admin_nav_service_groups_present -- dynamic per-vertical nav."""
    assert '"/admin/issue-types"' in read(CATALOG_MODULES_SEED)


def test_admin_nav_service_options_present():
    """See test_admin_nav_service_groups_present -- dynamic per-vertical nav."""
    assert '"/admin/service-options"' in read(CATALOG_MODULES_SEED)


def test_admin_nav_bookings_present():
    src = admin_layout_src()
    assert '"/admin/bookings"' in src


def test_admin_nav_customers_present():
    src = admin_layout_src()
    assert '"/admin/customers"' in src


def test_admin_nav_staff_present():
    src = admin_layout_src()
    assert '"/admin/staff"' in src


def test_admin_nav_reviews_present():
    src = admin_layout_src()
    assert '"/admin/reviews"' in src


def test_admin_nav_analytics_present():
    src = admin_layout_src()
    assert '"/admin/analytics"' in src


def test_admin_nav_marketing_present():
    src = admin_layout_src()
    assert '"/admin/marketing"' in src


def test_admin_nav_engines_present():
    src = admin_layout_src()
    assert '"/admin/engines"' in src


def test_admin_nav_audit_logs_present():
    src = admin_layout_src()
    assert '"/admin/audit-logs"' in src


def test_admin_nav_intelligence_present():
    src = admin_layout_src()
    assert '"/admin/intelligence"' in src


# ── Admin: all nav hrefs resolve to page files ────────────────────────────────
@pytest.mark.parametrize("href", [
    "/admin/dashboard",
    "/admin/tenants",
    "/admin/tenants/onboarding",
    "/admin/onboarding/providers",
    "/admin/packages",
    "/admin/bookings",
    "/admin/operations",
    "/admin/customers",
    "/admin/staff",
    "/admin/reviews",
    "/admin/complaints",
    "/admin/categories",
    "/admin/service-groups",
    "/admin/master-services",
    "/admin/types-brands",
    "/admin/service-options",
    "/admin/issue-types",
    "/admin/pricing-tiers",
    "/admin/location-mapping",
    "/admin/pricing-rules",
    "/admin/finance",
    "/admin/compliance",
    "/admin/marketing",
    "/admin/notifications",
    "/admin/brands",
    "/admin/brand-requests",
    "/admin/analytics",
    "/admin/intelligence",
    "/admin/engines",
    "/admin/security",
    "/admin/workflow-templates",
    "/admin/audit-logs",
    "/admin/users",
    "/admin/media",
    "/admin/settings",
])
def test_admin_nav_page_exists(href):
    """Every admin nav href must have a corresponding page.tsx or redirect."""
    # Strip /admin/ prefix to get relative path
    rel = href.replace("/admin/", "")
    page = os.path.join(ADMIN_APP, rel, "page.tsx")
    assert os.path.exists(page), f"Missing page.tsx for nav href {href} (expected at {page})"


# ── Admin: no duplicate nav ids ───────────────────────────────────────────────
def test_admin_nav_no_duplicate_ids():
    src = admin_layout_src()
    ids = re.findall(r'id:\s*"([^"]+)"', src)
    duplicates = {x for x in ids if ids.count(x) > 1}
    assert not duplicates, f"Duplicate nav item ids in AdminLayout: {duplicates}"


def test_admin_nav_no_duplicate_hrefs():
    hrefs = extract_admin_hrefs()
    duplicates = {x for x in hrefs if hrefs.count(x) > 1}
    assert not duplicates, f"Duplicate nav hrefs in AdminLayout: {duplicates}"


# ── Admin: complaints icon imported ──────────────────────────────────────────
def test_admin_complaints_icon_imported():
    src = admin_layout_src()
    # AlertOctagon or MessageSquareWarning should be imported
    assert "AlertOctagon" in src or "MessageSquareWarning" in src, \
        "No complaints-appropriate icon imported in AdminLayout"


# ── Complaints page wired ─────────────────────────────────────────────────────
def test_complaints_page_uses_complaints_api():
    path = os.path.join(ADMIN_APP, "complaints", "page.tsx")
    src = read(path)
    assert "complaintsApi" in src, "Complaints page does not import complaintsApi"


def test_complaints_api_exists_in_admin_api():
    src = read(ADMIN_API)
    assert "complaintsApi" in src, "complaintsApi not found in admin api.ts"


# ── Service Groups page wired ─────────────────────────────────────────────────
def test_service_groups_page_exists():
    path = os.path.join(ADMIN_APP, "service-groups", "page.tsx")
    assert os.path.exists(path), "service-groups/page.tsx missing"


def test_service_groups_page_has_api():
    path = os.path.join(ADMIN_APP, "service-groups", "page.tsx")
    src = read(path)
    # Must reference some API (serviceGroupsApi or catalogApi or adminApi)
    assert "Api" in src, "service-groups page imports no API client"


# ── Tenant fallback nav routes have pages ─────────────────────────────────────
@pytest.mark.parametrize("href", [
    "/dashboard",
    "/jobs",
    "/bookings",
    "/catalog",
    "/dispatch",
    "/staff",
    "/finance",
    "/reviews",
    "/provider/status",
    "/provider/marketing",
    "/provider/offerings",
    "/provider/service-areas",
    "/provider/team-members",
    "/provider/availability",
    "/onboarding-status",
    "/settings",
])
def test_tenant_fallback_nav_page_exists(href):
    """Every tenant fallback nav href must resolve to a page."""
    rel = href.lstrip("/")
    page = os.path.join(TENANT_APP, rel, "page.tsx")
    assert os.path.exists(page), \
        f"Missing tenant page.tsx for nav href {href} (expected at {page})"


# ── Tenant layout: nav visibility is entitlement-driven ──────────────────────
# NOTE (FINAL-L5-04B): the dynamic-nav-building approach these tests describe
# (buildApiNavGroups/NAV_GROUPS_FALLBACK/iconForRoute) was replaced by a
# static NAV_GROUPS list filtered per-tenant by a module/category entitlement
# system (EntitlementCtx/entitlementApi.getMyModules()/visibleNavGroups) --
# a deliberate, documented architecture change, not a regression.
def test_tenant_layout_has_api_nav_load():
    src = tenant_layout_src()
    assert "entitlementApi" in src, "Tenant nav does not load entitlements from API"
    assert "getMyModules" in src, "getMyModules call missing"
    assert "visibleNavGroups" in src, "Entitlement-filtered nav groups missing"


def test_tenant_layout_icon_map_has_common_routes():
    src = tenant_layout_src()
    assert '"/dashboard"' in src
    assert '"/bookings"' in src
    assert '"/jobs"' in src
    assert '"/finance/package"' in src
    assert '"/reviews"' in src


# ── No raw enum display in key admin pages ────────────────────────────────────
def test_admin_categories_no_raw_enum_replace():
    path = os.path.join(ADMIN_APP, "categories", "page.tsx")
    src = read(path)
    # Should use label maps not raw .replace(/_/g," ")
    raw_replace_count = src.count('.replace(/_/g, " ")')
    # Allow at most 1 (fallback in label maps), not multiple scattered uses
    assert raw_replace_count <= 2, \
        f"Too many raw enum replace() calls in categories page ({raw_replace_count})"


def test_admin_categories_has_label_maps():
    path = os.path.join(ADMIN_APP, "categories", "page.tsx")
    src = read(path)
    assert "VERTICAL_LABELS" in src, "Missing VERTICAL_LABELS map"
    assert "FINANCE_LABELS" in src, "Missing FINANCE_LABELS map"
    assert "FLOW_LABELS" in src, "Missing FLOW_LABELS map"


# ── Admin api.ts has key API clients ──────────────────────────────────────────
@pytest.mark.parametrize("api_name", [
    "complaintsApi",
    "categoryRuntimeApi",
    "catalogApi",
    "staffApi",
    "adminBookingsApi",
    "adminCustomersApi",
    "adminAnalyticsApi",
    "marketingApi",
])
def test_admin_api_client_exists(api_name):
    src = read(ADMIN_API)
    assert f"export const {api_name}" in src or f"export const {api_name} " in src or \
           f"const {api_name}" in src, \
        f"{api_name} not found in admin api.ts"


# ── Tenant api.ts has key API clients ────────────────────────────────────────
@pytest.mark.parametrize("api_name", [
    "categoryDashboardApi",
    "authApi",
    "financeApi",
])
def test_tenant_api_client_exists(api_name):
    src = read(TENANT_API)
    assert api_name in src, f"{api_name} not found in tenant api.ts"


# ── Admin layout: Operations group ordering ───────────────────────────────────
def _extract_group_block(src: str, group_label: str) -> str:
    """Extract the nav group block from the group label to the next closing brace + comma."""
    start = src.find(f'"{group_label}"')
    if start == -1:
        return ""
    # Find the end of this group: next occurrence of "},\n  {" after start
    end = src.find("},\n  {", start)
    if end == -1:
        end = src.find("];\n", start)
    return src[start: end] if end != -1 else src[start:]


def test_admin_operations_group_order():
    """Operations group should list: Bookings, Jobs, Customers, Staff, Reviews, Complaints."""
    src = admin_layout_src()
    block = _extract_group_block(src, "Operations")
    assert block, "Operations group not found"
    assert "/admin/bookings" in block,   "Bookings missing from Operations"
    assert "/admin/operations" in block, "Jobs missing from Operations"
    assert "/admin/customers" in block,  "Customers missing from Operations"
    assert "/admin/staff" in block,      "Staff missing from Operations"
    assert "/admin/reviews" in block,    "Reviews missing from Operations"
    assert "/admin/complaints" in block, "Complaints missing from Operations"


def test_admin_service_catalog_group_order():
    """Service Catalog is no longer a static AdminLayout group -- migration
    089 replaced it with DB-driven catalog_module_definitions, rendered
    dynamically per-vertical by VerticalCatalogSection. Verify the seed
    still contains the full hierarchy, and AdminLayout still renders it."""
    assert "VerticalCatalogSection" in admin_layout_src(), \
        "AdminLayout no longer renders dynamic per-vertical catalog modules"
    seed = read(CATALOG_MODULES_SEED)
    for href in ("/admin/categories", "/admin/service-groups", "/admin/master-services",
                 "/admin/types-brands", "/admin/service-options", "/admin/issue-types"):
        assert f'"{href}"' in seed, f"{href} missing from catalog_module_definitions seed"
