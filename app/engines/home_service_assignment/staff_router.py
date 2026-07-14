"""Sprint 20 — Staff / Technician Service Job APIs."""
from __future__ import annotations
import uuid

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import get_current_user, UserContext
from app.dependencies.db import get_db
from app.schemas.base import ApiResponse, ok
from app.engines.home_service_assignment.service import HomeServiceJobAssignmentService
from app.engines.home_service_assignment.constants import (
    ERR_JOB_NOT_FOUND, ERR_STAFF_JOB_NOT_ASSIGNED, ERR_STAFF_JOB_ALREADY_ACCEPTED,
    ERR_STAFF_JOB_ALREADY_REJECTED, ERR_REASON_REQUIRED, ERR_JOB_CANCELLED,
)


async def _resolve_staff_member_id(user: UserContext, db: AsyncSession) -> uuid.UUID:
    """HS8 fix: every handler in this router used `user.user_id` (the raw
    auth user id) directly as the staff_member_id to match against
    `ServiceJob.assigned_staff_id`, which actually stores
    `provider_team_members.id` — a different UUID. A real technician login
    (`staff@serviceos.in`) could never see any job assigned to them,
    despite `assign_job` (provider_router.py) correctly recording the
    assignment. Fixed by resolving the real team-member row via its
    `user_id` FK before using it as staff_id anywhere in this router."""
    from app.engines.home_service_assignment.staff_model import ProviderTeamMember
    res = await db.execute(
        select(ProviderTeamMember.id).where(
            ProviderTeamMember.user_id == uuid.UUID(user.user_id)
        )
    )
    row = res.scalars().first()
    if row:
        return row
    # FINAL-L5-05C reconciliation: the service layer (assign_job /
    # get_staff_assigned_jobs / technician_accept_job) was migrated to key staff
    # off `users.id` because `provider_team_members` is unpopulated in real/demo
    # data — assign_job stores `service_jobs.assigned_staff_id = users.id`. This
    # router, however, still translated the login through the empty
    # provider_team_members table, so a real technician could never see (empty
    # list) or act on (500 on accept) their own assigned job. Fall back to the
    # raw auth user id, which is exactly what the service layer now matches.
    return uuid.UUID(str(user.user_id))

router = APIRouter(
    prefix="/v1/staff/service-jobs",
    tags=["Staff Service Jobs"],
)

_RID = lambda r: getattr(r.state, "request_id", "—")

_MESSAGES = {
    ERR_JOB_NOT_FOUND:               "Job not found.",
    ERR_STAFF_JOB_NOT_ASSIGNED:      "This job is not assigned to you.",
    ERR_STAFF_JOB_ALREADY_ACCEPTED:  "You have already accepted this job.",
    ERR_STAFF_JOB_ALREADY_REJECTED:  "You have already rejected this job.",
    ERR_REASON_REQUIRED:             "Rejection reason is required.",
    ERR_JOB_CANCELLED:               "This job has been cancelled.",
}


def _err(code: str) -> dict:
    return {"success": False, "error": {"code": code, "message": _MESSAGES.get(code, "Action failed.")}}


class RejectRequest(BaseModel):
    reason: str


@router.get("", response_model=ApiResponse,
            summary="List service jobs assigned to me")
async def list_my_jobs(
    r:    Request      = ...,
    user: UserContext  = Depends(get_current_user),
    db:   AsyncSession = Depends(get_db),
):
    try:
        staff_id = await _resolve_staff_member_id(user, db)
    except ValueError:
        return ok({"jobs": [], "count": 0}, _RID(r), "assignment")
    svc = HomeServiceJobAssignmentService(db)
    jobs = await svc.get_staff_assigned_jobs(staff_id)
    return ok({"jobs": jobs, "count": len(jobs)}, _RID(r), "assignment")


@router.get("/{job_id}", response_model=ApiResponse,
            summary="Get detail of a job assigned to me")
async def get_my_job(
    job_id: uuid.UUID,
    r:    Request      = ...,
    user: UserContext  = Depends(get_current_user),
    db:   AsyncSession = Depends(get_db),
):
    staff_id = await _resolve_staff_member_id(user, db)
    svc = HomeServiceJobAssignmentService(db)
    try:
        detail = await svc.get_staff_job_detail(job_id, staff_id)
    except ValueError as exc:
        code = str(exc)
        return ok(_err(code), _RID(r), "assignment")
    return ok(detail, _RID(r), "assignment")


@router.post("/{job_id}/accept", response_model=ApiResponse,
             summary="Accept a job assigned to me")
async def accept_job(
    job_id: uuid.UUID,
    r:    Request      = ...,
    user: UserContext  = Depends(get_current_user),
    db:   AsyncSession = Depends(get_db),
):
    staff_id = await _resolve_staff_member_id(user, db)
    svc = HomeServiceJobAssignmentService(db)
    try:
        result = await svc.technician_accept_job(job_id, staff_id, _RID(r))
        await db.commit()
    except ValueError as exc:
        code = str(exc)
        return ok(_err(code), _RID(r), "assignment")
    return ok({"success": True, "data": result}, _RID(r), "assignment")


@router.post("/{job_id}/reject", response_model=ApiResponse,
             summary="Reject a job assigned to me (requires reason)")
async def reject_job(
    job_id: uuid.UUID,
    body:   RejectRequest,
    r:    Request      = ...,
    user: UserContext  = Depends(get_current_user),
    db:   AsyncSession = Depends(get_db),
):
    staff_id = await _resolve_staff_member_id(user, db)
    svc = HomeServiceJobAssignmentService(db)
    try:
        result = await svc.technician_reject_job(job_id, staff_id, body.reason, _RID(r))
        await db.commit()
    except ValueError as exc:
        code = str(exc)
        return ok(_err(code), _RID(r), "assignment")
    return ok({"success": True, "data": result}, _RID(r), "assignment")


@router.get("/{job_id}/assignment-timeline", response_model=ApiResponse,
            summary="Get assignment timeline for my assigned job")
async def get_my_job_timeline(
    job_id: uuid.UUID,
    r:    Request      = ...,
    user: UserContext  = Depends(get_current_user),
    db:   AsyncSession = Depends(get_db),
):
    staff_id = await _resolve_staff_member_id(user, db)
    svc = HomeServiceJobAssignmentService(db)
    # Verify access first
    try:
        await svc.get_staff_job_detail(job_id, staff_id)
    except ValueError as exc:
        code = str(exc)
        return ok(_err(code), _RID(r), "assignment")
    events = await svc.get_assignment_timeline(job_id)
    return ok({"job_id": str(job_id), "events": events}, _RID(r), "assignment")
