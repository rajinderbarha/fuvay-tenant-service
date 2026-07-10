"""Sprint 20 — Admin Service Job Assignment Visibility APIs (read-only)."""
from __future__ import annotations
import uuid

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import get_current_user, UserContext
from app.dependencies.db import get_db
from app.schemas.base import ApiResponse, ok
from app.engines.home_service_assignment.models import (
    ServiceJobAssignment, ServiceJobAssignmentEvent,
)

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
