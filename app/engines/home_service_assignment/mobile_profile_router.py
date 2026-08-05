"""Technician Mobile App Phase R — Profile & Account Hub routes.

Read-only identity/employment/readiness/documents projection + document
submission. Security actions (password change, MFA, sessions, logout) are
called by the mobile client directly against the EXISTING canonical
`/v1/auth/*` endpoints -- never duplicated here.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import require_staff_or_technician_only, UserContext
from app.dependencies.db import get_db
from app.schemas.base import ok
from app.exceptions import ServiceOSException
from app.engines.home_service_assignment.mobile_profile_service import MobileProfileService
from app.engines.platform_notifications.mobile_preferences_service import MobilePreferencesService

router = APIRouter(prefix="/v1/staff/me", tags=["Technician Mobile Profile"])
_svc = MobileProfileService()
_prefs_svc = MobilePreferencesService()


def _rid(r: Request) -> str:
    return getattr(r.state, "request_id", "—")


def _require_tenant(user: UserContext) -> None:
    if not user.tenant_id:
        raise ServiceOSException("TENANT_CONTEXT_MISSING", "No active tenant context.", status_code=403)


@router.get("/profile")
async def get_mobile_profile(request: Request, user: UserContext = Depends(require_staff_or_technician_only), db: AsyncSession = Depends(get_db)):
    _require_tenant(user)
    data = await _svc.get_profile(db, uuid.UUID(user.user_id), uuid.UUID(user.tenant_id))
    return ok(data, _rid(request), "home_service_assignment")


@router.post("/profile/documents")
async def add_mobile_profile_document(body: dict, request: Request, user: UserContext = Depends(require_staff_or_technician_only), db: AsyncSession = Depends(get_db)):
    _require_tenant(user)
    import datetime as dt
    expiry = dt.date.fromisoformat(body["expiry_date"]) if body.get("expiry_date") else None
    data = await _svc.add_document(
        db, uuid.UUID(user.user_id), uuid.UUID(user.tenant_id),
        document_type=body["document_type"], media_id=uuid.UUID(body["media_id"]), expiry_date=expiry,
    )
    return ok(data, _rid(request), "home_service_assignment")


@router.get("/notification-preferences")
async def get_mobile_notification_preferences(request: Request, user: UserContext = Depends(require_staff_or_technician_only), db: AsyncSession = Depends(get_db)):
    data = await _prefs_svc.get_preferences(db, uuid.UUID(user.user_id))
    return ok(data, _rid(request), "platform_notifications")


@router.put("/notification-preferences")
async def update_mobile_notification_preferences(body: dict, request: Request, user: UserContext = Depends(require_staff_or_technician_only), db: AsyncSession = Depends(get_db)):
    _require_tenant(user)
    data = await _prefs_svc.update_preference(db, uuid.UUID(user.user_id), uuid.UUID(user.tenant_id), body["category"], bool(body["enabled"]))
    return ok(data, _rid(request), "platform_notifications")
