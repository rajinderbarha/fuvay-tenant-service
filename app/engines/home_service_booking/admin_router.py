"""Sprint 16 — Admin Home Service Booking Drafts API.

3 read-only endpoints at /v1/admin/home-services/booking-drafts/*.
Auth: admin JWT required.
"""
from __future__ import annotations
import uuid
from typing import Optional

import structlog
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import get_current_user, UserContext
from app.dependencies.db import get_db
from app.engines.home_service_booking.service import HomeServiceChatbotBookingService
from app.schemas.base import ApiResponse, ok

logger = structlog.get_logger("home_service.admin_router")

router = APIRouter(
    prefix="/v1/admin/home-services/booking-drafts",
    tags=["Admin Home Service Booking Drafts"],
)


def _svc(r: Request, db: AsyncSession = Depends(get_db)) -> HomeServiceChatbotBookingService:
    return HomeServiceChatbotBookingService(db=db, request_id=getattr(r.state, "request_id", "—"))


def _rid(r: Request) -> str:
    return getattr(r.state, "request_id", "—")


# ── GET /  — List all drafts ──────────────────────────────────────────────────
@router.get(
    "",
    response_model=ApiResponse[dict],
    summary="Admin: list all Home Service booking drafts",
    description="Paginated list of all booking drafts. Filter by status, city, offering.",
)
async def admin_list_drafts(
    r: Request,
    page:        int           = Query(1,  ge=1),
    page_size:   int           = Query(20, ge=1, le=100),
    status:      Optional[str] = Query(None, description="Filter by status"),
    city:        Optional[str] = Query(None, description="Filter by city (partial match)"),
    offering_id: Optional[str] = Query(None, description="Filter by offering UUID"),
    svc: HomeServiceChatbotBookingService = Depends(_svc),
    user: UserContext = Depends(get_current_user),
):
    result = await svc.admin_list_drafts(
        page=page, page_size=page_size,
        status=status, city=city, offering_id=offering_id,
    )
    return ok(result, _rid(r), "home_service_booking")


# ── GET /{draft_id}  — Get single draft ──────────────────────────────────────
@router.get(
    "/{draft_id}",
    response_model=ApiResponse[dict],
    summary="Admin: get a single booking draft",
    responses={
        200: {"description": "Draft details"},
        404: {"description": "Draft not found"},
    },
)
async def admin_get_draft(
    draft_id: uuid.UUID,
    r: Request,
    svc: HomeServiceChatbotBookingService = Depends(_svc),
    user: UserContext = Depends(get_current_user),
):
    result = await svc.admin_get_draft(draft_id=draft_id)
    return ok(result, _rid(r), "home_service_booking")


# ── GET /{draft_id}/events  — Get events ─────────────────────────────────────
@router.get(
    "/{draft_id}/events",
    response_model=ApiResponse[dict],
    summary="Admin: get all events for a booking draft",
    description="Immutable event log: serviceability checks, price estimates, confirmations.",
)
async def admin_get_draft_events(
    draft_id: uuid.UUID,
    r: Request,
    svc: HomeServiceChatbotBookingService = Depends(_svc),
    user: UserContext = Depends(get_current_user),
):
    events = await svc.admin_get_draft_events(draft_id=draft_id)
    return ok({"events": events, "total": len(events)}, _rid(r), "home_service_booking")
