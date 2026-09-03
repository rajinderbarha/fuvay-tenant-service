"""Canonical Admin Home Services bookings/jobs regression contract."""
from pathlib import Path


ROOT = Path(__file__).parent.parent
ROUTER = ROOT / "app/engines/booking/admin_router.py"
WORKSPACE = ROOT / "frontend/super-admin/app/admin/home-services/bookings-jobs/page.tsx"
LEGACY_DETAIL = ROOT / "frontend/super-admin/app/admin/bookings/[id]/page.tsx"
API_TS = ROOT / "frontend/super-admin/lib/api.ts"
MAIN_PY = ROOT / "app/main.py"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_canonical_files_exist_and_legacy_detail_is_deleted():
    assert ROUTER.exists()
    assert WORKSPACE.exists()
    assert not LEGACY_DETAIL.exists()


def test_admin_booking_router_is_registered_and_protected():
    router = _read(ROUTER)
    assert "/v1/admin/bookings" in router
    assert "require_super_admin" in router
    assert "booking_admin_router" in _read(MAIN_PY)


def test_admin_booking_router_has_read_and_lifecycle_operations():
    router = _read(ROUTER)
    for route in ('router.get("")', '"/summary"', '"/export"',
                  '"/{booking_id}"', "timeline", "notes", "/cancel", "/void"):
        assert route in router


def test_admin_booking_sql_uses_real_columns_and_joins():
    router = _read(ROUTER)
    import re
    without_docstring = re.sub(r'^""".*?"""', "", router, count=1, flags=re.DOTALL)
    assert "b.deleted_at IS NULL" not in without_docstring
    assert "t.deleted_at IS NULL" not in without_docstring
    for expression in ("JOIN tenants", "JOIN users", "master_services", "JOIN jobs",
                       "ms.service_name", "address->>'state'", "address->>'district'"):
        assert expression in router


def test_admin_booking_filters_and_safe_sorting_remain_available():
    router = _read(ROUTER)
    for field in ("service_id", "state", "district", "amount_min", "amount_max",
                  "scheduled_from", "scheduled_to", "sort_by", "sort_dir", "_VALID_SORT"):
        assert field in router


def test_admin_booking_api_client_remains_wired():
    api = _read(API_TS)
    assert "adminBookingsApi" in api
    for method in ("getTimeline", "listNotes", "tenantSearch", "cancel", "void"):
        assert method in api


def test_canonical_workspace_has_filters_summary_and_pagination():
    page = _read(WORKSPACE)
    for marker in ("adminBookingsApi", "METRIC_TILES", "ProviderFilter", "tenantSearch",
                   "filtersOpen", "FilterChip", "zipcode", "amount_min", "Pagination"):
        assert marker in page


def test_canonical_workspace_has_real_inline_detail():
    page = _read(WORKSPACE)
    assert "WorkDetailDrawer" in page
    assert 'aria-label="Work item details"' in page
    assert "finalRecordsAdminApi.getJob" in page
    assert "adminExecutionApi.getJobTimeline" in page
    assert "adminExecutionApi.getJobNotes" in page


def test_inline_detail_shows_service_location_sla_timeline_notes_and_price():
    page = _read(WORKSPACE)
    for marker in ("Customer & Service", "Location", "SLA & Schedule", "Timeline",
                   "Notes", "price_snapshot", "customer_total", "display_price"):
        assert marker in page


def test_canonical_navigation_identity_is_used():
    page = _read(WORKSPACE)
    assert 'activeNav="home-services-operations"' in page
    assert 'href="/admin/bookings"' not in page
