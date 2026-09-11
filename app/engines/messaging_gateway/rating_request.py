"""Ask for an Instagram rating, then send the completed service's warranty PDF.

The staff app's final "Complete job" (`MobileDirectPaymentService.finalize_job`)
schedules `send_rating_request` to run after its response. The customer taps a
star rating, or types 1-5, and the answer is saved through the same
`ReviewService.submit_review` call the customer app's rating screen makes,
keyed by booking. So a booking can be rated once, from either place, and a chat
rating reaches the provider's reviews page and rating summaries exactly as an
in-app one does.

Whether a booking still wants a rating is simply whether it has a review yet.
After the prompt is sent, warranty_delivery sends the immutable certificate
and records its document reference and successful send on the completed job.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import structlog
from sqlalchemy import or_, select

from app.engines.messaging_gateway import meta_client, warranty_delivery
from app.engines.messaging_gateway.constants import (
    CUSTOMER_SERVICE_WINDOW_HOURS, PICK_RATING, PICKER_SEP, RATING_REQUEST_CHANNELS,
)
from app.engines.messaging_gateway.models import MessagingThread

logger = structlog.get_logger(__name__)

RATING_PROMPT = (
    "{heading} How would you rate the service?\n\n"
    "Tap a rating below, or reply with a number from 1 (poor) to 5 (excellent)."
)
RATING_THANKS = "Thank you! You rated this service {stars}/5 {bar}"
RATING_SORRY = (
    "We're sorry it wasn't better. Send /human if you would like our team "
    "to follow up."
)
RATING_ALREADY_GIVEN = "You have already rated this service {stars}/5. Thank you!"
RATING_UNAVAILABLE = "This service can no longer be rated here."

#: At or below this, the thank-you also offers a person to talk to.
LOW_RATING = 2
_STAR = "⭐"
_RATINGS = ("1", "2", "3", "4", "5")


def rating_rows(booking_id) -> list[dict]:
    """The five options, worst to best, each carrying its booking and score."""
    return [
        {"id": PICKER_SEP.join((PICK_RATING, str(booking_id), str(stars))),
         "title": f"{stars} {_STAR * stars}"}
        for stars in range(1, 6)
    ]


def typed_rating(thread, text: str) -> str | None:
    """The rating option a bare 1-5 answers, when a rating question is open.

    Instagram's desktop client shows no quick replies, and on mobile they
    scroll away, so the prompt invites a typed number. The gateway resolves it
    before deciding whether a message opens a new conversation: a "5" sent the
    next morning still answers the question we asked, not a welcome.
    """
    stripped = (text or "").strip()
    if stripped not in _RATINGS:
        return None
    for option in getattr(thread, "last_options", None) or []:
        kind, _, rest = str(option).partition(PICKER_SEP)
        if kind == PICK_RATING and rest.rpartition(PICKER_SEP)[2] == stripped:
            return str(option)
    return None


async def send_rating_request(job_id) -> bool:
    """Ask the customer of a just-completed job to rate it. Best-effort.

    Runs after the staff app's completion response, in its own session. The
    Graph API can take as long as the staff app's own request timeout, and a
    completed job must never look failed to the technician because Instagram
    was slow or down.
    """
    from app.database import get_session_factory

    try:
        async with get_session_factory()() as db:
            try:
                sent = await _ask(db, uuid.UUID(str(job_id)))
                await db.commit()
                return sent
            except Exception:
                await db.rollback()
                raise
    except Exception as exc:  # noqa: BLE001 - a rating ask never fails anything
        logger.warning("messaging_gateway.rating_request.failed",
                       job_id=str(job_id), error=str(exc))
        return False


async def _ask(db, job_id: uuid.UUID) -> bool:
    from app.engines.messaging_gateway.config_service import (
        messaging_channel_config_service,
    )

    target = await _completed_booking(db, job_id)
    if target is None:
        return False
    job, booking = target
    thread = await _reachable_thread(db, booking.customer_id)
    if thread is None:
        # Instagram allows a business-initiated message only within 24 hours
        # of the customer's own last message, and has no template to fall
        # back on. The customer app can still collect this rating.
        logger.info("messaging_gateway.rating_request.no_open_thread",
                    job_id=str(job_id))
        return False
    config = await messaging_channel_config_service.get(
        db, thread.channel, require_enabled=True,
    )
    if not config:
        return False

    rating_sent = False
    if await _existing_rating(db, booking.customer_id, booking.id) is None:
        rows = rating_rows(booking.id)
        result = await meta_client.send_options(
            thread.channel_user_id, await _prompt(db, job, booking), rows,
            channel=thread.channel, config=config,
            list_button="Rate", section_title="Rate your service",
        )
        if not result.get("sent"):
            return False
        thread.last_outbound_at = datetime.now(timezone.utc)
        if not thread.last_options:
            # Only when no numbered list is open: a customer halfway through a new
            # booking keeps their typed numbers, and can still tap a star chip.
            thread.last_options = [row["id"] for row in rows]
        logger.info("messaging_gateway.rating_request.sent",
                    job_id=str(job_id), thread_id=str(thread.id))
        # Make typed rating replies visible to the webhook while the PDF uploads.
        await db.commit()
        rating_sent = True
    # The warranty follows the question; it does not depend on the customer
    # submitting a rating. A fast in-app rating must not suppress the PDF.
    warranty_sent = await warranty_delivery.send_warranty_certificate(
        db, job, thread, config=config,
    )
    return rating_sent or warranty_sent


async def record_rating(db, thread, booking_id: str, stars: str) -> str:
    """Save a tapped or typed rating through the review engine; say what happened."""
    from app.engines.customer_reviews.constants import RECORD_TYPE_SERVICE_BOOKING
    from app.engines.customer_reviews.review_service import ReviewService

    customer_id = getattr(thread, "customer_id", None)
    if not customer_id or stars not in _RATINGS:
        return RATING_UNAVAILABLE
    booking = await _customer_booking(db, customer_id, booking_id)
    if booking is None:
        return RATING_UNAVAILABLE
    given = await _existing_rating(db, customer_id, booking.id)
    if given is not None:
        return RATING_ALREADY_GIVEN.format(stars=given)

    rating = int(stars)
    try:
        await ReviewService().submit_review(
            db, customer_id=customer_id, tenant_id=booking.tenant_id,
            record_type=RECORD_TYPE_SERVICE_BOOKING, record_id=booking.id,
            overall_rating=rating, request_id=f"chat:{thread.id}:rating",
        )
    except ValueError as exc:
        # The review engine owns eligibility (completed, not already reviewed);
        # a refusal there means this booking is no longer ratable here.
        logger.info("messaging_gateway.rating_rejected",
                    booking_id=str(booking.id), error=str(exc))
        return RATING_UNAVAILABLE
    thanks = RATING_THANKS.format(stars=rating, bar=_STAR * rating)
    return f"{thanks}\n\n{RATING_SORRY}" if rating <= LOW_RATING else thanks


# ── Lookups ──────────────────────────────────────────────────────────────────


async def _completed_booking(db, job_id: uuid.UUID):
    """The job and its booking, only if the job really is completed."""
    from app.engines.execution.constants import JS_COMPLETED
    from app.engines.final_records.models import ServiceBooking, ServiceJob

    job = await db.get(ServiceJob, job_id)
    if job is None or job.status != JS_COMPLETED or not job.customer_id:
        return None
    booking = await db.get(ServiceBooking, job.booking_id)
    if booking is None or booking.customer_id != job.customer_id:
        return None
    return job, booking


async def _customer_booking(db, customer_id, booking_id: str):
    """The booking a tap names, only if it belongs to the thread's customer.

    The id inside a tap is never authority on its own.
    """
    from app.engines.final_records.models import ServiceBooking

    try:
        booking_uuid = uuid.UUID(str(booking_id))
    except ValueError:
        return None
    return (await db.execute(
        select(ServiceBooking).where(
            ServiceBooking.id == booking_uuid,
            ServiceBooking.customer_id == customer_id,
        ).limit(1)
    )).scalars().first()


async def _existing_rating(db, customer_id, booking_id) -> int | None:
    """The customer's rating of this booking, from the app or from chat."""
    from app.engines.customer_reviews.models import CustomerReview

    return (await db.execute(
        select(CustomerReview.overall_rating).where(
            CustomerReview.customer_id == customer_id,
            CustomerReview.booking_id == booking_id,
        ).limit(1)
    )).scalars().first()


async def _reachable_thread(db, customer_id) -> MessagingThread | None:
    """The customer's most recent thread we may message, and whose answer we read.

    Opted-out, agent-owned and blocked threads are skipped: the gateway does
    not answer taps on any of them, so a question sent there could never be
    answered.
    """
    now = datetime.now(timezone.utc)
    return (await db.execute(
        select(MessagingThread).where(
            MessagingThread.customer_id == customer_id,
            MessagingThread.channel.in_(RATING_REQUEST_CHANNELS),
            MessagingThread.opted_out.is_(False),
            MessagingThread.human_handoff.is_(False),
            or_(MessagingThread.blocked_until.is_(None),
                MessagingThread.blocked_until <= now),
            MessagingThread.last_inbound_at >= now - timedelta(
                hours=CUSTOMER_SERVICE_WINDOW_HOURS),
        ).order_by(MessagingThread.last_inbound_at.desc()).limit(1)
    )).scalars().first()


async def _prompt(db, job, booking) -> str:
    from app.engines.admin_catalog.models import MasterService

    offering = await db.get(MasterService, job.offering_id)
    service = getattr(offering, "service_name", None)
    heading = (f"Your {service} booking {booking.booking_number} is complete."
               if service else f"Your booking {booking.booking_number} is complete.")
    return RATING_PROMPT.format(heading=heading)
