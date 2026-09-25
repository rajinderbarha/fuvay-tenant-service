from __future__ import annotations

import uuid
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.mark.asyncio
async def test_arrival_prompt_uses_customer_buttons_and_never_exposes_the_code():
    from app.engines.messaging_gateway import flow

    challenge_id = str(uuid.uuid4())
    identity = SimpleNamespace(pending_arrivals=AsyncMock(return_value=[{
        "challenge_id": challenge_id,
        "job_number": "JOB-1",
        "booking_number": "BK-1",
        "expires_at": "2026-09-25T10:00:00+00:00",
    }]))
    turn = await flow._arrival_step(
        identity, SimpleNamespace(id=uuid.uuid4()), "instagram",
    )

    assert "BK-1" in turn.text
    assert "one-time" not in turn.text.lower()
    assert [row["id"] for row in turn.picker["rows"]] == [
        f"arr|{challenge_id}|confirm", f"arr|{challenge_id}|deny",
    ]


@pytest.mark.asyncio
async def test_second_customer_denial_closes_and_penalises(monkeypatch):
    from app.engines.execution import arrival_confirmation_service as arrival

    policy = SimpleNamespace(
        false_arrival_auto_close=True,
        false_arrival_penalty_amount=Decimal("150.00"),
        arrival_denial_limit=2,
    )
    monkeypatch.setattr(
        "app.engines.vertical_monetization.runtime_operations."
        "get_home_services_operations_policy",
        AsyncMock(return_value=policy),
    )
    charge = AsyncMock(return_value=Decimal("150.00"))
    close = AsyncMock()
    health = AsyncMock()
    monkeypatch.setattr(
        "app.engines.execution.sla_breach_service._charge_penalty", charge,
    )
    monkeypatch.setattr(
        "app.engines.execution.sla_breach_service._close_breached_job", close,
    )
    monkeypatch.setattr(
        "app.engines.tenant_engine.health.refresh_provider_operational_health",
        health,
    )
    db = SimpleNamespace(execute=AsyncMock(), add=MagicMock())
    job = SimpleNamespace(
        id=uuid.uuid4(), booking_id=uuid.uuid4(), tenant_id=uuid.uuid4(),
        assigned_staff_id=uuid.uuid4(), status="on_the_way",
        assignment_status="assigned", failure_reason=None,
    )

    closed = await arrival._close_repeated_denied_arrival(
        db, job=job, denial_count=2,
    )

    assert closed is True
    assert job.status == "cancelled"
    assert job.failure_reason.startswith("Visit closed")
    charge.assert_awaited_once()
    close.assert_awaited_once()
    health.assert_awaited_once_with(db, job.tenant_id)
    event = db.add.call_args.args[0]
    assert event.event_type == "repeated_arrival_denial_closed"
    assert event.event_metadata["penalty_amount"] == 150.0


@pytest.mark.asyncio
async def test_first_customer_denial_is_an_escalation_not_an_auto_penalty(monkeypatch):
    from app.engines.execution import arrival_confirmation_service as arrival

    db = SimpleNamespace(execute=AsyncMock(), add=MagicMock())
    job = SimpleNamespace(id=uuid.uuid4())
    monkeypatch.setattr(
        "app.engines.vertical_monetization.runtime_operations."
        "get_home_services_operations_policy",
        AsyncMock(return_value=SimpleNamespace(arrival_denial_limit=2)),
    )
    assert await arrival._close_repeated_denied_arrival(
        db, job=job, denial_count=1,
    ) is False
    db.execute.assert_not_awaited()
    db.add.assert_not_called()


def test_arrival_controls_have_safe_runtime_defaults():
    from app.engines.vertical_monetization.runtime_operations import (
        HomeServicesOperationsPolicy,
    )

    policy = HomeServicesOperationsPolicy()
    assert policy.arrival_customer_confirmation_enabled is True
    assert policy.arrival_challenge_ttl_minutes == 10
    assert policy.arrival_code_max_attempts == 5
    assert policy.arrival_denial_limit == 2
    assert policy.job_stall_critical_multiplier == 2
