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
