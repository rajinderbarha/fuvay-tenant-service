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


def main() -> None:
    result = asyncio.run(_run())
    log.info("Done. total_expired=%d", result.get("total_expired", 0))
    sys.exit(0)


if __name__ == "__main__":
    main()
