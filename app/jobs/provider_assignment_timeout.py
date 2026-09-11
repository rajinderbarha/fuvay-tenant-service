"""Escalate provider-owned jobs that remain without a technician for 30 minutes."""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
import uuid

import structlog
from sqlalchemy import select

from app.engines.execution.models import ServiceJobExecutionEvent
from app.engines.final_records.models import ServiceBooking, ServiceJob

logger = structlog.get_logger("jobs.provider_assignment_timeout")
TIMEOUT_MINUTES = 30
INTERVAL_SECONDS = 60
ELIGIBLE_STATUSES = ("pending_assignment", "accepted")


async def _find_replacement(db, job: ServiceJob) -> tuple[uuid.UUID, dict] | None:
    if not job.tenant_id or not job.scheduled_date or not job.scheduled_time_window:
        return None
    booking = await db.get(ServiceBooking, job.booking_id)
    if not booking:
        return None
    from app.engines.home_service_booking.matching_engine import (
        build_customer_safe_provider,
        select_best_provider,
    )
    start = str(job.scheduled_time_window).split("-", 1)[0].strip()
    previous_rows = (await db.execute(select(ServiceJobExecutionEvent.event_metadata).where(
        ServiceJobExecutionEvent.job_id == job.id,
        ServiceJobExecutionEvent.event_type == "provider_assignment_timeout",
    ))).scalars().all()
    attempted = {job.tenant_id}
    for metadata in previous_rows:
        if isinstance(metadata, dict) and metadata.get("old_tenant_id"):
            try:
                attempted.add(uuid.UUID(metadata["old_tenant_id"]))
            except (TypeError, ValueError):
                pass
    result = await select_best_provider(
        db,
        category_id=job.category_id,
        offering_id=job.offering_id,
        city=job.city or booking.city or "",
        zipcode=job.zipcode or booking.zipcode,
        job_type_id=job.job_type_id,
        requested_at=f"{job.scheduled_date.isoformat()}T{start}",
        exclude_tenant_ids=attempted,
        serialize_allocation=True,
    )
    if not result:
        return None
    from app.engines.home_service_booking.provider_slot_service import slot_has_capacity
    for signals, score in result.get("all_scored", []):
        tenant_id = uuid.UUID(signals.tenant_id)
        if await slot_has_capacity(
            db, tenant_id=tenant_id, day=job.scheduled_date,
            time_window=job.scheduled_time_window,
            master_service_id=job.offering_id, job_type_id=job.job_type_id,
            exclude_job_id=job.id,
        ):
            return tenant_id, build_customer_safe_provider(signals, score)
    return None


async def sweep(db, *, limit: int = 50) -> dict:
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=TIMEOUT_MINUTES)
    jobs = list((await db.execute(
        select(ServiceJob).where(
            ServiceJob.status.in_(ELIGIBLE_STATUSES),
            # ``assigned_staff_id`` is the canonical proof that a technician
            # owns the job. Do not trust assignment_status here: historical
            # rows can say "accepted" while still having no real assignee.
            ServiceJob.assigned_staff_id.is_(None),
            ServiceJob.tenant_id.isnot(None),
            ServiceJob.updated_at <= cutoff,
        ).order_by(ServiceJob.updated_at.asc()).with_for_update(skip_locked=True).limit(limit)
    )).scalars().all())
    reassigned = closed = 0
    for job in jobs:
        old_tenant_id = job.tenant_id
        # The timeout event is the idempotency marker and the provider-health
        # evidence. A locked row plus this check also protects manual reruns.
        seen = await db.scalar(select(ServiceJobExecutionEvent.id).where(
            ServiceJobExecutionEvent.job_id == job.id,
            ServiceJobExecutionEvent.tenant_id == old_tenant_id,
            ServiceJobExecutionEvent.event_type == "provider_assignment_timeout",
        ).limit(1))
        if seen:
            continue
        replacement = await _find_replacement(db, job)
        event = ServiceJobExecutionEvent(
            booking_id=job.booking_id, job_id=job.id, tenant_id=old_tenant_id,
            actor_role="platform", event_type="provider_assignment_timeout",
            old_status=job.status,
            notes=f"No technician was assigned within {TIMEOUT_MINUTES} minutes.",
            request_id="job:provider_assignment_timeout",
        )
        if replacement:
            new_tenant_id, provider_snapshot = replacement
            event.new_status = "pending_assignment"
            event.event_metadata = {
                "old_tenant_id": str(old_tenant_id),
                "new_tenant_id": str(new_tenant_id),
                "outcome": "provider_reassigned",
            }
            job.tenant_id = new_tenant_id
            job.status = "pending_assignment"
            job.assignment_status = "unassigned"
            job.failure_reason = None
            booking = await db.get(ServiceBooking, job.booking_id)
            if booking:
                booking.tenant_id = new_tenant_id
                booking.status = "pending_assignment"
                booking.assignment_status = "unassigned"
                booking.provider_snapshot = provider_snapshot
                db.add(booking)
            reassigned += 1
        else:
            reason = "Closed because no alternative provider was available after 30 minutes without a technician assignment."
            event.new_status = "cancelled"
            event.notes = reason
            event.event_metadata = {"outcome": "closed_no_alternative_provider"}
            job.status = "cancelled"
            job.assignment_status = "cancelled"
            job.failure_reason = reason
            booking = await db.get(ServiceBooking, job.booking_id)
            if booking:
                booking.status = "cancelled"
                booking.assignment_status = "cancelled"
                booking.failure_reason = reason
                db.add(booking)
            closed += 1
        job.updated_at = datetime.now(timezone.utc)
        db.add_all([event, job])
        await db.flush()
        from app.engines.tenant_engine.health import refresh_provider_operational_health
        await refresh_provider_operational_health(db, old_tenant_id)
    return {"examined": len(jobs), "reassigned": reassigned, "closed": closed}


async def run_once() -> dict:
    from app.database import get_session_factory
    async with get_session_factory()() as db:
        result = await sweep(db)
        await db.commit()
        return result


async def background_loop() -> None:
    while True:
        try:
            result = await run_once()
            if result["reassigned"] or result["closed"]:
                logger.info("provider_assignment_timeout.swept", **result)
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # one bad sweep must not stop future recovery
            logger.warning("provider_assignment_timeout.failed", error=str(exc))
        await asyncio.sleep(INTERVAL_SECONDS)
