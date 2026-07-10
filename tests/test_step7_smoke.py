"""Step 7 manual smoke flows — repair / service / consultation, end to end at
the service layer (no real DB in this sandbox; conftest mocks all DB calls).
A single mutable job MagicMock flows through every call, exactly like a real
row would across requests, proving the full chain of business-rule gates."""
import uuid
from decimal import Decimal
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.engines.field_ops.constants import JS, JobType
from app.engines.field_ops.service import FieldOpsService


def make_job(**overrides):
    defaults = dict(
        id=uuid.uuid4(), tenant_id=uuid.uuid4(), customer_id=uuid.uuid4(),
        assigned_staff_id=None, status=JS.PENDING_ASSIGNMENT, job_type=JobType.REPAIR,
        title="Job", description=None, service_type_id="svc", service_category="cat",
        address={}, pincode=None, city="Mumbai", zipcode="400001",
        address_id=None, service_id=None, matched_service_area_id=None,
        matched_service_area_service_id=None, coverage_match_level=None,
        scheduled_at=None, parent_job_id=None, findings=None, recommendation=None,
        checklist=[], assessment_findings=None, recommended_work=None, estimated_parts=[],
        assessment_completed_at=None, quote_required=False, quote_id=None,
        pre_approval_limit=None, quote_sent_at=None, quote_approved_at=None,
        quote_rejected_at=None, quote_rejection_reason=None, checklist_required=False,
        checklist_started_at=None, checklist_completed_at=None, converted_from_consultation=False,
        sla_minutes=None, current_status_started_at=None, started_at=None, completed_at=None,
    )
    defaults.update(overrides)
    from datetime import datetime, timezone
    defaults.setdefault("updated_at", datetime.now(timezone.utc))
    defaults.setdefault("created_at", datetime.now(timezone.utc))
    return MagicMock(**defaults)


def db_for(job):
    result = MagicMock(); result.scalar_one_or_none.return_value = job
    db = MagicMock()
    db.execute = AsyncMock(return_value=result)
    db.add = MagicMock(); db.flush = AsyncMock()
    return db


@pytest.mark.asyncio
async def test_repair_smoke_flow():
    me = uuid.uuid4()
    job = make_job(job_type=JobType.REPAIR, status=JS.ARRIVED, assigned_staff_id=me)
    db = db_for(job)
    svc = FieldOpsService(db=db, actor_id=me, actor_role="staff")
    svc._write_history = AsyncMock(); svc._publish = AsyncMock()

    await svc.start_assessment(job.id)
    assert job.status == JS.ASSESSMENT_STARTED

    await svc.complete_assessment(job.id, "Gas leak", "Replace valve", quote_required=True)
    assert job.status == JS.ASSESSMENT_COMPLETE
    assert job.quote_required is True

    # Quote required — work_started must be blocked until approved.
    with pytest.raises(Exception):
        await svc.update_status(job.id, JS.WORK_STARTED, None, None, None)

    quote = MagicMock(id=uuid.uuid4(), job_id=job.id, status="draft", quote_number="QT-1",
                       expires_at=None, total_amount=Decimal("1250"), customer_id=job.customer_id)
    qdb_result = MagicMock(); qdb_result.scalar_one_or_none.return_value = quote
    no_sent = MagicMock(); no_sent.scalars.return_value.all.return_value = []
    db.execute = AsyncMock(side_effect=[
        MagicMock(scalar_one_or_none=MagicMock(return_value=job)),
        qdb_result, no_sent,
    ])
    await svc.send_job_quote(job.id, quote.id)
    assert job.status == JS.QUOTE_SENT

    cust = job.customer_id
    db.execute = AsyncMock(side_effect=[
        MagicMock(scalar_one_or_none=MagicMock(return_value=job)),
        MagicMock(scalar_one_or_none=MagicMock(return_value=quote)),
    ])
    await svc.approve_job_quote(job.id, quote.id, cust)
    assert job.status == JS.QUOTE_APPROVED

    db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=job)))
    await svc.update_status(job.id, JS.WORK_STARTED, None, None, None)
    assert job.status == JS.WORK_STARTED
    await svc.update_status(job.id, JS.WORK_COMPLETE, None, None, None)
    assert job.status == JS.WORK_COMPLETE
    await svc.update_status(job.id, JS.QUALITY_CHECK, None, None, None)
    await svc.update_status(job.id, JS.QUALITY_PASSED, None, None, None)
    await svc.update_status(job.id, JS.PENDING_SIGN_OFF, None, None, None)
    await svc.update_status(job.id, JS.SIGNED_OFF, None, None, None)
    await svc.update_status(job.id, JS.COMPLETED, None, None, None)
    assert job.status == JS.COMPLETED


@pytest.mark.asyncio
async def test_service_smoke_flow():
    me = uuid.uuid4()
    job = make_job(job_type=JobType.SERVICE, status=JS.ARRIVED, assigned_staff_id=me,
                    checklist_required=True, checklist=[{"step": "Clean filter", "completed": False}])
    db = db_for(job)
    svc = FieldOpsService(db=db, actor_id=me, actor_role="staff")
    svc._write_history = AsyncMock(); svc._publish = AsyncMock()

    await svc.update_status(job.id, JS.WORK_STARTED, None, None, None)
    assert job.status == JS.WORK_STARTED

    await svc.start_checklist(job.id)
    assert job.status == JS.CHECKLIST_STARTED

    with pytest.raises(Exception):
        await svc.complete_checklist(job.id)  # item still incomplete

    job.checklist = [{"step": "Clean filter", "completed": True}]
    await svc.complete_checklist(job.id)
    assert job.status == JS.CHECKLIST_COMPLETE

    await svc.update_status(job.id, JS.WORK_COMPLETE, None, None, None)
    assert job.status == JS.WORK_COMPLETE
    await svc.update_status(job.id, JS.QUALITY_CHECK, None, None, None)
    await svc.update_status(job.id, JS.QUALITY_PASSED, None, None, None)
    await svc.update_status(job.id, JS.PENDING_SIGN_OFF, None, None, None)
    await svc.update_status(job.id, JS.SIGNED_OFF, None, None, None)
    await svc.update_status(job.id, JS.COMPLETED, None, None, None)
    assert job.status == JS.COMPLETED


@pytest.mark.asyncio
async def test_consultation_smoke_flow_with_conversion():
    me = uuid.uuid4()
    tid = uuid.uuid4()
    job = make_job(job_type=JobType.CONSULTATION, status=JS.ARRIVED, assigned_staff_id=me, tenant_id=tid)
    db = db_for(job)
    svc = FieldOpsService(db=db, actor_id=me, actor_role="staff")
    svc._write_history = AsyncMock(); svc._publish = AsyncMock()

    await svc.start_assessment(job.id)
    assert job.status == JS.ASSESSMENT_STARTED

    await svc.complete_assessment(job.id, "Compressor failing", "Full replacement needed")
    assert job.status == JS.ASSESSMENT_COMPLETE

    quote = MagicMock(id=uuid.uuid4(), job_id=job.id, status="draft", quote_number="QT-2",
                       expires_at=None, total_amount=Decimal("3000"), customer_id=job.customer_id)
    no_sent = MagicMock(); no_sent.scalars.return_value.all.return_value = []
    db.execute = AsyncMock(side_effect=[
        MagicMock(scalar_one_or_none=MagicMock(return_value=job)),
        MagicMock(scalar_one_or_none=MagicMock(return_value=quote)), no_sent,
    ])
    await svc.send_job_quote(job.id, quote.id)
    assert job.status == JS.QUOTE_SENT

    cust = job.customer_id
    db.execute = AsyncMock(side_effect=[
        MagicMock(scalar_one_or_none=MagicMock(return_value=job)),
        MagicMock(scalar_one_or_none=MagicMock(return_value=quote)),
    ])
    await svc.approve_job_quote(job.id, quote.id, cust)
    assert job.status == JS.QUOTE_APPROVED

    # Tenant owner converts approved consultation to a repair job.
    tenant_svc = FieldOpsService(db=db, actor_id=uuid.uuid4(), actor_role="tenant_owner", actor_tenant_id=tid)
    tenant_svc._write_history = AsyncMock(); tenant_svc._publish = AsyncMock()
    db.execute = AsyncMock(side_effect=[
        MagicMock(scalar_one_or_none=MagicMock(return_value=job)),   # job lookup + tenant isolation
        MagicMock(scalar_one_or_none=MagicMock(return_value=None)),  # no existing child repair
    ])
    result = await tenant_svc.convert_to_repair(job.id)
    assert job.status == JS.CONVERTED_TO_REPAIR
    assert result["repair_job_status"] == JS.PENDING_ASSIGNMENT
    assert result["parent_job_id"] == str(job.id)
