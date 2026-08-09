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
        try:
            hour, _, minute = head.partition(":")
            start = dt.time(int(hour), int(minute or 0))
        except (TypeError, ValueError):
            return None
    return dt.datetime.combine(scheduled_date, start, tzinfo=_IST)
