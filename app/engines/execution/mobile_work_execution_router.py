"""Technician Mobile App Phase M — Work Execution routes.

Projection + work-session bookkeeping only. Checklist answers reuse the
EXISTING checklist_catalog staff endpoints (save-response/complete)
directly from the mobile client; part requests reuse the EXISTING
POST /v1/staff/service-jobs/{job_id}/parts-requests endpoint directly
(already technician-authorized via require_staff_or_above_mutation +
in-service assignment check) -- neither is duplicated here.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import require_staff_or_technician_only, UserContext
from app.dependencies.db import get_db
from app.schemas.base import ok
from app.exceptions import ServiceOSException
from app.engines.execution.mobile_work_execution_service import MobileWorkExecutionService

router = APIRouter(prefix="/v1/staff/service-jobs", tags=["Technician Mobile Work Execution"])
_svc = MobileWorkExecutionService()


def _rid(r: Request) -> str:
    return getattr(r.state, "request_id", "—")


def _require_tenant(user: UserContext) -> None:
    if not user.tenant_id:
        raise ServiceOSException("TENANT_CONTEXT_MISSING", "No active tenant context.", status_code=403)


@router.get("/{job_id}/mobile-work-execution")
async def get_mobile_work_execution(job_id: uuid.UUID, request: Request, user: UserContext = Depends(require_staff_or_technician_only), db: AsyncSession = Depends(get_db)):
    _require_tenant(user)
    data = await _svc.get_detail(db, uuid.UUID(user.user_id), uuid.UUID(user.tenant_id), job_id)
    await db.commit()
    return ok(data, _rid(request), "execution")


@router.post("/{job_id}/mobile-work-execution/start")
async def start_mobile_work(job_id: uuid.UUID, request: Request, user: UserContext = Depends(require_staff_or_technician_only), db: AsyncSession = Depends(get_db)):
    _require_tenant(user)
    data = await _svc.start_work(db, uuid.UUID(user.user_id), uuid.UUID(user.tenant_id), job_id, _rid(request))
    return ok(data, _rid(request), "execution")


@router.post("/{job_id}/mobile-work-execution/pause")
async def pause_mobile_work(job_id: uuid.UUID, body: dict, request: Request, user: UserContext = Depends(require_staff_or_technician_only), db: AsyncSession = Depends(get_db)):
    _require_tenant(user)
    data = await _svc.pause_work(db, uuid.UUID(user.user_id), uuid.UUID(user.tenant_id), job_id, body.get("reason"))
    return ok(data, _rid(request), "execution")


@router.post("/{job_id}/mobile-work-execution/resume")
async def resume_mobile_work(job_id: uuid.UUID, request: Request, user: UserContext = Depends(require_staff_or_technician_only), db: AsyncSession = Depends(get_db)):
    _require_tenant(user)
    data = await _svc.resume_work(db, uuid.UUID(user.user_id), uuid.UUID(user.tenant_id), job_id)
    return ok(data, _rid(request), "execution")


@router.post("/{job_id}/mobile-work-execution/finish")
async def finish_mobile_work(job_id: uuid.UUID, request: Request, user: UserContext = Depends(require_staff_or_technician_only), db: AsyncSession = Depends(get_db)):
    _require_tenant(user)
    data = await _svc.finish_work(db, uuid.UUID(user.user_id), uuid.UUID(user.tenant_id), job_id, _rid(request))
    return ok(data, _rid(request), "execution")
