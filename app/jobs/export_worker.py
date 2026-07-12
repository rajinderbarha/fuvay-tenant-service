"""FINAL-L5-05S — Export Worker.

Follows the same in-process asyncio-loop pattern already established and
running in production in this codebase (see `app/jobs/compliance_sla.py`)
rather than introducing a new external queue framework (no Celery/RQ/
Dramatiq/ARQ is configured anywhere in this repository -- confirmed via
dependency and codebase search). This is Part 5's "Strategy B: dedicated
database-backed worker": the export_jobs table itself is the queue,
claimed via `SELECT ... FOR UPDATE SKIP LOCKED` so multiple concurrent
loop ticks (or, if ever deployed as a separate process via the CLI
entrypoint below, multiple worker processes) cannot double-claim a job.

Usage:
    Automatic: asyncio background task in app/main.py lifespan (every 10s)
    Manual:    python -m app.jobs.export_worker tick
    Cleanup:   python -m app.jobs.export_worker cleanup
    Loop:      python -m app.jobs.export_worker run   (standalone process)
"""
from __future__ import annotations

import asyncio
import socket
import sys
import uuid
from datetime import datetime, timezone, timedelta

import structlog
from sqlalchemy import select, text

log = structlog.get_logger("jobs.export_worker")
utcnow = lambda: datetime.now(timezone.utc)

WORKER_ID = f"{socket.gethostname()}-{uuid.uuid4().hex[:8]}"

TICK_INTERVAL_SECONDS = 10
BATCH_SIZE = 5
MAX_RETRIES = 3
STALE_RUNNING_MINUTES = 15  # a job stuck RUNNING this long is presumed crashed
EXPORT_EXPIRY_HOURS = 24
CLEANUP_INTERVAL_SECONDS = 5 * 60

# Errors that should never be retried -- retrying them would produce the
# exact same failure every time (rule 21: non-retryable errors stop retry).
NON_RETRYABLE_PREFIXES = (
    "EXPORT_GENERATOR_UNAVAILABLE", "EXPORT_FIELD_NOT_ALLOWED",
    "EXPORT_RESOURCE_UNSUPPORTED", "EXPORT_FORMAT_UNSUPPORTED",
    "EXPORT_CROSS_TENANT_FORBIDDEN", "PERMISSION_DENIED",
)


async def _claim_next_job(db) -> "EnterpriseExportJob | None":
    """Atomically claim exactly one PENDING job. FOR UPDATE SKIP LOCKED
    guarantees at most one concurrent claimer wins any given row (rule 6)."""
    from app.engines.enterprise_grid.models import EnterpriseExportJob

    result = await db.execute(
        select(EnterpriseExportJob)
        .where(EnterpriseExportJob.status == "pending")
        .order_by(EnterpriseExportJob.created_at.asc())
        .limit(1)
        .with_for_update(skip_locked=True)
    )
    job = result.scalars().first()
    if job is None:
        return None
    job.status = "processing"
    job.worker_id = WORKER_ID
    job.claimed_at = utcnow()
    job.started_at = utcnow()
    job.progress = 0
    await db.commit()
    return job


async def _recover_stale_running_jobs(db) -> int:
    """Rule 4/crash-recovery: a job RUNNING for longer than
    STALE_RUNNING_MINUTES is presumed to belong to a crashed worker and is
    returned to PENDING (bounded by MAX_RETRIES) or FAILED."""
    from app.engines.enterprise_grid.models import EnterpriseExportJob

    cutoff = utcnow() - timedelta(minutes=STALE_RUNNING_MINUTES)
    result = await db.execute(
        select(EnterpriseExportJob).where(
            EnterpriseExportJob.status == "processing",
            EnterpriseExportJob.claimed_at < cutoff,
        )
    )
    stale = result.scalars().all()
    recovered = 0
    for job in stale:
        if job.retry_count >= MAX_RETRIES:
            job.status = "failed"
            job.error_code = "EXPORT_WORKER_TIMEOUT"
            job.error_message = "Export processing timed out after repeated worker crashes."
        else:
            job.status = "pending"
            job.retry_count += 1
            job.worker_id = None
            job.claimed_at = None
        recovered += 1
    if recovered:
        await db.commit()
        log.info("export_worker.stale_recovered", count=recovered)
    return recovered


async def _process_job(db, job) -> None:
    from app.engines.enterprise_grid.filter_registry import EnterpriseFilterRegistry
    from app.engines.enterprise_grid.resource_adapters import fetch_rows, is_runtime_supported
    from app.engines.enterprise_grid.services import ExportService
    from app.engines.enterprise_grid.export_storage import ExportStorageService
    from app.core.audit import record_platform_audit

    export_svc = ExportService()
    storage = ExportStorageService()

    if not is_runtime_supported(job.resource_key):
        job.status = "failed"
        job.error_code = "EXPORT_GENERATOR_UNAVAILABLE"
        job.error_message = f"No file-generation adapter exists yet for '{job.resource_key}'."
        job.failure_reason = job.error_message
        await db.commit()
        log.info("export_worker.unsupported_resource", job_id=str(job.id), resource=job.resource_key)
        return

    if job.export_format not in ("csv",):
        # FINAL-L5-05S Part 14/15: XLSX/PDF are NOT implemented this
        # sprint -- fail controlled rather than silently generating a CSV
        # under a different extension or hanging.
        job.status = "failed"
        job.error_code = "EXPORT_FORMAT_UNSUPPORTED"
        job.error_message = f"Format '{job.export_format}' is not supported yet (csv only)."
        job.failure_reason = job.error_message
        await db.commit()
        return

    try:
        # Rule 8: the query MUST use the job's own persisted tenant_id
        # (recorded authoritatively at creation time from the actor's
        # server-side context) -- never re-derive scope from the mutable
        # `filters` JSON blob.
        rows = await fetch_rows(db, job.resource_key, job.tenant_id, job.filters or {})
        job.progress = 50
        await db.commit()

        allowed_fields = EnterpriseFilterRegistry.get_allowed_export_fields(job.resource_key)
        columns = [c for c in (job.columns or []) if c in allowed_fields] or allowed_fields
        csv_text = export_svc.generate_csv(job.resource_key, columns, rows)
        content = csv_text.encode("utf-8")

        filename = f"{job.resource_key}-{job.id}.csv"
        stored = storage.upload_private(
            job_id=job.id, tenant_scope=job.tenant_id,
            filename=filename, content=content, content_type="text/csv",
        )

        job.status = "completed"
        job.row_count = len(rows)
        job.storage_key = stored.storage_key
        job.filename = stored.filename
        job.content_type = stored.content_type
        job.file_size = stored.file_size
        job.checksum = stored.checksum
        job.completed_at = utcnow()
        job.expires_at = utcnow() + timedelta(hours=EXPORT_EXPIRY_HOURS)
        job.progress = 100
        await db.commit()

        await record_platform_audit(
            db, operation="export.job_completed", engine_id="enterprise_grid",
            tenant_id=job.tenant_id, entity_type="export_job", entity_id=str(job.id),
            actor_id=job.requested_by_user_id, actor_role=None,
            after={"resource_key": job.resource_key, "row_count": len(rows),
                   "file_size": stored.file_size, "checksum": stored.checksum},
        )
        await db.commit()
        log.info("export_worker.completed", job_id=str(job.id), resource=job.resource_key,
                  row_count=len(rows), file_size=stored.file_size)

    except Exception as exc:
        await db.rollback()
        msg = str(exc)
        code = msg.split(":", 1)[0] if ":" in msg else "EXPORT_GENERATION_FAILED"
        retryable = not msg.startswith(NON_RETRYABLE_PREFIXES)
        # Re-fetch the job in a fresh transaction (the failed attempt may
        # have left the session in an inconsistent state after rollback).
        from app.engines.enterprise_grid.models import EnterpriseExportJob
        fresh = (await db.execute(
            select(EnterpriseExportJob).where(EnterpriseExportJob.id == job.id)
        )).scalars().first()
        if fresh is None:
            return
        if retryable and fresh.retry_count < MAX_RETRIES:
            fresh.status = "pending"
            fresh.retry_count += 1
            fresh.worker_id = None
            fresh.claimed_at = None
        else:
            fresh.status = "failed"
            fresh.error_code = code
            fresh.error_message = "Export generation failed. Contact support with the job ID if this persists."
            fresh.failure_reason = fresh.error_message
        await db.commit()
        log.error("export_worker.job_failed", job_id=str(job.id), error_code=code,
                   retryable=retryable, retry_count=fresh.retry_count)


async def run_worker_tick(batch_size: int = BATCH_SIZE) -> dict:
    """Claim and process up to `batch_size` pending jobs. Safe to call
    repeatedly/concurrently -- FOR UPDATE SKIP LOCKED prevents double
    claims even if two ticks overlap."""
    from app.database import get_session_factory

    session_factory = get_session_factory()
    processed = 0
    async with session_factory() as db:
        await _recover_stale_running_jobs(db)

    for _ in range(batch_size):
        async with session_factory() as db:
            job = await _claim_next_job(db)
            if job is None:
                break
            await _process_job(db, job)
            processed += 1
    return {"worker_id": WORKER_ID, "processed": processed, "run_at": utcnow().isoformat()}


async def run_cleanup() -> dict:
    """Rule 20/27/28: expire completed jobs past expires_at and delete
    their file; delete files for failed/cancelled jobs immediately if any
    partial object was left behind."""
    from app.database import get_session_factory
    from app.engines.enterprise_grid.models import EnterpriseExportJob
    from app.engines.enterprise_grid.export_storage import ExportStorageService
    from app.core.audit import record_platform_audit

    storage = ExportStorageService()
    expired = 0
    orphans_deleted = 0
    session_factory = get_session_factory()

    async with session_factory() as db:
        now = utcnow()
        result = await db.execute(
            select(EnterpriseExportJob).where(
                EnterpriseExportJob.status == "completed",
                EnterpriseExportJob.expires_at < now,
                EnterpriseExportJob.storage_key.isnot(None),
            )
        )
        for job in result.scalars().all():
            if job.storage_key and storage.exists(job.storage_key):
                storage.delete(job.storage_key)
                orphans_deleted += 1
            job.status = "expired"
            job.storage_key = None
            expired += 1
            await record_platform_audit(
                db, operation="export.job_expired", engine_id="enterprise_grid",
                tenant_id=job.tenant_id, entity_type="export_job", entity_id=str(job.id),
                actor_id=None, actor_role="system",
            )
        await db.commit()

        # Failed/cancelled jobs should never retain a storage object, but
        # clean up defensively in case a crash left one behind.
        result2 = await db.execute(
            select(EnterpriseExportJob).where(
                EnterpriseExportJob.status.in_(("failed", "cancelled")),
                EnterpriseExportJob.storage_key.isnot(None),
            )
        )
        for job in result2.scalars().all():
            if storage.exists(job.storage_key):
                storage.delete(job.storage_key)
                orphans_deleted += 1
            job.storage_key = None
        await db.commit()

    log.info("export_worker.cleanup_done", expired=expired, orphans_deleted=orphans_deleted)
    return {"expired": expired, "orphans_deleted": orphans_deleted, "run_at": utcnow().isoformat()}


async def background_loop(interval: int = TICK_INTERVAL_SECONDS,
                           cleanup_interval: int = CLEANUP_INTERVAL_SECONDS) -> None:
    log.info("export_worker.loop_started", worker_id=WORKER_ID, interval_seconds=interval)
    ticks_since_cleanup = 0
    ticks_per_cleanup = max(1, cleanup_interval // interval)
    while True:
        await asyncio.sleep(interval)
        try:
            result = await run_worker_tick()
            if result["processed"]:
                log.info("export_worker.loop_tick", processed=result["processed"])
            ticks_since_cleanup += 1
            if ticks_since_cleanup >= ticks_per_cleanup:
                await run_cleanup()
                ticks_since_cleanup = 0
        except asyncio.CancelledError:
            log.info("export_worker.loop_cancelled")
            raise
        except Exception as exc:
            log.error("export_worker.loop_error", error=str(exc))


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
    log.info("export_worker.cli_done", cmd=cmd, result=result)


if __name__ == "__main__":
    main()
