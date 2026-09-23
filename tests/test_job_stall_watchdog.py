"""A job that stops moving after the technician arrives must not go unnoticed.

Until this sweep existed, `reached_site` onwards had NO timer of any kind:

  * `provider_assignment_timeout` only looks at jobs with no technician
    assigned (TECHNICIAN_ASSIGNMENT_PENDING_STATUSES).
  * `sla_breach` only looks at BREACHABLE_STATUSES, which stops at
    `on_the_way`, and only while `arrival_verified_at IS NULL`.

Confirmed against live staging data on 2026-09-18: three jobs were sitting in
`reached_site` (3.8 days), `service_started` (3.8 days) and `work_done`
(2.7 days) with nothing watching any of them.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.jobs import job_stall_watchdog as watchdog


def _job(status, *, entered_minutes_ago, warned_at=None):
    now = datetime.now(timezone.utc)
    return SimpleNamespace(
        id=uuid.uuid4(), tenant_id=uuid.uuid4(), booking_id=uuid.uuid4(),
        job_number="JOB-TEST-0001", status=status,
        entered_at=now - timedelta(minutes=entered_minutes_ago),
        warned_at=warned_at,
    )


def _db(rows):
    db = MagicMock()
    added: list = []

    async def execute(*_a, **_kw):
        result = MagicMock()
        result.fetchall.return_value = rows
        # `_notify_provider` looks up the tenant owner through the same method.
        result.scalar.return_value = uuid.uuid4()
        return result

    db.execute = AsyncMock(side_effect=execute)
    db.flush = AsyncMock()
    db.add = MagicMock(side_effect=added.append)
    db.added = added
    return db


@pytest.fixture
def policy(monkeypatch):
    stub = SimpleNamespace(job_stall_watchdog_enabled=True)

    async def _policy(_db):
        return stub

    monkeypatch.setattr(
        "app.engines.vertical_monetization.runtime_operations."
        "get_home_services_operations_policy", _policy,
    )
    async def _no_stage_penalty(*_args, **_kwargs):
        return {"eligible": True, "penalised": False, "closed": False}

    monkeypatch.setattr(
        "app.engines.execution.sla_breach_service.enforce_stalled_provider_stage",
        _no_stage_penalty,
    )
    return stub


# ── coverage ─────────────────────────────────────────────────────────────────

def test_watches_every_status_no_other_timer_covers():
    """The gap this exists to close. `sla_breach` stops at on_the_way and
    `provider_assignment_timeout` needs an unassigned job."""
    from app.engines.execution.sla_breach_service import BREACHABLE_STATUSES
    from app.engines.home_service_assignment.assignment_deadlines import (
        TECHNICIAN_ASSIGNMENT_PENDING_STATUSES,
    )

    covered_elsewhere = set(BREACHABLE_STATUSES) | set(TECHNICIAN_ASSIGNMENT_PENDING_STATUSES)
    for status in ("reached_site", "inspection_started", "inspection_done",
                   "quote_required", "service_started", "work_done",
                   "customer_not_available"):
        assert status not in covered_elsewhere, (
            f"{status} is covered elsewhere -- this sweep would double-alert"
        )
        assert status in watchdog.STALL_LIMIT_MINUTES


def test_travel_is_left_to_the_travel_timeout_sweep():
    """`travel_timeout` cancels an overdue journey at the buffer deadline. A
    stall alert here would race it at that same deadline."""
    assert "on_the_way" not in watchdog.STALL_LIMIT_MINUTES


def test_never_watches_a_terminal_status():
    from app.engines.execution.constants import TERMINAL_JOB_STATUSES

    assert not (set(watchdog.STALL_LIMIT_MINUTES) & TERMINAL_JOB_STATUSES)


# ── escalation ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_escalates_a_job_parked_past_its_limit(policy):
    db = _db([_job("reached_site", entered_minutes_ago=5525)])

    result = await watchdog.sweep(db)

    assert result["escalated"] == 1
    event = next(row for row in db.added if hasattr(row, "event_type"))
    assert event.event_type == "job_stalled"
    # Recorded as a non-transition: nothing moved, which is the point.
    assert event.old_status == event.new_status == "reached_site"
    assert event.event_metadata["stalled_minutes"] >= 5525
    assert event.event_metadata["outcome"] == "escalated_no_status_change"


@pytest.mark.asyncio
async def test_never_changes_the_job_status(policy):
    """A missed deadline is not evidence of what happened on site, and a
    booking the customer paid for must not be closed by a timer."""
    job = _job("service_started", entered_minutes_ago=5000)
    db = _db([job])

    await watchdog.sweep(db)

    assert job.status == "service_started"


@pytest.mark.asyncio
async def test_leaves_a_job_inside_its_limit_alone(policy):
    db = _db([_job("service_started", entered_minutes_ago=30)])

    result = await watchdog.sweep(db)

    assert result["escalated"] == 0
    assert db.added == []


@pytest.mark.asyncio
async def test_escalates_only_once_per_entry_into_a_status(policy):
    """A job left overnight must not notify every ten minutes."""
    now = datetime.now(timezone.utc)
    job = _job("work_done", entered_minutes_ago=3000)
    job.warned_at = now - timedelta(minutes=100)   # warned AFTER it entered

    result = await watchdog.sweep(_db([job]))

    assert result["escalated"] == 0


@pytest.mark.asyncio
async def test_escalates_again_when_the_job_re_enters_the_same_status(policy):
    """`customer_not_available` can be re-entered. A warning from the previous
    visit must not silence the next one."""
    now = datetime.now(timezone.utc)
    job = _job("customer_not_available", entered_minutes_ago=600)
    job.warned_at = now - timedelta(minutes=5000)  # warned BEFORE this entry

    result = await watchdog.sweep(_db([job]))

    assert result["escalated"] == 1


@pytest.mark.asyncio
async def test_names_the_customer_when_the_job_waits_on_them(policy):
    """Blaming the provider for a customer's unanswered estimate is how an
    operator teaches providers to ignore the alert."""
    db = _db([_job("quote_required", entered_minutes_ago=5000)])

    await watchdog.sweep(db)

    event = next(row for row in db.added if hasattr(row, "event_type"))
    assert event.event_metadata["waiting_on"] == "customer"
    notification = next(row for row in db.added if hasattr(row, "notification_type"))
    assert "waiting on the customer" in notification.body


@pytest.mark.asyncio
async def test_can_be_switched_off_by_policy(policy):
    policy.job_stall_watchdog_enabled = False

    result = await watchdog.sweep(_db([_job("reached_site", entered_minutes_ago=9999)]))

    assert result == {"examined": 0, "escalated": 0, "disabled": True}


@pytest.mark.asyncio
async def test_a_notification_failure_still_records_the_escalation(policy, monkeypatch):
    async def boom(*_a, **_kw):
        raise RuntimeError("notification backend down")

    monkeypatch.setattr(watchdog, "_notify_provider", boom)
    db = _db([_job("reached_site", entered_minutes_ago=5000)])

    with pytest.raises(RuntimeError):
        await watchdog.sweep(db)
    # The event is written BEFORE the notification is attempted, so the audit
    # trail survives a broken notifier.
    assert any(hasattr(row, "event_type") for row in db.added)


# ── the sweep is registered ──────────────────────────────────────────────────

def test_the_loop_is_actually_scheduled():
    """A sweep nobody runs is worse than no sweep: it reads as covered."""
    import inspect
    import app.main

    source = inspect.getsource(app.main)
    assert "job_stall_watchdog" in source
    assert '("job_stall_watchdog", job_stall_watchdog_loop)' in source
