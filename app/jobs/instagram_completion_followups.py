"""Retry Instagram rating and warranty delivery after completed jobs.

The completion route sends immediately. This loop covers transient Graph or
storage failures without requiring the technician to complete the job twice.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

import structlog
from sqlalchemy import text

logger = structlog.get_logger(__name__)
INTERVAL_SECONDS = 300


async def run_once() -> int:
    from app.database import get_session_factory
    from app.engines.messaging_gateway.rating_request import send_rating_request

    async with get_session_factory()() as db:
        rows = (await db.execute(text("""
            SELECT j.id FROM service_jobs j
            JOIN service_bookings b ON b.id = j.booking_id
            WHERE j.status = 'completed' AND b.source_channel = 'instagram'
              AND b.source_actor_id IS NOT NULL
              AND j.updated_at >= :cutoff
              AND (
                j.completion_data->>'instagram_rating_prompt_sent_at' IS NULL
                OR j.completion_data->'instagram_warranty_pdf'->>'sent_at' IS NULL
              )
            ORDER BY j.updated_at DESC LIMIT 200
        """), {"cutoff": datetime.now(timezone.utc) - timedelta(hours=48)})).scalars().all()
    delivered = 0
    for job_id in rows:
        if await send_rating_request(job_id):
            delivered += 1
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
