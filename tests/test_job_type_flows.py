"""
Phase 7 — Universal Service Phase Logic. None of this existed before:
no job_type concept, no way to skip assessment for service jobs, no quote
model, no checklist, no consultation type, no follow-up-job spawning.

These tests exercise the three flows end-to-end at the service layer
(mocked DB) to prove the branching state machine and side effects are wired
correctly, not just that the code compiles.
"""
import uuid
from decimal import Decimal
from datetime import datetime, timezone
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.exceptions import ServiceOSException, NotFoundException
from app.engines.field_ops.constants import JS, JobType, get_allowed_transitions


def make_job(status, job_type=JobType.REPAIR, **kw):
    defaults = dict(
        id=uuid.uuid4(), tenant_id=uuid.uuid4(), status=status, job_type=job_type,
        assigned_staff_id=None, customer_id=uuid.uuid4(), job_number="JOB-1",
        title="AC issue", service_type_id="ac_repair", service_category="general",
        checklist=[], findings=None, recommendation=None, parent_job_id=None,
        address={}, pincode=None, quoted_price=None, final_price=None,
        started_at=None, completed_at=None, customer_rating=None, tags=[],
        commission_deducted=False, commission_amount=None, sla_breach=False,
        created_at=datetime.now(timezone.utc), customer_token="tok",
        duration_estimate_minutes=None,
    )
    defaults.update(kw)
    return MagicMock(**defaults)


def svc_with_job(job, actor_role="staff", actor_id=None):
    from app.engines.field_ops.service import FieldOpsService
    result = MagicMock()
    result.scalar_one_or_none.return_value = job
    db = MagicMock()
    db.execute = AsyncMock(return_value=result)
    db.flush = AsyncMock()
    # Mimic the ORM's Python-side default for created_at on any real model
    # instance passed to db.add() — a real flush would populate this.
    def fake_add(obj):
        if getattr(obj, "created_at", None) is None:
            obj.created_at = datetime.now(timezone.utc)
    db.add = MagicMock(side_effect=fake_add)
    s = FieldOpsService(db=db, actor_id=actor_id or job.assigned_staff_id, actor_role=actor_role)
    s._write_history = AsyncMock()
    s._publish = AsyncMock()
    return s, db


# ── Transition graph branching ──────────────────────────────────────────────

def test_service_job_can_skip_assessment_straight_to_work():
    assert JS.WORK_STARTED in get_allowed_transitions(JobType.SERVICE, JS.ARRIVED)
    assert JS.ASSESSMENT_STARTED not in get_allowed_transitions(JobType.SERVICE, JS.ARRIVED)


def test_repair_job_must_go_through_assessment():
    allowed = get_allowed_transitions(JobType.REPAIR, JS.ARRIVED)
    assert allowed == [JS.ASSESSMENT_STARTED]


def test_consultation_never_reaches_work_started():
    allowed = get_allowed_transitions(JobType.CONSULTATION, JS.ASSESSMENT_COMPLETE)
    assert JS.WORK_STARTED not in allowed
    assert JS.QUOTE_PENDING in allowed


def test_consultation_quote_approval_goes_straight_to_signoff_not_work():
    allowed = get_allowed_transitions(JobType.CONSULTATION, JS.QUOTE_APPROVED)
    # Step 7: dedicated convert-to-repair path added alongside the legacy
    # sign-off/invoice/close path that still bills the consult fee.
    assert JS.PENDING_SIGN_OFF in allowed
    assert JS.WORK_STARTED not in allowed


def test_repair_quote_approval_continues_to_work():
    allowed = get_allowed_transitions(JobType.REPAIR, JS.QUOTE_APPROVED)
    assert JS.WORK_STARTED in allowed and JS.PARTS_REQUIRED in allowed


# ── Service: checklist mandatory before work_complete ───────────────────────

@pytest.mark.asyncio
async def test_service_job_blocks_work_complete_with_incomplete_checklist():
    job = make_job(JS.WORK_STARTED, job_type=JobType.SERVICE,
                    checklist=[{"step": "Clean filter", "completed": True},
                               {"step": "Check refrigerant", "completed": False}])
    svc, _ = svc_with_job(job, actor_role="staff", actor_id=job.assigned_staff_id)

    with pytest.raises(ServiceOSException) as exc:
        await svc.update_status(job.id, JS.WORK_COMPLETE, None, None, None)
    assert exc.value.error_code == "CHECKLIST_INCOMPLETE"


@pytest.mark.asyncio
async def test_service_job_allows_work_complete_when_checklist_done():
    job = make_job(JS.WORK_STARTED, job_type=JobType.SERVICE,
                    checklist=[{"step": "Clean filter", "completed": True}])
    svc, _ = svc_with_job(job, actor_role="staff", actor_id=job.assigned_staff_id)

    result = await svc.update_status(job.id, JS.WORK_COMPLETE, None, None, None)
    assert result["status"] == JS.WORK_COMPLETE


# ── Findings ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_submit_findings_advances_assessment_started_to_complete():
    job = make_job(JS.ASSESSMENT_STARTED, job_type=JobType.CONSULTATION)
    svc, _ = svc_with_job(job, actor_role="staff", actor_id=job.assigned_staff_id)

    result = await svc.submit_findings(job.id, "Compressor failing", "Needs replacement")
    assert job.findings == "Compressor failing"
    assert job.recommendation == "Needs replacement"
    assert result["status"] == JS.ASSESSMENT_COMPLETE


@pytest.mark.asyncio
async def test_submit_findings_rejected_outside_assessment():
    job = make_job(JS.WORK_STARTED, job_type=JobType.REPAIR)
    svc, _ = svc_with_job(job, actor_role="staff", actor_id=job.assigned_staff_id)

    with pytest.raises(ServiceOSException):
        await svc.submit_findings(job.id, "too late", None)


# ── Quotes ───────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_quote_transitions_job_to_quote_pending():
    job = make_job(JS.ASSESSMENT_COMPLETE, job_type=JobType.REPAIR)
    svc, db = svc_with_job(job, actor_role="tenant_owner")

    result = await svc.create_quote(job.id, Decimal("2500"),
                                     [{"item": "compressor", "cost": 2500}], None, "Urgent")
    assert job.status == JS.QUOTE_PENDING
    assert result["amount"] == 2500.0
    assert db.add.called


@pytest.mark.asyncio
async def test_create_quote_rejected_from_invalid_status():
    job = make_job(JS.WORK_STARTED, job_type=JobType.REPAIR)
    svc, _ = svc_with_job(job, actor_role="tenant_owner")

    with pytest.raises(ServiceOSException):
        await svc.create_quote(job.id, Decimal("100"), [], None, None)


@pytest.mark.asyncio
async def test_customer_cannot_respond_to_another_customers_quote():
    from app.engines.field_ops.service import FieldOpsService
    quote = MagicMock(id=uuid.uuid4(), job_id=uuid.uuid4(), customer_id=uuid.uuid4(), status="pending", expires_at=None)
    quote_result = MagicMock()
    quote_result.scalar_one_or_none.return_value = quote
    db = MagicMock()
    db.execute = AsyncMock(return_value=quote_result)

    svc = FieldOpsService(db=db, actor_id=uuid.uuid4(), actor_role="customer")
    with pytest.raises(NotFoundException):
        await svc.respond_to_quote(quote.id, uuid.uuid4(), True)  # different customer_id


@pytest.mark.asyncio
async def test_repair_quote_rejection_cancels_job_no_spawn():
    job = make_job(JS.QUOTE_PENDING, job_type=JobType.REPAIR)
    customer_id = job.customer_id
    quote = MagicMock(id=uuid.uuid4(), job_id=job.id, customer_id=customer_id, status="pending", expires_at=None)

    quote_result = MagicMock()
    quote_result.scalar_one_or_none.return_value = quote
    job_result = MagicMock()
    job_result.scalar_one_or_none.return_value = job
    db = MagicMock()
    db.execute = AsyncMock(side_effect=[quote_result, job_result])

    from app.engines.field_ops.service import FieldOpsService
    svc = FieldOpsService(db=db, actor_id=customer_id, actor_role="customer")
    svc._write_history = AsyncMock()
    svc._publish = AsyncMock()

    result = await svc.respond_to_quote(quote.id, customer_id, False)
    assert quote.status == "rejected"
    assert job.status == JS.QUOTE_REJECTED
    assert "spawned_job" not in result


# ── Consultation → Repair spawning ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_consultation_quote_approval_spawns_repair_job_with_inherited_data():
    job = make_job(JS.QUOTE_PENDING, job_type=JobType.CONSULTATION,
                    findings="Leaking compressor", recommendation="Full replacement needed")
    customer_id = job.customer_id
    quote = MagicMock(id=uuid.uuid4(), job_id=job.id, customer_id=customer_id,
                       status="pending", amount=Decimal("3000"), expires_at=None)

    quote_result = MagicMock()
    quote_result.scalar_one_or_none.return_value = quote
    job_result = MagicMock()
    job_result.scalar_one_or_none.return_value = job
    db = MagicMock()
    db.execute = AsyncMock(side_effect=[quote_result, job_result])
    db.flush = AsyncMock()
    # Mimic the ORM's Python-side default for created_at, which a real flush
    # would populate — the mocked session never does.
    def fake_add(obj):
        if getattr(obj, "created_at", None) is None:
            obj.created_at = datetime.now(timezone.utc)
    db.add = MagicMock(side_effect=fake_add)

    from app.engines.field_ops.service import FieldOpsService
    svc = FieldOpsService(db=db, actor_id=customer_id, actor_role="customer")
    svc._write_history = AsyncMock()
    svc._publish = AsyncMock()
    svc.create_job = AsyncMock(return_value={
        "job_id": str(uuid.uuid4()),
        "job_type": JobType.REPAIR,
        "parent_job_id": str(job.id),
        "findings": job.findings,
        "recommendation": job.recommendation,
        "quoted_price": float(quote.amount),
    })

    result = await svc.respond_to_quote(quote.id, customer_id, True)

    assert quote.status == "approved"
    assert job.status == JS.QUOTE_APPROVED
    # From here, a normal update_status call can advance straight to sign-off —
    # no WORK_STARTED/QUALITY_CHECK detour for consultation. Step 7 also adds a
    # dedicated convert-to-repair path alongside this legacy one.
    allowed_next = get_allowed_transitions(JobType.CONSULTATION, JS.QUOTE_APPROVED)
    assert JS.PENDING_SIGN_OFF in allowed_next
    assert JS.WORK_STARTED not in allowed_next
    assert "spawned_job" in result
    spawned = result["spawned_job"]
    assert spawned["job_type"] == JobType.REPAIR
    assert spawned["parent_job_id"] == str(job.id)
    assert spawned["findings"] == "Leaking compressor"
    assert spawned["recommendation"] == "Full replacement needed"
    assert spawned["quoted_price"] == 3000.0
    create_tenant_id, create_data = svc.create_job.await_args.args
    assert create_tenant_id == job.tenant_id
    assert create_data["customer_id"] == str(job.customer_id)
    assert create_data["service_type_id"] == job.service_type_id
    assert create_data["address"] == job.address
