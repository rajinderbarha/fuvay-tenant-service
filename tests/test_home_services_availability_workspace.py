"""Contract checks for the provider Availability & Capacity workspace."""
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "frontend/tenant-portal/app/(tenant)/home-services/availability/page.tsx"
GRID = ROOT / "frontend/tenant-portal/components/availability/WeeklyGrid.tsx"
FILTERS = ROOT / "frontend/tenant-portal/components/availability/AvailabilityFilters.tsx"
ROUTER = ROOT / "app/engines/home_service_assignment/availability_planner_router.py"
RESOLVER = ROOT / "app/engines/home_service_assignment/availability_resolver.py"
MIGRATION = ROOT / "alembic/versions/297_availability_planner_scale_indexes.py"


def source(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def test_planner_contract_has_real_server_filters_and_pagination():
    router = source(ROUTER)
    for query in ("search", "designation", "capability", "availability", "focus_date", "limit", "offset"):
        assert f"{query}:" in router
    page = source(PAGE)
    for parameter in ("search", "designation", "capability", "availability", "focus_date", "limit", "offset"):
        assert f'qs.set("{parameter}"' in page or f"{parameter}:" in page
    assert "planner.data.pagination.has_next" in page


def test_capability_filter_uses_stable_service_id_and_not_selected_member_data():
    filters = source(FILTERS)
    page = source(PAGE)
    assert "value: item.id" in filters
    assert "available_filters.capabilities" in page
    assert "/team/${selectedStaffId}/overview" not in page


def test_navigation_has_no_dead_copy_control_and_uses_canonical_links():
    page = source(PAGE)
    grid = source(GRID)
    assert "Copy previous week" not in page
    assert "onClick={goToday}" in page
    assert "moveRange(-1)" in page and "moveRange(1)" in page
    assert "technician=${selectedStaffId}" in page
    assert "staff_id=${selectedStaffId}" not in page
    assert "router.push(`/service-jobs/${jobId}`)" in page
    assert "event.stopPropagation()" in grid


def test_resolver_is_batched_field_technician_only_and_keeps_invalid_assignments_visible():
    resolver = source(RESOLVER)
    assert "_prefetch_resolution_cache" in resolver
    assert 'db.info["availability_resolution_cache"] = cache' in resolver
    assert "member_type IN ('technician','owner_technician')" in resolver
    assert '"job_id": str(a["id"])' in resolver
    assert "R_ASSIGNMENT_OUTSIDE_AVAILABILITY" in resolver
    assert "working_window" in resolver and "break_window" in resolver and "leave_window" in resolver


def test_scale_migration_covers_roster_capability_rules_jobs_and_leave():
    migration = source(MIGRATION)
    for index in (
        "ix_ptm_availability_roster",
        "ix_ptm_supported_offerings_gin",
        "ix_par_availability_scope_day",
        "ix_sj_availability_staff_date",
        "ix_sto_availability_staff_range",
        "ix_stor_availability_staff_range",
    ):
        assert index in migration
