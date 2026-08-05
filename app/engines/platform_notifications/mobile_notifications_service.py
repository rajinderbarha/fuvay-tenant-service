"""Technician Mobile App Phase Q — Notifications Center projection.

Reuses the canonical `InAppNotification` model and
`NotificationService.get_user_notifications` (already tenant/recipient-
scoped by `user_id`, already supports read_status/category/action_required
filtering) — never a second notification engine. This module adds only:
technician-specific category chips (Jobs/Schedule/Payments/Account, distinct
from the tenant workspace's 7-category set), day grouping (Today/Yesterday/
Earlier), and an explicit, allowlisted destination registry for the mobile
app's own routes (the tenant-web `TRUSTED_DESTINATIONS` in
workspace_projection.py point at tenant-portal URLs, not usable here).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

# notification_type prefix -> technician-facing category chip. Deliberately
# a SEPARATE mapping from workspace_projection.py's tenant categories --
# spec requires exactly 4 chips (Jobs/Schedule/Payments/Account), not the
# tenant workspace's 7.
_CATEGORY_PREFIXES: list[tuple[str, str]] = [
    ("job", "jobs"), ("booking.", "jobs"), ("quote.", "jobs"), ("appointment.", "jobs"), ("lead.", "jobs"),
    ("leave.", "schedule"), ("shift.", "schedule"),
    ("payment.", "payments"), ("invoice.", "payments"), ("wallet.", "payments"), ("commission.", "payments"),
    ("auth.", "account"), ("tenant.", "account"), ("document.", "account"), ("complaint.", "account"),
]

# Real event_type strings (both dot and underscore forms fired by the two
# real job-assignment producers -- see audit) that represent something the
# technician still needs to act on WHILE unread. Kept small and honest --
# most events fired today are informational only.
_ACTION_REQUIRED_TYPES = {"quote.revision_requested", "leave.rejected"}

# Explicit allowlisted destination registry (spec section 5) -- an unknown
# notification_type simply has no destination, never an arbitrary URL.
def _resolve_destination(notification_type: str, source_record_type: str | None, source_record_id: str | None) -> dict | None:
    if notification_type in ("job.assigned", "job_assigned") and source_record_id:
        return {"type": "job", "id": source_record_id, "section": None}
    if notification_type in ("quote.revision_requested", "quote.sent_to_customer") and source_record_id:
        return {"type": "job", "id": source_record_id, "section": "estimate"}
    if notification_type == "payment.confirmation_requested" and source_record_id:
        return {"type": "job", "id": source_record_id, "section": "payment"}
    if notification_type in ("leave.approved", "leave.rejected"):
        return {"type": "schedule", "id": None, "section": None}
    if notification_type.startswith("auth.") or notification_type.startswith("tenant."):
        return {"type": "security", "id": None, "section": None}
    return None


def _resolve_category(notification_type: str) -> str:
    for prefix, label in _CATEGORY_PREFIXES:
        if notification_type.startswith(prefix):
            return label
    return "account"


def _day_group(created_at: datetime) -> str:
    now = datetime.now(timezone.utc)
    delta_days = (now.date() - created_at.date()).days
    if delta_days <= 0:
        return "today"
    if delta_days == 1:
        return "yesterday"
    return "earlier"


class MobileNotificationsService:
    async def get_inbox(
        self, db: AsyncSession, user_id: uuid.UUID, *,
        filter_key: str, category: str | None, limit: int, offset: int,
    ) -> dict:
        from app.engines.platform_notifications.notification_service import NotificationService
        from app.engines.platform_notifications.constants import READ_UNREAD

        svc = NotificationService()
        read_status = READ_UNREAD if filter_key == "unread" else None
        raw = await svc.get_user_notifications(db, user_id, read_status=read_status, limit=1000, offset=0)
        items = raw["items"]

        projected = []
        for n in items:
            cat = _resolve_category(n["notification_type"])
            action_required = n["read_status"] == "unread" and n["notification_type"] in _ACTION_REQUIRED_TYPES
            projected.append({
                "id": n["id"], "event_type": n["notification_type"], "category": cat,
                "severity": n["severity"], "title": n["title"], "body": n["body"],
                "is_read": n["read_status"] != "unread", "action_required": action_required,
                "created_at": n["created_at"],
                "destination": _resolve_destination(n["notification_type"], n["source_record_type"], n["source_record_id"]),
                "day_group": _day_group(datetime.fromisoformat(n["created_at"])),
            })

        counts = {
            "all": len(projected),
            "unread": len([p for p in projected if not p["is_read"]]),
            "action_required": len([p for p in projected if p["action_required"]]),
        }

        filtered = projected
        if filter_key == "unread":
            filtered = [p for p in filtered if not p["is_read"]]
        elif filter_key == "action_required":
            filtered = [p for p in filtered if p["action_required"]]
        if category:
            filtered = [p for p in filtered if p["category"] == category]

        page = filtered[offset:offset + limit]
        next_cursor = str(offset + limit) if offset + limit < len(filtered) else None

        return {"items": page, "counts": counts, "next_cursor": next_cursor}
