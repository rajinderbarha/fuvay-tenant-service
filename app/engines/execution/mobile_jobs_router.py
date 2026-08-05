"""Technician Mobile App Phase I — GET /v1/staff/mobile-jobs.

See mobile_jobs_service.py for full derivation notes.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import require_staff_or_technician_only, UserContext
from app.dependencies.db import get_db
from app.schemas.base import ok
from app.exceptions import ServiceOSException
from app.engines.execution.mobile_jobs_service import TechnicianMobileJobsService, VALID_VIEWS

router = APIRouter(prefix="/v1/staff", tags=["Technician Mobile Jobs"])
_svc = TechnicianMobileJobsService()


def _rid(request: Request) -> str:
    return getattr(request.state, "request_id", "—")


@router.get("/mobile-jobs", summary="Technician mobile Jobs directory")
async def get_mobile_jobs(
    request: Request,
    view: str = Query("today", description="today|active|upcoming|completed|archive"),
    search: str | None = Query(None, max_length=100),
    workflow_status: str | None = Query(None),
    action_required: bool | None = Query(None),
    cursor: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    user: UserContext = Depends(require_staff_or_technician_only),
    db: AsyncSession = Depends(get_db),
):
    if not user.tenant_id:
        raise ServiceOSException("TENANT_CONTEXT_MISSING", "No tenant context on this account.", status_code=403)
    if view not in VALID_VIEWS:
        raise ServiceOSException("VALIDATION_ERROR", f"view must be one of {sorted(VALID_VIEWS)}.", status_code=422)

    data = await _svc.list_jobs(
        db, uuid.UUID(user.user_id), uuid.UUID(user.tenant_id),
        view=view, search=search, workflow_status=workflow_status,
        action_required=action_required, cursor=cursor, limit=limit,
    )
    return ok(data, _rid(request), "execution")
