"""Act on jobs that have run out of time.

Breach is decided by `service_jobs.sla_due_at`, not by when this loop fires, so
a missed run costs latency and nothing else -- a late sweep reaches the same
outcome as a punctual one. The same pass reinstates providers whose suspension
has served its time.
"""
from __future__ import annotations

import asyncio

import structlog

logger = structlog.get_logger("jobs.sla_breach")

#: Every 15 minutes. The SLA is measured in hours, so a tighter cadence buys
#: nothing; a looser one leaves a customer waiting on a job already written off.
INTERVAL_SECONDS = 900


async def run_once() -> dict:
    from app.database import get_session_factory
    from app.engines.execution import sla_breach_service as sla

    async with get_session_factory()() as db:
        result = await sla.sweep(db)
        await db.commit()
        return result


async def background_loop() -> None:
    while True:
        try:
            result = await run_once()
            if result.get("breached") or result.get("suspended") or result.get("reinstated"):
                logger.info("sla_breach.swept", **result)
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001 -- a bad sweep must not kill the loop
            logger.warning("sla_breach.sweep_failed", error=str(exc))
        await asyncio.sleep(INTERVAL_SECONDS)
