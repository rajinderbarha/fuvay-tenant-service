"""Customer-backed arrival confirmation for Instagram-created visits.

The customer never leaves Instagram.  A technician supplies fresh device GPS,
then the customer confirms the doorstep arrival through a postback or gives a
short-lived one-time code to the technician in person.  Neither approximate
postal addresses nor a technician's self-declared status can stop the arrival
SLA on their own.
"""
from __future__ import annotations

import hashlib
import hmac
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.engines.execution.constants import EV_REACHED_SITE, JS_ON_THE_WAY, JS_REACHED_SITE
from app.engines.execution.models import ServiceJobArrivalChallenge, ServiceJobExecutionEvent
from app.engines.final_records.models import ServiceBooking, ServiceJob
from app.exceptions import ServiceOSException

CHALLENGE_TTL_MINUTES = 10
MAX_CODE_ATTEMPTS = 5


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _code_hash(challenge_id: uuid.UUID, code: str) -> str:
    secret = get_settings().SECRET_KEY.encode("utf-8")
    material = f"arrival:{challenge_id}:{code}".encode("utf-8")
    return hmac.new(secret, material, hashlib.sha256).hexdigest()


async def _assigned_location(db: AsyncSession, job: ServiceJob, staff_member_id: uuid.UUID):
    location = (await db.execute(text(
        "SELECT latitude, longitude, accuracy_meters, recorded_at "
        "FROM technician_live_locations WHERE job_id=:jid AND staff_id=:sid LIMIT 1"
    ), {"jid": str(job.id), "sid": str(staff_member_id)})).first()
    if not location:
        raise ServiceOSException(
            "ARRIVAL_LOCATION_REQUIRED",
            "Enable location and update your current GPS before requesting arrival confirmation.",
            status_code=409,
        )

    from app.engines.vertical_monetization.runtime_operations import (
        get_home_services_operations_policy,
    )
    policy = await get_home_services_operations_policy(db)
    recorded_at = location.recorded_at
    if recorded_at.tzinfo is None:
        recorded_at = recorded_at.replace(tzinfo=timezone.utc)
    age = (_now() - recorded_at).total_seconds()
    if age > int(policy.arrival_location_max_age_seconds):
        raise ServiceOSException(
            "ARRIVAL_LOCATION_STALE",
            "Update your current GPS before requesting arrival confirmation.",
            status_code=409,
        )
    accuracy = float(location.accuracy_meters) if location.accuracy_meters is not None else None
    if accuracy is None or accuracy > int(policy.arrival_max_accuracy_meters):
        raise ServiceOSException(
            "ARRIVAL_LOCATION_INACCURATE",
            "Wait for a more accurate GPS signal before requesting arrival confirmation.",
            status_code=409,
        )
    return location, accuracy, recorded_at


async def request_arrival_confirmation(
    db: AsyncSession, *, job: ServiceJob, staff_member_id: uuid.UUID,
    requested_by_user_id: uuid.UUID | None,
) -> dict:
    """Create the one pending challenge for an Instagram visit.

    The plain code is sent only to the booking's captured Instagram identity.
    It is deliberately absent from the return value and every audit event.
    """
    if job.status != JS_ON_THE_WAY:
        raise ServiceOSException(
            "ARRIVAL_REQUEST_INVALID_STATUS",
            "Arrival can be requested only while the technician is on the way.",
            status_code=409,
        )
    if str(job.assigned_staff_id) != str(staff_member_id):
        raise ServiceOSException("EXECUTION_STAFF_NOT_ASSIGNED", "This job is not assigned to you.", status_code=403)

    booking = await db.get(ServiceBooking, job.booking_id)
    if not booking or booking.source_channel != "instagram":
        raise ServiceOSException(
            "ARRIVAL_CONFIRMATION_NOT_REQUIRED",
            "This booking does not use Instagram arrival confirmation.",
            status_code=409,
        )
    if not job.customer_id:
        raise ServiceOSException(
            "ARRIVAL_CUSTOMER_IDENTITY_REQUIRED",
            "The booking has no verified customer identity for arrival confirmation.",
            status_code=409,
        )

    existing = (await db.execute(select(ServiceJobArrivalChallenge).where(
        ServiceJobArrivalChallenge.job_id == job.id,
        ServiceJobArrivalChallenge.status == "pending",
    ).with_for_update())).scalars().first()
    now = _now()
    if existing and existing.expires_at > now:
        return {
            "job_id": str(job.id), "status": "awaiting_customer_confirmation",
            "challenge_id": str(existing.id), "expires_at": existing.expires_at.isoformat(),
            "notification_sent": bool(existing.notification_sent_at),
        }
    if existing:
        existing.status = "expired"
        existing.responded_at = now
        # Release the partial unique index before inserting the replacement
        # pending challenge.  Relying on ORM update/insert ordering here can
        # otherwise produce a transient duplicate-key failure.
        await db.flush()

    location, accuracy, recorded_at = await _assigned_location(db, job, staff_member_id)
    challenge_id = uuid.uuid4()
    code = f"{secrets.randbelow(1_000_000):06d}"
    challenge = ServiceJobArrivalChallenge(
        id=challenge_id,
        job_id=job.id, booking_id=job.booking_id, tenant_id=job.tenant_id,
        customer_id=job.customer_id, staff_member_id=staff_member_id,
        requested_by_user_id=requested_by_user_id,
        status="pending", otp_hash=_code_hash(challenge_id, code),
        failed_code_attempts=0, requested_at=now,
        expires_at=now + timedelta(minutes=CHALLENGE_TTL_MINUTES),
        technician_latitude=float(location.latitude),
        technician_longitude=float(location.longitude),
        technician_accuracy_meters=accuracy, location_recorded_at=recorded_at,
    )
    db.add(challenge)
    db.add(ServiceJobExecutionEvent(
        booking_id=job.booking_id, job_id=job.id, tenant_id=job.tenant_id,
        staff_member_id=staff_member_id, actor_user_id=requested_by_user_id,
        actor_role="staff", event_type="arrival_confirmation_requested",
        old_status=job.status, new_status=job.status,
        notes="Technician requested customer-backed arrival confirmation.",
        event_metadata={
            "challenge_id": str(challenge.id), "expires_at": challenge.expires_at.isoformat(),
            "location_recorded_at": recorded_at.isoformat(), "accuracy_meters": accuracy,
        },
    ))
    await db.flush()

    from app.engines.messaging_gateway.booking_updates import send_arrival_confirmation_request
    sent = await send_arrival_confirmation_request(db, job, challenge, code)
    if sent:
        challenge.notification_sent_at = _now()
        await db.flush()
    return {
        "job_id": str(job.id), "status": "awaiting_customer_confirmation",
        "challenge_id": str(challenge.id), "expires_at": challenge.expires_at.isoformat(),
        "notification_sent": sent,
        "instruction": (
            "Ask the customer to open the Instagram booking chat and confirm arrival. "
            "They may instead tell you the six-digit code shown there."
        ),
    }


async def _lock_challenge(db: AsyncSession, challenge_id: uuid.UUID) -> ServiceJobArrivalChallenge:
    challenge = (await db.execute(select(ServiceJobArrivalChallenge).where(
        ServiceJobArrivalChallenge.id == challenge_id,
    ).with_for_update())).scalars().first()
    if not challenge:
        raise ServiceOSException("ARRIVAL_CHALLENGE_NOT_FOUND", "Arrival request not found.", status_code=404)
    if challenge.status != "pending":
        raise ServiceOSException(
            "ARRIVAL_CHALLENGE_ALREADY_DECIDED",
            "This arrival request is no longer waiting for a decision.", status_code=409,
        )
    if challenge.expires_at <= _now():
        challenge.status = "expired"
        challenge.responded_at = _now()
        raise ServiceOSException(
            "ARRIVAL_CHALLENGE_EXPIRED",
            "The arrival code expired. Ask the technician to request a new confirmation.",
            status_code=409,
        )
    return challenge


async def confirm_arrival(
    db: AsyncSession, *, challenge_id: uuid.UUID, source: str,
    customer_id: uuid.UUID | None = None, staff_member_id: uuid.UUID | None = None,
    actor_user_id: uuid.UUID | None = None, code: str | None = None,
    expected_job_id: uuid.UUID | None = None,
) -> dict:
    challenge = await _lock_challenge(db, challenge_id)
    if expected_job_id is not None and str(challenge.job_id) != str(expected_job_id):
        raise ServiceOSException(
            "ARRIVAL_CHALLENGE_JOB_MISMATCH",
            "This arrival code belongs to a different job.", status_code=409,
        )
    if customer_id is not None and str(challenge.customer_id) != str(customer_id):
        raise ServiceOSException("ARRIVAL_CONFIRMATION_FORBIDDEN", "This arrival request is not yours.", status_code=403)
    if staff_member_id is not None and str(challenge.staff_member_id) != str(staff_member_id):
        raise ServiceOSException("ARRIVAL_CONFIRMATION_FORBIDDEN", "This job is not assigned to you.", status_code=403)
    if source == "technician_code":
        normalized = "".join(ch for ch in str(code or "") if ch.isdigit())
        valid = len(normalized) == 6 and hmac.compare_digest(
            challenge.otp_hash, _code_hash(challenge.id, normalized),
        )
        if not valid:
            challenge.failed_code_attempts += 1
            if challenge.failed_code_attempts >= MAX_CODE_ATTEMPTS:
                challenge.status = "expired"
                challenge.responded_at = _now()
            # Preserve brute-force accounting even though the API response is
            # an error and the request dependency will otherwise roll back.
            await db.commit()
            raise ServiceOSException(
                "ARRIVAL_CODE_INVALID",
                "The arrival code is incorrect or expired.", status_code=409,
            )

    job = (await db.execute(select(ServiceJob).where(
        ServiceJob.id == challenge.job_id,
    ).with_for_update())).scalars().first()
    if not job or job.status != JS_ON_THE_WAY:
        raise ServiceOSException(
            "ARRIVAL_JOB_NOT_WAITING",
            "This job is no longer waiting for arrival confirmation.", status_code=409,
        )

    now = _now()
    challenge.status = "confirmed"
    challenge.responded_at = now
    challenge.response_source = source
    job.arrival_verified_at = now
    job.arrival_distance_meters = None
    verified_location = {
        "latitude": float(challenge.technician_latitude),
        "longitude": float(challenge.technician_longitude),
        "location_source": "customer_confirmed_arrival",
        "location_confirmed_at": now.isoformat(),
    }
    job.address_snapshot = {**(job.address_snapshot or {}), **verified_location}
    booking = await db.get(ServiceBooking, challenge.booking_id)
    if booking:
        booking.address_snapshot = {**(booking.address_snapshot or {}), **verified_location}
        # Establish a reusable doorstep coordinate for later bookings at this
        # same saved address.  The customer confirmation, not Google, is what
        # makes it trusted.
        try:
            from app.engines.home_service_booking.models import HomeServiceBookingDraft
            from app.engines.serviceability.models import CustomerAddress
            draft = await db.get(HomeServiceBookingDraft, booking.draft_id)
            if draft and draft.address_id:
                address = await db.get(CustomerAddress, draft.address_id)
                if address and str(address.customer_id) == str(challenge.customer_id):
                    address.latitude = float(challenge.technician_latitude)
                    address.longitude = float(challenge.technician_longitude)
        except Exception:
            # The immutable job/challenge evidence is sufficient; a missing
            # legacy address link must not prevent the live visit progressing.
            pass

    from app.engines.execution.home_service_service import HomeServiceJobExecutionService
    await HomeServiceJobExecutionService()._set_status(
        db, job, JS_REACHED_SITE, EV_REACHED_SITE,
        actor_user_id=actor_user_id or customer_id,
        actor_role="customer" if source == "instagram_customer" else "staff",
        notes="Arrival confirmed by customer." if source == "instagram_customer" else "Arrival confirmed with customer one-time code.",
        metadata={
            "arrival_challenge_id": str(challenge.id),
            "arrival_confirmation_source": source,
            "technician_location": {
                "latitude": float(challenge.technician_latitude),
                "longitude": float(challenge.technician_longitude),
                "accuracy_meters": (float(challenge.technician_accuracy_meters)
                                    if challenge.technician_accuracy_meters is not None else None),
                "recorded_at": challenge.location_recorded_at.isoformat(),
            },
        },
    )
    from app.engines.execution.sla_breach_service import stop_sla
    await stop_sla(db, job.id)
    job.sla_due_at = None
    job.sla_next_penalty_at = None
    job.sla_stopped_at = now
    # Tracking ends at verified arrival. The immutable challenge keeps the
    # evidentiary fix; the mutable live-location row is no longer needed.
    await db.execute(text(
        "DELETE FROM technician_live_locations WHERE job_id=:job_id"
    ), {"job_id": str(job.id)})
    await db.flush()

    from app.engines.messaging_gateway.booking_updates import send_arrival_confirmed
    await send_arrival_confirmed(db, job)
    return {"job_id": str(job.id), "status": job.status, "arrival_verified": True,
            "confirmation_source": source}


async def deny_arrival(
    db: AsyncSession, *, challenge_id: uuid.UUID, customer_id: uuid.UUID,
) -> dict:
    challenge = await _lock_challenge(db, challenge_id)
    if str(challenge.customer_id) != str(customer_id):
        raise ServiceOSException("ARRIVAL_CONFIRMATION_FORBIDDEN", "This arrival request is not yours.", status_code=403)
    now = _now()
    challenge.status = "denied"
    challenge.responded_at = now
    challenge.response_source = "instagram_customer"
    challenge.denial_reason = "Customer reported that the technician was not present."
    # A retry must carry a new device fix; otherwise the technician could
    # replay the same location and repeatedly pressure the customer.
    await db.execute(text(
        "DELETE FROM technician_live_locations WHERE job_id=:job_id"
    ), {"job_id": str(challenge.job_id)})
    job = await db.get(ServiceJob, challenge.job_id)
    if job:
        db.add(ServiceJobExecutionEvent(
            booking_id=challenge.booking_id, job_id=challenge.job_id,
            tenant_id=challenge.tenant_id, staff_member_id=challenge.staff_member_id,
            actor_user_id=customer_id, actor_role="customer",
            event_type="arrival_denied_by_customer", old_status=job.status,
            new_status=job.status,
            notes=challenge.denial_reason,
            event_metadata={"challenge_id": str(challenge.id)},
        ))
        await db.flush()
        denial_count = int((await db.execute(select(func.count()).select_from(
            ServiceJobArrivalChallenge,
        ).where(
            ServiceJobArrivalChallenge.job_id == job.id,
            ServiceJobArrivalChallenge.status == "denied",
        ))).scalar_one() or 0)
        closed = await _close_repeated_denied_arrival(
            db, job=job, denial_count=denial_count,
        )
        await _notify_arrival_denied(db, job, closed=closed)
    else:
        closed = False
    await db.flush()
    return {
        "job_id": str(challenge.job_id),
        "status": "job_cancelled" if closed else "arrival_denied",
        "message": (
            "The visit was cancelled after repeated unverified arrival claims."
            if closed else
            "The provider has been alerted. Inspection remains blocked."
        ),
    }


async def _close_repeated_denied_arrival(
    db: AsyncSession, *, job: ServiceJob, denial_count: int,
) -> bool:
    """Close only after two independent customer denials.

    One denial may be a misunderstanding at a gate or a mistap.  A second
    denial requires a new challenge and a new fresh GPS fix, so continuing to
    claim arrival is no longer a safe state.  The admin-published false-arrival
    policy still controls whether automatic closure is enabled and its amount.
    """
    if denial_count < 2:
        return False
    from app.engines.vertical_monetization.runtime_operations import (
        get_home_services_operations_policy,
    )
    policy = await get_home_services_operations_policy(db)
    if not policy.false_arrival_auto_close:
        return False
    from app.engines.execution.sla_breach_service import (
        _charge_penalty, _close_breached_job,
    )
    taken = await _charge_penalty(
        db, tenant_id=job.tenant_id, job_id=job.id,
        amount=policy.false_arrival_penalty_amount, cap=None,
        day_number=1, source="repeated_arrival_denial",
    )
    await db.execute(text(
        "UPDATE service_jobs SET "
        "sla_penalty_charged=COALESCE(sla_penalty_charged,0)+:taken, "
        "sla_stopped_at=now(), sla_next_penalty_at=NULL, updated_at=now() "
        "WHERE id=:job_id"
    ), {"job_id": str(job.id), "taken": taken})
    reason = "Visit closed after the customer denied two technician arrival claims"
    await _close_breached_job(
        db, job_id=job.id, booking_id=job.booking_id, reason=reason,
    )
    job.status = "cancelled"
    job.assignment_status = "cancelled"
    job.failure_reason = reason
    db.add(ServiceJobExecutionEvent(
        booking_id=job.booking_id, job_id=job.id, tenant_id=job.tenant_id,
        staff_member_id=job.assigned_staff_id, actor_role="platform",
        event_type="repeated_arrival_denial_closed",
        old_status=JS_ON_THE_WAY, new_status="cancelled", notes=reason,
        event_metadata={"denial_count": denial_count, "penalty_amount": float(taken)},
        request_id="arrival:customer_denial",
    ))
    from app.engines.tenant_engine.health import refresh_provider_operational_health
    await refresh_provider_operational_health(db, job.tenant_id)
    return True


async def _notify_arrival_denied(
    db: AsyncSession, job: ServiceJob, *, closed: bool = False,
) -> None:
    """Escalate a denied claim without automatically declaring fraud."""
    try:
        from app.engines.platform_notifications.models import InAppNotification
        owner = (await db.execute(text(
            "SELECT id FROM users WHERE tenant_id=:tenant_id AND role='tenant_owner' "
            "AND is_active=true LIMIT 1"
        ), {"tenant_id": str(job.tenant_id)})).scalar()
        recipients: list[tuple[uuid.UUID, str]] = []
        if owner:
            recipients.append((owner, f"/home-services/bookings-jobs?job_id={job.id}"))
        staff_user = (await db.execute(text(
            "SELECT user_id FROM provider_team_members WHERE id=:staff_id "
            "AND tenant_id=:tenant_id AND deleted_at IS NULL LIMIT 1"
        ), {"staff_id": str(job.assigned_staff_id), "tenant_id": str(job.tenant_id)})).scalar()
        if staff_user:
            recipients.append((staff_user, f"/staff/home-services/jobs/{job.id}"))
        for user_id, url in recipients:
            db.add(InAppNotification(
                user_id=user_id, tenant_id=job.tenant_id,
                notification_type="arrival_denied",
                title=("Job cancelled after repeated arrival denials" if closed
                       else "Customer says technician has not arrived"),
                body=(
                    f"Job {job.job_number} was cancelled after the customer denied "
                    "two arrival claims. The configured false-arrival penalty was applied."
                    if closed else
                    f"Arrival for {job.job_number} was denied. Contact the customer and verify the visit."
                ),
                action_url=url, action_label="Open job",
                source_record_type="service_jobs", source_record_id=job.id,
                severity="critical",
            ))
    except Exception:
        # The customer decision must survive a notification subsystem issue.
        return


async def pending_arrivals_for_customer(
    db: AsyncSession, customer_id: uuid.UUID, *, source_channel: str,
    source_actor_id: str,
) -> list[dict]:
    now = _now()
    rows = (await db.execute(
        select(ServiceJobArrivalChallenge, ServiceJob.job_number, ServiceBooking.booking_number)
        .join(ServiceJob, ServiceJob.id == ServiceJobArrivalChallenge.job_id)
        .join(ServiceBooking, ServiceBooking.id == ServiceJobArrivalChallenge.booking_id)
        .where(
            ServiceJobArrivalChallenge.customer_id == customer_id,
            ServiceBooking.source_channel == source_channel,
            ServiceBooking.source_actor_id == source_actor_id,
            ServiceJobArrivalChallenge.status == "pending",
            ServiceJobArrivalChallenge.expires_at > now,
            ServiceJob.status == JS_ON_THE_WAY,
        )
        .order_by(ServiceJobArrivalChallenge.requested_at)
        .limit(5)
    )).all()
    return [{
        "challenge_id": str(challenge.id), "job_number": job_number,
        "booking_number": booking_number, "expires_at": challenge.expires_at.isoformat(),
    } for challenge, job_number, booking_number in rows]
