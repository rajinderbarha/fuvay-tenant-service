"""UX-05 — Tenant Home Services Availability & Capacity Planner (spec section 12).

Thin projection endpoints over the canonical resolver in
availability_resolver.py — no duplicate availability engine, no
frontend-side approximation of availability.
"""
from __future__ import annotations

import datetime as dt
import uuid

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import require_staff_or_above, UserContext
from app.dependencies.db import get_db
from app.core.permissions import require_tenant_owner_mutation
from app.exceptions import ServiceOSException
from app.schemas.base import ApiResponse, ok
from app.engines.home_service_assignment.availability_resolver import (
    resolve_tenant_week, resolve_staff_day, preview_staff_pattern_change,
)

router = APIRouter(prefix="/v1/tenant/home-services", tags=["Tenant Home Services — Availability Planner"])

_RID = lambda r: getattr(r.state, "request_id", "—")


def _tenant_id(user: UserContext) -> uuid.UUID:
    if not user.tenant_id:
        raise ServiceOSException("TENANT_CONTEXT_REQUIRED",
                                  "This workspace requires a tenant-scoped session.", status_code=403)
    return uuid.UUID(str(user.tenant_id))


@router.get("/availability", response_model=ApiResponse,
            summary="Canonical availability & capacity planner projection")
async def get_availability_planner(
    r: Request,
    date_from: str | None = Query(None, alias="from"),
    date_to: str | None = Query(None, alias="to"),
    staff_id: uuid.UUID | None = Query(None),
    user: UserContext = Depends(require_staff_or_above),
    db: AsyncSession = Depends(get_db),
):
    tid = _tenant_id(user)
    today = dt.date.today()
    try:
        d_from = dt.date.fromisoformat(date_from) if date_from else today
        d_to = dt.date.fromisoformat(date_to) if date_to else (d_from + dt.timedelta(days=6))
    except ValueError:
        raise ServiceOSException("INVALID_DATE_RANGE", "from/to must be ISO dates (YYYY-MM-DD).", status_code=422)
    if d_to < d_from:
        raise ServiceOSException("INVALID_DATE_RANGE", "'to' must not be before 'from'.", status_code=422)
    if (d_to - d_from).days > 31:
        raise ServiceOSException("DATE_RANGE_TOO_WIDE", "Range must be 31 days or fewer.", status_code=422)

    data = await resolve_tenant_week(db, tid, d_from, d_to, staff_id=staff_id)
    return ok(data, request_id=_RID(r))


@router.get("/availability/staff/{staff_id}", response_model=ApiResponse,
            summary="Canonical single-technician effective schedule for a date")
async def get_staff_availability(
    r: Request,
    staff_id: uuid.UUID,
    date: str | None = Query(None),
    user: UserContext = Depends(require_staff_or_above),
    db: AsyncSession = Depends(get_db),
):
    tid = _tenant_id(user)
    try:
        target = dt.date.fromisoformat(date) if date else dt.date.today()
    except ValueError:
        raise ServiceOSException("INVALID_DATE_RANGE", "date must be an ISO date (YYYY-MM-DD).", status_code=422)

    day = await resolve_staff_day(db, tid, staff_id, target)
    return ok(day, request_id=_RID(r))


class PreviewChangeRequest(BaseModel):
    staff_id: uuid.UUID
    day_of_week: int
    is_active: bool = True
    start_time: str | None = None
    end_time: str | None = None
    max_jobs_per_day: int | None = None


@router.post("/availability/preview-change", response_model=ApiResponse,
             summary="Impact preview for a proposed weekly-pattern/capacity change (spec sections 6/11)")
async def preview_availability_change(
    r: Request,
    body: PreviewChangeRequest,
    user: UserContext = Depends(require_tenant_owner_mutation),
    db: AsyncSession = Depends(get_db),
):
    """Never writes anything. Reuses the resolver's own real-assignment
    lookup (via preview_staff_pattern_change, which shares _fetch_assignments
    with resolve_staff_day — no separate conflict engine) to report how many
    REAL upcoming service_jobs rows for this technician would be affected by
    the proposed change, before the caller commits it."""
    tid = _tenant_id(user)
    if body.day_of_week < 0 or body.day_of_week > 6:
        raise ServiceOSException("INVALID_DAY_OF_WEEK", "day_of_week must be 0-6 (0=Sunday).", status_code=422)
    if body.max_jobs_per_day is not None and body.max_jobs_per_day < 0:
        raise ServiceOSException("INVALID_MAX_JOBS_PER_DAY", "max_jobs_per_day must not be negative.", status_code=422)

    preview = await preview_staff_pattern_change(
        db, tid, body.staff_id, body.day_of_week,
        proposed_is_active=body.is_active,
        proposed_max_jobs_per_day=body.max_jobs_per_day,
        proposed_start_time=body.start_time,
        proposed_end_time=body.end_time,
    )
    return ok(preview, request_id=_RID(r))
