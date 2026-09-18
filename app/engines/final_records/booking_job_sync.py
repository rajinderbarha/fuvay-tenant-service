"""One place that mirrors a ServiceJob's status onto its ServiceBooking.

`service_bookings.status` is a mirror of `service_jobs.status`, but the job
row has several writers and only the execution engine's `_set_status` ever
remembered to update the booking. Every other writer left the customer-facing
record frozen at whatever it happened to say:

  * `quote_checklist.quote_service._sync_job_status` -- so a customer who
    DECLINED an estimate kept a booking reading `inspection_done` forever.
    Confirmed live: BK-20260912-000005 had booking `inspection_done` against
    job `closed_estimate_declined`, written two minutes apart.
  * `execution.admin_job_actions.force_close` / `void` -- an admin closing a
    job left the booking active-looking for good.

That divergence is not cosmetic. `LIVE_BOOKING_STATUSES` in the messaging
gateway decides what the chat bot calls a live booking, so a stranded booking
is offered under "Track my booking" long after its job is terminal, and the
customer app reads the same field.

Callers pass the job status they just wrote; nothing here decides transitions
(the caller has already validated against JOB_TRANSITIONS).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


async def sync_booking_to_job_status(
    db: AsyncSession, booking_id: uuid.UUID | None, new_status: str,
    *, assignment_status: str | None = None,
) -> None:
    """Mirror `new_status` onto the booking, leaving the job row alone.

    Issued as a single UPDATE rather than a load-modify-save so it cannot
    lose a concurrent write to another column of the same booking.
    """
    if not booking_id or not new_status:
        return
    from app.engines.final_records.models import ServiceBooking

    values: dict = {"status": new_status, "updated_at": _utcnow()}
    if assignment_status:
        values["assignment_status"] = assignment_status
    await db.execute(
        update(ServiceBooking).where(ServiceBooking.id == booking_id).values(**values)
    )


async def sync_booking_of_job(
    db: AsyncSession, job_id: uuid.UUID | None, new_status: str,
) -> None:
    """Same mirror, for a caller that holds the job id but not the booking id.

    Resolves the booking through a correlated subquery so this stays ONE
    round trip -- a separate `SELECT booking_id` first would be a second
    statement for no benefit.
    """
    if not job_id or not new_status:
        return
    from app.engines.final_records.models import ServiceBooking, ServiceJob

    await db.execute(
        update(ServiceBooking)
        .where(
            ServiceBooking.id == select(ServiceJob.booking_id)
            .where(ServiceJob.id == job_id)
            .scalar_subquery()
        )
        .values(status=new_status, updated_at=_utcnow())
    )
