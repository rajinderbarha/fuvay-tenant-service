"""A technician who taps "On my way" and never arrives is closed safely.

Travel expiry alerts first. The SLA deducts the missed-slot charge, then this
final safety net closes only when the persisted final deadline has elapsed.
"""
from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace as NS
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.engines.execution.sla_breach_service import (
    settle_no_arrival_close as real_settle_no_arrival_close,  # before the autouse stub
)
from app.jobs import travel_timeout


def _row(*, entered_minutes_ago, limit=30, snapshot=True, travel_minutes=30,
         penalty_day_count=1, final_due_minutes_ago=1):
    now = datetime.now(timezone.utc)
    return NS(
        id=uuid.uuid4(), tenant_id=uuid.uuid4(), booking_id=uuid.uuid4(),
        customer_id=uuid.uuid4(), job_number="JOB-TEST-0001",
        booking_number="BK-TEST-0001", assigned_staff_id=uuid.uuid4(),
        travel_minutes=travel_minutes,
        stage_metadata=({"stage_timer": {"status": "on_the_way", "limit_minutes": limit}}
                        if snapshot else None),
        entered_at=now - timedelta(minutes=entered_minutes_ago),
        sla_penalty_day_count=penalty_day_count,
        sla_next_penalty_at=now - timedelta(minutes=final_due_minutes_ago),
    )


def _db(rows, *, locked_status="on_the_way"):
    """`locked_status` is what the row lock sees: a status, or None when a
    request in flight already holds the row."""
    db = MagicMock()
    db.added = []
    db.statements = []

    async def execute(stmt, params=None):
        db.statements.append((str(stmt), params or {}))
        result = MagicMock()
        result.fetchall.return_value = rows
        result.scalar.return_value = uuid.uuid4()   # tenant owner / technician user
        return result

    @asynccontextmanager
    async def begin_nested():
        yield

    db.execute = AsyncMock(side_effect=execute)
    db.scalar = AsyncMock(return_value=locked_status)
    db.begin_nested = begin_nested
    db.flush = AsyncMock()
    db.add = MagicMock(side_effect=db.added.append)
    return db


def _updates(db, table):
    return [params for sql, params in db.statements if sql.lstrip().startswith(f"UPDATE {table} ")]


def _events(db):
    return [row for row in db.added if hasattr(row, "event_type")]


def _notices(db):
    return [row for row in db.added if hasattr(row, "notification_type")]


@pytest.fixture(autouse=True)
def _no_health_refresh(monkeypatch):
    monkeypatch.setattr(
        "app.engines.tenant_engine.health.refresh_provider_operational_health",
        AsyncMock(return_value={}),
    )


@pytest.fixture(autouse=True)
def settle(monkeypatch):
    """The missed-arrival charge; its own arithmetic is tested at the bottom."""
    from decimal import Decimal
    fake = AsyncMock(return_value=Decimal("150"))
    monkeypatch.setattr(
        "app.engines.execution.sla_breach_service.settle_no_arrival_close", fake,
    )
    return fake


# ── cancellation ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_cancels_only_after_the_persisted_final_sla_deadline():
    row = _row(entered_minutes_ago=31, limit=30)
    db = _db([row])

    result = await travel_timeout.sweep(db)

    assert result["cancelled"] == 1
    assert result["cancelled_job_ids"] == [str(row.id)]
    job_update, = _updates(db, "service_jobs")
    assert job_update["cancelled"] == "cancelled"
    assert job_update["reason"].startswith(travel_timeout.FAILURE_REASON_PREFIX)
    assert "30 minutes" in job_update["reason"]
    # Booking and assignment close with the job, so nothing still shows it live.
    assert _updates(db, "service_bookings")[0]["id"] == str(row.booking_id)
    assert _updates(db, "service_job_assignments")[0]["id"] == str(row.id)

    cancelled = next(e for e in _events(db) if e.event_type == "job_cancelled")
    assert (cancelled.old_status, cancelled.new_status) == ("on_the_way", "cancelled")
    assert cancelled.actor_role == "platform"
    assert cancelled.event_metadata["reason_code"] == "technician_not_available"


@pytest.mark.asyncio
async def test_tells_the_customer_the_technician_is_not_available():
    row = _row(entered_minutes_ago=45)
    db = _db([row])

    await travel_timeout.sweep(db)

    customer = next(n for n in _notices(db) if n.user_id == row.customer_id)
    assert customer.title == "Your booking was cancelled"
    assert "technician is not available" in customer.body
    assert "BK-TEST-0001" in customer.body
    # The provider owner and the technician hear it too.
    assert len(_notices(db)) == 3


@pytest.mark.asyncio
async def test_keeps_the_provider_health_signal_the_stall_alert_used_to_give():
    """Health counts provider-owned `job_stalled` events. Cancelling instead of
    alerting must not quietly let an abandoned trip stop counting."""
    db = _db([_row(entered_minutes_ago=31)])

    await travel_timeout.sweep(db)

    stalled = next(e for e in _events(db) if e.event_type == "job_stalled")
    assert stalled.event_metadata["waiting_on"] == "provider"
    assert stalled.event_metadata["outcome"] == "cancelled_technician_not_available"


@pytest.mark.asyncio
async def test_leaves_a_journey_inside_its_buffer_alone():
    db = _db([_row(entered_minutes_ago=20, limit=30)])

    result = await travel_timeout.sweep(db)

    assert result["cancelled"] == 0
    assert db.added == []
    assert _updates(db, "service_jobs") == []


@pytest.mark.asyncio
async def test_uses_the_buffer_promised_when_travel_started():
    """A provider shortening its buffer mid-journey must not cancel a
    technician who set off under the longer one."""
    db = _db([_row(entered_minutes_ago=40, limit=60, travel_minutes=15)])

    result = await travel_timeout.sweep(db)

    assert result["cancelled"] == 0


@pytest.mark.parametrize("snapshot, travel_minutes, expected", [
    (False, 45, 45),     # legacy journey: the provider's current buffer
    (False, 0, 30),      # zero spaces slots; it is not a journey limit
    (False, None, 30),   # provider never set a buffer
    (True, 45, 30),      # the snapshot wins over today's setting
])
def test_travel_limit(snapshot, travel_minutes, expected):
    row = _row(entered_minutes_ago=0, limit=30, snapshot=snapshot,
               travel_minutes=travel_minutes)
    assert travel_timeout.travel_limit_minutes(row) == expected


# ── races with the technician ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_a_technician_who_reached_site_first_keeps_the_job():
    db = _db([_row(entered_minutes_ago=31)], locked_status="reached_site")

    result = await travel_timeout.sweep(db)

    assert result["cancelled"] == 0
    assert _updates(db, "service_jobs") == []
    assert db.added == []


@pytest.mark.asyncio
async def test_a_job_held_by_a_request_in_flight_waits_for_the_next_sweep():
    db = _db([_row(entered_minutes_ago=31)], locked_status=None)

    result = await travel_timeout.sweep(db)

    assert result["cancelled"] == 0
    assert _updates(db, "service_jobs") == []


@pytest.mark.asyncio
async def test_one_failing_job_does_not_stop_the_rest(monkeypatch):
    first, second = _row(entered_minutes_ago=90), _row(entered_minutes_ago=60)
    real_cancel = travel_timeout._cancel

    async def cancel(db, row, **kw):
        if row is first:
            raise RuntimeError("row is broken")
        return await real_cancel(db, row, **kw)

    monkeypatch.setattr(travel_timeout, "_cancel", cancel)

    result = await travel_timeout.sweep(_db([first, second]))

    assert result["cancelled_job_ids"] == [str(second.id)]


# ── Instagram, after commit ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_the_chat_message_is_sent_only_after_the_cancellation_commits(monkeypatch):
    """A chat message cannot be unsent, so it must never announce a
    cancellation that then rolled back."""
    order: list[str] = []
    session = MagicMock()
    session.commit = AsyncMock(side_effect=lambda: order.append("commit"))

    @asynccontextmanager
    async def open_session():
        yield session

    monkeypatch.setattr("app.database.get_session_factory", lambda: open_session)
    monkeypatch.setattr(travel_timeout, "sweep", AsyncMock(return_value={
        "examined": 1, "cancelled": 1, "cancelled_job_ids": ["job-1"],
    }))

    async def send(job_id):
        order.append(f"send:{job_id}")
        return True

    monkeypatch.setattr(
        "app.engines.messaging_gateway.booking_updates.send_technician_unavailable_cancelled",
        send,
    )

    await travel_timeout.run_once()

    assert order == ["commit", "send:job-1"]


def _ig_session(monkeypatch, *, failure_reason, already=None, sent=True):
    from app.engines.final_records.models import ServiceBooking, ServiceJob
    from app.engines.messaging_gateway import booking_updates

    job = NS(id=uuid.uuid4(), booking_id=uuid.uuid4(), tenant_id=uuid.uuid4(),
             status="cancelled", failure_reason=failure_reason)
    booking = NS(id=job.booking_id, booking_number="BK-77", source_channel="instagram")

    async def get(model, _pk):
        return {ServiceJob: job, ServiceBooking: booking}[model]

    db = MagicMock()
    db.added = []
    # First scalar is the advisory lock, second the "already told" lookup.
    db.scalar = AsyncMock(side_effect=[True, already])
    db.get = AsyncMock(side_effect=get)
    db.add = MagicMock(side_effect=db.added.append)
    db.commit = AsyncMock()

    @asynccontextmanager
    async def open_session():
        yield db

    monkeypatch.setattr("app.database.get_session_factory", lambda: open_session)
    notify = AsyncMock(return_value=sent)
    monkeypatch.setattr(booking_updates, "notify_booking_customer", notify)
    return job, db, notify


REASON = (f"{travel_timeout.FAILURE_REASON_PREFIX}: did not reach the customer "
          "within 30 minutes of starting travel")


@pytest.mark.asyncio
async def test_instagram_is_told_the_technician_is_not_available(monkeypatch):
    from app.engines.messaging_gateway import booking_updates

    job, db, notify = _ig_session(monkeypatch, failure_reason=REASON)

    assert await booking_updates.send_technician_unavailable_cancelled(job.id) is True

    message = notify.call_args.args[2]
    assert "BK-77" in message and "technician is not available" in message
    assert notify.call_args.kwargs["rows"][0]["title"] == "Book again"
    event, = db.added
    assert event.event_type == booking_updates.TECHNICIAN_UNAVAILABLE_EVENT_TYPE
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_instagram_is_not_told_twice(monkeypatch):
    from app.engines.messaging_gateway import booking_updates

    job, db, notify = _ig_session(monkeypatch, failure_reason=REASON, already=uuid.uuid4())

    assert await booking_updates.send_technician_unavailable_cancelled(job.id) is True
    notify.assert_not_awaited()


@pytest.mark.asyncio
async def test_other_cancellations_do_not_blame_the_technician(monkeypatch):
    from app.engines.messaging_gateway import booking_updates

    job, db, notify = _ig_session(monkeypatch, failure_reason="Customer changed plans")

    assert await booking_updates.send_technician_unavailable_cancelled(job.id) is False
    notify.assert_not_awaited()


@pytest.mark.asyncio
async def test_an_undelivered_message_records_nothing(monkeypatch):
    """Outside Instagram's 24-hour window the send is refused. Recording it as
    delivered would hide that the customer was never told."""
    from app.engines.messaging_gateway import booking_updates

    job, db, notify = _ig_session(monkeypatch, failure_reason=REASON, sent=False)

    assert await booking_updates.send_technician_unavailable_cancelled(job.id) is False
    assert db.added == []
    db.commit.assert_not_awaited()


# ── the sweep is registered ──────────────────────────────────────────────────

def test_the_loop_is_actually_scheduled():
    import inspect
    import app.main

    assert '("travel_timeout", travel_timeout_loop)' in inspect.getsource(app.main)


# ── never before the visit is late, and never for free ──────────────────────

def _slot_row(*, entered_minutes_ago, late_in_minutes):
    """A job whose booked window is still open for `late_in_minutes`."""
    row = _row(entered_minutes_ago=entered_minutes_ago)
    row.sla_due_at = datetime.now(timezone.utc) + timedelta(minutes=late_in_minutes)
    return row


@pytest.mark.asyncio
async def test_a_technician_who_set_off_early_is_not_cancelled_inside_the_window():
    """Seen live: "On the way" tapped 1-2 hours before a 14:00-16:00 slot.

    Thirty minutes after that tap the technician is still early, not missing.
    Cancelling then told the customer nobody was coming while they were on
    the road, for a visit whose window had not even opened.
    """
    row = _slot_row(entered_minutes_ago=90, late_in_minutes=60)
    row.sla_penalty_day_count = 0
    db = _db([row])

    result = await travel_timeout.sweep(db)

    assert result["cancelled"] == 0
    assert _updates(db, "service_jobs") == []


@pytest.mark.asyncio
async def test_slot_end_alone_does_not_cancel_before_the_24_hour_close_window():
    row = _slot_row(entered_minutes_ago=180, late_in_minutes=-5)
    row.sla_penalty_day_count = 0
    db = _db([row])

    result = await travel_timeout.sweep(db)

    assert result["cancelled"] == 0
    assert _updates(db, "service_jobs") == []


@pytest.mark.asyncio
async def test_after_first_charge_the_final_deadline_closes_and_says_why():
    row = _slot_row(entered_minutes_ago=1500, late_in_minutes=-1445)
    row.sla_penalty_day_count = 1
    row.sla_next_penalty_at = datetime.now(timezone.utc) - timedelta(minutes=5)
    db = _db([row])

    result = await travel_timeout.sweep(db)

    assert result["cancelled"] == 1
    reason = _updates(db, "service_jobs")[0]["reason"]
    assert reason.startswith(travel_timeout.FAILURE_REASON_PREFIX)
    cancelled = next(e for e in _events(db) if e.event_type == "job_cancelled")
    assert cancelled.event_metadata["deadline_at"] == row.sla_next_penalty_at.isoformat()


@pytest.mark.asyncio
async def test_a_late_start_still_gets_its_whole_buffer():
    """Setting off ten minutes before the window closes is not a no-show yet."""
    row = _slot_row(entered_minutes_ago=15, late_in_minutes=-5)
    row.sla_penalty_day_count = 0
    db = _db([row])

    assert (await travel_timeout.sweep(db))["cancelled"] == 0


def test_a_job_without_a_stored_deadline_uses_its_slot_end():
    from app.engines.weather.slots import slot_end

    row = _row(entered_minutes_ago=10)
    row.sla_due_at = None
    row.scheduled_date = datetime.now(timezone.utc).date() + timedelta(days=1)
    row.scheduled_time_window = "14:00-16:00"
    deadline = travel_timeout.travel_deadline(row, row.entered_at, 30)
    assert deadline == slot_end(row.scheduled_date, "14:00-16:00")


@pytest.mark.asyncio
async def test_every_cancellation_settles_the_missed_arrival_penalty(settle):
    """A cancelled job is outside the SLA engine's reach; the charge happens here."""
    row = _row(entered_minutes_ago=45)
    await travel_timeout.sweep(_db([row]))
    settle.assert_awaited_once()
    assert settle.await_args.kwargs == {"job_id": row.id}


@pytest.mark.asyncio
async def test_a_charge_that_fails_leaves_the_job_for_the_next_sweep(settle):
    """Never cancel for free: the job stays open, and the SLA engine is still
    the backstop that charges and closes it if this keeps failing."""
    settle.side_effect = RuntimeError("ledger unavailable")
    row = _row(entered_minutes_ago=45)

    assert (await travel_timeout.sweep(_db([row])))["cancelled"] == 0


# ── the charge itself ────────────────────────────────────────────────────────

@pytest.mark.asyncio
@pytest.mark.parametrize("already, expected", [
    (0, 150),     # nothing charged yet: the full no-show total
    (50, 100),    # the missed-slot 50 was taken: only the close top-up
    (150, 0),     # already fully charged: nothing more
])
async def test_a_no_show_costs_what_the_sla_close_would(monkeypatch, already, expected):
    """Live policy: 50 when the slot is missed, 150 in total when it closes."""
    from decimal import Decimal
    from app.engines.execution import sla_breach_service as sla

    policy = NS(id=uuid.uuid4(), sla_penalty_amount=Decimal("50"), sla_penalty_type="fixed",
                sla_penalty_percentage=None, sla_penalty_min=None, sla_penalty_max=None,
                sla_total_penalty_amount=Decimal("150"), sla_penalty_debt_cap=None,
                sla_penalty_to_customer=False, sla_notify_provider=False)
    job = NS(id=uuid.uuid4(), tenant_id=uuid.uuid4(), booking_id=uuid.uuid4(),
             customer_id=uuid.uuid4(), job_type_id=uuid.uuid4(),
             charged_so_far=Decimal(already), job_value=Decimal("0"))
    monkeypatch.setattr(sla, "_policy", AsyncMock(return_value=policy))
    monkeypatch.setattr(sla, "_job_type_override", AsyncMock(return_value=(True, None)))
    charge = AsyncMock(side_effect=lambda db, **kw: kw["amount"])
    monkeypatch.setattr(sla, "_charge_penalty", charge)

    db = MagicMock()
    db.statements = []

    async def execute(stmt, params=None):
        db.statements.append((str(stmt), params or {}))
        result = MagicMock()
        result.first.return_value = job
        return result
    db.execute = AsyncMock(side_effect=execute)

    taken = await real_settle_no_arrival_close(db, job_id=job.id)

    assert taken == Decimal(expected)
    if expected:
        kwargs = charge.await_args.kwargs
        # The final-close key: an SLA sweep that already closed it cannot charge twice.
        assert (kwargs["source"], kwargs["day_number"]) == ("sla_final_close", 2)
    else:
        charge.assert_not_awaited()
    # The clock stops either way, so no later sweep can charge this job again.
    stop = next(params for sql, params in db.statements if "sla_stopped_at=now()" in sql)
    assert stop["charged"] == Decimal(already) + Decimal(expected)
