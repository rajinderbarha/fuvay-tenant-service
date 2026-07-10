"""Step 8 manual smoke flows — quote approve/reject + checklist template ->
job execution, end to end at the service layer (no real DB in this sandbox)."""
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.engines.field_ops.constants import JS, JobType
from app.engines.field_ops.service import FieldOpsService
from app.engines.field_ops.checklist_template_service import ChecklistTemplateService

utcnow = lambda: datetime.now(timezone.utc)


def make_job(**overrides):
    defaults = dict(
        id=uuid.uuid4(), tenant_id=uuid.uuid4(), customer_id=uuid.uuid4(),
        assigned_staff_id=None, status=JS.ARRIVED, job_type=JobType.REPAIR,
        title="Job", description=None, service_type_id="svc", service_category="cat",
        booking_id=None, address={}, pincode=None, city="Mumbai", zipcode="400001",
        address_id=None, service_id=uuid.uuid4(), matched_service_area_id=None,
        matched_service_area_service_id=None, coverage_match_level=None,
        scheduled_at=None, parent_job_id=None, findings=None, recommendation=None,
        checklist=[], assessment_findings=None, recommended_work=None, estimated_parts=[],
        assessment_completed_at=None, quote_required=False, quote_id=None,
        pre_approval_limit=None, quote_sent_at=None, quote_approved_at=None,
        quote_rejected_at=None, quote_rejection_reason=None, checklist_required=False,
        checklist_started_at=None, checklist_completed_at=None, converted_from_consultation=False,
        sla_minutes=None, current_status_started_at=None, started_at=None, completed_at=None,
        updated_at=utcnow(), created_at=utcnow(),
    )
    defaults.update(overrides)
    return MagicMock(**defaults)


def db_for(job):
    result = MagicMock(); result.scalar_one_or_none.return_value = job
    db = MagicMock()
    db.execute = AsyncMock(return_value=result)
    db.add = MagicMock(); db.flush = AsyncMock()
    return db


@pytest.mark.asyncio
async def test_quote_approve_smoke_flow():
    me = uuid.uuid4()
    job = make_job(job_type=JobType.REPAIR, status=JS.ARRIVED, assigned_staff_id=me)
    db = db_for(job)
    svc = FieldOpsService(db=db, actor_id=me, actor_role="staff")
    svc._write_history = AsyncMock(); svc._publish = AsyncMock()

    await svc.start_assessment(job.id)
    await svc.complete_assessment(job.id, "Gas leak", "Replace valve")
    assert job.status == JS.ASSESSMENT_COMPLETE

    quote = MagicMock(id=uuid.uuid4(), job_id=job.id, status="draft", quote_number="QT-1",
                       expires_at=None, total_amount=Decimal("1450"), customer_id=job.customer_id,
                       findings_snapshot="Gas leak", recommended_work="Replace valve")
    no_sent = MagicMock(); no_sent.scalars.return_value.all.return_value = []
    db.execute = AsyncMock(side_effect=[
        MagicMock(scalar_one_or_none=MagicMock(return_value=job)),
        MagicMock(scalar_one_or_none=MagicMock(return_value=quote)), no_sent,
    ])
    await svc.send_job_quote(job.id, quote.id)
    assert job.status == JS.QUOTE_SENT

    # Customer opens quote detail.
    cust = job.customer_id
    customer_svc = FieldOpsService(db=db, actor_id=cust, actor_role="customer")
    db.execute = AsyncMock(side_effect=[
        MagicMock(scalar_one_or_none=MagicMock(return_value=quote)),
        MagicMock(scalar_one_or_none=MagicMock(return_value=job)),
        MagicMock(scalar_one_or_none=MagicMock(return_value=None)),  # tenant lookup (best-effort)
        MagicMock(scalar_one_or_none=MagicMock(return_value=None)),  # staff lookup
    ])
    detail = await customer_svc.get_customer_quote_detail(cust, quote.id)
    assert detail["assessment"]["findings"] == "Gas leak"
    assert detail["price_breakdown"]["total_amount"] == 1450.0
    assert detail["can_approve"] is True

    # Customer approves.
    db.execute = AsyncMock(side_effect=[
        MagicMock(scalar_one_or_none=MagicMock(return_value=quote)),
        MagicMock(scalar_one_or_none=MagicMock(return_value=job)),
        MagicMock(scalar_one_or_none=MagicMock(return_value=quote)),
        MagicMock(scalar_one_or_none=MagicMock(return_value=job)),
    ])
    result = await customer_svc.approve_customer_quote(quote.id, cust)
    assert result["job_status"] == JS.QUOTE_APPROVED
    assert quote.status == "approved"

    # Staff can now start work.
    db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=job)))
    await svc.update_status(job.id, JS.WORK_STARTED, None, None, None)
    assert job.status == JS.WORK_STARTED


@pytest.mark.asyncio
async def test_quote_reject_smoke_flow():
    me = uuid.uuid4()
    job = make_job(job_type=JobType.REPAIR, status=JS.QUOTE_SENT, assigned_staff_id=me)
    quote = MagicMock(id=uuid.uuid4(), job_id=job.id, status="sent", quote_number="QT-2",
                       expires_at=None, customer_id=job.customer_id)
    db = MagicMock()
    db.add = MagicMock(); db.flush = AsyncMock()
    svc = FieldOpsService(db=db, actor_id=job.customer_id, actor_role="customer")
    svc._write_history = AsyncMock(); svc._publish = AsyncMock()

    db.execute = AsyncMock(side_effect=[
        MagicMock(scalar_one_or_none=MagicMock(return_value=quote)),
        MagicMock(scalar_one_or_none=MagicMock(return_value=job)),
        MagicMock(scalar_one_or_none=MagicMock(return_value=quote)),
        MagicMock(scalar_one_or_none=MagicMock(return_value=job)),
    ])
    result = await svc.reject_customer_quote(quote.id, job.customer_id, "Too expensive")
    assert result["job_status"] == JS.QUOTE_REJECTED
    assert quote.status == "rejected"

    # work_started must remain blocked.
    db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=job)))
    staff_svc = FieldOpsService(db=db, actor_id=me, actor_role="staff")
    with pytest.raises(Exception):
        await staff_svc.update_status(job.id, JS.WORK_STARTED, None, None, None)


@pytest.mark.asyncio
async def test_checklist_smoke_flow_template_to_completion():
    tid = uuid.uuid4()
    sid = uuid.uuid4()
    template = MagicMock(id=uuid.uuid4(), tenant_id=tid, service_id=sid, name="AC Annual Service",
                          is_active=True, deleted_at=None)
    no_dup = MagicMock(); no_dup.scalar_one_or_none.return_value = None
    tmpl_db = MagicMock()
    tmpl_db.execute = AsyncMock(return_value=no_dup)
    tmpl_db.add = MagicMock(side_effect=lambda o: setattr(o, "id", uuid.uuid4()))
    tmpl_db.flush = AsyncMock()
    tmpl_svc = ChecklistTemplateService(db=tmpl_db, actor_id=uuid.uuid4(), actor_role="tenant_owner",
                                         actor_tenant_id=tid)
    created_template = await tmpl_svc.create_template(tid, {"service_id": str(sid), "name": "AC Annual Service"})
    assert created_template["name"] == "AC Annual Service"

    # Tenant adds a required item.
    tmpl_db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=template)))
    await tmpl_svc.add_item(template.id, {"title": "Clean filter", "is_required": True})

    # Staff starts checklist on a service job — lazily provisions from template.
    me = uuid.uuid4()
    job = make_job(job_type=JobType.SERVICE, status=JS.WORK_STARTED, assigned_staff_id=me,
                    tenant_id=tid, service_id=sid, checklist_required=False)
    job_db = db_for(job)
    svc = FieldOpsService(db=job_db, actor_id=me, actor_role="staff")
    svc._write_history = AsyncMock(); svc._publish = AsyncMock()

    template_item = MagicMock(id=uuid.uuid4(), title="Clean filter", description=None, sort_order=1,
                               is_required=True, requires_photo=False, requires_note=False)
    no_existing_items = MagicMock(); no_existing_items.scalars.return_value.first.return_value = None
    created_job_items = []
    job_db.add = MagicMock(side_effect=lambda o: created_job_items.append(o))
    job_db.execute = AsyncMock(side_effect=[
        MagicMock(scalar_one_or_none=MagicMock(return_value=job)),  # _get_job_for_staff_action
        no_existing_items,                                          # check for existing job_checklist_items
        MagicMock(scalar_one_or_none=MagicMock(return_value=template)),  # find active template
        MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[template_item])))),
        MagicMock(scalar_one_or_none=MagicMock(return_value=job)),  # get_job_checklist_items: job lookup
        MagicMock(scalars=MagicMock(return_value=MagicMock(
            all=MagicMock(side_effect=lambda: list(created_job_items))))),  # items lookup
    ])
    started = await svc.start_job_checklist(job.id)
    assert started["job_id"] == str(job.id)
    assert job.status == JS.CHECKLIST_STARTED
    assert job.checklist_required is True

    # Staff completes the (one) required item.
    job_item = MagicMock(id=uuid.uuid4(), job_id=job.id, is_required=True, requires_note=False,
                          requires_photo=False, is_completed=False, completed_by_staff_id=None,
                          completed_at=None, notes=None, photo_urls=[])
    job_db.execute = AsyncMock(side_effect=[
        MagicMock(scalar_one_or_none=MagicMock(return_value=job)),
        MagicMock(scalar_one_or_none=MagicMock(return_value=job_item)),
    ])
    await svc.update_job_checklist_item(job.id, job_item.id, True, "Cleaned", [])
    assert job_item.is_completed is True

    # Complete checklist.
    items_result = MagicMock(); items_result.scalars.return_value.all.return_value = [job_item]
    items_result2 = MagicMock(); items_result2.scalars.return_value.all.return_value = [job_item]
    job_db.execute = AsyncMock(side_effect=[
        MagicMock(scalar_one_or_none=MagicMock(return_value=job)), items_result,
        MagicMock(scalar_one_or_none=MagicMock(return_value=job)), items_result2,
    ])
    await svc.complete_job_checklist(job.id)
    assert job.status == JS.CHECKLIST_COMPLETE

    # work_complete now allowed.
    job_db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=job)))
    await svc.update_status(job.id, JS.WORK_COMPLETE, None, None, None)
    assert job.status == JS.WORK_COMPLETE
