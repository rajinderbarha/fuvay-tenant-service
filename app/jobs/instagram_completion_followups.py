"""Retry pending Instagram completion messages while a customer thread is open.

The completion route sends immediately. Jobs remain pending for as long as a
rating prompt or warranty PDF is undelivered; a fresh customer inbound can
reopen Instagram's 24-hour messaging window even days after completion.
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
MAX_RETRY_SECONDS = 3600


async def _schedule_next_attempt(job_id, attempts: int) -> None:
    """Persist a retry delay without changing the job's business updated_at.

    Sorting undelayed jobs before delayed ones prevents a failing oldest batch
    from starving the rest of the backlog. A completed delivery needs no retry
    marker; the SQL removes one left by an earlier partial failure.
    """
    from app.database import get_session_factory

    now = datetime.now(timezone.utc)
    delay_seconds = min(MAX_RETRY_SECONDS, INTERVAL_SECONDS * 2 ** min(attempts - 1, 4))
    async with get_session_factory()() as db:
        await db.execute(text("""
            UPDATE service_jobs
            SET completion_data = CASE
                WHEN completion_data->>'instagram_rating_prompt_sent_at' IS NOT NULL
                 AND completion_data->'instagram_warranty_pdf'->>'sent_at' IS NOT NULL
                THEN completion_data - 'instagram_followup_retry'
                ELSE jsonb_set(
                    COALESCE(completion_data, '{}'::jsonb),
                    '{instagram_followup_retry}',
                    jsonb_build_object(
                        'attempts', :attempts,
                        'last_attempt_at', :attempted_at,
                        'next_attempt_epoch', :next_attempt_epoch
                    ), true
                )
            END
            WHERE id = :job_id AND status = 'completed'
        """), {
            "job_id": job_id,
            "attempts": attempts,
            "attempted_at": now.isoformat(),
            "next_attempt_epoch": now.timestamp() + delay_seconds,
        })
        await db.commit()


async def run_once() -> int:
    from app.database import get_session_factory
    from app.engines.messaging_gateway.rating_request import send_rating_request

    now = datetime.now(timezone.utc)
    async with get_session_factory()() as db:
        rows = (await db.execute(text("""
            SELECT j.id,
                   COALESCE((j.completion_data->'instagram_followup_retry'->>'attempts')::integer, 0)
            FROM service_jobs j
            JOIN service_bookings b ON b.id = j.booking_id
            WHERE j.status = 'completed' AND b.source_channel = 'instagram'
              AND b.source_actor_id IS NOT NULL AND b.source_actor_id <> ''
              AND (
                j.completion_data->>'instagram_rating_prompt_sent_at' IS NULL
                OR j.completion_data->'instagram_warranty_pdf'->>'sent_at' IS NULL
              )
              AND COALESCE(
                (j.completion_data->'instagram_followup_retry'->>'next_attempt_epoch')::double precision,
                0
              ) <= :now_epoch
              AND EXISTS (
                SELECT 1 FROM messaging_threads mt
                WHERE mt.customer_id = b.customer_id
                  AND mt.channel = 'instagram'
                  AND mt.channel_user_id = b.source_actor_id
                  AND mt.opted_out IS FALSE
                  AND mt.human_handoff IS FALSE
                  AND (mt.blocked_until IS NULL OR mt.blocked_until <= :now)
                  AND mt.last_inbound_at >= :window_start
              )
            ORDER BY COALESCE(
                (j.completion_data->'instagram_followup_retry'->>'next_attempt_epoch')::double precision,
                0
            ), j.created_at, j.id
            LIMIT :batch_size
        """), {
            "now": now,
            "now_epoch": now.timestamp(),
            "window_start": now - timedelta(hours=CUSTOMER_SERVICE_WINDOW_HOURS),
            "batch_size": MAX_BATCH_SIZE,
        })).all()
    delivered = 0
    for job_id, prior_attempts in rows:
        if await send_rating_request(job_id):
            delivered += 1
        try:
            await _schedule_next_attempt(job_id, int(prior_attempts) + 1)
        except Exception as exc:  # one broken job must not starve the batch
            logger.warning("instagram_completion_followups.schedule_failed",
                           job_id=str(job_id), error=str(exc))
    return delivered


async def background_loop() -> None:
    while True:
        try:
            delivered = await run_once()
            if delivered:
                logger.info("instagram_completion_followups.delivered", count=delivered)
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001
            logger.warning("instagram_completion_followups.failed", error=str(exc))
        await asyncio.sleep(INTERVAL_SECONDS)
