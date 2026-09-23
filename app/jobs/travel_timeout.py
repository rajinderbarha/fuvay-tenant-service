"""Cancel a job whose technician started travelling and never arrived.

Tapping "On my way" snapshots the provider's travel buffer into the
transition event (`stage_timer_service`). If the job is still `on_the_way`
when that buffer runs out, the technician has not reached the customer, has
not marked them unavailable and has not cancelled. Before this sweep the job
then sat open until the slot SLA closed it, up to a day later, while the
customer's app kept showing a technician on the way.

The job is now cancelled at the buffer deadline, always: no policy switch or
job-type cancellation rule keeps it open. The deadline is never earlier than
the moment the visit is actually late, though: a technician who sets off early
is on time until the booked window ends. The customer is told the technician
is not available, in the app and in the Instagram chat they booked from, and
the provider pays the same missed-arrival penalty the SLA engine would have.

The provider-health signal is unchanged. The stall watchdog used to record a
provider-owned `job_stalled` event at this same deadline, and health counts
those, so the sweep still records one before it cancels.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

import structlog
from sqlalchemy import text

from app.engines.execution.constants import EV_JOB_CANCELLED, JS_CANCELLED, JS_ON_THE_WAY
from app.engines.execution.models import ServiceJobExecutionEvent
from app.engines.execution.stage_timer_service import DEFAULT_STAGE_LIMIT_MINUTES

logger = structlog.get_logger("jobs.travel_timeout")

#: Every minute. The buffer is typically 30 minutes, so the ten-minute stall
#: watchdog cadence would let a cancellation land a third of a buffer late.
INTERVAL_SECONDS = 60
REQUEST_ID = "job:travel_timeout"
REASON_CODE = "technician_not_available"
#: `booking_updates.send_technician_unavailable_cancelled` matches on this.
FAILURE_REASON_PREFIX = "Technician not available"

_CANDIDATE_SQL = text(
    """
    SELECT j.id, j.tenant_id, j.booking_id, j.customer_id, j.job_number,
           j.assigned_staff_id, b.booking_number,
           j.sla_due_at, j.scheduled_date, j.scheduled_time_window,
           w.buffer_minutes_between_jobs AS travel_minutes,
           entered.metadata AS stage_metadata,
           COALESCE(entered.at, j.updated_at, j.created_at) AS entered_at
      FROM service_jobs j
      LEFT JOIN LATERAL (
        SELECT e.created_at AS at, e.metadata
          FROM service_job_execution_events e
         WHERE e.job_id = j.id AND e.new_status = j.status
           AND e.old_status IS DISTINCT FROM e.new_status
         ORDER BY e.created_at DESC LIMIT 1
      ) AS entered ON true
      LEFT JOIN service_bookings b ON b.id = j.booking_id
      LEFT JOIN tenant_booking_window_settings w ON w.tenant_id = j.tenant_id
     WHERE j.status = :status
       AND j.tenant_id IS NOT NULL
     ORDER BY COALESCE(entered.at, j.updated_at, j.created_at) ASC
     LIMIT :lim
    """
)


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def travel_limit_minutes(row) -> int:
    """The buffer this journey was promised when travel started.

    The snapshot wins, so a provider shortening its buffer mid-journey cannot
    cancel a technician who set off under the longer one. Jobs that entered
    travel before snapshots existed fall back to the provider's current
    buffer, where zero means the default, exactly as the snapshot would have.
    """
    default = DEFAULT_STAGE_LIMIT_MINUTES[JS_ON_THE_WAY]
    snapshot = (getattr(row, "stage_metadata", None) or {}).get("stage_timer") or {}
    raw = (snapshot.get("limit_minutes") if snapshot.get("status") == JS_ON_THE_WAY
           else getattr(row, "travel_minutes", None))
    try:
        return min(10080, max(1, int(raw or default)))
    except (TypeError, ValueError):
        return default


def travel_deadline(row, entered_at: datetime, minutes: int) -> datetime:
    """When the technician counts as not coming.

    Never before the visit is actually late. A technician who taps "On the
    way" an hour early for a 14:00-16:00 slot is on time until 16:00
    (`slot_end`: arriving at 15:45 is on time), so cancelling them 30 minutes
    after the tap told a customer their technician was unavailable while they
    were still driving over. Live technicians do set off that early. The job's
    `sla_due_at` is the same "late" moment the missed-arrival charge uses,
    grace hours included, so the two sweeps can never disagree about whether
    a visit was missed; the slot end stands in for a job that has none.
    """
    deadline = entered_at + timedelta(minutes=minutes)
    late_at = getattr(row, "sla_due_at", None)
    if late_at is None:
        from app.engines.weather.slots import slot_end
        late_at = slot_end(getattr(row, "scheduled_date", None),
                           getattr(row, "scheduled_time_window", None))
    if late_at is not None:
        deadline = max(deadline, _aware(late_at))
    return deadline


def _why(minutes: int, *, slot_bound: bool) -> str:
    """The reason, true to whichever limit actually ran out."""
    if slot_bound:
        return "did not arrive by the end of the booked visit window"
    return f"did not reach the customer within {minutes} minutes of starting travel"


async def _notify(db, row, *, why: str) -> None:
    """Customer, provider owner and technician each hear it in their own words.

    Best-effort: a notice that cannot be written must never keep a job open.
    """
    try:
        from app.engines.platform_notifications.models import InAppNotification

        booking_number = row.booking_number or row.job_number
        if row.customer_id and row.booking_id:
            db.add(InAppNotification(
                user_id=row.customer_id, tenant_id=row.tenant_id,
                notification_type="booking_cancelled_technician_unavailable",
                title="Your booking was cancelled",
                body=(f"Booking {booking_number} was cancelled because the technician "
                      "is not available. We are sorry for the inconvenience. You can "
                      "book again straight away."),
                action_url=f"/customer/bookings/{row.booking_id}",
                action_label="View booking",
                source_record_type="service_bookings", source_record_id=row.booking_id,
                severity="warning",
            ))

        body = (f"Job {row.job_number} was cancelled because the technician {why}. "
                "The customer has been told the technician is not available.")
        owner = (await db.execute(text(
            "SELECT id FROM users WHERE tenant_id = :t AND role = 'tenant_owner' "
            "AND is_active = true LIMIT 1"), {"t": str(row.tenant_id)})).scalar()
        if owner is not None:
            db.add(InAppNotification(
                user_id=owner, tenant_id=row.tenant_id,
                notification_type="job_cancelled_technician_unavailable",
                title="Job cancelled: technician did not arrive",
                body=body,
                action_url=f"/home-services/bookings-jobs?job_id={row.id}",
                action_label="Open job",
                source_record_type="service_jobs", source_record_id=row.id,
                severity="warning",
            ))
        if row.assigned_staff_id:
            staff_user = (await db.execute(text(
                "SELECT user_id FROM provider_team_members WHERE id=:staff_id "
                "AND tenant_id=:tenant_id AND deleted_at IS NULL LIMIT 1"
            ), {"staff_id": str(row.assigned_staff_id),
                "tenant_id": str(row.tenant_id)})).scalar()
            if staff_user:
                db.add(InAppNotification(
                    user_id=staff_user, tenant_id=row.tenant_id,
                    notification_type="job_cancelled_technician_unavailable",
                    title="Your job was cancelled",
                    body=f"Job {row.job_number} was cancelled because you {why}.",
                    action_url=f"/staff/home-services/jobs/{row.id}",
                    action_label="View job",
                    source_record_type="service_jobs", source_record_id=row.id,
                    severity="warning",
                ))
    except Exception as exc:  # noqa: BLE001 -- never keep the job open over a notice
        logger.warning("travel_timeout.notify_failed", job_id=str(row.id), error=str(exc))


async def _cancel(db, row, *, minutes: int, entered_at: datetime, deadline: datetime,
                  now: datetime) -> bool:
    """Cancel one overdue journey. False when the technician got there first.

    The row lock is the same one `_set_status` takes, so this cannot interleave
    with a "Reached site" tap: whichever commits second sees the other's status.
    A job locked by a request in flight is skipped and re-examined next minute.
    """
    locked = await db.scalar(text(
        "SELECT status FROM service_jobs WHERE id = :id FOR UPDATE SKIP LOCKED"
    ), {"id": str(row.id)})
    if locked != JS_ON_THE_WAY:
        return False

    why = _why(minutes, slot_bound=deadline > entered_at + timedelta(minutes=minutes))
    reason = f"{FAILURE_REASON_PREFIX}: {why}"
    stalled_for = int((now - entered_at).total_seconds() // 60)
    db.add(ServiceJobExecutionEvent(
        booking_id=row.booking_id, job_id=row.id, tenant_id=row.tenant_id,
        staff_member_id=row.assigned_staff_id,
        actor_role="platform", event_type="job_stalled",
        old_status=JS_ON_THE_WAY, new_status=JS_ON_THE_WAY,
        notes=f"No arrival for {stalled_for} minutes (limit {minutes}).",
        event_metadata={
            "status": JS_ON_THE_WAY, "stalled_minutes": stalled_for,
            "limit_minutes": minutes, "waiting_on": "provider",
            "entered_at": entered_at.isoformat(),
            "outcome": "cancelled_technician_not_available",
        },
        request_id=REQUEST_ID,
    ))

    await db.execute(text(
        "UPDATE service_jobs SET status = :cancelled, assignment_status = 'cancelled', "
        "failure_reason = :reason, updated_at = now() WHERE id = :id"
    ), {"cancelled": JS_CANCELLED, "reason": reason, "id": str(row.id)})
    if row.booking_id:
        await db.execute(text(
            "UPDATE service_bookings SET status = :cancelled, assignment_status = 'cancelled', "
            "failure_reason = :reason, updated_at = now() WHERE id = :id"
        ), {"cancelled": JS_CANCELLED, "reason": reason, "id": str(row.booking_id)})
    await db.execute(text(
        "UPDATE service_job_assignments SET is_current = false, assignment_status = 'cancelled', "
        "cancelled_at = now(), notes = :reason, updated_at = now() "
        "WHERE job_id = :id AND is_current = true"
    ), {"reason": reason, "id": str(row.id)})

    db.add(ServiceJobExecutionEvent(
        booking_id=row.booking_id, job_id=row.id, tenant_id=row.tenant_id,
        staff_member_id=row.assigned_staff_id,
        actor_role="platform", event_type=EV_JOB_CANCELLED,
        old_status=JS_ON_THE_WAY, new_status=JS_CANCELLED,
        notes=reason,
        event_metadata={
            "reason_code": REASON_CODE, "limit_minutes": minutes,
            "entered_at": entered_at.isoformat(),
            "deadline_at": deadline.isoformat(),
        },
        request_id=REQUEST_ID,
    ))
    await db.flush()
    # A no-show that ends in cancellation costs what the SLA engine's own close
    # would: cancelled jobs are outside its reach, so without this the provider
    # who set off and never arrived would pay nothing at all.
    from app.engines.execution.sla_breach_service import settle_no_arrival_close
    await settle_no_arrival_close(db, job_id=row.id)
    await _notify(db, row, why=why)

    from app.engines.tenant_engine.health import refresh_provider_operational_health
    await refresh_provider_operational_health(db, row.tenant_id)
    return True


async def sweep(db, *, limit: int = 200) -> dict:
    rows = (await db.execute(_CANDIDATE_SQL, {
        "status": JS_ON_THE_WAY, "lim": limit,
    })).fetchall()

    now = datetime.now(timezone.utc)
    cancelled: list[str] = []
    for row in rows:
        if row.entered_at is None:
            continue
        entered_at = _aware(row.entered_at)
        minutes = travel_limit_minutes(row)
        deadline = travel_deadline(row, entered_at, minutes)
        if now < deadline:
            continue
        try:
            # A savepoint per job: one bad row must not roll back every other
            # job's cancellation in the same sweep.
            async with db.begin_nested():
                done = await _cancel(db, row, minutes=minutes, entered_at=entered_at,
                                     deadline=deadline, now=now)
        except Exception as exc:  # noqa: BLE001 -- retried on the next sweep
            logger.warning("travel_timeout.cancel_failed", job_id=str(row.id), error=str(exc))
            continue
        if done:
            cancelled.append(str(row.id))
    return {"examined": len(rows), "cancelled": len(cancelled), "cancelled_job_ids": cancelled}


async def run_once() -> dict:
    from app.database import get_session_factory
    from app.engines.messaging_gateway.booking_updates import (
        send_technician_unavailable_cancelled,
    )

    async with get_session_factory()() as db:
        result = await sweep(db)
        await db.commit()
    # Only after commit: a chat message cannot be unsent, so the customer must
    # never hear about a cancellation that rolled back.
    for job_id in result["cancelled_job_ids"]:
        await send_technician_unavailable_cancelled(job_id)
    return result


async def background_loop() -> None:
    while True:
        try:
            result = await run_once()
            if result.get("cancelled"):
                logger.info("travel_timeout.swept", examined=result["examined"],
                            cancelled=result["cancelled"])
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001 -- a sweep failure must not kill the loop
            logger.warning("travel_timeout.failed", error=str(exc))
        await asyncio.sleep(INTERVAL_SECONDS)
