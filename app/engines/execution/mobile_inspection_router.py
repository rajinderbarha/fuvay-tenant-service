"""Technician Mobile App Phase K — Inspection & Diagnosis projection route.

Read-only. Mutations reuse the existing checklist_catalog staff endpoints
and the existing complete-inspection workflow endpoint -- see
mobile_inspection_service.py docstring.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import require_staff_or_technician_only, UserContext
from app.dependencies.db import get_db
from app.schemas.base import ok
from app.exceptions import ServiceOSException
from app.engines.execution.mobile_inspection_service import MobileInspectionService

router = APIRouter(prefix="/v1/staff", tags=["Technician Mobile Inspection"])
_svc = MobileInspectionService()


def _rid(r: Request) -> str:
    return getattr(r.state, "request_id", "—")


@router.get("/service-jobs/{job_id}/mobile-inspection")
async def get_mobile_inspection_detail(
    job_id: uuid.UUID, request: Request,
    user: UserContext = Depends(require_staff_or_technician_only),
    db: AsyncSession = Depends(get_db),
):
    if not user.tenant_id:
        raise ServiceOSException("TENANT_CONTEXT_MISSING", "No active tenant context.", status_code=403)
    data = await _svc.get_detail(db, uuid.UUID(user.user_id), uuid.UUID(user.tenant_id), job_id)
    await db.commit()
    return ok(data, _rid(request), "execution")
