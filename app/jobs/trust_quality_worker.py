"""Trust & Quality recalculation worker.

`POST /v1/admin/trust-quality/recalculate/all` used to run the whole platform
sweep inline, so the admin's browser held a request open while every provider was
re-scored one at a time. That is survivable with 190 providers and impossible
with a million: the request times out, the connection is dropped, and the job row
is left saying `running` forever with no way to tell a crashed sweep from a slow
one.

The endpoint now only enqueues. This module is what actually runs the work,
following the same in-process asyncio-loop pattern already established and
running in this codebase (`app/jobs/export_worker.py`): the jobs table is the
queue, rows are claimed with `SELECT ... FOR UPDATE SKIP LOCKED` so overlapping
ticks — or several API processes — can never double-claim, and a job whose worker
died is recovered by timeout rather than stranded.

Usage:
    Automatic: asyncio background task in app/main.py lifespan (every 15s)
    Manual:    python -m app.jobs.trust_quality_worker tick
    Loop:      python -m app.jobs.trust_quality_worker run   (standalone process)
"""
from __future__ import annotations

import asyncio
import socket
import sys
import uuid
from datetime import datetime, timezone, timedelta

import structlog
from sqlalchemy import select

from app.engines.trust_quality.models import TrustQualityRecalculationJob
from app.engines.trust_quality.recalculation import (
    BATCH_SIZE, apply_badges_batch, apply_health_batch, apply_risk_batch,
    enumerate_batch, estimate_total, gather_metrics_bulk, load_ruleset,
)

log = structlog.get_logger("jobs.trust_quality_worker")

WORKER_ID = f"{socket.gethostname()}-{uuid.uuid4().hex[:8]}"

TICK_INTERVAL_SECONDS = 15
# One sweep at a time per tick. A recalculation is a long, DB-heavy job; running
# several concurrently would multiply pool pressure for no throughput gain.
BATCH_LIMIT = 1
# A job still claimed after this long is presumed to belong to a crashed worker.
STALE_RUNNING_MINUTES = 30
# Jobs are the sweep's audit record, but they are not needed forever.
JOB_RETENTION_DAYS = 90
CLEANUP_INTERVAL_SECONDS = 60 * 60

# Yield to the event loop between batches. The worker shares its process with the
# API; without this a large sweep would monopolise the loop and add latency to
# every request being served alongside it.
INTER_BATCH_PAUSE_SECONDS = 0.05


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


async def _claim_next_job(db) -> TrustQualityRecalculationJob | None:
    """Atomically claim exactly one queued job."""
    job = (await db.execute(
        select(TrustQualityRecalculationJob)
        .where(TrustQualityRecalculationJob.status == "queued")
        .order_by(TrustQualityRecalculationJob.created_at.asc())
        .limit(1)
        .with_for_update(skip_locked=True)
    )).scalars().first()
    if job is None:
        return None
    job.status = "running"
    job.started_at = utcnow()
    job.updated_at = utcnow()
    await db.commit()
    return job


async def _recover_stale_jobs(db) -> int:
    """A job RUNNING past the stale window belongs to a crashed worker.

    It is failed rather than requeued: the sweep is not transactional, so the
    targets it already scored are scored, and re-running from the start would
    redo that work. The admin can simply start a new sweep, which is cheap
    relative to guessing where the dead one got to.
    """
    cutoff = utcnow() - timedelta(minutes=STALE_RUNNING_MINUTES)
    stale = (await db.execute(
        select(TrustQualityRecalculationJob).where(
            TrustQualityRecalculationJob.status == "running",
            TrustQualityRecalculationJob.started_at < cutoff,
        )
    )).scalars().all()
    for job in stale:
        job.status = "failed"
        job.completed_at = utcnow()
        job.updated_at = utcnow()
        job.error_summary = (
            f"Worker stopped responding after {STALE_RUNNING_MINUTES} minutes; "
            f"{job.processed_count} target(s) were scored before it died. "
            "Start a new recalculation to finish the rest."
        )
    if stale:
        await db.commit()
        log.warning("trust_quality_worker.stale_recovered", count=len(stale))
    return len(stale)


async def _is_cancelled(db, job_id: uuid.UUID) -> bool:
    """Whether an admin asked this running job to stop, read fresh each batch."""
    status = (await db.execute(
        select(TrustQualityRecalculationJob.status)
        .where(TrustQualityRecalculationJob.id == job_id)
    )).scalar_one_or_none()
    return status == "cancelling"


async def process_job(db, job: TrustQualityRecalculationJob) -> None:
    """Run one sweep to completion, committing progress batch by batch."""
    job_id = job.id
    scope_type, scope_id = job.scope_type, job.scope_id

    try:
        ruleset = await load_ruleset(db, job.job_type)
        job.total_count = await estimate_total(db, ruleset, scope_type, scope_id)
        job.updated_at = utcnow()
        await db.commit()
    except Exception as exc:  # noqa: BLE001
        await db.rollback()
        await _fail(db, job_id, f"Could not load the active rules: {exc}")
        log.error("trust_quality_worker.load_failed", job_id=str(job_id), error=str(exc))
        return

    processed = failed = 0
    errors: list[str] = []
    cancelled = False

    for target_type in ruleset.target_types():
        badge_cfgs = ruleset.badge_rules.get(target_type, [])
        health_cfgs = ruleset.health_formulas.get(target_type, [])
        risk_rules = ruleset.risk_rules.get(target_type, [])
        if not (badge_cfgs or health_cfgs or risk_rules):
            continue

        after_id: uuid.UUID | None = None
        while True:
            if await _is_cancelled(db, job_id):
                cancelled = True
                break
            try:
                ids = await enumerate_batch(db, target_type, scope_type, scope_id,
                                            after_id, BATCH_SIZE)
            except Exception as exc:  # noqa: BLE001
                await db.rollback()
                errors.append(f"{target_type}: could not enumerate targets: {exc}")
                break
            if not ids:
                break
            after_id = ids[-1]

            try:
                metrics = await gather_metrics_bulk(db, target_type, ids)
                if badge_cfgs:
                    await apply_badges_batch(db, badge_cfgs, target_type, metrics)
                    processed += len(ids)
                for cfg in health_cfgs:
                    await apply_health_batch(db, cfg, target_type, metrics)
                    processed += len(ids)
                if risk_rules:
                    await apply_risk_batch(db, risk_rules, target_type, metrics)
                    processed += len(ids)

                fresh = await db.get(TrustQualityRecalculationJob, job_id)
                if fresh is not None:
                    fresh.processed_count = processed
                    fresh.failed_count = failed
                    fresh.updated_at = utcnow()
                await db.commit()
            except Exception as exc:  # noqa: BLE001
                # One bad batch must not sink the sweep — roll it back, count it,
                # and carry on with the next batch.
                await db.rollback()
                units = (bool(badge_cfgs) + len(health_cfgs) + bool(risk_rules))
                failed += len(ids) * units
                if len(errors) < 10:
                    errors.append(f"{target_type}/batch@{after_id}: {exc}")
                log.error("trust_quality_worker.batch_failed", job_id=str(job_id),
                          target_type=target_type, error=str(exc))

            await asyncio.sleep(INTER_BATCH_PAUSE_SECONDS)

        if cancelled:
            break

    fresh = await db.get(TrustQualityRecalculationJob, job_id)
    if fresh is None:
        return
    fresh.processed_count = processed
    fresh.failed_count = failed
    # total_count was an estimate taken before the walk; the walk is the truth, so
    # a job never reports 900/1000 done when it in fact finished everything there
    # was (rows can be created or deleted mid-sweep).
    if not cancelled and processed + failed != fresh.total_count:
        fresh.total_count = processed + failed
    fresh.error_summary = "; ".join(errors) or None
    fresh.status = ("cancelled" if cancelled
                    else "completed" if failed == 0 else "completed_with_errors")
    fresh.completed_at = utcnow()
    fresh.updated_at = utcnow()
    await db.commit()
    log.info("trust_quality_worker.job_done", job_id=str(job_id), status=fresh.status,
             processed=processed, failed=failed)


async def _fail(db, job_id: uuid.UUID, message: str) -> None:
    job = await db.get(TrustQualityRecalculationJob, job_id)
    if job is None:
        return
    job.status = "failed"
    job.error_summary = message
    job.completed_at = utcnow()
    job.updated_at = utcnow()
    await db.commit()


async def run_worker_tick(batch_limit: int = BATCH_LIMIT) -> dict:
    """Recover stale jobs, then claim and run up to `batch_limit` queued jobs."""
    from app.database import get_session_factory

    session_factory = get_session_factory()
    async with session_factory() as db:
        await _recover_stale_jobs(db)

    ran = 0
    for _ in range(batch_limit):
        async with session_factory() as db:
            job = await _claim_next_job(db)
            if job is None:
                break
            await process_job(db, job)
            ran += 1
    return {"worker_id": WORKER_ID, "ran": ran, "run_at": utcnow().isoformat()}


async def run_cleanup(retention_days: int = JOB_RETENTION_DAYS) -> dict:
    """Drop finished job rows past the retention window.

    Without this the jobs table grows without bound — a sweep every hour is
    ~9k rows a year, and the recalculation tab reads it on every page load.
    """
    from app.database import get_session_factory
    from sqlalchemy import delete

    cutoff = utcnow() - timedelta(days=retention_days)
    async with get_session_factory()() as db:
        result = await db.execute(
            delete(TrustQualityRecalculationJob).where(
                TrustQualityRecalculationJob.status.in_(
                    ("completed", "completed_with_errors", "failed", "cancelled")),
                TrustQualityRecalculationJob.created_at < cutoff,
            )
        )
        await db.commit()
    deleted = result.rowcount or 0
    if deleted:
        log.info("trust_quality_worker.cleanup_done", deleted=deleted)
    return {"deleted": deleted, "run_at": utcnow().isoformat()}


async def background_loop(interval: int = TICK_INTERVAL_SECONDS,
                          cleanup_interval: int = CLEANUP_INTERVAL_SECONDS) -> None:
    log.info("trust_quality_worker.loop_started", worker_id=WORKER_ID, interval_seconds=interval)
    ticks_since_cleanup = 0
    ticks_per_cleanup = max(1, cleanup_interval // interval)
    while True:
        await asyncio.sleep(interval)
        try:
            result = await run_worker_tick()
            if result["ran"]:
                log.info("trust_quality_worker.loop_tick", ran=result["ran"])
            ticks_since_cleanup += 1
            if ticks_since_cleanup >= ticks_per_cleanup:
                await run_cleanup()
                ticks_since_cleanup = 0
        except asyncio.CancelledError:
            log.info("trust_quality_worker.loop_cancelled")
            raise
        except Exception as exc:  # noqa: BLE001
            log.error("trust_quality_worker.loop_error", error=str(exc))


def main() -> None:
    cmd = sys.argv[1] if len(sys.argv) > 1 else "tick"
    if cmd == "tick":
        result = asyncio.run(run_worker_tick())
    elif cmd == "cleanup":
        result = asyncio.run(run_cleanup())
    elif cmd == "run":
        asyncio.run(background_loop())
        return
    else:
        print(f"Unknown command: {cmd}. Use: tick | cleanup | run")
        sys.exit(1)
    log.info("trust_quality_worker.cli_done", cmd=cmd, result=result)


if __name__ == "__main__":
    main()
