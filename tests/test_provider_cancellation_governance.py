from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.engines.vertical_monetization.policy_service import VerticalMonetizationPolicyService


def _result(first=None):
    result = MagicMock()
    result.scalars.return_value.first.return_value = first
    return result


def _pending_request():
    now = datetime.now(timezone.utc)
    return SimpleNamespace(
        id=uuid.uuid4(), job_id=uuid.uuid4(), booking_id=uuid.uuid4(),
        tenant_id=uuid.uuid4(), customer_id=uuid.uuid4(),
        requested_by_user_id=uuid.uuid4(), reason_code="customer_requested",
        reason_label="Customer requested cancellation", reason_snapshot={},
        provider_notes=None, call_attempt_count=1, status="pending",
        requested_at=now, expires_at=now + timedelta(minutes=15),
        notification_sent_at=None, resolved_by=None, resolved_at=None,
        rejection_reason=None,
    )


def test_admin_policy_rejects_unverified_customer_cancellation():
    errors = VerticalMonetizationPolicyService()._validate({
        "provider_model": "NONE", "customer_fee_model": "NONE",
        "provider_cancellation_reasons": [{
            "code": "customer_requested", "label": "Customer requested cancellation",
            "outcome": "provider_cancel", "responsibility": "customer",
            "active": True, "requires_note": False,
            "minimum_call_attempts": 1, "health_impact": False,
        }],
    })
    assert any("requires customer confirmation" in error for error in errors)


@pytest.mark.asyncio
async def test_provider_owned_reason_cancels_immediately_with_audit_metadata(monkeypatch):
    from app.engines.execution import provider_cancellation_service as service

    tenant_id = uuid.uuid4()
    job = SimpleNamespace(
        id=uuid.uuid4(), booking_id=uuid.uuid4(), tenant_id=tenant_id,
        status="assigned", assigned_staff_id=None,
    )
    db = MagicMock()
    db.execute = AsyncMock(return_value=_result(job))
    db.scalar = AsyncMock(return_value=0)
    rule = {
        "code": "no_technician", "label": "No technician available",
        "outcome": "provider_cancel", "responsibility": "provider",
        "active": True, "requires_note": False, "minimum_call_attempts": 0,
        "health_impact": True,
    }
    monkeypatch.setattr(service, "cancellation_policy", AsyncMock(return_value={
        "confirmation_minutes": 15, "minimum_note_length": 10, "reasons": [rule],
    }))
    cancel = AsyncMock(return_value={"id": str(job.id), "status": "cancelled"})

    with patch(
        "app.engines.execution.home_service_service.HomeServiceJobExecutionService.cancel_job",
        cancel,
    ):
        outcome = await service.initiate(
            db, job_id=job.id, tenant_id=tenant_id, actor_user_id=uuid.uuid4(),
            reason_code="no_technician", notes=None,
        )

    assert outcome["status"] == "cancelled"
    assert cancel.await_args.kwargs["actor_role"] == "provider"
    assert cancel.await_args.kwargs["notify_customer"] is False
    assert cancel.await_args.kwargs["metadata"]["reason_code"] == "no_technician"
    assert cancel.await_args.kwargs["metadata"]["health_impact"] is True


@pytest.mark.asyncio
async def test_customer_reason_stays_pending_and_does_not_cancel(monkeypatch):
    from app.engines.execution import provider_cancellation_service as service
    from app.engines.execution.models import ServiceJobCancellationRequest

    tenant_id = uuid.uuid4()
    customer_id = uuid.uuid4()
    job = SimpleNamespace(
        id=uuid.uuid4(), booking_id=uuid.uuid4(), tenant_id=tenant_id,
        status="assigned", assigned_staff_id=None,
    )
    booking = SimpleNamespace(
        id=job.booking_id, customer_id=customer_id, booking_number="BK-100",
    )
    db = MagicMock()
    db.execute = AsyncMock(side_effect=[_result(job), _result(None)])
    db.scalar = AsyncMock(return_value=1)
    db.get = AsyncMock(return_value=booking)
    db.add = MagicMock()

    async def flush():
        for call in db.add.call_args_list:
            row = call.args[0]
            if isinstance(row, ServiceJobCancellationRequest) and row.id is None:
                row.id = uuid.uuid4()
    db.flush = AsyncMock(side_effect=flush)
    rule = {
        "code": "customer_requested", "label": "Customer requested cancellation",
        "outcome": "customer_confirmation", "responsibility": "customer",
        "active": True, "requires_note": False, "minimum_call_attempts": 1,
        "health_impact": False,
    }
    monkeypatch.setattr(service, "cancellation_policy", AsyncMock(return_value={
        "confirmation_minutes": 15, "minimum_note_length": 10, "reasons": [rule],
    }))
    cancel = AsyncMock()

    with patch(
        "app.engines.execution.home_service_service.HomeServiceJobExecutionService.cancel_job",
        cancel,
    ):
        outcome = await service.initiate(
            db, job_id=job.id, tenant_id=tenant_id, actor_user_id=uuid.uuid4(),
            reason_code="customer_requested", notes=None,
        )

    assert outcome["status"] == "pending_customer_confirmation"
    assert outcome["call_attempt_count"] == 1
    cancel.assert_not_awaited()
    assert any(
        getattr(call.args[0], "event_type", None)
        == "provider_cancellation_confirmation_requested"
        for call in db.add.call_args_list
    )


@pytest.mark.asyncio
async def test_customer_reason_requires_configured_call_attempts(monkeypatch):
    from app.engines.execution import provider_cancellation_service as service
    from app.exceptions import ServiceOSException

    job = SimpleNamespace(
        id=uuid.uuid4(), booking_id=uuid.uuid4(), tenant_id=uuid.uuid4(),
        status="assigned", assigned_staff_id=None,
    )
    db = MagicMock()
    db.execute = AsyncMock(return_value=_result(job))
    db.scalar = AsyncMock(return_value=1)
    monkeypatch.setattr(service, "cancellation_policy", AsyncMock(return_value={
        "confirmation_minutes": 15, "minimum_note_length": 10,
        "reasons": [{
            "code": "customer_unreachable", "label": "Customer unreachable",
            "outcome": "customer_confirmation", "responsibility": "customer",
            "active": True, "requires_note": False, "minimum_call_attempts": 2,
            "health_impact": False,
        }],
    }))

    with pytest.raises(ServiceOSException) as exc:
        await service.initiate(
            db, job_id=job.id, tenant_id=job.tenant_id,
            actor_user_id=uuid.uuid4(), reason_code="customer_unreachable", notes=None,
        )
    assert exc.value.error_code == "CANCELLATION_CALL_ATTEMPTS_REQUIRED"


@pytest.mark.asyncio
async def test_customer_rejection_keeps_job_open_and_audits_decision(monkeypatch):
    from app.engines.execution import provider_cancellation_service as service

    request = _pending_request()
    booking = SimpleNamespace(id=request.booking_id, customer_id=request.customer_id)
    job = SimpleNamespace(
        id=request.job_id, booking_id=request.booking_id,
        tenant_id=request.tenant_id, assigned_staff_id=None,
        status="assigned", job_number="JOB-1",
    )
    db = SimpleNamespace(
        execute=AsyncMock(return_value=_result(request)),
        get=AsyncMock(side_effect=[job, booking]), add=MagicMock(), flush=AsyncMock(),
    )
    notify = AsyncMock()
    monkeypatch.setattr(service, "_notify_provider_decision", notify)

    result = await service.decide_request(
        db, request_id=request.id, customer_id=request.customer_id,
        decision="reject", actor_user_id=request.customer_id,
    )

    assert result["status"] == "rejected"
    assert job.status == "assigned"
    event = db.add.call_args.args[0]
    assert event.event_type == "provider_cancellation_rejected"
    notify.assert_awaited_once_with(db, job, request, approved=False)


@pytest.mark.asyncio
async def test_customer_approval_uses_customer_responsibility_without_health_hit(monkeypatch):
    from app.engines.execution import provider_cancellation_service as service

    request = _pending_request()
    booking = SimpleNamespace(id=request.booking_id, customer_id=request.customer_id)
    job = SimpleNamespace(
        id=request.job_id, booking_id=request.booking_id,
        tenant_id=request.tenant_id, assigned_staff_id=None,
        status="assigned", job_number="JOB-1",
    )
    db = SimpleNamespace(
        execute=AsyncMock(return_value=_result(request)),
        get=AsyncMock(side_effect=[job, booking]), add=MagicMock(), flush=AsyncMock(),
    )
    notify = AsyncMock()
    monkeypatch.setattr(service, "_notify_provider_decision", notify)
    cancel = AsyncMock(return_value={"id": str(job.id), "status": "cancelled"})

    with patch(
        "app.engines.execution.home_service_service.HomeServiceJobExecutionService.cancel_job",
        cancel,
    ):
        result = await service.decide_request(
            db, request_id=request.id, customer_id=request.customer_id,
            decision="approve", actor_user_id=request.customer_id,
        )

    assert result["status"] == "approved"
    kwargs = cancel.await_args.kwargs
    assert kwargs["actor_role"] == "customer"
    assert kwargs["notify_customer"] is False
    assert kwargs["metadata"]["customer_confirmed"] is True
    assert kwargs["metadata"]["health_impact"] is False
    notify.assert_awaited_once_with(db, job, request, approved=True)


@pytest.mark.asyncio
async def test_instagram_prompt_has_confirm_and_keep_buttons(monkeypatch):
    from app.engines.messaging_gateway import booking_updates

    request = _pending_request()
    booking = SimpleNamespace(id=request.booking_id, booking_number="BK-1")
    job = SimpleNamespace(id=request.job_id, booking_id=request.booking_id)
    db = SimpleNamespace(get=AsyncMock(return_value=booking))
    notify = AsyncMock(return_value=True)
    monkeypatch.setattr(booking_updates, "notify_booking_customer", notify)

    assert await booking_updates.send_provider_cancellation_confirmation_request(
        db, job, request,
    )
    rows = notify.await_args.kwargs["rows"]
    assert rows == [
        {"id": f"pcx|{request.id}|approve", "title": "Yes, cancel booking"},
        {"id": f"pcx|{request.id}|reject", "title": "No, keep booking"},
    ]
    assert "sla remain active" in notify.await_args.args[2].lower()
