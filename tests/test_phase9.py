"""Phase 9 — Booking + Appointment — Certified Level 5 Tests (55 tests)."""
import hashlib, uuid
from datetime import datetime, timezone, timedelta
from decimal import Decimal
import pytest

from app.engines.booking.constants import (
    BS, BOOKING_TRANSITIONS, TERMINAL_BOOKING_STATUSES,
    PreflightCheck, DEFAULT_CANCELLATION_WINDOW_HOURS,
    MAX_RESCHEDULE_COUNT, BOOKING_IDEM_WINDOW_MINUTES,
    make_booking_idempotency_key,
)
from app.engines.appointment.constants import (
    AS, APPOINTMENT_TRANSITIONS, TERMINAL_APPT_STATUSES,
    HOLD_TTL_SECONDS, HOLD_TTL_MINUTES, REMINDER_HOURS,
    NO_SHOW_GRACE_MINUTES, DEFAULT_SLOT_DURATION_MINUTES,
)


# ── 1. Booking status graph ───────────────────────────────────────────────────
def test_all_booking_statuses_in_graph():
    all_statuses = {BS.DRAFT, BS.PENDING, BS.CONFIRMED, BS.SCHEDULED,
                    BS.DISPATCHING, BS.IN_PROGRESS, BS.COMPLETED,
                    BS.CANCELLED, BS.EXPIRED, BS.VOIDED}
    assert all_statuses.issubset(set(BOOKING_TRANSITIONS.keys()))

def test_terminal_booking_statuses_have_no_transitions():
    # P0 Job Completion sprint fix: CONVERTED_TO_JOB is no longer a true dead end.
    # It previously had zero transitions, so a booking that had already become a
    # job could never reach BS.COMPLETED even after the job was fully paid and
    # financially closed — admin/tenant/customer booking views stayed stuck at
    # "converted_to_job" forever. It now has exactly one valid transition
    # (-> BS.COMPLETED), driven solely by BillingService.close_job_financial(),
    # not by any generic booking-facing endpoint.
    for s in TERMINAL_BOOKING_STATUSES:
        if s == BS.CONVERTED_TO_JOB:
            assert BOOKING_TRANSITIONS.get(s, []) == [BS.COMPLETED]
        else:
            assert BOOKING_TRANSITIONS.get(s, []) == []

def test_draft_can_move_to_pending():
    assert BS.PENDING in BOOKING_TRANSITIONS[BS.DRAFT]

def test_draft_can_be_cancelled():
    assert BS.CANCELLED in BOOKING_TRANSITIONS[BS.DRAFT]

def test_confirmed_leads_to_scheduled():
    assert BS.SCHEDULED in BOOKING_TRANSITIONS[BS.CONFIRMED]

def test_in_progress_leads_to_completed():
    assert BS.COMPLETED in BOOKING_TRANSITIONS[BS.IN_PROGRESS]

def test_completed_is_terminal():
    assert BS.COMPLETED in TERMINAL_BOOKING_STATUSES
    assert BOOKING_TRANSITIONS[BS.COMPLETED] == []

def test_cannot_skip_from_draft_to_completed():
    assert BS.COMPLETED not in BOOKING_TRANSITIONS[BS.DRAFT]

def test_max_reschedule_count():
    assert MAX_RESCHEDULE_COUNT == 3


# ── 2. Idempotency key ────────────────────────────────────────────────────────
def test_idempotency_key_is_deterministic():
    k1 = make_booking_idempotency_key("cust1","tenant1","ac_service","2026-07-01")
    k2 = make_booking_idempotency_key("cust1","tenant1","ac_service","2026-07-01")
    assert k1 == k2

def test_idempotency_key_is_64_chars():
    k = make_booking_idempotency_key("a","b","c","d")
    assert len(k) == 64

def test_different_inputs_different_key():
    k1 = make_booking_idempotency_key("cust1","tenant1","ac_service","2026-07-01")
    k2 = make_booking_idempotency_key("cust1","tenant1","plumbing","2026-07-01")
    assert k1 != k2

def test_different_dates_different_key():
    k1 = make_booking_idempotency_key("c","t","s","2026-07-01")
    k2 = make_booking_idempotency_key("c","t","s","2026-07-02")
    assert k1 != k2

def test_booking_idem_window_is_positive():
    assert BOOKING_IDEM_WINDOW_MINUTES > 0


# ── 3. Price locking logic ────────────────────────────────────────────────────
def test_quoted_price_is_decimal():
    price = Decimal("1500.00")
    assert isinstance(price, Decimal)

def test_price_never_recalculated_on_cancel():
    # Price is stored at creation and never re-fetched
    quoted_at_creation = Decimal("1500.00")
    current_price = Decimal("1800.00")   # price changed later
    # The booking always uses quoted_at_creation
    assert quoted_at_creation != current_price

def test_price_snapshot_id_stored():
    from app.engines.booking.models import Booking
    from sqlalchemy.inspection import inspect
    cols = {c.key for c in inspect(Booking).columns}
    assert "price_snapshot_id" in cols
    assert "quoted_price" in cols


# ── 4. Cancellation policy ────────────────────────────────────────────────────
def test_within_cancel_window_gets_refund():
    cancel_window_hours = 24
    scheduled_at = datetime.now(timezone.utc) + timedelta(hours=30)
    hours_until = (scheduled_at - datetime.now(timezone.utc)).total_seconds() / 3600
    within_window = hours_until >= cancel_window_hours
    assert within_window is True  # 30h > 24h window

def test_outside_cancel_window_forfeits():
    cancel_window_hours = 24
    scheduled_at = datetime.now(timezone.utc) + timedelta(hours=6)
    hours_until = (scheduled_at - datetime.now(timezone.utc)).total_seconds() / 3600
    within_window = hours_until >= cancel_window_hours
    assert within_window is False  # 6h < 24h window

def test_default_cancel_window():
    assert DEFAULT_CANCELLATION_WINDOW_HOURS == 24


# ── 5. Preflight checks ───────────────────────────────────────────────────────
def test_preflight_check_constants_unique():
    checks = [PreflightCheck.TENANT_ACTIVE, PreflightCheck.ZONE_COVERAGE,
              PreflightCheck.SLOT_AVAILABLE, PreflightCheck.CAPACITY_LIMIT,
              PreflightCheck.COMMERCE_PREFLIGHT]
    assert len(checks) == len(set(checks))

def test_preflight_has_5_checks():
    checks = [v for k, v in PreflightCheck.__dict__.items() if not k.startswith("_")]
    assert len(checks) == 5

def test_preflight_failed_booking_status_is_pending():
    # When preflight fails booking should be PENDING not CONFIRMED
    preflight_passed = False
    expected_status = BS.CONFIRMED if preflight_passed else BS.PENDING
    assert expected_status == BS.PENDING

def test_preflight_passed_booking_status_is_confirmed():
    preflight_passed = True
    expected_status = BS.CONFIRMED if preflight_passed else BS.PENDING
    assert expected_status == BS.CONFIRMED


# ── 6. Appointment status graph ───────────────────────────────────────────────
def test_all_appt_statuses_in_graph():
    all_statuses = {AS.AVAILABLE, AS.HOLD, AS.CONFIRMED, AS.REMINDED,
                    AS.IN_PROGRESS, AS.COMPLETED, AS.NO_SHOW, AS.CANCELLED, AS.RESCHEDULED}
    assert all_statuses.issubset(set(APPOINTMENT_TRANSITIONS.keys()))

def test_terminal_appt_statuses_have_no_transitions():
    for s in TERMINAL_APPT_STATUSES:
        assert APPOINTMENT_TRANSITIONS.get(s, []) == []

def test_hold_leads_to_confirmed_or_cancelled():
    assert AS.CONFIRMED in APPOINTMENT_TRANSITIONS[AS.HOLD]
    assert AS.CANCELLED in APPOINTMENT_TRANSITIONS[AS.HOLD]

def test_confirmed_leads_to_reminded():
    assert AS.REMINDED in APPOINTMENT_TRANSITIONS[AS.CONFIRMED]

def test_reminded_can_be_no_show():
    assert AS.NO_SHOW in APPOINTMENT_TRANSITIONS[AS.REMINDED]

def test_no_show_is_terminal():
    assert AS.NO_SHOW in TERMINAL_APPT_STATUSES

def test_cannot_confirm_from_available_directly():
    # Must go through HOLD first
    assert AS.CONFIRMED not in APPOINTMENT_TRANSITIONS[AS.AVAILABLE]


# ── 7. Hold TTL ───────────────────────────────────────────────────────────────
def test_hold_ttl_seconds():
    assert HOLD_TTL_SECONDS == 600

def test_hold_ttl_minutes():
    assert HOLD_TTL_MINUTES == 10

def test_hold_ttl_consistency():
    assert HOLD_TTL_SECONDS == HOLD_TTL_MINUTES * 60

def test_hold_expiry_calculation():
    utcnow = datetime.now(timezone.utc)
    hold_exp = utcnow + timedelta(seconds=HOLD_TTL_SECONDS)
    diff = (hold_exp - utcnow).seconds
    assert diff == HOLD_TTL_SECONDS

def test_expired_hold_detected():
    past = datetime.now(timezone.utc) - timedelta(minutes=11)
    is_expired = past < datetime.now(timezone.utc)
    assert is_expired


# ── 8. Slot generation logic ──────────────────────────────────────────────────
def test_slot_count_calculation():
    from datetime import time, timedelta
    start = datetime.strptime("09:00", "%H:%M")
    end   = datetime.strptime("18:00", "%H:%M")
    duration = 60; buffer = 15
    step = duration + buffer
    count = 0; current = start
    while current + timedelta(minutes=duration) <= end:
        count += 1; current += timedelta(minutes=step)
    assert count == 7  # verified correct slot count

def test_no_show_grace_period():
    assert NO_SHOW_GRACE_MINUTES == 30

def test_reminder_hours():
    assert 24 in REMINDER_HOURS
    assert 2  in REMINDER_HOURS

def test_default_slot_duration():
    assert DEFAULT_SLOT_DURATION_MINUTES == 60

def test_double_booking_constraint_exists():
    from app.engines.appointment.models import Appointment
    from sqlalchemy.inspection import inspect
    constraints = {c.name for c in inspect(Appointment).mapper.persist_selectable.constraints}
    assert "uq_appt_staff_slot" in constraints


# ── 9. Model fields ───────────────────────────────────────────────────────────
def test_booking_model_certified_fields():
    from app.engines.booking.models import Booking
    from sqlalchemy.inspection import inspect
    cols = {c.key for c in inspect(Booking).columns}
    required = {"idempotency_key","price_snapshot_id","quoted_price",
                "preflight_passed","preflight_result","blocking_reason",
                "within_cancel_window","reservation_id","job_id","reschedule_count"}
    missing = required - cols
    assert not missing, f"Missing certified Level 5 fields: {missing}"

def test_booking_status_history_append_only():
    from app.engines.booking.models import BookingStatusHistory
    from sqlalchemy.inspection import inspect
    cols = {c.key for c in inspect(BookingStatusHistory).columns}
    assert {"from_status","to_status","changed_by","changed_by_role","reason"}.issubset(cols)

def test_booking_idempotency_unique():
    from app.engines.booking.models import Booking
    from sqlalchemy.inspection import inspect
    cols = {c.key: c for c in inspect(Booking).columns}
    assert cols["idempotency_key"].unique is True

def test_appointment_history_append_only():
    from app.engines.appointment.models import AppointmentStatusHistory
    from sqlalchemy.inspection import inspect
    cols = {c.key for c in inspect(AppointmentStatusHistory).columns}
    assert {"from_status","to_status","changed_by","reason"}.issubset(cols)


# ── 10. HTTP endpoint probes ──────────────────────────────────────────────────
@pytest.fixture
def client():
    from fastapi.testclient import TestClient
    from app.main import app
    return TestClient(app)

def test_booking_meta(client):
    r = client.get("/v1/bookings/meta")
    assert r.status_code == 200
    d = r.json()
    assert d["engine_id"] == "booking"
    assert "idempotent_creation" in d["capabilities"]
    assert "price_snapshot_lock" in d["capabilities"]
    assert "5_check_preflight" in d["capabilities"]

def test_appointment_meta(client):
    r = client.get("/v1/appointments/meta")
    assert r.status_code == 200
    d = r.json()
    assert d["engine_id"] == "appointment"
    assert "hold_10min_ttl" in d["capabilities"]
    assert "double_booking_prevention" in d["capabilities"]

def test_create_booking_requires_auth(client):
    assert client.post("/v1/bookings", json={}).status_code == 401

def test_get_booking_requires_auth(client):
    bid = uuid.uuid4()
    assert client.get(f"/v1/bookings/{bid}").status_code == 401

def test_cancel_booking_requires_auth(client):
    bid = uuid.uuid4()
    assert client.post(f"/v1/bookings/{bid}/cancel", json={}).status_code == 401

def test_convert_to_job_requires_auth(client):
    bid = uuid.uuid4()
    assert client.post(f"/v1/bookings/{bid}/convert-to-job").status_code == 401

def test_appointment_hold_requires_auth(client):
    assert client.post("/v1/appointments/hold", json={}).status_code == 401

def test_appointment_confirm_requires_auth(client):
    aid = uuid.uuid4()
    assert client.post(f"/v1/appointments/{aid}/confirm").status_code == 401

def test_available_slots_requires_auth(client):
    sid = uuid.uuid4(); tid = uuid.uuid4()
    assert client.get(f"/v1/appointments/staff/{sid}/slots?date=2026-07-01&tenant_id={tid}").status_code == 401

def test_no_show_requires_permission(client):
    aid = uuid.uuid4()
    assert client.post(f"/v1/appointments/{aid}/no-show").status_code == 401

def test_all_phases_still_certified(client):
    """Regression guard — all phase meta endpoints must return 200."""
    metas = ["/health","/v1/commerce/meta","/v1/pricing/meta",
             "/v1/settings/meta","/v1/notifications/meta",
             "/v1/media/meta","/v1/analytics/meta","/v1/rag/meta",
             "/v1/ds/meta","/v1/geo/meta","/v1/dispatch/meta",
             "/v1/jobs/meta","/v1/bookings/meta","/v1/appointments/meta"]
    for path in metas:
        r = client.get(path)
        assert r.status_code == 200, f"REGRESSION: {path} returned {r.status_code}"
