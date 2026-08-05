"""Technician Mobile App Phase H — GET /v1/staff/mobile-home.

One purpose-built projection for the technician mobile Home screen. See
mobile_home_service.py for full derivation notes.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import get_current_user, require_staff_or_technician_only, UserContext
from app.dependencies.db import get_db
from app.schemas.base import ok
from app.exceptions import ServiceOSException
from app.engines.execution.mobile_home_service import TechnicianMobileHomeService
from app.engines.home_service_assignment.staff_model import ProviderTeamMember, AVAILABILITY_STATES

router = APIRouter(prefix="/v1/staff", tags=["Technician Mobile Home"])
_svc = TechnicianMobileHomeService()


def _rid(request: Request) -> str:
    return getattr(request.state, "request_id", "—")


@router.get("/mobile-home", summary="Technician mobile Home projection")
async def get_mobile_home(
    request: Request,
    user: UserContext = Depends(require_staff_or_technician_only),
    db: AsyncSession = Depends(get_db),
):
    if not user.tenant_id:
        raise ServiceOSException("TENANT_CONTEXT_MISSING", "No tenant context on this account.", status_code=403)
    data = await _svc.get_home(db, uuid.UUID(user.user_id), uuid.UUID(user.tenant_id))
    return ok(data, _rid(request), "execution")


class UpdateAvailabilityRequest(BaseModel):
    state: str = Field(..., description="available | busy | offline")


@router.put("/me/availability", summary="Set technician's own availability state")
async def update_availability(
    body: UpdateAvailabilityRequest,
    request: Request,
    user: UserContext = Depends(require_staff_or_technician_only),
    db: AsyncSession = Depends(get_db),
):
    """Self-service presence state (migration 209) -- distinct from
    `can_receive_assignment` (tenant-controlled eligibility, untouched here)
    and from `status` (tenant-controlled active/inactive membership).
    Never abandons existing assigned jobs -- it only affects eligibility
    for FUTURE assignment matching, enforced entirely server-side."""
    if body.state not in AVAILABILITY_STATES:
        raise ServiceOSException(
            "VALIDATION_ERROR", f"state must be one of {AVAILABILITY_STATES}.", status_code=422,
        )

    from sqlalchemy import select
    res = await db.execute(select(ProviderTeamMember).where(ProviderTeamMember.user_id == uuid.UUID(user.user_id)))
    member = res.scalars().first()
    if not member:
        raise ServiceOSException("NOT_FOUND", "Technician profile not found.", status_code=404)

    member.availability_state = body.state
    member.availability_updated_at = datetime.now(timezone.utc)
    await db.commit()

    return ok(
        {"state": member.availability_state, "updated_at": member.availability_updated_at.isoformat()},
        _rid(request), "execution",
    )
