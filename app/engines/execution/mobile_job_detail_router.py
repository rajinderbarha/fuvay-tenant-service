"""Technician Mobile App Phase J — Job Detail / Execution Command Center.

GET /v1/staff/service-jobs/{job_id}/mobile-detail
GET /v1/staff/service-jobs/{job_id}/mobile-timeline

See mobile_job_detail_service.py for full derivation notes. Mutations
(start travel / mark arrived) are NOT duplicated here -- the mobile client
calls the existing, real execution endpoints
(POST /v1/staff/service-jobs/{job_id}/on-the-way, /reached-site) directly,
per spec section 8 ("do not invent new mutation endpoints").
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import require_staff_or_technician_only, UserContext
from app.dependencies.db import get_db
from app.schemas.base import ok
from app.exceptions import ServiceOSException
from app.engines.execution.mobile_job_detail_service import TechnicianJobDetailService

router = APIRouter(prefix="/v1/staff", tags=["Technician Mobile Job Detail"])
_svc = TechnicianJobDetailService()


def _rid(request: Request) -> str:
    return getattr(request.state, "request_id", "—")


@router.get("/service-jobs/{job_id}/mobile-detail", summary="Technician mobile Job Detail command-center projection")
async def get_mobile_job_detail(
    job_id: uuid.UUID,
    request: Request,
    user: UserContext = Depends(require_staff_or_technician_only),
    db: AsyncSession = Depends(get_db),
):
    if not user.tenant_id:
        raise ServiceOSException("TENANT_CONTEXT_MISSING", "No tenant context on this account.", status_code=403)
    data = await _svc.get_detail(db, uuid.UUID(user.user_id), uuid.UUID(user.tenant_id), job_id)
    return ok(data, _rid(request), "execution")


@router.get("/service-jobs/{job_id}/mobile-timeline", summary="Technician mobile Job Detail read-only timeline")
async def get_mobile_job_timeline(
    job_id: uuid.UUID,
    request: Request,
    user: UserContext = Depends(require_staff_or_technician_only),
    db: AsyncSession = Depends(get_db),
):
    if not user.tenant_id:
        raise ServiceOSException("TENANT_CONTEXT_MISSING", "No tenant context on this account.", status_code=403)
    data = await _svc.get_timeline(db, uuid.UUID(user.user_id), uuid.UUID(user.tenant_id), job_id)
    return ok(data, _rid(request), "execution")
