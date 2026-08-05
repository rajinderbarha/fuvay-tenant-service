"""Technician Mobile App Phase U — Notification Preferences + push-device
registration routes.
"""
from __future__ import annotations

import datetime as dt
import uuid

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import require_staff_or_technician_only, UserContext
from app.dependencies.db import get_db
from app.exceptions import ServiceOSException
from app.schemas.base import ok
from app.engines.auth.models import User
from app.engines.platform_notifications.push_device_models import StaffPushDevice
from app.engines.home_service_assignment.mobile_notification_preferences_service import MobileNotificationPreferencesService

router = APIRouter(prefix="/v1/staff/notification-preferences", tags=["Mobile Notification Preferences"])
push_router = APIRouter(prefix="/v1/staff/push-devices", tags=["Mobile Push Devices"])

_svc = MobileNotificationPreferencesService()


def _rid(request: Request) -> str:
    return request.headers.get("x-request-id", str(uuid.uuid4()))


async def _load_user(db: AsyncSession, user: UserContext) -> User:
    row = await db.get(User, uuid.UUID(user.user_id))
    if not row:
        raise ServiceOSException("NOT_FOUND", "User not found.", status_code=404)
    return row


@router.get("")
async def get_notification_preferences(
    request: Request,
    user: UserContext = Depends(require_staff_or_technician_only),
    db: AsyncSession = Depends(get_db),
):
    row = await _load_user(db, user)
    tid = uuid.UUID(user.tenant_id) if user.tenant_id else None
    data = await _svc.get_preferences(db, row, tid)
    return ok(data, request_id=_rid(request), engine_id="platform_notifications")


@router.patch("")
async def update_notification_preferences(
    body: dict, request: Request,
    user: UserContext = Depends(require_staff_or_technician_only),
    db: AsyncSession = Depends(get_db),
):
    row = await _load_user(db, user)
    tid = uuid.UUID(user.tenant_id) if user.tenant_id else None
    version = (body or {}).get("version")
    if version is None:
        raise ServiceOSException("VALIDATION_ERROR", "version is required.", status_code=400)

    if "code" in (body or {}):
        data = await _svc.update_event_preference(
            db, row, tid, code=body["code"], enabled=bool(body.get("enabled")), expected_version=int(version),
        )
    elif "quiet_hours" in (body or {}):
        qh = body["quiet_hours"] or {}
        data = await _svc.update_quiet_hours(
            db, row, enabled=bool(qh.get("enabled")),
            start_local=qh.get("start_local_time"), end_local=qh.get("end_local_time"),
            expected_version=int(version),
        )
    else:
        raise ServiceOSException("VALIDATION_ERROR", "Either 'code' or 'quiet_hours' must be provided.", status_code=400)

    return ok(data, request_id=_rid(request), engine_id="platform_notifications")


@push_router.post("")
async def register_push_device(
    body: dict, request: Request,
    user: UserContext = Depends(require_staff_or_technician_only),
    db: AsyncSession = Depends(get_db),
):
    device_id = (body or {}).get("device_id")
    token = (body or {}).get("expo_push_token")
    if not device_id or not token:
        raise ServiceOSException("VALIDATION_ERROR", "device_id and expo_push_token are required.", status_code=400)

    user_id = uuid.UUID(user.user_id)
    now = dt.datetime.now(dt.timezone.utc)

    # Prevent cross-user token reuse -- if this exact Expo token was
    # registered under a DIFFERENT user (device handed to someone else,
    # reinstalled under another account), revoke that old binding.
    others = (await db.execute(select(StaffPushDevice).where(
        StaffPushDevice.expo_push_token == token, StaffPushDevice.user_id != user_id,
        StaffPushDevice.revoked_at.is_(None),
    ))).scalars().all()
    for other in others:
        other.revoked_at = now

    existing = (await db.execute(select(StaffPushDevice).where(
        StaffPushDevice.user_id == user_id, StaffPushDevice.device_id == device_id,
    ))).scalar_one_or_none()

    if existing:
        existing.expo_push_token = token
        existing.platform = (body or {}).get("platform")
        existing.app_version = (body or {}).get("app_version")
        existing.last_seen_at = now
        existing.revoked_at = None
    else:
        existing = StaffPushDevice(
            user_id=user_id, device_id=device_id, expo_push_token=token,
            platform=(body or {}).get("platform"), app_version=(body or {}).get("app_version"),
            last_seen_at=now,
        )
        db.add(existing)

    await db.commit()
    return ok({"registered": True}, request_id=_rid(request), engine_id="platform_notifications")


@push_router.delete("/current")
async def revoke_current_push_device(
    body: dict, request: Request,
    user: UserContext = Depends(require_staff_or_technician_only),
    db: AsyncSession = Depends(get_db),
):
    device_id = (body or {}).get("device_id")
    if not device_id:
        raise ServiceOSException("VALIDATION_ERROR", "device_id is required.", status_code=400)
    row = (await db.execute(select(StaffPushDevice).where(
        StaffPushDevice.user_id == uuid.UUID(user.user_id), StaffPushDevice.device_id == device_id,
        StaffPushDevice.revoked_at.is_(None),
    ))).scalar_one_or_none()
    if row:
        row.revoked_at = dt.datetime.now(dt.timezone.utc)
        await db.commit()
    return ok({"revoked": bool(row)}, request_id=_rid(request), engine_id="platform_notifications")
