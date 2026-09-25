"""Governed provider cancellation workflow for Home Services.

Provider-owned reasons close immediately. A provider claim that the customer
asked to cancel becomes a durable request and does not stop SLA enforcement
until the exact booking customer confirms it.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select

from app.engines.execution.models import (
    ServiceJobCancellationRequest, ServiceJobExecutionEvent,
)
from app.engines.final_records.models import ServiceBooking, ServiceJob
from app.exceptions import ServiceOSException


PENDING = "pending"
APPROVED = "approved"
REJECTED = "rejected"
EXPIRED = "expired"
SUPERSEDED = "superseded"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _public_rule(rule: dict) -> dict:
    responsibility = str(rule.get("responsibility") or "provider")
    return {
        "code": str(rule.get("code") or ""),
        "label": str(rule.get("label") or ""),
        "outcome": str(rule.get("outcome") or "provider_cancel"),
        "responsibility": responsibility,
        "active": bool(rule.get("active", True)),
        "requires_note": bool(rule.get("requires_note", False)),
        "minimum_call_attempts": max(0, int(rule.get("minimum_call_attempts") or 0)),
        # Fail closed for customer-attributed reasons even if an old/manual DB
        # row predates the explicit health flag.
        "health_impact": bool(rule.get("health_impact", responsibility != "customer")),
    }


async def cancellation_policy(db) -> dict:
    from app.engines.vertical_monetization.runtime_operations import (
        get_home_services_operations_policy,
    )
    policy = await get_home_services_operations_policy(db)
    reasons = [
        _public_rule(rule) for rule in policy.provider_cancellation_reasons
        if isinstance(rule, dict) and rule.get("active", True)
    ]
    return {
        "confirmation_minutes": policy.provider_cancellation_confirmation_minutes,
        "minimum_note_length": policy.provider_cancellation_min_note_length,
        "reasons": reasons,
    }


async def _call_attempt_count(db, job_id: uuid.UUID) -> int:
    # Two audited call paths coexist while the native staff app migrates to
    # platform-masked calling.  Count both so a legitimate provider call from
    # the web workspace satisfies an admin-configured prerequisite, while a
    # customer-initiated reverse call never does.  One scalar query also keeps
    # this check atomic from the caller's perspective.
    from app.engines.masked_calling.models import MaskedCallSession

    legacy_calls = select(func.count(ServiceJobExecutionEvent.id)).where(
        ServiceJobExecutionEvent.job_id == job_id,
        ServiceJobExecutionEvent.event_type == "customer_call_dialed",
    ).scalar_subquery()
    masked_calls = select(func.count(MaskedCallSession.id)).where(
        MaskedCallSession.job_id == job_id,
        MaskedCallSession.direction == "staff_to_customer",
    ).scalar_subquery()
    return int(await db.scalar(select(legacy_calls + masked_calls)) or 0)


def _result(row: ServiceJobCancellationRequest, *, notification_sent=None) -> dict:
    return {
        "status": "pending_customer_confirmation" if row.status == PENDING else row.status,
        "request_id": str(row.id),
        "job_id": str(row.job_id),
        "booking_id": str(row.booking_id),
        "reason_code": row.reason_code,
        "reason_label": row.reason_label,
        "expires_at": row.expires_at.isoformat(),
        "call_attempt_count": row.call_attempt_count,
        "notification_sent": bool(row.notification_sent_at) if notification_sent is None else bool(notification_sent),
    }


async def initiate(
    db, *, job_id: uuid.UUID, tenant_id: uuid.UUID, actor_user_id: uuid.UUID,
    reason_code: str, notes: str | None, request_id: str | None = None,
) -> dict:
    job = (await db.execute(select(ServiceJob).where(
        ServiceJob.id == job_id, ServiceJob.tenant_id == tenant_id,
    ).with_for_update())).scalars().first()
    if job is None:
        raise ServiceOSException("JOB_NOT_FOUND", "Job not found.", status_code=404)
    if job.status in {"cancelled", "completed", "failed"}:
        raise ServiceOSException(
            "JOB_CANCELLATION_NOT_AVAILABLE",
            "This job is already closed and cannot be cancelled again.", status_code=409,
        )

    policy = await cancellation_policy(db)
    rule = next((r for r in policy["reasons"] if r["code"] == reason_code), None)
    if rule is None:
        raise ServiceOSException(
            "CANCELLATION_REASON_INVALID",
            "Choose one of the active cancellation reasons.", status_code=422,
        )
    clean_notes = (notes or "").strip()
    if rule["requires_note"] and len(clean_notes) < policy["minimum_note_length"]:
        raise ServiceOSException(
            "CANCELLATION_NOTE_REQUIRED",
            f"Add at least {policy['minimum_note_length']} characters explaining this cancellation.",
            status_code=422,
        )
    call_attempts = await _call_attempt_count(db, job.id)
    if call_attempts < rule["minimum_call_attempts"]:
        raise ServiceOSException(
            "CANCELLATION_CALL_ATTEMPTS_REQUIRED",
            f"Call the customer at least {rule['minimum_call_attempts']} time(s) before using this reason. "
            f"Recorded attempts: {call_attempts}.", status_code=409,
        )

    display_reason = rule["label"]
    metadata = {
        "reason_code": rule["code"], "reason_label": display_reason,
        "responsibility": rule["responsibility"],
        "health_impact": rule["health_impact"],
        "call_attempt_count": call_attempts,
        "provider_notes": clean_notes or None,
    }
    # Fail safe even if an old or manually edited policy row is malformed:
    # anything attributed to the customer requires the customer to confirm.
    requires_customer_confirmation = (
        rule["outcome"] == "customer_confirmation"
        or rule["responsibility"] == "customer"
    )
    if not requires_customer_confirmation:
        from app.engines.execution.home_service_service import HomeServiceJobExecutionService
        result = await HomeServiceJobExecutionService().cancel_job(
            db, job.id, tenant_id, actor_user_id, reason=display_reason,
            actor_role="provider", request_id=request_id, metadata=metadata,
            # Instagram delivery happens after the router commits. Sending
            # external messages inside this transaction can tell a customer a
            # job was cancelled even if the database commit later fails.
            notify_customer=False,
        )
        return {"status": "cancelled", "job": result, **metadata}

    booking = await db.get(ServiceBooking, job.booking_id)
    if booking is None or not booking.customer_id:
        raise ServiceOSException(
            "CANCELLATION_CUSTOMER_CONFIRMATION_UNAVAILABLE",
            "This booking has no verified customer who can confirm cancellation.",
            status_code=409,
        )
    now = _now()
    pending = (await db.execute(select(ServiceJobCancellationRequest).where(
        ServiceJobCancellationRequest.job_id == job.id,
        ServiceJobCancellationRequest.status == PENDING,
    ).with_for_update())).scalars().first()
    if pending and pending.expires_at <= now:
        pending.status = EXPIRED
        pending.resolved_at = now
        pending = None
        await db.flush()
    if pending and pending.reason_code == rule["code"]:
        return _result(pending)
    if pending:
        pending.status = SUPERSEDED
        pending.resolved_at = now
        pending.resolved_by = actor_user_id
        await db.flush()

    row = ServiceJobCancellationRequest(
        job_id=job.id, booking_id=booking.id, tenant_id=tenant_id,
        customer_id=booking.customer_id, requested_by_user_id=actor_user_id,
        reason_code=rule["code"], reason_label=display_reason,
        reason_snapshot=rule, provider_notes=clean_notes or None,
        call_attempt_count=call_attempts, status=PENDING, requested_at=now,
        expires_at=now + timedelta(minutes=policy["confirmation_minutes"]),
    )
    db.add(row)
    await db.flush()
    db.add(ServiceJobExecutionEvent(
        booking_id=booking.id, job_id=job.id, tenant_id=tenant_id,
        staff_member_id=job.assigned_staff_id, actor_user_id=actor_user_id,
        actor_role="provider", event_type="provider_cancellation_confirmation_requested",
        old_status=job.status, new_status=job.status, notes=display_reason,
        event_metadata={**metadata, "request_id": str(row.id),
                        "expires_at": row.expires_at.isoformat()},
        request_id=request_id,
    ))
    try:
        from app.engines.platform_notifications.models import InAppNotification
        db.add(InAppNotification(
            user_id=booking.customer_id, tenant_id=tenant_id,
            notification_type="provider_cancellation_confirmation_requested",
            title="Confirm cancellation request",
            body=f"Your provider says you requested cancellation of {booking.booking_number}.",
            action_url=f"/customer/bookings/{booking.id}", action_label="Review request",
            source_record_type="service_job_cancellation_requests",
            source_record_id=row.id, severity="warning",
        ))
    except Exception:
        pass
    await db.flush()
    return _result(row)


async def deliver_request(db, request_id: uuid.UUID) -> bool:
    row = await db.get(ServiceJobCancellationRequest, request_id)
    if row is None or row.status != PENDING:
        return False
    if row.notification_sent_at:
        return True
    if row.expires_at <= _now():
        row.status = EXPIRED
        row.resolved_at = _now()
        await db.flush()
        return False
    job = await db.get(ServiceJob, row.job_id)
    booking = await db.get(ServiceBooking, row.booking_id)
    if job is None or booking is None:
        return False
    from app.engines.messaging_gateway.booking_updates import (
        send_provider_cancellation_confirmation_request,
    )
    sent = await send_provider_cancellation_confirmation_request(db, job, row)
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
        select(ServiceJobCancellationRequest, ServiceBooking.booking_number)
        .join(ServiceBooking, ServiceBooking.id == ServiceJobCancellationRequest.booking_id)
        .where(
            ServiceJobCancellationRequest.customer_id == customer_id,
            ServiceJobCancellationRequest.status == PENDING,
            ServiceJobCancellationRequest.expires_at > now,
        )
    )
    if source_channel is not None:
        query = query.where(ServiceBooking.source_channel == source_channel)
    if source_actor_id is not None:
        query = query.where(ServiceBooking.source_actor_id == source_actor_id)
    if booking_number:
        query = query.where(ServiceBooking.booking_number == booking_number)
    rows = (await db.execute(
        query.order_by(ServiceJobCancellationRequest.requested_at).limit(10)
    )).all()
    return [{**_result(req), "booking_number": number} for req, number in rows]


async def decide_request(
    db, *, request_id: uuid.UUID, customer_id: uuid.UUID, decision: str,
    actor_user_id: uuid.UUID | None = None,
) -> dict:
    row = (await db.execute(select(ServiceJobCancellationRequest).where(
        ServiceJobCancellationRequest.id == request_id,
    ).with_for_update())).scalars().first()
    if row is None or str(row.customer_id) != str(customer_id):
        raise ServiceOSException("CANCELLATION_REQUEST_NOT_FOUND", "Request not found.", status_code=404)
    if row.status != PENDING:
        raise ServiceOSException(
            "CANCELLATION_REQUEST_ALREADY_DECIDED",
            "This cancellation request is no longer waiting for a decision.", status_code=409,
        )
    now = _now()
    if row.expires_at <= now:
        row.status = EXPIRED
        row.resolved_at = now
        await db.flush()
        return _result(row)
    if decision not in {"approve", "reject"}:
        raise ServiceOSException(
            "CANCELLATION_DECISION_INVALID", "Choose approve or reject.", status_code=422,
        )
    job = await db.get(ServiceJob, row.job_id)
    booking = await db.get(ServiceBooking, row.booking_id)
    if job is None or booking is None or str(booking.customer_id) != str(customer_id):
        raise ServiceOSException("CANCELLATION_REQUEST_NOT_FOUND", "Request not found.", status_code=404)

    row.resolved_at = now
    row.resolved_by = actor_user_id or customer_id
    if decision == "reject":
        row.status = REJECTED
        row.rejection_reason = "Customer denied requesting cancellation."
        db.add(ServiceJobExecutionEvent(
            booking_id=booking.id, job_id=job.id, tenant_id=job.tenant_id,
            staff_member_id=job.assigned_staff_id, actor_user_id=customer_id,
            actor_role="customer", event_type="provider_cancellation_rejected",
            old_status=job.status, new_status=job.status,
            notes=row.rejection_reason,
            event_metadata={"request_id": str(row.id), "reason_code": row.reason_code},
        ))
        await _notify_provider_decision(db, job, row, approved=False)
        await db.flush()
        return _result(row)

    row.status = APPROVED
    from app.engines.execution.home_service_service import HomeServiceJobExecutionService
    await HomeServiceJobExecutionService().cancel_job(
        db, job.id, job.tenant_id, actor_user_id or customer_id,
        reason=row.reason_label, actor_role="customer",
        metadata={
            "reason_code": row.reason_code, "reason_label": row.reason_label,
            "responsibility": "customer", "health_impact": False,
            "provider_request_id": str(row.id),
            "customer_confirmed": True,
        },
        notify_customer=False,
    )
    await _notify_provider_decision(db, job, row, approved=True)
    await db.flush()
    return _result(row)


async def _notify_provider_decision(db, job, row, *, approved: bool) -> None:
    try:
        from app.engines.platform_notifications.models import InAppNotification
        from app.engines.auth.models import User
        owner = (await db.execute(select(User.id).where(
            User.tenant_id == job.tenant_id, User.role == "tenant_owner",
            User.is_active.is_(True),
        ).limit(1))).scalar_one_or_none()
        if owner:
            db.add(InAppNotification(
                user_id=owner, tenant_id=job.tenant_id,
                notification_type=("provider_cancellation_customer_approved" if approved
                                   else "provider_cancellation_customer_denied"),
                title=("Customer confirmed cancellation" if approved
                       else "Customer denied cancellation request"),
                body=(f"Cancellation request for job {job.job_number} was "
                      f"{'confirmed' if approved else 'denied'} by the customer."),
                action_url=f"/home-services/bookings-jobs?job_id={job.id}",
                action_label="Open job", source_record_type="service_job_cancellation_requests",
                source_record_id=row.id, severity="warning",
            ))
    except Exception:
        pass
