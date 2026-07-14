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


async def _tenant_owner_ids(db: AsyncSession, tenant_id) -> list[uuid.UUID]:
    from app.engines.auth.models import User
    if not tenant_id:
        return []
    rows = await db.execute(
        select(User.id).where(
            User.tenant_id == tenant_id,
            User.role == "tenant_owner",
            User.is_active.is_(True),
        )
    )
    return [r for r in rows.scalars().all()]


async def notify_customer_complaint(
    db: AsyncSession,
    complaint,
    *,
    notification_type: str,
    title: str,
    body: str,
    severity: str = "info",
) -> int:
    """Notify the customer who raised the complaint. MODULE-L5-02 bug #42: the
    dual-acceptance flow needs each party to act in turn, but the customer was
    never told when a resolution or settlement proposal was awaiting them — so it
    silently waited on someone who had no idea it was their move."""
    from app.engines.platform_notifications.models import InAppNotification
    if not complaint.customer_id:
        return 0
    db.add(InAppNotification(
        user_id=complaint.customer_id,
        tenant_id=None,
        notification_type=notification_type,
        title=title,
        body=body,
        action_url=f"/customer/complaints/{complaint.id}",
        action_label="View complaint",
        source_record_type="customer_complaints",
        source_record_id=complaint.id,
        severity=severity,
        read_status="unread",
    ))
    return 1


async def notify_provider_complaint(
    db: AsyncSession,
    complaint,
    *,
    notification_type: str,
    title: str,
    body: str,
    severity: str = "info",
) -> int:
    """Notify the provider (tenant owners) whose job the complaint is about."""
    from app.engines.platform_notifications.models import InAppNotification
    owner_ids = await _tenant_owner_ids(db, complaint.tenant_id)
    for oid in owner_ids:
        db.add(InAppNotification(
            user_id=oid,
            tenant_id=complaint.tenant_id,
            notification_type=notification_type,
            title=title,
            body=body,
            action_url=f"/provider/complaints/{complaint.id}",
            action_label="View complaint",
            source_record_type="customer_complaints",
            source_record_id=complaint.id,
            severity=severity,
            read_status="unread",
        ))
    return len(owner_ids)


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
