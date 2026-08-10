"""What the provider's dashboard should interrupt them about.

Two kinds of thing, and they are deliberately not the same shape of message:

* A NEW job has arrived. That is good news and worth celebrating -- it is money, and a
  provider who does not notice it for an hour has kept a customer waiting for nothing.
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

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.home_service_assignment import urgency as urgency_rules
from app.engines.platform_notifications.constants import (
    EVT_JOB_DELAYED, SEV_SUCCESS, SEV_WARNING,
)

TONE_CELEBRATE = SEV_SUCCESS
TONE_URGENT = SEV_WARNING

# How far back "new" reaches when the client does not say when it last looked. Long
# enough to catch a job that arrived while the dashboard was closed over lunch, short
# enough that reopening the page tomorrow does not congratulate anyone for yesterday.
NEW_JOB_WINDOW_HOURS = 12

# The dashboard interrupts with a popup; a queue of them is not an interruption, it is an
# obstacle. Applied by the ROUTER when it builds the response, never before the notifier
# runs -- every late job must be reported even if only a few are shown.
MAX_ALERTS = 5


async def _load_jobs(db: AsyncSession, tenant_id: uuid.UUID):
    from app.engines.final_records.models import ServiceJob

    return (await db.execute(
        select(
            ServiceJob.id, ServiceJob.job_number, ServiceJob.status,
            ServiceJob.scheduled_date, ServiceJob.scheduled_time_window,
            ServiceJob.created_at, ServiceJob.city,
        ).where(ServiceJob.tenant_id == tenant_id)
    )).all()


def _job_label(job) -> str:
    """What to call the job in a one-line alert. Its number, which is what a provider
    searches by -- never an internal id."""
    return job.job_number or f"Job {str(job.id)[:8]}"


async def build_alerts(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    since: dt.datetime | None = None,
    now: dt.datetime | None = None,
) -> dict:
    """The dashboard's alerts, newest-and-worst first.

    `since` is when this dashboard last looked. Passing it is what stops a provider being
    congratulated twice for the same job every time they refresh; without it, a stated
    window is used rather than "everything", because "42 new jobs!" on a first login is
    not news, it is a backlog.

    Delayed jobs are ranked by how late they are, so the worst is the one that gets seen.
    """
    moment = now or dt.datetime.now(dt.timezone.utc)
    cutoff = since or (moment - dt.timedelta(hours=NEW_JOB_WINDOW_HOURS))

    jobs = await _load_jobs(db, tenant_id)

    new_jobs = []
    delayed = []
    for job in jobs:
        created = job.created_at
        if created is not None:
            if created.tzinfo is None:
                created = created.replace(tzinfo=dt.timezone.utc)
            # Any job that ARRIVED recently and is still live counts as new.
            #
            # This used to require `pending_assignment`, which made the whole feature
            # silent on this platform: bookings come in already `accepted`, so a service
            # booked from the customer app produced no popup at all -- verified live, the
            # newest three bookings were all "accepted" within minutes of being made and
            # `new_job_total` was 0. Arrival is the news, not the assignment state; the
            # only exclusions are jobs already finished or cancelled, where congratulating
            # anyone would be absurd.
            if created > cutoff and str(job.status or "").lower() not in urgency_rules.TERMINAL_STATUSES:
                new_jobs.append({
                    "job_id": str(job.id),
                    "label": _job_label(job),
                    "city": job.city,
                    "created_at": created.isoformat(),
                    "tone": TONE_CELEBRATE,
                    "title": "New job received",
                    "message": f"{_job_label(job)} just came in. Assign a technician to get started.",
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
            })

    new_jobs.sort(key=lambda a: a["created_at"], reverse=True)
    delayed.sort(key=lambda a: a["minutes_late"], reverse=True)

    return {
        # FULL lists. Capping belongs to whatever draws the popup -- when the cap lived
        # here, the notifier only ever saw the first five, so 25 late jobs produced 5
        # notifications and the other 20 were silently never reported.
        "new_jobs": new_jobs,
        "new_job_total": len(new_jobs),
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
