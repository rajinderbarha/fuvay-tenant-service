"""Technician Mobile App Phase S — Employment Details routes."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import require_staff_or_technician_only, UserContext
from app.dependencies.db import get_db
from app.dependencies.vertical_guard import require_tenant_vertical_active
from app.core.permissions import require_tenant_owner_mutation
from app.schemas.base import ok
from app.exceptions import ServiceOSException
from app.engines.home_service_assignment.mobile_employment_service import MobileEmploymentService

router = APIRouter(prefix="/v1/staff/me", tags=["Mobile Employment Details"])
tenant_router = APIRouter(prefix="/v1/tenant/home-services/staff-corrections", tags=["Employment Correction Review"])

_svc = MobileEmploymentService()


def _rid(request: Request) -> str:
    return request.headers.get("x-request-id", str(uuid.uuid4()))


@router.get("/employment-details")
async def get_employment_details(
    request: Request,
    user: UserContext = Depends(require_staff_or_technician_only),
    _vertical: UserContext = Depends(require_tenant_vertical_active("home_services")),
    db: AsyncSession = Depends(get_db),
):
    if not user.tenant_id:
        raise ServiceOSException("TENANT_REQUIRED", "No tenant context on this account.", status_code=403)
    data = await _svc.get_employment_details(db, uuid.UUID(user.user_id), uuid.UUID(user.tenant_id))
    return ok(data, request_id=_rid(request), engine_id="home_service_assignment")


@router.get("/employment-details/permissions")
async def get_permissions_summary(
    request: Request,
    user: UserContext = Depends(require_staff_or_technician_only),
    _vertical: UserContext = Depends(require_tenant_vertical_active("home_services")),
    db: AsyncSession = Depends(get_db),
):
    if not user.tenant_id:
        raise ServiceOSException("TENANT_REQUIRED", "No tenant context on this account.", status_code=403)
    data = await _svc.get_permissions_summary(db, uuid.UUID(user.user_id), uuid.UUID(user.tenant_id))
    return ok(data, request_id=_rid(request), engine_id="home_service_assignment")


@router.post("/employment-correction-requests")
async def submit_correction(
    body: dict, request: Request,
    user: UserContext = Depends(require_staff_or_technician_only),
    _vertical: UserContext = Depends(require_tenant_vertical_active("home_services")),
    db: AsyncSession = Depends(get_db),
):
    if not user.tenant_id:
        raise ServiceOSException("TENANT_REQUIRED", "No tenant context on this account.", status_code=403)
    field_key = (body or {}).get("field_key")
    requested_value = (body or {}).get("requested_value")
    reason = (body or {}).get("reason")
    if not field_key or not requested_value or not reason:
        raise ServiceOSException("VALIDATION_ERROR", "field_key, requested_value and reason are required.", status_code=400)
    data = await _svc.submit_correction(
        db, uuid.UUID(user.user_id), uuid.UUID(user.tenant_id),
        field_key=field_key, requested_value=requested_value, reason=reason,
    )
    return ok(data, request_id=_rid(request), engine_id="home_service_assignment")


@router.get("/employment-correction-requests")
async def list_my_corrections(
    request: Request,
    user: UserContext = Depends(require_staff_or_technician_only),
    db: AsyncSession = Depends(get_db),
):
    if not user.tenant_id:
        raise ServiceOSException("TENANT_REQUIRED", "No tenant context on this account.", status_code=403)
    data = await _svc.list_my_corrections(db, uuid.UUID(user.user_id), uuid.UUID(user.tenant_id))
    return ok({"requests": data}, request_id=_rid(request), engine_id="home_service_assignment")


def _decide(decision: str):
    async def _handler(
        request_id: uuid.UUID, body: dict, request: Request,
        user: UserContext = Depends(require_tenant_owner_mutation),
        db: AsyncSession = Depends(get_db),
    ):
        if not user.tenant_id:
            raise ServiceOSException("TENANT_REQUIRED", "No tenant context on this account.", status_code=403)
        data = await _svc.decide_correction(
            db, uuid.UUID(user.tenant_id), request_id,
            decision=decision, reviewer_user_id=uuid.UUID(user.user_id),
            reviewer_note=(body or {}).get("note"),
        )
        return ok(data, request_id=_rid(request), engine_id="home_service_assignment")
    return _handler


tenant_router.add_api_route("/{request_id}/approve", _decide("approve"), methods=["POST"])
tenant_router.add_api_route("/{request_id}/reject", _decide("reject"), methods=["POST"])
tenant_router.add_api_route("/{request_id}/request-changes", _decide("request_changes"), methods=["POST"])
