"""Tenant verification-status admin notifications.

Real gap this closes: reject_verification/request_changes/send_notification
in admin_service.py all saved a reason/message (audit log, suspension_reason,
changes_requested_note) but never actually notified the tenant owner --
send_notification in particular is a pure audit-log stub despite its name
and docstring claiming it sends something. A provider whose verification was
rejected or sent back for changes had no way to find out WHY short of asking
support, and no path back to fixing and resubmitting. Mirrors the same
InAppNotification pattern already used by complaints/notifications.py etc.
"""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# Where the tenant owner should land to see the reason and act on it --
# the Home Services setup review step shows verification_status/rejection
# reason and is where documents/business profile get resubmitted from.
_RESUBMIT_URL = "/tenant/home-services/setup/review"


async def _tenant_owner_ids(db: AsyncSession, tenant_id: uuid.UUID) -> list[uuid.UUID]:
    from app.engines.auth.models import User
    rows = await db.execute(
        select(User.id).where(
            User.tenant_id == tenant_id,
            User.role == "tenant_owner",
            User.is_active.is_(True),
        )
    )
    return [r for r in rows.scalars().all()]


async def notify_tenant_verification(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    notification_type: str,
    title: str,
    body: str,
    severity: str = "warning",
    action_url: str = _RESUBMIT_URL,
    action_label: str = "Review and resubmit",
) -> int:
    """Notify the tenant owner(s) about a verification decision, with the
    real reason in the body so they know exactly what to fix before
    resubmitting. Best-effort: caller should not let a notification failure
    block the verification decision itself."""
    from app.engines.platform_notifications.models import InAppNotification

    owner_ids = await _tenant_owner_ids(db, tenant_id)
    for oid in owner_ids:
        db.add(InAppNotification(
            user_id=oid,
            tenant_id=tenant_id,
            notification_type=notification_type,
            title=title,
            body=body,
            action_url=action_url,
            action_label=action_label,
            source_record_type="tenants",
            source_record_id=tenant_id,
            severity=severity,
            read_status="unread",
        ))
    return len(owner_ids)
