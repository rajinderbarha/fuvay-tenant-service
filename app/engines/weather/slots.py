"""Turning a stored slot into a real moment in time.

Shared by the customer advisory and the provider's weather gate so both look up the
SAME hour -- two copies of this arithmetic would eventually disagree, and an
advisory that contradicts the gate is worse than neither.
"""
from __future__ import annotations

import datetime as dt

# The stored window is local wall-clock text with no offset ("14:00-15:00"). Reading
# it as UTC would look up the forecast five and a half hours late, which for an
# evening slot is the wrong day entirely.
_IST = dt.timezone(dt.timedelta(hours=5, minutes=30))

# Used only when a job has a date but no window at all. Mid-morning is when most
# visits actually start, and it is stated here rather than hidden in a caller.
_DEFAULT_START = dt.time(9, 0)


def _parse_wall_time(value: str) -> dt.time | None:
    """Read provider windows in either 24-hour or customer-friendly AM/PM form."""
    raw = " ".join(str(value or "").strip().upper().split())
    for pattern in ("%H:%M", "%H", "%I:%M %p", "%I %p"):
        try:
            return dt.datetime.strptime(raw, pattern).time()
        except ValueError:
            continue
    return None


def slot_start(scheduled_date: dt.date | None, window: str | None) -> dt.datetime | None:
    """Start of the slot in IST, or None if it cannot be read.

    None rather than a guess: a forecast for the wrong hour is worse than no
    forecast, because it gets shown to a customer as fact.
    """
    if scheduled_date is None:
        return None
    start = _DEFAULT_START
    if window:
        head = str(window).split("-")[0].strip()
        parsed = _parse_wall_time(head)
        if parsed is None:
            return None
        start = parsed
    return dt.datetime.combine(scheduled_date, start, tzinfo=_IST)


# How long a visit is assumed to take when the stored window has no end ("14:00" or a
# date with no window at all). Stated here rather than hidden in a caller, and used
# ONLY to decide whether a slot has passed -- never shown to anyone as a finish time.
_ASSUMED_DURATION = dt.timedelta(hours=2)


def slot_end(scheduled_date: dt.date | None, window: str | None) -> dt.datetime | None:
    """End of the slot in IST, or None if it cannot be read.

    Lateness is measured from the END of the committed window, not its start: a
    technician arriving at 14:45 for a 14:00-15:00 slot is on time, and calling that
    job late would be wrong in the direction that matters -- it would tell a customer
    their provider had failed them when they had not.
    """
    start = slot_start(scheduled_date, window)
    if start is None:
        return None
    if window and "-" in str(window):
        tail = str(window).split("-", 1)[1].strip()
        end_time = _parse_wall_time(tail)
        if end_time is None:
            return start + _ASSUMED_DURATION
        end = dt.datetime.combine(start.date(), end_time, tzinfo=_IST)
        # A window that ends before it starts crosses midnight.
        return end + dt.timedelta(days=1) if end <= start else end
    return start + _ASSUMED_DURATION


def slot_has_ended(
    scheduled_date: dt.date | None,
    window: str | None,
    *,
    now: dt.datetime | None = None,
) -> bool:
    """Whether the committed visit window is irreversibly in the past.

    Assignment, auto-assignment and dispatch must answer this identically.
    A missing or malformed slot is *not* called expired; those jobs remain
    unscheduled and are handled by the scheduling workflow instead.
    """
    if scheduled_date is None or not str(window or "").strip():
        return False
    end = slot_end(scheduled_date, window)
    if end is None:
        return False
    current = now or dt.datetime.now(dt.timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=dt.timezone.utc)
    return current.astimezone(_IST) >= end
