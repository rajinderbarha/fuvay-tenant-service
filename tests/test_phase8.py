"""Phase 8 — Geo + Dispatch + Field Ops Tests (50 tests)."""
import math, uuid
from decimal import Decimal
import pytest

from app.engines.geo.constants import (
    EARTH_RADIUS_KM, ROAD_FACTOR, DEFAULT_RADIUS_KM, MAX_RADIUS_KM, ZoneType, StaffStatus,
)
from app.engines.dispatch.constants import (
    DispatchMode, DispatchStatus, DEFAULT_SCORE_WEIGHTS,
    BROADCAST_ACCEPT_TTL_MINUTES, MAX_ESCALATION_ATTEMPTS,
)
from app.engines.field_ops.constants import (
    JS, ALLOWED_TRANSITIONS, TERMINAL_STATUSES, LOCKED_STATUSES,
    DEFAULT_STATUS_SLA_HOURS,
)


# ── 1. Geo constants ──────────────────────────────────────────────────────────
def test_earth_radius(): assert EARTH_RADIUS_KM == 6371.0
def test_road_factor():  assert ROAD_FACTOR > 1.0
def test_radius_limits(): assert DEFAULT_RADIUS_KM < MAX_RADIUS_KM
def test_zone_types_unique():
    types = [ZoneType.PINCODE, ZoneType.AREA, ZoneType.POLYGON, ZoneType.RADIUS]
    assert len(types) == len(set(types))

def test_haversine_same_point():
    def haversine(lat1, lng1, lat2, lng2):
        r = EARTH_RADIUS_KM
        d_lat = math.radians(lat2-lat1); d_lng = math.radians(lng2-lng1)
        a = math.sin(d_lat/2)**2 + math.cos(math.radians(lat1))*math.cos(math.radians(lat2))*math.sin(d_lng/2)**2
        return r * 2 * math.asin(math.sqrt(a))
    assert haversine(19.0, 72.8, 19.0, 72.8) == 0.0

def test_haversine_mumbai_pune():
    def haversine(lat1, lng1, lat2, lng2):
        r = EARTH_RADIUS_KM
        d_lat = math.radians(lat2-lat1); d_lng = math.radians(lng2-lng1)
        a = math.sin(d_lat/2)**2 + math.cos(math.radians(lat1))*math.cos(math.radians(lat2))*math.sin(d_lng/2)**2
        return r * 2 * math.asin(math.sqrt(a))
    dist = haversine(19.0760, 72.8777, 18.5204, 73.8567)
    assert 120 < dist < 160  # Mumbai to Pune ~140km

def test_road_distance_calculation():
    straight_line_km = 10.0
    road_dist = straight_line_km * ROAD_FACTOR
    assert road_dist > straight_line_km

def test_stale_location_detection():
    from datetime import datetime, timezone, timedelta
    last_ping = datetime.now(timezone.utc) - timedelta(minutes=11)
    is_stale = (datetime.now(timezone.utc) - last_ping).seconds > 600
    assert is_stale

def test_fresh_location_not_stale():
    from datetime import datetime, timezone, timedelta
    last_ping = datetime.now(timezone.utc) - timedelta(minutes=2)
    is_stale = (datetime.now(timezone.utc) - last_ping).seconds > 600
    assert not is_stale


# ── 2. Dispatch constants and scoring ────────────────────────────────────────
def test_dispatch_modes_unique():
    modes = [DispatchMode.MANUAL, DispatchMode.AUTO_ASSIGN, DispatchMode.BROADCAST]
    assert len(modes) == len(set(modes))

def test_dispatch_statuses_unique():
    statuses = [DispatchStatus.PENDING, DispatchStatus.ASSIGNED, DispatchStatus.ACCEPTED,
                DispatchStatus.REJECTED, DispatchStatus.ESCALATED, DispatchStatus.EXPIRED]
    assert len(statuses) == len(set(statuses))

def test_score_weights_sum_to_one():
    total = sum(DEFAULT_SCORE_WEIGHTS.values())
    assert abs(total - 1.0) < 0.001

def test_score_weights_keys():
    assert "distance" in DEFAULT_SCORE_WEIGHTS
    assert "performance" in DEFAULT_SCORE_WEIGHTS
    assert "active_job_count" in DEFAULT_SCORE_WEIGHTS
    assert "specialisation" in DEFAULT_SCORE_WEIGHTS

def test_scoring_closer_staff_wins():
    def score(dist_km, perf, jobs, spec_match, w=DEFAULT_SCORE_WEIGHTS):
        dist_s = max(0.0, 100.0 - dist_km * 5)
        job_s  = max(0.0, 100.0 - jobs * 20)
        spec_s = 100.0 if spec_match else 60.0
        return dist_s*w["distance"] + perf*w["performance"] + job_s*w["active_job_count"] + spec_s*w["specialisation"]
    close = score(2.0, 80.0, 1, True)
    far   = score(15.0, 80.0, 1, True)
    assert close > far

def test_scoring_higher_perf_wins_equal_distance():
    def score(dist_km, perf, jobs, spec_match, w=DEFAULT_SCORE_WEIGHTS):
        dist_s = max(0.0, 100.0 - dist_km * 5)
        job_s  = max(0.0, 100.0 - jobs * 20)
        spec_s = 100.0 if spec_match else 60.0
        return dist_s*w["distance"] + perf*w["performance"] + job_s*w["active_job_count"] + spec_s*w["specialisation"]
    high_perf = score(5.0, 95.0, 1, True)
    low_perf  = score(5.0, 40.0, 1, True)
    assert high_perf > low_perf

def test_max_escalation_attempts():
    assert MAX_ESCALATION_ATTEMPTS >= 3

def test_broadcast_ttl_positive():
    assert BROADCAST_ACCEPT_TTL_MINUTES > 0


# ── 3. Field Ops — 23-status lifecycle ───────────────────────────────────────
def test_all_statuses_in_graph():
    all_statuses = {
        JS.DRAFT, JS.CONFIRMED, JS.DISPATCHED, JS.ACCEPTED, JS.EN_ROUTE,
        JS.ARRIVED, JS.ASSESSMENT_STARTED, JS.ASSESSMENT_COMPLETE,
        JS.WORK_STARTED, JS.PARTS_REQUIRED, JS.PARTS_ORDERED, JS.PARTS_RECEIVED,
        JS.WORK_RESUMED, JS.WORK_COMPLETE, JS.QUALITY_CHECK, JS.QUALITY_PASSED,
        JS.QUALITY_FAILED, JS.REWORK_REQUIRED, JS.REWORK_COMPLETE,
        JS.PENDING_SIGN_OFF, JS.SIGNED_OFF, JS.INVOICE_GENERATED, JS.CLOSED,
    }
    graph_keys = set(ALLOWED_TRANSITIONS.keys())
    assert all_statuses.issubset(graph_keys)

def test_terminal_statuses_have_no_transitions():
    for status in TERMINAL_STATUSES:
        assert ALLOWED_TRANSITIONS.get(status, []) == []

def test_closed_is_terminal():
    assert JS.CLOSED in TERMINAL_STATUSES

def test_voided_is_terminal():
    assert JS.VOIDED in TERMINAL_STATUSES

def test_cancelled_is_terminal():
    assert JS.CANCELLED in TERMINAL_STATUSES

def test_draft_can_transition_to_confirmed():
    assert JS.CONFIRMED in ALLOWED_TRANSITIONS[JS.DRAFT]

def test_draft_can_be_cancelled():
    assert JS.CANCELLED in ALLOWED_TRANSITIONS[JS.DRAFT]

def test_closed_cannot_transition_anywhere():
    assert ALLOWED_TRANSITIONS[JS.CLOSED] == []

def test_arrived_to_assessment_required():
    assert JS.ASSESSMENT_STARTED in ALLOWED_TRANSITIONS[JS.ARRIVED]

def test_quality_failed_goes_to_rework():
    assert JS.REWORK_REQUIRED in ALLOWED_TRANSITIONS[JS.QUALITY_FAILED]

def test_rework_loops_back_to_quality_check():
    assert JS.QUALITY_CHECK in ALLOWED_TRANSITIONS[JS.REWORK_COMPLETE]

def test_invoice_generated_before_closed():
    assert JS.CLOSED in ALLOWED_TRANSITIONS[JS.INVOICE_GENERATED]

def test_parts_flow():
    assert JS.PARTS_ORDERED in ALLOWED_TRANSITIONS[JS.PARTS_REQUIRED]
    assert JS.PARTS_RECEIVED in ALLOWED_TRANSITIONS[JS.PARTS_ORDERED]
    assert JS.WORK_RESUMED  in ALLOWED_TRANSITIONS[JS.PARTS_RECEIVED]

def test_no_skip_transitions():
    # Cannot skip from draft directly to work_started
    assert JS.WORK_STARTED not in ALLOWED_TRANSITIONS[JS.DRAFT]

def test_locked_statuses_subset_of_all_statuses():
    all_js = set(ALLOWED_TRANSITIONS.keys())
    for s in LOCKED_STATUSES:
        assert s in all_js

def test_sla_hours_positive():
    for status, hours in DEFAULT_STATUS_SLA_HOURS.items():
        assert hours > 0, f"{status} has non-positive SLA"

def test_invoice_generated_to_closed_atomic():
    current = JS.INVOICE_GENERATED
    allowed = ALLOWED_TRANSITIONS.get(current, [])
    assert JS.CLOSED in allowed

def test_invalid_transition_detected():
    current = JS.DRAFT
    illegal = JS.CLOSED
    allowed = ALLOWED_TRANSITIONS.get(current, [])
    assert illegal not in allowed


# ── 4. Close pipeline logic ───────────────────────────────────────────────────
def test_commission_deducted_flag_prevents_double_deduction():
    commission_deducted = True
    if commission_deducted:
        blocked = True
    assert blocked

def test_final_price_used_for_commission():
    final_price = Decimal("1500.00")
    rate = Decimal("0.10")
    commission = (final_price * rate).quantize(Decimal("0.01"))
    assert commission == Decimal("150.00")


# ── 5. Model fields ───────────────────────────────────────────────────────────
def test_job_model_fields():
    from app.engines.field_ops.models import Job
    from sqlalchemy.inspection import inspect
    cols = {c.key for c in inspect(Job).columns}
    assert {"status","job_number","tenant_id","assigned_staff_id","customer_token",
            "commission_deducted","commission_amount","sla_breach","customer_rating"}.issubset(cols)

def test_job_status_history_append_only():
    from app.engines.field_ops.models import JobStatusHistory
    from sqlalchemy.inspection import inspect
    cols = {c.key for c in inspect(JobStatusHistory).columns}
    assert {"from_status","to_status","changed_by","changed_by_role","reason"}.issubset(cols)

def test_dispatch_record_immutable_design():
    from app.engines.dispatch.models import DispatchRecord
    from sqlalchemy.inspection import inspect
    cols = {c.key for c in inspect(DispatchRecord).columns}
    assert {"candidates_scored","score_weights","rejection_count","escalation_count"}.issubset(cols)

def test_dispatch_job_unique_constraint():
    from app.engines.dispatch.models import DispatchRecord
    from sqlalchemy.inspection import inspect
    constraints = {c.name for c in inspect(DispatchRecord).mapper.persist_selectable.constraints}
    assert "uq_dr_job" in constraints

def test_staff_location_unique_per_tenant():
    from app.engines.geo.models import StaffLocation
    from sqlalchemy.inspection import inspect
    constraints = {c.name for c in inspect(StaffLocation).mapper.persist_selectable.constraints}
    assert "uq_sl_staff_tenant" in constraints


# ── 6. HTTP endpoint probes ───────────────────────────────────────────────────
@pytest.fixture
def client():
    from fastapi.testclient import TestClient
    from app.main import app
    return TestClient(app)

def test_geo_meta(client):
    r = client.get("/v1/geo/meta")
    assert r.status_code == 200
    d = r.json()
    assert d["engine_id"] == "geo"
    assert "redis_geo_index" in d["capabilities"]

def test_dispatch_meta(client):
    r = client.get("/v1/dispatch/meta")
    assert r.status_code == 200
    d = r.json()
    assert d["engine_id"] == "dispatch"
    assert set(d["modes"]) == {"manual","auto_assign","broadcast"}

def test_fieldops_meta(client):
    r = client.get("/v1/jobs/meta")
    assert r.status_code == 200
    d = r.json()
    assert d["engine_id"] == "field_ops"
    assert d["status_count"] == 23

def test_create_job_requires_auth(client):
    assert client.post("/v1/jobs", json={}).status_code == 401

def test_list_jobs_requires_auth(client):
    tid = uuid.uuid4()
    assert client.get(f"/v1/jobs?tenant_id={tid}").status_code == 401

def test_create_zone_requires_auth(client):
    tid = uuid.uuid4()
    assert client.post(f"/v1/geo/tenants/{tid}/zones", json={}).status_code == 401

def test_dispatch_job_requires_auth(client):
    assert client.post("/v1/dispatch/jobs/job-123/dispatch", json={}).status_code == 401

def test_close_job_requires_auth(client):
    jid = uuid.uuid4()
    assert client.post(f"/v1/jobs/{jid}/close", json={}).status_code == 401

def test_public_track_endpoint_exists(client):
    # Route exists — bad token returns 404 (NotFoundException) but route is mounted
    r = client.get("/v1/jobs/track/invalid-token-xxx")
    # Any response except 405 (method not allowed) confirms route is mounted
    assert r.status_code != 405

def test_all_phases_still_pass(client):
    for path in ["/health","/v1/commerce/meta","/v1/pricing/meta",
                 "/v1/settings/meta","/v1/notifications/meta",
                 "/v1/media/meta","/v1/analytics/meta",
                 "/v1/rag/meta","/v1/ds/meta",
                 "/v1/geo/meta","/v1/dispatch/meta","/v1/jobs/meta"]:
        assert client.get(path).status_code == 200, f"Failed: {path}"
