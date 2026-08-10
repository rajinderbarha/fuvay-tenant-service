"""Is this visit late, today, or still ahead?

One definition, computed on the server, because the customer's list and the provider's
dashboard must never disagree about which jobs are late. Two clients each deriving it
from a date string is how a customer comes to see "Today" for a job the provider's
board calls overdue.

WHAT LATENESS MEANS HERE, and what it deliberately does not:

The live jobs table (`service_jobs`) carries only the committed slot -- `scheduled_date`
and `scheduled_time_window`. There is no SLA clock on it. The columns that sound like
one (`jobs.sla_breached`, `jobs.sla_breach_level`, `jobs.sla_minutes`) belong to the
legacy `field_ops` table, which holds ZERO rows; reading those and calling the answer an
"SLA breach" would be reporting a number nobody measured. So lateness is derived from
the one fact that is real and checkable: the provider committed to a window, and that
window has passed with the work unfinished.

It is measured from the END of the window. A technician arriving at 14:45 for a
14:00-15:00 slot is on time, and calling that late would be wrong in the direction that
matters most -- telling a customer their provider had failed them when they had not.
"""
from __future__ import annotations

import datetime as dt

from app.engines.weather.slots import slot_end, slot_start

_IST = dt.timezone(dt.timedelta(hours=5, minutes=30))

# Nothing is expected of these any more, so they are never late.
TERMINAL_STATUSES = frozenset({"completed", "cancelled", "failed", "rejected"})

# Work is under way. Still reported as late once the window has passed -- a visit that
# started at 18:00 for a 10:00-12:00 slot IS late, and hiding that because someone
# eventually turned up is how a delay stops being visible to anyone.
IN_PROGRESS_STATUSES = frozenset({
    "on_the_way", "reached_site", "inspection_started", "inspection_done",
    "service_started", "work_done",
})

URGENCY_LATE = "late"
URGENCY_TODAY = "today"
URGENCY_UPCOMING = "upcoming"
URGENCY_UNSCHEDULED = "unscheduled"
URGENCY_NONE = None

#: Order the app should draw the groups in. Late first, because it is the only one that
#: needs an action today.
URGENCY_ORDER = (URGENCY_LATE, URGENCY_TODAY, URGENCY_UPCOMING, URGENCY_UNSCHEDULED)


def _now_ist(now: dt.datetime | None = None) -> dt.datetime:
    return (now or dt.datetime.now(dt.timezone.utc)).astimezone(_IST)


def classify(
    status: str | None,
    scheduled_date: dt.date | None,
    scheduled_time_window: str | None,
    now: dt.datetime | None = None,
) -> str | None:
    """Which group this job belongs to, or None when urgency does not apply.

    None for finished and cancelled work: a completed job that ran late is history, and
    listing it under "Late" would make a customer think something still needs doing.

    `unscheduled` is its own answer rather than being folded into "upcoming". A job with
    no slot yet is not a job scheduled for later -- it is one nobody has committed to,
    which is a different thing to tell someone and a different thing to fix.
    """
    if status and str(status).strip().lower() in TERMINAL_STATUSES:
        return URGENCY_NONE

    moment = _now_ist(now)
    end = slot_end(scheduled_date, scheduled_time_window)
    if end is None:
        return URGENCY_UNSCHEDULED
    if end < moment:
        return URGENCY_LATE

    start = slot_start(scheduled_date, scheduled_time_window)
    if start is None:
        return URGENCY_UPCOMING
    # Already under way counts as today even if the window opened yesterday -- a
    # 23:00-01:00 slot being served at 00:30 is happening NOW, and calling it
    # "upcoming" would file work in progress under things that have not started.
    if start <= moment:
        return URGENCY_TODAY
    if start.date() == moment.date():
        return URGENCY_TODAY
    return URGENCY_UPCOMING


def minutes_late(
    status: str | None,
    scheduled_date: dt.date | None,
    scheduled_time_window: str | None,
    now: dt.datetime | None = None,
) -> int | None:
    """How far past the committed window this job is, or None if it is not late.

    A real count, so a caller can say "40 minutes late" or "2 days late" rather than
    just "late" -- and so a dashboard can rank the worst first instead of alphabetically.
    """
    if classify(status, scheduled_date, scheduled_time_window, now) != URGENCY_LATE:
        return None
    end = slot_end(scheduled_date, scheduled_time_window)
    if end is None:
        return None
    return int((_now_ist(now) - end).total_seconds() // 60)


def describe(minutes: int | None) -> str | None:
    """Plain wording for a delay. None when there is nothing to describe.

    Rounded DOWN to the unit below, so it never overstates: 119 minutes reads as
    "1 hour late", not "2 hours".
    """
    if minutes is None or minutes < 1:
        return None
    if minutes < 60:
        return f"{minutes} min late"
    hours = minutes // 60
    if hours < 24:
        return f"{hours} hour{'s' if hours > 1 else ''} late"
    days = hours // 24
    return f"{days} day{'s' if days > 1 else ''} late"
