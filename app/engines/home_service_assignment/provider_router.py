"""Sprint 20 — Provider Service Job Assignment APIs."""
from __future__ import annotations
import uuid
from datetime import date

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import require_tenant_owner_mutation
from app.dependencies.auth import get_current_user, UserContext
from app.dependencies.db import get_db
from app.schemas.base import ApiResponse, ok
from app.engines.home_service_assignment.service import HomeServiceJobAssignmentService
from app.engines.home_service_assignment.constants import (
    ERR_JOB_NOT_FOUND, ERR_ACCESS_DENIED, ERR_STAFF_NOT_FOUND,
    ERR_STAFF_WRONG_TENANT, ERR_STAFF_INACTIVE, ERR_ROLE_NOT_ALLOWED,
    ERR_STAFF_NOT_ELIGIBLE, ERR_REASSIGN_NOT_ALLOWED, ERR_CANCEL_NOT_ALLOWED,
    ERR_INVALID_STATUS, ERR_REASON_REQUIRED, ERR_JOB_CANCELLED, ERR_JOB_COMPLETED,
    ERR_ASSIGNMENT_NOT_FOUND,
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
}


def _err(code: str) -> dict:
    return {"success": False, "error": {"code": code, "message": _MESSAGES.get(code, "Action failed.")}}


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
        return ok(_err(code), _RID(r), "assignment")
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
        return ok(_err(code), _RID(r), "assignment")
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
        return ok(_err(code), _RID(r), "assignment")
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
        return ok(_err(code), _RID(r), "assignment")
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
        return ok(_err(code), _RID(r), "assignment")
    return ok({"success": True, "data": result}, _RID(r), "assignment")


@router.get("/{job_id}/weather-reschedule-eligibility", response_model=ApiResponse,
            summary="Whether weather is an available reason to move this job")
async def get_weather_reschedule_eligibility(
    job_id: uuid.UUID,
    r:      Request      = ...,
    user:   UserContext  = Depends(get_current_user),
    db:     AsyncSession = Depends(get_db),
):
    """Rescheduling for weather exists for TECHNICIAN SAFETY, so it is gated on a
    real reading rather than a claim: without a weather source, or without a reading
    for that slot's hour, weather is not an available reason. The provider can still
    move the job -- they give the actual reason instead, which is what keeps the
    record of why visits move worth reading.
    """
    from app.engines.weather.scheduling import weather_reschedule_permitted
    from app.engines.weather.slots import slot_start
    tenant_id = uuid.UUID(user.tenant_id)
    svc = HomeServiceJobAssignmentService(db)
    job = await svc._load_job(job_id)
    if not job or str(job.tenant_id) != str(tenant_id):
        return ok(_err("JOB_NOT_FOUND"), _RID(r), "assignment")
    verdict = await weather_reschedule_permitted(
        db, place=job.zipcode,
        slot_at=slot_start(job.scheduled_date, job.scheduled_time_window),
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
            return ok(_err("JOB_NOT_FOUND"), _RID(r), "assignment")
        # Checked against the slot the job is being moved TO, not the one it is
        # leaving: the safety question is about the visit that will actually happen.
        verdict = await weather_reschedule_permitted(
            db, place=current.zipcode,
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
            actor_user_id=uuid.UUID(user.user_id), request_id=_RID(r),
        )
        await db.commit()
    except ValueError as exc:
        code = str(exc)
        return ok(_err(code), _RID(r), "assignment")
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
