"""Technician Mobile App Phase P — Schedule & Availability routes.

Staff-facing (technician self-service) endpoints under `/v1/staff/me/`, plus
a minimal tenant-owner approve/reject pair for time-off decisions -- the
technician can never approve their own request (spec section 6).
"""
from __future__ import annotations

import datetime as dt
import uuid

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import require_staff_or_technician_only, UserContext
from app.dependencies.db import get_db
from app.core.permissions import require_tenant_owner_mutation
from app.schemas.base import ok
from app.exceptions import ServiceOSException
from app.engines.home_service_assignment.mobile_schedule_service import MobileScheduleService

router = APIRouter(prefix="/v1/staff/me", tags=["Technician Mobile Schedule"])
tenant_router = APIRouter(prefix="/v1/tenant/home-services/time-off", tags=["Tenant Time Off Decisions"])
_svc = MobileScheduleService()


def _rid(r: Request) -> str:
    return getattr(r.state, "request_id", "—")


def _require_tenant(user: UserContext) -> None:
    if not user.tenant_id:
        raise ServiceOSException("TENANT_CONTEXT_MISSING", "No active tenant context.", status_code=403)


def _parse_time(value: str, field: str) -> dt.time:
    try:
        return dt.time.fromisoformat(value)
    except ValueError:
        raise ServiceOSException("VALIDATION_ERROR", f"'{field}' must be HH:MM.", status_code=422)


@router.get("/schedule")
async def get_mobile_schedule(
    request: Request,
    date_from: str = Query(..., alias="from"), date_to: str = Query(..., alias="to"),
    user: UserContext = Depends(require_staff_or_technician_only), db: AsyncSession = Depends(get_db),
):
    _require_tenant(user)
    try:
        f = dt.date.fromisoformat(date_from)
        t = dt.date.fromisoformat(date_to)
    except ValueError:
        raise ServiceOSException("VALIDATION_ERROR", "from/to must be YYYY-MM-DD.", status_code=422)
    data = await _svc.get_schedule(db, uuid.UUID(user.user_id), uuid.UUID(user.tenant_id), f, t)
    return ok(data, _rid(request), "home_service_assignment")


@router.post("/schedule/blocked-time")
async def create_mobile_blocked_time(body: dict, request: Request, user: UserContext = Depends(require_staff_or_technician_only), db: AsyncSession = Depends(get_db)):
    _require_tenant(user)
    data = await _svc.create_blocked_time(
        db, uuid.UUID(user.user_id), uuid.UUID(user.tenant_id),
        block_date=dt.date.fromisoformat(body["date"]),
        start_time=_parse_time(body["start_time"], "start_time"),
        end_time=_parse_time(body["end_time"], "end_time"),
        reason=body.get("reason"),
    )
    return ok(data, _rid(request), "home_service_assignment")


@router.delete("/schedule/blocked-time/{block_id}")
async def remove_mobile_blocked_time(block_id: uuid.UUID, request: Request, user: UserContext = Depends(require_staff_or_technician_only), db: AsyncSession = Depends(get_db)):
    _require_tenant(user)
    data = await _svc.remove_blocked_time(db, uuid.UUID(user.user_id), uuid.UUID(user.tenant_id), block_id)
    return ok(data, _rid(request), "home_service_assignment")


@router.get("/time-off")
async def list_mobile_time_off(request: Request, user: UserContext = Depends(require_staff_or_technician_only), db: AsyncSession = Depends(get_db)):
    _require_tenant(user)
    data = await _svc.list_time_off(db, uuid.UUID(user.user_id), uuid.UUID(user.tenant_id))
    return ok(data, _rid(request), "home_service_assignment")


@router.post("/time-off")
async def submit_mobile_time_off(body: dict, request: Request, user: UserContext = Depends(require_staff_or_technician_only), db: AsyncSession = Depends(get_db)):
    _require_tenant(user)
    is_full_day = bool(body.get("is_full_day", True))
    data = await _svc.submit_time_off(
        db, uuid.UUID(user.user_id), uuid.UUID(user.tenant_id),
        start_date=dt.date.fromisoformat(body["start_date"]), end_date=dt.date.fromisoformat(body["end_date"]),
        is_full_day=is_full_day,
        start_time=_parse_time(body["start_time"], "start_time") if not is_full_day and body.get("start_time") else None,
        end_time=_parse_time(body["end_time"], "end_time") if not is_full_day and body.get("end_time") else None,
        reason_category=body["reason_category"], note=body.get("note"),
    )
    return ok(data, _rid(request), "home_service_assignment")


@router.post("/time-off/{request_id}/cancel")
async def cancel_mobile_time_off(request_id: uuid.UUID, request: Request, user: UserContext = Depends(require_staff_or_technician_only), db: AsyncSession = Depends(get_db)):
    _require_tenant(user)
    data = await _svc.cancel_time_off(db, uuid.UUID(user.user_id), uuid.UUID(user.tenant_id), request_id)
    return ok(data, _rid(request), "home_service_assignment")


# ── Tenant-side decision (never the technician themselves) ─────────────────

@tenant_router.post("/{request_id}/approve")
async def approve_time_off(request_id: uuid.UUID, body: dict, request: Request, user: UserContext = Depends(require_tenant_owner_mutation), db: AsyncSession = Depends(get_db)):
    from app.engines.home_service_assignment.schedule_models import StaffTimeOffRequest
    req = await db.get(StaffTimeOffRequest, request_id)
    if not req or str(req.tenant_id) != str(user.tenant_id):
        raise ServiceOSException("ENTITY_NOT_FOUND", "Time-off request not found.", status_code=404)
    if req.status != "pending":
        raise ServiceOSException("TIME_OFF_ALREADY_DECIDED", f"This request is already '{req.status}'.", status_code=409)
    req.status = "approved"
    req.decided_by_user_id = uuid.UUID(user.user_id)
    req.decided_at = dt.datetime.now(dt.timezone.utc)
    req.decision_note = body.get("note")
    db.add(req)
    await db.commit()
    await _notify_leave_decision(db, req, approved=True)
    return ok(req.to_dict(), _rid(request), "home_service_assignment")


async def _notify_leave_decision(db: AsyncSession, req, *, approved: bool) -> None:
    try:
        from app.engines.platform_notifications.notification_service import NotificationService
        from app.engines.platform_notifications.constants import EVT_LEAVE_APPROVED, EVT_LEAVE_REJECTED
        await NotificationService().fire_event(
            db, EVT_LEAVE_APPROVED if approved else EVT_LEAVE_REJECTED,
            payload={"request_id": str(req.id), "start_date": req.start_date.isoformat()},
            tenant_id=req.tenant_id,
            source_record_type="staff_time_off_requests", source_record_id=req.id,
            recipients=[{"user_id": req.requested_by_user_id, "recipient_type": "staff"}],
        )
    except Exception:
        pass


@tenant_router.post("/{request_id}/reject")
async def reject_time_off(request_id: uuid.UUID, body: dict, request: Request, user: UserContext = Depends(require_tenant_owner_mutation), db: AsyncSession = Depends(get_db)):
    from app.engines.home_service_assignment.schedule_models import StaffTimeOffRequest
    req = await db.get(StaffTimeOffRequest, request_id)
    if not req or str(req.tenant_id) != str(user.tenant_id):
        raise ServiceOSException("ENTITY_NOT_FOUND", "Time-off request not found.", status_code=404)
    if req.status != "pending":
        raise ServiceOSException("TIME_OFF_ALREADY_DECIDED", f"This request is already '{req.status}'.", status_code=409)
    req.status = "rejected"
    req.decided_by_user_id = uuid.UUID(user.user_id)
    req.decided_at = dt.datetime.now(dt.timezone.utc)
    req.decision_note = body.get("note")
    db.add(req)
    await db.commit()
    await _notify_leave_decision(db, req, approved=False)
    return ok(req.to_dict(), _rid(request), "home_service_assignment")
