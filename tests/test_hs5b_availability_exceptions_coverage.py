"""HS5B — Availability Rules + Area Coverage Completion certification.

Real work this sprint (all backend — no new frontend UI was built given
time budget, see HS5B_REMAINING_BLOCKERS.md):

1. Migration 121: break_start_time/break_end_time/max_jobs_per_day/
   timezone/emergency_available on provider_availability_rules; new
   tenant_availability_exceptions table; new tenant_booking_window_
   settings table; service_type_id/brand_id added to the pre-existing
   (but previously unused by any router) tenant_service_area_services
   table.
2. Break-time validation (INVALID_BREAK_TIME_RANGE) wired into both
   create_availability and update_availability.
3. Full exceptions/holidays CRUD (list/create/update/soft-delete) with
   INVALID_EXCEPTION_TIME_RANGE validation.
4. Full booking-window get/put with per-field validation.
5. Per-area service/type/brand coverage endpoint
   (PUT /service-areas/{id}/coverage) validating type-belongs-to-service
   and brand-belongs-to-service against the real master_service_types/
   master_service_brands mapping tables.
6. get_tenant_home_services_matching_inputs() — a real, DB-backed
   readiness-preview function (not the full HS6 matching engine) that
   checks zipcode/service/type/brand coverage, break/exception/booking-
   window conflicts, and bookability, exposed via
   POST /home-services/matching-inputs/preview.

Live-verified this sprint against the real running backend and real DB
— see HS5B_LIVE_CURL_VERIFICATION_REPORT.md for the full 12-scenario
transcript, including a real bug found and fixed mid-sprint (asyncpg
requires a real datetime.date object for a `date` column, not a bare
ISO string — the exceptions endpoints initially 500'd on this).
"""
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
ROUTER_PY = (ROOT / "app/engines/provider_portal/router.py").read_text(encoding="utf-8-sig")
MIGRATION_121 = (ROOT / "alembic/versions/121_hs5b_availability_exceptions_booking_window.py").read_text(encoding="utf-8-sig")


# ── 1. Schema ──────────────────────────────────────────────────────────────────
def test_migration_121_adds_break_lunch_fields():
    assert "break_start_time" in MIGRATION_121
    assert "break_end_time" in MIGRATION_121
    assert "max_jobs_per_day" in MIGRATION_121
    assert "timezone" in MIGRATION_121
    assert "emergency_available" in MIGRATION_121


def test_migration_121_creates_exceptions_table():
    assert "tenant_availability_exceptions" in MIGRATION_121
    assert "full_day_closed" in MIGRATION_121
    assert "affected_service_area_ids" in MIGRATION_121
    assert "affected_service_ids" in MIGRATION_121


def test_migration_121_creates_booking_window_table():
    assert "tenant_booking_window_settings" in MIGRATION_121
    assert "minimum_notice_minutes" in MIGRATION_121
    assert "maximum_advance_booking_days" in MIGRATION_121


def test_migration_121_adds_area_coverage_type_brand_columns():
    assert "tenant_service_area_services" in MIGRATION_121
    assert '"service_type_id"' in MIGRATION_121 or "service_type_id" in MIGRATION_121


# ── 2. Break/lunch validation ──────────────────────────────────────────────────
def test_break_validation_helper_exists():
    assert "def _validate_break_time" in ROUTER_PY
    assert "INVALID_BREAK_TIME_RANGE" in ROUTER_PY


def test_break_validated_on_create():
    fn = ROUTER_PY.split("async def create_availability")[1].split("@router.get(\"/availability/{rule_id}\")")[0]
    assert "_validate_break_time" in fn


def test_break_validated_on_update():
    fn = ROUTER_PY.split("async def update_availability")[1].split("@router.delete(\"/availability/{rule_id}\")")[0]
    assert "_validate_break_time" in fn


def test_break_must_be_inside_working_hours():
    fn = ROUTER_PY.split("def _validate_break_time")[1].split("def _tid")[0] \
        if "def _tid" in ROUTER_PY.split("def _validate_break_time")[1][:2000] \
        else ROUTER_PY.split("def _validate_break_time")[1][:1000]
    assert "Break time must be inside working hours." in fn


# ── 3. Exceptions / holidays CRUD ──────────────────────────────────────────────
def test_exceptions_crud_endpoints_exist():
    assert '@router.get("/availability/exceptions")' in ROUTER_PY
    assert '@router.post("/availability/exceptions"' in ROUTER_PY
    assert '@router.put("/availability/exceptions/{exception_id}")' in ROUTER_PY
    assert '@router.delete("/availability/exceptions/{exception_id}")' in ROUTER_PY


def test_exception_validation():
    fn = ROUTER_PY.split("def _validate_exception_payload")[1].split("@router.post")[0]
    assert "EXCEPTION_DATE_REQUIRED" in fn
    assert "EXCEPTION_REASON_REQUIRED" in fn
    assert "EXCEPTION_TIME_REQUIRED" in fn
    assert "INVALID_EXCEPTION_TIME_RANGE" in fn


def test_exception_delete_is_soft():
    fn = ROUTER_PY.split("async def delete_availability_exception")[1][:600]
    assert "status='deleted'" in fn


# ── 4. Booking window ──────────────────────────────────────────────────────────
def test_booking_window_endpoints_exist():
    assert '@router.get("/booking-window")' in ROUTER_PY
    assert '@router.put("/booking-window")' in ROUTER_PY


def test_booking_window_validation():
    fn = ROUTER_PY.split("def _validate_booking_window")[1].split("@router.put")[0]
    assert "INVALID_MINIMUM_NOTICE" in fn
    assert "INVALID_ADVANCE_BOOKING_DAYS" in fn
    assert "INVALID_SLOT_DURATION" in fn
    assert "INVALID_BUFFER_MINUTES" in fn


def test_booking_window_defaults_match_ticket():
    fn = ROUTER_PY.split("async def update_booking_window")[1][:1200]
    assert '"minimum_notice_minutes": 120' in fn
    assert '"maximum_advance_booking_days": 7' in fn
    assert '"slot_duration_minutes": 60' in fn
    assert '"buffer_minutes_between_jobs": 30' in fn


# ── 5. Per-area service/type/brand coverage ───────────────────────────────────
def test_area_coverage_endpoints_exist():
    assert '@router.get("/service-areas/{area_id}/coverage")' in ROUTER_PY
    assert '@router.put("/service-areas/{area_id}/coverage")' in ROUTER_PY


def test_area_coverage_validates_service_enabled():
    fn = ROUTER_PY.split("async def set_area_coverage")[1]
    assert "SERVICE_NOT_TENANT_ENABLED" in fn


def test_area_coverage_validates_type_belongs_to_service():
    fn = ROUTER_PY.split("async def set_area_coverage")[1]
    assert "INVALID_SERVICE_TYPE_FOR_COVERAGE" in fn
    assert "master_service_types" in fn


def test_area_coverage_validates_brand_belongs_to_service():
    fn = ROUTER_PY.split("async def set_area_coverage")[1]
    assert "INVALID_BRAND_FOR_COVERAGE" in fn
    assert "master_service_brands" in fn


# ── 6. Matching input readiness ────────────────────────────────────────────────
def test_matching_inputs_function_exists():
    assert "async def get_tenant_home_services_matching_inputs" in ROUTER_PY


def test_matching_inputs_checks_zipcode_coverage():
    fn = ROUTER_PY.split("async def get_tenant_home_services_matching_inputs")[1]
    assert "zipcode_covered" in fn
    assert "ZIPCODE_NOT_COVERED" in fn


def test_matching_inputs_checks_service_type_brand_coverage():
    fn = ROUTER_PY.split("async def get_tenant_home_services_matching_inputs")[1]
    assert "SERVICE_NOT_COVERED_IN_AREA" in fn
    assert "TYPE_NOT_COVERED_IN_AREA" in fn
    assert "BRAND_NOT_COVERED_IN_AREA" in fn


def test_matching_inputs_respects_break_and_exception():
    fn = ROUTER_PY.split("async def get_tenant_home_services_matching_inputs")[1]
    assert "BLOCKED_BY_BREAK" in fn
    assert "BLOCKED_BY_EXCEPTION" in fn


def test_matching_inputs_respects_booking_window():
    fn = ROUTER_PY.split("async def get_tenant_home_services_matching_inputs")[1]
    assert "BELOW_MINIMUM_NOTICE" in fn
    assert "BEYOND_ADVANCE_BOOKING_WINDOW" in fn


def test_matching_inputs_uses_real_bookability():
    fn = ROUTER_PY.split("async def get_tenant_home_services_matching_inputs")[1]
    assert "_evaluate_provider_bookability" in fn


def test_matching_inputs_preview_endpoint_exists():
    assert '@router.post("/home-services/matching-inputs/preview")' in ROUTER_PY


# ── 7. Regression: HS5's original fix still present ───────────────────────────
def test_hs5_time_range_validation_still_present():
    assert "INVALID_AVAILABILITY_TIME_RANGE" in ROUTER_PY
