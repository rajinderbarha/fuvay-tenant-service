"""Continuously publish live evidence for the tenant service-status banner."""
from __future__ import annotations

import asyncio
from datetime import timedelta

import structlog
from sqlalchemy import delete

from app.database import get_db_session
from app.engines.support.models import SupportStatusHeartbeat
from app.engines.support.service import record_heartbeat, utcnow
from app.redis_client import get_redis

log = structlog.get_logger("jobs.platform_status")
LOOP_INTERVAL_SECONDS = 300


async def run_once() -> dict:
    redis_healthy = False
    detail = "database=ok; redis=unavailable"
    try:
        redis_healthy = bool(await get_redis().ping())
        detail = "database=ok; redis=ok" if redis_healthy else detail
    except Exception as exc:  # database can still publish the degraded state
        detail = f"database=ok; redis=unavailable ({type(exc).__name__})"

    async with get_db_session() as db:
        await record_heartbeat(db, "core_services", redis_healthy, detail)
        # Five-minute evidence is useful; unbounded heartbeat history is not.
        await db.execute(delete(SupportStatusHeartbeat).where(
            SupportStatusHeartbeat.checked_at < utcnow() - timedelta(days=30)
        ))
    return {"healthy": redis_healthy, "detail": detail}


async def background_loop(interval: int = LOOP_INTERVAL_SECONDS) -> None:
    log.info("jobs.platform_status.loop_started", interval_seconds=interval)
    while True:
        try:
            result = await run_once()
            log.info("jobs.platform_status.loop_tick", **result)
            await asyncio.sleep(interval)
        except asyncio.CancelledError:
            log.info("jobs.platform_status.loop_cancelled")
            raise
        except Exception as exc:
            log.error("jobs.platform_status.loop_error", error=str(exc))
            await asyncio.sleep(min(interval, 60))
