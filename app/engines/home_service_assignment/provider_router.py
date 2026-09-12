"""Sprint 20 — Provider Service Job Assignment APIs."""
from __future__ import annotations
import uuid
import datetime as dt
from datetime import date

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import require_tenant_owner_mutation
from app.dependencies.auth import get_current_user, UserContext
from app.dependencies.db import get_db
from app.exceptions import ServiceOSException
from app.schemas.base import ApiResponse, ok
from app.engines.home_service_assignment.service import HomeServiceJobAssignmentService
from app.engines.home_service_assignment.constants import (
    ERR_JOB_NOT_FOUND, ERR_ACCESS_DENIED, ERR_STAFF_NOT_FOUND,
    ERR_STAFF_WRONG_TENANT, ERR_STAFF_INACTIVE, ERR_ROLE_NOT_ALLOWED,
    ERR_STAFF_NOT_ELIGIBLE, ERR_REASSIGN_NOT_ALLOWED, ERR_CANCEL_NOT_ALLOWED,
    ERR_INVALID_STATUS, ERR_REASON_REQUIRED, ERR_JOB_CANCELLED, ERR_JOB_COMPLETED,
    ERR_ASSIGNMENT_NOT_FOUND, ERR_SLOT_UNAVAILABLE,
    ERR_CUSTOMER_APPROVAL_REQUIRED, ERR_PROVIDER_OFFER_EXPIRED,
)

router = APIRouter(
    prefix="/v1/provider/service-jobs",
    tags=["Provider Service Job Assignment"],
)

_RID = lambda r: getattr(r.state, "request_id", "—")

_MESSAGES = {
    ERR_JOB_NOT_FOUND:         "Job not found.",
    ERR_ACCESS_DENIED:         "Access denied.",
    ERR_STAFF_NOT_FOUND:       "Staff member not found.",
    ERR_STAFF_WRONG_TENANT:    "Staff member does not belong to your organization.",
    ERR_STAFF_INACTIVE:        "Staff member is inactive.",
    ERR_ROLE_NOT_ALLOWED:      "Staff member's role is not eligible for field assignments.",
    ERR_STAFF_NOT_ELIGIBLE:    "Staff member is not eligible for this job.",
    ERR_REASSIGN_NOT_ALLOWED:  "Cannot reassign an already accepted job.",
    ERR_CANCEL_NOT_ALLOWED:    "Cannot cancel an accepted assignment.",
    ERR_INVALID_STATUS:        "Job is not in a valid state for this action.",
    ERR_REASON_REQUIRED:       "Reason is required.",
    ERR_JOB_CANCELLED:         "Job is cancelled.",
    ERR_JOB_COMPLETED:         "Job is already completed.",
    ERR_ASSIGNMENT_NOT_FOUND:  "No active assignment found.",
    ERR_SLOT_UNAVAILABLE:      "That slot is no longer available. Choose another open slot.",
    ERR_CUSTOMER_APPROVAL_REQUIRED: "The customer must approve any change to an existing visit slot.",
    ERR_PROVIDER_OFFER_EXPIRED: "The assignment window has expired. This job is being offered to another provider.",
}


#: HTTP status per failure kind. Everything else is a 422 (the request was
#: understood but the action is not legal in this state).
_ERR_STATUS = {
    ERR_JOB_NOT_FOUND:        404,
    ERR_STAFF_NOT_FOUND:      404,
    ERR_ASSIGNMENT_NOT_FOUND: 404,
    # 404, not 403: this fires when the job belongs to ANOTHER tenant. A 403
    # would confirm that a job with this id exists to someone who may not see
    # it; 404 keeps cross-tenant existence private, which is the same choice the
    # staff router makes.
    ERR_ACCESS_DENIED:        404,
    ERR_STAFF_WRONG_TENANT:   403,
    ERR_REASSIGN_NOT_ALLOWED: 409,
    ERR_CANCEL_NOT_ALLOWED:   409,
    ERR_JOB_CANCELLED:        409,
    ERR_JOB_COMPLETED:        409,
    ERR_SLOT_UNAVAILABLE:     409,
    ERR_CUSTOMER_APPROVAL_REQUIRED: 409,
    ERR_PROVIDER_OFFER_EXPIRED: 409,
}


def _fail(code: str) -> ServiceOSException:
    """Raise a real error instead of a 200 that merely claims to be one.

    These handlers used to `return ok(_err(code))`, which sent HTTP 200 with a
    top-level `"success": true` envelope wrapping `{"success": false, ...}`.
    Only the Dispatch board unwrapped that second layer; the job detail page's
    `handleAssign` just checked `if (res)` — and a failure object is truthy, so
    a REFUSED assignment closed the modal and refetched as though it had worked,
    with no error shown. Confirmed live: assigning a deactivated technician
    returned 200 `success: true` carrying JOB_ASSIGNMENT_STAFF_INACTIVE.

    Raising lets the shared handler emit a proper 4xx problem document, which
    `apiFetch` turns into a thrown ServiceOSError for every caller at once.
    """
    return ServiceOSException(
        error_code=code,
        detail=_MESSAGES.get(code, "Action failed."),
        status_code=_ERR_STATUS.get(code, 422),
    )


class AssignRequest(BaseModel):
    staff_member_id:       uuid.UUID
    scheduled_date:        date | None = None
    scheduled_time_window: str | None  = None
    notes:                 str | None  = None


class ReassignRequest(BaseModel):
    staff_member_id: uuid.UUID
    reason:          str


class CancelAssignmentRequest(BaseModel):
    reason: str


def _job_place(job) -> str | None:
    """A weather-resolvable location for a job.

    Prefers the coordinates on its address snapshot; a PIN alone is not a location
    this provider can resolve in India, and a bare city name can resolve to another
    country (see weather/place.py).
    """
    from app.engines.weather.place import resolve_place
    snapshot = job.address_snapshot if isinstance(job.address_snapshot, dict) else {}
    return resolve_place(
        city=snapshot.get("city") or job.city,
        state=snapshot.get("state"),
        zipcode=snapshot.get("zipcode") or job.zipcode,
        latitude=snapshot.get("latitude"),
        longitude=snapshot.get("longitude"),
    )


class ScheduleRequest(BaseModel):
    scheduled_date:        date
    scheduled_time_window: str
    # "weather" is checked against a real reading before it is accepted -- see the
    # endpoint. Any other reason is recorded as given.
    reason:                str | None = None


@router.get("/assignable", response_model=ApiResponse,
            summary="List assignable service jobs for this provider")
async def list_assignable_jobs(
    assignment_status: str | None = None,
    limit:  int = 50,
    offset: int = 0,
    r:    Request     = ...,
    user: UserContext = Depends(get_current_user),
    db:   AsyncSession = Depends(get_db),
):
    tenant_id = uuid.UUID(user.tenant_id)  # HS8 fix: was user_id, never matched any real job's tenant_id
    svc = HomeServiceJobAssignmentService(db)
    jobs = await svc.list_assignable_jobs(tenant_id, assignment_status, limit, offset)
    return ok({"jobs": jobs, "count": len(jobs)}, _RID(r), "assignment")


@router.get("/{job_id}/assignment-context", response_model=ApiResponse,
            summary="Get job assignment context including current assignment")
async def get_assignment_context(
    job_id: uuid.UUID,
    r:    Request      = ...,
    user: UserContext  = Depends(get_current_user),
    db:   AsyncSession = Depends(get_db),
):
    tenant_id = uuid.UUID(user.tenant_id)  # HS8 fix: was user_id, never matched any real job's tenant_id
    svc = HomeServiceJobAssignmentService(db)
    try:
        ctx = await svc.get_job_assignment_context(job_id, tenant_id)
    except ValueError as exc:
        code = str(exc)
        raise _fail(code)
    return ok(ctx, _RID(r), "assignment")


@router.get("/{job_id}/eligible-staff", response_model=ApiResponse,
            summary="List eligible and blocked staff for a job")
async def list_eligible_staff(
    job_id: uuid.UUID,
    r:    Request      = ...,
    user: UserContext  = Depends(get_current_user),
    db:   AsyncSession = Depends(get_db),
):
    tenant_id = uuid.UUID(user.tenant_id)  # HS8 fix: was user_id, never matched any real job's tenant_id
    svc = HomeServiceJobAssignmentService(db)
    try:
        result = await svc.list_eligible_staff_for_job(job_id, tenant_id)
    except ValueError as exc:
        code = str(exc)
        raise _fail(code)
    return ok(result, _RID(r), "assignment")


@router.post("/{job_id}/assign", response_model=ApiResponse,
             summary="Assign a technician to a job")
async def assign_job(
    job_id: uuid.UUID,
    body:   AssignRequest,
    r:      Request      = ...,
    user:   UserContext  = Depends(require_tenant_owner_mutation),
    db:     AsyncSession = Depends(get_db),
):
    tenant_id = uuid.UUID(user.tenant_id)  # HS8 fix: was user_id, never matched any real job's tenant_id
    svc = HomeServiceJobAssignmentService(db)
    try:
        result = await svc.assign_job(
            job_id=job_id, staff_member_id=body.staff_member_id,
            tenant_id=tenant_id, actor_user_id=uuid.UUID(user.user_id),
            scheduled_date=body.scheduled_date,
            scheduled_time_window=body.scheduled_time_window,
            notes=body.notes, request_id=_RID(r),
        )
        await db.commit()
    except ValueError as exc:
        code = str(exc)
        raise _fail(code)
    return ok({"success": True, "data": result}, _RID(r), "assignment")


@router.post("/{job_id}/reassign", response_model=ApiResponse,
             summary="Reassign job to a different technician")
async def reassign_job(
    job_id: uuid.UUID,
    body:   ReassignRequest,
    r:      Request      = ...,
    user:   UserContext  = Depends(require_tenant_owner_mutation),
    db:     AsyncSession = Depends(get_db),
):
    tenant_id = uuid.UUID(user.tenant_id)  # HS8 fix: was user_id, never matched any real job's tenant_id
    svc = HomeServiceJobAssignmentService(db)
    try:
        result = await svc.reassign_job(
            job_id=job_id, staff_member_id=body.staff_member_id,
            tenant_id=tenant_id, reason=body.reason,
            actor_user_id=uuid.UUID(user.user_id), request_id=_RID(r),
        )
        await db.commit()
    except ValueError as exc:
        code = str(exc)
        raise _fail(code)
    return ok({"success": True, "data": result}, _RID(r), "assignment")


@router.post("/{job_id}/cancel-assignment", response_model=ApiResponse,
             summary="Cancel the current job assignment")
async def cancel_assignment(
    job_id: uuid.UUID,
    body:   CancelAssignmentRequest,
    r:      Request      = ...,
    user:   UserContext  = Depends(require_tenant_owner_mutation),
    db:     AsyncSession = Depends(get_db),
):
    tenant_id = uuid.UUID(user.tenant_id)  # HS8 fix: was user_id, never matched any real job's tenant_id
    svc = HomeServiceJobAssignmentService(db)
    try:
        result = await svc.cancel_assignment(
            job_id=job_id, tenant_id=tenant_id, reason=body.reason,
            actor_user_id=uuid.UUID(user.user_id), request_id=_RID(r),
        )
        await db.commit()
    except ValueError as exc:
        code = str(exc)
        raise _fail(code)
    return ok({"success": True, "data": result}, _RID(r), "assignment")


@router.get("/dashboard-alerts", response_model=ApiResponse,
            summary="New and delayed jobs for the provider dashboard")
async def get_dashboard_alerts(
    since: dt.datetime | None = None,
    notify: bool = True,
    r:    Request      = ...,
    user: UserContext  = Depends(get_current_user),
    db:   AsyncSession = Depends(get_db),
):
    """What the dashboard should interrupt the provider about.

    Declared BEFORE `/{job_id}/...` on purpose: FastAPI matches in order, so a literal
    path registered after a parameterised one is swallowed by it -- "dashboard-alerts"
    would arrive as a job id and 422 on the UUID parse.

    `since` is when this dashboard last looked, echoed back from `as_of`. Without it a
    stated window applies instead of "everything", because "42 new jobs" on a first
    login is a backlog, not news.

    `notify` raises `job.delayed` for any delay not reported before -- once per job, by
    checking what was actually sent rather than a flag on the job that could drift. A
    caller polling every thirty seconds therefore does not produce a notification every
    thirty seconds. It is a query parameter so a passive refresh can opt out.
    """
    from app.engines.home_service_assignment import dashboard_alerts

    tenant_id = uuid.UUID(user.tenant_id)
    alerts = await dashboard_alerts.build_alerts(db, tenant_id, since=since)

    # Notify on EVERY delay, before the display cap is applied: a provider with 25 late
    # jobs must be told about 25, not about the five the popup has room for.
    if notify and alerts["delayed_jobs"]:
        raised = await dashboard_alerts.notify_delayed_jobs(db, tenant_id, alerts["delayed_jobs"])
        if raised:
            await db.commit()
        alerts["notifications_raised"] = raised

    cap = dashboard_alerts.MAX_ALERTS
    alerts["new_jobs"] = alerts["new_jobs"][:cap]
    alerts["delayed_jobs"] = alerts["delayed_jobs"][:cap]
    return ok(alerts, _RID(r), "assignment")


@router.get("/{job_id}/available-slots", response_model=ApiResponse,
            summary="Slots this provider can actually take, for scheduling this job")
async def get_job_available_slots(
    job_id: uuid.UUID,
    emergency: bool = False,
    r:    Request      = ...,
    user: UserContext  = Depends(get_current_user),
    db:   AsyncSession = Depends(get_db),
):
    """The provider's own bookable slots, so scheduling is a choice rather than typing.

    Reuses `provider_slot_service.list_available_slots` -- the SAME function the customer
    booking flow offers slots from, and the same one `slot_has_capacity` re-checks at
    confirmation. That matters more than the convenience: a second implementation here
    would eventually offer a window the provider's own working hours, notice period or
    per-slot capacity do not allow, and the booking would then be refused after the
    provider had already told the customer a time.

    Nothing is invented when the provider has no availability configured -- the list comes
    back empty and the caller falls back to free text rather than showing made-up windows.
    """
    from app.engines.home_service_booking import provider_slot_service

    tenant_id = uuid.UUID(user.tenant_id)
    svc = HomeServiceJobAssignmentService(db)
    job = await svc._load_job(job_id)
    if not job or str(job.tenant_id) != str(tenant_id):
        raise _fail(ERR_JOB_NOT_FOUND)

    slots = await provider_slot_service.list_available_slots(
        db, tenant_id=tenant_id, emergency=bool(emergency),
    )
    return ok({
        "slots": slots,
        # Echoed back so a caller can show the job's existing commitment as selected
        # rather than looking like nothing was ever agreed.
        "current": {
            "scheduled_date": job.scheduled_date.isoformat() if job.scheduled_date else None,
            "scheduled_time_window": job.scheduled_time_window,
        },
    }, _RID(r), "assignment")


@router.get("/{job_id}/weather-reschedule-eligibility", response_model=ApiResponse,
            summary="Whether weather is an available reason to move this job")
async def get_weather_reschedule_eligibility(
    job_id: uuid.UUID,
    scheduled_date:        date | None = None,
    scheduled_time_window: str | None  = None,
    r:      Request      = ...,
    user:   UserContext  = Depends(get_current_user),
    db:     AsyncSession = Depends(get_db),
):
    """Rescheduling for weather exists for TECHNICIAN SAFETY, so it is gated on a
    real reading rather than a claim: without a weather source, or without a reading
    for that slot's hour, weather is not an available reason. The provider can still
    move the job -- they give the actual reason instead, which is what keeps the
    record of why visits move worth reading.

    This is also the ONLY place a weather lookup is triggered by an ordinary screen,
    and it happens because a provider explicitly picked weather as the reason. Nothing
    a customer opens calls the weather API.

    `scheduled_date`/`scheduled_time_window` are the slot being considered. They
    default to the job's current slot, but the UI passes the target slot, because that
    is what POST /schedule enforces -- an eligibility answer about a different slot
    than the one being saved is how a provider gets told "yes" and then refused.
    """
    from app.engines.weather.place import resolve_place
    from app.engines.weather.scheduling import weather_reschedule_permitted
    from app.engines.weather.slots import slot_start
    tenant_id = uuid.UUID(user.tenant_id)
    svc = HomeServiceJobAssignmentService(db)
    job = await svc._load_job(job_id)
    if not job or str(job.tenant_id) != str(tenant_id):
        raise _fail(ERR_JOB_NOT_FOUND)
    verdict = await weather_reschedule_permitted(
        db, place=_job_place(job),
        slot_at=slot_start(
            scheduled_date or job.scheduled_date,
            scheduled_time_window or job.scheduled_time_window,
        ),
    )
    return ok(verdict, _RID(r), "assignment")


@router.post("/{job_id}/schedule", response_model=ApiResponse,
             summary="Schedule the job with a date and time window")
async def schedule_job(
    job_id: uuid.UUID,
    body:   ScheduleRequest,
    r:      Request      = ...,
    user:   UserContext  = Depends(require_tenant_owner_mutation),
    db:     AsyncSession = Depends(get_db),
):
    tenant_id = uuid.UUID(user.tenant_id)  # HS8 fix: was user_id, never matched any real job's tenant_id
    svc = HomeServiceJobAssignmentService(db)

    # A weather reason has to be backed by weather. Refused rather than silently
    # recorded, so the reschedule log never contains a cause nobody can check.
    if (body.reason or "").strip().lower() == "weather":
        from app.engines.weather.scheduling import weather_reschedule_permitted
        from app.engines.weather.slots import slot_start
        current = await svc._load_job(job_id)
        if not current or str(current.tenant_id) != str(tenant_id):
            raise _fail(ERR_JOB_NOT_FOUND)
        # Checked against the slot the job is being moved TO, not the one it is
        # leaving: the safety question is about the visit that will actually happen.
        verdict = await weather_reschedule_permitted(
            db, place=_job_place(current),
            slot_at=slot_start(body.scheduled_date, body.scheduled_time_window),
        )
        if not verdict["permitted"]:
            return ok(
                {"success": False, "error_code": "WEATHER_REASON_UNSUPPORTED",
                 "message": verdict["detail"], "weather": verdict},
                _RID(r), "assignment",
            )
    try:
        result = await svc.schedule_job(
            job_id=job_id, tenant_id=tenant_id,
            scheduled_date=body.scheduled_date,
            scheduled_time_window=body.scheduled_time_window,
            reason=(body.reason or "").strip() or None,
            actor_user_id=uuid.UUID(user.user_id), request_id=_RID(r),
        )
        await db.commit()
    except ValueError as exc:
        code = str(exc)
        raise _fail(code)
    return ok({"success": True, "data": result}, _RID(r), "assignment")


@router.get("/{job_id}/assignment-timeline", response_model=ApiResponse,
            summary="Get assignment event timeline for a job")
async def get_assignment_timeline(
    job_id: uuid.UUID,
    r:    Request      = ...,
    user: UserContext  = Depends(get_current_user),
    db:   AsyncSession = Depends(get_db),
):
    tenant_id = uuid.UUID(user.tenant_id)  # HS8 fix: was user_id, never matched any real job's tenant_id
    svc = HomeServiceJobAssignmentService(db)
    events = await svc.get_assignment_timeline(job_id, tenant_id)
    return ok({"job_id": str(job_id), "events": events}, _RID(r), "assignment")
