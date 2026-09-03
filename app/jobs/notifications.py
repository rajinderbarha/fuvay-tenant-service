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
    from app.database import get_session_factory
    session_factory = get_session_factory()
    async with session_factory() as db:
        yield db


async def dispatch_pending(limit: int = 100) -> dict:
    """Process pending outbox records. Safe to run repeatedly."""
    from app.database import get_session_factory
    from app.engines.platform_notifications.notification_service import NotificationService
    svc = NotificationService()
    session_factory = get_session_factory()
    async with session_factory() as db:
        result = await svc.dispatch_pending(db, limit=limit)
    log.info("jobs.dispatch_pending.done", **result)
    return result


async def retry_failed(limit: int = 50) -> dict:
    """Re-queue failed outbox records within retry limit."""
    from app.database import get_session_factory
    from app.engines.platform_notifications.notification_service import NotificationService
    svc = NotificationService()
    session_factory = get_session_factory()
    async with session_factory() as db:
        result = await svc.retry_failed(db, limit=limit)
    log.info("jobs.retry_failed.done", **result)
    return result


async def cleanup_expired(days: int = 30) -> dict:
    """Clean up old processed notification events (non-destructive: marks expired)."""
    from app.database import get_session_factory
    from app.engines.platform_notifications.models import NotificationOutbox
    from app.engines.platform_notifications.constants import DELIVERY_DELIVERED, DELIVERY_SKIPPED
    cutoff = utcnow() - timedelta(days=days)
    deleted = 0
    session_factory = get_session_factory()
    async with session_factory() as db:
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
    from app.jobs.booking_reminders import send_due_reminders
    await send_due_reminders()
    log.info("jobs.notifications.done")


# ─────────────────────────────────────────────────────────────────────────────
# BACKGROUND LOOP
# ─────────────────────────────────────────────────────────────────────────────

LOOP_INTERVAL_SECONDS = 60  # docstring: "dispatch: every 1 minute"


async def background_loop(interval: int = LOOP_INTERVAL_SECONDS) -> None:
    """MODULE-L5-11: notification delivery is inline on create, so this loop is
    the retry/catch-up net — it re-dispatches records left PENDING by a transient
    inline-delivery failure and re-queues FAILED ones within the retry limit.
    Nothing ran it: unlike the compliance-SLA, complaint-SLA and export-worker
    loops (all started in the app lifespan), the notification dispatcher was
    CLI-only, so in any deployment without an external per-minute cron a
    transiently-failed notification stayed PENDING forever and was never retried.
    Started as an asyncio task in app/main.py lifespan."""
    log.info("jobs.notifications.loop_started", interval_seconds=interval)
    while True:
        await asyncio.sleep(interval)
        try:
            d = await dispatch_pending()
            f = await retry_failed()
            from app.jobs.booking_reminders import send_due_reminders
            reminders = await send_due_reminders()
            log.info("jobs.notifications.loop_tick",
                     dispatched=d.get("processed"), retried=f.get("requeued"), **reminders)
        except asyncio.CancelledError:
            log.info("jobs.notifications.loop_cancelled")
            raise
        except Exception as exc:  # never crash the loop on a transient error
            log.error("jobs.notifications.loop_error", error=str(exc))


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
