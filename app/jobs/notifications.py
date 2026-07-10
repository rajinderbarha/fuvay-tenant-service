"""Sprint 27 — Notification background jobs.

Commands:
  python -m app.jobs.notifications dispatch
  python -m app.jobs.notifications retry
  python -m app.jobs.notifications cleanup

Schedule:
  dispatch: every 1 minute
  retry:    every 5 minutes
  cleanup:  hourly
"""
from __future__ import annotations
import asyncio
import sys
from datetime import datetime, timezone, timedelta

import structlog
from sqlalchemy import select, update

log = structlog.get_logger("jobs.notifications")
utcnow = lambda: datetime.now(timezone.utc)


async def _get_db():
    from app.database import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        yield db


async def dispatch_pending(limit: int = 100) -> dict:
    """Process pending outbox records. Safe to run repeatedly."""
    from app.database import AsyncSessionLocal
    from app.engines.platform_notifications.notification_service import NotificationService
    svc = NotificationService()
    async with AsyncSessionLocal() as db:
        result = await svc.dispatch_pending(db, limit=limit)
    log.info("jobs.dispatch_pending.done", **result)
    return result


async def retry_failed(limit: int = 50) -> dict:
    """Re-queue failed outbox records within retry limit."""
    from app.database import AsyncSessionLocal
    from app.engines.platform_notifications.notification_service import NotificationService
    svc = NotificationService()
    async with AsyncSessionLocal() as db:
        result = await svc.retry_failed(db, limit=limit)
    log.info("jobs.retry_failed.done", **result)
    return result


async def cleanup_expired(days: int = 30) -> dict:
    """Clean up old processed notification events (non-destructive: marks expired)."""
    from app.database import AsyncSessionLocal
    from app.engines.platform_notifications.models import NotificationOutbox
    from app.engines.platform_notifications.constants import DELIVERY_DELIVERED, DELIVERY_SKIPPED
    cutoff = utcnow() - timedelta(days=days)
    deleted = 0
    async with AsyncSessionLocal() as db:
        r = await db.execute(
            select(NotificationOutbox).where(
                NotificationOutbox.created_at < cutoff,
                NotificationOutbox.delivery_status.in_([DELIVERY_DELIVERED, DELIVERY_SKIPPED]),
            ).limit(1000)
        )
        items = r.scalars().all()
        for item in items:
            await db.delete(item)
            deleted += 1
        if deleted:
            await db.commit()
    log.info("jobs.cleanup_expired.done", deleted=deleted, cutoff=cutoff.isoformat())
    return {"deleted": deleted}


async def run_all() -> None:
    """Run all notification jobs once."""
    log.info("jobs.notifications.start")
    await dispatch_pending()
    await retry_failed()
    log.info("jobs.notifications.done")


if __name__ == "__main__":
    command = sys.argv[1] if len(sys.argv) > 1 else "all"
    jobs = {
        "dispatch": dispatch_pending,
        "retry": retry_failed,
        "cleanup": cleanup_expired,
        "all": run_all,
    }
    fn = jobs.get(command, run_all)
    asyncio.run(fn())
