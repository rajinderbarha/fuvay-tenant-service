"""Regression coverage for social complaints, SLA closure, health, and badges."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
import uuid

import pytest

from app.engines.complaints.complaint_service import ComplaintService
from app.engines.complaints.models import CustomerComplaint
from app.engines.messaging_gateway import flow
from app.engines.messaging_gateway.constants import (
    CHANNEL_INSTAGRAM,
    CMD_COMPLAINT,
    DURABLE_ACTION_PICKS,
    KNOWN_COMMANDS,
    PICK_COMPLAINT,
)


ROOT = Path(__file__).resolve().parents[1]


def _booking() -> dict:
    return {
        "record_type": "service_job",
        "record_id": str(uuid.uuid4()),
        "booking_id": str(uuid.uuid4()),
        "booking_number": "BK-20260913-000001",
        "category_id": str(uuid.uuid4()),
        "offering_id": str(uuid.uuid4()),
        "service": "AC repair",
        "problem": "AC not cooling",
    }


class FakeComplaintIdentity:
    def __init__(self):
        self.booking = _booking()
        self.state = None

    async def complaint_cases(self, _thread):
        return []

    async def complaint_bookings(self, _thread):
        return [self.booking]

    async def begin_social_complaint(self, _thread, booking, complaint_type=None):
        self.state = {"mode": "new", **booking}
        if complaint_type:
            self.state["complaint_type"] = complaint_type
        return self.state

    async def social_complaint_state(self, _thread):
        return self.state


def test_complaint_is_a_known_durable_social_action():
    assert CMD_COMPLAINT in KNOWN_COMMANDS
    assert PICK_COMPLAINT in DURABLE_ACTION_PICKS


@pytest.mark.asyncio
async def test_customer_complaint_options_are_provider_owned_and_canonical():
    from app.engines.complaints.customer_router import (
        complaint_options, customer_complaint_router,
    )

    response = await complaint_options(r=None, _u=SimpleNamespace())
    assert response.data == {
        "handled_by": "provider",
        "available_after": "service_started",
        "options": [
            {"value": "service_quality", "label": "Service quality issue"},
            {"value": "technician_behavior", "label": "Technician behaviour"},
            {"value": "property_damage", "label": "Property damage"},
        ],
    }
    paths = [route.path for route in customer_complaint_router.routes]
    assert paths.index("/v1/customer/complaints/options") < paths.index(
        "/v1/customer/complaints/{complaint_id}"
    )


@pytest.mark.asyncio
async def test_instagram_complaint_selects_booking_then_type_then_description():
    identity = FakeComplaintIdentity()
    thread = SimpleNamespace(customer_id=uuid.uuid4(), id=uuid.uuid4())

    choose_type = await flow._complaint_step(
        thread, identity, "new", CHANNEL_INSTAGRAM,
    )
    assert choose_type.picker
    ids = [
        row["id"] for row in choose_type.picker["rows"]
        if row["id"].startswith("cmp|type|")
    ]
    assert ids == [
        "cmp|type|service_quality",
        "cmp|type|technician_behavior",
        "cmp|type|property_damage",
    ]
    assert not any("late_arrival" in item or "no_show" in item for item in ids)
    assert identity.state["booking_number"] == "BK-20260913-000001"

    describe = await flow._complaint_step(
        thread, identity, "type|service_quality", CHANNEL_INSTAGRAM,
    )
    assert describe.picker is None
    assert "next message" in describe.text.lower()
    assert identity.state["complaint_type"] == "service_quality"


@pytest.mark.asyncio
async def test_instagram_case_renders_resolution_accept_and_reject_actions():
    identity = FakeComplaintIdentity()
    complaint_id = str(uuid.uuid4())
    resolution_id = str(uuid.uuid4())
    identity.complaint_status_view = AsyncMock(return_value={
        "id": complaint_id,
        "number": "CMP-12345678",
        "type": "service_quality",
        "status": "resolution_proposed",
        "description": "Cooling stopped again after the visit.",
        "sla_status": "on_time",
        "resolution": {
            "id": resolution_id,
            "type": "rework",
            "description": "A technician will revisit at no labour charge.",
            "notes": None,
        },
    })
    thread = SimpleNamespace(customer_id=uuid.uuid4(), id=uuid.uuid4())

    turn = await flow._complaint_step(
        thread, identity, f"case|{complaint_id}", CHANNEL_INSTAGRAM,
    )
    ids = [row["id"] for row in turn.picker["rows"]]
    assert f"cmp|accept|{complaint_id}|{resolution_id}" in ids
    assert f"cmp|reject|{complaint_id}|{resolution_id}" in ids
    assert "PROPOSED RESOLUTION" in turn.text


@pytest.mark.asyncio
async def test_first_response_sla_never_reopens_after_provider_response():
    complaint = CustomerComplaint(
        customer_id=uuid.uuid4(), category_id=uuid.uuid4(),
        record_type="service_job", record_id=uuid.uuid4(),
        complaint_type="service_quality", description="test complaint",
        status="open", sla_status="on_time",
        tenant_first_response_due_at=datetime.now(timezone.utc) - timedelta(days=2),
        provider_responded_at=datetime.now(timezone.utc) - timedelta(days=1),
    )
    db = AsyncMock()
    result = await ComplaintService().check_and_update_sla(db, complaint)
    assert result.sla_status == "on_time"
    db.flush.assert_not_awaited()


def test_sla_worker_filters_answered_complaints_and_dashboard_returns_badges():
    worker = (ROOT / "app/jobs/complaint_sla.py").read_text(encoding="utf-8")
    dashboard = (ROOT / "app/engines/execution/home_services_dashboard_service.py").read_text(encoding="utf-8")
    provider_page = (ROOT / "frontend/tenant-portal/app/(tenant)/dashboard/page.tsx").read_text(encoding="utf-8")
    assert "CustomerComplaint.provider_responded_at.is_(None)" in worker
    assert '"badges": public_badges' in dashboard
    assert "<TrustBadges badges={data.provider_health.badges}" in provider_page


def test_only_unresolved_complaints_feed_quality_rate():
    single = (ROOT / "app/engines/trust_quality/service.py").read_text(encoding="utf-8")
    batch = (ROOT / "app/engines/trust_quality/recalculation.py").read_text(encoding="utf-8")
    operational = (ROOT / "app/engines/tenant_engine/health.py").read_text(encoding="utf-8")
    for source in (single, batch, operational):
        assert "'resolved','closed','cancelled','rejected','settled'" in source
    assert 'write_health_signal(\n                tenant_id, "customer_satisfaction"' in operational


def test_home_service_complaints_start_with_actual_work():
    """Pre-work timing is automatic; customer complaints begin with service."""
    from app.engines.complaints.constants import (
        HOME_SERVICE_PROVIDER_COMPLAINT_TYPES,
        HOME_SERVICE_WORK_STARTED_STATUSES,
    )

    assert HOME_SERVICE_PROVIDER_COMPLAINT_TYPES == {
        "service_quality", "technician_behavior", "property_damage",
    }
    assert "service_started" in HOME_SERVICE_WORK_STARTED_STATUSES
    assert "completed" in HOME_SERVICE_WORK_STARTED_STATUSES
    assert "assigned" not in HOME_SERVICE_WORK_STARTED_STATUSES
    assert "on_the_way" not in HOME_SERVICE_WORK_STARTED_STATUSES
    assert "inspection_started" not in HOME_SERVICE_WORK_STARTED_STATUSES


@pytest.mark.asyncio
async def test_pre_work_home_service_complaint_is_not_eligible():
    from app.engines.complaints.eligibility_service import ComplaintEligibilityService

    customer_id = uuid.uuid4()
    service = ComplaintEligibilityService()
    service._fetch_record = AsyncMock(return_value=SimpleNamespace(
        status="on_the_way", customer_id=customer_id, created_at=datetime.now(timezone.utc),
    ))
    service._home_service_work_started = AsyncMock(return_value=False)
    service._customer_owns_record = AsyncMock(return_value=True)

    result = await service.check_eligible(
        AsyncMock(), customer_id, "service_job", uuid.uuid4(),
        complaint_type="service_quality",
    )
    assert result["eligible"] is False
    assert "after the technician starts" in result["reason"]


@pytest.mark.asyncio
@pytest.mark.parametrize("status", ["service_started", "completed"])
async def test_booking_age_does_not_expire_a_newly_started_service_issue(status):
    from app.engines.complaints.eligibility_service import ComplaintEligibilityService

    customer_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    svc = ComplaintEligibilityService()
    svc._fetch_record = AsyncMock(return_value=SimpleNamespace(
        status=status, customer_id=customer_id,
        created_at=now - timedelta(days=20),
        updated_at=now - timedelta(hours=1),
    ))
    svc._home_service_work_started = AsyncMock(return_value=True)
    svc._customer_owns_record = AsyncMock(return_value=True)
    svc.get_complaint_policy = AsyncMock(return_value=None)
    svc.check_duplicate_open_complaint = AsyncMock(return_value=False)

    result = await svc.check_eligible(
        AsyncMock(), customer_id, "service_job", uuid.uuid4(),
        complaint_type="property_damage",
    )
    assert result["eligible"] is True


@pytest.mark.asyncio
async def test_retired_late_arrival_choice_is_rejected_by_backend():
    from app.engines.complaints.constants import ERR_COMPLAINT_TYPE_NOT_SUPPORTED
    from app.engines.complaints.eligibility_service import ComplaintEligibilityService

    customer_id = uuid.uuid4()
    service = ComplaintEligibilityService()
    service._fetch_record = AsyncMock(return_value=SimpleNamespace(
        status="service_started", customer_id=customer_id,
        created_at=datetime.now(timezone.utc),
    ))

    result = await service.check_eligible(
        AsyncMock(), customer_id, "service_job", uuid.uuid4(),
        complaint_type="late_arrival",
    )
    assert result["eligible"] is False
    assert result["reason_code"] == ERR_COMPLAINT_TYPE_NOT_SUPPORTED


@pytest.mark.asyncio
async def test_invoice_record_cannot_reintroduce_retired_issue_choices():
    from app.engines.complaints.constants import ERR_COMPLAINT_TYPE_NOT_SUPPORTED
    from app.engines.complaints.eligibility_service import ComplaintEligibilityService

    customer_id = uuid.uuid4()
    svc = ComplaintEligibilityService()
    svc._fetch_record = AsyncMock(return_value=SimpleNamespace(
        status="paid", customer_id=customer_id, job_id=uuid.uuid4(),
        created_at=datetime.now(timezone.utc),
    ))
    svc._customer_owns_record = AsyncMock(return_value=True)
    result = await svc.check_eligible(
        AsyncMock(), customer_id, "service_invoice", uuid.uuid4(),
        complaint_type="late_arrival",
    )
    assert result["reason_code"] == ERR_COMPLAINT_TYPE_NOT_SUPPORTED


@pytest.mark.asyncio
async def test_work_start_proof_rejects_pre_work_and_admin_closed_jobs():
    from app.engines.complaints.eligibility_service import ComplaintEligibilityService

    svc = ComplaintEligibilityService()
    db = MagicMock()
    db.execute = AsyncMock(return_value=MagicMock())
    db.execute.return_value.scalar_one_or_none.return_value = None
    job_id = uuid.uuid4()
    assert not await svc._home_service_work_started(
        db, record_type="service_job", record_id=job_id,
        record=SimpleNamespace(status="on_the_way"),
    )
    db.execute.assert_not_awaited()
    assert not await svc._home_service_work_started(
        db, record_type="service_job", record_id=job_id,
        record=SimpleNamespace(status="completed"),
    )
    db.execute.assert_awaited_once()

    db.execute.return_value.scalar_one_or_none.return_value = 1
    assert await svc._home_service_work_started(
        db, record_type="service_job", record_id=job_id,
        record=SimpleNamespace(status="completed"),
    )


@pytest.mark.asyncio
async def test_dedicated_refund_can_create_backing_case_without_public_refund_choice():
    from app.engines.complaints.complaint_service import ComplaintService

    svc = ComplaintService()
    svc._eligibility.check_eligible = AsyncMock(return_value={
        "eligible": False, "reason_code": "COMPLAINT_NOT_ELIGIBLE",
    })
    with pytest.raises(ValueError, match="COMPLAINT_NOT_ELIGIBLE"):
        await svc.create_complaint(
            AsyncMock(), uuid.uuid4(), category_id=uuid.uuid4(),
            record_type="service_job", record_id=uuid.uuid4(),
            complaint_type="refund_request", description="Refund for job",
            internal_refund_request=True,
        )
    assert svc._eligibility.check_eligible.await_args.kwargs["complaint_type"] is None
