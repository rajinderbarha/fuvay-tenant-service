"""Runnable expiry job: python -m app.jobs.expire_drafts

Expires all stale drafts across every lead-flow engine.
Safe to run repeatedly (idempotent). Intended for cron / task-queue scheduling.

Usage:
    cd g:/serviceos
    python -m app.jobs.expire_drafts
"""
from __future__ import annotations

import asyncio
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger(__name__)


async def _run() -> dict:
    from app.database import init_db, get_db_session
    await init_db()

    from app.engines.real_estate_lead.draft_expiry import DraftExpiryService

    async with get_db_session() as db:
        async with db.begin():
            svc    = DraftExpiryService(db=db)
            result = await svc.expire_all()
            log.info("expire_drafts result: %s", result)
            return result


LOOP_INTERVAL_SECONDS = 30 * 60  # housekeeping cadence


async def _expire_once() -> dict:
    """Expire stale drafts using the already-initialised session factory
    (for the in-process loop, where init_db has already run)."""
    from app.database import get_session_factory
    from app.engines.real_estate_lead.draft_expiry import DraftExpiryService
    session_factory = get_session_factory()
    async with session_factory() as db:
        svc = DraftExpiryService(db=db)
        result = await svc.expire_all()
        await db.commit()
        return result


async def background_loop(interval: int = LOOP_INTERVAL_SECONDS) -> None:
    """MODULE-L5-11: nothing scheduled the draft-expiry job in-process — it was
    CLI-only (python -m app.jobs.expire_drafts) with a manual admin trigger, so
    without external cron abandoned lead/booking/appointment drafts were never
    cleaned up. Started as an asyncio task in app/main.py lifespan, like the
    other workers."""
    log.info("jobs.expire_drafts.loop_started interval_seconds=%d", interval)
    while True:
        await asyncio.sleep(interval)
        try:
            result = await _expire_once()
            log.info("jobs.expire_drafts.loop_tick total_expired=%d",
                     result.get("total_expired", 0))
        except asyncio.CancelledError:
            log.info("jobs.expire_drafts.loop_cancelled")
            raise
        except Exception as exc:  # never crash the loop on a transient error
            log.error("jobs.expire_drafts.loop_error: %s", exc)


def main() -> None:
    result = asyncio.run(_run())
    log.info("Done. total_expired=%d", result.get("total_expired", 0))
    sys.exit(0)


if __name__ == "__main__":
    main()
