"""
Step 6 — Job Assignment + Staff Status Lifecycle.

Job execution foundation after booking -> job conversion (Step 5):
tenant assigns staff -> staff accepts/rejects -> staff moves job through the
valid status lifecycle -> every transition recorded in job_status_history ->
tenant/customer can track progress. Strict tenant/staff/customer isolation.
"""
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.exceptions import ServiceOSException, NotFoundException
from app.engines.field_ops.constants import JS, ALLOWED_TRANSITIONS, TERMINAL_STATUSES
from app.engines.field_ops.service import FieldOpsService
from app.engines.field_ops.models import Job, JobStatusHistory
from app.engines.auth.models import User
from app.schemas.base import ERROR_CODES

utcnow = lambda: datetime.now(timezone.utc)


def make_db_returning(*objs):
    """Each call to db.execute returns the next object in sequence (wrapped
    so .scalar_one_or_none() works); falls back to repeating the last one."""
    results = []
    for o in objs:
        r = MagicMock()
        r.scalar_one_or_none.return_value = o
        results.append(r)
    db = MagicMock()
    db.execute = AsyncMock(side_effect=results if len(results) > 1 else None,
                            return_value=results[0] if len(results) == 1 else None)
    db.add = MagicMock(); db.flush = AsyncMock()
    return db


def make_job(**overrides):
    defaults = dict(
        id=uuid.uuid4(), tenant_id=uuid.uuid4(), customer_id=uuid.uuid4(),
        assigned_staff_id=None, status=JS.PENDING_ASSIGNMENT, job_type="repair",
        booking_id=None, sla_minutes=None, current_status_started_at=None,
        updated_at=utcnow(), created_at=utcnow(), city="Mumbai", zipcode="400001",
        service_type_id="ac_repair", estimated_price=Decimal("500"),
        scheduled_at=None, staff_rejection_reason=None,
    )
    defaults.update(overrides)
    return MagicMock(**defaults)


def make_staff(**overrides):
    defaults = dict(id=uuid.uuid4(), tenant_id=uuid.uuid4(), role="staff",
                     is_active=True, full_name="Aman Technician", phone="9990001111")
    defaults.update(overrides)
    return MagicMock(**defaults)


# ── 1. Constants / transitions ────────────────────────────────────────────────

def test_assigned_status_exists():
    assert JS.ASSIGNED == "assigned"

def test_rejected_by_staff_status_exists():
    assert JS.REJECTED_BY_STAFF == "rejected_by_staff"

def test_completed_status_exists():
    assert JS.COMPLETED == "completed"

def test_pending_assignment_to_assigned_allowed():
    assert JS.ASSIGNED in ALLOWED_TRANSITIONS[JS.PENDING_ASSIGNMENT]

def test_assigned_to_accepted_allowed():
    assert JS.ACCEPTED in ALLOWED_TRANSITIONS[JS.ASSIGNED]

def test_assigned_to_rejected_by_staff_allowed():
    assert JS.REJECTED_BY_STAFF in ALLOWED_TRANSITIONS[JS.ASSIGNED]

def test_full_lifecycle_chain_present():
    chain = [JS.ACCEPTED, JS.EN_ROUTE, JS.ARRIVED, JS.ASSESSMENT_STARTED,
             JS.ASSESSMENT_COMPLETE, JS.WORK_STARTED, JS.WORK_COMPLETE,
             JS.QUALITY_CHECK, JS.QUALITY_PASSED, JS.PENDING_SIGN_OFF, JS.SIGNED_OFF]
    for cur, nxt in zip(chain, chain[1:]):
        assert nxt in ALLOWED_TRANSITIONS[cur], f"{cur} -> {nxt} missing"

def test_signed_off_to_completed_allowed():
    assert JS.COMPLETED in ALLOWED_TRANSITIONS[JS.SIGNED_OFF]

def test_completed_is_terminal():
    assert JS.COMPLETED in TERMINAL_STATUSES
    assert ALLOWED_TRANSITIONS[JS.COMPLETED] == []

def test_cancellation_allowed_from_pending_assignment_assigned_accepted():
    assert JS.CANCELLED in ALLOWED_TRANSITIONS[JS.PENDING_ASSIGNMENT]
    assert JS.CANCELLED in ALLOWED_TRANSITIONS[JS.ASSIGNED]
    assert JS.CANCELLED in ALLOWED_TRANSITIONS[JS.ACCEPTED]

def test_invalid_jump_pending_assignment_to_en_route_blocked():
    assert JS.EN_ROUTE not in ALLOWED_TRANSITIONS[JS.PENDING_ASSIGNMENT]

def test_invalid_jump_assigned_to_work_started_blocked():
    assert JS.WORK_STARTED not in ALLOWED_TRANSITIONS[JS.ASSIGNED]

def test_invalid_jump_accepted_to_completed_blocked():
    assert JS.COMPLETED not in ALLOWED_TRANSITIONS[JS.ACCEPTED]

def test_invalid_jump_completed_to_work_started_blocked():
    assert ALLOWED_TRANSITIONS[JS.COMPLETED] == []

def test_invalid_jump_cancelled_to_accepted_blocked():
    assert ALLOWED_TRANSITIONS[JS.CANCELLED] == []


# ── 2. Error codes ─────────────────────────────────────────────────────────────

@pytest.mark.parametrize("code", [
    "JOB_NOT_FOUND", "JOB_ACCESS_DENIED", "JOB_ASSIGNMENT_FAILED", "JOB_ALREADY_ASSIGNED",
    "JOB_NOT_ASSIGNABLE", "STAFF_NOT_FOUND", "STAFF_INACTIVE", "STAFF_TENANT_MISMATCH",
    "STAFF_NOT_ASSIGNED_TO_JOB", "INVALID_JOB_STATUS", "INVALID_JOB_STATUS_TRANSITION",
    "JOB_ALREADY_COMPLETED", "JOB_ALREADY_CANCELLED", "JOB_STATUS_UPDATE_FAILED",
    "JOB_REJECTION_REASON_REQUIRED", "JOB_HISTORY_NOT_FOUND", "CUSTOMER_JOB_ACCESS_DENIED",
    "TENANT_JOB_ACCESS_DENIED", "CROSS_TENANT_ASSIGNMENT_BLOCKED",
])
def test_error_code_registered(code):
    assert code in ERROR_CODES


# ── 3. Model fields ────────────────────────────────────────────────────────────

@pytest.mark.parametrize("field", [
    "assigned_at", "assigned_by_user_id", "accepted_at", "rejected_at",
    "staff_rejection_reason", "en_route_at", "arrived_at", "work_started_at",
    "work_completed_at", "cancelled_at", "cancellation_reason", "status_updated_at",
    "minutes_in_status", "sla_breached", "sla_breach_level",
    "current_status_started_at", "closing_notes",
])
def test_job_model_has_step6_field(field):
    assert hasattr(Job, field)


# ── 4. Assignment ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_tenant_owner_can_assign_own_job_to_active_staff():
    tid = uuid.uuid4()
    job = make_job(tenant_id=tid, status=JS.PENDING_ASSIGNMENT)
    staff = make_staff(tenant_id=tid)
    db = make_db_returning(job, staff)
    svc = FieldOpsService(db=db, actor_id=uuid.uuid4(), actor_role="tenant_owner", actor_tenant_id=tid)
    svc._write_history = AsyncMock(); svc._publish = AsyncMock()

    result = await svc.assign_staff(job.id, staff.id, notes="Nearest technician")
    assert result["status"] == JS.ASSIGNED
    assert result["assigned_staff_id"] == str(staff.id)
    assert job.assigned_staff_id == staff.id
    assert job.status == JS.ASSIGNED
    assert job.assigned_at is not None

@pytest.mark.asyncio
async def test_assignment_creates_status_history():
    tid = uuid.uuid4()
    job = make_job(tenant_id=tid, status=JS.PENDING_ASSIGNMENT)
    staff = make_staff(tenant_id=tid)
    db = make_db_returning(job, staff)
    svc = FieldOpsService(db=db, actor_id=uuid.uuid4(), actor_role="tenant_owner", actor_tenant_id=tid)
    svc._write_history = AsyncMock(); svc._publish = AsyncMock()

    await svc.assign_staff(job.id, staff.id)
    svc._write_history.assert_awaited_once()
    args = svc._write_history.call_args.args
    assert args[2] == JS.ASSIGNED

@pytest.mark.asyncio
async def test_tenant_owner_cannot_assign_another_tenants_job():
    job = make_job(tenant_id=uuid.uuid4(), status=JS.PENDING_ASSIGNMENT)
    db = make_db_returning(job)
    svc = FieldOpsService(db=db, actor_id=uuid.uuid4(), actor_role="tenant_owner",
                           actor_tenant_id=uuid.uuid4())
    with pytest.raises(ServiceOSException) as exc:
        await svc.assign_staff(job.id, uuid.uuid4())
    assert exc.value.error_code == "JOB_NOT_FOUND"

@pytest.mark.asyncio
async def test_cannot_assign_staff_from_another_tenant():
    tid = uuid.uuid4()
    job = make_job(tenant_id=tid, status=JS.PENDING_ASSIGNMENT)
    staff = make_staff(tenant_id=uuid.uuid4())  # different tenant
    db = make_db_returning(job, staff)
    svc = FieldOpsService(db=db, actor_id=uuid.uuid4(), actor_role="tenant_owner", actor_tenant_id=tid)
    with pytest.raises(ServiceOSException) as exc:
        await svc.assign_staff(job.id, staff.id)
    assert exc.value.error_code == "CROSS_TENANT_ASSIGNMENT_BLOCKED"

@pytest.mark.asyncio
async def test_cannot_assign_inactive_staff():
    tid = uuid.uuid4()
    job = make_job(tenant_id=tid, status=JS.PENDING_ASSIGNMENT)
    staff = make_staff(tenant_id=tid, is_active=False)
    db = make_db_returning(job, staff)
    svc = FieldOpsService(db=db, actor_id=uuid.uuid4(), actor_role="tenant_owner", actor_tenant_id=tid)
    with pytest.raises(ServiceOSException) as exc:
        await svc.assign_staff(job.id, staff.id)
    assert exc.value.error_code == "STAFF_INACTIVE"

@pytest.mark.asyncio
async def test_cannot_assign_completed_job():
    tid = uuid.uuid4()
    job = make_job(tenant_id=tid, status=JS.COMPLETED)
    db = make_db_returning(job)
    svc = FieldOpsService(db=db, actor_id=uuid.uuid4(), actor_role="tenant_owner", actor_tenant_id=tid)
    with pytest.raises(ServiceOSException) as exc:
        await svc.assign_staff(job.id, uuid.uuid4())
    assert exc.value.error_code == "JOB_NOT_ASSIGNABLE"

@pytest.mark.asyncio
async def test_reassignment_works_from_rejected_by_staff():
    tid = uuid.uuid4()
    job = make_job(tenant_id=tid, status=JS.REJECTED_BY_STAFF)
    staff = make_staff(tenant_id=tid)
    db = make_db_returning(job, staff)
    svc = FieldOpsService(db=db, actor_id=uuid.uuid4(), actor_role="tenant_owner", actor_tenant_id=tid)
    svc._write_history = AsyncMock(); svc._publish = AsyncMock()
    result = await svc.assign_staff(job.id, staff.id)
    assert result["status"] == JS.ASSIGNED

@pytest.mark.asyncio
async def test_assign_unknown_staff_raises_staff_not_found():
    tid = uuid.uuid4()
    job = make_job(tenant_id=tid, status=JS.PENDING_ASSIGNMENT)
    db = make_db_returning(job, None)
    svc = FieldOpsService(db=db, actor_id=uuid.uuid4(), actor_role="tenant_owner", actor_tenant_id=tid)
    with pytest.raises(ServiceOSException) as exc:
        await svc.assign_staff(job.id, uuid.uuid4())
    assert exc.value.error_code == "STAFF_NOT_FOUND"


# ── 5. Staff accept / reject ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_assigned_staff_can_accept_job():
    me = uuid.uuid4()
    job = make_job(assigned_staff_id=me, status=JS.ASSIGNED)
    db = make_db_returning(job)
    svc = FieldOpsService(db=db, actor_id=me, actor_role="staff")
    svc._write_history = AsyncMock(); svc._publish = AsyncMock()

    result = await svc.accept_job(job.id, notes="On my way")
    assert result["status"] == JS.ACCEPTED
    assert job.accepted_at is not None

@pytest.mark.asyncio
async def test_accept_creates_status_history():
    me = uuid.uuid4()
    job = make_job(assigned_staff_id=me, status=JS.ASSIGNED)
    db = make_db_returning(job)
    svc = FieldOpsService(db=db, actor_id=me, actor_role="staff")
    svc._write_history = AsyncMock(); svc._publish = AsyncMock()
    await svc.accept_job(job.id)
    svc._write_history.assert_awaited_once()

@pytest.mark.asyncio
async def test_unassigned_staff_cannot_accept_job():
    job = make_job(assigned_staff_id=uuid.uuid4(), status=JS.ASSIGNED)
    db = make_db_returning(job)
    svc = FieldOpsService(db=db, actor_id=uuid.uuid4(), actor_role="staff")
    with pytest.raises(ServiceOSException) as exc:
        await svc.accept_job(job.id)
    assert exc.value.error_code == "STAFF_NOT_ASSIGNED_TO_JOB"

@pytest.mark.asyncio
async def test_staff_can_reject_assigned_job_with_reason():
    me = uuid.uuid4()
    job = make_job(assigned_staff_id=me, status=JS.ASSIGNED)
    db = make_db_returning(job)
    svc = FieldOpsService(db=db, actor_id=me, actor_role="staff")
    svc._write_history = AsyncMock(); svc._publish = AsyncMock()

    result = await svc.reject_assignment(job.id, "Too far from my current location")
    assert result["status"] == JS.REJECTED_BY_STAFF
    assert job.staff_rejection_reason == "Too far from my current location"

@pytest.mark.asyncio
async def test_reject_requires_reason():
    me = uuid.uuid4()
    job = make_job(assigned_staff_id=me, status=JS.ASSIGNED)
    db = make_db_returning(job)
    svc = FieldOpsService(db=db, actor_id=me, actor_role="staff")
    with pytest.raises(ServiceOSException) as exc:
        await svc.reject_assignment(job.id, "")
    assert exc.value.error_code == "JOB_REJECTION_REASON_REQUIRED"

@pytest.mark.asyncio
async def test_reject_only_from_assigned_status():
    me = uuid.uuid4()
    job = make_job(assigned_staff_id=me, status=JS.ACCEPTED)
    db = make_db_returning(job)
    svc = FieldOpsService(db=db, actor_id=me, actor_role="staff")
    with pytest.raises(ServiceOSException) as exc:
        await svc.reject_assignment(job.id, "changed my mind")
    assert exc.value.error_code == "INVALID_JOB_STATUS_TRANSITION"


# ── 6. Status lifecycle (via existing update_status) ──────────────────────────

LIFECYCLE_STEPS = [
    (JS.ACCEPTED, JS.EN_ROUTE), (JS.EN_ROUTE, JS.ARRIVED),
    (JS.ARRIVED, JS.ASSESSMENT_STARTED), (JS.ASSESSMENT_STARTED, JS.ASSESSMENT_COMPLETE),
    (JS.ASSESSMENT_COMPLETE, JS.WORK_STARTED), (JS.WORK_STARTED, JS.WORK_COMPLETE),
    (JS.WORK_COMPLETE, JS.QUALITY_CHECK), (JS.QUALITY_CHECK, JS.QUALITY_PASSED),
    (JS.QUALITY_PASSED, JS.PENDING_SIGN_OFF), (JS.PENDING_SIGN_OFF, JS.SIGNED_OFF),
    (JS.SIGNED_OFF, JS.COMPLETED),
]

@pytest.mark.asyncio
@pytest.mark.parametrize("from_status,to_status", LIFECYCLE_STEPS)
async def test_lifecycle_step_succeeds(from_status, to_status):
    me = uuid.uuid4()
    job = make_job(assigned_staff_id=me, status=from_status, job_type="repair",
                    started_at=None, completed_at=None, checklist=[])
    db = make_db_returning(job)
    svc = FieldOpsService(db=db, actor_id=me, actor_role="staff")
    svc._write_history = AsyncMock(); svc._publish = AsyncMock()

    result = await svc.update_status(job.id, to_status, "progressing", None, None)
    assert result["status"] == to_status

@pytest.mark.asyncio
async def test_invalid_transition_pending_assignment_to_en_route_fails():
    me = uuid.uuid4()
    job = make_job(assigned_staff_id=me, status=JS.PENDING_ASSIGNMENT)
    db = make_db_returning(job)
    svc = FieldOpsService(db=db, actor_id=me, actor_role="staff")
    with pytest.raises(ServiceOSException) as exc:
        await svc.update_status(job.id, JS.EN_ROUTE, None, None, None)
    assert exc.value.error_code == "INVALID_TRANSITION"

@pytest.mark.asyncio
async def test_invalid_transition_accepted_to_completed_fails():
    me = uuid.uuid4()
    job = make_job(assigned_staff_id=me, status=JS.ACCEPTED)
    db = make_db_returning(job)
    svc = FieldOpsService(db=db, actor_id=me, actor_role="staff")
    with pytest.raises(ServiceOSException) as exc:
        await svc.update_status(job.id, JS.COMPLETED, None, None, None)
    assert exc.value.error_code == "INVALID_TRANSITION"

@pytest.mark.asyncio
async def test_completed_to_work_started_fails():
    me = uuid.uuid4()
    job = make_job(assigned_staff_id=me, status=JS.COMPLETED)
    db = make_db_returning(job)
    svc = FieldOpsService(db=db, actor_id=me, actor_role="staff")
    with pytest.raises(ServiceOSException) as exc:
        await svc.update_status(job.id, JS.WORK_STARTED, None, None, None)
    assert exc.value.error_code == "CONFLICT"  # terminal status guard fires first

@pytest.mark.asyncio
async def test_status_update_creates_history_every_time():
    me = uuid.uuid4()
    job = make_job(assigned_staff_id=me, status=JS.ACCEPTED)
    db = make_db_returning(job)
    svc = FieldOpsService(db=db, actor_id=me, actor_role="staff")
    svc._write_history = AsyncMock(); svc._publish = AsyncMock()
    await svc.update_status(job.id, JS.EN_ROUTE, None, None, None)
    svc._write_history.assert_awaited_once()

@pytest.mark.asyncio
async def test_status_update_sets_timestamp_fields():
    me = uuid.uuid4()
    job = make_job(assigned_staff_id=me, status=JS.ACCEPTED)
    db = make_db_returning(job)
    svc = FieldOpsService(db=db, actor_id=me, actor_role="staff")
    svc._write_history = AsyncMock(); svc._publish = AsyncMock()
    await svc.update_status(job.id, JS.EN_ROUTE, None, None, None)
    assert job.en_route_at is not None
    assert job.status_updated_at is not None
    assert job.current_status_started_at is not None


# ── 7. Security / isolation ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_staff_cannot_update_another_staffs_job():
    job = make_job(assigned_staff_id=uuid.uuid4(), status=JS.ACCEPTED)
    db = make_db_returning(job)
    svc = FieldOpsService(db=db, actor_id=uuid.uuid4(), actor_role="staff")
    with pytest.raises(NotFoundException):
        await svc.update_status(job.id, JS.EN_ROUTE, None, None, None)

@pytest.mark.asyncio
async def test_customer_cannot_update_job_status_via_router_role_gate():
    # Service layer doesn't special-case "customer" inside update_status —
    # the router only wires PUT /status through FIELD_OPS_JOBS_UPDATE, which
    # customers never hold (see ROLE_PERMISSIONS["customer"]).
    from app.core.permissions import P, ROLE_PERMISSIONS
    assert P.FIELD_OPS_JOBS_UPDATE not in ROLE_PERMISSIONS["customer"]

@pytest.mark.asyncio
async def test_tenant_owner_cannot_update_another_tenants_job():
    job = make_job(tenant_id=uuid.uuid4(), assigned_staff_id=uuid.uuid4(), status=JS.ACCEPTED)
    db = make_db_returning(job)
    svc = FieldOpsService(db=db, actor_id=uuid.uuid4(), actor_role="tenant_owner",
                           actor_tenant_id=uuid.uuid4())
    with pytest.raises(NotFoundException):
        await svc.update_status(job.id, JS.EN_ROUTE, None, None, None)

@pytest.mark.asyncio
async def test_cross_tenant_assignment_is_blocked():
    tid = uuid.uuid4()
    job = make_job(tenant_id=tid, status=JS.PENDING_ASSIGNMENT)
    staff = make_staff(tenant_id=uuid.uuid4())
    db = make_db_returning(job, staff)
    svc = FieldOpsService(db=db, actor_id=uuid.uuid4(), actor_role="tenant_owner", actor_tenant_id=tid)
    with pytest.raises(ServiceOSException) as exc:
        await svc.assign_staff(job.id, staff.id)
    assert exc.value.error_code == "CROSS_TENANT_ASSIGNMENT_BLOCKED"

@pytest.mark.asyncio
async def test_super_admin_can_assign_any_tenants_job():
    tid = uuid.uuid4()
    job = make_job(tenant_id=tid, status=JS.PENDING_ASSIGNMENT)
    staff = make_staff(tenant_id=tid)
    db = make_db_returning(job, staff)
    svc = FieldOpsService(db=db, actor_id=uuid.uuid4(), actor_role="super_admin")
    svc._write_history = AsyncMock(); svc._publish = AsyncMock()
    result = await svc.assign_staff(job.id, staff.id)
    assert result["status"] == JS.ASSIGNED


# ── 8. Customer tracking ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_customer_can_view_own_job_progress():
    cid = uuid.uuid4()
    job = make_job(customer_id=cid, status=JS.EN_ROUTE, assigned_staff_id=None)
    db = make_db_returning(job)
    svc = FieldOpsService(db=db, actor_id=cid, actor_role="customer")
    result = await svc.get_customer_job_progress(job.id, cid)
    assert result["status"] == JS.EN_ROUTE
    assert result["job_id"] == str(job.id)

@pytest.mark.asyncio
async def test_customer_cannot_view_another_customers_job():
    job = make_job(customer_id=uuid.uuid4(), status=JS.EN_ROUTE)
    db = make_db_returning(job)
    svc = FieldOpsService(db=db, actor_id=uuid.uuid4(), actor_role="customer")
    with pytest.raises(NotFoundException):
        await svc.get_customer_job_progress(job.id, uuid.uuid4())

@pytest.mark.asyncio
async def test_progress_shows_assigned_staff_public_summary():
    cid = uuid.uuid4()
    staff = make_staff()
    job = make_job(customer_id=cid, status=JS.ACCEPTED, assigned_staff_id=staff.id)
    db = make_db_returning(job, staff)
    svc = FieldOpsService(db=db, actor_id=cid, actor_role="customer")
    result = await svc.get_customer_job_progress(job.id, cid)
    assert result["assigned_staff"]["name"] == staff.full_name


# ── 9. SLA ──────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_sla_info_returns_on_job_detail():
    me = uuid.uuid4()
    job = make_job(assigned_staff_id=me, status=JS.EN_ROUTE, sla_minutes=60,
                    current_status_started_at=utcnow() - timedelta(minutes=10),
                    minutes_in_status=0, sla_breached=False, sla_breach_level=None)
    db = make_db_returning(job)
    svc = FieldOpsService(db=db, actor_id=me, actor_role="staff")
    result = await svc.get_job(job.id)
    assert "minutes_in_status" in result and "sla_breach_level" in result

@pytest.mark.asyncio
async def test_sla_on_time_band():
    job = make_job(sla_minutes=60, status=JS.EN_ROUTE,
                    current_status_started_at=utcnow() - timedelta(minutes=10))
    svc = FieldOpsService(db=MagicMock())
    svc._update_sla(job)
    assert job.sla_breach_level == "on_time"

@pytest.mark.asyncio
async def test_sla_at_risk_band():
    job = make_job(sla_minutes=60, status=JS.EN_ROUTE,
                    current_status_started_at=utcnow() - timedelta(minutes=75))
    svc = FieldOpsService(db=MagicMock())
    svc._update_sla(job)
    assert job.sla_breach_level == "at_risk"

@pytest.mark.asyncio
async def test_sla_overdue_band():
    job = make_job(sla_minutes=60, status=JS.EN_ROUTE,
                    current_status_started_at=utcnow() - timedelta(minutes=100))
    svc = FieldOpsService(db=MagicMock())
    svc._update_sla(job)
    assert job.sla_breach_level == "overdue"

@pytest.mark.asyncio
async def test_sla_critical_band():
    job = make_job(sla_minutes=60, status=JS.EN_ROUTE,
                    current_status_started_at=utcnow() - timedelta(minutes=130))
    svc = FieldOpsService(db=MagicMock())
    svc._update_sla(job)
    assert job.sla_breach_level == "critical"


# ── 10. valid-next-statuses & history endpoints ────────────────────────────────

@pytest.mark.asyncio
async def test_valid_next_statuses_for_accepted():
    me = uuid.uuid4()
    job = make_job(assigned_staff_id=me, status=JS.ACCEPTED)
    db = make_db_returning(job)
    svc = FieldOpsService(db=db, actor_id=me, actor_role="staff")
    result = await svc.get_valid_next_statuses(job.id)
    assert result["current_status"] == JS.ACCEPTED
    assert JS.EN_ROUTE in result["valid_next_statuses"]
    assert JS.CANCELLED in result["valid_next_statuses"]

@pytest.mark.asyncio
async def test_job_history_returns_records():
    me = uuid.uuid4()
    job = make_job(assigned_staff_id=me, status=JS.ACCEPTED)
    h1 = MagicMock(from_status=JS.ASSIGNED, to_status=JS.ACCEPTED, changed_by_role="staff",
                    reason="Accepted job", created_at=utcnow())
    db = make_db_returning(job)
    scalars_result = MagicMock(); scalars_result.all.return_value = [h1]
    hist_result = MagicMock(); hist_result.scalars.return_value = scalars_result
    db.execute = AsyncMock(side_effect=[
        MagicMock(scalar_one_or_none=MagicMock(return_value=job)), hist_result])
    svc = FieldOpsService(db=db, actor_id=me, actor_role="staff")
    result = await svc.get_job_history(job.id)
    assert result["job_id"] == str(job.id)
    assert len(result["history"]) == 1
    assert result["history"][0]["new_status"] == JS.ACCEPTED


# ── 11. List jobs — role-based scoping ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_tenant_owner_list_jobs_forced_to_own_tenant():
    own_tid = uuid.uuid4()
    other_tid = uuid.uuid4()
    captured = {}
    scalars_result = MagicMock(); scalars_result.all.return_value = []
    exec_result = MagicMock(); exec_result.scalars.return_value = scalars_result
    db = MagicMock()
    async def fake_execute(query):
        captured["sql"] = str(query.compile(compile_kwargs={"literal_binds": True}))
        return exec_result
    db.execute = fake_execute
    svc = FieldOpsService(db=db, actor_id=uuid.uuid4(), actor_role="tenant_owner", actor_tenant_id=own_tid)

    await svc.list_jobs(other_tid, None, None, 50, None)
    assert own_tid.hex in captured["sql"]
    assert other_tid.hex not in captured["sql"]


# ── 12. OpenAPI ──────────────────────────────────────────────────────────────────

def test_openapi_includes_assignment_endpoint():
    from app.main import app
    schema = app.openapi()
    assert "/v1/jobs/{job_id}/assign" in schema["paths"]

def test_openapi_includes_staff_job_endpoints():
    from app.main import app
    schema = app.openapi()
    assert "/v1/staff/me/jobs" in schema["paths"]
    assert "/v1/staff/me/jobs/{job_id}/accept" in schema["paths"]

def test_openapi_includes_customer_job_endpoints():
    from app.main import app
    schema = app.openapi()
    assert "/v1/customer/jobs" in schema["paths"]
    assert "/v1/customer/jobs/{job_id}/progress" in schema["paths"]

def test_openapi_includes_status_update_endpoint():
    from app.main import app
    schema = app.openapi()
    assert "/v1/jobs/{job_id}/status" in schema["paths"]

def test_openapi_includes_history_endpoint():
    from app.main import app
    schema = app.openapi()
    assert "/v1/jobs/{job_id}/history" in schema["paths"]

def test_openapi_schema_is_valid():
    from app.main import app
    schema = app.openapi()
    assert schema["openapi"]
    assert "paths" in schema and "components" in schema
