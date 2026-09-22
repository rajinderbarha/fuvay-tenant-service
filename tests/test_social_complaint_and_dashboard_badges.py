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
    PICK_WARRANTY,
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
    assert PICK_WARRANTY in DURABLE_ACTION_PICKS


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
    # The prompt arms the customer's NEXT message, so it has to be possible
    # to change your mind: without a Cancel the only escape was to type
    # something, which then became the complaint.
    assert describe.picker["allow_text"] is True
    assert [row["id"] for row in describe.picker["rows"]] == ["cmp|cancel"]
    assert "next message" in describe.picker["body"].lower()
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
    assert "inspection_started" in HOME_SERVICE_WORK_STARTED_STATUSES


@pytest.mark.asyncio
async def test_social_menu_does_not_offer_issue_reporting_immediately_after_booking():
    """A pre-service booking can be tracked/cancelled, but cannot create a case."""
    class Identity:
        async def live_bookings(self, _thread):
            return [{"number": "BK-1", "service": "AC repair", "status": "Assigned"}]

        async def cancel_options(self, _thread, _booking_number):
            return {"can_cancel": True}

        async def complaint_cases(self, _thread):
            return []

        async def complaint_bookings(self, _thread):
            return []

        async def warranty_menu_available(self, _thread):
            return False

    thread = SimpleNamespace(customer_id=uuid.uuid4(), id=uuid.uuid4())
    turn = await flow._booked_menu_for(Identity(), thread, "BK-1", "Booked")
    titles = {row["title"] for row in turn.picker["rows"]}
    assert flow.TRACK_ROW in titles
    assert flow.CANCEL_ROW in titles
    assert flow.REPORT_ISSUE_ROW not in titles
    assert flow.TRACK_COMPLAINT_ROW not in titles
    assert flow.WARRANTY_ROW not in titles


@pytest.mark.asyncio
async def test_social_menu_separates_old_case_tracking_from_new_issue_permission():
    """An older open case must not make a fresh booking look reportable."""
    class Identity:
        async def live_bookings(self, _thread):
            return [{"number": "BK-2", "service": "AC install", "status": "Assigned"}]

        async def cancel_options(self, _thread, _booking_number):
            return {"can_cancel": True}

        async def complaint_cases(self, _thread):
            return [{"id": str(uuid.uuid4()), "status": "awaiting_provider"}]

        async def complaint_bookings(self, _thread):
            return []

        async def warranty_menu_available(self, _thread):
            return False

    thread = SimpleNamespace(customer_id=uuid.uuid4(), id=uuid.uuid4())
    turn = await flow._booked_menu_for(Identity(), thread, "BK-2", "Booked")
    rows = {row["title"]: row["id"] for row in turn.picker["rows"]}
    assert rows[flow.TRACK_COMPLAINT_ROW] == "cmp|cases"
    assert flow.REPORT_ISSUE_ROW not in rows


@pytest.mark.asyncio
async def test_new_booking_menu_cannot_inherit_old_complaint_or_warranty():
    """A prior completed job must not advertise remedies for today's booking."""
    class Identity:
        async def live_bookings(self, _thread):
            return [{"number": "BK-NEW", "service": "AC repair", "status": "Assigned"}]

        async def cancel_options(self, _thread, _number):
            return {"can_cancel": True}

        async def complaint_cases(self, _thread):
            return []

        async def complaint_bookings(self, _thread):
            return [{"booking_number": "BK-OLD", "status": "completed"}]

        async def warranty_menu_available(self, _thread, booking_number=None):
            return booking_number in (None, "BK-OLD")

    thread = SimpleNamespace(customer_id=uuid.uuid4(), id=uuid.uuid4())
    for booking_number in ("", "BK-NEW"):
        turn = await flow._booked_menu_for(
            Identity(), thread, booking_number, "Booking confirmed")
        titles = {row["title"] for row in turn.picker["rows"]}
        assert flow.TRACK_ROW in titles
        assert flow.REPORT_ISSUE_ROW not in titles
        assert flow.WARRANTY_ROW not in titles


@pytest.mark.asyncio
async def test_issue_appears_for_inspected_booking_and_warranty_only_for_completed_one():
    class Identity:
        async def live_bookings(self, _thread):
            return [{"number": "BK-ACTIVE", "service": "AC repair", "status": "Inspection started"}]

        async def cancel_options(self, _thread, _number):
            return {"can_cancel": False}

        async def complaint_cases(self, _thread):
            return []

        async def complaint_bookings(self, _thread):
            return [{"booking_number": "BK-ACTIVE", "status": "inspection_started"}]

        async def warranty_menu_available(self, _thread, booking_number=None):
            return booking_number == "BK-COMPLETE"

    thread = SimpleNamespace(customer_id=uuid.uuid4(), id=uuid.uuid4())
    active = await flow._booked_menu_for(
        Identity(), thread, "BK-ACTIVE", "Inspection started")
    active_titles = {row["title"] for row in active.picker["rows"]}
    assert flow.REPORT_ISSUE_ROW in active_titles
    assert flow.WARRANTY_ROW not in active_titles

    completed = await flow._booked_menu_for(
        Identity(), thread, "BK-COMPLETE", "Job completed")
    completed_titles = {row["title"] for row in completed.picker["rows"]}
    assert flow.REPORT_ISSUE_ROW not in completed_titles
    assert flow.WARRANTY_ROW in completed_titles


@pytest.mark.asyncio
async def test_instagram_issue_catalog_requires_verified_on_site_arrival():
    from app.engines.messaging_gateway.service import MessagingGatewayService

    booking = SimpleNamespace(id=uuid.uuid4())
    job = SimpleNamespace(status="inspection_started", arrival_verified_at=None)
    booking_rows = MagicMock()
    booking_rows.scalars.return_value.all.return_value = [booking]
    job_rows = MagicMock()
    job_rows.scalars.return_value.first.return_value = job
    service = MessagingGatewayService.__new__(MessagingGatewayService)
    service.db = MagicMock()
    service.db.execute = AsyncMock(side_effect=[booking_rows, job_rows])

    assert await service.complaint_bookings(
        SimpleNamespace(customer_id=uuid.uuid4())) == []
    assert service.db.execute.await_count == 2


@pytest.mark.asyncio
async def test_confirmed_booking_number_is_carried_into_its_action_menu(monkeypatch):
    from app.engines.messaging_gateway import addons

    monkeypatch.setattr(addons, "needs_review", lambda _draft: False)
    executor = SimpleNamespace(
        customer_id=uuid.uuid4(),
        _tool_confirm_home_service_booking=AsyncMock(return_value={
            "confirmed": True, "booking_number": "BK-JUST-BOOKED",
        }),
    )
    thread = SimpleNamespace(customer_id=None)
    note, page, menu_draft = await flow._confirm(
        None, thread, executor, {"id": "draft-1", "status": "collecting"})
    assert page == flow.BOOKED
    assert "BK-JUST-BOOKED" in note
    assert menu_draft["_confirmed_booking_number"] == "BK-JUST-BOOKED"
    assert thread.customer_id == executor.customer_id


@pytest.mark.asyncio
async def test_warranty_menu_matches_the_completed_booking_not_an_older_claim():
    from app.engines.messaging_gateway.service import MessagingGatewayService

    service = MessagingGatewayService.__new__(MessagingGatewayService)
    service.warranty_cases = AsyncMock(return_value=[
        {"booking_number": "BK-OLD", "claim_id": "claim-1"},
    ])
    service.warranty_jobs = AsyncMock(return_value=[
        {"booking_number": "BK-OLD", "job_id": "job-1"},
    ])
    thread = SimpleNamespace(customer_id=uuid.uuid4())
    assert not await service.warranty_menu_available(thread, "BK-NEW")
    assert await service.warranty_menu_available(thread, "BK-OLD")


def test_completed_service_uses_warranty_for_quality_but_keeps_incident_types():
    booking = _booking() | {
        "complaint_types": ["technician_behavior", "property_damage"],
    }
    turn = flow._complaint_type_turn(booking, CHANNEL_INSTAGRAM)
    ids = {row["id"] for row in turn.picker["rows"]}
    assert "cmp|type|service_quality" not in ids
    assert "cmp|type|technician_behavior" in ids
    assert "cmp|type|property_damage" in ids


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
async def test_work_done_quality_problem_is_still_a_complaint():
    """`work_done` is the technician saying they are finished, not closure.

    Treating it as "completed" sent the customer to warranty, which only
    opens at `completed` and refused them too -- a customer who saw the
    problem while the technician was still there had nowhere to report it.
    """
    from app.engines.complaints.eligibility_service import ComplaintEligibilityService

    customer_id = uuid.uuid4()
    service = ComplaintEligibilityService()
    service._fetch_record = AsyncMock(return_value=SimpleNamespace(
        status="work_done", customer_id=customer_id,
        created_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc),
    ))
    service._home_service_work_started = AsyncMock(return_value=True)
    service._customer_owns_record = AsyncMock(return_value=True)
    service.get_complaint_policy = AsyncMock(return_value=None)
    service.check_duplicate_open_complaint = AsyncMock(return_value=False)

    result = await service.check_eligible(
        AsyncMock(), customer_id, "service_job", uuid.uuid4(),
        complaint_type="service_quality",
    )
    assert result["eligible"] is True


@pytest.mark.asyncio
@pytest.mark.parametrize("status", ["completed", "invoice_issued", "paid"])
async def test_completed_quality_problem_is_warranty_not_complaint(status):
    from app.engines.complaints.constants import ERR_COMPLAINT_TYPE_NOT_SUPPORTED
    from app.engines.complaints.eligibility_service import ComplaintEligibilityService

    customer_id = uuid.uuid4()
    service = ComplaintEligibilityService()
    service._fetch_record = AsyncMock(return_value=SimpleNamespace(
        status=status, customer_id=customer_id,
        created_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc),
    ))
    service._home_service_work_started = AsyncMock(return_value=True)
    service._customer_owns_record = AsyncMock(return_value=True)

    result = await service.check_eligible(
        AsyncMock(), customer_id, "service_job", uuid.uuid4(),
        complaint_type="service_quality",
    )
    assert result["eligible"] is False
    assert result["reason_code"] == ERR_COMPLAINT_TYPE_NOT_SUPPORTED
    assert "warranty" in result["reason"].lower()


@pytest.mark.asyncio
async def test_warranty_support_collects_issue_type_then_description():
    class WarrantyIdentity:
        def __init__(self):
            self.state = None

        async def warranty_jobs(self, _thread):
            return [{
                "job_id": str(uuid.uuid4()),
                "booking_id": str(uuid.uuid4()),
                "booking_number": "BK-20260913-000009",
                "service": "AC repair",
                "problem": "AC not cooling",
                "warranty_expires_at": "2026-09-18T12:00:00+00:00",
            }]

        async def begin_social_warranty(self, _thread, job, claim_type=None):
            self.state = {"mode": "new", **job}
            if claim_type:
                self.state["claim_type"] = claim_type
            return self.state

        async def social_warranty_state(self, _thread):
            return self.state

    identity = WarrantyIdentity()
    thread = SimpleNamespace(customer_id=uuid.uuid4(), id=uuid.uuid4())
    choose_type = await flow._warranty_step(
        thread, identity, "new", CHANNEL_INSTAGRAM,
    )
    ids = {row["id"] for row in choose_type.picker["rows"]}
    assert "wty|type|problem_returned" in ids
    assert "wty|type|service_not_working" in ids
    assert "wty|type|workmanship_issue" in ids

    describe = await flow._warranty_step(
        thread, identity, "type|problem_returned", CHANNEL_INSTAGRAM,
    )
    assert describe.picker["allow_text"] is True
    assert [row["id"] for row in describe.picker["rows"]] == ["wty|cancel"]
    assert "next message" in describe.picker["body"].lower()
    assert identity.state["claim_type"] == "problem_returned"


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
