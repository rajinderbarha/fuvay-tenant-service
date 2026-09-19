"""Escalate a job whose execution has stopped moving.

Before this, the moment a technician marked "reached site" the job left the
reach of every timer the platform had:

  * `provider_assignment_timeout` only looks at jobs with NO technician
    assigned (TECHNICIAN_ASSIGNMENT_PENDING_STATUSES).
  * `sla_breach` only looks at BREACHABLE_STATUSES, which stops at
    `on_the_way`, and only while `arrival_verified_at IS NULL`.

So `on_the_way` had no provider-travel-duration timer, while `reached_site`,
`inspection_started`, `inspection_done`, `quote_required`,
`service_started`, `work_done` and `customer_not_available` had no deadline of
any kind. A technician whose phone died mid-visit left the job open forever:
the customer's app kept showing it as live, the chat bot kept offering it under
"Track my booking", no penalty applied, and provider health never noticed.

This sweep escalates at the deadline and again at the critical threshold. It
never fabricates an arrival, inspection, work, payment, or completion event:
elapsed time is not evidence of what happened on site.  The separate
missed-arrival SLA still owns penalties and safe closure before verified field
work begins.  Post-arrival stalls remain visible to a human who can continue or
cancel the job with the correct reason.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

import structlog
from sqlalchemy import text

from app.engines.execution.models import ServiceJobExecutionEvent
from app.engines.execution.stage_timer_service import DEFAULT_STAGE_LIMIT_MINUTES, WAITING_ON

logger = structlog.get_logger("jobs.job_stall_watchdog")

INTERVAL_SECONDS = 600
EVENT_TYPE = "job_stalled"
CRITICAL_EVENT_TYPE = "job_stage_critical"

#: How long a job may sit in each status before a human should look at it.
#: Deliberately generous -- this is a safety net for an abandoned job, not an
#: SLA. A real deep-clean can run for hours, so a limit tight enough to be
#: "helpful" would only teach providers to ignore the alert.
STALL_LIMIT_MINUTES: dict[str, int] = {
    # This value is replaced with the provider's snapshotted travel buffer.
    "on_the_way": DEFAULT_STAGE_LIMIT_MINUTES["on_the_way"],
    # On site but nothing started. The shortest limit here: arriving and then
    # going quiet is the strongest signal that something went wrong.
    "reached_site": 45,
    "inspection_started": 120,
    # Inspection finished but no estimate raised and no work begun.
    "inspection_done": 120,
    # Waiting on the CUSTOMER, not the technician, so this one is long -- and
    # the message has to say who it is waiting for.
    "quote_required": 2880,
    "service_started": 480,
    # Work is finished; only the paperwork/payment step is missing.
    "work_done": 1440,
    # Recoverable, but it must not become a parking space.
    "customer_not_available": 240,
}

#: Whose turn it is, per status -- the alert is useless if it blames the wrong
#: party, and `quote_required` in particular is the customer's move.
_WAITING_ON = WAITING_ON

_CANDIDATE_SQL = text(
    """
    SELECT j.id, j.tenant_id, j.booking_id, j.job_number, j.status,
           j.assigned_staff_id, j.sla_due_at, j.sla_enforcement_started_at,
           j.customer_id, j.job_type_id, j.scheduled_date, j.scheduled_time_window,
           COALESCE((SELECT i.total_amount FROM service_invoices i
                     WHERE i.job_id=j.id AND i.status<>'cancelled'
                     ORDER BY i.created_at DESC LIMIT 1), 0) AS job_value,
           COALESCE(w.buffer_minutes_between_jobs, 30) AS travel_minutes,
           entered.metadata AS stage_metadata,
           COALESCE(entered.at, j.updated_at, j.created_at) AS entered_at,
           warned.at AS warned_at, critical.at AS critical_at
      FROM service_jobs j
      LEFT JOIN LATERAL (
        SELECT e.created_at AS at, e.metadata
          FROM service_job_execution_events e
         WHERE e.job_id = j.id AND e.new_status = j.status
           AND e.old_status IS DISTINCT FROM e.new_status
         ORDER BY e.created_at DESC LIMIT 1
      ) AS entered ON true
      LEFT JOIN LATERAL (
        SELECT max(e.created_at) AS at
          FROM service_job_execution_events e
         WHERE e.job_id = j.id AND e.new_status = j.status
           AND e.event_type = :event_type
      ) AS warned ON true
      LEFT JOIN LATERAL (
        SELECT max(e.created_at) AS at
          FROM service_job_execution_events e
         WHERE e.job_id = j.id AND e.new_status = j.status
           AND e.event_type = :critical_event_type
      ) AS critical ON true
      LEFT JOIN tenant_booking_window_settings w ON w.tenant_id = j.tenant_id
     WHERE j.status = ANY(:statuses)
       AND j.tenant_id IS NOT NULL
     ORDER BY COALESCE(entered.at, j.updated_at, j.created_at) ASC
     LIMIT :lim
    """
)


def _limit_minutes(status: str, policy, job=None) -> int:
    """Per-status limit, overridable by the operations policy when it has one."""
    default = STALL_LIMIT_MINUTES[status]
    snapshot = (getattr(job, "stage_metadata", None) or {}).get("stage_timer", {}) if job else {}
    if snapshot.get("status") == status:
        try:
            return max(1, int(snapshot["limit_minutes"]))
        except (KeyError, TypeError, ValueError):
            pass
    if status == "on_the_way" and job is not None:
        try:
            return max(1, int(getattr(job, "travel_minutes", None) or default))
        except (TypeError, ValueError):
            return default
    overrides = getattr(policy, "job_stall_limit_minutes", None) or {}
    try:
        return max(1, int(overrides.get(status, default)))
    except (TypeError, ValueError):
        return default


async def _notify_provider(db, *, job, minutes: int) -> None:
    """Tell the provider's owner, in the words of whoever has to act.

    Best-effort: an escalation that cannot be delivered must still be recorded.
    """
    try:
        from app.engines.platform_notifications.models import InAppNotification

        owner = (await db.execute(text(
            "SELECT id FROM users WHERE tenant_id = :t AND role = 'tenant_owner' "
            "AND is_active = true LIMIT 1"), {"t": str(job.tenant_id)})).scalar()
        if owner is None:
            return
        hours = minutes / 60
        elapsed = f"{minutes} minutes" if minutes < 120 else f"{hours:.0f} hours"
        waiting_on = _WAITING_ON.get(job.status)
        if waiting_on == "customer":
            body = (f"Job {job.job_number} has been waiting on the customer for "
                    f"over {elapsed}. Follow it up so it does not stall.")
        else:
            body = (f"Job {job.job_number} has not moved from "
                    f"'{job.status.replace('_', ' ')}' for over {elapsed}. "
                    "Check whether the technician needs help.")
        db.add(InAppNotification(
            user_id=owner, tenant_id=job.tenant_id,
            notification_type="job_stalled",
            title="A job has stopped progressing",
            body=body,
            action_url=f"/home-services/bookings-jobs?job_id={job.id}", action_label="Open job",
            source_record_type="service_jobs", source_record_id=job.id,
            severity="warning",
        ))
        staff_id = getattr(job, "assigned_staff_id", None)
        if staff_id:
            staff_user = (await db.execute(text(
                "SELECT user_id FROM provider_team_members WHERE id=:staff_id "
                "AND tenant_id=:tenant_id AND deleted_at IS NULL LIMIT 1"
            ), {"staff_id": str(staff_id), "tenant_id": str(job.tenant_id)})).scalar()
            if staff_user:
                db.add(InAppNotification(
                    user_id=staff_user, tenant_id=job.tenant_id,
                    notification_type="job_stage_deadline",
                    title="Action required on your active job",
                    body=body,
                    action_url=f"/staff/home-services/jobs/{job.id}",
                    action_label="Continue job",
                    source_record_type="service_jobs", source_record_id=job.id,
                    severity="warning",
                ))
    except Exception as exc:  # noqa: BLE001 -- never lose the escalation to a notice
        logger.warning("job_stall_watchdog.notify_failed",
                       job_id=str(job.id), error=str(exc))


async def sweep(db, *, limit: int = 100) -> dict:
    from app.engines.vertical_monetization.runtime_operations import (
        get_home_services_operations_policy,
    )

    policy = await get_home_services_operations_policy(db)
    if not getattr(policy, "job_stall_watchdog_enabled", True):
        return {"examined": 0, "escalated": 0, "disabled": True}

    rows = (await db.execute(_CANDIDATE_SQL, {
        "statuses": list(STALL_LIMIT_MINUTES),
        "event_type": EVENT_TYPE,
        "critical_event_type": CRITICAL_EVENT_TYPE,
        "lim": limit,
    })).fetchall()

    now = datetime.now(timezone.utc)
    escalated = 0
    critical = 0
    penalised = 0
    closed = 0
    for job in rows:
        minutes = _limit_minutes(job.status, policy, job)
        entered_at = job.entered_at
        if entered_at is None:
            continue
        if entered_at.tzinfo is None:
            entered_at = entered_at.replace(tzinfo=timezone.utc)
        if now - entered_at < timedelta(minutes=minutes):
            continue
        # One escalation per entry into a status, not one per sweep: a job
        # left overnight must not generate a notification every ten minutes.
        # A LATER re-entry into the same status escalates again, because
        # `warned_at` is then older than `entered_at`.
        warned_at = job.warned_at
        if warned_at is not None:
            if warned_at.tzinfo is None:
                warned_at = warned_at.replace(tzinfo=timezone.utc)
            already_warned = warned_at >= entered_at
        else:
            already_warned = False

        critical_at = getattr(job, "critical_at", None)
        if critical_at is not None and critical_at.tzinfo is None:
            critical_at = critical_at.replace(tzinfo=timezone.utc)
        already_critical = critical_at is not None and critical_at >= entered_at

        # Travel is also subject to the financial missed-arrival lifecycle.
        # Enrol old jobs that entered travel before assignment-time stamping
        # existed; the SLA worker owns the eventual penalty/closure decision.
        if (job.status == "on_the_way"
                and getattr(job, "sla_due_at", None) is None
                and getattr(job, "sla_enforcement_started_at", None) is None):
            try:
                from app.engines.execution.sla_breach_service import stamp_due_at
                await stamp_due_at(db, job.id)
            except Exception as exc:  # noqa: BLE001
                logger.warning("job_stall_watchdog.sla_enrol_failed",
                               job_id=str(job.id), error=str(exc))

        # A verified arrival ends the missed-arrival clock, but it must not be
        # a loophole that lets the provider park the job forever. Provider-
        # owned post-arrival stages use the same policy amounts: initial
        # deduction after both slot and stage deadlines, cumulative close
        # deduction after the configured (normally 24-hour) window.
        from app.engines.execution.sla_breach_service import enforce_stalled_provider_stage
        stage_enforcement = await enforce_stalled_provider_stage(
            db, job=job, entered_at=entered_at,
            stage_limit_minutes=minutes, now=now,
        )
        if stage_enforcement.get("penalised"):
            penalised += 1
        if stage_enforcement.get("closed"):
            closed += 1
            continue

        if already_warned and (now - entered_at) < timedelta(minutes=minutes * 2):
            continue
        if already_warned and already_critical:
            continue

        stalled_for = int((now - entered_at).total_seconds() // 60)
        is_critical = already_warned and (now - entered_at) >= timedelta(minutes=minutes * 2)
        event_type = CRITICAL_EVENT_TYPE if is_critical else EVENT_TYPE
        db.add(ServiceJobExecutionEvent(
            booking_id=job.booking_id, job_id=job.id, tenant_id=job.tenant_id,
            actor_role="platform", event_type=event_type,
            # Recorded as a non-transition: old and new are the SAME status,
            # because nothing moved. That is the point of the event.
            old_status=job.status, new_status=job.status,
            notes=(f"No progress for {stalled_for} minutes "
                   f"(limit {minutes})."),
            event_metadata={
                "status": job.status,
                "stalled_minutes": stalled_for,
                "limit_minutes": minutes,
                "waiting_on": _WAITING_ON.get(job.status, "provider"),
                "entered_at": entered_at.isoformat(),
                "outcome": "critical_provider_intervention_required" if is_critical else "escalated_no_status_change",
            },
            request_id="job:stall_watchdog",
        ))
        await db.flush()
        await _notify_provider(db, job=job, minutes=minutes)
        if is_critical:
            critical += 1
        else:
            escalated += 1

    return {"examined": len(rows), "escalated": escalated, "critical": critical,
            "penalised": penalised, "closed": closed}


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
            if result.get("escalated"):
                logger.info("job_stall_watchdog.swept", **result)
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001 -- a sweep failure must not kill the loop
            logger.warning("job_stall_watchdog.failed", error=str(exc))
        await asyncio.sleep(INTERVAL_SECONDS)
