"""What should interrupt a provider anywhere in the authenticated portal.

Three kinds of thing, deliberately presented with different urgency:

* A NEW job has arrived. That is good news and worth celebrating -- it is money, and a
  provider who does not notice it for an hour has kept a customer waiting for nothing.
* An assigned visit starts soon but the technician is not on the way. The provider can
  still intervene before the customer is kept waiting.
* A job is PAST its committed slot. That is bad news and needs an action today.

Each alert carries a `tone` so the surface showing it does not have to guess from the
wording, and so the two can never end up looking alike. The tones come from the
notification registry's own severity vocabulary (`success`, `warning`, ...) rather than a
second scale invented here -- one platform, one idea of how serious something is.

Lateness itself is not defined here. It comes from `urgency.py`, which the customer's
own list also reads, so a provider is never shown a job as overdue that the customer's
app is calling "Today".
"""
from __future__ import annotations

import datetime as dt
import uuid
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.home_service_assignment import urgency as urgency_rules
from app.engines.home_service_assignment.assignment_deadlines import (
    TECHNICIAN_ASSIGNMENT_PENDING_STATUSES, for_job,
)
from app.engines.platform_notifications.constants import (
    EVT_JOB_DELAYED, SEV_SUCCESS, SEV_WARNING,
)
from app.engines.weather.slots import slot_start

TONE_CELEBRATE = SEV_SUCCESS
TONE_URGENT = SEV_WARNING

# Retained for callers that import this historical constant. Actionable offers
# now use the configured assignment deadline, not a generic age window.
NEW_JOB_WINDOW_HOURS = 12

# The dashboard interrupts with a popup; a queue of them is not an interruption, it is an
# obstacle. Applied by the ROUTER when it builds the response, never before the notifier
# runs -- every late job must be reported even if only a few are shown.
MAX_ALERTS = 5
DEPARTURE_WARNING_MINUTES = 15


async def _load_jobs(db: AsyncSession, tenant_id: uuid.UUID):
    from app.engines.final_records.models import ServiceJob

    return (await db.execute(
        select(
            ServiceJob.id, ServiceJob.job_number, ServiceJob.status,
            ServiceJob.scheduled_date, ServiceJob.scheduled_time_window,
            ServiceJob.created_at, ServiceJob.city,
            ServiceJob.assigned_staff_id, ServiceJob.provider_offer_started_at,
            ServiceJob.is_emergency, ServiceJob.job_type_id,
        ).where(ServiceJob.tenant_id == tenant_id)
    )).all()


def _job_label(job) -> str:
    """What to call the job in a one-line alert. Its number, which is what a provider
    searches by -- never an internal id."""
    return job.job_number or f"Job {str(job.id)[:8]}"


def _money(value) -> str:
    amount = Decimal(str(value or 0))
    return f"₹{amount:,.0f}" if amount == amount.to_integral_value() else f"₹{amount:,.2f}"


async def _penalty_context(db: AsyncSession, jobs) -> tuple[object | None, dict]:
    """Load the exact published SLA policy and per-job-type exemptions once."""
    from app.engines.execution.sla_breach_service import _policy
    policy = await _policy(db)
    if policy is None or policy.sla_breach_hours is None:
        return None, {}
    job_type_ids = {
        job.job_type_id for job in jobs if getattr(job, "job_type_id", None)
    }
    if not job_type_ids:
        return policy, {}
    from app.engines.vertical_monetization.models import MonetizationJobTypeRule
    rows = (await db.execute(select(
        MonetizationJobTypeRule.job_type_id,
        MonetizationJobTypeRule.sla_penalty_enabled,
        MonetizationJobTypeRule.sla_penalty_amount,
    ).where(
        MonetizationJobTypeRule.policy_id == policy.id,
        MonetizationJobTypeRule.job_type_id.in_(job_type_ids),
        MonetizationJobTypeRule.status == "active",
    ))).all()
    return policy, {
        row.job_type_id: (bool(row.sla_penalty_enabled), row.sla_penalty_amount)
        for row in rows
    }


def _penalty_notice(policy, overrides: dict, job) -> str | None:
    """Human-readable consequence matching the enforcement policy for this job."""
    if policy is None:
        return None
    override = overrides.get(getattr(job, "job_type_id", None))
    if override is not None and not override[0]:
        return None
    override_amount = override[1] if override is not None else None
    if override_amount is not None:
        first_charge = _money(override_amount)
    elif (policy.sla_penalty_type or "fixed") == "percentage":
        first_charge = f"{Decimal(str(policy.sla_penalty_percentage or 0)):g}% of job value"
    else:
        first_charge = _money(policy.sla_penalty_amount)
    grace_hours = max(0, int(policy.sla_breach_hours or 0))
    first_when = (
        "after the slot ends" if grace_hours == 0
        else f"{grace_hours}h after the slot ends"
    )
    close_hours = max(1, min(168, int(policy.sla_close_after_hours or 24)))
    total = _money(policy.sla_total_penalty_amount)
    close = (
        f" If unresolved for {close_hours}h, the job closes with {total} total deduction."
        if policy.sla_auto_cancel else
        f" Further enforcement can increase the total deduction to {total}."
    )
    return f"SLA penalty: {first_charge} may be deducted {first_when}.{close}"


async def build_alerts(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    since: dt.datetime | None = None,
    now: dt.datetime | None = None,
    assignment_timeout_minutes: int | None = None,
    penalty_policy=None,
) -> dict:
    """The dashboard's alerts, newest-and-worst first.

    `since` remains in the response contract, but an unassigned provider offer
    stays visible on every poll until assigned or expired. The browser may
    snooze the popup briefly without hiding the actual work.

    Delayed jobs are ranked by how late they are, so the worst is the one that gets seen.
    """
    moment = now or dt.datetime.now(dt.timezone.utc)
    jobs = await _load_jobs(db, tenant_id)
    timeout_enabled = True
    policy = None
    load_live_policy = assignment_timeout_minutes is None
    if load_live_policy:
        from app.engines.vertical_monetization.runtime_operations import get_home_services_operations_policy
        policy = await get_home_services_operations_policy(db)
        assignment_timeout_minutes = policy.assignment_timeout_minutes
        timeout_enabled = policy.assignment_timeout_enabled
    if policy is None:
        from types import SimpleNamespace
        policy = SimpleNamespace(
            assignment_timeout_minutes=assignment_timeout_minutes,
            urgent_assignment_timeout_minutes=assignment_timeout_minutes,
            urgent_assignment_threshold_minutes=0,
        )

    penalty_overrides: dict = {}
    if load_live_policy and penalty_policy is None:
        penalty_policy, penalty_overrides = await _penalty_context(db, jobs)
    departure_warning_minutes = max(
        5, min(120, int(getattr(policy, "provider_departure_warning_minutes", DEPARTURE_WARNING_MINUTES)))
    )

    new_jobs = []
    departure_jobs = []
    delayed = []
    for job in jobs:
        penalty_notice = _penalty_notice(penalty_policy, penalty_overrides, job)
        offered = job.provider_offer_started_at or job.created_at
        if offered is not None:
            if offered.tzinfo is None:
                offered = offered.replace(tzinfo=dt.timezone.utc)
            assignment = for_job(job, policy, moment)
            deadline = assignment.deadline
            window_open = timeout_enabled or offered > moment - dt.timedelta(hours=NEW_JOB_WINDOW_HOURS)
            if (job.assigned_staff_id is None
                    and job.status in TECHNICIAN_ASSIGNMENT_PENDING_STATUSES
                    and window_open):
                overdue = bool(timeout_enabled and assignment.overdue)
                new_jobs.append({
                    "job_id": str(job.id),
                    "label": _job_label(job),
                    "city": job.city,
                    "created_at": offered.isoformat(),
                    "assignment_deadline_at": deadline.isoformat() if timeout_enabled and deadline else None,
                    "assignment_required": True,
                    "assignment_overdue": overdue,
                    "assignment_window_minutes": assignment.minutes,
                    "urgent_assignment": assignment.urgent,
                    "scheduled_date": job.scheduled_date.isoformat() if job.scheduled_date else None,
                    "scheduled_time_window": job.scheduled_time_window,
                    "tone": TONE_URGENT if overdue else TONE_CELEBRATE,
                    "title": "Technician assignment overdue" if overdue else "New job received",
                    "message": (
                        f"{_job_label(job)} is still waiting for a technician. "
                        "The provider and customer price remain locked."
                        if overdue else
                        f"{_job_label(job)} just came in. Assign a technician to get started."
                    ),
                    "alert_kind": "assignment",
                    "penalty_notice": penalty_notice,
                })

        visit_start = slot_start(job.scheduled_date, job.scheduled_time_window)
        if visit_start is not None:
            minutes_until_start = int(
                (visit_start - moment.astimezone(visit_start.tzinfo)).total_seconds() // 60
            )
            if (
                job.assigned_staff_id is not None
                and job.status in {"assigned", "accepted", "scheduled"}
                and 0 <= minutes_until_start <= departure_warning_minutes
            ):
                departure_jobs.append({
                    "job_id": str(job.id),
                    "label": _job_label(job),
                    "city": job.city,
                    "scheduled_date": job.scheduled_date.isoformat() if job.scheduled_date else None,
                    "scheduled_time_window": job.scheduled_time_window,
                    "tone": TONE_URGENT,
                    "title": "Technician has not started travelling",
                    "message": (
                        f"The visit starts in {minutes_until_start} minute"
                        f"{'s' if minutes_until_start != 1 else ''}. Contact the technician "
                        "and arrange departure now so arrival can still happen within the slot."
                    ),
                    "alert_kind": "departure",
                    "departure_required": True,
                    "starts_in_minutes": minutes_until_start,
                    "penalty_notice": penalty_notice,
                })

        late_by = urgency_rules.minutes_late(
            job.status, job.scheduled_date, job.scheduled_time_window, moment,
        )
        if late_by is not None:
            delayed.append({
                "job_id": str(job.id),
                "label": _job_label(job),
                "city": job.city,
                "minutes_late": late_by,
                "lateness_label": urgency_rules.describe(late_by),
                "scheduled_date": job.scheduled_date.isoformat() if job.scheduled_date else None,
                "scheduled_time_window": job.scheduled_time_window,
                "tone": TONE_URGENT,
                "title": "Job past its slot",
                "message": (
                    f"{_job_label(job)} is {urgency_rules.describe(late_by)}. "
                    "Reschedule it or update the customer."
                ),
                "alert_kind": "delayed",
                "penalty_notice": (
                    penalty_notice if job.status in {
                        "pending_assignment", "assigned", "accepted", "scheduled", "on_the_way"
                    } else None
                ),
            })

    new_jobs.sort(key=lambda a: a["created_at"], reverse=True)
    departure_jobs.sort(key=lambda a: a["starts_in_minutes"])
    delayed.sort(key=lambda a: a["minutes_late"], reverse=True)

    return {
        # FULL lists. Capping belongs to whatever draws the popup -- when the cap lived
        # here, the notifier only ever saw the first five, so 25 late jobs produced 5
        # notifications and the other 20 were silently never reported.
        "new_jobs": new_jobs,
        "new_job_total": len(new_jobs),
        "departure_jobs": departure_jobs,
        "departure_total": len(departure_jobs),
        "delayed_jobs": delayed,
        "delayed_total": len(delayed),
        # The moment this answer was computed. The dashboard sends it back as `since` on
        # the next poll, which is what makes "new" mean "new to you".
        "as_of": moment.isoformat(),
    }


async def notify_delayed_jobs(db: AsyncSession, tenant_id: uuid.UUID, delayed: list[dict]) -> int:
    """Raises `job.delayed` for jobs that have not been reported yet. Returns how many.

    Idempotent by checking the notification table for an existing event against the same
    job: a dashboard poll every thirty seconds must not become a notification every
    thirty seconds. That check is the whole mechanism -- there is no "already notified"
    flag on the job to drift out of sync with what was actually sent.
    """
    if not delayed:
        return 0

    from app.engines.platform_notifications.models import NotificationEvent
    from app.engines.platform_notifications.notification_service import NotificationService

    job_ids = [uuid.UUID(a["job_id"]) for a in delayed]
    already = {
        row[0] for row in (await db.execute(
            select(NotificationEvent.source_record_id).where(
                NotificationEvent.event_key == EVT_JOB_DELAYED,
                NotificationEvent.source_record_id.in_(job_ids),
            )
        )).all()
    }

    service = NotificationService()
    sent = 0
    for alert in delayed:
        job_id = uuid.UUID(alert["job_id"])
        if job_id in already:
            continue
        await service.fire_event(
            db,
            EVT_JOB_DELAYED,
            {
                "job_number": alert["label"],
                "lateness_label": alert["lateness_label"],
                "scheduled_date": alert.get("scheduled_date"),
                "scheduled_time_window": alert.get("scheduled_time_window"),
            },
            tenant_id=tenant_id,
            source_record_type="service_job",
            source_record_id=job_id,
        )
        sent += 1
    return sent
