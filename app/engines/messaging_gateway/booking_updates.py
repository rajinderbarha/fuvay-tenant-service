"""Customer-facing messages for provider-offer failures.

The booking's captured channel identity is authoritative. A customer's latest
chat may be a different Instagram account, so never guess a recipient.
"""
from __future__ import annotations

import functools
import uuid
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

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
# One "your technician" message per technician, wherever it is raised from.
ASSIGNED_EVENT_TYPE = "customer_technician_assigned_notified"
TECHNICIAN_UNAVAILABLE_EVENT_TYPE = "customer_technician_unavailable_notified"
SLA_CANCELLED_EVENT_TYPE = "customer_sla_cancelled_notified"
PROVIDER_CANCELLED_EVENT_TYPE = "customer_provider_cancelled_notified"
LOCAL_TZ = ZoneInfo("Asia/Kolkata")


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


def _best_effort(send):
    """A job update must never fail the field operation that raised it.

    `notify_booking_customer` already swallows delivery errors, but these
    senders also look up the technician and past announcements first, and
    they run inside assignment, travel start and arrival.
    """
    @functools.wraps(send)
    async def wrapper(db, job, *args, **kwargs):
        try:
            return await send(db, job, *args, **kwargs)
        except Exception as exc:  # noqa: BLE001 - never break field work over a message
            logger.warning("booking_updates.state_message_failed", sender=send.__name__,
                           job_id=str(getattr(job, "id", "-")), error=str(exc))
            return False
    return wrapper


def visit_label(job) -> str:
    """The visit in the customer's words: "today at 10:00-12:00".

    Every update about a visit uses this one phrasing, so the reminder and
    the assigned/on-the-way/arrived messages can never describe the same
    visit two different ways. Dates are read in IST, the only timezone these
    bookings are taken in. Empty when the booking has no date yet: "scheduled
    to visit you" would then be a promise nothing backs.
    """
    scheduled = getattr(job, "scheduled_date", None)
    if isinstance(scheduled, datetime):
        scheduled = scheduled.date()
    if not isinstance(scheduled, date):
        return ""
    today = datetime.now(timezone.utc).astimezone(LOCAL_TZ).date()
    if scheduled == today:
        day = "today"
    elif scheduled == today + timedelta(days=1):
        day = "tomorrow"
    elif scheduled == today - timedelta(days=1):
        day = "yesterday"
    else:
        day = f"on {scheduled.strftime('%d %b')}"
    window = str(getattr(job, "scheduled_time_window", "") or "").strip()
    return f"{day} at {window}" if window else day


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


@_best_effort
async def send_technician_assigned(db, job) -> bool:
    """Name the technician who is coming, and when, once per technician.

    Assignment and the technician's own acceptance both reach this, seconds
    apart, and a reassignment reaches it again with a different name. Sending
    every time would stack near-identical messages in the chat, so a delivered
    announcement is recorded against the technician it named: a genuinely new
    technician is announced, the same one is not announced twice. A send that
    never reached the customer records nothing, so the next state still can.
    """
    # Never announce an impossible visit. Assignment mutation blocks this too,
    # but the notifier is deliberately defensive because legacy/admin callers
    # may invoke it directly.
    from app.engines.weather.slots import slot_has_ended
    if slot_has_ended(
        getattr(job, "scheduled_date", None),
        getattr(job, "scheduled_time_window", None),
    ):
        logger.warning(
            "booking_updates.expired_assignment_suppressed",
            job_id=str(getattr(job, "id", "-")),
        )
        return False
    booking = await db.get(ServiceBooking, job.booking_id) if job.booking_id else None
    if booking is None:
        return False
    staff_id = getattr(job, "assigned_staff_id", None)
    if staff_id is not None:
        already = await db.scalar(select(ServiceJobExecutionEvent.id).where(
            ServiceJobExecutionEvent.job_id == job.id,
            ServiceJobExecutionEvent.event_type == ASSIGNED_EVENT_TYPE,
            ServiceJobExecutionEvent.staff_member_id == staff_id,
        ).limit(1))
        if already:
            return False
    name = await _technician_name(db, job)
    visit = visit_label(job)
    when = f" They are scheduled to visit you {visit}." if visit else ""
    sent = await notify_booking_customer(
        db, booking,
        f"{name} is assigned to booking {booking.booking_number}.{when}",
        rows=[_track_row()], section_title="Your technician",
    )
    if sent and staff_id is not None:
        db.add(ServiceJobExecutionEvent(
            booking_id=booking.id, job_id=job.id, tenant_id=job.tenant_id,
            staff_member_id=staff_id, actor_role="platform",
            event_type=ASSIGNED_EVENT_TYPE,
            notes=f"Technician announced to the booking's {booking.source_channel} chat.",
        ))
    return sent


@_best_effort
async def send_on_the_way(db, job) -> bool:
    name = await _technician_name(db, job)
    visit = visit_label(job)
    when = f" Your visit is scheduled {visit}." if visit else ""
    return await notify_job_customer(
        db, job, f"{name} is on the way to you now.{when}",
        rows=[_track_row()], section_title="Your technician",
    )


@_best_effort
async def send_arrived(db, job) -> bool:
    name = await _technician_name(db, job)
    visit = visit_label(job)
    what = f"your visit {visit}" if visit else "your service"
    return await notify_job_customer(
        db, job, f"{name} has arrived for {what}.",
        rows=[_track_row()], section_title="Your technician",
    )


async def send_arrival_confirmation_request(db, job, challenge, code: str) -> bool:
    """Ask the captured Instagram identity to verify the doorstep claim.

    The OTP is intentionally delivered only here; it is never returned to the
    technician API or placed in an execution event.
    """
    from app.engines.messaging_gateway.constants import PICK_ARRIVAL, PICKER_SEP

    name = await _technician_name(db, job)
    ttl_seconds = max(60, int((challenge.expires_at - challenge.requested_at).total_seconds()))
    ttl_minutes = max(1, round(ttl_seconds / 60))
    return await notify_job_customer(
        db, job,
        f"{name} says they are at your service location.\n\n"
        "ਕੀ technician ਤੁਹਾਡੇ ਸਾਹਮਣੇ ਪਹੁੰਚ ਗਿਆ ਹੈ? Confirm only after you can "
        f"see them. Your one-time arrival code is {code}. It expires in {ttl_minutes} minutes. "
        "Do not share this code over a phone call.",
        rows=[
            {"id": PICKER_SEP.join((PICK_ARRIVAL, str(challenge.id), "confirm")),
             "title": "Yes, arrived"},
            {"id": PICKER_SEP.join((PICK_ARRIVAL, str(challenge.id), "deny")),
             "title": "No, not here"},
        ],
        section_title="Confirm arrival",
    )


@_best_effort
async def send_arrival_confirmed(db, job) -> bool:
    return await notify_job_customer(
        db, job,
        "Arrival is verified. The technician can now begin inspection or the approved service.",
        rows=[_track_row()], section_title="Arrival verified",
    )


async def send_reschedule_approval_request(db, job, request) -> bool:
    """Send the provider's proposed slot to the exact booking Instagram chat."""
    from app.engines.messaging_gateway.constants import (
        PICKER_SEP, PICK_RESCHEDULE,
    )

    booking = await db.get(ServiceBooking, job.booking_id)
    if booking is None:
        return False
    original = " · ".join(filter(None, (
        str(request.original_date or ""), str(request.original_slot or ""),
    )))
    proposed = " · ".join(filter(None, (
        str(request.requested_date or ""), str(request.requested_slot or ""),
    )))
    expiry = request.expires_at.astimezone(LOCAL_TZ).strftime("%d %b, %I:%M %p")
    return await notify_booking_customer(
        db, booking,
        f"Your provider requested a new visit slot for {booking.booking_number}.\n\n"
        f"Current: {original}\nRequested: {proposed}\nReason: {request.reason}\n\n"
        f"Your current slot stays confirmed unless you approve. Request expires {expiry}.",
        rows=[
            {"id": PICKER_SEP.join((PICK_RESCHEDULE, str(request.id), "approve")),
             "title": "Approve new slot"},
            {"id": PICKER_SEP.join((PICK_RESCHEDULE, str(request.id), "reject")),
             "title": "Keep current slot"},
        ],
        section_title="Visit slot approval",
    )


async def send_provider_cancellation_confirmation_request(db, job, request) -> bool:
    """Ask the exact booking identity to confirm a provider cancellation claim."""
    from app.engines.messaging_gateway.constants import (
        PICKER_SEP, PICK_PROVIDER_CANCEL,
    )

    booking = await db.get(ServiceBooking, job.booking_id)
    if booking is None:
        return False
    expiry = request.expires_at.astimezone(LOCAL_TZ).strftime("%d %b, %I:%M %p")
    return await notify_booking_customer(
        db, booking,
        f"Your provider says you requested cancellation of {booking.booking_number}.\n\n"
        f"Reason: {request.reason_label}\n\n"
        "Confirm only if you asked to cancel. Your booking and SLA remain active "
        f"until you confirm. This request expires {expiry}.",
        rows=[
            {"id": PICKER_SEP.join((PICK_PROVIDER_CANCEL, str(request.id), "approve")),
             "title": "Yes, cancel booking"},
            {"id": PICKER_SEP.join((PICK_PROVIDER_CANCEL, str(request.id), "reject")),
             "title": "No, keep booking"},
        ],
        section_title="Confirm cancellation",
    )


_STAGE_MESSAGES = {
    "scheduled": ("Your visit schedule has been updated.", "Visit scheduled"),
    "inspection_started": (
        "The technician has started the inspection. We will message you before any quoted work begins.",
        "Inspection started",
    ),
    "inspection_done": (
        "The inspection is complete. If an estimate is required, approve it here before work begins.",
        "Inspection complete",
    ),
    "quote_required": (
        "The technician is preparing an estimate or parts request. Work cannot continue without the required approval.",
        "Approval required",
    ),
    "service_started": (
        "The approved service work has started.", "Work started",
    ),
    "work_done": (
        "The technician marked the work as done. Review the completion proof, handover and payment request before closure.",
        "Work marked done",
    ),
    "customer_not_available": (
        "The technician reported that the customer was unavailable. Contact the provider to reschedule or resolve the visit.",
        "Customer unavailable",
    ),
}


@_best_effort
async def send_stage_update(db, job, stage: str) -> bool:
    """Send one idempotent customer update for a meaningful field stage."""
    content = _STAGE_MESSAGES.get(stage)
    if not content:
        return False
    event_type = f"customer_{stage}_notified"[:60]
    exists = await db.scalar(select(ServiceJobExecutionEvent.id).where(
        ServiceJobExecutionEvent.job_id == job.id,
        ServiceJobExecutionEvent.event_type == event_type,
    ).limit(1))
    if exists:
        return False
    message, title = content
    sent = await notify_job_customer(
        db, job, message, rows=[_track_row()], section_title=title,
    )
    if sent:
        db.add(ServiceJobExecutionEvent(
            booking_id=job.booking_id, job_id=job.id, tenant_id=job.tenant_id,
            staff_member_id=job.assigned_staff_id, actor_role="platform",
            event_type=event_type, old_status=job.status, new_status=job.status,
            notes=f"Customer notified of {stage.replace('_', ' ')}.",
        ))
        await db.flush()
    return sent


@_best_effort
async def send_stage_delay(
    db, job, *, stage: str, critical: bool, waiting_on: str,
) -> bool:
    """Keep an Instagram customer informed when a live visit stops moving."""
    stage_label = stage.replace("_", " ")
    if waiting_on == "customer":
        message = (
            f"Booking {job.job_number} is waiting for your confirmation at "
            f"the {stage_label} step. ਕਿਰਪਾ ਕਰਕੇ chat ਵਿੱਚ pending approval complete ਕਰੋ."
        )
        title = "Your action is needed"
    elif critical:
        message = (
            f"Booking {job.job_number} is delayed at the {stage_label} step. "
            "ਅਸੀਂ provider ਨੂੰ urgent action ਲਈ alert ਕਰ ਦਿੱਤਾ ਹੈ."
        )
        title = "Service delay update"
    else:
        message = (
            f"Booking {job.job_number} has not progressed from {stage_label}. "
            "Provider ਨੂੰ check ਕਰਨ ਲਈ alert ਕੀਤਾ ਗਿਆ ਹੈ; status ਇੱਥੇ track ਕਰੋ."
        )
        title = "Service status update"
    return await notify_job_customer(
        db, job, message, rows=[_track_row()], section_title=title,
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


async def send_provider_cancelled_once(job_id: str | uuid.UUID) -> bool:
    """Deliver a committed provider cancellation exactly once.

    The provider endpoint calls this only after its business transaction has
    committed. The advisory lock and durable execution-event marker make an
    endpoint retry and the background recovery worker safe to run together.
    """
    from app.database import get_session_factory

    try:
        async with get_session_factory()() as db:
            locked = await db.scalar(text(
                "SELECT pg_try_advisory_xact_lock(hashtextextended(:key, 0))"
            ), {"key": f"ig:provider_cancelled:{job_id}"})
            if not locked:
                return False
            job = await db.get(ServiceJob, uuid.UUID(str(job_id)))
            if not job or job.status != "cancelled":
                return False
            already = await db.scalar(select(ServiceJobExecutionEvent.id).where(
                ServiceJobExecutionEvent.job_id == job.id,
                ServiceJobExecutionEvent.event_type == PROVIDER_CANCELLED_EVENT_TYPE,
            ).limit(1))
            if already:
                return True
            cancellation = await db.scalar(select(ServiceJobExecutionEvent).where(
                ServiceJobExecutionEvent.job_id == job.id,
                ServiceJobExecutionEvent.event_type == "job_cancelled",
                ServiceJobExecutionEvent.actor_role == "provider",
            ).order_by(ServiceJobExecutionEvent.created_at.desc()).limit(1))
            if cancellation is None:
                return False
            booking = await db.get(ServiceBooking, job.booking_id) if job.booking_id else None
            if booking is None:
                return False
            reason = cancellation.notes or job.failure_reason
            if not await send_provider_cancelled(db, job, reason):
                return False
            db.add(ServiceJobExecutionEvent(
                booking_id=booking.id, job_id=job.id, tenant_id=job.tenant_id,
                staff_member_id=job.assigned_staff_id, actor_role="platform",
                event_type=PROVIDER_CANCELLED_EVENT_TYPE,
                old_status="cancelled", new_status="cancelled",
                notes=f"Provider cancellation sent to the booking's {booking.source_channel} chat.",
                event_metadata={"channel": booking.source_channel},
                request_id="job:instagram_cancellation_followup",
            ))
            await db.commit()
            return True
    except Exception as exc:  # noqa: BLE001 - delivery must not roll back cancellation
        logger.warning("booking_updates.provider_cancelled_failed",
                       job_id=str(job_id), error=str(exc))
        return False


async def send_technician_unavailable_cancelled(job_id: str | uuid.UUID) -> bool:
    """Tell the booking's chat that the technician never arrived, once.

    Called by the travel-timeout sweep after its cancellation commits, in a
    session of its own, so a failed send cannot roll the cancellation back.
    The delivered message is recorded, so a retry after a worker restart does
    not repeat it.
    """
    from app.database import get_session_factory
    from app.engines.messaging_gateway.constants import PICK_RESTART, PICKER_SEP
    from app.jobs.travel_timeout import FAILURE_REASON_PREFIX

    try:
        async with get_session_factory()() as db:
            locked = await db.scalar(text(
                "SELECT pg_try_advisory_xact_lock(hashtextextended(:key, 0))"
            ), {"key": f"ig:technician_unavailable:{job_id}"})
            if not locked:
                return False
            job = await db.get(ServiceJob, uuid.UUID(str(job_id)))
            if (not job or job.status != "cancelled"
                    or not (job.failure_reason or "").startswith(FAILURE_REASON_PREFIX)):
                return False
            booking = await db.get(ServiceBooking, job.booking_id) if job.booking_id else None
            if booking is None:
                return False
            already = await db.scalar(select(ServiceJobExecutionEvent.id).where(
                ServiceJobExecutionEvent.job_id == job.id,
                ServiceJobExecutionEvent.event_type == TECHNICIAN_UNAVAILABLE_EVENT_TYPE,
            ).limit(1))
            if already:
                return True
            sent = await notify_booking_customer(
                db, booking,
                f"Booking {booking.booking_number} has been cancelled because the "
                "technician is not available. We are sorry for the inconvenience. "
                "You can book another slot below.",
                rows=[{"id": f"{PICK_RESTART}{PICKER_SEP}1", "title": "Book again"}],
                section_title="Booking cancelled",
            )
            if not sent:
                return False
            db.add(ServiceJobExecutionEvent(
                booking_id=booking.id, job_id=job.id, tenant_id=job.tenant_id,
                actor_role="platform", event_type=TECHNICIAN_UNAVAILABLE_EVENT_TYPE,
                notes=f"Cancellation sent to the booking's {booking.source_channel} chat.",
                request_id="job:travel_timeout",
            ))
            await db.commit()
            return True
    except Exception as exc:  # noqa: BLE001 - notification must not stop the sweeper
        logger.warning("booking_updates.technician_unavailable_failed",
                       job_id=str(job_id), error=str(exc))
        return False


async def send_sla_cancelled(job_id: str | uuid.UUID) -> bool:
    """Tell the exact Instagram booking identity about final SLA closure."""
    from app.database import get_session_factory
    from app.engines.messaging_gateway.constants import PICK_RESTART, PICKER_SEP

    try:
        async with get_session_factory()() as db:
            locked = await db.scalar(text(
                "SELECT pg_try_advisory_xact_lock(hashtextextended(:key, 0))"
            ), {"key": f"ig:sla_cancelled:{job_id}"})
            if not locked:
                return False
            job = await db.get(ServiceJob, uuid.UUID(str(job_id)))
            if (not job or job.status != "cancelled"
                    or not (job.failure_reason or "").startswith(
                        "Technician did not arrive")):
                return False
            booking = await db.get(ServiceBooking, job.booking_id) if job.booking_id else None
            if booking is None:
                return False
            already = await db.scalar(select(ServiceJobExecutionEvent.id).where(
                ServiceJobExecutionEvent.job_id == job.id,
                ServiceJobExecutionEvent.event_type == SLA_CANCELLED_EVENT_TYPE,
            ).limit(1))
            if already:
                return True
            sent = await notify_booking_customer(
                db, booking,
                f"Booking {booking.booking_number} was cancelled because the technician "
                "did not arrive within the service deadline. ਸਾਨੂੰ ਅਫਸੋਸ ਹੈ—ਤੁਸੀਂ ਹੁਣ "
                "ਨਵੀਂ booking ਕਰ ਸਕਦੇ ਹੋ.",
                rows=[{"id": f"{PICK_RESTART}{PICKER_SEP}1", "title": "Book again"}],
                section_title="Booking cancelled",
            )
            if not sent:
                return False
            db.add(ServiceJobExecutionEvent(
                booking_id=booking.id, job_id=job.id, tenant_id=job.tenant_id,
                actor_role="platform", event_type=SLA_CANCELLED_EVENT_TYPE,
                notes=f"SLA cancellation sent to the booking's {booking.source_channel} chat.",
                request_id="job:sla_breach",
            ))
            await db.commit()
            return True
    except Exception as exc:  # noqa: BLE001 - never break the worker over Meta
        logger.warning("booking_updates.sla_cancelled_failed",
                       job_id=str(job_id), error=str(exc))
        return False


async def send_visit_reminder(db, job, when_label: str) -> bool:
    """Remind the chat of the visit, once a technician is actually coming.

    Before assignment there is nobody to name, and the reminder read "Your
    technician is scheduled to visit you tomorrow" for a booking nobody had
    taken. The chat now stays quiet until then; assignment itself announces
    the technician and the visit time. The in-app reminder is unaffected.
    """
    if (getattr(job, "assigned_staff_id", None) is None
            or getattr(job, "status", None) == "pending_assignment"):
        return False
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
