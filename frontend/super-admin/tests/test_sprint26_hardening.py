"""
Sprint 26 Hardening — Frontend test suite (Phase 8).
Verifies EnterpriseDataGrid URL sync, migrated page structure,
component completeness, and no-inline-fetch discipline.
All tests are pure Python file-system + content checks.
"""
import os
import re

ADMIN   = "g:/serviceos/frontend/super-admin"
TENANT  = "g:/serviceos/frontend/tenant-portal"
ADMIN_COMPS = f"{ADMIN}/components/enterprise"
TENANT_COMPS = f"{TENANT}/components/enterprise"
ADMIN_APP   = f"{ADMIN}/app/admin"
TENANT_APP  = f"{TENANT}/app/(tenant)"


# ── helpers ───────────────────────────────────────────────────────────────────

def _read(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


def _exists(path: str) -> bool:
    return os.path.exists(path)


# ── 1. Enterprise component files exist in super-admin ────────────────────────

def test_enterprise_data_grid_exists_super_admin():
    assert _exists(f"{ADMIN_COMPS}/EnterpriseDataGrid.tsx")


def test_enterprise_filter_bar_exists_super_admin():
    assert _exists(f"{ADMIN_COMPS}/EnterpriseFilterBar.tsx")


def test_enterprise_pagination_exists_super_admin():
    assert _exists(f"{ADMIN_COMPS}/EnterprisePagination.tsx")


def test_enterprise_column_manager_exists_super_admin():
    assert _exists(f"{ADMIN_COMPS}/EnterpriseColumnManager.tsx")


# ── 2. Enterprise component files exist in tenant-portal ─────────────────────

def test_enterprise_data_grid_exists_tenant_portal():
    assert _exists(f"{TENANT_COMPS}/EnterpriseDataGrid.tsx")


def test_enterprise_filter_bar_exists_tenant_portal():
    assert _exists(f"{TENANT_COMPS}/EnterpriseFilterBar.tsx")


def test_enterprise_pagination_exists_tenant_portal():
    assert _exists(f"{TENANT_COMPS}/EnterprisePagination.tsx")


def test_enterprise_column_manager_exists_tenant_portal():
    assert _exists(f"{TENANT_COMPS}/EnterpriseColumnManager.tsx")


# ── 3. EnterpriseDataGrid URL sync in super-admin ────────────────────────────

def test_data_grid_uses_search_params():
    src = _read(f"{ADMIN_COMPS}/EnterpriseDataGrid.tsx")
    assert "useSearchParams" in src, "EnterpriseDataGrid must use useSearchParams"


def test_data_grid_uses_router_replace():
    src = _read(f"{ADMIN_COMPS}/EnterpriseDataGrid.tsx")
    assert "router.replace" in src, "EnterpriseDataGrid must call router.replace for URL sync"


def test_data_grid_uses_pathname():
    src = _read(f"{ADMIN_COMPS}/EnterpriseDataGrid.tsx")
    assert "usePathname" in src, "EnterpriseDataGrid must use usePathname"


def test_data_grid_has_search_debounce():
    src = _read(f"{ADMIN_COMPS}/EnterpriseDataGrid.tsx")
    assert "searchTimer" in src or "debounce" in src.lower() or "setTimeout" in src, \
        "EnterpriseDataGrid must debounce search URL updates"


def test_data_grid_reset_clears_url():
    src = _read(f"{ADMIN_COMPS}/EnterpriseDataGrid.tsx")
    assert "handleReset" in src
    # reset should call router.replace with just the pathname (no query string)
    assert re.search(r"router\.replace\s*\(\s*pathname", src), \
        "handleReset must call router.replace(pathname) to clear query params"


def test_data_grid_page_resets_on_filter_change():
    src = _read(f"{ADMIN_COMPS}/EnterpriseDataGrid.tsx")
    # When filter changes, setPage(1) should be called
    assert "setPage(1)" in src, "Filter change must reset page to 1"


# ── 4. 7 priority admin pages migrated ───────────────────────────────────────

ADMIN_MIGRATED_PAGES = [
    "commission-records/page.tsx",
    "payments/page.tsx",
    "tenants/page.tsx",
    "reviews/page.tsx",
    "complaints/page.tsx",
    "refund-requests/page.tsx",
    "audit-logs/page.tsx",
]

def test_admin_migrated_pages_exist():
    missing = [p for p in ADMIN_MIGRATED_PAGES if not _exists(f"{ADMIN_APP}/{p}")]
    assert not missing, f"Missing migrated pages: {missing}"


def test_admin_migrated_pages_use_enterprise_data_grid():
    for page in ADMIN_MIGRATED_PAGES:
        src = _read(f"{ADMIN_APP}/{page}")
        assert "EnterpriseDataGrid" in src, f"{page} must use EnterpriseDataGrid"


def test_admin_migrated_pages_have_default_sort():
    for page in ADMIN_MIGRATED_PAGES:
        src = _read(f"{ADMIN_APP}/{page}")
        assert "defaultSort" in src, f"{page} must specify defaultSort"


def test_admin_migrated_pages_have_columns():
    for page in ADMIN_MIGRATED_PAGES:
        src = _read(f"{ADMIN_APP}/{page}")
        assert "COLUMNS" in src or "columns={" in src, f"{page} must define columns"


def test_admin_migrated_pages_no_inline_useapi():
    for page in ADMIN_MIGRATED_PAGES:
        src = _read(f"{ADMIN_APP}/{page}")
        assert "useApi(" not in src, \
            f"{page} must not use legacy useApi() hook after migration"


# ── 5. 7 priority provider pages migrated ────────────────────────────────────

PROVIDER_MIGRATED_PAGES = [
    "provider/service-invoices/page.tsx",
    "provider/complaints/page.tsx",
    "provider/reviews/page.tsx",
    "provider/refund-requests/page.tsx",
]

TENANT_MIGRATED_PAGES = [
    "service-jobs/page.tsx",
    "appointments/page.tsx",
]

def test_provider_migrated_pages_exist():
    missing = [p for p in PROVIDER_MIGRATED_PAGES if not _exists(f"{TENANT_APP}/{p}")]
    assert not missing, f"Missing provider pages: {missing}"


def test_provider_migrated_pages_use_enterprise_data_grid():
    for page in PROVIDER_MIGRATED_PAGES:
        src = _read(f"{TENANT_APP}/{page}")
        assert "EnterpriseDataGrid" in src, f"{page} must use EnterpriseDataGrid"


def test_tenant_migrated_pages_exist():
    missing = [p for p in TENANT_MIGRATED_PAGES if not _exists(f"{TENANT_APP}/{p}")]
    assert not missing, f"Missing tenant pages: {missing}"


def test_tenant_migrated_pages_use_enterprise_data_grid():
    for page in TENANT_MIGRATED_PAGES:
        src = _read(f"{TENANT_APP}/{page}")
        assert "EnterpriseDataGrid" in src, f"{page} must use EnterpriseDataGrid"


# ── 6. No legacy useApi in provider migrated pages ───────────────────────────

def test_provider_migrated_no_legacy_useapi():
    for page in PROVIDER_MIGRATED_PAGES:
        src = _read(f"{TENANT_APP}/{page}")
        assert "useApi(" not in src, \
            f"Provider page {page} must not use legacy useApi() after migration"


# ── 7. Export button only in pages with enableExport ─────────────────────────

def test_admin_commission_page_has_export():
    src = _read(f"{ADMIN_APP}/commission-records/page.tsx")
    assert "enableExport" in src


def test_admin_payments_page_has_export():
    src = _read(f"{ADMIN_APP}/payments/page.tsx")
    assert "enableExport" in src


def test_admin_tenants_page_has_export():
    src = _read(f"{ADMIN_APP}/tenants/page.tsx")
    assert "enableExport" in src


def test_audit_logs_no_export_sensitive():
    src = _read(f"{ADMIN_APP}/audit-logs/page.tsx")
    # Audit logs don't have export enabled (sensitive data)
    assert "enableExport" not in src, "Audit logs should not expose export"


# ── 8. EnterpriseDataGrid tenant-portal also has URL sync ────────────────────

def test_tenant_data_grid_uses_search_params():
    src = _read(f"{TENANT_COMPS}/EnterpriseDataGrid.tsx")
    assert "useSearchParams" in src


def test_tenant_data_grid_uses_router_replace():
    src = _read(f"{TENANT_COMPS}/EnterpriseDataGrid.tsx")
    assert "router.replace" in src


def test_tenant_data_grid_has_search_debounce():
    src = _read(f"{TENANT_COMPS}/EnterpriseDataGrid.tsx")
    assert "searchTimer" in src or "setTimeout" in src
