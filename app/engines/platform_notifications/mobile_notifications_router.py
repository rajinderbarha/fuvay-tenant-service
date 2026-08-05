"""Technician Mobile App Phase Q — Notifications Center route.

Read-only projection only. Mutations (mark-one-read, mark-all-read,
unread-count) reuse the EXISTING `staff_notif_router` endpoints directly
from the mobile client (`/v1/staff/notifications/*`, already
`require_staff_or_technician_only`-scoped) -- never duplicated here.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import require_staff_or_technician_only, UserContext
from app.dependencies.db import get_db
from app.schemas.base import ok
from app.engines.platform_notifications.mobile_notifications_service import MobileNotificationsService

router = APIRouter(prefix="/v1/staff/mobile-notifications", tags=["Technician Mobile Notifications"])
_svc = MobileNotificationsService()


def _rid(r: Request) -> str:
    return getattr(r.state, "request_id", "—")


@router.get("")
async def get_mobile_notifications(
    request: Request,
    filter: str = Query("all", pattern="^(all|unread|action_required)$"),
    category: str | None = Query(None, pattern="^(jobs|schedule|payments|account)$"),
    cursor: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    user: UserContext = Depends(require_staff_or_technician_only),
    db: AsyncSession = Depends(get_db),
):
    offset = int(cursor) if cursor and cursor.isdigit() else 0
    data = await _svc.get_inbox(db, uuid.UUID(user.user_id), filter_key=filter, category=category, limit=limit, offset=offset)
    return ok(data, _rid(request), "platform_notifications")
