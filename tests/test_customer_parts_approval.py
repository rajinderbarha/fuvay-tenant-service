"""PARTS-APPROVAL phase -- exercises the new customer-facing methods on
`HomeServiceJobExecutionService` directly (the same service the new
`/v1/customer/service-jobs/*` router calls). Real factories, no mocked-away
ownership/serialization.
"""
import uuid
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.engines.execution.home_service_service import HomeServiceJobExecutionService
from app.engines.execution.models import PartsRequest
from app.engines.execution.constants import (
    PARTS_STATUS_REQUESTED, PARTS_STATUS_BUSINESS_APPROVED, PARTS_STATUS_BUSINESS_REJECTED,
    PARTS_STATUS_CUSTOMER_APPROVAL_PENDING, PARTS_STATUS_CUSTOMER_APPROVED, PARTS_STATUS_CUSTOMER_REJECTED,
)
from app.exceptions import ServiceOSException


class _FakeJob:
    def __init__(self, job_id, customer_id, tenant_id, status="quote_required", booking_id=None, assigned_staff_id=None):
        self.id = job_id
        self.customer_id = customer_id
        self.tenant_id = tenant_id
        self.status = status
        self.booking_id = booking_id or uuid.uuid4()
        self.assigned_staff_id = assigned_staff_id


def _pr(job_id, tenant_id, **overrides):
    defaults = dict(
        id=uuid.uuid4(), job_id=job_id, tenant_id=tenant_id, technician_id=uuid.uuid4(),
        part_name="AC capacitor", quantity=1, estimated_cost=Decimal("850"),
        reason="Needed to restore cooling performance.", photo_ids=[], technician_note=None,
        customer_approval_required=True, business_approval_required=True,
        status=PARTS_STATUS_CUSTOMER_APPROVAL_PENDING,
        approved_by=None, approved_at=None, rejected_by=None, rejected_at=None,
        rejection_reason=None, request_id=None, created_at=None, updated_at=None,
    )
    defaults.update(overrides)
    pr = PartsRequest()
    for k, v in defaults.items():
        setattr(pr, k, v)
    return pr


def _scalars(items):
    result = MagicMock()
    result.scalars.return_value.all.return_value = list(items)
    result.scalars.return_value.first.return_value = items[0] if items else None
    return result


@pytest.mark.asyncio
async def test_customer_can_read_own_visible_parts_requests():
    customer_id = uuid.uuid4()
    job = _FakeJob(uuid.uuid4(), customer_id, uuid.uuid4())
    pr = _pr(job.id, job.tenant_id)
    db = MagicMock()
    db.get = AsyncMock(return_value=job)
    db.execute = AsyncMock(side_effect=[_scalars([pr]), _scalars([])])
    svc = HomeServiceJobExecutionService()
    data = await svc.customer_list_parts_requests(db, job.id, customer_id)
    assert len(data["items"]) == 1
    assert data["items"][0]["status"] == PARTS_STATUS_CUSTOMER_APPROVAL_PENDING


@pytest.mark.asyncio
async def test_foreign_customer_cannot_read_job_parts_requests():
    job = _FakeJob(uuid.uuid4(), uuid.uuid4(), uuid.uuid4())
    db = MagicMock()
    db.get = AsyncMock(return_value=job)
    svc = HomeServiceJobExecutionService()
    with pytest.raises(ServiceOSException) as exc:
        await svc.customer_list_parts_requests(db, job.id, uuid.uuid4())
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_nonexistent_job_is_enumeration_safe():
    db = MagicMock()
    db.get = AsyncMock(return_value=None)
    svc = HomeServiceJobExecutionService()
    with pytest.raises(ServiceOSException) as exc:
        await svc.customer_list_parts_requests(db, uuid.uuid4(), uuid.uuid4())
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_internal_only_requests_remain_hidden_from_customer():
    customer_id = uuid.uuid4()
    job = _FakeJob(uuid.uuid4(), customer_id, uuid.uuid4())
    requested = _pr(job.id, job.tenant_id, status=PARTS_STATUS_REQUESTED)
    business_rejected = _pr(job.id, job.tenant_id, status=PARTS_STATUS_BUSINESS_REJECTED)
    db = MagicMock()
    db.get = AsyncMock(return_value=job)
    db.execute = AsyncMock(side_effect=[_scalars([requested, business_rejected]), _scalars([])])
    svc = HomeServiceJobExecutionService()
    data = await svc.customer_list_parts_requests(db, job.id, customer_id)
    assert data["items"] == []


@pytest.mark.asyncio
async def test_customer_safe_fields_exclude_internal_data():
    customer_id = uuid.uuid4()
    job = _FakeJob(uuid.uuid4(), customer_id, uuid.uuid4())
    pr = _pr(job.id, job.tenant_id, technician_note="internal note", photo_ids=["p1"])
    db = MagicMock()
    db.get = AsyncMock(return_value=job)
    db.execute = AsyncMock(side_effect=[_scalars([pr]), _scalars([])])
    svc = HomeServiceJobExecutionService()
    data = await svc.customer_list_parts_requests(db, job.id, customer_id)
    item = data["items"][0]
    assert "technician_note" not in item
    assert "photo_ids" not in item
    assert "technician_id" not in item
    assert "tenant_id" not in item


@pytest.mark.asyncio
async def test_multiple_line_items_sum_into_backend_authoritative_totals():
    customer_id = uuid.uuid4()
    job = _FakeJob(uuid.uuid4(), customer_id, uuid.uuid4())
    p1 = _pr(job.id, job.tenant_id, estimated_cost=Decimal("850"), quantity=1)
    p2 = _pr(job.id, job.tenant_id, estimated_cost=Decimal("200"), quantity=2, status=PARTS_STATUS_BUSINESS_APPROVED, customer_approval_required=False)
    db = MagicMock()
    db.get = AsyncMock(return_value=job)
    db.execute = AsyncMock(side_effect=[_scalars([p1, p2]), _scalars([])])
    svc = HomeServiceJobExecutionService()
    data = await svc.customer_list_parts_requests(db, job.id, customer_id)
    assert data["additional_total"] == "1250"
    assert data["new_estimated_total"] == "1250"


@pytest.mark.asyncio
async def test_previous_estimate_comes_from_the_current_quote():
    customer_id = uuid.uuid4()
    job = _FakeJob(uuid.uuid4(), customer_id, uuid.uuid4())
    pr = _pr(job.id, job.tenant_id)
    quote = MagicMock(customer_payable_amount=Decimal("1450"), currency="INR")
    db = MagicMock()
    db.get = AsyncMock(return_value=job)
    db.execute = AsyncMock(side_effect=[_scalars([pr]), _scalars([quote])])
    svc = HomeServiceJobExecutionService()
    data = await svc.customer_list_parts_requests(db, job.id, customer_id)
    assert data["previous_estimated_total"] == "1450"
    assert data["new_estimated_total"] == "2300"


@pytest.mark.asyncio
async def test_customer_can_approve_a_pending_request():
    customer_id = uuid.uuid4()
    job = _FakeJob(uuid.uuid4(), customer_id, uuid.uuid4())
    pr = _pr(job.id, job.tenant_id)
    db = MagicMock()
    db.execute = AsyncMock(return_value=_scalars([pr]))
    db.get = AsyncMock(return_value=job)
    db.add = MagicMock()
    db.flush = AsyncMock()
    svc = HomeServiceJobExecutionService()
    data = await svc.customer_decide_parts_request(db, pr.id, customer_id, "approve", None)
    assert data["status"] == PARTS_STATUS_CUSTOMER_APPROVED


@pytest.mark.asyncio
async def test_customer_can_decline_a_pending_request_with_a_reason():
    customer_id = uuid.uuid4()
    job = _FakeJob(uuid.uuid4(), customer_id, uuid.uuid4())
    pr = _pr(job.id, job.tenant_id)
    db = MagicMock()
    db.execute = AsyncMock(return_value=_scalars([pr]))
    db.get = AsyncMock(return_value=job)
    db.add = MagicMock()
    db.flush = AsyncMock()
    svc = HomeServiceJobExecutionService()
    data = await svc.customer_decide_parts_request(db, pr.id, customer_id, "decline", "Too expensive")
    assert data["status"] == PARTS_STATUS_CUSTOMER_REJECTED
    assert data["rejection_reason"] == "Too expensive"


@pytest.mark.asyncio
async def test_decline_requires_a_reason():
    customer_id = uuid.uuid4()
    job = _FakeJob(uuid.uuid4(), customer_id, uuid.uuid4())
    pr = _pr(job.id, job.tenant_id)
    db = MagicMock()
    db.execute = AsyncMock(return_value=_scalars([pr]))
    db.get = AsyncMock(return_value=job)
    svc = HomeServiceJobExecutionService()
    with pytest.raises(ServiceOSException) as exc:
        await svc.customer_decide_parts_request(db, pr.id, customer_id, "decline", "")
    assert exc.value.error_code == "PART_REASON_REQUIRED"


@pytest.mark.asyncio
async def test_visibility_only_request_cannot_be_decided_by_customer():
    customer_id = uuid.uuid4()
    job = _FakeJob(uuid.uuid4(), customer_id, uuid.uuid4())
    pr = _pr(job.id, job.tenant_id, customer_approval_required=False, status=PARTS_STATUS_BUSINESS_APPROVED)
    db = MagicMock()
    db.execute = AsyncMock(return_value=_scalars([pr]))
    db.get = AsyncMock(return_value=job)
    svc = HomeServiceJobExecutionService()
    with pytest.raises(ServiceOSException) as exc:
        await svc.customer_decide_parts_request(db, pr.id, customer_id, "approve", None)
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_repeated_decision_after_approval_fails_safely():
    customer_id = uuid.uuid4()
    job = _FakeJob(uuid.uuid4(), customer_id, uuid.uuid4())
    pr = _pr(job.id, job.tenant_id, status=PARTS_STATUS_CUSTOMER_APPROVED, approved_by=customer_id)
    db = MagicMock()
    db.execute = AsyncMock(return_value=_scalars([pr]))
    db.get = AsyncMock(return_value=job)
    svc = HomeServiceJobExecutionService()
    with pytest.raises(ServiceOSException) as exc:
        await svc.customer_decide_parts_request(db, pr.id, customer_id, "approve", None)
    assert exc.value.error_code == "PARTS_REQUEST_ALREADY_DECIDED"
    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_decline_after_approve_fails():
    customer_id = uuid.uuid4()
    job = _FakeJob(uuid.uuid4(), customer_id, uuid.uuid4())
    pr = _pr(job.id, job.tenant_id, status=PARTS_STATUS_CUSTOMER_APPROVED)
    db = MagicMock()
    db.execute = AsyncMock(return_value=_scalars([pr]))
    db.get = AsyncMock(return_value=job)
    svc = HomeServiceJobExecutionService()
    with pytest.raises(ServiceOSException) as exc:
        await svc.customer_decide_parts_request(db, pr.id, customer_id, "decline", "changed my mind")
    assert exc.value.error_code == "PARTS_REQUEST_ALREADY_DECIDED"


@pytest.mark.asyncio
async def test_business_pending_request_cannot_be_decided_by_customer_yet():
    customer_id = uuid.uuid4()
    job = _FakeJob(uuid.uuid4(), customer_id, uuid.uuid4())
    pr = _pr(job.id, job.tenant_id, status=PARTS_STATUS_REQUESTED)
    db = MagicMock()
    db.execute = AsyncMock(return_value=_scalars([pr]))
    db.get = AsyncMock(return_value=job)
    svc = HomeServiceJobExecutionService()
    with pytest.raises(ServiceOSException) as exc:
        await svc.customer_decide_parts_request(db, pr.id, customer_id, "approve", None)
    assert exc.value.error_code == "PARTS_REQUEST_ALREADY_DECIDED"


@pytest.mark.asyncio
async def test_foreign_customer_cannot_decide():
    job = _FakeJob(uuid.uuid4(), uuid.uuid4(), uuid.uuid4())
    pr = _pr(job.id, job.tenant_id)
    db = MagicMock()
    db.execute = AsyncMock(return_value=_scalars([pr]))
    db.get = AsyncMock(return_value=job)
    svc = HomeServiceJobExecutionService()
    with pytest.raises(ServiceOSException) as exc:
        await svc.customer_decide_parts_request(db, pr.id, uuid.uuid4(), "approve", None)
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_nonexistent_parts_request_is_enumeration_safe():
    db = MagicMock()
    db.execute = AsyncMock(return_value=_scalars([]))
    svc = HomeServiceJobExecutionService()
    with pytest.raises(ServiceOSException) as exc:
        await svc.customer_decide_parts_request(db, uuid.uuid4(), uuid.uuid4(), "approve", None)
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_approval_never_writes_a_payment_record():
    customer_id = uuid.uuid4()
    job = _FakeJob(uuid.uuid4(), customer_id, uuid.uuid4())
    pr = _pr(job.id, job.tenant_id)
    db = MagicMock()
    db.execute = AsyncMock(return_value=_scalars([pr]))
    db.get = AsyncMock(return_value=job)
    db.add = MagicMock()
    db.flush = AsyncMock()
    svc = HomeServiceJobExecutionService()
    data = await svc.customer_decide_parts_request(db, pr.id, customer_id, "approve", None)
    assert "payment" not in data
    assert "collected_amount" not in data


@pytest.mark.asyncio
async def test_decision_logs_a_job_event():
    customer_id = uuid.uuid4()
    job = _FakeJob(uuid.uuid4(), customer_id, uuid.uuid4())
    pr = _pr(job.id, job.tenant_id)
    db = MagicMock()
    db.execute = AsyncMock(return_value=_scalars([pr]))
    db.get = AsyncMock(return_value=job)
    added = []
    db.add = MagicMock(side_effect=lambda obj: added.append(obj))
    db.flush = AsyncMock()
    svc = HomeServiceJobExecutionService()
    await svc.customer_decide_parts_request(db, pr.id, customer_id, "approve", None)
    event_types = [getattr(o, "event_type", None) for o in added]
    assert "customer_part_approved" in event_types
