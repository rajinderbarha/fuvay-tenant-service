"""Tenant-facing Home Services operational dashboard.

Access requires the exact Home Services vertical enrollment to be 'active'
(require_tenant_vertical_active) -- approved-pending-activation is not
enough, matching the same guard already proven for the operational
provider_portal endpoints this dashboard aggregates.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import UserContext
from app.dependencies.db import get_db
from app.dependencies.vertical_guard import require_tenant_vertical_active
from app.schemas.base import ok
from app.engines.execution.home_services_dashboard_service import get_dashboard, get_jobs_list, get_job_detail

router = APIRouter(prefix="/v1/tenant/home-services", tags=["Tenant Home Services Dashboard"])


@router.get("/dashboard")
async def get_dashboard_endpoint(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_tenant_vertical_active("home_services")),
):
    if not user.tenant_id:
        raise HTTPException(403, "No tenant context")
    rid = (getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID", "—"))
    data = await get_dashboard(db, uuid.UUID(user.tenant_id))
    return ok(data, request_id=rid)


@router.get("/jobs")
async def get_jobs_list_endpoint(
    request: Request,
    group: str | None = Query(None),
    search: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_tenant_vertical_active("home_services")),
):
    if not user.tenant_id:
        raise HTTPException(403, "No tenant context")
    rid = (getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID", "—"))
    data = await get_jobs_list(db, uuid.UUID(user.tenant_id), group=group, search=search, limit=limit, offset=offset)
    return ok(data, request_id=rid)


@router.get("/jobs/{job_id}")
async def get_job_detail_endpoint(
    job_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_tenant_vertical_active("home_services")),
):
    if not user.tenant_id:
        raise HTTPException(403, "No tenant context")
    rid = (getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID", "—"))
    data = await get_job_detail(db, uuid.UUID(user.tenant_id), job_id)
    if not data:
        raise HTTPException(404, "Job not found")
    return ok(data, request_id=rid)
