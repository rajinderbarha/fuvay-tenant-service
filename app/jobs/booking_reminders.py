"""Idempotent Home Services booking and visit reminders.

The job stores delivery markers on the canonical ServiceJob record. A process
restart or repeated scheduler tick therefore cannot charge an external channel
twice for the same customer or operational reminder.
"""
from __future__ import annotations

import re
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

import structlog
from sqlalchemy import select

log = structlog.get_logger("jobs.booking_reminders")
LOCAL_TZ = ZoneInfo("Asia/Kolkata")
ACTIVE_STATUSES = {"pending_assignment", "assigned", "accepted", "scheduled"}


def _start_time(window: str | None) -> time | None:
    if not window:
        return None
    twelve_hour = re.search(
        r"(?:^|\s)(1[0-2]|0?[1-9])(?::([0-5]\d))?\s*([ap])\.?m\.?",
        window,
        re.IGNORECASE,
    )
    if twelve_hour:
        hour = int(twelve_hour.group(1)) % 12
        if twelve_hour.group(3).lower() == "p":
            hour += 12
        return time(hour, int(twelve_hour.group(2) or 0))
    match = re.search(r"(?:^|\s)([01]?\d|2[0-3])[:.]([0-5]\d)", window)
    if not match:
        return None
    return time(int(match.group(1)), int(match.group(2)))


async def _operational_recipients(db, job) -> tuple[list[dict], list[dict]]:
    """Resolve active provider owners and the assigned technician account.

    ``assigned_staff_id`` is normally a provider_team_members id, while older
    jobs can contain the linked users.id. Supporting both prevents a legacy job
    from silently losing its visit reminder.
    """
    from app.engines.auth.models import User
    from app.engines.home_service_assignment.staff_model import ProviderTeamMember

    owners = (await db.execute(
        select(User.id).where(
            User.tenant_id == job.tenant_id,
            User.role == "tenant_owner",
            User.is_active.is_(True),
            User.deleted_at.is_(None),
        )
    )).scalars().all()
    provider_recipients = [
        {"user_id": str(user_id), "recipient_type": "provider"}
        for user_id in dict.fromkeys(owners)
    ]

    staff_recipients: list[dict] = []
    if job.assigned_staff_id:
        linked_user_id = (await db.execute(
            select(ProviderTeamMember.user_id).where(
                ProviderTeamMember.id == job.assigned_staff_id,
                ProviderTeamMember.tenant_id == job.tenant_id,
                ProviderTeamMember.status == "active",
                ProviderTeamMember.deleted_at.is_(None),
            )
        )).scalar_one_or_none()
        candidate_user_id = linked_user_id or job.assigned_staff_id
        staff_user_id = (await db.execute(
            select(User.id).where(
                User.id == candidate_user_id,
                User.tenant_id == job.tenant_id,
                User.is_active.is_(True),
                User.deleted_at.is_(None),
            )
        )).scalar_one_or_none()
        if staff_user_id:
            staff_recipients.append({"user_id": str(staff_user_id), "recipient_type": "staff"})

    return provider_recipients, staff_recipients


async def _existing_operational_reminder(db, job_id, recipient_type: str) -> datetime | None:
    """Recover the marker if the event committed before the worker restarted."""
    from app.engines.platform_notifications.constants import EVT_JOB_VISIT_REMINDER_30M
    from app.engines.platform_notifications.models import NotificationEvent, NotificationOutbox

    return (await db.execute(
        select(NotificationEvent.created_at)
        .join(NotificationOutbox, NotificationOutbox.notification_event_id == NotificationEvent.id)
        .where(
            NotificationEvent.event_key == EVT_JOB_VISIT_REMINDER_30M,
            NotificationEvent.source_record_type == "service_job",
            NotificationEvent.source_record_id == job_id,
            NotificationOutbox.recipient_type == recipient_type,
        )
        .limit(1)
    )).scalar_one_or_none()


async def send_due_reminders() -> dict:
    from app.database import get_session_factory
    from app.engines.admin_catalog.models import MasterService
    from app.engines.final_records.models import ServiceBooking, ServiceJob
    from app.engines.platform_notifications.constants import (
        EVT_BOOKING_REMINDER_1H,
        EVT_BOOKING_REMINDER_24H,
        EVT_JOB_VISIT_REMINDER_30M,
    )
    from app.engines.platform_notifications.notification_service import NotificationService
    from app.engines.messaging_gateway.booking_updates import send_visit_reminder

    now_local = datetime.now(timezone.utc).astimezone(LOCAL_TZ)
    today = now_local.date()
    tomorrow = today + timedelta(days=1)
    sent_24h = sent_1h = sent_provider_30m = sent_staff_30m = 0

    session_factory = get_session_factory()
    async with session_factory() as db:
        rows = (await db.execute(
            select(ServiceJob, ServiceBooking, MasterService)
            .join(ServiceBooking, ServiceBooking.id == ServiceJob.booking_id)
            .outerjoin(MasterService, MasterService.id == ServiceJob.offering_id)
            .where(
                ServiceJob.status.in_(ACTIVE_STATUSES),
                ServiceJob.customer_id.is_not(None),
                ServiceJob.scheduled_date.in_([today, tomorrow]),
            )
            # Only the durable reminder markers on ServiceJob are mutated.
            # PostgreSQL rejects an unqualified FOR UPDATE when this query
            # contains the nullable MasterService outer join.
            .with_for_update(of=ServiceJob, skip_locked=True)
        )).all()

        notifier = NotificationService()
        for job, booking, offering in rows:
            service_name = offering.service_name if offering else "home service"
            payload = {
                "booking_id": str(booking.id),
                "booking_number": booking.booking_number,
                "service_name": service_name,
                "date": job.scheduled_date.isoformat(),
                "time": job.scheduled_time_window or "your scheduled time",
            }
            recipient = [{"user_id": str(job.customer_id), "recipient_type": "customer"}]

            if job.scheduled_date == tomorrow and job.reminder_24h_sent_at is None:
                event = await notifier.fire_event(
                    db, EVT_BOOKING_REMINDER_24H, payload,
                    tenant_id=job.tenant_id, customer_id=job.customer_id,
                    source_record_type="service_booking", source_record_id=booking.id,
                    recipients=recipient,
                )
                # The in-app notification never reaches a customer who booked
                # on Instagram and has no app; send it to that chat too.
                await send_visit_reminder(db, job, "tomorrow")
                if event is not None:
                    job.reminder_24h_sent_at = datetime.now(timezone.utc)
                    sent_24h += 1

            start = _start_time(job.scheduled_time_window)
            if job.scheduled_date == today and start and job.reminder_1h_sent_at is None:
                starts_at = datetime.combine(today, start, LOCAL_TZ)
                minutes_until = (starts_at - now_local).total_seconds() / 60
                if 0 <= minutes_until <= 75:
                    event = await notifier.fire_event(
                        db, EVT_BOOKING_REMINDER_1H, payload,
                        tenant_id=job.tenant_id, customer_id=job.customer_id,
                        source_record_type="service_booking", source_record_id=booking.id,
                        recipients=recipient,
                    )
                    await send_visit_reminder(
                        db, job, f"today at {job.scheduled_time_window or 'your booked time'}",
                    )
                    if event is not None:
                        job.reminder_1h_sent_at = datetime.now(timezone.utc)
                        sent_1h += 1

            if job.scheduled_date == today and start:
                starts_at = datetime.combine(today, start, LOCAL_TZ)
                minutes_until = (starts_at - now_local).total_seconds() / 60
                if 0 < minutes_until <= 30:
                    provider_recipients, staff_recipients = await _operational_recipients(db, job)

                    if job.provider_reminder_30m_sent_at is None and provider_recipients:
                        job.provider_reminder_30m_sent_at = await _existing_operational_reminder(
                            db, job.id, "provider"
                        )
                    if job.provider_reminder_30m_sent_at is None and provider_recipients:
                        provider_payload = {
                            **payload,
                            "job_id": str(job.id),
                            "action_url": f"/home-services/bookings-jobs?job_id={job.id}",
                            "visit_instruction": (
                                "Confirm the assigned technician is ready and on route."
                                if job.assigned_staff_id
                                else "No technician is assigned. Assign one now to protect the visit."
                            ),
                        }
                        event = await notifier.fire_event(
                            db, EVT_JOB_VISIT_REMINDER_30M, provider_payload,
                            tenant_id=job.tenant_id,
                            source_record_type="service_job", source_record_id=job.id,
                            recipients=provider_recipients,
                        )
                        if event is not None:
                            job.provider_reminder_30m_sent_at = datetime.now(timezone.utc)
                            sent_provider_30m += 1

                    if job.staff_reminder_30m_sent_at is None and staff_recipients:
                        job.staff_reminder_30m_sent_at = await _existing_operational_reminder(
                            db, job.id, "staff"
                        )
                    if job.staff_reminder_30m_sent_at is None and staff_recipients:
                        staff_payload = {
                            **payload,
                            "job_id": str(job.id),
                            "action_url": f"/staff/jobs/{job.id}",
                            "visit_instruction": "Open the job, confirm your route and prepare for the visit.",
                        }
                        event = await notifier.fire_event(
                            db, EVT_JOB_VISIT_REMINDER_30M, staff_payload,
                            tenant_id=job.tenant_id,
                            source_record_type="service_job", source_record_id=job.id,
                            recipients=staff_recipients,
                        )
                        if event is not None:
                            job.staff_reminder_30m_sent_at = datetime.now(timezone.utc)
                            sent_staff_30m += 1

        await db.commit()

    result = {
        "sent_24h": sent_24h,
        "sent_1h": sent_1h,
        "sent_provider_30m": sent_provider_30m,
        "sent_staff_30m": sent_staff_30m,
    }
    if any(result.values()):
        log.info("booking_reminders.sent", **result)
    return result
