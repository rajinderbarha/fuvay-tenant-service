"""Sprint 17 — Admin Coaching Appointment Draft API (4 read-only endpoints)."""
from __future__ import annotations
import uuid

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import require_super_admin, UserContext
from app.dependencies.db import get_db
from app.schemas.base import ApiResponse, ok
from app.engines.coaching_appointment.service import CoachingAppointmentFlowService

router = APIRouter(
    prefix="/v1/admin/coaching",
    tags=["Admin Coaching Appointment Drafts"],
)


def _rid(r: Request) -> str:
    return getattr(r.state, "request_id", "—")


@router.get("/appointment-drafts", response_model=ApiResponse)
async def admin_list_drafts(
    r: Request,
    status:    str | None = Query(None),
    city:      str | None = Query(None),
    page:      int        = Query(1, ge=1),
    page_size: int        = Query(25, ge=1, le=100),
    user: UserContext = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    svc    = CoachingAppointmentFlowService(db, _rid(r))
    result = await svc.admin_list_drafts(status=status, city=city, page=page, page_size=page_size)
    return ok(result, _rid(r), "coaching_appointment")


@router.get("/appointment-drafts/{draft_id}", response_model=ApiResponse)
async def admin_get_draft(
    draft_id: uuid.UUID,
    r: Request,
    user: UserContext = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    svc    = CoachingAppointmentFlowService(db, _rid(r))
    result = await svc.admin_get_draft(draft_id)
    return ok(result, _rid(r), "coaching_appointment")


@router.get("/appointment-drafts/{draft_id}/events", response_model=ApiResponse)
async def admin_get_draft_events(
    draft_id: uuid.UUID,
    r: Request,
    user: UserContext = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    svc    = CoachingAppointmentFlowService(db, _rid(r))
    result = await svc.admin_get_draft_events(draft_id)
    return ok(result, _rid(r), "coaching_appointment")


@router.get("/appointment-slot-holds", response_model=ApiResponse)
async def admin_list_slot_holds(
    r: Request,
    status:    str | None = Query(None),
    page:      int        = Query(1, ge=1),
    page_size: int        = Query(25, ge=1, le=100),
    user: UserContext = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    svc    = CoachingAppointmentFlowService(db, _rid(r))
    result = await svc.admin_list_slot_holds(status=status, page=page, page_size=page_size)
    return ok(result, _rid(r), "coaching_appointment")
