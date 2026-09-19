from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.engines.execution import stage_timer_service as timers


def _job(status="on_the_way"):
    now = datetime.now(timezone.utc)
    return SimpleNamespace(
        id=uuid.uuid4(), tenant_id=uuid.uuid4(), status=status,
        created_at=now, updated_at=now,
    )


@pytest.mark.asyncio
async def test_travel_timer_snapshots_the_provider_buffer():
    result = MagicMock()
    result.scalar.return_value = 55
    db = SimpleNamespace(execute=AsyncMock(return_value=result))
    entered = datetime(2026, 9, 19, 10, 0, tzinfo=timezone.utc)

    timer = await timers.build_stage_timer_snapshot(
        db, _job(), "on_the_way", entered_at=entered,
    )

    assert timer["source"] == "provider_travel_buffer"
    assert timer["limit_minutes"] == 55
    assert timer["deadline_at"] == (entered + timedelta(minutes=55)).isoformat()


@pytest.mark.asyncio
async def test_a_snapshot_keeps_the_original_deadline_when_policy_changes(monkeypatch):
    entered = datetime(2026, 9, 19, 10, 0, tzinfo=timezone.utc)
    snapshot = {
        "status": "service_started", "entered_at": entered.isoformat(),
        "warning_at": (entered + timedelta(minutes=60)).isoformat(),
        "deadline_at": (entered + timedelta(minutes=80)).isoformat(),
        "critical_at": (entered + timedelta(minutes=160)).isoformat(),
        "limit_minutes": 80, "waiting_on": "provider", "source": "platform_policy",
    }
    event = SimpleNamespace(
        created_at=entered, event_metadata={"stage_timer": snapshot},
    )
    scalars = MagicMock()
    scalars.first.return_value = event
    result = MagicMock()
    result.scalars.return_value = scalars
    db = SimpleNamespace(execute=AsyncMock(return_value=result))

    async def changed_rule(*_args):
        return 10, "platform_policy"

    monkeypatch.setattr(timers, "_stage_rule", changed_rule)
    timer = await timers.describe_stage_timer(
        db, _job("service_started"), now=entered + timedelta(minutes=90),
    )

    assert timer["limit_minutes"] == 80
    assert timer["state"] == "breached"
    assert timer["overdue_seconds"] == 600


@pytest.mark.asyncio
async def test_terminal_stage_has_no_timer():
    db = SimpleNamespace(execute=AsyncMock())
    timer = await timers.describe_stage_timer(db, _job("completed"))
    assert timer["active"] is False
    assert timer["state"] == "inactive"
    db.execute.assert_not_awaited()
