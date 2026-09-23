"""What an Instagram customer is told while their visit approaches.

The visit reminder named the technician and the time ("scheduled to visit you
today at 10:00-12:00"); the assigned/on-the-way/arrived messages did not, and
the assigned one waited for the technician's own acceptance, so a customer
whose technician never opened the app was never told anyone was coming.
"""
import uuid
from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace as NS
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.engines.messaging_gateway import booking_updates
from app.engines.messaging_gateway.booking_updates import visit_label

TODAY = datetime.now(timezone.utc).astimezone(booking_updates.LOCAL_TZ).date()


def _job(**kw):
    return NS(id=kw.pop("id", uuid.uuid4()), booking_id=kw.pop("booking_id", uuid.uuid4()),
              tenant_id=uuid.uuid4(), assigned_staff_id=kw.pop("staff", uuid.uuid4()),
              scheduled_date=kw.pop("scheduled_date", TODAY),
              scheduled_time_window=kw.pop("window", "10:00-12:00"), **kw)


def _booking(job, **kw):
    return NS(id=job.booking_id, customer_id=uuid.uuid4(), booking_number="BK-77",
              source_channel=kw.pop("channel", "instagram"),
              source_actor_id="igsid-booker", **kw)


def _wire(monkeypatch, booking, *, announced=None, sent=True, name="Ramesh Kumar"):
    """A chat that is open, with `announced` standing in for a past message."""
    from app.engines.final_records.models import ServiceBooking

    thread = NS(id=uuid.uuid4(), channel="instagram", channel_user_id="igsid-booker",
                customer_id=booking.customer_id, blocked_until=None,
                last_outbound_at=None, last_options=None)

    async def get(model, _pk):
        return booking if model is ServiceBooking else NS(full_name=name)

    db = AsyncMock()
    db.get = AsyncMock(side_effect=get)
    db.scalar = AsyncMock(return_value=announced)
    result = MagicMock()
    result.scalars.return_value.first.return_value = thread
    db.execute = AsyncMock(return_value=result)
    db.add = MagicMock()

    monkeypatch.setattr(booking_updates.messaging_channel_config_service, "get",
                        AsyncMock(return_value={"access_token": "t"}))
    send = AsyncMock(return_value={"sent": sent})
    monkeypatch.setattr(booking_updates.meta_client, "send_options", send)
    return db, send


def _message(send):
    return send.call_args.args[1]


# ── One phrasing for the visit, everywhere ───────────────────────────────────

@pytest.mark.parametrize("scheduled, window, expected", [
    (TODAY, "10:00-12:00", "today at 10:00-12:00"),
    (TODAY + timedelta(days=1), "2 PM - 4 PM", "tomorrow at 2 PM - 4 PM"),
    (TODAY - timedelta(days=1), "10:00-12:00", "yesterday at 10:00-12:00"),
    (TODAY, None, "today"),
    # No date yet: "scheduled to visit you" would promise what nothing backs.
    (None, "10:00-12:00", ""),
])
def test_the_visit_reads_the_same_way_in_every_message(scheduled, window, expected):
    assert visit_label(NS(scheduled_date=scheduled, scheduled_time_window=window)) == expected


def test_a_far_off_visit_names_its_date():
    label = visit_label(NS(scheduled_date=TODAY + timedelta(days=4),
                           scheduled_time_window="09:00-11:00"))
    assert label == f"on {(TODAY + timedelta(days=4)).strftime('%d %b')} at 09:00-11:00"


# ── The three states ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_the_assigned_message_names_the_technician_and_the_visit(monkeypatch):
    job = _job()
    db, send = _wire(monkeypatch, _booking(job))

    assert await booking_updates.send_technician_assigned(db, job) is True
    assert _message(send) == (
        "Ramesh Kumar is assigned to booking BK-77. "
        "They are scheduled to visit you today at 10:00-12:00."
    )
    assert [row["id"] for row in send.call_args.args[2]] == ["tr|"]


@pytest.mark.asyncio
async def test_the_on_the_way_message_repeats_the_booked_time(monkeypatch):
    job = _job()
    db, send = _wire(monkeypatch, _booking(job))

    assert await booking_updates.send_on_the_way(db, job) is True
    assert _message(send) == (
        "Ramesh Kumar is on the way to you now. "
        "Your visit is scheduled today at 10:00-12:00."
    )


@pytest.mark.asyncio
async def test_the_arrived_message_says_which_visit(monkeypatch):
    job = _job()
    db, send = _wire(monkeypatch, _booking(job))

    assert await booking_updates.send_arrived(db, job) is True
    assert _message(send) == "Ramesh Kumar has arrived for your visit today at 10:00-12:00."


@pytest.mark.asyncio
async def test_an_undated_job_never_promises_a_time(monkeypatch):
    job = _job(scheduled_date=None, window=None)
    db, send = _wire(monkeypatch, _booking(job))

    await booking_updates.send_on_the_way(db, job)
    assert _message(send) == "Ramesh Kumar is on the way to you now."
    await booking_updates.send_arrived(db, job)
    assert _message(send) == "Ramesh Kumar has arrived for your service."


# ── Announced once per technician ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_the_technician_is_announced_once_not_again_on_acceptance(monkeypatch):
    """Assignment and acceptance are seconds apart and say the same thing."""
    job = _job()
    db, send = _wire(monkeypatch, _booking(job))

    assert await booking_updates.send_technician_assigned(db, job) is True
    db.add.assert_called_once()
    recorded = db.add.call_args.args[0]
    assert recorded.event_type == booking_updates.ASSIGNED_EVENT_TYPE
    assert recorded.staff_member_id == job.assigned_staff_id

    # The acceptance hook now finds that record.
    db, send = _wire(monkeypatch, _booking(job), announced=uuid.uuid4())
    assert await booking_updates.send_technician_assigned(db, job) is False
    send.assert_not_awaited()


@pytest.mark.asyncio
async def test_a_message_that_never_arrived_is_not_recorded_as_sent(monkeypatch):
    """A closed 24-hour window must not silence the next technician too."""
    job = _job()
    db, send = _wire(monkeypatch, _booking(job), sent=False)

    assert await booking_updates.send_technician_assigned(db, job) is False
    db.add.assert_not_called()


@pytest.mark.asyncio
async def test_the_customer_hears_as_soon_as_a_technician_is_assigned():
    """Waiting for acceptance left a booking silent when nobody accepted."""
    source = open(
        "app/engines/home_service_assignment/service.py", encoding="utf-8",
    ).read()
    assign = source[source.index("async def assign_job"):source.index("async def technician_accept_job")]
    assert "send_technician_assigned" in assign


@pytest.mark.asyncio
@pytest.mark.parametrize("sender", ["send_technician_assigned", "send_on_the_way", "send_arrived"])
async def test_a_broken_lookup_never_fails_the_field_operation(sender):
    """These run inside assign_job, mark_on_the_way and mark_reached_site."""
    db = AsyncMock()
    db.get = AsyncMock(side_effect=RuntimeError("database hiccup"))
    db.scalar = AsyncMock(side_effect=RuntimeError("database hiccup"))
    assert await getattr(booking_updates, sender)(db, _job()) is False
