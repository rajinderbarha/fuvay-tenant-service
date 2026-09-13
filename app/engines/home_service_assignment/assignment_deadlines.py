"""One definition of the provider's technician-assignment deadline.

The provider already owns the booking.  This deadline therefore escalates and
auto-assigns within that provider; it never expires or transfers the booking.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from app.engines.weather.slots import slot_start

# Provider ownership and technician ownership are separate. Older/manual flows
# may already have advanced the job projection to assigned/scheduled while the
# technician snapshot is still empty. Every surface and the recovery worker
# must treat those states alike instead of displaying a breach the worker will
# never pick up.
TECHNICIAN_ASSIGNMENT_PENDING_STATUSES = (
    "pending_assignment", "accepted", "assigned", "scheduled",
)


@dataclass(frozen=True)
class AssignmentDeadline:
    deadline: datetime | None
    minutes: int
    urgent: bool
    overdue: bool


def for_job(job, policy, now: datetime | None = None) -> AssignmentDeadline:
    moment = now or datetime.now(timezone.utc)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    offered = getattr(job, "provider_offer_started_at", None) or getattr(job, "created_at", None)
    normal_minutes = int(getattr(policy, "assignment_timeout_minutes", 30) or 30)
    urgent_minutes = int(getattr(policy, "urgent_assignment_timeout_minutes", 10) or 10)
    threshold_minutes = int(getattr(policy, "urgent_assignment_threshold_minutes", 120) or 120)
    visit = slot_start(
        getattr(job, "scheduled_date", None),
        getattr(job, "scheduled_time_window", None),
    )
    visit_is_same_day = bool(
        visit and visit.date() == moment.astimezone(visit.tzinfo).date()
    )
    urgent = bool(
        getattr(job, "is_emergency", False)
        or visit_is_same_day
        or (
            visit
            and visit.astimezone(timezone.utc)
            <= moment + timedelta(minutes=threshold_minutes)
        )
    )
    minutes = urgent_minutes if urgent else normal_minutes
    if offered is None:
        return AssignmentDeadline(None, minutes, urgent, False)
    if offered.tzinfo is None:
        offered = offered.replace(tzinfo=timezone.utc)
    deadline = offered + timedelta(minutes=minutes)
    return AssignmentDeadline(deadline, minutes, urgent, moment >= deadline)
