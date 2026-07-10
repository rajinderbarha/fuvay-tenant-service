"""Tests for P0 Enterprise Admin Booking Management — platform-wide.

ROOT-CAUSE FIX VERIFIED:
  bookings table has no deleted_at column. Previous code filtered
  `b.deleted_at IS NULL` → PostgreSQL error → "unexpected error" in UI.
  Fixed by removing that filter from all SQL.
"""
import re
from pathlib import Path

ROOT           = Path(__file__).parent.parent
ROUTER         = ROOT / "app" / "engines" / "booking" / "admin_router.py"
FRONTEND_PAGE  = ROOT / "frontend" / "super-admin" / "app" / "admin" / "bookings" / "page.tsx"
DETAIL_PAGE    = ROOT / "frontend" / "super-admin" / "app" / "admin" / "bookings" / "[id]" / "page.tsx"
API_TS         = ROOT / "frontend" / "super-admin" / "lib" / "api.ts"
MAIN_PY        = ROOT / "app" / "main.py"

# ── File existence ────────────────────────────────────────────────────────────

def test_admin_router_exists():
    assert ROUTER.exists()

def test_admin_bookings_page_exists():
    assert FRONTEND_PAGE.exists()

def test_admin_bookings_detail_page_exists():
    assert DETAIL_PAGE.exists()

# ── ROOT-CAUSE FIX: no deleted_at on bookings ─────────────────────────────────

def test_admin_router_does_not_filter_booking_deleted_at():
    """Bookings table has no deleted_at column — this filter was the root cause of the error."""
    src = ROUTER.read_text(encoding="utf-8")
    # Strip the module docstring (triple-quoted at top of file) before checking
    import re as _re
    no_docstring = _re.sub(r'^""".*?"""', "", src, count=1, flags=_re.DOTALL)
    # b.deleted_at IS NULL/NOT NULL must not appear in live SQL code
    assert not _re.search(r"b\.deleted_at\s+IS\s+", no_docstring, _re.IGNORECASE), \
        "b.deleted_at IS NULL/NOT NULL still in SQL — bookings table has no such column"

def test_admin_router_does_not_filter_tenant_deleted_at_in_where():
    """Tenants table has no deleted_at column either."""
    src = ROUTER.read_text(encoding="utf-8")
    # t.deleted_at may appear in JOINs or comments but not as an IS NULL filter in WHERE
    assert "t.deleted_at IS NULL" not in src, "t.deleted_at IS NULL still in SQL — tenants table has no such column"

def test_admin_router_conditions_start_empty():
    """_build_filters must not seed a deleted_at condition."""
    src = ROUTER.read_text(encoding="utf-8")
    build_start = src.find("def _build_filters")
    build_end   = src.find("\ndef ", build_start + 1)
    block = src[build_start:build_end]
    assert "deleted_at" not in block

# ── Backend router structure ──────────────────────────────────────────────────

def test_admin_router_has_list_endpoint():
    src = ROUTER.read_text(encoding="utf-8")
    assert 'router.get("")' in src or "router.get('')" in src

def test_admin_router_has_summary_endpoint():
    src = ROUTER.read_text(encoding="utf-8")
    assert '"/summary"' in src

def test_admin_router_has_export_endpoint():
    src = ROUTER.read_text(encoding="utf-8")
    assert '"/export"' in src

def test_admin_router_has_detail_endpoint():
    src = ROUTER.read_text(encoding="utf-8")
    assert '"/{booking_id}"' in src

def test_admin_router_has_timeline_endpoint():
    src = ROUTER.read_text(encoding="utf-8")
    assert "timeline" in src

def test_admin_router_has_notes_endpoint():
    src = ROUTER.read_text(encoding="utf-8")
    assert "notes" in src

def test_admin_router_has_cancel_endpoint():
    src = ROUTER.read_text(encoding="utf-8")
    assert "/cancel" in src

def test_admin_router_has_void_endpoint():
    src = ROUTER.read_text(encoding="utf-8")
    assert "/void" in src

def test_admin_router_has_tenant_search_endpoint():
    src = ROUTER.read_text(encoding="utf-8")
    assert "tenant-search" in src

def test_admin_router_prefix():
    src = ROUTER.read_text(encoding="utf-8")
    assert "/v1/admin/bookings" in src

def test_admin_router_requires_super_admin():
    src = ROUTER.read_text(encoding="utf-8")
    assert "require_super_admin" in src

# ── SQL correctness ───────────────────────────────────────────────────────────

def test_admin_router_joins_tenants():
    src = ROUTER.read_text(encoding="utf-8")
    assert "JOIN tenants" in src

def test_admin_router_joins_users():
    src = ROUTER.read_text(encoding="utf-8")
    assert "JOIN users" in src

def test_admin_router_joins_master_services():
    src = ROUTER.read_text(encoding="utf-8")
    assert "master_services" in src

def test_admin_router_joins_jobs():
    src = ROUTER.read_text(encoding="utf-8")
    assert "JOIN jobs" in src

def test_admin_router_service_name_from_join():
    """service_name should come from master_services join, not raw service_type_id.

    NOTE: this previously asserted the literal (and wrong) column reference
    "ms.name" — master_services has no "name" column, only "service_name".
    That earlier assertion encoded a real bug that a live curl smoke test
    caught this sprint (500 UndefinedColumnError on /v1/admin/bookings and
    /v1/admin/bookings/{id}) — see CROSS_APP_FRONTEND_FIX_REPORT.md.
    """
    src = ROUTER.read_text(encoding="utf-8")
    assert "ms.service_name" in src

def test_admin_router_state_from_address_jsonb():
    src = ROUTER.read_text(encoding="utf-8")
    assert "address->>'state'" in src

def test_admin_router_district_from_address_jsonb():
    src = ROUTER.read_text(encoding="utf-8")
    assert "address->>'district'" in src

def test_admin_router_sla_breached_field():
    src = ROUTER.read_text(encoding="utf-8")
    assert "sla_breached" in src

def test_admin_router_assignment_status_computed():
    """assignment_status derived from job.assigned_staff_id, not a stored column."""
    src = ROUTER.read_text(encoding="utf-8")
    assert "assigned_staff_id" in src

# ── Expanded filters ──────────────────────────────────────────────────────────

def test_admin_router_filter_by_service_id():
    src = ROUTER.read_text(encoding="utf-8")
    assert "service_id" in src

def test_admin_router_filter_by_state():
    src = ROUTER.read_text(encoding="utf-8")
    assert "state" in src

def test_admin_router_filter_by_district():
    src = ROUTER.read_text(encoding="utf-8")
    assert "district" in src

def test_admin_router_filter_by_amount_min_max():
    src = ROUTER.read_text(encoding="utf-8")
    assert "amount_min" in src
    assert "amount_max" in src

def test_admin_router_filter_by_scheduled_dates():
    src = ROUTER.read_text(encoding="utf-8")
    assert "scheduled_from" in src
    assert "scheduled_to" in src

def test_admin_router_sort_by_and_dir():
    src = ROUTER.read_text(encoding="utf-8")
    assert "sort_by" in src
    assert "sort_dir" in src

def test_admin_router_sort_injection_safe():
    """Sort column must be validated against allowlist."""
    src = ROUTER.read_text(encoding="utf-8")
    assert "_VALID_SORT" in src

# ── Summary cards ─────────────────────────────────────────────────────────────

def test_admin_router_summary_has_scheduled():
    src = ROUTER.read_text(encoding="utf-8")
    assert "scheduled" in src

def test_admin_router_summary_has_unassigned():
    src = ROUTER.read_text(encoding="utf-8")
    assert "unassigned" in src

def test_admin_router_summary_has_at_risk():
    src = ROUTER.read_text(encoding="utf-8")
    assert "at_risk" in src

# ── main.py registration ──────────────────────────────────────────────────────

def test_main_registers_booking_admin_router():
    src = MAIN_PY.read_text(encoding="utf-8")
    assert "booking_admin_router" in src

# ── API client ────────────────────────────────────────────────────────────────

def test_api_ts_has_admin_bookings_api():
    src = API_TS.read_text(encoding="utf-8")
    assert "adminBookingsApi" in src

def test_api_ts_admin_booking_has_new_fields():
    src = API_TS.read_text(encoding="utf-8")
    start = src.find("export interface AdminBooking")
    end   = src.find("}", start)
    block = src[start:end]
    for field in ["provider_name", "job_status", "assignment_status", "state", "district", "sla_breached"]:
        assert field in block, f"AdminBooking missing field: {field}"

def test_api_ts_summary_has_new_cards():
    src = API_TS.read_text(encoding="utf-8")
    start = src.find("export interface AdminBookingSummary")
    end   = src.find("}", start)
    block = src[start:end]
    for field in ["scheduled", "unassigned", "at_risk"]:
        assert field in block, f"AdminBookingSummary missing: {field}"

def test_api_ts_admin_bookings_has_get_timeline():
    src = API_TS.read_text(encoding="utf-8")
    assert "getTimeline" in src

def test_api_ts_admin_bookings_has_list_notes():
    src = API_TS.read_text(encoding="utf-8")
    assert "listNotes" in src

def test_api_ts_admin_bookings_has_cancel():
    src = API_TS.read_text(encoding="utf-8")
    assert "adminBookingsApi" in src
    start = src.find("export const adminBookingsApi")
    end   = src.find("};", start)
    block = src[start:end]
    assert "cancel" in block

def test_api_ts_admin_bookings_has_void():
    src = API_TS.read_text(encoding="utf-8")
    start = src.find("export const adminBookingsApi")
    end   = src.find("};", start)
    block = src[start:end]
    assert "void" in block

def test_api_ts_admin_bookings_has_tenant_search():
    src = API_TS.read_text(encoding="utf-8")
    assert "tenantSearch" in src

def test_api_ts_list_params_includes_new_filters():
    src = API_TS.read_text(encoding="utf-8")
    start = src.find("export interface AdminBookingListParams")
    end   = src.find("}", start)
    block = src[start:end]
    for field in ["service_id", "state", "district", "scheduled_from", "scheduled_to", "amount_min", "amount_max", "sort_by", "sort_dir"]:
        assert field in block, f"AdminBookingListParams missing: {field}"

# ── Frontend list page ────────────────────────────────────────────────────────

def test_frontend_uses_admin_bookings_api():
    src = FRONTEND_PAGE.read_text(encoding="utf-8")
    assert "adminBookingsApi" in src

def test_frontend_has_summary_cards():
    src = FRONTEND_PAGE.read_text(encoding="utf-8")
    assert "SummaryCard" in src

def test_frontend_has_clickable_summary_cards():
    src = FRONTEND_PAGE.read_text(encoding="utf-8")
    assert "applyStatusCard" in src or "onClick" in src

def test_frontend_has_advanced_filters():
    src = FRONTEND_PAGE.read_text(encoding="utf-8")
    assert "showAdvanced" in src

def test_frontend_has_async_tenant_selector():
    src = FRONTEND_PAGE.read_text(encoding="utf-8")
    assert "AsyncTenantSelect" in src

def test_frontend_has_filter_chips():
    src = FRONTEND_PAGE.read_text(encoding="utf-8")
    assert "Chip" in src or "activeChips" in src

def test_frontend_has_state_filter():
    src = FRONTEND_PAGE.read_text(encoding="utf-8")
    assert "state" in src.lower()

def test_frontend_has_district_filter():
    src = FRONTEND_PAGE.read_text(encoding="utf-8")
    assert "district" in src.lower()

def test_frontend_has_zipcode_filter():
    src = FRONTEND_PAGE.read_text(encoding="utf-8")
    assert "zipcode" in src.lower()

def test_frontend_has_amount_range_filter():
    src = FRONTEND_PAGE.read_text(encoding="utf-8")
    assert "amtMin" in src or "amount_min" in src

def test_frontend_has_sort_options():
    src = FRONTEND_PAGE.read_text(encoding="utf-8")
    assert "SORT_OPTS" in src or "sort_by" in src

def test_frontend_has_error_state_with_retry():
    src = FRONTEND_PAGE.read_text(encoding="utf-8")
    assert "Retry" in src or "retry" in src.lower()

def test_frontend_has_proper_empty_state():
    src = FRONTEND_PAGE.read_text(encoding="utf-8")
    assert "No bookings" in src

def test_frontend_pagination_controls():
    src = FRONTEND_PAGE.read_text(encoding="utf-8")
    assert "goToPage" in src

def test_frontend_export_csv():
    src = FRONTEND_PAGE.read_text(encoding="utf-8")
    assert "exportCsv" in src

def test_frontend_has_sla_breached_indicator():
    src = FRONTEND_PAGE.read_text(encoding="utf-8")
    assert "sla_breached" in src

def test_frontend_has_assignment_status_column():
    src = FRONTEND_PAGE.read_text(encoding="utf-8")
    assert "assignment_status" in src

def test_frontend_reset_all_filters():
    src = FRONTEND_PAGE.read_text(encoding="utf-8")
    assert "resetAll" in src or "Reset" in src

def test_frontend_no_static_tenant_dropdown():
    """Provider selector must be async, not a static hardcoded list."""
    src = FRONTEND_PAGE.read_text(encoding="utf-8")
    # Should use async search, not a pre-loaded dropdown of all tenants
    assert "tenantSearch" in src or "AsyncTenantSelect" in src

def test_frontend_page_size_options():
    src = FRONTEND_PAGE.read_text(encoding="utf-8")
    assert "50" in src and "100" in src  # multiple page size options

def test_frontend_correct_active_nav():
    src = FRONTEND_PAGE.read_text(encoding="utf-8")
    assert 'activeNav="bookings"' in src

# ── Detail page ───────────────────────────────────────────────────────────────

def test_detail_page_uses_admin_bookings_api():
    src = DETAIL_PAGE.read_text(encoding="utf-8")
    assert "adminBookingsApi" in src

def test_detail_page_does_not_use_tenant_bookings_api_for_get():
    """The critical fix — detail page must use admin endpoint, not tenant endpoint."""
    src = DETAIL_PAGE.read_text(encoding="utf-8")
    # Must use adminBookingsApi.get(), not the tenant-scoped bookingsApi.get()
    # Strip comments first — the docstring mentions the old pattern
    import re as _re
    # Remove single-line // comments and multi-line /* */ and docstring comment block
    no_comments = _re.sub(r"/\*.*?\*/", "", src, flags=_re.DOTALL)
    no_comments = _re.sub(r"//.*", "", no_comments)
    # Check that bare bookingsApi.get( (without "admin" prefix) doesn't appear in live code
    assert "adminBookingsApi.get(" in no_comments, "Must use adminBookingsApi.get()"
    # The old bookingsApi.get( should not be in executable code lines
    # (it's fine in comment strings)
    lines_with_old = [
        ln for ln in no_comments.splitlines()
        if "bookingsApi.get(" in ln and "adminBookingsApi" not in ln
    ]
    assert len(lines_with_old) == 0, f"Found old bookingsApi.get() in non-comment code: {lines_with_old}"

def test_detail_page_uses_admin_get_timeline():
    src = DETAIL_PAGE.read_text(encoding="utf-8")
    assert "adminBookingsApi.getTimeline" in src

def test_detail_page_uses_admin_list_notes():
    src = DETAIL_PAGE.read_text(encoding="utf-8")
    assert "adminBookingsApi.listNotes" in src

def test_detail_page_uses_admin_cancel():
    src = DETAIL_PAGE.read_text(encoding="utf-8")
    assert "adminBookingsApi.cancel" in src

def test_detail_page_uses_admin_void():
    src = DETAIL_PAGE.read_text(encoding="utf-8")
    assert "adminBookingsApi.void" in src

def test_detail_page_correct_field_service_name():
    """Must use service_name (admin field), not service_type_id (tenant field)."""
    src = DETAIL_PAGE.read_text(encoding="utf-8")
    assert "service_name" in src

def test_detail_page_correct_field_category_name():
    """Must use category_name, not service_category."""
    src = DETAIL_PAGE.read_text(encoding="utf-8")
    assert "category_name" in src

def test_detail_page_correct_field_estimated_amount():
    """Must use estimated_amount, not quoted_price."""
    src = DETAIL_PAGE.read_text(encoding="utf-8")
    assert "estimated_amount" in src
    assert "quoted_price" not in src

def test_detail_page_breadcrumb_points_to_bookings():
    src = DETAIL_PAGE.read_text(encoding="utf-8")
    assert "/admin/bookings" in src

def test_detail_page_correct_active_nav():
    src = DETAIL_PAGE.read_text(encoding="utf-8")
    assert 'activeNav="bookings"' in src

def test_detail_page_has_error_state():
    src = DETAIL_PAGE.read_text(encoding="utf-8")
    assert "Could not load" in src or "error" in src.lower()

def test_detail_page_has_retry_button():
    src = DETAIL_PAGE.read_text(encoding="utf-8")
    assert "Retry" in src

def test_detail_page_shows_location_fields():
    src = DETAIL_PAGE.read_text(encoding="utf-8")
    assert "state" in src and "district" in src

def test_detail_page_shows_job_status():
    src = DETAIL_PAGE.read_text(encoding="utf-8")
    assert "job_status" in src

def test_detail_page_shows_assignment_status():
    src = DETAIL_PAGE.read_text(encoding="utf-8")
    assert "assignment_status" in src

def test_detail_page_shows_sla_breached():
    src = DETAIL_PAGE.read_text(encoding="utf-8")
    assert "sla_breached" in src

def test_detail_page_has_timeline_section():
    src = DETAIL_PAGE.read_text(encoding="utf-8")
    assert "Timeline" in src

def test_detail_page_has_notes_section():
    src = DETAIL_PAGE.read_text(encoding="utf-8")
    assert "Notes" in src

def test_detail_page_has_cancel_modal():
    src = DETAIL_PAGE.read_text(encoding="utf-8")
    assert "cancelModal" in src

def test_detail_page_has_void_modal():
    src = DETAIL_PAGE.read_text(encoding="utf-8")
    assert "voidModal" in src
