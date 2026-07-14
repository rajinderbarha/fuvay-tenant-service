"""MODULE-L5-02 bug #40 — complaint admin notifications.

The complaints engine never created a single in-app notification. When the AI
settlement escalates a case to admin manual review (its whole over-cap /
no-money path), or the SLA engine pushes a stalled complaint onto the admin
queue, the admin was never told — they would only find out by happening to look
at the list. This adds targeted notifications to every super_admin, reusing the
same InAppNotification the compliance SLA job uses.
"""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


async def _super_admin_ids(db: AsyncSession) -> list[uuid.UUID]:
    from app.engines.auth.models import User
    rows = await db.execute(
        select(User.id).where(User.role == "super_admin", User.is_active.is_(True))
    )
    return [r for r in rows.scalars().all()]


async def notify_admins_complaint(
    db: AsyncSession,
    complaint,
    *,
    notification_type: str,
    title: str,
    body: str,
    severity: str = "warning",
) -> int:
    """Notify every active super_admin about a complaint. Best-effort: a
    notification failure must never break the settlement/escalation it reports
    on, so callers wrap this in try/except."""
    from app.engines.platform_notifications.models import InAppNotification

    admin_ids = await _super_admin_ids(db)
    for aid in admin_ids:
        db.add(InAppNotification(
            user_id=aid,
            tenant_id=None,
            notification_type=notification_type,
            title=title,
            body=body,
            action_url=f"/admin/complaints/{complaint.id}",
            action_label="Review complaint",
            source_record_type="customer_complaints",
            source_record_id=complaint.id,
            severity=severity,
            read_status="unread",
        ))
    return len(admin_ids)
