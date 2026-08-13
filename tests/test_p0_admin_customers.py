"""Tests for P0 Admin Customers Page — platform-wide customer management."""
from pathlib import Path
import re

ROOT = Path(__file__).parent.parent
BACKEND_ROUTER = ROOT / "app" / "engines" / "auth" / "admin_customers_router.py"
FRONTEND_PAGE  = ROOT / "frontend" / "super-admin" / "app" / "admin" / "customers" / "page.tsx"
DETAIL_PAGE    = ROOT / "frontend" / "super-admin" / "app" / "admin" / "customers" / "[id]" / "page.tsx"
API_TS         = ROOT / "frontend" / "super-admin" / "lib" / "api.ts"
MAIN_PY        = ROOT / "app" / "main.py"


# ── File existence ─────────────────────────────────────────────────────────────

def test_admin_customers_router_exists():
    assert BACKEND_ROUTER.exists()

def test_admin_customers_page_exists():
    assert FRONTEND_PAGE.exists()

def test_admin_customers_detail_page_exists():
    assert DETAIL_PAGE.exists()

def test_api_ts_has_admin_customers_api():
    assert "adminCustomersApi" in API_TS.read_text(encoding="utf-8")

def test_api_ts_has_admin_customer_type():
    assert "AdminCustomer" in API_TS.read_text(encoding="utf-8")

def test_api_ts_has_admin_customer_summary_type():
    assert "AdminCustomerSummary" in API_TS.read_text(encoding="utf-8")


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
    assert '"/{customer_id}"' in src

def test_router_has_booking_history_endpoint():
    src = BACKEND_ROUTER.read_text(encoding="utf-8")
    assert '"/{customer_id}/bookings"' in src

def test_router_prefix():
    src = BACKEND_ROUTER.read_text(encoding="utf-8")
    assert "/v1/admin/customers" in src

def test_router_requires_super_admin():
    src = BACKEND_ROUTER.read_text(encoding="utf-8")
    assert "require_super_admin" in src

def test_router_filters_by_customer_role():
    src = BACKEND_ROUTER.read_text(encoding="utf-8")
    assert "role = 'customer'" in src or "role='customer'" in src

def test_router_no_required_tenant_id():
    src = BACKEND_ROUTER.read_text(encoding="utf-8")
    # tenant_id must be optional (Query(None)) not positional required
    assert "tenant_id: Optional" in src or "tenant_id:         Optional" in src

def test_router_joins_bookings_for_aggregation():
    src = BACKEND_ROUTER.read_text(encoding="utf-8")
    assert "FROM service_bookings" in src
    assert "FROM bookings" not in src

def test_router_joins_customer_addresses():
    src = BACKEND_ROUTER.read_text(encoding="utf-8")
    assert "customer_addresses" in src

def test_router_computes_health_band():
    src = BACKEND_ROUTER.read_text(encoding="utf-8")
    assert "health_band" in src
    assert "CASE" in src

def test_router_health_band_includes_dormant():
    src = BACKEND_ROUTER.read_text(encoding="utf-8")
    assert "dormant" in src

def test_router_health_band_includes_at_risk():
    src = BACKEND_ROUTER.read_text(encoding="utf-8")
    assert "at_risk" in src

def test_router_health_band_includes_complaint_risk():
    src = BACKEND_ROUTER.read_text(encoding="utf-8")
    assert "complaint_risk" in src

def test_router_supports_city_filter():
    src = BACKEND_ROUTER.read_text(encoding="utf-8")
    assert "city" in src and "ILIKE" in src

def test_router_supports_state_filter():
    src = BACKEND_ROUTER.read_text(encoding="utf-8")
    assert "state" in src

def test_router_supports_has_complaints_filter():
    src = BACKEND_ROUTER.read_text(encoding="utf-8")
    assert "has_complaints" in src

def test_router_supports_booking_count_filters():
    src = BACKEND_ROUTER.read_text(encoding="utf-8")
    assert "booking_count_min" in src and "booking_count_max" in src

def test_router_supports_date_range_filters():
    src = BACKEND_ROUTER.read_text(encoding="utf-8")
    assert "last_booking_from" in src and "last_booking_to" in src

def test_router_supports_pagination():
    src = BACKEND_ROUTER.read_text(encoding="utf-8")
    assert "page" in src and "offset" in src

def test_router_supports_sorting():
    src = BACKEND_ROUTER.read_text(encoding="utf-8")
    assert "sort_by" in src and "sort_dir" in src

def test_router_csv_export():
    src = BACKEND_ROUTER.read_text(encoding="utf-8")
    assert "text/csv" in src and "csv.writer" in src

def test_router_summary_has_all_bands():
    src = BACKEND_ROUTER.read_text(encoding="utf-8")
    assert "at_risk" in src
    assert "dormant" in src
    assert "has_complaints" in src

def test_router_uses_sqlalchemy_text():
    src = BACKEND_ROUTER.read_text(encoding="utf-8")
    assert "from sqlalchemy import text" in src

def test_router_booking_history_filters_by_customer():
    src = BACKEND_ROUTER.read_text(encoding="utf-8")
    assert "b.customer_id = :cid" in src


# ── main.py registration ──────────────────────────────────────────────────────

def test_main_py_imports_admin_customers_router():
    src = MAIN_PY.read_text(encoding="utf-8")
    assert "admin_customers_router" in src

def test_main_py_includes_admin_customers_router():
    src = MAIN_PY.read_text(encoding="utf-8")
    assert "admin_customers_router" in src


# ── Frontend list page ────────────────────────────────────────────────────────

def test_frontend_page_no_tenant_gate():
    src = FRONTEND_PAGE.read_text(encoding="utf-8")
    # Old blocking pattern must be gone
    assert "Promise.resolve" not in src
    assert "Select a tenant to view" not in src
    assert "Choose a tenant" not in src

def test_frontend_page_uses_admin_customers_api():
    src = FRONTEND_PAGE.read_text(encoding="utf-8")
    assert "adminCustomersApi" in src

def test_frontend_page_loads_on_mount():
    src = FRONTEND_PAGE.read_text(encoding="utf-8")
    # must call summary and list via useApi/useCallback without tenantId guard
    assert "adminCustomersApi.summary" in src
    assert "adminCustomersApi.list" in src

def test_frontend_page_has_summary_cards():
    src = FRONTEND_PAGE.read_text(encoding="utf-8")
    assert "SummaryCard" in src

def test_frontend_page_has_health_band_filter():
    src = FRONTEND_PAGE.read_text(encoding="utf-8")
    assert "HEALTH_BANDS" in src or "health_band" in src.lower()

def test_frontend_page_has_search_input():
    src = FRONTEND_PAGE.read_text(encoding="utf-8")
    assert "Search" in src or "search" in src

def test_frontend_page_has_advanced_filters():
    src = FRONTEND_PAGE.read_text(encoding="utf-8")
    assert "showAdvanced" in src or "advanced" in src.lower()

def test_frontend_page_has_city_filter():
    src = FRONTEND_PAGE.read_text(encoding="utf-8")
    assert "city" in src.lower()

def test_frontend_page_has_state_filter():
    src = FRONTEND_PAGE.read_text(encoding="utf-8")
    assert "state" in src.lower()

def test_frontend_page_has_active_filter_chips():
    src = FRONTEND_PAGE.read_text(encoding="utf-8")
    assert "FilterChip" in src or "filter-chip" in src.lower()

def test_frontend_page_has_data_table():
    src = FRONTEND_PAGE.read_text(encoding="utf-8")
    assert "DataTable" in src

def test_frontend_page_has_health_badge():
    src = FRONTEND_PAGE.read_text(encoding="utf-8")
    assert "HEALTH_BADGE" in src

def test_frontend_page_has_pagination():
    src = FRONTEND_PAGE.read_text(encoding="utf-8")
    assert "goToPage" in src or "total_pages" in src

def test_frontend_page_has_csv_export():
    src = FRONTEND_PAGE.read_text(encoding="utf-8")
    assert "CSV" in src or "export" in src.lower()

def test_frontend_page_proper_empty_state():
    src = FRONTEND_PAGE.read_text(encoding="utf-8")
    assert "emptyText" in src
    assert "No customers yet" in src or "No customers match" in src

def test_frontend_page_no_old_tenant_dropdown():
    src = FRONTEND_PAGE.read_text(encoding="utf-8")
    # Old page had "Select Tenant" as a required first step label
    assert "Select Tenant" not in src
    assert "Choose a tenant" not in src

def test_frontend_page_links_to_detail():
    src = FRONTEND_PAGE.read_text(encoding="utf-8")
    assert "/admin/customers/" in src

def test_frontend_page_has_complaints_column():
    src = FRONTEND_PAGE.read_text(encoding="utf-8")
    assert "complaints" in src.lower()

def test_frontend_page_has_booking_count_column():
    src = FRONTEND_PAGE.read_text(encoding="utf-8")
    assert "total_bookings" in src


# ── Detail page ───────────────────────────────────────────────────────────────

def test_detail_page_uses_admin_customers_api():
    src = DETAIL_PAGE.read_text(encoding="utf-8")
    assert "adminCustomersApi" in src

def test_detail_page_fetches_customer_by_id():
    src = DETAIL_PAGE.read_text(encoding="utf-8")
    assert "adminCustomersApi.get" in src

def test_detail_page_has_booking_history_tab():
    src = DETAIL_PAGE.read_text(encoding="utf-8")
    assert "bookings" in src.lower()
    assert "adminCustomersApi.bookings" in src

def test_detail_page_has_back_link():
    src = DETAIL_PAGE.read_text(encoding="utf-8")
    assert "/admin/customers" in src

def test_detail_page_shows_health_band():
    src = DETAIL_PAGE.read_text(encoding="utf-8")
    assert "health_band" in src

def test_detail_page_shows_contact_details():
    src = DETAIL_PAGE.read_text(encoding="utf-8")
    assert "phone" in src.lower() and "email" in src.lower()

def test_detail_page_shows_location():
    src = DETAIL_PAGE.read_text(encoding="utf-8")
    assert "city" in src.lower() and "state" in src.lower()

def test_detail_page_has_error_state():
    src = DETAIL_PAGE.read_text(encoding="utf-8")
    assert "error" in src.lower() or "Error" in src


# ── API client ────────────────────────────────────────────────────────────────

def test_api_ts_admin_customers_list_tenant_optional():
    src = API_TS.read_text(encoding="utf-8")
    start = src.find("export const adminCustomersApi")
    end   = src.find("};", start)
    block = src[start:end]
    assert "tenant_id?" in block

def test_api_ts_admin_customers_has_summary():
    src = API_TS.read_text(encoding="utf-8")
    assert "adminCustomersApi" in src
    assert "/v1/admin/customers/summary" in src

def test_api_ts_admin_customers_has_export():
    src = API_TS.read_text(encoding="utf-8")
    assert "/v1/admin/customers/export" in src

def test_api_ts_admin_customers_has_filters():
    src = API_TS.read_text(encoding="utf-8")
    assert "/v1/admin/customers/filters" in src

def test_api_ts_admin_customers_has_bookings_method():
    src = API_TS.read_text(encoding="utf-8")
    assert "adminCustomersApi" in src
    idx = src.find("export const adminCustomersApi")
    end = src.find("};", idx)
    block = src[idx:end]
    assert "bookings" in block

def test_api_ts_admin_customer_summary_fields():
    src = API_TS.read_text(encoding="utf-8")
    assert "at_risk" in src
    assert "dormant" in src
    assert "has_complaints" in src
    assert "bookings_per_customer" in src
