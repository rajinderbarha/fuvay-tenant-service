"""Purge job photos whose retention has run out.

Hourly and retention-driven rather than "everything at 2am on Sunday": what
gets deleted is decided by each job's own date, so a missed run costs latency
instead of silently skipping a week, and re-running is harmless.
"""
from __future__ import annotations

import asyncio

import structlog

logger = structlog.get_logger("jobs.media_retention")

INTERVAL_SECONDS = 3600


async def run_once() -> dict:
    from app.database import get_session_factory
    from app.engines.execution import media_retention_service as retention

    async with get_session_factory()() as db:
        result = await retention.sweep(db)
        await db.commit()
        return result


async def background_loop() -> None:
    while True:
        try:
            result = await run_once()
            if (result.get("customer", {}).get("jobs")
                    or result.get("completion", {}).get("jobs")):
                logger.info("media_retention.swept", **result)
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001 -- a bad sweep must not kill the loop
            logger.warning("media_retention.sweep_failed", error=str(exc))
        await asyncio.sleep(INTERVAL_SECONDS)
