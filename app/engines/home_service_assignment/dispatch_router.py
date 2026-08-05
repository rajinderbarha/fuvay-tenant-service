"""Home Services Dispatch Board — tenant-facing read projection.

Mutations (assign/reassign/unassign/schedule) are NOT duplicated here --
the canonical routes already exist at
app.engines.home_service_assignment.provider_router (/v1/provider/service-jobs/...)
and the frontend calls those directly. This router only adds the two new
READ projections the Dispatch Board needs (day/week summary + per-job
assignment options with excluded-technician reason codes), gated on the
tenant's Home Services enrollment being active -- the mutation routes are
gated by require_tenant_owner_mutation already but NOT by vertical-active,
which is a pre-existing gap on those shared routes (see final report)."""
from __future__ import annotations

import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import UserContext
from app.dependencies.db import get_db
from app.dependencies.vertical_guard import require_tenant_vertical_active
from app.schemas.base import ApiResponse, ok
from app.exceptions import ServiceOSException
from app.engines.home_service_assignment.dispatch_service import HomeServiceDispatchProjectionService

router = APIRouter(prefix="/v1/tenant/home-services", tags=["Home Services Dispatch"])

_RID = lambda r: getattr(r.state, "request_id", "—")


@router.get("/dispatch", response_model=ApiResponse, summary="Dispatch Board day/week projection")
async def get_dispatch_board(
    r: Request,
    date_: date = Query(date.today(), alias="date"),
    view: str = Query("day"),
    user: UserContext = Depends(require_tenant_vertical_active("home_services")),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = uuid.UUID(user.tenant_id)
    svc = HomeServiceDispatchProjectionService(db)
    data = await svc.get_dispatch_projection(tenant_id, date_)
    return ok(data, _RID(r), "assignment")


@router.get("/jobs/{job_id}/assignment-options", response_model=ApiResponse,
            summary="Eligible/excluded technicians for one job")
async def get_assignment_options(
    job_id: uuid.UUID,
    r: Request,
    user: UserContext = Depends(require_tenant_vertical_active("home_services")),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = uuid.UUID(user.tenant_id)
    svc = HomeServiceDispatchProjectionService(db)
    try:
        data = await svc.get_assignment_options(tenant_id, job_id)
    except ValueError as exc:
        raise ServiceOSException(error_code=str(exc), detail="Job not found or not accessible.", status_code=404)
    return ok(data, _RID(r), "assignment")
