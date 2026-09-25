"""Customer approval for provider-initiated Home Services slot changes.

The committed visit is never mutated when the provider asks. Approval is a
separate, durable record tied to the exact booking/customer. Capacity is
checked both when proposed and again under a transaction lock when approved.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select, text

from app.engines.booking.models import BookingRescheduleRequest
from app.engines.final_records.models import ServiceBooking, ServiceJob
from app.engines.home_service_assignment.models import (
    ServiceJobAssignment, ServiceJobAssignmentEvent,
)
from app.exceptions import ServiceOSException


PENDING = "pending"
APPROVED = "approved"
REJECTED = "rejected"
EXPIRED = "expired"
SUPERSEDED = "superseded"


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def _capacity_available(db, job: ServiceJob, day: date, window: str) -> bool:
    await db.execute(
        text("SELECT pg_advisory_xact_lock(hashtextextended(:capacity_key, 0))"),
        {"capacity_key": f"home-service-capacity:{job.tenant_id}"},
    )
    from app.engines.home_service_booking.provider_slot_service import slot_has_capacity
    return await slot_has_capacity(
        db, tenant_id=job.tenant_id, day=day, time_window=window,
        master_service_id=job.offering_id, job_type_id=job.job_type_id,
        exclude_job_id=job.id,
    )


def _result(row: BookingRescheduleRequest, *, notification_sent: bool | None = None) -> dict:
    return {
        "request_id": str(row.id),
        "booking_id": str(row.booking_id),
        "job_id": str(row.job_id),
        "status": "pending_customer_approval" if row.status == PENDING else row.status,
        "original_date": row.original_date,
        "original_time_window": row.original_slot,
        "requested_date": row.requested_date,
        "requested_time_window": row.requested_slot,
        "reason": row.reason,
        "expires_at": row.expires_at.isoformat() if row.expires_at else None,
        "notification_sent": (
            bool(row.notification_sent_at)
            if notification_sent is None else notification_sent
        ),
    }


async def create_request(
    db, *, job_id: uuid.UUID, tenant_id: uuid.UUID, requested_date: date,
    requested_time_window: str, reason: str, actor_user_id: uuid.UUID | None,
    request_id: str | None = None,
) -> dict:
    if not (reason or "").strip():
        raise ServiceOSException(
            "JOB_ASSIGNMENT_REASON_REQUIRED", "Reason is required.", status_code=422,
        )
    if requested_date < _now().date():
        raise ServiceOSException(
            "JOB_ASSIGNMENT_PAST_DATE", "The requested date cannot be in the past.",
            status_code=422,
        )
    from app.engines.weather.slots import slot_has_ended
    if slot_has_ended(requested_date, requested_time_window):
        raise ServiceOSException(
            "JOB_ASSIGNMENT_VISIT_SLOT_EXPIRED",
            "Choose a visit window that has not ended.", status_code=422,
        )
    job = (await db.execute(select(ServiceJob).where(
        ServiceJob.id == job_id,
    ).with_for_update())).scalars().first()
    if not job or str(job.tenant_id) != str(tenant_id):
        raise ServiceOSException("JOB_ASSIGNMENT_JOB_NOT_FOUND", "Job not found.", status_code=404)
    if job.status not in {
        "pending_assignment", "assigned", "accepted", "scheduled",
        "customer_not_available",
    }:
        raise ServiceOSException(
            "JOB_ASSIGNMENT_INVALID_STATUS",
            "This job cannot be rescheduled in its current stage.", status_code=409,
        )
    if job.scheduled_date is None and not job.scheduled_time_window:
        raise ServiceOSException(
            "JOB_RESCHEDULE_ORIGINAL_SLOT_REQUIRED",
            "This job has no committed slot to change.", status_code=409,
        )
    if (job.scheduled_date == requested_date
            and job.scheduled_time_window == requested_time_window):
        return {
            "job_id": str(job.id), "status": "unchanged",
            "scheduled_date": requested_date.isoformat(),
            "scheduled_time_window": requested_time_window,
        }

    from app.engines.execution.home_service_service import HomeServiceJobExecutionService
    workflow = await HomeServiceJobExecutionService()._resolve_job_type_workflow(db, job)
    if workflow is not None and not workflow.allows_reschedule:
        raise ServiceOSException(
            "JOB_ASSIGNMENT_RESCHEDULE_NOT_ALLOWED",
            "This service workflow does not allow rescheduling.", status_code=409,
        )
    from app.engines.vertical_monetization.runtime_operations import (
        get_home_services_operations_policy,
    )
    policy = await get_home_services_operations_policy(db)
    if (job.reschedule_count or 0) >= policy.customer_reschedule_limit:
        raise ServiceOSException(
            "JOB_ASSIGNMENT_RESCHEDULE_LIMIT_REACHED",
            "The reschedule limit has been reached for this booking.", status_code=409,
        )
    if not await _capacity_available(db, job, requested_date, requested_time_window):
        raise ServiceOSException(
            "JOB_ASSIGNMENT_SLOT_UNAVAILABLE",
            "That slot is no longer available. Choose another open slot.", status_code=409,
        )

    booking = await db.get(ServiceBooking, job.booking_id)
    if booking is None or not booking.customer_id:
        raise ServiceOSException(
            "JOB_RESCHEDULE_CUSTOMER_REQUIRED",
            "The booking has no verified customer who can approve this change.",
            status_code=409,
        )
    now = _now()
    pending = (await db.execute(select(BookingRescheduleRequest).where(
        BookingRescheduleRequest.job_id == job.id,
        BookingRescheduleRequest.request_source == "provider",
        BookingRescheduleRequest.status == PENDING,
    ).with_for_update())).scalars().first()
    if pending and pending.expires_at and pending.expires_at <= now:
        pending.status = EXPIRED
        pending.resolved_at = now
        await db.flush()
        pending = None
    if pending and pending.requested_date == requested_date.isoformat() \
            and pending.requested_slot == requested_time_window:
        return _result(pending)
    if pending:
        pending.status = SUPERSEDED
        pending.resolved_at = now
        pending.resolved_by = actor_user_id
        await db.flush()

    row = BookingRescheduleRequest(
        booking_id=booking.id, job_id=job.id, tenant_id=tenant_id,
        requested_by=actor_user_id, request_source="provider",
        original_date=job.scheduled_date.isoformat() if job.scheduled_date else None,
        original_slot=job.scheduled_time_window,
        requested_date=requested_date.isoformat(),
        requested_slot=requested_time_window, reason=reason.strip(), status=PENDING,
        expires_at=now + timedelta(hours=policy.provider_reschedule_approval_hours),
    )
    db.add(row)
    await db.flush()
    db.add(ServiceJobAssignmentEvent(
        job_id=job.id, booking_id=booking.id, tenant_id=tenant_id,
        actor_user_id=actor_user_id, actor_role="provider",
        event_type="provider_reschedule_requested",
        old_value={"scheduled_date": row.original_date,
                   "scheduled_time_window": row.original_slot},
        new_value={"scheduled_date": row.requested_date,
                   "scheduled_time_window": row.requested_slot,
                   "request_id": str(row.id), "status": PENDING},
        reason=row.reason, request_id=request_id,
    ))
    # Customer app users see the same approval even when the booking was not
    # created in Instagram. Chat delivery is added after the transaction commits.
    try:
        from app.engines.platform_notifications.models import InAppNotification
        db.add(InAppNotification(
            user_id=booking.customer_id, tenant_id=tenant_id,
            notification_type="provider_reschedule_requested",
            title="Approve a new visit slot",
            body=(f"Your provider requested {row.requested_date} "
                  f"({row.requested_slot}) for booking {booking.booking_number}."),
            action_url=f"/customer/bookings/{booking.id}",
            action_label="Review request", source_record_type="booking_reschedule_requests",
            source_record_id=row.id, severity="warning",
        ))
    except Exception:
        pass
    await db.flush()
    return _result(row)


async def deliver_request(db, request_id: uuid.UUID) -> bool:
    row = await db.get(BookingRescheduleRequest, request_id)
    if row is None or row.request_source != "provider" or row.status != PENDING:
        return False
    # Provider-router retries must not produce duplicate Instagram approval
    # prompts after the first delivery was recorded successfully.
    if row.notification_sent_at:
        return True
    if row.expires_at and row.expires_at <= _now():
        row.status = EXPIRED
        row.resolved_at = _now()
        await db.flush()
        return False
    job = await db.get(ServiceJob, row.job_id)
    booking = await db.get(ServiceBooking, row.booking_id)
    if not job or not booking:
        return False
    from app.engines.messaging_gateway.booking_updates import send_reschedule_approval_request
    sent = await send_reschedule_approval_request(db, job, row)
    if sent:
        row.notification_sent_at = _now()
        await db.flush()
    return sent


async def pending_for_customer(
    db, customer_id: uuid.UUID, *, source_channel: str | None = None,
    source_actor_id: str | None = None, booking_number: str | None = None,
) -> list[dict]:
    now = _now()
    query = (
        select(BookingRescheduleRequest, ServiceBooking.booking_number)
        .join(ServiceBooking, ServiceBooking.id == BookingRescheduleRequest.booking_id)
        .where(
            BookingRescheduleRequest.request_source == "provider",
            BookingRescheduleRequest.status == PENDING,
            BookingRescheduleRequest.expires_at > now,
            ServiceBooking.customer_id == customer_id,
        )
    )
    if source_channel is not None:
        query = query.where(ServiceBooking.source_channel == source_channel)
    if source_actor_id is not None:
        query = query.where(ServiceBooking.source_actor_id == source_actor_id)
    if booking_number:
        query = query.where(ServiceBooking.booking_number == booking_number)
    rows = (await db.execute(
        query.order_by(BookingRescheduleRequest.created_at).limit(10)
    )).all()
    return [{**_result(req), "booking_number": number} for req, number in rows]


async def decide_request(
    db, *, request_id: uuid.UUID, customer_id: uuid.UUID, decision: str,
    actor_user_id: uuid.UUID | None = None,
) -> dict:
    row = (await db.execute(select(BookingRescheduleRequest).where(
        BookingRescheduleRequest.id == request_id,
    ).with_for_update())).scalars().first()
    if row is None or row.request_source != "provider":
        raise ServiceOSException("RESCHEDULE_REQUEST_NOT_FOUND", "Request not found.", status_code=404)
    booking = await db.get(ServiceBooking, row.booking_id)
    if booking is None or str(booking.customer_id) != str(customer_id):
        raise ServiceOSException("RESCHEDULE_REQUEST_NOT_FOUND", "Request not found.", status_code=404)
    if row.status != PENDING:
        raise ServiceOSException(
            "RESCHEDULE_REQUEST_ALREADY_DECIDED",
            "This slot-change request is no longer waiting for a decision.", status_code=409,
        )
    now = _now()
    if row.expires_at and row.expires_at <= now:
        row.status = EXPIRED
        row.resolved_at = now
        await db.flush()
        return _result(row)
    if decision not in {"approve", "reject"}:
        raise ServiceOSException(
            "RESCHEDULE_DECISION_INVALID", "Choose approve or reject.", status_code=422,
        )
    job = (await db.execute(select(ServiceJob).where(
        ServiceJob.id == row.job_id,
    ).with_for_update())).scalars().first()
    if job is None or str(job.booking_id) != str(booking.id):
        raise ServiceOSException("JOB_ASSIGNMENT_JOB_NOT_FOUND", "Job not found.", status_code=404)

    row.resolved_at = now
    row.resolved_by = actor_user_id or customer_id
    if decision == "reject":
        row.status = REJECTED
        row.rejection_reason = "Customer declined the proposed visit slot."
        db.add(ServiceJobAssignmentEvent(
            job_id=job.id, booking_id=booking.id, tenant_id=job.tenant_id,
            actor_user_id=customer_id, actor_role="customer",
            event_type="provider_reschedule_rejected",
            old_value={"scheduled_date": row.original_date,
                       "scheduled_time_window": row.original_slot},
            new_value={"request_id": str(row.id), "status": REJECTED},
            reason=row.rejection_reason,
        ))
        await _notify_provider_decision(db, job, row, approved=False)
        await db.flush()
        return _result(row)

    requested_date = date.fromisoformat(str(row.requested_date))
    requested_window = str(row.requested_slot or "").strip()
    if not await _capacity_available(db, job, requested_date, requested_window):
        # Do not consume the decision: the provider can supersede this now-full
        # proposal with another slot, while the original commitment stays safe.
        row.status = EXPIRED
        row.rejection_reason = "The proposed slot became unavailable before approval."
        await _notify_provider_decision(db, job, row, approved=False)
        await db.flush()
        return {**_result(row), "status": "slot_unavailable"}
    from app.engines.vertical_monetization.runtime_operations import (
        get_home_services_operations_policy,
    )
    policy = await get_home_services_operations_policy(db)
    if (job.reschedule_count or 0) >= policy.customer_reschedule_limit:
        row.status = EXPIRED
        row.rejection_reason = "The reschedule limit was reached before approval."
        await _notify_provider_decision(db, job, row, approved=False)
        await db.flush()
        return {**_result(row), "status": "reschedule_limit_reached"}

    old_status = job.status
    job.scheduled_date = requested_date
    job.scheduled_time_window = requested_window
    job.status = "scheduled"
    job.reschedule_count = (job.reschedule_count or 0) + 1
    job.reminder_24h_sent_at = None
    job.reminder_1h_sent_at = None
    job.provider_reminder_30m_sent_at = None
    job.staff_reminder_30m_sent_at = None
    job.arrival_verified_at = None
    job.arrival_distance_meters = None
    job.sla_stopped_at = None
    booking.preferred_date = requested_date
    booking.preferred_time_window = requested_window
    booking.status = "scheduled"
    assignment = (await db.execute(select(ServiceJobAssignment).where(
        ServiceJobAssignment.job_id == job.id,
        ServiceJobAssignment.is_current.is_(True),
    ).with_for_update())).scalars().first()
    if assignment:
        assignment.scheduled_date = requested_date
        assignment.scheduled_time_window = requested_window
    row.status = APPROVED
    await db.flush()
    from app.engines.execution.sla_breach_service import stamp_due_at
    await stamp_due_at(db, job.id)
    db.add(ServiceJobAssignmentEvent(
        job_id=job.id, booking_id=booking.id, tenant_id=job.tenant_id,
        assignment_id=assignment.id if assignment else None,
        actor_user_id=customer_id, actor_role="customer",
        event_type="provider_reschedule_approved",
        old_value={"scheduled_date": row.original_date,
                   "scheduled_time_window": row.original_slot,
                   "status": old_status},
        new_value={"scheduled_date": row.requested_date,
                   "scheduled_time_window": row.requested_slot,
                   "status": "scheduled", "request_id": str(row.id)},
        reason=row.reason,
    ))
    await _notify_provider_decision(db, job, row, approved=True)
    if assignment:
        await _notify_assigned_technician_rescheduled(db, job, assignment, row)
    await db.flush()
    return _result(row)


async def _notify_provider_decision(db, job, row, *, approved: bool) -> None:
    try:
        from app.engines.platform_notifications.models import InAppNotification
        owner = (await db.execute(text(
            "SELECT id FROM users WHERE tenant_id=:tenant_id AND role='tenant_owner' "
            "AND is_active=true LIMIT 1"
        ), {"tenant_id": str(job.tenant_id)})).scalar()
        if owner:
            rejected = row.status == REJECTED
            db.add(InAppNotification(
                user_id=owner, tenant_id=job.tenant_id,
                notification_type=(
                    "provider_reschedule_approved" if approved
                    else "provider_reschedule_rejected" if rejected
                    else "provider_reschedule_unavailable"
                ),
                title=(
                    "Customer approved the new slot" if approved
                    else "Customer declined the new slot" if rejected
                    else "Proposed slot is no longer available"
                ),
                body=(f"Job {job.job_number}: {row.requested_date} "
                      f"({row.requested_slot})."
                      + (f" {row.rejection_reason}" if row.rejection_reason else "")),
                action_url=f"/home-services/dispatch?job_id={job.id}",
                action_label="Open dispatch", source_record_type="booking_reschedule_requests",
                source_record_id=row.id, severity="info" if approved else "warning",
            ))
    except Exception:
        pass


async def _notify_assigned_technician_rescheduled(db, job, assignment, row) -> None:
    """Tell the field user when an approved customer decision moves a visit."""
    try:
        from app.engines.auth.models import User
        from app.engines.home_service_assignment.staff_model import ProviderTeamMember
        from app.engines.platform_notifications.models import InAppNotification

        staff_id = assignment.assigned_staff_member_id
        recipient = (await db.execute(select(ProviderTeamMember.user_id).where(
            ProviderTeamMember.id == staff_id,
            ProviderTeamMember.tenant_id == job.tenant_id,
            ProviderTeamMember.deleted_at.is_(None),
        ))).scalar_one_or_none()
        if recipient is None:
            recipient = (await db.execute(select(User.id).where(
                User.id == staff_id,
                User.tenant_id == job.tenant_id,
            ))).scalar_one_or_none()
        if recipient:
            db.add(InAppNotification(
                user_id=recipient, tenant_id=job.tenant_id,
                notification_type="assigned_visit_rescheduled",
                title="Visit time updated",
                body=(f"Customer approved {row.requested_date} "
                      f"({row.requested_slot}) for job {job.job_number}."),
                action_url=f"/staff/jobs/{job.id}", action_label="Open job",
                source_record_type="booking_reschedule_requests",
                source_record_id=row.id, severity="warning",
            ))
    except Exception:
        pass
