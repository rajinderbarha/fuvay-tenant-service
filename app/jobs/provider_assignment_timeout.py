"""Escalate provider-owned jobs whose technician has not been assigned.

The provider and customer price are contractual once booking succeeds. A
missed technician-assignment deadline never transfers or cancels that job.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import uuid

import structlog
from sqlalchemy import func, select

from app.engines.execution.constants import TERMINAL_JOB_STATUSES
from app.engines.execution.models import ServiceJobExecutionEvent
from app.exceptions import ServiceOSException
from app.engines.final_records.models import ServiceJob
from app.engines.home_service_assignment.assignment_deadlines import (
    TECHNICIAN_ASSIGNMENT_PENDING_STATUSES, for_job,
)
from app.engines.home_service_assignment.constants import ASSIGN_TYPE_AUTO
from app.engines.home_service_assignment.service import HomeServiceJobAssignmentService

logger = structlog.get_logger("jobs.provider_assignment_timeout")
TIMEOUT_MINUTES = 30
INTERVAL_SECONDS = 60
ELIGIBLE_STATUSES = TECHNICIAN_ASSIGNMENT_PENDING_STATUSES
EVENT_TYPE = "technician_assignment_overdue"


async def _ranked_eligible_staff(db, service, job) -> list[uuid.UUID]:
    """Eligible technicians for this job, least-loaded first.

    Workload counts every non-terminal job the technician still holds. The
    old list named statuses the engine never writes (`in_progress`,
    `estimate_*`) and missed `service_started`, `work_done` and friends, so a
    technician mid-job looked free.
    """
    options = await service.list_eligible_staff_for_job(job.id, job.tenant_id)
    candidates = options.get("eligible_staff") or []
    if not candidates:
        return []
    ids = [candidate["staff_member_id"] for candidate in candidates]
    workload_rows = (await db.execute(
        select(ServiceJob.assigned_staff_id, func.count(ServiceJob.id))
        .where(
            ServiceJob.tenant_id == job.tenant_id,
            ServiceJob.assigned_staff_id.in_(ids),
            ServiceJob.status.notin_(list(TERMINAL_JOB_STATUSES)),
        ).group_by(ServiceJob.assigned_staff_id)
    )).all()
    workload = {str(staff_id): int(count) for staff_id, count in workload_rows}
    candidates.sort(key=lambda item: (
        workload.get(str(item["staff_member_id"]), 0),
        str(item.get("name") or "").lower(), str(item["staff_member_id"]),
    ))
    return [uuid.UUID(str(candidate["staff_member_id"])) for candidate in candidates]


async def sweep(db, *, limit: int = 50) -> dict:
    from app.engines.vertical_monetization.runtime_operations import get_home_services_operations_policy
    policy = await get_home_services_operations_policy(db)
    if not policy.assignment_timeout_enabled:
        return {"examined": 0, "auto_assigned": 0, "escalated": 0, "disabled": True}

    candidates = list((await db.execute(
        select(ServiceJob).where(
            ServiceJob.status.in_(ELIGIBLE_STATUSES),
            ServiceJob.assigned_staff_id.is_(None),
            ServiceJob.tenant_id.isnot(None),
        ).order_by(
            func.coalesce(ServiceJob.provider_offer_started_at, ServiceJob.created_at).asc()
        ).with_for_update(skip_locked=True).limit(max(limit * 5, limit))
    )).scalars().all())
    now = datetime.now(timezone.utc)
    jobs = [job for job in candidates if for_job(job, policy, now).overdue][:limit]
    service = HomeServiceJobAssignmentService(db)
    auto_assigned = escalated = 0

    for job in jobs:
        clock_started = job.provider_offer_started_at or job.created_at
        event = await db.scalar(select(ServiceJobExecutionEvent).where(
            ServiceJobExecutionEvent.job_id == job.id,
            ServiceJobExecutionEvent.tenant_id == job.tenant_id,
            ServiceJobExecutionEvent.event_type == EVENT_TYPE,
            ServiceJobExecutionEvent.created_at >= clock_started,
        ).limit(1))
        deadline = for_job(job, policy, now)
        from app.engines.weather.slots import slot_has_ended
        expired_slot = slot_has_ended(
            job.scheduled_date, job.scheduled_time_window, now=now,
        )
        first_escalation = event is None
        if first_escalation:
            event = ServiceJobExecutionEvent(
                booking_id=job.booking_id, job_id=job.id, tenant_id=job.tenant_id,
                actor_role="platform", event_type=EVENT_TYPE,
                old_status=job.status, new_status=job.status,
                notes=f"No technician was assigned within {deadline.minutes} minutes.",
                event_metadata={
                    "outcome": (
                        "slot_recovery_required"
                        if expired_slot else "awaiting_manual_assignment"
                    ),
                    "assignment_deadline_at": deadline.deadline.isoformat() if deadline.deadline else None,
                    "urgent_window": deadline.urgent, "provider_retained": True,
                },
                request_id="job:technician_assignment_overdue",
            )
            db.add(event)
            await db.flush()
            escalated += 1

        if expired_slot:
            event.event_metadata = {
                **(event.event_metadata or {}),
                "outcome": "slot_recovery_required",
                "expired_scheduled_date": (
                    job.scheduled_date.isoformat() if job.scheduled_date else None
                ),
                "expired_time_window": job.scheduled_time_window,
                "required_action": "customer_approved_reschedule",
            }
            if first_escalation:
                try:
                    from sqlalchemy import text
                    from app.engines.platform_notifications.models import InAppNotification
                    owner = (await db.execute(text(
                        "SELECT id FROM users WHERE tenant_id=:tenant_id "
                        "AND role='tenant_owner' AND is_active=true LIMIT 1"
                    ), {"tenant_id": str(job.tenant_id)})).scalar()
                    if owner:
                        db.add(InAppNotification(
                            user_id=owner, tenant_id=job.tenant_id,
                            notification_type="visit_slot_recovery_required",
                            title="Visit slot expired",
                            body=(f"Job {job.job_number} needs a new slot approved "
                                  "by the customer before technician assignment."),
                            action_url=f"/home-services/dispatch?job_id={job.id}",
                            action_label="Choose recovery slot",
                            source_record_type="service_jobs",
                            source_record_id=job.id, severity="critical",
                        ))
                except Exception:
                    pass
                from app.engines.tenant_engine.health import refresh_provider_operational_health
                await refresh_provider_operational_health(db, job.tenant_id)
            # Do not auto-assign a field worker to an appointment that can no
            # longer be met. SLA penalties continue independently.
            continue

        if getattr(policy, "assignment_auto_assign_enabled", True):
            last_error = None
            assigned_to = None
            for staff_id in await _ranked_eligible_staff(db, service, job):
                try:
                    # A savepoint per attempt: a refused assignment must not
                    # poison the transaction that also carries every other
                    # job's escalation event.
                    async with db.begin_nested():
                        await service.assign_job(
                            job_id=job.id, staff_member_id=staff_id, tenant_id=job.tenant_id,
                            actor_user_id=None,
                            notes="Automatically assigned after the provider assignment deadline.",
                            request_id="job:auto_assign_after_deadline",
                            assignment_type=ASSIGN_TYPE_AUTO, actor_role="platform",
                        )
                except (ValueError, ServiceOSException) as exc:
                    # A technician's calendar can clash with this visit, and
                    # the provider can be at its work-in-progress limit
                    # (ServiceOSException). Try the next technician; if none
                    # can take it, the next sweep retries. Catching only
                    # ValueError let the capacity error abort the whole sweep
                    # and roll back every other job's escalation with it.
                    last_error = str(getattr(exc, "detail", None) or exc)[:120]
                    continue
                assigned_to = staff_id
                break
            if assigned_to is not None:
                event.event_metadata = {
                    **(event.event_metadata or {}), "outcome": "technician_auto_assigned",
                    "staff_member_id": str(assigned_to),
                }
                auto_assigned += 1
            elif last_error:
                event.event_metadata = {
                    **(event.event_metadata or {}),
                    "outcome": "auto_assignment_retry_required",
                    "last_error": last_error,
                }

        if first_escalation:
            from app.engines.tenant_engine.health import refresh_provider_operational_health
            await refresh_provider_operational_health(db, job.tenant_id)

    return {
        "examined": len(jobs), "auto_assigned": auto_assigned, "escalated": escalated,
        "assignment_timeout_minutes": policy.assignment_timeout_minutes,
        "urgent_assignment_timeout_minutes": getattr(policy, "urgent_assignment_timeout_minutes", 10),
    }


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
            if result.get("auto_assigned") or result.get("escalated"):
                logger.info("provider_assignment_timeout.swept", **result)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.warning("provider_assignment_timeout.failed", error=str(exc))
        await asyncio.sleep(INTERVAL_SECONDS)
