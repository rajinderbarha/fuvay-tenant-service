"""Provider and customer notifications for directly resolved complaints.

Platform admins monitor aggregate SLA and quality signals, but the provider
responds to the customer and owns the resolution. No complaint is routed to
an admin adjudication queue by these helpers.
"""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


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
    customer_id = getattr(complaint, "customer_id", None)
    # Persisted complaints always carry a UUID.  Reject incomplete projections
    # instead of attempting to write an unusable notification recipient.
    if not isinstance(customer_id, uuid.UUID):
        return 0
    db.add(InAppNotification(
        user_id=customer_id,
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


async def notify_customer_complaint_channel(
    db: AsyncSession,
    complaint,
    *,
    text: str,
    rows: list[dict] | None = None,
    section_title: str = "Complaint update",
) -> bool:
    """Send the same case update back to the social thread that made the job.

    This is deliberately best-effort. The complaint transition remains valid if
    Meta's 24-hour service window is closed; the in-app notification above is the
    durable fallback. ``source_ai_session_id`` prevents an approval from leaking
    to another Instagram account linked to the same phone/customer.
    """
    from sqlalchemy import text as sql_text
    from app.engines.messaging_gateway.service import notify_customer

    customer_id = getattr(complaint, "customer_id", None)
    if not isinstance(customer_id, uuid.UUID):
        return False

    source_session_id = None
    booking_id = getattr(complaint, "booking_id", None)
    if not booking_id and getattr(complaint, "job_id", None):
        booking_id = (await db.execute(sql_text(
            "SELECT booking_id FROM service_jobs WHERE id=:job_id"
        ), {"job_id": str(complaint.job_id)})).scalar_one_or_none()
    if booking_id:
        source_session_id = (await db.execute(sql_text(
            "SELECT ai_session_id FROM service_bookings WHERE id=:booking_id"
        ), {"booking_id": str(booking_id)})).scalar_one_or_none()
    return await notify_customer(
        db,
        customer_id,
        text,
        rows=rows,
        source_ai_session_id=source_session_id,
        section_title=section_title,
    )


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
