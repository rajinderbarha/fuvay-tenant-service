"""Masked calling — service layer.

Places a bridged call between a technician and a customer about ONE job, so
neither ever learns the other's number, and records what happened.

Off-platform prevention, concretely:
  1. `describe_contact` is the ONLY thing any caller-facing surface should show.
     It returns a display alias and a `can_call` flag -- never a number.
  2. `place_call` reads the two real numbers, hands them straight to the
     telephony provider and does not persist them.
  3. A binding is scoped to one job and expires (BINDING_TTL_MINUTES), so it is
     never a standing private line between two people.
  4. A CONNECTED call satisfies the "call the customer first" task; a ring-out
     does not, so the step cannot be ticked off without a real conversation.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.engines.masked_calling import constants as c
from app.engines.masked_calling.models import MaskedCallSession
from app.engines.masked_calling.provider import get_provider
from app.exceptions import ServiceOSException


def _now() -> datetime:
    return datetime.now(timezone.utc)


def customer_display_alias(customer_id) -> str:
    """Stable, non-identifying label. Mirrors the convention the technician
    mobile home screen already uses (`_customer_alias`)."""
    if not customer_id:
        return "Customer"
    return f"Customer HS-{str(customer_id).replace('-', '')[:4].upper()}"


async def _load_job(db: AsyncSession, job_id: uuid.UUID, tenant_id: uuid.UUID):
    row = (await db.execute(text(
        "SELECT id, booking_id, tenant_id, customer_id, status, assigned_staff_id "
        "FROM service_jobs WHERE id=:jid AND tenant_id=:tid"
    ), {"jid": str(job_id), "tid": str(tenant_id)})).fetchone()
    if not row:
        raise ServiceOSException(c.ERR_JOB_NOT_FOUND, "Job not found.", status_code=404)
    return row._mapping


async def _load_customer_job(
    db: AsyncSession, booking_id: uuid.UUID, customer_id: uuid.UUID,
):
    """Resolve an owned booking to its job without exposing whether another
    customer's booking exists."""
    row = (await db.execute(text(
        "SELECT sj.id, sj.booking_id, sj.tenant_id, sj.customer_id, "
        "sj.status, sj.assigned_staff_id "
        "FROM service_jobs sj "
        "JOIN service_bookings sb ON sb.id = sj.booking_id "
        "WHERE sb.id=:bid AND sb.customer_id=:cid"
    ), {"bid": str(booking_id), "cid": str(customer_id)})).fetchone()
    if not row:
        raise ServiceOSException(c.ERR_JOB_NOT_FOUND, "Job not found.", status_code=404)
    return row._mapping


async def _customer_number(db: AsyncSession, job) -> str | None:
    """Read at dial time only, never persisted by this engine.

    `service_bookings.customer_phone` is the number the customer gave for THIS
    booking, which is the right one to reach them on -- preferred over the
    account-level profile number, which may be stale.
    """
    if job.get("booking_id"):
        phone = (await db.execute(text(
            "SELECT customer_phone FROM service_bookings WHERE id=:bid"
        ), {"bid": str(job["booking_id"])})).scalar()
        if phone:
            return str(phone)
    if job.get("customer_id"):
        phone = (await db.execute(text(
            "SELECT phone FROM users WHERE id=:cid"
        ), {"cid": str(job["customer_id"])})).scalar()
        if phone:
            return str(phone)
    return None


async def _staff_number(db: AsyncSession, user_id: uuid.UUID) -> str | None:
    phone = (await db.execute(text(
        "SELECT phone FROM users WHERE id=:uid"
    ), {"uid": str(user_id)})).scalar()
    return str(phone) if phone else None


async def describe_contact(db: AsyncSession, job_id: uuid.UUID, tenant_id: uuid.UUID) -> dict:
    """What a job screen may show about reaching the customer.

    Never includes a phone number. `can_call` is false with an explicit reason
    when calling is unavailable, so the UI can be honest instead of showing a
    dead button or, worse, falling back to a raw number.
    """
    job = await _load_job(db, job_id, tenant_id)
    provider = get_provider()
    has_number = await _customer_number(db, job) is not None
    job_callable = str(job["status"]) not in c.NON_CALLABLE_JOB_STATUSES

    reason = None
    if not provider.configured:
        reason = c.ERR_CALLING_NOT_CONFIGURED
    elif not job_callable:
        reason = c.ERR_JOB_NOT_CALLABLE
    elif not has_number:
        reason = c.ERR_NO_CUSTOMER_NUMBER

    last = (await db.execute(
        select(MaskedCallSession)
        .where(MaskedCallSession.job_id == job_id)
        .order_by(MaskedCallSession.created_at.desc()).limit(1)
    )).scalars().first()

    return {
        "job_id": str(job_id),
        "customer_display": customer_display_alias(job.get("customer_id")),
        # Deliberately absent: any real number. Present so a client cannot
        # mistake omission for an oversight and go looking elsewhere.
        "phone_number_visible": False,
        "phone_number_policy": (
            "Calls are connected through the platform. Neither you nor the "
            "customer sees the other's number."
        ),
        "can_call": reason is None,
        "cannot_call_reason": reason,
        "connected_before": await has_connected_call(db, job_id),
        "last_call": last.to_dict() if last else None,
    }


async def has_connected_call(db: AsyncSession, job_id: uuid.UUID) -> bool:
    """Whether a real conversation has happened on this job.

    Only CONNECTED/COMPLETED count -- a ring-out or busy tone must not satisfy
    the "call the customer first" task.
    """
    row = (await db.execute(text(
        "SELECT 1 FROM masked_call_sessions "
        "WHERE job_id=:jid AND status = ANY(:st) LIMIT 1"
    ), {"jid": str(job_id), "st": list(c.CONNECTED_STATUSES)})).fetchone()
    return row is not None


async def place_call(
    db: AsyncSession, *, job_id: uuid.UUID, tenant_id: uuid.UUID,
    initiator_user_id: uuid.UUID, initiator_role: str = c.ROLE_STAFF,
) -> MaskedCallSession:
    """Bridge the technician and the customer for this job.

    Raises rather than returning a number when anything is unavailable -- there
    is no path through this function that reveals a real phone number to a
    caller, which is the invariant the whole engine rests on.
    """
    job = await _load_job(db, job_id, tenant_id)
    if str(job["status"]) in c.NON_CALLABLE_JOB_STATUSES:
        raise ServiceOSException(
            c.ERR_JOB_NOT_CALLABLE,
            "This job is closed, so a new call cannot be placed for it.",
            status_code=409,
        )

    provider = get_provider()
    if not provider.configured:
        raise ServiceOSException(
            c.ERR_CALLING_NOT_CONFIGURED,
            "Calling is not available right now. Please try again later.",
            status_code=503,
        )

    settings = get_settings()
    caller_id = settings.MASKED_CALLING_CALLER_ID
    if not caller_id:
        raise ServiceOSException(
            c.ERR_CALLING_NOT_CONFIGURED,
            "Calling is not available right now. Please try again later.",
            status_code=503,
        )

    customer_number = await _customer_number(db, job)
    if not customer_number:
        raise ServiceOSException(
            c.ERR_NO_CUSTOMER_NUMBER,
            "We do not have a contact number for this customer.",
            status_code=422,
        )
    staff_number = await _staff_number(db, initiator_user_id)
    if not staff_number:
        raise ServiceOSException(
            c.ERR_NO_STAFF_NUMBER,
            "Add a phone number to your profile before placing calls.",
            status_code=422,
        )

    session = MaskedCallSession(
        job_id=job_id, booking_id=job.get("booking_id"), tenant_id=tenant_id,
        customer_id=job.get("customer_id"),
        initiated_by_user_id=initiator_user_id, initiator_role=initiator_role,
        direction=c.DIR_STAFF_TO_CUSTOMER,
        provider=provider.name, caller_id_used=caller_id,
        status=c.STATUS_REQUESTED,
        expires_at=_now() + timedelta(minutes=c.BINDING_TTL_MINUTES),
    )
    db.add(session)
    await db.flush()   # need session.id as the provider reference

    result = await provider.bridge(
        from_number=staff_number, to_number=customer_number,
        caller_id=caller_id, reference=str(session.id),
    )
    if not result.accepted:
        session.status = c.STATUS_FAILED
        session.failure_reason = (result.failure_reason or c.ERR_PROVIDER_FAILED)[:200]
        session.ended_at = _now()
        await db.flush()
        raise ServiceOSException(
            c.ERR_PROVIDER_FAILED,
            "We could not connect the call. Please try again.",
            status_code=502,
        )

    session.provider_call_id = result.provider_call_id
    session.status = c.STATUS_RINGING
    await db.flush()
    return session


async def place_customer_call(
    db: AsyncSession, *, booking_id: uuid.UUID, customer_id: uuid.UUID,
) -> MaskedCallSession:
    """Bridge an owning customer to the technician assigned to this booking.

    The customer starts the provider bridge from their own number, but neither
    party receives the other's number. An unassigned booking cannot be called.
    """
    job = await _load_customer_job(db, booking_id, customer_id)
    if str(job["status"]) in c.NON_CALLABLE_JOB_STATUSES:
        raise ServiceOSException(
            c.ERR_JOB_NOT_CALLABLE,
            "This job is closed, so a new call cannot be placed for it.",
            status_code=409,
        )
    if not job.get("assigned_staff_id"):
        raise ServiceOSException(
            c.ERR_NO_ASSIGNED_STAFF,
            "A technician has not been assigned yet.",
            status_code=409,
        )

    provider = get_provider()
    settings = get_settings()
    caller_id = settings.MASKED_CALLING_CALLER_ID
    if not provider.configured or not caller_id:
        raise ServiceOSException(
            c.ERR_CALLING_NOT_CONFIGURED,
            "Calling is not available right now. Please try again later.",
            status_code=503,
        )

    customer_number = await _customer_number(db, job)
    if not customer_number:
        raise ServiceOSException(
            c.ERR_NO_CUSTOMER_NUMBER,
            "Add a phone number to your profile before placing calls.",
            status_code=422,
        )
    staff_number = await _staff_number(db, job["assigned_staff_id"])
    if not staff_number:
        raise ServiceOSException(
            c.ERR_NO_STAFF_NUMBER,
            "Calling is not available for this technician right now.",
            status_code=422,
        )

    session = MaskedCallSession(
        job_id=job["id"], booking_id=job.get("booking_id"),
        tenant_id=job["tenant_id"], customer_id=customer_id,
        initiated_by_user_id=customer_id, initiator_role=c.ROLE_CUSTOMER,
        direction=c.DIR_CUSTOMER_TO_STAFF,
        provider=provider.name, caller_id_used=caller_id,
        status=c.STATUS_REQUESTED,
        expires_at=_now() + timedelta(minutes=c.BINDING_TTL_MINUTES),
    )
    db.add(session)
    await db.flush()
    result = await provider.bridge(
        from_number=customer_number,
        to_number=staff_number,
        caller_id=caller_id,
        reference=str(session.id),
    )
    if not result.accepted:
        session.status = c.STATUS_FAILED
        session.failure_reason = (result.failure_reason or c.ERR_PROVIDER_FAILED)[:200]
        session.ended_at = _now()
        await db.flush()
        raise ServiceOSException(
            c.ERR_PROVIDER_FAILED,
            "We could not connect the call. Please try again.",
            status_code=502,
        )
    session.provider_call_id = result.provider_call_id
    session.status = c.STATUS_RINGING
    await db.flush()
    return session


# ── Provider status callbacks ─────────────────────────────────────────────

_PROVIDER_STATUS_MAP = {
    "in-progress": c.STATUS_CONNECTED, "in_progress": c.STATUS_CONNECTED,
    "answered": c.STATUS_CONNECTED, "connected": c.STATUS_CONNECTED,
    "completed": c.STATUS_COMPLETED, "complete": c.STATUS_COMPLETED,
    "no-answer": c.STATUS_NO_ANSWER, "no_answer": c.STATUS_NO_ANSWER,
    "missed": c.STATUS_NO_ANSWER,
    "busy": c.STATUS_BUSY,
    "failed": c.STATUS_FAILED, "canceled": c.STATUS_FAILED, "cancelled": c.STATUS_FAILED,
}


def normalize_provider_status(raw: str | None) -> str | None:
    if not raw:
        return None
    return _PROVIDER_STATUS_MAP.get(str(raw).strip().lower())


def assert_webhook_authorized(supplied_secret: str | None) -> None:
    """A forged callback must not be able to mark a call connected.

    Fails CLOSED when no secret is configured: an unauthenticated status
    endpoint that anybody can post to is worse than the feature not working,
    because a fake `connected` would tick off the technician's obligation to
    actually speak to the customer.
    """
    expected = get_settings().MASKED_CALLING_WEBHOOK_SECRET
    if not expected or not supplied_secret or supplied_secret != expected:
        raise ServiceOSException(
            c.ERR_WEBHOOK_UNAUTHORIZED, "Unauthorized.", status_code=401,
        )


async def apply_provider_status(
    db: AsyncSession, *, provider_call_id: str | None, session_reference: str | None,
    raw_status: str | None, duration_seconds: int | None = None,
    recording_url: str | None = None,
) -> MaskedCallSession | None:
    """Update a session from a provider callback.

    Matched on our OWN reference first (the id we handed the provider), falling
    back to their call id -- never on a job id supplied in the payload, which a
    forged callback could aim at any job.

    Idempotent for terminal states: a replayed 'completed' does not reopen or
    double-count a call.
    """
    session: MaskedCallSession | None = None
    if session_reference:
        try:
            session = await db.get(MaskedCallSession, uuid.UUID(str(session_reference)))
        except (ValueError, TypeError):
            session = None
    if session is None and provider_call_id:
        session = (await db.execute(
            select(MaskedCallSession).where(
                MaskedCallSession.provider_call_id == str(provider_call_id)
            ).limit(1)
        )).scalars().first()
    if session is None:
        return None

    if session.status in c.TERMINAL_STATUSES:
        return session   # already final -- replay is a no-op

    mapped = normalize_provider_status(raw_status)
    if mapped is None:
        return session   # unknown vendor status: leave state alone rather than guess

    session.status = mapped
    if provider_call_id and not session.provider_call_id:
        session.provider_call_id = str(provider_call_id)
    if mapped in c.CONNECTED_STATUSES and session.connected_at is None:
        session.connected_at = _now()
    if mapped in c.TERMINAL_STATUSES:
        session.ended_at = _now()
    if duration_seconds is not None:
        try:
            session.duration_seconds = max(0, int(duration_seconds))
        except (ValueError, TypeError):
            pass
    if recording_url:
        session.recording_url = str(recording_url)[:1000]
    session.updated_at = _now()
    await db.flush()

    # A real conversation satisfies the provider's first task. Recorded through
    # the execution engine's own event so there is ONE definition of
    # "customer contacted", shared with the manual endpoint.
    if mapped in c.CONNECTED_STATUSES:
        await _record_customer_contacted(db, session)
    return session


async def _record_customer_contacted(db: AsyncSession, session: MaskedCallSession) -> None:
    from app.engines.execution.constants import EV_CUSTOMER_CONTACTED
    from app.engines.execution.models import ServiceJobExecutionEvent

    already = (await db.execute(text(
        "SELECT 1 FROM service_job_execution_events "
        "WHERE job_id=:jid AND event_type=:et LIMIT 1"
    ), {"jid": str(session.job_id), "et": EV_CUSTOMER_CONTACTED})).fetchone()
    if already:
        return
    status = (await db.execute(text(
        "SELECT status FROM service_jobs WHERE id=:jid"
    ), {"jid": str(session.job_id)})).scalar()
    db.add(ServiceJobExecutionEvent(
        booking_id=session.booking_id, job_id=session.job_id, tenant_id=session.tenant_id,
        staff_member_id=None, actor_user_id=session.initiated_by_user_id, actor_role="staff",
        event_type=EV_CUSTOMER_CONTACTED, old_status=status, new_status=status,
        notes="Customer reached on a platform-connected call.",
        event_metadata={"masked_call_session_id": str(session.id), "via": "masked_call"},
        request_id=None,
    ))
    await db.flush()
