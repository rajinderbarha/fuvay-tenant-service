"""Customer-facing messages for provider-offer failures.

The booking's captured channel identity is authoritative. A customer's latest
chat may be a different Instagram account, so never guess a recipient.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import structlog
from sqlalchemy import select, text

from app.engines.execution.models import ServiceJobExecutionEvent
from app.engines.final_records.models import ServiceBooking, ServiceJob
from app.engines.messaging_gateway import meta_client
from app.engines.messaging_gateway.config_service import messaging_channel_config_service
from app.engines.messaging_gateway.constants import CHANNEL_INSTAGRAM, CUSTOMER_SERVICE_WINDOW_HOURS
from app.engines.messaging_gateway.models import MessagingThread

logger = structlog.get_logger(__name__)
EVENT_TYPE = "customer_assignment_cancelled_notified"


async def booking_thread(db, booking) -> MessagingThread | None:
    """The chat this booking was made in, when we may still message it.

    Scoped to the booking's captured sender: a customer's newest chat can be
    a different Instagram account, and a job update must never be delivered
    to one. Returns None when the booking did not come from chat or the
    24-hour customer-service window has closed.
    """
    channel = str(getattr(booking, "source_channel", "") or "")
    actor = str(getattr(booking, "source_actor_id", "") or "")
    if channel != CHANNEL_INSTAGRAM or not actor or not getattr(booking, "customer_id", None):
        return None
    now = datetime.now(timezone.utc)
    thread = (await db.execute(select(MessagingThread).where(
        MessagingThread.channel == channel,
        MessagingThread.channel_user_id == actor,
        MessagingThread.customer_id == booking.customer_id,
        MessagingThread.opted_out.is_(False),
        MessagingThread.human_handoff.is_(False),
        MessagingThread.last_inbound_at.isnot(None),
        MessagingThread.last_inbound_at >= now - timedelta(hours=CUSTOMER_SERVICE_WINDOW_HOURS),
    ).limit(1))).scalars().first()
    if thread is None or (thread.blocked_until and thread.blocked_until > now):
        return None
    return thread


async def notify_booking_customer(
    db, booking, message: str, *, rows: list[dict] | None = None,
    section_title: str = "Your booking",
) -> bool:
    """Tell the customer about their job, in the chat they booked from.

    Best effort in every sense: an update that cannot be delivered must never
    fail the field operation that raised it, and Instagram simply refuses
    business-initiated messages outside its 24-hour window.
    """
    try:
        thread = await booking_thread(db, booking)
        if thread is None:
            return False
        config = await messaging_channel_config_service.get(
            db, thread.channel, require_enabled=True,
        )
        if not config:
            return False
        if rows:
            result = await meta_client.send_options(
                thread.channel_user_id, message, rows, channel=thread.channel,
                config=config, list_button="Choose", section_title=section_title,
                presentation="quick_replies",
            )
        else:
            result = await meta_client.send_text(
                thread.channel_user_id, message, channel=thread.channel, config=config,
            )
        if not result.get("sent"):
            logger.info("booking_updates.not_sent", booking_id=str(booking.id),
                        reason=result.get("reason"))
            return False
        thread.last_outbound_at = datetime.now(timezone.utc)
        if rows:
            thread.last_options = [str(row.get("id") or "") for row in rows]
        return True
    except Exception as exc:  # noqa: BLE001 - never break field work over a message
        logger.warning("booking_updates.failed", error=str(exc),
                       booking_id=str(getattr(booking, "id", "-")))
        return False


async def notify_job_customer(db, job, message: str, **kwargs) -> bool:
    """`notify_booking_customer`, resolved from the job's booking."""
    booking_id = getattr(job, "booking_id", None)
    if not booking_id:
        return False
    booking = await db.get(ServiceBooking, booking_id)
    if booking is None:
        return False
    return await notify_booking_customer(db, booking, message, **kwargs)


# ── The updates a customer is owed while their job runs ──────────────────────
#
# The booking confirmation promises "we will message you when a technician is
# assigned", and closure cannot finish until the customer confirms handover
# and payment. None of that reached an Instagram customer before: the only
# other notifier is the in-app NotificationService, which has no chat channel,
# so chat-only customers heard nothing and jobs stalled at work_done.


def _track_row() -> dict:
    from app.engines.messaging_gateway.constants import PICK_TRACK, PICKER_SEP
    return {"id": f"{PICK_TRACK}{PICKER_SEP}", "title": "Track booking"}


async def _technician_name(db, job) -> str:
    from app.engines.home_service_assignment.staff_model import ProviderTeamMember
    staff_id = getattr(job, "assigned_staff_id", None)
    if not staff_id:
        return "Your technician"
    member = await db.get(ProviderTeamMember, staff_id)
    name = getattr(member, "full_name", None)
    if not name:
        from app.engines.auth.models import User
        user = await db.get(User, staff_id)
        name = getattr(user, "full_name", None)
    return str(name or "Your technician")


async def send_technician_assigned(db, job) -> bool:
    booking = await db.get(ServiceBooking, job.booking_id) if job.booking_id else None
    if booking is None:
        return False
    name = await _technician_name(db, job)
    when = ""
    if getattr(job, "scheduled_date", None):
        when = f" on {job.scheduled_date.isoformat()}"
        if job.scheduled_time_window:
            when += f", {job.scheduled_time_window}"
    return await notify_booking_customer(
        db, booking,
        f"{name} is assigned to booking {booking.booking_number}{when}.",
        rows=[_track_row()], section_title="Your technician",
    )


async def send_on_the_way(db, job) -> bool:
    name = await _technician_name(db, job)
    return await notify_job_customer(
        db, job, f"{name} is on the way to you now.",
        rows=[_track_row()], section_title="Your technician",
    )


async def send_arrived(db, job) -> bool:
    name = await _technician_name(db, job)
    return await notify_job_customer(
        db, job, f"{name} has arrived for your service.",
        rows=[_track_row()], section_title="Your technician",
    )


async def send_handover_request(db, job, *, reminder: bool = False) -> bool:
    from app.engines.messaging_gateway.constants import (
        PICK_COMPLAINT, PICK_HANDOVER, PICKER_SEP,
    )
    from app.engines.messaging_gateway.flow import HANDOVER_ACK_ROW, HANDOVER_HEADER
    lead = "Reminder: " if reminder else ""
    return await notify_job_customer(
        db, job, f"{lead}{HANDOVER_HEADER}",
        rows=[
            {"id": PICKER_SEP.join((PICK_HANDOVER, str(job.id), "acknowledge")),
             "title": HANDOVER_ACK_ROW},
            {"id": PICKER_SEP.join((PICK_COMPLAINT, "new")), "title": "Report a problem"},
        ],
        section_title="Service handover",
    )


async def send_payment_request(db, job, pay, *, reminder: bool = False) -> bool:
    from app.engines.messaging_gateway.constants import PICK_PAYMENT, PICKER_SEP
    from app.engines.messaging_gateway.flow import (
        PAYMENT_CONFIRM_ROW, PAYMENT_NOT_PAID_ROW, _money,
    )
    amount = _money(getattr(pay, "currency", "INR") or "INR", pay.collected_amount)
    lead = "Reminder: " if reminder else ""
    return await notify_job_customer(
        db, job,
        f"{lead}Your provider recorded a direct payment of {amount} for this service. "
        "You paid the provider directly; Fuvay did not collect this money.",
        rows=[
            {"id": PICKER_SEP.join((PICK_PAYMENT, str(pay.id), "confirm")),
             "title": PAYMENT_CONFIRM_ROW},
            {"id": PICKER_SEP.join((PICK_PAYMENT, str(pay.id), "review_not_paid")),
             "title": PAYMENT_NOT_PAID_ROW},
        ],
        section_title="Direct payment",
    )


async def send_provider_cancelled(db, job, reason: str | None) -> bool:
    from app.engines.messaging_gateway.constants import PICK_RESTART, PICKER_SEP
    booking = await db.get(ServiceBooking, job.booking_id) if job.booking_id else None
    if booking is None:
        return False
    why = f" Reason: {reason.strip()}" if (reason or "").strip() else ""
    return await notify_booking_customer(
        db, booking,
        f"Booking {booking.booking_number} was cancelled by the provider.{why} "
        "We are sorry for the inconvenience — you can book another slot below.",
        rows=[{"id": f"{PICK_RESTART}{PICKER_SEP}1", "title": "Book again"}],
        section_title="Booking cancelled",
    )


async def send_visit_reminder(db, job, when_label: str) -> bool:
    name = await _technician_name(db, job)
    return await notify_job_customer(
        db, job, f"Reminder: {name} is scheduled to visit you {when_label}.",
        rows=[_track_row()], section_title="Visit reminder",
    )


async def send_assignment_cancelled(job_id: str | uuid.UUID) -> bool:
    """Notify the exact booking sender; retryable and safe after a worker restart."""
    from app.database import get_session_factory

    try:
        async with get_session_factory()() as db:
            locked = await db.scalar(text(
                "SELECT pg_try_advisory_xact_lock(hashtextextended(:key, 0))"
            ), {"key": f"ig:assignment_cancelled:{job_id}"})
            if not locked:
                return False
            job = await db.get(ServiceJob, uuid.UUID(str(job_id)))
            if (not job or job.status != "cancelled"
                    or not (job.failure_reason or "").startswith(
                        "Closed because no alternative provider")):
                return False
            booking = await db.get(ServiceBooking, job.booking_id)
            if (not booking or booking.source_channel != CHANNEL_INSTAGRAM
                    or not booking.source_actor_id or not booking.customer_id):
                return False
            already = await db.scalar(select(ServiceJobExecutionEvent.id).where(
                ServiceJobExecutionEvent.job_id == job.id,
                ServiceJobExecutionEvent.event_type == EVENT_TYPE,
            ).limit(1))
            if already:
                return True
            now = datetime.now(timezone.utc)
            thread = (await db.execute(select(MessagingThread).where(
                MessagingThread.channel == CHANNEL_INSTAGRAM,
                MessagingThread.channel_user_id == booking.source_actor_id,
                MessagingThread.customer_id == booking.customer_id,
                MessagingThread.opted_out.is_(False),
                MessagingThread.human_handoff.is_(False),
                MessagingThread.last_inbound_at >= now - timedelta(hours=CUSTOMER_SERVICE_WINDOW_HOURS),
            ).limit(1))).scalars().first()
            if not thread or (thread.blocked_until and thread.blocked_until > now):
                return False
            config = await messaging_channel_config_service.get(db, CHANNEL_INSTAGRAM, require_enabled=True)
            if not config:
                return False
            message = (
                f"Booking {booking.booking_number} was cancelled because the provider did not "
                "assign a technician within the required time, and no other available "
                "provider could take the job. We are sorry for the inconvenience. "
                "Please start a new booking for another slot, or reply /human for help."
            )
            result = await meta_client.send_text(
                thread.channel_user_id, message, channel=CHANNEL_INSTAGRAM, config=config,
            )
            if not result.get("sent"):
                logger.warning("booking_updates.cancel_send_failed", job_id=str(job.id), reason=result.get("reason"))
                return False
            thread.last_outbound_at = now
            db.add(ServiceJobExecutionEvent(
                booking_id=booking.id, job_id=job.id, tenant_id=job.tenant_id,
                actor_role="platform", event_type=EVENT_TYPE,
                notes="Assignment cancellation sent to booking's Instagram identity.",
                request_id="job:provider_assignment_timeout",
            ))
            await db.commit()
            return True
    except Exception as exc:  # noqa: BLE001 - notification must not stop the sweeper
        logger.warning("booking_updates.cancel_failed", job_id=str(job_id), error=str(exc))
        return False
