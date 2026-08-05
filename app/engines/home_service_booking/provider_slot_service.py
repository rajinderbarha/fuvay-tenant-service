"""Provider-level bookable-slot resolution.

The PROVIDER owns capacity: they configure their own business hours,
slot length and how many jobs they will accept per slot
(`provider_availability_rules`, scope_type='provider' --
`slot_duration_minutes` / `max_bookings_per_slot`). Technician allocation
is entirely the provider's own downstream responsibility, so nothing here
looks at individual technicians or their leave: a slot is bookable when
the PROVIDER has capacity in it, full stop.

Real gap this closes: providers could already configure slot length and
per-slot capacity through the provider portal, but NOTHING in the booking
pipeline ever read it. Bookings were accepted with no regard to whether
the provider had any capacity at all, and the customer was never told
when their service would actually happen.

The customer is shown a real, capacity-checked slot BEFORE they confirm
(today first, then the next day, and so on), so they make the final call
on a promise the provider can actually keep -- rather than confirming
blind and waiting to find out.
"""
from __future__ import annotations
import datetime as dt
import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

# How far ahead to look before giving up. A provider with no configured
# availability at all should fail fast and visibly, not scan forever.
DEFAULT_SEARCH_DAYS = 14

# Used only when a provider has rules but left slot length unset.
FALLBACK_SLOT_MINUTES = 60

# Used only when a provider has rules but left per-slot capacity unset.
# 1 is the safe reading of "unconfigured": never silently overbook someone.
FALLBACK_MAX_PER_SLOT = 1


def _parse_hhmm(value) -> dt.time | None:
    """Rules store times as strings ("09:00" / "09:00:00")."""
    if value is None:
        return None
    if isinstance(value, dt.time):
        return value
    s = str(value).strip()
    for fmt in ("%H:%M:%S", "%H:%M"):
        try:
            return dt.datetime.strptime(s, fmt).time()
        except ValueError:
            continue
    return None


def _window_label(start: dt.time, end: dt.time) -> str:
    """The canonical `scheduled_time_window` string stored on the job."""
    return f"{start.strftime('%H:%M')}-{end.strftime('%H:%M')}"


async def _provider_rules_for_day(db: AsyncSession, tenant_id: uuid.UUID, dow: int) -> list[dict]:
    rows = (await db.execute(text(
        "SELECT * FROM provider_availability_rules "
        "WHERE tenant_id=:tid AND scope_type='provider' AND scope_id IS NULL "
        "AND day_of_week=:dow AND is_active=true "
        "ORDER BY start_time"
    ), {"tid": str(tenant_id), "dow": dow})).fetchall()
    return [dict(r._mapping) for r in rows]


async def _is_closed(db: AsyncSession, tenant_id: uuid.UUID, day: dt.date) -> bool:
    row = (await db.execute(text(
        "SELECT full_day_closed FROM tenant_availability_exceptions "
        "WHERE tenant_id=:tid AND date=:d AND status='active'"
    ), {"tid": str(tenant_id), "d": day})).fetchone()
    return bool(row and row._mapping.get("full_day_closed"))


async def _booked_counts(db: AsyncSession, tenant_id: uuid.UUID, day: dt.date) -> dict[str, int]:
    """How many live jobs the provider already holds per time window that day.

    Cancelled/failed jobs must not consume capacity -- otherwise a day of
    cancellations would permanently block a provider's calendar.
    """
    rows = (await db.execute(text(
        "SELECT scheduled_time_window, COUNT(*) AS n FROM service_jobs "
        "WHERE tenant_id=:tid AND scheduled_date=:d "
        "AND scheduled_time_window IS NOT NULL "
        "AND status NOT IN ('cancelled','failed','rejected') "
        "GROUP BY scheduled_time_window"
    ), {"tid": str(tenant_id), "d": day})).fetchall()
    return {r._mapping["scheduled_time_window"]: int(r._mapping["n"]) for r in rows}


def _slots_from_rule(rule: dict) -> list[tuple[dt.time, dt.time]]:
    start = _parse_hhmm(rule.get("start_time"))
    end = _parse_hhmm(rule.get("end_time"))
    if not start or not end or start >= end:
        return []
    minutes = rule.get("slot_duration_minutes") or FALLBACK_SLOT_MINUTES
    if minutes <= 0:
        minutes = FALLBACK_SLOT_MINUTES

    slots: list[tuple[dt.time, dt.time]] = []
    cursor = dt.datetime.combine(dt.date.today(), start)
    limit = dt.datetime.combine(dt.date.today(), end)
    step = dt.timedelta(minutes=minutes)
    while cursor + step <= limit:
        nxt = cursor + step
        slots.append((cursor.time(), nxt.time()))
        cursor = nxt
    return slots


async def find_earliest_available_slot(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    from_datetime: dt.datetime | None = None,
    search_days: int = DEFAULT_SEARCH_DAYS,
) -> dict | None:
    """First slot this provider genuinely has capacity for.

    Walks forward day by day from `from_datetime` (default: now) and
    returns the first slot whose live booking count is below the
    provider's own `max_bookings_per_slot`. Slots that already started
    today are skipped -- a provider cannot honour a window that has
    passed.

    Returns None when the provider has no capacity anywhere in the search
    horizon. Callers must treat that as "cannot promise a time", never as
    "book it anyway".
    """
    now = from_datetime or dt.datetime.now()
    day = now.date()

    for offset in range(search_days):
        target = day + dt.timedelta(days=offset)
        if await _is_closed(db, tenant_id, target):
            continue

        dow = target.isoweekday() % 7  # 0=Sunday, matches provider_availability_rules
        rules = await _provider_rules_for_day(db, tenant_id, dow)
        if not rules:
            continue

        booked = await _booked_counts(db, tenant_id, target)

        for rule in rules:
            cap = rule.get("max_bookings_per_slot") or FALLBACK_MAX_PER_SLOT
            for start, end in _slots_from_rule(rule):
                # Never offer a window that has already begun today.
                if offset == 0 and dt.datetime.combine(target, start) <= now:
                    continue
                label = _window_label(start, end)
                if booked.get(label, 0) >= cap:
                    continue
                return {
                    "date": target.isoformat(),
                    "time_window": label,
                    "starts_at": dt.datetime.combine(target, start).isoformat(),
                    "ends_at": dt.datetime.combine(target, end).isoformat(),
                    "slot_minutes": int(
                        (dt.datetime.combine(target, end) - dt.datetime.combine(target, start)).total_seconds() // 60
                    ),
                    "capacity": cap,
                    "already_booked": booked.get(label, 0),
                    "days_ahead": offset,
                }
    return None


async def slot_has_capacity(
    db: AsyncSession, *, tenant_id: uuid.UUID, day: dt.date, time_window: str,
) -> bool:
    """Re-check a specific slot at confirmation time.

    The customer may sit on the review screen for a while, and another
    customer can take the last place in the meantime -- so the promise is
    always re-validated before it is committed, never trusted from the
    earlier offer.
    """
    if await _is_closed(db, tenant_id, day):
        return False
    dow = day.isoweekday() % 7
    rules = await _provider_rules_for_day(db, tenant_id, dow)
    if not rules:
        return False
    booked = (await _booked_counts(db, tenant_id, day)).get(time_window, 0)
    for rule in rules:
        cap = rule.get("max_bookings_per_slot") or FALLBACK_MAX_PER_SLOT
        for start, end in _slots_from_rule(rule):
            if _window_label(start, end) == time_window:
                return booked < cap
    return False
