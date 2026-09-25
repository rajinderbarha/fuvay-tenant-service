from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest


class _Scalars:
    def __init__(self, value):
        self.value = value

    def scalars(self):
        return self

    def first(self):
        return self.value


def _pending_request():
    now = datetime.now(timezone.utc)
    return SimpleNamespace(
        id=uuid.uuid4(), booking_id=uuid.uuid4(), job_id=uuid.uuid4(),
        tenant_id=uuid.uuid4(), request_source="provider", status="pending",
        original_date="2026-09-25", original_slot="09:00-11:00",
        requested_date="2026-09-26", requested_slot="11:00-13:00",
        reason="Technician availability changed", expires_at=now + timedelta(hours=2),
        notification_sent_at=None, resolved_at=None, resolved_by=None,
        rejection_reason=None,
    )


@pytest.mark.asyncio
async def test_existing_committed_slot_creates_approval_instead_of_mutating(monkeypatch):
    from app.engines.home_service_assignment import provider_reschedule_service as approval
    from app.engines.home_service_assignment.service import HomeServiceJobAssignmentService

    tenant_id = uuid.uuid4()
    job = SimpleNamespace(
        id=uuid.uuid4(), tenant_id=tenant_id, status="scheduled",
        scheduled_date=date(2026, 9, 25), scheduled_time_window="09:00-11:00",
    )
    db = SimpleNamespace()
    service = HomeServiceJobAssignmentService(db)
    monkeypatch.setattr(service, "_load_job", AsyncMock(return_value=job))
    create = AsyncMock(return_value={
        "request_id": str(uuid.uuid4()), "status": "pending_customer_approval",
    })
    monkeypatch.setattr(approval, "create_request", create)

    result = await service.schedule_job(
        job_id=job.id, tenant_id=tenant_id,
        scheduled_date=date(2026, 9, 26),
        scheduled_time_window="11:00-13:00",
        reason="Technician availability changed",
    )

    assert result["status"] == "pending_customer_approval"
    assert job.scheduled_date == date(2026, 9, 25)
    assert job.scheduled_time_window == "09:00-11:00"
    create.assert_awaited_once()


@pytest.mark.asyncio
async def test_successful_delivery_retry_does_not_send_duplicate_instagram_prompt(monkeypatch):
    from app.engines.home_service_assignment import provider_reschedule_service as svc

    request = _pending_request()
    request.notification_sent_at = datetime.now(timezone.utc)
    db = SimpleNamespace(get=AsyncMock(return_value=request), flush=AsyncMock())
    send = AsyncMock(return_value=True)
    monkeypatch.setattr(
        "app.engines.messaging_gateway.booking_updates.send_reschedule_approval_request",
        send,
    )

    assert await svc.deliver_request(db, request.id) is True
    send.assert_not_awaited()


@pytest.mark.asyncio
async def test_reject_keeps_original_slot_and_audits_customer_decision(monkeypatch):
    from app.engines.home_service_assignment import provider_reschedule_service as svc

    request = _pending_request()
    customer_id = uuid.uuid4()
    booking = SimpleNamespace(id=request.booking_id, customer_id=customer_id)
    job = SimpleNamespace(
        id=request.job_id, booking_id=request.booking_id, tenant_id=request.tenant_id,
        job_number="JOB-1", scheduled_date=date(2026, 9, 25),
        scheduled_time_window="09:00-11:00",
    )
    db = SimpleNamespace(
        execute=AsyncMock(side_effect=[_Scalars(request), _Scalars(job)]),
        get=AsyncMock(return_value=booking), add=MagicMock(), flush=AsyncMock(),
    )
    notify = AsyncMock()
    monkeypatch.setattr(svc, "_notify_provider_decision", notify)

    result = await svc.decide_request(
        db, request_id=request.id, customer_id=customer_id,
        decision="reject", actor_user_id=customer_id,
    )

    assert result["status"] == "rejected"
    assert job.scheduled_date == date(2026, 9, 25)
    assert job.scheduled_time_window == "09:00-11:00"
    event = db.add.call_args.args[0]
    assert event.event_type == "provider_reschedule_rejected"
    notify.assert_awaited_once_with(db, job, request, approved=False)


@pytest.mark.asyncio
async def test_approval_rechecks_capacity_then_resets_visit_timers(monkeypatch):
    from app.engines.home_service_assignment import provider_reschedule_service as svc

    request = _pending_request()
    customer_id = uuid.uuid4()
    booking = SimpleNamespace(
        id=request.booking_id, customer_id=customer_id,
        preferred_date=date(2026, 9, 25), preferred_time_window="09:00-11:00",
        status="accepted",
    )
    job = SimpleNamespace(
        id=request.job_id, booking_id=request.booking_id, tenant_id=request.tenant_id,
        job_number="JOB-1", offering_id=uuid.uuid4(), job_type_id=uuid.uuid4(),
        scheduled_date=date(2026, 9, 25), scheduled_time_window="09:00-11:00",
        status="accepted", reschedule_count=0,
        reminder_24h_sent_at=datetime.now(timezone.utc),
        reminder_1h_sent_at=datetime.now(timezone.utc),
        provider_reminder_30m_sent_at=datetime.now(timezone.utc),
        staff_reminder_30m_sent_at=datetime.now(timezone.utc),
        arrival_verified_at=datetime.now(timezone.utc), arrival_distance_meters=10,
        sla_stopped_at=datetime.now(timezone.utc),
    )
    assignment = SimpleNamespace(
        id=uuid.uuid4(), scheduled_date=job.scheduled_date,
        scheduled_time_window=job.scheduled_time_window,
    )
    db = SimpleNamespace(
        execute=AsyncMock(side_effect=[
            _Scalars(request), _Scalars(job), _Scalars(assignment),
        ]),
        get=AsyncMock(return_value=booking), add=MagicMock(), flush=AsyncMock(),
    )
    capacity = AsyncMock(return_value=True)
    monkeypatch.setattr(svc, "_capacity_available", capacity)
    monkeypatch.setattr(
        "app.engines.vertical_monetization.runtime_operations."
        "get_home_services_operations_policy",
        AsyncMock(return_value=SimpleNamespace(customer_reschedule_limit=3)),
    )
    stamp = AsyncMock()
    monkeypatch.setattr("app.engines.execution.sla_breach_service.stamp_due_at", stamp)
    monkeypatch.setattr(svc, "_notify_provider_decision", AsyncMock())

    result = await svc.decide_request(
        db, request_id=request.id, customer_id=customer_id,
        decision="approve", actor_user_id=customer_id,
    )

    assert result["status"] == "approved"
    assert job.scheduled_date == date(2026, 9, 26)
    assert job.scheduled_time_window == "11:00-13:00"
    assert job.status == booking.status == "scheduled"
    assert job.reschedule_count == 1
    assert assignment.scheduled_date == date(2026, 9, 26)
    assert job.reminder_24h_sent_at is None
    assert job.provider_reminder_30m_sent_at is None
    assert job.arrival_verified_at is None
    capacity.assert_awaited_once()
    stamp.assert_awaited_once_with(db, job.id)
    event = db.add.call_args.args[0]
    assert event.event_type == "provider_reschedule_approved"


@pytest.mark.asyncio
async def test_full_slot_at_approval_never_changes_original_visit(monkeypatch):
    from app.engines.home_service_assignment import provider_reschedule_service as svc

    request = _pending_request()
    customer_id = uuid.uuid4()
    booking = SimpleNamespace(id=request.booking_id, customer_id=customer_id)
    job = SimpleNamespace(
        id=request.job_id, booking_id=request.booking_id, tenant_id=request.tenant_id,
        job_number="JOB-1", offering_id=uuid.uuid4(), job_type_id=uuid.uuid4(),
        scheduled_date=date(2026, 9, 25), scheduled_time_window="09:00-11:00",
    )
    db = SimpleNamespace(
        execute=AsyncMock(side_effect=[_Scalars(request), _Scalars(job)]),
        get=AsyncMock(return_value=booking), add=MagicMock(), flush=AsyncMock(),
    )
    monkeypatch.setattr(svc, "_capacity_available", AsyncMock(return_value=False))
    monkeypatch.setattr(svc, "_notify_provider_decision", AsyncMock())

    result = await svc.decide_request(
        db, request_id=request.id, customer_id=customer_id,
        decision="approve", actor_user_id=customer_id,
    )

    assert result["status"] == "slot_unavailable"
    assert request.status == "expired"
    assert job.scheduled_date == date(2026, 9, 25)
    assert job.scheduled_time_window == "09:00-11:00"


@pytest.mark.asyncio
async def test_instagram_prompt_has_explicit_approve_and_keep_buttons(monkeypatch):
    from app.engines.messaging_gateway import booking_updates

    request = _pending_request()
    booking = SimpleNamespace(id=request.booking_id, booking_number="BK-1")
    job = SimpleNamespace(id=request.job_id, booking_id=request.booking_id)
    db = SimpleNamespace(get=AsyncMock(return_value=booking))
    notify = AsyncMock(return_value=True)
    monkeypatch.setattr(booking_updates, "notify_booking_customer", notify)

    assert await booking_updates.send_reschedule_approval_request(db, job, request)
    rows = notify.await_args.kwargs["rows"]
    assert rows == [
        {"id": f"rsc|{request.id}|approve", "title": "Approve new slot"},
        {"id": f"rsc|{request.id}|reject", "title": "Keep current slot"},
    ]
    assert "current slot stays confirmed" in notify.await_args.args[2].lower()


@pytest.mark.asyncio
async def test_track_flow_surfaces_pending_slot_approval_before_status():
    from app.engines.messaging_gateway import flow

    request_id = str(uuid.uuid4())
    identity = SimpleNamespace(pending_provider_reschedules=AsyncMock(return_value=[{
        "request_id": request_id, "booking_number": "BK-1",
        "original_date": "2026-09-25", "original_time_window": "09:00-11:00",
        "requested_date": "2026-09-26", "requested_time_window": "11:00-13:00",
        "reason": "Technician availability changed",
    }]))
    turn = await flow._reschedule_step(
        identity, SimpleNamespace(), "instagram", "BK-1",
    )

    assert "Current: 2026-09-25" in turn.text
    assert [row["id"] for row in turn.picker["rows"]] == [
        f"rsc|{request_id}|approve", f"rsc|{request_id}|reject",
    ]
