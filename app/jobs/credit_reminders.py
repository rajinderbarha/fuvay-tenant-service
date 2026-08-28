"""Remind providers whose credit is running out.

Runs hourly; the CADENCE is decided per tenant from how bad their balance is,
so this loop firing often does not mean a provider is notified often.
"""
from __future__ import annotations

import asyncio

import structlog

logger = structlog.get_logger("jobs.credit_reminders")

INTERVAL_SECONDS = 3600


async def run_once() -> dict:
    from app.database import get_session_factory
    from app.engines.vertical_catalog import credit_reminder_service as reminders

    async with get_session_factory()() as db:
        result = await reminders.sweep(db)
        await db.commit()
        return result


async def background_loop() -> None:
    while True:
        try:
            result = await run_once()
            if result.get("sent") or result.get("recovered"):
                logger.info("credit_reminders.swept", **result)
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001 -- a bad sweep must not kill the loop
            logger.warning("credit_reminders.sweep_failed", error=str(exc))
        await asyncio.sleep(INTERVAL_SECONDS)
