"""Sprint 20 — Admin Service Job Assignment Visibility APIs (read-only).

FINAL-L5-05C: added the admin-facing reassignment mutation (Part 4). Reuses
HomeServiceJobAssignmentService.reassign_job (already tenant-checked,
staff-eligibility-checked, history-preserving, event-emitting) rather than
duplicating that logic here.
"""
from __future__ import annotations
import uuid

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import record_platform_audit
from app.core.permissions import P, require_permission
from app.dependencies.auth import get_current_user, require_super_admin, UserContext
from app.dependencies.db import get_db
from app.exceptions import ServiceOSException
from app.schemas.base import ApiResponse, ok
from app.engines.home_service_assignment.constants import (
    ERR_JOB_NOT_FOUND, ERR_JOB_CANCELLED, ERR_JOB_COMPLETED, ERR_ACCESS_DENIED,
    ERR_STAFF_NOT_FOUND, ERR_STAFF_WRONG_TENANT, ERR_STAFF_INACTIVE,
    ERR_ROLE_NOT_ALLOWED, ERR_STAFF_NOT_ELIGIBLE, ERR_REASON_REQUIRED,
    ERR_REASSIGN_NOT_ALLOWED,
)
from app.engines.home_service_assignment.models import (
    ServiceJobAssignment, ServiceJobAssignmentEvent,
)
from app.engines.home_service_assignment.service import HomeServiceJobAssignmentService

router = APIRouter(
    prefix="/v1/admin/service-job-assignments",
    tags=["Admin Service Job Assignments"],
)

_RID = lambda r: getattr(r.state, "request_id", "—")


@router.get("", response_model=ApiResponse,
            summary="List all service job assignments with optional filters")
async def list_assignments(
    tenant_id:         uuid.UUID | None = None,
    staff_member_id:   uuid.UUID | None = None,
    assignment_status: str | None       = None,
    limit:  int = 50,
    offset: int = 0,
    r:    Request      = ...,
    user: UserContext  = Depends(get_current_user),
    db:   AsyncSession = Depends(get_db),
):
    q = select(ServiceJobAssignment)
    if tenant_id:
        q = q.where(ServiceJobAssignment.tenant_id == tenant_id)
    if staff_member_id:
        q = q.where(ServiceJobAssignment.assigned_staff_member_id == staff_member_id)
    if assignment_status:
        q = q.where(ServiceJobAssignment.assignment_status == assignment_status)
    q = q.order_by(ServiceJobAssignment.created_at.desc()).limit(limit).offset(offset)
    res = await db.execute(q)
    rows = [a.to_dict() for a in res.scalars().all()]
    return ok({"assignments": rows, "count": len(rows)}, _RID(r), "assignment")


@router.get("/unassigned", response_model=ApiResponse,
            summary="List service jobs with no current active assignment")
async def list_unassigned_jobs(
    tenant_id:   uuid.UUID | None = None,
    limit:  int = 50,
    offset: int = 0,
    r:    Request      = ...,
    user: UserContext  = Depends(get_current_user),
    db:   AsyncSession = Depends(get_db),
):
    from app.engines.final_records.models import ServiceJob
    q = select(ServiceJob).where(ServiceJob.assignment_status == "unassigned")
    if tenant_id:
        q = q.where(ServiceJob.tenant_id == tenant_id)
    q = q.order_by(ServiceJob.created_at.desc()).limit(limit).offset(offset)
    res = await db.execute(q)
    rows = [j.to_dict() for j in res.scalars().all()]
    return ok({"jobs": rows, "count": len(rows)}, _RID(r), "assignment")


@router.get("/assigned", response_model=ApiResponse,
            summary="List service jobs that are currently assigned")
async def list_assigned_jobs(
    tenant_id:   uuid.UUID | None = None,
    limit:  int = 50,
    offset: int = 0,
    r:    Request      = ...,
    user: UserContext  = Depends(get_current_user),
    db:   AsyncSession = Depends(get_db),
):
    from app.engines.final_records.models import ServiceJob
    q = select(ServiceJob).where(
        ServiceJob.assignment_status.in_(["assigned", "accepted", "scheduled"])
    )
    if tenant_id:
        q = q.where(ServiceJob.tenant_id == tenant_id)
    q = q.order_by(ServiceJob.created_at.desc()).limit(limit).offset(offset)
    res = await db.execute(q)
    rows = [j.to_dict() for j in res.scalars().all()]
    return ok({"jobs": rows, "count": len(rows)}, _RID(r), "assignment")


@router.get("/{assignment_id}", response_model=ApiResponse,
            summary="Get a specific assignment record")
async def get_assignment(
    assignment_id: uuid.UUID,
    r:    Request      = ...,
    user: UserContext  = Depends(get_current_user),
    db:   AsyncSession = Depends(get_db),
):
    res = await db.execute(
        select(ServiceJobAssignment).where(ServiceJobAssignment.id == assignment_id)
    )
    a = res.scalars().first()
    if not a:
        return ok({"success": False, "error": {"code": "JOB_ASSIGNMENT_NOT_FOUND",
                   "message": "Assignment not found."}}, _RID(r), "assignment")
    return ok(a.to_dict(), _RID(r), "assignment")


# ── Admin job timeline endpoint (different prefix) ────────────────────────────

admin_jobs_router = APIRouter(
    prefix="/v1/admin/service-jobs",
    tags=["Admin Service Job Assignments"],
)


@admin_jobs_router.get("/{job_id}/assignment-timeline", response_model=ApiResponse,
                       summary="Get full assignment event timeline for a job")
async def admin_get_timeline(
    job_id: uuid.UUID,
    r:    Request      = ...,
    user: UserContext  = Depends(get_current_user),
    db:   AsyncSession = Depends(get_db),
):
    res = await db.execute(
        select(ServiceJobAssignmentEvent)
        .where(ServiceJobAssignmentEvent.job_id == job_id)
        .order_by(ServiceJobAssignmentEvent.created_at)
    )
    events = [e.to_dict() for e in res.scalars().all()]
    return ok({"job_id": str(job_id), "events": events}, _RID(r), "assignment")


# ── FINAL-L5-05C Part 4: admin reassignment mutation ──────────────────────────

class AdminReassignJobRequest(BaseModel):
    technician_id: uuid.UUID
    reason: str = Field(..., min_length=1)


_REASSIGN_ERROR_MAP: dict[str, tuple[int, str]] = {
    ERR_JOB_NOT_FOUND:        (404, "JOB_NOT_FOUND"),
    ERR_JOB_CANCELLED:        (409, "JOB_REASSIGN_NOT_ALLOWED"),
    ERR_JOB_COMPLETED:        (409, "JOB_REASSIGN_NOT_ALLOWED"),
    ERR_ACCESS_DENIED:        (403, "JOB_REASSIGN_FORBIDDEN"),
    ERR_STAFF_NOT_FOUND:      (422, "TECHNICIAN_NOT_ELIGIBLE"),
    ERR_STAFF_WRONG_TENANT:   (409, "TECHNICIAN_TENANT_MISMATCH"),
    ERR_STAFF_INACTIVE:       (422, "TECHNICIAN_NOT_ELIGIBLE"),
    ERR_ROLE_NOT_ALLOWED:     (422, "TECHNICIAN_NOT_ELIGIBLE"),
    ERR_STAFF_NOT_ELIGIBLE:   (422, "TECHNICIAN_NOT_ELIGIBLE"),
    ERR_REASON_REQUIRED:      (422, "REASON_REQUIRED"),
    ERR_REASSIGN_NOT_ALLOWED: (409, "JOB_REASSIGN_NOT_ALLOWED"),
}


@admin_jobs_router.get("/{job_id}/eligible-technicians", response_model=ApiResponse,
                       summary="Admin: list real, active technicians eligible to be assigned to this job's tenant")
async def admin_list_eligible_technicians(
    job_id: uuid.UUID,
    r:    Request      = ...,
    user: UserContext  = Depends(require_permission(P.ADMIN_JOBS_READ)),
    db:   AsyncSession = Depends(get_db),
):
    """Reads real technician users (role='technician'/'staff', is_active) scoped
    to the job's own tenant. Deliberately queries User rather than
    ProviderTeamMember -- see the L5-05C-001 fix in service.py for why."""
    from app.engines.final_records.models import ServiceJob
    from app.engines.auth.models import User

    job_row = (await db.execute(select(ServiceJob).where(ServiceJob.id == job_id))).scalars().first()
    if not job_row:
        raise ServiceOSException(error_code="JOB_NOT_FOUND", detail="Service job not found.",
                                  status_code=404)

    res = await db.execute(
        select(User).where(
            and_(User.tenant_id == job_row.tenant_id, User.role.in_(["technician", "staff"]),
                 User.is_active == True)
        )
    )
    technicians = [{"id": str(u.id), "full_name": u.full_name, "role": u.role} for u in res.scalars().all()]
    return ok({"job_id": str(job_id), "technicians": technicians}, _RID(r), "assignment")


@admin_jobs_router.post("/{job_id}/reassign", response_model=ApiResponse,
                        summary="Admin: reassign a service job to a different technician")
async def admin_reassign_job(
    job_id: uuid.UUID,
    body: AdminReassignJobRequest,
    r:    Request      = ...,
    user: UserContext  = Depends(require_permission(P.ADMIN_JOBS_REASSIGN)),
    db:   AsyncSession = Depends(get_db),
):
    from app.engines.final_records.models import ServiceJob

    job_row = (await db.execute(select(ServiceJob).where(ServiceJob.id == job_id))).scalars().first()
    if not job_row:
        raise ServiceOSException(error_code="JOB_NOT_FOUND", detail="Service job not found.",
                                  status_code=404)

    before_state = {"assigned_staff_id": str(job_row.assigned_staff_id) if job_row.assigned_staff_id else None,
                     "status": job_row.status, "assignment_status": job_row.assignment_status}

    svc = HomeServiceJobAssignmentService(db)
    try:
        result = await svc.reassign_job(
            job_id=job_id,
            staff_member_id=body.technician_id,
            tenant_id=job_row.tenant_id,
            reason=body.reason,
            actor_user_id=uuid.UUID(user.user_id) if user.user_id else None,
            request_id=_RID(r),
        )
    except ValueError as e:
        status_code, error_code = _REASSIGN_ERROR_MAP.get(str(e), (400, str(e)))
        raise ServiceOSException(error_code=error_code, detail=str(e), status_code=status_code)

    await record_platform_audit(
        db, operation="service_job.reassigned", engine_id="home_service_assignment",
        entity_id=str(job_id), entity_type="service_job", tenant_id=job_row.tenant_id,
        actor_id=uuid.UUID(user.user_id) if user.user_id else None, actor_role=user.role,
        request_id=_RID(r), before=before_state,
        after={"assigned_staff_id": str(body.technician_id), "reason": body.reason,
               "status": result.get("status"), "assignment_status": result.get("assignment_status")},
    )
    await db.commit()

    return ok(result, _RID(r), "assignment")
