"""Recover Instagram provider-cancellation messages after transient failures.

The live cancellation endpoint attempts delivery immediately after commit. This
worker covers process interruption, Meta errors and a customer reopening the
24-hour messaging window later. Delivery itself is advisory-locked and marked
on the job timeline, so multiple workers remain idempotent.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

import structlog
from sqlalchemy import text

from app.engines.messaging_gateway.constants import CUSTOMER_SERVICE_WINDOW_HOURS

logger = structlog.get_logger(__name__)
INTERVAL_SECONDS = 300
MAX_BATCH_SIZE = 200


async def run_once() -> int:
    from app.database import get_session_factory
    from app.engines.messaging_gateway.booking_updates import (
        PROVIDER_CANCELLED_EVENT_TYPE,
        send_provider_cancelled_once,
    )

    now = datetime.now(timezone.utc)
    async with get_session_factory()() as db:
        rows = (await db.execute(text("""
            SELECT cancelled.job_id
            FROM service_job_execution_events cancelled
            JOIN service_jobs job ON job.id = cancelled.job_id
            JOIN service_bookings booking ON booking.id = job.booking_id
            WHERE cancelled.event_type = 'job_cancelled'
              AND cancelled.actor_role = 'provider'
              AND cancelled.created_at >= :cancellation_cutoff
              AND job.status = 'cancelled'
              AND booking.source_channel = 'instagram'
              AND booking.source_actor_id IS NOT NULL
              AND booking.source_actor_id <> ''
              AND NOT EXISTS (
                SELECT 1 FROM service_job_execution_events delivered
                WHERE delivered.job_id = cancelled.job_id
                  AND delivered.event_type = :delivered_event
              )
              AND EXISTS (
                SELECT 1 FROM messaging_threads thread
                WHERE thread.customer_id = booking.customer_id
                  AND thread.channel = 'instagram'
                  AND thread.channel_user_id = booking.source_actor_id
                  AND thread.opted_out IS FALSE
                  AND thread.human_handoff IS FALSE
                  AND (thread.blocked_until IS NULL OR thread.blocked_until <= :now)
                  AND thread.last_inbound_at >= :window_start
              )
            GROUP BY cancelled.job_id
            ORDER BY max(cancelled.created_at)
            LIMIT :batch_size
        """), {
            "delivered_event": PROVIDER_CANCELLED_EVENT_TYPE,
            "now": now,
            "window_start": now - timedelta(hours=CUSTOMER_SERVICE_WINDOW_HOURS),
            "cancellation_cutoff": now - timedelta(days=7),
            "batch_size": MAX_BATCH_SIZE,
        })).all()

    delivered = 0
    for (job_id,) in rows:
        try:
            if await send_provider_cancelled_once(job_id):
                delivered += 1
        except Exception as exc:  # one broken job must not starve the batch
            logger.warning("instagram_cancellation_followups.job_failed",
                           job_id=str(job_id), error=str(exc))
    return delivered


async def background_loop() -> None:
    while True:
        try:
            delivered = await run_once()
            if delivered:
                logger.info("instagram_cancellation_followups.delivered", count=delivered)
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001
            logger.warning("instagram_cancellation_followups.failed", error=str(exc))
        await asyncio.sleep(INTERVAL_SECONDS)
