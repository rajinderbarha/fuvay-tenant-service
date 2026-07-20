"""
Step 8 — Customer Quote Approval + Service Checklist UI/API.

Part A: customer-facing quote list/detail/approve/reject hardened on top of
the Step 7 line-item JobQuote.
Part B: normalized service checklist — tenant-owned templates
(ServiceChecklistTemplate/Item) executed per job (JobChecklistItem), replacing
the Step 7 JSONB placeholder for the canonical /v1/jobs/{id}/checklist routes.
"""
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.exceptions import ServiceOSException, NotFoundException
from app.engines.field_ops.constants import JS, JobType
from app.engines.field_ops.service import FieldOpsService
from app.engines.field_ops.models import (
    Job, JobQuote, ServiceChecklistTemplate, ServiceChecklistItem, JobChecklistItem,
)
from app.engines.field_ops.checklist_template_service import ChecklistTemplateService
from app.schemas.base import ERROR_CODES

utcnow = lambda: datetime.now(timezone.utc)


def db_seq(*objs):
    results = []
    for o in objs:
        r = MagicMock(); r.scalar_one_or_none.return_value = o
        results.append(r)
    db = MagicMock()
    db.execute = AsyncMock(side_effect=results if len(results) > 1 else None,
                            return_value=results[0] if len(results) == 1 else None)
    db.add = MagicMock(); db.flush = AsyncMock()
    return db


def make_job(**overrides):
    defaults = dict(
        id=uuid.uuid4(), tenant_id=uuid.uuid4(), customer_id=uuid.uuid4(),
        assigned_staff_id=None, status=JS.ARRIVED, job_type=JobType.REPAIR,
        title="AC Repair", description=None, service_type_id="ac_repair",
        service_category="ac", booking_id=None,
        address={}, pincode=None, city="Mumbai", zipcode="400001",
        address_id=None, service_id=uuid.uuid4(), matched_service_area_id=None,
        matched_service_area_service_id=None, coverage_match_level=None,
        scheduled_at=None, parent_job_id=None, findings=None, recommendation=None,
        checklist=[], assessment_findings="Gas leak", recommended_work="Replace valve",
        estimated_parts=[], assessment_completed_at=None,
        quote_required=False, quote_id=None, pre_approval_limit=None,
        quote_sent_at=None, quote_approved_at=None, quote_rejected_at=None,
        quote_rejection_reason=None, checklist_required=False,
        checklist_started_at=None, checklist_completed_at=None, converted_from_consultation=False,
        sla_minutes=None, current_status_started_at=None, updated_at=utcnow(), created_at=utcnow(),
        estimated_price=Decimal("500"), staff_rejection_reason=None,
    )
    defaults.update(overrides)
    return MagicMock(**defaults)


def make_quote(**overrides):
    defaults = dict(
        id=uuid.uuid4(), job_id=uuid.uuid4(), tenant_id=uuid.uuid4(), customer_id=uuid.uuid4(),
        quote_number="QT-1", quote_type="repair_quote",
        findings_snapshot="Gas leak", recommended_work="Replace valve",
        labour_amount=Decimal("800"), parts_amount=Decimal("450"), visit_fee=Decimal("200"),
        discount_amount=Decimal("0"), tax_amount=Decimal("0"), total_amount=Decimal("1450"),
        pre_approval_limit=None, requires_customer_approval=True,
        status="sent", sent_at=utcnow(), approved_at=None, rejected_at=None,
        rejection_reason=None, expires_at=utcnow() + timedelta(days=7),
        created_by_staff_id=uuid.uuid4(), approved_by_customer_id=None,
        created_at=utcnow(), updated_at=utcnow(),
    )
    defaults.update(overrides)
    return MagicMock(**defaults)


def make_template(**overrides):
    defaults = dict(id=uuid.uuid4(), tenant_id=uuid.uuid4(), service_id=uuid.uuid4(),
                     name="AC Annual Service", description="desc", is_active=True,
                     deleted_at=None, created_at=utcnow(), updated_at=utcnow())
    defaults.update(overrides)
    return MagicMock(**defaults)


def make_item(**overrides):
    defaults = dict(id=uuid.uuid4(), template_id=uuid.uuid4(), title="Clean filter",
                     description=None, sort_order=1, is_required=True,
                     requires_photo=False, requires_note=False, is_active=True, deleted_at=None)
    defaults.update(overrides)
    return MagicMock(**defaults)


def make_job_item(**overrides):
    defaults = dict(id=uuid.uuid4(), job_id=uuid.uuid4(), tenant_id=uuid.uuid4(),
                     template_item_id=None, title="Clean filter", description=None,
                     sort_order=1, is_required=True, requires_photo=False, requires_note=False,
                     is_completed=False, completed_by_staff_id=None, completed_at=None,
                     notes=None, photo_urls=[])
    defaults.update(overrides)
    return MagicMock(**defaults)


# ── 1. Error codes ─────────────────────────────────────────────────────────────

@pytest.mark.parametrize("code", [
    "QUOTE_NOT_FOUND", "QUOTE_ACCESS_DENIED", "QUOTE_ALREADY_APPROVED", "QUOTE_ALREADY_REJECTED",
    "QUOTE_EXPIRED", "QUOTE_NOT_APPROVABLE", "QUOTE_NOT_REJECTABLE", "QUOTE_REJECTION_REASON_REQUIRED",
    "QUOTE_APPROVAL_FAILED", "QUOTE_REJECTION_FAILED", "CHECKLIST_TEMPLATE_NOT_FOUND",
    "CHECKLIST_TEMPLATE_ACCESS_DENIED", "CHECKLIST_ITEM_NOT_FOUND", "CHECKLIST_ITEM_ACCESS_DENIED",
    "CHECKLIST_NOT_FOUND_FOR_JOB", "CHECKLIST_REQUIRED", "CHECKLIST_NOT_COMPLETE",
    "CHECKLIST_ITEM_NOTE_REQUIRED", "CHECKLIST_ITEM_PHOTO_REQUIRED", "CHECKLIST_ALREADY_COMPLETED",
    "CHECKLIST_NOT_ALLOWED_FOR_JOB_TYPE", "CHECKLIST_UPDATE_FAILED",
])
def test_error_code_registered(code):
    assert code in ERROR_CODES


# ── 2. Customer quote list ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_customer_can_list_own_quotes():
    cid = uuid.uuid4()
    job = make_job(customer_id=cid)
    quote = make_quote(customer_id=cid, job_id=job.id)
    db = MagicMock()
    result_rows = MagicMock(); result_rows.all.return_value = [(quote, job)]
    db.execute = AsyncMock(return_value=result_rows)
    svc = FieldOpsService(db=db, actor_id=cid, actor_role="customer")
    result = await svc.list_customer_quotes(cid)
    assert len(result["quotes"]) == 1
    assert result["quotes"][0]["quote_id"] == str(quote.id)
    assert result["quotes"][0]["total_amount"] == 1450.0

@pytest.mark.asyncio
async def test_customer_quote_list_filters_by_status():
    cid = uuid.uuid4()
    job = make_job(customer_id=cid)
    sent_quote = make_quote(customer_id=cid, job_id=job.id, status="sent")
    approved_quote = make_quote(customer_id=cid, job_id=job.id, status="approved")
    db = MagicMock()
    result_rows = MagicMock(); result_rows.all.return_value = [(sent_quote, job), (approved_quote, job)]
    db.execute = AsyncMock(return_value=result_rows)
    svc = FieldOpsService(db=db, actor_id=cid, actor_role="customer")
    result = await svc.list_customer_quotes(cid, status="approved")
    assert len(result["quotes"]) == 1
    assert result["quotes"][0]["status"] == "approved"


# ── 3. Customer quote detail ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_customer_quote_detail_includes_findings_and_breakdown():
    cid = uuid.uuid4()
    job = make_job(customer_id=cid, assigned_staff_id=None)
    quote = make_quote(customer_id=cid, job_id=job.id)
    db = db_seq(quote, job)
    svc = FieldOpsService(db=db, actor_id=cid, actor_role="customer")
    result = await svc.get_customer_quote_detail(cid, quote.id)
    assert result["assessment"]["findings"] == "Gas leak"
    assert result["price_breakdown"]["total_amount"] == 1450.0
    assert result["can_approve"] is True
    assert result["can_reject"] is True

@pytest.mark.asyncio
async def test_customer_cannot_view_another_customers_quote():
    cid = uuid.uuid4()
    quote = make_quote(customer_id=uuid.uuid4())  # different customer
    db = db_seq(quote)
    svc = FieldOpsService(db=db, actor_id=cid, actor_role="customer")
    with pytest.raises(ServiceOSException) as exc:
        await svc.get_customer_quote_detail(cid, quote.id)
    assert exc.value.error_code == "QUOTE_NOT_FOUND"

@pytest.mark.asyncio
async def test_expired_quote_detail_cannot_approve():
    cid = uuid.uuid4()
    job = make_job(customer_id=cid)
    quote = make_quote(customer_id=cid, job_id=job.id, status="sent",
                        expires_at=utcnow() - timedelta(days=1))
    db = db_seq(quote, job)
    svc = FieldOpsService(db=db, actor_id=cid, actor_role="customer")
    result = await svc.get_customer_quote_detail(cid, quote.id)
    assert result["status"] == "expired"
    assert result["can_approve"] is False


# ── 4. Customer approve/reject quote ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_customer_can_approve_sent_quote():
    cid = uuid.uuid4()
    job = make_job(customer_id=cid, status=JS.QUOTE_SENT, job_type=JobType.REPAIR)
    quote = make_quote(customer_id=cid, job_id=job.id, status="sent")
    db = MagicMock()
    db.execute = AsyncMock(side_effect=[
        MagicMock(scalar_one_or_none=MagicMock(return_value=quote)),  # lookup in approve_customer_quote
        MagicMock(scalar_one_or_none=MagicMock(return_value=job)),    # inside approve_job_quote
        MagicMock(scalar_one_or_none=MagicMock(return_value=quote)),  # inside _get_quote_for_customer
        MagicMock(scalar_one_or_none=MagicMock(return_value=job)),    # re-fetch for response
    ])
    svc = FieldOpsService(db=db, actor_id=cid, actor_role="customer")
    svc._write_history = AsyncMock(); svc._publish = AsyncMock()
    result = await svc.approve_customer_quote(quote.id, cid)
    assert result["quote_status"] == "approved"
    assert result["job_status"] == JS.QUOTE_APPROVED
    assert quote.status == "approved"
    assert job.status == JS.QUOTE_APPROVED

@pytest.mark.asyncio
async def test_approving_sets_quote_and_job_status():
    cid = uuid.uuid4()
    job = make_job(customer_id=cid, status=JS.QUOTE_SENT, job_type=JobType.REPAIR)
    quote = make_quote(customer_id=cid, job_id=job.id, status="sent")
    db = MagicMock()
    db.execute = AsyncMock(side_effect=[
        MagicMock(scalar_one_or_none=MagicMock(return_value=quote)),
        MagicMock(scalar_one_or_none=MagicMock(return_value=job)),
        MagicMock(scalar_one_or_none=MagicMock(return_value=quote)),
        MagicMock(scalar_one_or_none=MagicMock(return_value=job)),
    ])
    svc = FieldOpsService(db=db, actor_id=cid, actor_role="customer")
    svc._write_history = AsyncMock(); svc._publish = AsyncMock()
    await svc.approve_customer_quote(quote.id, cid)
    assert quote.status == "approved" and job.status == JS.QUOTE_APPROVED

@pytest.mark.asyncio
async def test_customer_can_reject_sent_quote_with_reason():
    cid = uuid.uuid4()
    job = make_job(customer_id=cid, status=JS.QUOTE_SENT, job_type=JobType.REPAIR)
    quote = make_quote(customer_id=cid, job_id=job.id, status="sent")
    db = MagicMock()
    db.execute = AsyncMock(side_effect=[
        MagicMock(scalar_one_or_none=MagicMock(return_value=quote)),
        MagicMock(scalar_one_or_none=MagicMock(return_value=job)),
        MagicMock(scalar_one_or_none=MagicMock(return_value=quote)),
        MagicMock(scalar_one_or_none=MagicMock(return_value=job)),
    ])
    svc = FieldOpsService(db=db, actor_id=cid, actor_role="customer")
    svc._write_history = AsyncMock(); svc._publish = AsyncMock()
    result = await svc.reject_customer_quote(quote.id, cid, "Price too high")
    assert result["quote_status"] == "rejected"
    assert result["job_status"] == JS.QUOTE_REJECTED
    assert quote.rejection_reason == "Price too high"

@pytest.mark.asyncio
async def test_reject_reason_is_required():
    cid = uuid.uuid4()
    job = make_job(customer_id=cid, status=JS.QUOTE_SENT)
    quote = make_quote(customer_id=cid, job_id=job.id, status="sent")
    db = db_seq(quote)
    svc = FieldOpsService(db=db, actor_id=cid, actor_role="customer")
    with pytest.raises(ServiceOSException) as exc:
        await svc.reject_customer_quote(quote.id, cid, "")
    assert exc.value.error_code == "QUOTE_REJECTION_REASON_REQUIRED"

@pytest.mark.asyncio
async def test_expired_quote_cannot_be_approved_via_customer_endpoint():
    cid = uuid.uuid4()
    job = make_job(customer_id=cid, status=JS.QUOTE_SENT)
    quote = make_quote(customer_id=cid, job_id=job.id, status="sent",
                        expires_at=utcnow() - timedelta(days=1))
    db = MagicMock()
    db.execute = AsyncMock(side_effect=[
        MagicMock(scalar_one_or_none=MagicMock(return_value=quote)),
        MagicMock(scalar_one_or_none=MagicMock(return_value=job)),
        MagicMock(scalar_one_or_none=MagicMock(return_value=quote)),
    ])
    svc = FieldOpsService(db=db, actor_id=cid, actor_role="customer")
    with pytest.raises(ServiceOSException) as exc:
        await svc.approve_customer_quote(quote.id, cid)
    assert exc.value.error_code == "QUOTE_EXPIRED"

@pytest.mark.asyncio
async def test_already_approved_quote_cannot_be_rejected():
    cid = uuid.uuid4()
    job = make_job(customer_id=cid, status=JS.QUOTE_APPROVED)
    quote = make_quote(customer_id=cid, job_id=job.id, status="approved")
    db = MagicMock()
    db.execute = AsyncMock(side_effect=[
        MagicMock(scalar_one_or_none=MagicMock(return_value=quote)),
        MagicMock(scalar_one_or_none=MagicMock(return_value=job)),
        MagicMock(scalar_one_or_none=MagicMock(return_value=quote)),
    ])
    svc = FieldOpsService(db=db, actor_id=cid, actor_role="customer")
    with pytest.raises(ServiceOSException) as exc:
        await svc.reject_customer_quote(quote.id, cid, "changed my mind")
    assert exc.value.error_code == "QUOTE_ALREADY_APPROVED"

@pytest.mark.asyncio
async def test_already_rejected_quote_cannot_be_approved():
    cid = uuid.uuid4()
    job = make_job(customer_id=cid, status=JS.QUOTE_REJECTED)
    quote = make_quote(customer_id=cid, job_id=job.id, status="rejected")
    db = MagicMock()
    db.execute = AsyncMock(side_effect=[
        MagicMock(scalar_one_or_none=MagicMock(return_value=quote)),
        MagicMock(scalar_one_or_none=MagicMock(return_value=job)),
        MagicMock(scalar_one_or_none=MagicMock(return_value=quote)),
    ])
    svc = FieldOpsService(db=db, actor_id=cid, actor_role="customer")
    with pytest.raises(ServiceOSException) as exc:
        await svc.approve_customer_quote(quote.id, cid)
    assert exc.value.error_code == "QUOTE_ALREADY_REJECTED"

@pytest.mark.asyncio
async def test_customer_cannot_approve_another_customers_quote_via_wrapper():
    cid = uuid.uuid4()
    quote = make_quote(customer_id=uuid.uuid4())
    db = db_seq(quote)
    svc = FieldOpsService(db=db, actor_id=cid, actor_role="customer")
    with pytest.raises(ServiceOSException) as exc:
        await svc.approve_customer_quote(quote.id, cid)
    assert exc.value.error_code == "QUOTE_NOT_FOUND"

@pytest.mark.asyncio
async def test_quote_decision_creates_status_history():
    cid = uuid.uuid4()
    job = make_job(customer_id=cid, status=JS.QUOTE_SENT)
    quote = make_quote(customer_id=cid, job_id=job.id, status="sent")
    db = MagicMock()
    db.execute = AsyncMock(side_effect=[
        MagicMock(scalar_one_or_none=MagicMock(return_value=quote)),
        MagicMock(scalar_one_or_none=MagicMock(return_value=job)),
        MagicMock(scalar_one_or_none=MagicMock(return_value=quote)),
        MagicMock(scalar_one_or_none=MagicMock(return_value=job)),
    ])
    svc = FieldOpsService(db=db, actor_id=cid, actor_role="customer")
    svc._write_history = AsyncMock(); svc._publish = AsyncMock()
    await svc.approve_customer_quote(quote.id, cid)
    svc._write_history.assert_awaited_once()


# ── 5. Checklist Templates (tenant CRUD) ────────────────────────────────────────

@pytest.mark.asyncio
async def test_tenant_owner_can_create_template():
    tid = uuid.uuid4()
    no_dup = MagicMock(); no_dup.scalar_one_or_none.return_value = None
    db = MagicMock()
    db.execute = AsyncMock(return_value=no_dup)
    db.add = MagicMock(); db.flush = AsyncMock()
    svc = ChecklistTemplateService(db=db, actor_id=uuid.uuid4(), actor_role="tenant_owner", actor_tenant_id=tid)
    result = await svc.create_template(tid, {"service_id": str(uuid.uuid4()), "name": "AC Annual Service"})
    assert result["name"] == "AC Annual Service"
    assert db.add.called

@pytest.mark.asyncio
async def test_tenant_owner_can_add_checklist_item():
    template = make_template()
    db = db_seq(template)
    svc = ChecklistTemplateService(db=db, actor_id=uuid.uuid4(), actor_role="tenant_owner",
                                    actor_tenant_id=template.tenant_id)
    result = await svc.add_item(template.id, {"title": "Clean filter", "is_required": True})
    assert result["title"] == "Clean filter"

@pytest.mark.asyncio
async def test_tenant_owner_can_edit_checklist_item():
    template = make_template()
    item = make_item(template_id=template.id)
    db = db_seq(template, item)
    svc = ChecklistTemplateService(db=db, actor_id=uuid.uuid4(), actor_role="tenant_owner",
                                    actor_tenant_id=template.tenant_id)
    result = await svc.update_item(template.id, item.id, {"title": "Clean filter thoroughly"})
    assert result["title"] == "Clean filter thoroughly"

@pytest.mark.asyncio
async def test_tenant_owner_can_soft_delete_item():
    template = make_template()
    item = make_item(template_id=template.id)
    db = db_seq(template, item)
    svc = ChecklistTemplateService(db=db, actor_id=uuid.uuid4(), actor_role="tenant_owner",
                                    actor_tenant_id=template.tenant_id)
    result = await svc.delete_item(template.id, item.id)
    assert result["deleted"] is True
    assert item.is_active is False
    assert item.deleted_at is not None

@pytest.mark.asyncio
async def test_tenant_owner_cannot_access_another_tenants_template():
    template = make_template(tenant_id=uuid.uuid4())
    db = db_seq(template)
    svc = ChecklistTemplateService(db=db, actor_id=uuid.uuid4(), actor_role="tenant_owner",
                                    actor_tenant_id=uuid.uuid4())
    with pytest.raises(ServiceOSException) as exc:
        await svc.get_template(template.id)
    assert exc.value.error_code == "CHECKLIST_TEMPLATE_NOT_FOUND"

@pytest.mark.asyncio
async def test_super_admin_can_access_any_template():
    template = make_template()
    items_result = MagicMock(); items_result.scalars.return_value.all.return_value = []
    db = MagicMock()
    db.execute = AsyncMock(side_effect=[
        MagicMock(scalar_one_or_none=MagicMock(return_value=template)), items_result])
    svc = ChecklistTemplateService(db=db, actor_id=uuid.uuid4(), actor_role="super_admin")
    result = await svc.get_template(template.id)
    assert result["template_id"] == str(template.id)

@pytest.mark.asyncio
async def test_duplicate_active_template_name_blocked():
    tid = uuid.uuid4()
    sid = uuid.uuid4()
    existing = make_template(tenant_id=tid, service_id=sid, name="AC Annual Service")
    dup_result = MagicMock(); dup_result.scalar_one_or_none.return_value = existing
    db = MagicMock()
    db.execute = AsyncMock(return_value=dup_result)
    svc = ChecklistTemplateService(db=db, actor_id=uuid.uuid4(), actor_role="tenant_owner", actor_tenant_id=tid)
    with pytest.raises(ServiceOSException) as exc:
        await svc.create_template(tid, {"service_id": str(sid), "name": "AC Annual Service"})
    assert exc.value.error_code == "CONFLICT"


# ── 6. Job checklist execution (normalized) ─────────────────────────────────────

@pytest.mark.asyncio
async def test_service_job_get_checklist_returns_items():
    me = uuid.uuid4()
    job = make_job(job_type=JobType.SERVICE, assigned_staff_id=me, status=JS.CHECKLIST_STARTED,
                    checklist_required=True)
    item1 = make_job_item(job_id=job.id, is_completed=True)
    item2 = make_job_item(job_id=job.id, is_completed=False)
    items_result = MagicMock(); items_result.scalars.return_value.all.return_value = [item1, item2]
    db = MagicMock()
    db.execute = AsyncMock(side_effect=[
        MagicMock(scalar_one_or_none=MagicMock(return_value=job)), items_result])
    svc = FieldOpsService(db=db, actor_id=me, actor_role="staff")
    result = await svc.get_job_checklist_items(job.id)
    assert result["total_items"] == 2
    assert result["completed_items"] == 1
    assert result["can_complete_checklist"] is False

@pytest.mark.asyncio
async def test_unassigned_staff_cannot_view_checklist():
    job = make_job(job_type=JobType.SERVICE, assigned_staff_id=uuid.uuid4())
    db = db_seq(job)
    svc = FieldOpsService(db=db, actor_id=uuid.uuid4(), actor_role="staff")
    with pytest.raises(NotFoundException):
        await svc.get_job_checklist_items(job.id)

@pytest.mark.asyncio
async def test_staff_can_mark_item_complete():
    me = uuid.uuid4()
    job = make_job(job_type=JobType.SERVICE, assigned_staff_id=me, status=JS.CHECKLIST_STARTED)
    item = make_job_item(job_id=job.id, is_required=True, requires_note=False, requires_photo=False)
    db = db_seq(job, item)
    svc = FieldOpsService(db=db, actor_id=me, actor_role="staff")
    result = await svc.update_job_checklist_item(job.id, item.id, True, "All good", [])
    assert result["is_completed"] is True
    assert item.completed_by_staff_id == me

@pytest.mark.asyncio
async def test_item_requiring_note_rejects_missing_note():
    me = uuid.uuid4()
    job = make_job(job_type=JobType.SERVICE, assigned_staff_id=me, status=JS.CHECKLIST_STARTED)
    item = make_job_item(job_id=job.id, requires_note=True)
    db = db_seq(job, item)
    svc = FieldOpsService(db=db, actor_id=me, actor_role="staff")
    with pytest.raises(ServiceOSException) as exc:
        await svc.update_job_checklist_item(job.id, item.id, True, None, None)
    assert exc.value.error_code == "CHECKLIST_ITEM_NOTE_REQUIRED"

@pytest.mark.asyncio
async def test_item_requiring_photo_rejects_missing_photo():
    me = uuid.uuid4()
    job = make_job(job_type=JobType.SERVICE, assigned_staff_id=me, status=JS.CHECKLIST_STARTED)
    item = make_job_item(job_id=job.id, requires_photo=True)
    db = db_seq(job, item)
    svc = FieldOpsService(db=db, actor_id=me, actor_role="staff")
    with pytest.raises(ServiceOSException) as exc:
        await svc.update_job_checklist_item(job.id, item.id, True, "note here", [])
    assert exc.value.error_code == "CHECKLIST_ITEM_PHOTO_REQUIRED"

@pytest.mark.asyncio
async def test_complete_checklist_fails_when_required_items_incomplete():
    me = uuid.uuid4()
    job = make_job(job_type=JobType.SERVICE, assigned_staff_id=me, status=JS.CHECKLIST_STARTED)
    item = make_job_item(job_id=job.id, is_required=True, is_completed=False)
    items_result = MagicMock(); items_result.scalars.return_value.all.return_value = [item]
    db = MagicMock()
    db.execute = AsyncMock(side_effect=[
        MagicMock(scalar_one_or_none=MagicMock(return_value=job)), items_result])
    svc = FieldOpsService(db=db, actor_id=me, actor_role="staff")
    with pytest.raises(ServiceOSException) as exc:
        await svc.complete_job_checklist(job.id)
    assert exc.value.error_code == "CHECKLIST_NOT_COMPLETE"

@pytest.mark.asyncio
async def test_complete_checklist_succeeds_when_all_required_complete():
    me = uuid.uuid4()
    job = make_job(job_type=JobType.SERVICE, assigned_staff_id=me, status=JS.CHECKLIST_STARTED)
    item = make_job_item(job_id=job.id, is_required=True, is_completed=True)
    items_result = MagicMock(); items_result.scalars.return_value.all.return_value = [item]
    items_result2 = MagicMock(); items_result2.scalars.return_value.all.return_value = [item]
    db = MagicMock()
    db.execute = AsyncMock(side_effect=[
        MagicMock(scalar_one_or_none=MagicMock(return_value=job)), items_result,
        MagicMock(scalar_one_or_none=MagicMock(return_value=job)), items_result2,
    ])
    svc = FieldOpsService(db=db, actor_id=me, actor_role="staff")
    svc._write_history = AsyncMock(); svc._publish = AsyncMock()
    result = await svc.complete_job_checklist(job.id)
    assert job.status == JS.CHECKLIST_COMPLETE
    assert job.checklist_completed_at is not None
    assert result["checklist_status"] == "complete"

@pytest.mark.asyncio
async def test_work_complete_blocked_before_checklist_complete():
    me = uuid.uuid4()
    job = make_job(job_type=JobType.SERVICE, assigned_staff_id=me, status=JS.WORK_STARTED,
                    checklist_required=True)
    db = db_seq(job)
    svc = FieldOpsService(db=db, actor_id=me, actor_role="staff")
    with pytest.raises(ServiceOSException) as exc:
        await svc.update_status(job.id, JS.WORK_COMPLETE, None, None, None)
    assert exc.value.error_code == "CHECKLIST_REQUIRED_BEFORE_WORK_COMPLETE"

@pytest.mark.asyncio
async def test_work_complete_works_after_checklist_complete():
    me = uuid.uuid4()
    job = make_job(job_type=JobType.SERVICE, assigned_staff_id=me, status=JS.CHECKLIST_COMPLETE,
                    checklist_required=True)
    db = db_seq(job)
    svc = FieldOpsService(db=db, actor_id=me, actor_role="staff")
    svc._write_history = AsyncMock(); svc._publish = AsyncMock()
    result = await svc.update_status(job.id, JS.WORK_COMPLETE, None, None, None)
    assert result["status"] == JS.WORK_COMPLETE

@pytest.mark.asyncio
async def test_customer_can_view_completed_checklist_summary():
    cid = uuid.uuid4()
    job = make_job(customer_id=cid, checklist_required=True, checklist_completed_at=utcnow())
    item = make_job_item(job_id=job.id, is_completed=True)
    items_result = MagicMock(); items_result.scalars.return_value.all.return_value = [item]
    db = MagicMock()
    db.execute = AsyncMock(side_effect=[
        MagicMock(scalar_one_or_none=MagicMock(return_value=job)), items_result])
    svc = FieldOpsService(db=db, actor_id=cid, actor_role="customer")
    result = await svc.get_customer_checklist_summary(job.id, cid)
    assert result["completed_required_items"] == 1
    assert result["checklist_completed_at"] is not None

@pytest.mark.asyncio
async def test_customer_cannot_view_another_customers_checklist():
    job = make_job(customer_id=uuid.uuid4())
    db = db_seq(job)
    svc = FieldOpsService(db=db, actor_id=uuid.uuid4(), actor_role="customer")
    with pytest.raises(ServiceOSException) as exc:
        await svc.get_customer_checklist_summary(job.id, uuid.uuid4())
    assert exc.value.error_code == "JOB_NOT_FOUND"

@pytest.mark.asyncio
async def test_tenant_owner_can_view_job_checklist():
    tid = uuid.uuid4()
    job = make_job(tenant_id=tid, job_type=JobType.SERVICE)
    items_result = MagicMock(); items_result.scalars.return_value.all.return_value = []
    db = MagicMock()
    db.execute = AsyncMock(side_effect=[
        MagicMock(scalar_one_or_none=MagicMock(return_value=job)), items_result])
    svc = FieldOpsService(db=db, actor_id=uuid.uuid4(), actor_role="tenant_owner", actor_tenant_id=tid)
    result = await svc.get_job_checklist_items(job.id)
    assert result["job_id"] == str(job.id)

@pytest.mark.asyncio
async def test_cross_tenant_checklist_access_blocked():
    job = make_job(job_type=JobType.SERVICE, tenant_id=uuid.uuid4())
    db = db_seq(job)
    svc = FieldOpsService(db=db, actor_id=uuid.uuid4(), actor_role="tenant_owner",
                           actor_tenant_id=uuid.uuid4())
    with pytest.raises(NotFoundException):
        await svc.get_job_checklist_items(job.id)


# ── 7. Model fields ───────────────────────────────────────────────────────────────

@pytest.mark.parametrize("field", [
    "tenant_id", "service_id", "name", "description", "is_active", "deleted_at",
])
def test_service_checklist_template_has_field(field):
    assert hasattr(ServiceChecklistTemplate, field)

@pytest.mark.parametrize("field", [
    "template_id", "title", "description", "sort_order", "is_required",
    "requires_photo", "requires_note", "is_active", "deleted_at",
])
def test_service_checklist_item_has_field(field):
    assert hasattr(ServiceChecklistItem, field)

@pytest.mark.parametrize("field", [
    "job_id", "tenant_id", "template_item_id", "title", "description", "sort_order",
    "is_required", "requires_photo", "requires_note", "is_completed",
    "completed_by_staff_id", "completed_at", "notes", "photo_urls",
])
def test_job_checklist_item_has_field(field):
    assert hasattr(JobChecklistItem, field)


# ── 8. OpenAPI ────────────────────────────────────────────────────────────────────

def test_openapi_includes_customer_quote_endpoints():
    from app.main import app
    schema = app.openapi()
    assert "/v1/customer/quotes" in schema["paths"]
    assert "/v1/customer/quotes/{quote_id}" in schema["paths"]
    assert "/v1/customer/quotes/{quote_id}/approve" in schema["paths"]
    assert "/v1/customer/quotes/{quote_id}/reject" in schema["paths"]

def test_openapi_includes_checklist_template_endpoints():
    from app.main import app
    schema = app.openapi()
    assert "/v1/tenant/checklist-templates" in schema["paths"]
    assert "/v1/tenant/checklist-templates/{template_id}" in schema["paths"]
    assert "/v1/tenant/checklist-templates/{template_id}/items" in schema["paths"]

def test_openapi_includes_job_checklist_endpoints():
    from app.main import app
    schema = app.openapi()
    assert "/v1/jobs/{job_id}/checklist" in schema["paths"]
    assert "/v1/staff/me/jobs/{job_id}/checklist" in schema["paths"]
    assert "/v1/customer/jobs/{job_id}/checklist" in schema["paths"]

def test_openapi_schema_is_valid():
    from app.main import app
    schema = app.openapi()
    assert schema["openapi"]
    assert "paths" in schema and "components" in schema
