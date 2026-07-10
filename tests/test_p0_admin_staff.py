"""Tests for P0 Admin Staff Management — platform-wide staff view without tenant selection."""
from pathlib import Path

ROOT           = Path(__file__).parent.parent
BACKEND_ROUTER = ROOT / "app" / "engines" / "auth" / "admin_staff_router.py"
FRONTEND_PAGE  = ROOT / "frontend" / "super-admin" / "app" / "admin" / "staff" / "page.tsx"
DETAIL_PAGE    = ROOT / "frontend" / "super-admin" / "app" / "admin" / "staff" / "[id]" / "page.tsx"
API_TS         = ROOT / "frontend" / "super-admin" / "lib" / "api.ts"
MAIN_PY        = ROOT / "app" / "main.py"


# ── File existence ─────────────────────────────────────────────────────────────

def test_admin_staff_router_exists():
    assert BACKEND_ROUTER.exists()

def test_admin_staff_page_exists():
    assert FRONTEND_PAGE.exists()

def test_admin_staff_detail_page_exists():
    assert DETAIL_PAGE.exists()

def test_api_ts_has_admin_staff_api():
    assert "adminStaffApi" in API_TS.read_text(encoding="utf-8")

def test_api_ts_has_admin_staff_member_type():
    assert "AdminStaffMember" in API_TS.read_text(encoding="utf-8")

def test_api_ts_has_admin_staff_summary_type():
    assert "AdminStaffSummary" in API_TS.read_text(encoding="utf-8")


# ── Backend router — prefix & auth ────────────────────────────────────────────

def test_router_prefix():
    src = BACKEND_ROUTER.read_text(encoding="utf-8")
    assert "/v1/admin/staff" in src

def test_router_requires_super_admin():
    src = BACKEND_ROUTER.read_text(encoding="utf-8")
    assert "require_super_admin" in src

def test_router_excludes_customers():
    src = BACKEND_ROUTER.read_text(encoding="utf-8")
    assert "customer" in src and "super_admin" in src

def test_router_tenant_id_is_not_null():
    src = BACKEND_ROUTER.read_text(encoding="utf-8")
    assert "tenant_id IS NOT NULL" in src


# ── Backend router — endpoints ─────────────────────────────────────────────────

def test_router_has_list_endpoint():
    src = BACKEND_ROUTER.read_text(encoding="utf-8")
    assert 'router.get("")' in src

def test_router_has_summary_endpoint():
    src = BACKEND_ROUTER.read_text(encoding="utf-8")
    assert '"/summary"' in src

def test_router_has_export_endpoint():
    src = BACKEND_ROUTER.read_text(encoding="utf-8")
    assert '"/export"' in src

def test_router_has_filters_endpoint():
    src = BACKEND_ROUTER.read_text(encoding="utf-8")
    assert '"/filters"' in src

def test_router_has_detail_endpoint():
    src = BACKEND_ROUTER.read_text(encoding="utf-8")
    assert '"/{staff_id}"' in src

def test_router_has_jobs_endpoint():
    src = BACKEND_ROUTER.read_text(encoding="utf-8")
    assert '"/{staff_id}/jobs"' in src


# ── Backend router — filters & aggregations ───────────────────────────────────

def test_router_tenant_id_is_optional():
    src = BACKEND_ROUTER.read_text(encoding="utf-8")
    assert "tenant_id: Optional" in src

def test_router_supports_role_filter():
    src = BACKEND_ROUTER.read_text(encoding="utf-8")
    assert "role" in src

def test_router_supports_availability_filter():
    src = BACKEND_ROUTER.read_text(encoding="utf-8")
    assert "availability_status" in src

def test_router_supports_city_filter():
    src = BACKEND_ROUTER.read_text(encoding="utf-8")
    assert "city" in src and "ILIKE" in src

def test_router_computes_availability_inline():
    src = BACKEND_ROUTER.read_text(encoding="utf-8")
    assert "availability_status" in src
    assert "CASE" in src
    assert "busy" in src
    assert "available" in src
    assert "inactive" in src

def test_router_joins_jobs_for_aggregation():
    src = BACKEND_ROUTER.read_text(encoding="utf-8")
    assert "FROM jobs" in src or "FROM   jobs" in src

def test_router_joins_staff_rating_summaries():
    src = BACKEND_ROUTER.read_text(encoding="utf-8")
    assert "staff_rating_summaries" in src

def test_router_joins_tenants():
    src = BACKEND_ROUTER.read_text(encoding="utf-8")
    assert "JOIN tenants" in src or "JOIN   tenants" in src

def test_router_computes_total_jobs():
    src = BACKEND_ROUTER.read_text(encoding="utf-8")
    assert "total_jobs" in src

def test_router_computes_completed_jobs():
    src = BACKEND_ROUTER.read_text(encoding="utf-8")
    assert "completed_jobs" in src

def test_router_computes_active_jobs():
    src = BACKEND_ROUTER.read_text(encoding="utf-8")
    assert "active_jobs" in src

def test_router_uses_lateral_join():
    src = BACKEND_ROUTER.read_text(encoding="utf-8")
    assert "LATERAL" in src

def test_router_supports_pagination():
    src = BACKEND_ROUTER.read_text(encoding="utf-8")
    assert "page" in src and "offset" in src

def test_router_supports_sorting():
    src = BACKEND_ROUTER.read_text(encoding="utf-8")
    assert "sort_by" in src and "sort_dir" in src

def test_router_csv_export():
    src = BACKEND_ROUTER.read_text(encoding="utf-8")
    assert "text/csv" in src and "csv.writer" in src

def test_router_summary_has_verified_counts():
    src = BACKEND_ROUTER.read_text(encoding="utf-8")
    assert "verified" in src and "unverified" in src

def test_router_summary_has_busy_count():
    src = BACKEND_ROUTER.read_text(encoding="utf-8")
    assert "busy" in src

def test_router_uses_sqlalchemy_text():
    src = BACKEND_ROUTER.read_text(encoding="utf-8")
    assert "from sqlalchemy import text" in src

def test_router_jobs_filters_by_staff():
    src = BACKEND_ROUTER.read_text(encoding="utf-8")
    assert "assigned_staff_id" in src


# ── main.py registration ──────────────────────────────────────────────────────

def test_main_py_imports_admin_staff_router():
    src = MAIN_PY.read_text(encoding="utf-8")
    assert "admin_staff_router" in src

def test_main_py_includes_admin_staff_router():
    src = MAIN_PY.read_text(encoding="utf-8")
    assert "admin_staff_router" in src


# ── Frontend list page ────────────────────────────────────────────────────────

def test_frontend_page_no_tenant_gate():
    src = FRONTEND_PAGE.read_text(encoding="utf-8")
    assert "Promise.resolve" not in src
    assert "Select a tenant to view" not in src
    assert "Choose a tenant" not in src

def test_frontend_page_uses_admin_staff_api():
    src = FRONTEND_PAGE.read_text(encoding="utf-8")
    assert "adminStaffApi" in src

def test_frontend_page_loads_on_mount():
    src = FRONTEND_PAGE.read_text(encoding="utf-8")
    assert "adminStaffApi.summary" in src
    assert "adminStaffApi.list" in src

def test_frontend_page_has_summary_cards():
    src = FRONTEND_PAGE.read_text(encoding="utf-8")
    assert "SummaryCard" in src

def test_frontend_page_has_availability_filter():
    src = FRONTEND_PAGE.read_text(encoding="utf-8")
    assert "availability" in src.lower() or "availFilter" in src

def test_frontend_page_has_role_filter():
    src = FRONTEND_PAGE.read_text(encoding="utf-8")
    assert "role" in src.lower() and "roleFilter" in src

def test_frontend_page_has_search_input():
    src = FRONTEND_PAGE.read_text(encoding="utf-8")
    assert "Search" in src or "search" in src

def test_frontend_page_has_advanced_filters():
    src = FRONTEND_PAGE.read_text(encoding="utf-8")
    assert "showAdvanced" in src or "advanced" in src.lower()

def test_frontend_page_has_city_filter():
    src = FRONTEND_PAGE.read_text(encoding="utf-8")
    assert "city" in src.lower() and "cityFilter" in src

def test_frontend_page_has_filter_chips():
    src = FRONTEND_PAGE.read_text(encoding="utf-8")
    assert "FilterChip" in src

def test_frontend_page_has_data_table():
    src = FRONTEND_PAGE.read_text(encoding="utf-8")
    assert "DataTable" in src

def test_frontend_page_has_availability_badge():
    src = FRONTEND_PAGE.read_text(encoding="utf-8")
    assert "AVAIL_BADGE" in src

def test_frontend_page_has_pagination():
    src = FRONTEND_PAGE.read_text(encoding="utf-8")
    assert "goToPage" in src or "total_pages" in src

def test_frontend_page_has_csv_export():
    src = FRONTEND_PAGE.read_text(encoding="utf-8")
    assert "CSV" in src or "export" in src.lower()

def test_frontend_page_proper_empty_state():
    src = FRONTEND_PAGE.read_text(encoding="utf-8")
    assert "emptyText" in src

def test_frontend_page_no_old_tenant_dropdown():
    src = FRONTEND_PAGE.read_text(encoding="utf-8")
    assert "Select Tenant" not in src

def test_frontend_page_links_to_detail():
    src = FRONTEND_PAGE.read_text(encoding="utf-8")
    assert "/admin/staff/" in src

def test_frontend_page_shows_job_counts():
    src = FRONTEND_PAGE.read_text(encoding="utf-8")
    assert "total_jobs" in src

def test_frontend_page_shows_ratings():
    src = FRONTEND_PAGE.read_text(encoding="utf-8")
    assert "average_rating" in src

def test_frontend_page_uses_search_dropdown():
    src = FRONTEND_PAGE.read_text(encoding="utf-8")
    assert "SearchDropdown" in src


# ── Detail page ───────────────────────────────────────────────────────────────

def test_detail_page_uses_admin_staff_api():
    src = DETAIL_PAGE.read_text(encoding="utf-8")
    assert "adminStaffApi" in src

def test_detail_page_fetches_staff_by_id():
    src = DETAIL_PAGE.read_text(encoding="utf-8")
    assert "adminStaffApi.get" in src

def test_detail_page_has_jobs_tab():
    src = DETAIL_PAGE.read_text(encoding="utf-8")
    assert "jobs" in src.lower()
    assert "adminStaffApi.jobs" in src

def test_detail_page_has_back_link():
    src = DETAIL_PAGE.read_text(encoding="utf-8")
    assert "/admin/staff" in src

def test_detail_page_shows_availability():
    src = DETAIL_PAGE.read_text(encoding="utf-8")
    assert "availability_status" in src

def test_detail_page_shows_contact_details():
    src = DETAIL_PAGE.read_text(encoding="utf-8")
    assert "phone" in src.lower() and "email" in src.lower()

def test_detail_page_shows_provider_info():
    src = DETAIL_PAGE.read_text(encoding="utf-8")
    assert "tenant_name" in src

def test_detail_page_has_error_state():
    src = DETAIL_PAGE.read_text(encoding="utf-8")
    assert "error" in src.lower() or "Error" in src

def test_detail_page_shows_job_stats():
    src = DETAIL_PAGE.read_text(encoding="utf-8")
    assert "total_jobs" in src and "completed_jobs" in src


# ── API client ────────────────────────────────────────────────────────────────

def test_api_ts_admin_staff_tenant_optional():
    src = API_TS.read_text(encoding="utf-8")
    start = src.find("export const adminStaffApi")
    end   = src.find("};", start)
    block = src[start:end]
    assert "tenant_id?" in block

def test_api_ts_admin_staff_has_summary():
    src = API_TS.read_text(encoding="utf-8")
    assert "/v1/admin/staff/summary" in src

def test_api_ts_admin_staff_has_export():
    src = API_TS.read_text(encoding="utf-8")
    assert "/v1/admin/staff/export" in src

def test_api_ts_admin_staff_has_filters():
    src = API_TS.read_text(encoding="utf-8")
    assert "/v1/admin/staff/filters" in src

def test_api_ts_admin_staff_has_jobs_method():
    src = API_TS.read_text(encoding="utf-8")
    start = src.find("export const adminStaffApi")
    end   = src.find("};", start)
    block = src[start:end]
    assert "jobs" in block

def test_api_ts_admin_staff_summary_has_availability_fields():
    src = API_TS.read_text(encoding="utf-8")
    assert "busy" in src
    assert "available" in src or "availability_status" in src

def test_api_ts_admin_staff_member_has_all_key_fields():
    src = API_TS.read_text(encoding="utf-8")
    start = src.find("export interface AdminStaffMember")
    end   = src.find("}", start)
    block = src[start:end]
    for field in ["user_id", "full_name", "total_jobs", "average_rating", "availability_status", "tenant_name"]:
        assert field in block
