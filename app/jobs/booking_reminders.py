"""Idempotent Home Services booking reminders.

The job stores delivery markers on the canonical ServiceJob record. A process
restart or repeated scheduler tick therefore cannot charge an external channel
twice for the same 24-hour/1-hour reminder.
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


async def send_due_reminders() -> dict:
    from app.database import get_session_factory
    from app.engines.admin_catalog.models import MasterService
    from app.engines.final_records.models import ServiceBooking, ServiceJob
    from app.engines.platform_notifications.constants import (
        EVT_BOOKING_REMINDER_1H,
        EVT_BOOKING_REMINDER_24H,
    )
    from app.engines.platform_notifications.notification_service import NotificationService

    now_local = datetime.now(timezone.utc).astimezone(LOCAL_TZ)
    today = now_local.date()
    tomorrow = today + timedelta(days=1)
    sent_24h = sent_1h = 0

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
                    if event is not None:
                        job.reminder_1h_sent_at = datetime.now(timezone.utc)
                        sent_1h += 1

        await db.commit()

    result = {"sent_24h": sent_24h, "sent_1h": sent_1h}
    if sent_24h or sent_1h:
        log.info("booking_reminders.sent", **result)
    return result
