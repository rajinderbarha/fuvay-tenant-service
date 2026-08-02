"""
Step 7 — Job Type-Specific Flow: Repair vs Service vs Consultation.

Routing intelligence on top of the existing 23-status lifecycle (Phase 7 /
Step 6): assessment workflow, line-item quotes, consultation->repair
conversion, and a minimal service checklist foundation — each gated by
job_type so repair/service/consultation never cross-contaminate.
"""
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.exceptions import ServiceOSException, NotFoundException
from app.engines.field_ops.constants import (
    JS, JobType, JOB_TYPES, TRANSITIONS_BY_JOB_TYPE, get_allowed_transitions,
)
from app.engines.field_ops.service import FieldOpsService
from app.engines.field_ops.models import Job, JobQuote
from app.schemas.base import ERROR_CODES

utcnow = lambda: datetime.now(timezone.utc)


def make_db_returning(*objs):
    results = []
    for o in objs:
        r = MagicMock(); r.scalar_one_or_none.return_value = o
        results.append(r)
    db = MagicMock()
    if len(results) == 1:
        db.execute = AsyncMock(return_value=results[0])
    else:
        db.execute = AsyncMock(side_effect=results)
    db.add = MagicMock(); db.flush = AsyncMock()
    return db


def make_job(**overrides):
    defaults = dict(
        id=uuid.uuid4(), tenant_id=uuid.uuid4(), customer_id=uuid.uuid4(),
        assigned_staff_id=None, status=JS.ARRIVED, job_type=JobType.REPAIR,
        title="AC Repair", description=None, service_type_id="ac_repair",
        service_category="ac", address={}, pincode=None, city="Mumbai", zipcode="400001",
        address_id=None, service_id=None, matched_service_area_id=None,
        matched_service_area_service_id=None, coverage_match_level=None,
        scheduled_at=None, parent_job_id=None,
        findings=None, recommendation=None, checklist=[],
        assessment_findings=None, recommended_work=None, estimated_parts=[],
        assessment_completed_at=None, quote_required=False, quote_id=None,
        pre_approval_limit=None, quote_sent_at=None, quote_approved_at=None,
        quote_rejected_at=None, quote_rejection_reason=None,
        checklist_required=False, checklist_started_at=None, checklist_completed_at=None,
        converted_from_consultation=False,
        sla_minutes=None, current_status_started_at=None, updated_at=utcnow(), created_at=utcnow(),
        estimated_price=Decimal("500"), staff_rejection_reason=None,
    )
    defaults.update(overrides)
    return MagicMock(**defaults)


# ── 1. job_type / constants ───────────────────────────────────────────────────

def test_job_types_enum():
    # Migration 151: extended from 3 to 9 values to match admin_catalog's
    # VALID_JOB_TYPES, which already allowed all 9 -- the original 3 remain
    # first and unchanged in behavior (see test_module_job_types_reconciliation.py).
    assert JOB_TYPES[:3] == [JobType.REPAIR, JobType.SERVICE, JobType.CONSULTATION]
    assert set(JOB_TYPES) == {
        "repair", "service", "consultation",
        "installation", "uninstallation", "inspection",
        "maintenance", "cleaning", "custom",
    }

def test_transitions_by_job_type_has_all_three():
    for jt in JOB_TYPES:
        assert jt in TRANSITIONS_BY_JOB_TYPE

def test_transitions_by_job_type_repair_matches_get_allowed_transitions():
    for status in TRANSITIONS_BY_JOB_TYPE[JobType.REPAIR]:
        assert (TRANSITIONS_BY_JOB_TYPE[JobType.REPAIR][status]
                == get_allowed_transitions(JobType.REPAIR, status))

def test_checklist_started_complete_statuses_exist():
    assert JS.CHECKLIST_STARTED == "checklist_started"
    assert JS.CHECKLIST_COMPLETE == "checklist_complete"

def test_converted_to_repair_status_exists():
    assert JS.CONVERTED_TO_REPAIR == "converted_to_repair"

def test_quote_sent_alias_matches_quote_pending():
    assert JS.QUOTE_SENT == JS.QUOTE_PENDING == "quote_sent"


@pytest.mark.parametrize("code", [
    "INVALID_JOB_TYPE_TRANSITION", "ASSESSMENT_NOT_ALLOWED_FOR_SERVICE",
    "ASSESSMENT_REQUIRED_BEFORE_WORK", "ASSESSMENT_NOT_STARTED", "ASSESSMENT_ALREADY_COMPLETED",
    "ASSESSMENT_FINDINGS_REQUIRED", "QUOTE_REQUIRED_BEFORE_WORK", "QUOTE_NOT_FOUND",
    "QUOTE_ALREADY_SENT", "QUOTE_ALREADY_APPROVED", "QUOTE_ALREADY_REJECTED",
    "QUOTE_APPROVAL_REQUIRED", "QUOTE_ACCESS_DENIED", "INVALID_QUOTE_AMOUNT",
    "WORK_NOT_ALLOWED_FOR_CONSULTATION", "CHECKLIST_REQUIRED_BEFORE_WORK_COMPLETE",
    "CHECKLIST_NOT_COMPLETE", "CONSULTATION_CONVERSION_NOT_ALLOWED",
    "CONSULTATION_ALREADY_CONVERTED", "PARENT_JOB_NOT_FOUND", "REPAIR_SERVICE_REQUIRED",
    "INVALID_JOB_TYPE", "INVALID_JOB_STATUS_TRANSITION", "QUOTE_EXPIRED",
])
def test_error_code_registered(code):
    assert code in ERROR_CODES


# ── 2. Repair flow ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_repair_requires_assessment_before_work_started():
    job = make_job(status=JS.ARRIVED, job_type=JobType.REPAIR)
    allowed = get_allowed_transitions(job.job_type, job.status)
    assert JS.WORK_STARTED not in allowed
    assert JS.ASSESSMENT_STARTED in allowed

@pytest.mark.asyncio
async def test_repair_arrived_to_assessment_started():
    me = uuid.uuid4()
    job = make_job(status=JS.ARRIVED, job_type=JobType.REPAIR, assigned_staff_id=me)
    db = make_db_returning(job)
    svc = FieldOpsService(db=db, actor_id=me, actor_role="staff")
    svc._write_history = AsyncMock(); svc._publish = AsyncMock()
    result = await svc.start_assessment(job.id)
    assert result["status"] == JS.ASSESSMENT_STARTED

@pytest.mark.asyncio
async def test_repair_assessment_started_to_complete():
    me = uuid.uuid4()
    job = make_job(status=JS.ASSESSMENT_STARTED, job_type=JobType.REPAIR, assigned_staff_id=me)
    db = make_db_returning(job)
    svc = FieldOpsService(db=db, actor_id=me, actor_role="staff")
    svc._write_history = AsyncMock(); svc._publish = AsyncMock()
    result = await svc.complete_assessment(job.id, "Gas leak found", "Replace valve")
    assert result["status"] == JS.ASSESSMENT_COMPLETE
    assert job.assessment_findings == "Gas leak found"
    assert job.recommended_work == "Replace valve"

@pytest.mark.asyncio
async def test_repair_blocks_work_started_before_assessment_complete():
    me = uuid.uuid4()
    job = make_job(status=JS.ARRIVED, job_type=JobType.REPAIR, assigned_staff_id=me)
    db = make_db_returning(job)
    svc = FieldOpsService(db=db, actor_id=me, actor_role="staff")
    with pytest.raises(ServiceOSException) as exc:
        await svc.update_status(job.id, JS.WORK_STARTED, None, None, None)
    assert exc.value.error_code == "INVALID_TRANSITION"

@pytest.mark.asyncio
async def test_repair_quote_required_blocks_work_started():
    me = uuid.uuid4()
    job = make_job(status=JS.ASSESSMENT_COMPLETE, job_type=JobType.REPAIR,
                    assigned_staff_id=me, quote_required=True)
    db = make_db_returning(job)
    svc = FieldOpsService(db=db, actor_id=me, actor_role="staff")
    with pytest.raises(ServiceOSException) as exc:
        await svc.update_status(job.id, JS.WORK_STARTED, None, None, None)
    assert exc.value.error_code == "QUOTE_REQUIRED_BEFORE_WORK"

@pytest.mark.asyncio
async def test_repair_quote_sent_after_assessment_complete():
    me = uuid.uuid4()
    job = make_job(status=JS.ASSESSMENT_COMPLETE, job_type=JobType.REPAIR, assigned_staff_id=me,
                    recommended_work="Replace valve", pre_approval_limit=None)
    quote = MagicMock(id=uuid.uuid4(), job_id=job.id, status="draft", quote_number="QT-1", expires_at=None)
    job_result = MagicMock(); job_result.scalar_one_or_none.return_value = job
    quote_result = MagicMock(); quote_result.scalar_one_or_none.return_value = quote
    no_sent_result = MagicMock(); no_sent_result.scalars.return_value.all.return_value = []
    db = MagicMock()
    db.execute = AsyncMock(side_effect=[job_result, quote_result, no_sent_result])
    db.add = MagicMock(); db.flush = AsyncMock()
    svc = FieldOpsService(db=db, actor_id=me, actor_role="staff")
    svc._write_history = AsyncMock(); svc._publish = AsyncMock()
    result = await svc.send_job_quote(job.id, quote.id)
    assert result["status"] == "sent"
    assert job.status == JS.QUOTE_SENT

@pytest.mark.asyncio
async def test_repair_quote_approved_allows_work_started():
    me = uuid.uuid4()
    job = make_job(status=JS.QUOTE_APPROVED, job_type=JobType.REPAIR,
                    assigned_staff_id=me, quote_required=True)
    db = make_db_returning(job)
    svc = FieldOpsService(db=db, actor_id=me, actor_role="staff")
    svc._write_history = AsyncMock(); svc._publish = AsyncMock()
    result = await svc.update_status(job.id, JS.WORK_STARTED, None, None, None)
    assert result["status"] == JS.WORK_STARTED

@pytest.mark.asyncio
async def test_repair_quote_rejected_blocks_work_path():
    job = make_job(status=JS.QUOTE_REJECTED, job_type=JobType.REPAIR)
    allowed = get_allowed_transitions(job.job_type, job.status)
    assert JS.WORK_STARTED not in allowed

def test_repair_parts_loop_exists():
    allowed = get_allowed_transitions(JobType.REPAIR, JS.PARTS_REQUIRED)
    assert JS.PARTS_ORDERED in allowed

@pytest.mark.asyncio
async def test_repair_quality_failed_goes_to_rework_required():
    me = uuid.uuid4()
    job = make_job(status=JS.QUALITY_CHECK, job_type=JobType.REPAIR, assigned_staff_id=me)
    db = make_db_returning(job)
    svc = FieldOpsService(db=db, actor_id=me, actor_role="staff")
    svc._write_history = AsyncMock(); svc._publish = AsyncMock()
    result = await svc.update_status(job.id, JS.QUALITY_FAILED, None, None, None)
    assert result["status"] == JS.QUALITY_FAILED

@pytest.mark.asyncio
async def test_repair_rework_complete_returns_to_quality_check():
    me = uuid.uuid4()
    job = make_job(status=JS.REWORK_COMPLETE, job_type=JobType.REPAIR, assigned_staff_id=me)
    db = make_db_returning(job)
    svc = FieldOpsService(db=db, actor_id=me, actor_role="staff")
    svc._write_history = AsyncMock(); svc._publish = AsyncMock()
    result = await svc.update_status(job.id, JS.QUALITY_CHECK, None, None, None)
    assert result["status"] == JS.QUALITY_CHECK

def test_repair_cannot_complete_before_sign_off():
    allowed = get_allowed_transitions(JobType.REPAIR, JS.SIGNED_OFF)
    assert JS.COMPLETED in allowed
    not_allowed = get_allowed_transitions(JobType.REPAIR, JS.QUALITY_PASSED)
    assert JS.COMPLETED not in not_allowed


# ── 3. Service flow ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_service_arrived_to_work_started_direct():
    me = uuid.uuid4()
    job = make_job(status=JS.ARRIVED, job_type=JobType.SERVICE, assigned_staff_id=me)
    db = make_db_returning(job)
    svc = FieldOpsService(db=db, actor_id=me, actor_role="staff")
    svc._write_history = AsyncMock(); svc._publish = AsyncMock()
    result = await svc.update_status(job.id, JS.WORK_STARTED, None, None, None)
    assert result["status"] == JS.WORK_STARTED

def test_service_does_not_require_assessment():
    allowed = get_allowed_transitions(JobType.SERVICE, JS.ARRIVED)
    assert JS.ASSESSMENT_STARTED not in allowed

@pytest.mark.asyncio
async def test_service_blocks_assessment_started_by_default():
    me = uuid.uuid4()
    job = make_job(status=JS.ARRIVED, job_type=JobType.SERVICE, assigned_staff_id=me)
    db = make_db_returning(job)
    svc = FieldOpsService(db=db, actor_id=me, actor_role="staff")
    with pytest.raises(ServiceOSException) as exc:
        await svc.update_status(job.id, JS.ASSESSMENT_STARTED, None, None, None)
    assert exc.value.error_code == "ASSESSMENT_NOT_ALLOWED_FOR_SERVICE"

@pytest.mark.asyncio
async def test_service_emergency_assessment_override():
    me = uuid.uuid4()
    job = make_job(status=JS.ARRIVED, job_type=JobType.SERVICE, assigned_staff_id=me)
    db = make_db_returning(job)
    svc = FieldOpsService(db=db, actor_id=me, actor_role="staff")
    svc._write_history = AsyncMock(); svc._publish = AsyncMock()
    result = await svc.update_status(job.id, JS.ASSESSMENT_STARTED, None, None, None,
                                      emergency_assessment=True)
    assert result["status"] == JS.ASSESSMENT_STARTED

@pytest.mark.asyncio
async def test_service_blocks_work_complete_if_checklist_required_incomplete():
    me = uuid.uuid4()
    job = make_job(status=JS.WORK_STARTED, job_type=JobType.SERVICE,
                    assigned_staff_id=me, checklist_required=True)
    db = make_db_returning(job)
    svc = FieldOpsService(db=db, actor_id=me, actor_role="staff")
    with pytest.raises(ServiceOSException) as exc:
        await svc.update_status(job.id, JS.WORK_COMPLETE, None, None, None)
    assert exc.value.error_code == "CHECKLIST_REQUIRED_BEFORE_WORK_COMPLETE"

@pytest.mark.asyncio
async def test_service_allows_work_complete_after_checklist_complete():
    me = uuid.uuid4()
    job = make_job(status=JS.CHECKLIST_COMPLETE, job_type=JobType.SERVICE,
                    assigned_staff_id=me, checklist_required=True)
    db = make_db_returning(job)
    svc = FieldOpsService(db=db, actor_id=me, actor_role="staff")
    svc._write_history = AsyncMock(); svc._publish = AsyncMock()
    result = await svc.update_status(job.id, JS.WORK_COMPLETE, None, None, None)
    assert result["status"] == JS.WORK_COMPLETE

@pytest.mark.asyncio
async def test_service_checklist_start_and_complete():
    me = uuid.uuid4()
    job = make_job(status=JS.WORK_STARTED, job_type=JobType.SERVICE, assigned_staff_id=me,
                    checklist=[{"step": "Clean filter", "completed": True}])
    db = make_db_returning(job)
    svc = FieldOpsService(db=db, actor_id=me, actor_role="staff")
    svc._write_history = AsyncMock(); svc._publish = AsyncMock()
    started = await svc.start_checklist(job.id)
    assert started["status"] == JS.CHECKLIST_STARTED
    completed = await svc.complete_checklist(job.id)
    assert completed["status"] == JS.CHECKLIST_COMPLETE

@pytest.mark.asyncio
async def test_service_checklist_complete_blocked_when_items_incomplete():
    me = uuid.uuid4()
    job = make_job(status=JS.CHECKLIST_STARTED, job_type=JobType.SERVICE, assigned_staff_id=me,
                    checklist=[{"step": "Clean filter", "completed": False, "is_required": True}])
    db = make_db_returning(job)
    svc = FieldOpsService(db=db, actor_id=me, actor_role="staff")
    with pytest.raises(ServiceOSException) as exc:
        await svc.complete_checklist(job.id)
    assert exc.value.error_code == "CHECKLIST_NOT_COMPLETE"

def test_service_goes_through_quality_check():
    allowed = get_allowed_transitions(JobType.SERVICE, JS.WORK_COMPLETE)
    assert JS.QUALITY_CHECK in allowed

def test_service_cannot_use_consultation_conversion():
    allowed = get_allowed_transitions(JobType.SERVICE, JS.QUOTE_APPROVED)
    assert JS.CONVERTED_TO_REPAIR not in allowed


# ── 4. Consultation flow ────────────────────────────────────────────────────────

def test_consultation_arrived_to_assessment_started():
    allowed = get_allowed_transitions(JobType.CONSULTATION, JS.ARRIVED)
    assert JS.ASSESSMENT_STARTED in allowed

def test_consultation_assessment_complete_to_quote_sent():
    allowed = get_allowed_transitions(JobType.CONSULTATION, JS.ASSESSMENT_COMPLETE)
    assert JS.QUOTE_SENT in allowed

@pytest.mark.asyncio
async def test_consultation_blocks_work_started():
    me = uuid.uuid4()
    job = make_job(status=JS.ASSESSMENT_COMPLETE, job_type=JobType.CONSULTATION, assigned_staff_id=me)
    db = make_db_returning(job)
    svc = FieldOpsService(db=db, actor_id=me, actor_role="staff")
    with pytest.raises(ServiceOSException) as exc:
        await svc.update_status(job.id, JS.WORK_STARTED, None, None, None)
    assert exc.value.error_code == "WORK_NOT_ALLOWED_FOR_CONSULTATION"

@pytest.mark.asyncio
async def test_consultation_quote_approved_allows_convert_to_repair():
    allowed = get_allowed_transitions(JobType.CONSULTATION, JS.QUOTE_APPROVED)
    assert JS.CONVERTED_TO_REPAIR in allowed

def test_consultation_quote_rejected_closes():
    allowed = get_allowed_transitions(JobType.CONSULTATION, JS.QUOTE_REJECTED)
    assert JS.CLOSED in allowed or JS.PENDING_SIGN_OFF in allowed


# ── 5. Consultation -> Repair conversion ────────────────────────────────────────

@pytest.mark.asyncio
async def test_convert_to_repair_creates_repair_job():
    tid = uuid.uuid4()
    job = make_job(tenant_id=tid, job_type=JobType.CONSULTATION, status=JS.QUOTE_APPROVED,
                    assessment_findings="Compressor failing", recommended_work="Replace compressor")
    db = make_db_returning(job, None)  # job lookup, then duplicate-child check
    svc = FieldOpsService(db=db, actor_id=uuid.uuid4(), actor_role="tenant_owner", actor_tenant_id=tid)
    svc._write_history = AsyncMock(); svc._publish = AsyncMock()

    result = await svc.convert_to_repair(job.id)
    assert result["repair_job_status"] == JS.PENDING_ASSIGNMENT
    assert result["parent_job_id"] == str(job.id)
    assert job.status == JS.CONVERTED_TO_REPAIR

    created_jobs = [c.args[0] for c in db.add.call_args_list if isinstance(c.args[0], Job)]
    assert len(created_jobs) == 1
    assert created_jobs[0].parent_job_id == job.id
    assert created_jobs[0].assessment_findings == "Compressor failing"
    assert created_jobs[0].recommended_work == "Replace compressor"
    assert created_jobs[0].job_type == JobType.REPAIR
    assert created_jobs[0].converted_from_consultation is True

@pytest.mark.asyncio
async def test_convert_to_repair_with_staff_sets_assigned():
    tid = uuid.uuid4()
    staff_id = uuid.uuid4()
    job = make_job(tenant_id=tid, job_type=JobType.CONSULTATION, status=JS.QUOTE_APPROVED)
    db = make_db_returning(job, None)
    svc = FieldOpsService(db=db, actor_id=uuid.uuid4(), actor_role="tenant_owner", actor_tenant_id=tid)
    svc._write_history = AsyncMock(); svc._publish = AsyncMock()

    result = await svc.convert_to_repair(job.id, assigned_staff_id=staff_id)
    assert result["repair_job_status"] == JS.ASSIGNED

@pytest.mark.asyncio
async def test_duplicate_conversion_blocked_by_status():
    tid = uuid.uuid4()
    job = make_job(tenant_id=tid, job_type=JobType.CONSULTATION, status=JS.CONVERTED_TO_REPAIR)
    db = make_db_returning(job)
    svc = FieldOpsService(db=db, actor_id=uuid.uuid4(), actor_role="tenant_owner", actor_tenant_id=tid)
    with pytest.raises(ServiceOSException) as exc:
        await svc.convert_to_repair(job.id)
    assert exc.value.error_code == "CONSULTATION_ALREADY_CONVERTED"

@pytest.mark.asyncio
async def test_duplicate_conversion_blocked_by_existing_child():
    tid = uuid.uuid4()
    job = make_job(tenant_id=tid, job_type=JobType.CONSULTATION, status=JS.QUOTE_APPROVED)
    existing_child = make_job(parent_job_id=job.id, job_type=JobType.REPAIR)
    db = make_db_returning(job, existing_child)
    svc = FieldOpsService(db=db, actor_id=uuid.uuid4(), actor_role="tenant_owner", actor_tenant_id=tid)
    with pytest.raises(ServiceOSException) as exc:
        await svc.convert_to_repair(job.id)
    assert exc.value.error_code == "CONSULTATION_ALREADY_CONVERTED"

@pytest.mark.asyncio
async def test_convert_to_repair_only_for_consultation():
    job = make_job(job_type=JobType.REPAIR, status=JS.QUOTE_APPROVED)
    db = make_db_returning(job)
    svc = FieldOpsService(db=db, actor_id=uuid.uuid4(), actor_role="tenant_owner",
                           actor_tenant_id=job.tenant_id)
    with pytest.raises(ServiceOSException) as exc:
        await svc.convert_to_repair(job.id)
    assert exc.value.error_code == "CONSULTATION_CONVERSION_NOT_ALLOWED"

@pytest.mark.asyncio
async def test_convert_to_repair_requires_quote_approved_status():
    job = make_job(job_type=JobType.CONSULTATION, status=JS.ASSESSMENT_COMPLETE)
    db = make_db_returning(job)
    svc = FieldOpsService(db=db, actor_id=uuid.uuid4(), actor_role="tenant_owner",
                           actor_tenant_id=job.tenant_id)
    with pytest.raises(ServiceOSException) as exc:
        await svc.convert_to_repair(job.id)
    assert exc.value.error_code == "CONSULTATION_CONVERSION_NOT_ALLOWED"

@pytest.mark.asyncio
async def test_cross_tenant_consultation_conversion_blocked():
    job = make_job(job_type=JobType.CONSULTATION, status=JS.QUOTE_APPROVED)
    db = make_db_returning(job)
    svc = FieldOpsService(db=db, actor_id=uuid.uuid4(), actor_role="tenant_owner",
                           actor_tenant_id=uuid.uuid4())  # different tenant
    with pytest.raises(ServiceOSException) as exc:
        await svc.convert_to_repair(job.id)
    assert exc.value.error_code == "JOB_NOT_FOUND"


# ── 6. Job Quotes (line-item) ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_job_quote_after_assessment_complete():
    me = uuid.uuid4()
    job = make_job(status=JS.ASSESSMENT_COMPLETE, job_type=JobType.REPAIR, assigned_staff_id=me,
                    recommended_work="Replace valve")
    db = make_db_returning(job)
    svc = FieldOpsService(db=db, actor_id=me, actor_role="staff")
    result = await svc.create_job_quote(job.id, {
        "recommended_work": "Replace valve and refill gas.",
        "labour_amount": 800, "parts_amount": 450, "visit_fee": 200,
    })
    assert result["total_amount"] == 1450.0
    assert result["status"] == "draft"

@pytest.mark.asyncio
async def test_quote_total_amount_calculation():
    me = uuid.uuid4()
    job = make_job(status=JS.ASSESSMENT_COMPLETE, job_type=JobType.REPAIR, assigned_staff_id=me,
                    recommended_work="x")
    db = make_db_returning(job)
    svc = FieldOpsService(db=db, actor_id=me, actor_role="staff")
    result = await svc.create_job_quote(job.id, {
        "recommended_work": "x", "labour_amount": 1000, "parts_amount": 500,
        "visit_fee": 100, "tax_amount": 50, "discount_amount": 100,
    })
    assert result["total_amount"] == 1550.0  # 1000+500+100+50-100

@pytest.mark.asyncio
async def test_negative_quote_amount_rejected():
    me = uuid.uuid4()
    job = make_job(status=JS.ASSESSMENT_COMPLETE, job_type=JobType.REPAIR, assigned_staff_id=me)
    db = make_db_returning(job)
    svc = FieldOpsService(db=db, actor_id=me, actor_role="staff")
    with pytest.raises(ServiceOSException) as exc:
        await svc.create_job_quote(job.id, {"recommended_work": "x", "labour_amount": -100})
    assert exc.value.error_code == "INVALID_QUOTE_AMOUNT"

@pytest.mark.asyncio
async def test_quote_requires_assessment_complete():
    me = uuid.uuid4()
    job = make_job(status=JS.ARRIVED, job_type=JobType.REPAIR, assigned_staff_id=me)
    db = make_db_returning(job)
    svc = FieldOpsService(db=db, actor_id=me, actor_role="staff")
    with pytest.raises(ServiceOSException) as exc:
        await svc.create_job_quote(job.id, {"recommended_work": "x"})
    assert exc.value.error_code == "ASSESSMENT_NOT_STARTED"

@pytest.mark.asyncio
async def test_customer_can_approve_own_quote():
    cid = uuid.uuid4()
    job = make_job(status=JS.QUOTE_SENT, job_type=JobType.REPAIR, customer_id=cid)
    quote = MagicMock(id=uuid.uuid4(), job_id=job.id, customer_id=cid, status="sent", expires_at=None,
                       total_amount=Decimal("1000"))
    db = make_db_returning(job, quote)
    svc = FieldOpsService(db=db, actor_id=cid, actor_role="customer")
    svc._write_history = AsyncMock(); svc._publish = AsyncMock()
    result = await svc.approve_job_quote(job.id, quote.id, cid)
    assert result["status"] == "approved"
    assert job.status == JS.QUOTE_APPROVED

@pytest.mark.asyncio
async def test_customer_can_reject_own_quote():
    cid = uuid.uuid4()
    job = make_job(status=JS.QUOTE_SENT, job_type=JobType.REPAIR, customer_id=cid)
    quote = MagicMock(id=uuid.uuid4(), job_id=job.id, customer_id=cid, status="sent", expires_at=None)
    db = make_db_returning(job, quote)
    svc = FieldOpsService(db=db, actor_id=cid, actor_role="customer")
    svc._write_history = AsyncMock(); svc._publish = AsyncMock()
    result = await svc.reject_job_quote(job.id, quote.id, cid, "too expensive")
    assert result["status"] == "rejected"
    assert job.status == JS.QUOTE_REJECTED

@pytest.mark.asyncio
async def test_customer_cannot_approve_another_customers_quote():
    cid = uuid.uuid4()
    other_cid = uuid.uuid4()
    job = make_job(status=JS.QUOTE_SENT, job_type=JobType.REPAIR, customer_id=cid)
    quote = MagicMock(id=uuid.uuid4(), job_id=job.id, customer_id=cid, status="sent", expires_at=None)
    db = make_db_returning(job, quote)
    svc = FieldOpsService(db=db, actor_id=other_cid, actor_role="customer")
    with pytest.raises(ServiceOSException) as exc:
        await svc.approve_job_quote(job.id, quote.id, other_cid)
    assert exc.value.error_code == "JOB_NOT_FOUND"

@pytest.mark.asyncio
async def test_expired_quote_cannot_be_approved():
    cid = uuid.uuid4()
    job = make_job(status=JS.QUOTE_SENT, job_type=JobType.REPAIR, customer_id=cid)
    quote = MagicMock(id=uuid.uuid4(), job_id=job.id, customer_id=cid, status="sent",
                       expires_at=utcnow() - timedelta(days=1))
    db = make_db_returning(job, quote)
    svc = FieldOpsService(db=db, actor_id=cid, actor_role="customer")
    with pytest.raises(ServiceOSException) as exc:
        await svc.approve_job_quote(job.id, quote.id, cid)
    assert exc.value.error_code == "QUOTE_EXPIRED"

@pytest.mark.asyncio
async def test_only_one_active_sent_quote_per_job():
    me = uuid.uuid4()
    job = make_job(status=JS.ASSESSMENT_COMPLETE, job_type=JobType.REPAIR, assigned_staff_id=me)
    quote = MagicMock(id=uuid.uuid4(), job_id=job.id, status="draft", quote_number="QT-1")
    existing_sent_result = MagicMock()
    existing_sent_result.scalars.return_value.all.return_value = [MagicMock()]
    db = make_db_returning(job, quote)
    db.execute = AsyncMock(side_effect=[
        MagicMock(scalar_one_or_none=MagicMock(return_value=job)),
        MagicMock(scalar_one_or_none=MagicMock(return_value=quote)),
        existing_sent_result,
    ])
    svc = FieldOpsService(db=db, actor_id=me, actor_role="staff")
    with pytest.raises(ServiceOSException) as exc:
        await svc.send_job_quote(job.id, quote.id)
    assert exc.value.error_code == "QUOTE_ALREADY_SENT"

@pytest.mark.asyncio
async def test_staff_cannot_create_quote_for_another_tenants_job():
    job = make_job(status=JS.ASSESSMENT_COMPLETE, job_type=JobType.REPAIR, assigned_staff_id=uuid.uuid4())
    db = make_db_returning(job)
    svc = FieldOpsService(db=db, actor_id=uuid.uuid4(), actor_role="staff")  # not assigned
    with pytest.raises(ServiceOSException) as exc:
        await svc.create_job_quote(job.id, {"recommended_work": "x"})
    assert exc.value.error_code == "STAFF_NOT_ASSIGNED_TO_JOB"

@pytest.mark.asyncio
async def test_tenant_owner_cannot_manage_another_tenants_quote():
    job = make_job(status=JS.ASSESSMENT_COMPLETE, job_type=JobType.REPAIR)
    db = make_db_returning(job)
    svc = FieldOpsService(db=db, actor_id=uuid.uuid4(), actor_role="tenant_owner",
                           actor_tenant_id=uuid.uuid4())
    with pytest.raises(ServiceOSException) as exc:
        await svc.create_job_quote(job.id, {"recommended_work": "x"})
    assert exc.value.error_code == "JOB_NOT_FOUND"


# ── 7. Security ──────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_staff_cannot_assess_unassigned_job():
    job = make_job(status=JS.ARRIVED, job_type=JobType.REPAIR, assigned_staff_id=uuid.uuid4())
    db = make_db_returning(job)
    svc = FieldOpsService(db=db, actor_id=uuid.uuid4(), actor_role="staff")
    with pytest.raises(ServiceOSException) as exc:
        await svc.start_assessment(job.id)
    assert exc.value.error_code == "STAFF_NOT_ASSIGNED_TO_JOB"

@pytest.mark.asyncio
async def test_assessment_not_allowed_for_service_job():
    me = uuid.uuid4()
    job = make_job(status=JS.ARRIVED, job_type=JobType.SERVICE, assigned_staff_id=me)
    db = make_db_returning(job)
    svc = FieldOpsService(db=db, actor_id=me, actor_role="staff")
    with pytest.raises(ServiceOSException) as exc:
        await svc.start_assessment(job.id)
    assert exc.value.error_code == "ASSESSMENT_NOT_ALLOWED_FOR_SERVICE"


# ── 8. valid-next-statuses is job-type-aware ─────────────────────────────────────

@pytest.mark.asyncio
async def test_valid_next_statuses_excludes_work_started_when_quote_required():
    me = uuid.uuid4()
    job = make_job(status=JS.ASSESSMENT_COMPLETE, job_type=JobType.REPAIR,
                    assigned_staff_id=me, quote_required=True)
    db = make_db_returning(job)
    svc = FieldOpsService(db=db, actor_id=me, actor_role="staff")
    result = await svc.get_valid_next_statuses(job.id)
    assert result["job_type"] == JobType.REPAIR
    assert JS.WORK_STARTED not in result["valid_next_statuses"]
    assert JS.QUOTE_SENT in result["valid_next_statuses"]

@pytest.mark.asyncio
async def test_valid_next_statuses_service_after_arrived():
    me = uuid.uuid4()
    job = make_job(status=JS.ARRIVED, job_type=JobType.SERVICE, assigned_staff_id=me)
    db = make_db_returning(job)
    svc = FieldOpsService(db=db, actor_id=me, actor_role="staff")
    result = await svc.get_valid_next_statuses(job.id)
    assert JS.WORK_STARTED in result["valid_next_statuses"]

@pytest.mark.asyncio
async def test_valid_next_statuses_consultation_after_quote_approved():
    me = uuid.uuid4()
    job = make_job(status=JS.QUOTE_APPROVED, job_type=JobType.CONSULTATION, assigned_staff_id=me)
    db = make_db_returning(job)
    svc = FieldOpsService(db=db, actor_id=me, actor_role="staff")
    result = await svc.get_valid_next_statuses(job.id)
    assert JS.CONVERTED_TO_REPAIR in result["valid_next_statuses"]


# ── 9. OpenAPI ────────────────────────────────────────────────────────────────────

def test_openapi_includes_assessment_endpoints():
    from app.main import app
    schema = app.openapi()
    assert "/v1/jobs/{job_id}/assessment/start" in schema["paths"]
    assert "/v1/jobs/{job_id}/assessment/complete" in schema["paths"]

def test_openapi_includes_quote_endpoints():
    from app.main import app
    schema = app.openapi()
    assert "/v1/jobs/{job_id}/quotes" in schema["paths"]
    assert "/v1/jobs/{job_id}/quotes/{quote_id}/send" in schema["paths"]
    assert "/v1/jobs/{job_id}/quotes/{quote_id}/approve" in schema["paths"]
    assert "/v1/jobs/{job_id}/quotes/{quote_id}/reject" in schema["paths"]

def test_openapi_includes_convert_to_repair_endpoint():
    from app.main import app
    schema = app.openapi()
    assert "/v1/jobs/{job_id}/convert-to-repair" in schema["paths"]

def test_openapi_includes_checklist_endpoints():
    from app.main import app
    schema = app.openapi()
    assert "/v1/jobs/{job_id}/checklist" in schema["paths"]
    assert "/v1/jobs/{job_id}/checklist/start" in schema["paths"]
    assert "/v1/jobs/{job_id}/checklist/complete" in schema["paths"]

def test_openapi_schema_is_valid():
    from app.main import app
    schema = app.openapi()
    assert schema["openapi"]
    assert "paths" in schema and "components" in schema


# ── 10. Model fields ──────────────────────────────────────────────────────────────

@pytest.mark.parametrize("field", [
    "quote_required", "quote_id", "pre_approval_limit", "assessment_findings",
    "recommended_work", "estimated_parts", "assessment_completed_at", "quote_sent_at",
    "quote_approved_at", "quote_rejected_at", "quote_rejection_reason", "checklist_required",
    "checklist_started_at", "checklist_completed_at", "converted_from_consultation",
])
def test_job_model_has_step7_field(field):
    assert hasattr(Job, field)

@pytest.mark.parametrize("field", [
    "quote_number", "quote_type", "recommended_work", "labour_amount", "parts_amount",
    "visit_fee", "discount_amount", "tax_amount", "total_amount", "pre_approval_limit",
    "requires_customer_approval", "sent_at", "approved_at", "rejected_at", "rejection_reason",
    "created_by_staff_id", "approved_by_customer_id",
])
def test_job_quote_model_has_step7_field(field):
    assert hasattr(JobQuote, field)
