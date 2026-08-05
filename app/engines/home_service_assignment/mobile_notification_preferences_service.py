"""Technician Mobile App Phase U — Notification Preferences.

Reuses the CANONICAL `NotificationService.get_preferences`/`update_preference`
(per-`(user_id, event_key, channel="in_app")` rows, already real and already
gated at dispatch time in `_create_outbox_for_recipient` -- confirmed by
audit) over REAL, already-registered event keys this session's own producers
confirmed deliver to a technician recipient (`EVT_JOB_ASSIGNED` via
`also_notify=[RECIP_STAFF]`; `EVT_LEAVE_APPROVED/REJECTED` via Phase Q's
`_notify_leave_decision`; `EVT_CORRECTION_*` via Phase S's `_notify_decision`;
`document.verified/rejected/changes_requested` via Phase T's
`_notify_technician`). Never a second event registry or a fabricated
preference for a category with no confirmed technician-facing producer.

Mandatory-ness is resolved from TWO sources, both backend-authoritative
(never the mobile client): the shared registry's `cfg.is_mandatory`, OR this
service's own `STAFF_MANDATORY_OVERRIDE` policy set for events the registry
doesn't mark globally mandatory but that MUST stay on for a technician
specifically (job assignment) -- this is a backend policy layer, not a
client-side list, satisfying spec section 3.
"""
from __future__ import annotations

import datetime as dt
import re
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import ServiceOSException
from app.engines.platform_notifications.notification_service import NotificationService
from app.engines.platform_notifications.event_registry import NotificationEventRegistry
from app.engines.platform_notifications.constants import CHANNEL_IN_APP
from app.engines.platform_notifications.push_device_models import StaffPushDevice

_TIME_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")

# Backend policy: events that must remain enabled for a technician even
# though the shared, cross-audience registry doesn't mark them globally
# mandatory (e.g. a customer-facing copy of the same event key is optional
# for them, but losing your own job-assignment record is not optional for a
# technician). Additive only -- never used to loosen `cfg.is_mandatory`.
STAFF_MANDATORY_OVERRIDE = {"job.assigned"}

# One representative "toggle" per user-facing group, each backed by every
# real event_key this session's own code confirmed delivers to a technician
# recipient. Categories with no confirmed technician-facing producer today
# (payment confirmation, job-status reminders, security alerts, product
# updates, estimate & parts) are deliberately NOT listed here rather than
# fabricated -- spec section 1: "Only show preferences supported end to end."
EVENT_GROUPS: list[dict] = [
    {"group": "jobs", "code": "job.assigned", "label": "New job assignments",
     "description": "When work is assigned or removed", "event_keys": ["job.assigned"]},
    {"group": "schedule", "code": "schedule.leave_decision", "label": "Schedule changes",
     "description": "Rescheduled jobs and leave decisions", "event_keys": ["leave.approved", "leave.rejected"]},
    {"group": "account", "code": "account.employment_correction", "label": "Employment correction updates",
     "description": "Decisions on your employment correction requests",
     "event_keys": ["employment_correction.approved", "employment_correction.changes_requested", "employment_correction.rejected"]},
    {"group": "account", "code": "account.document_reminders", "label": "Document reminders",
     "description": "Review, expiry and replacement updates",
     "event_keys": ["document.verified", "document.rejected", "document.changes_requested"]},
]


class MobileNotificationPreferencesService:
    async def get_preferences(self, db: AsyncSession, user, tenant_id: uuid.UUID | None) -> dict:
        svc = NotificationService()
        rows = await svc.get_preferences(db, user.id)
        by_key_channel = {(r.event_key, r.channel): r.is_enabled for r in rows}

        device_count = (await db.execute(select(StaffPushDevice).where(
            StaffPushDevice.user_id == user.id, StaffPushDevice.revoked_at.is_(None),
        ))).scalars().all()
        push_registered = len(device_count) > 0

        events = []
        for group in EVENT_GROUPS:
            keys = group["event_keys"]
            cfgs = [NotificationEventRegistry.get(k) for k in keys]
            cfgs = [c for c in cfgs if c is not None]
            mandatory = any(c.is_mandatory for c in cfgs) or any(k in STAFF_MANDATORY_OVERRIDE for k in keys)
            # A group is "enabled" if ANY of its underlying event_keys is
            # enabled for in_app -- default true (no row = enabled), matching
            # NotificationService._check_preference's own default.
            enabled = any(by_key_channel.get((k, CHANNEL_IN_APP), True) for k in keys)
            events.append({
                "event_group": group["group"], "code": group["code"], "label": group["label"],
                "description": group["description"],
                "push_enabled": enabled, "configurable": not mandatory, "mandatory": mandatory,
            })

        return {
            "timezone": user.timezone,
            "delivery": {
                "push": {"supported": True, "enabled": push_registered, "configurable": True, "os_permission": "unknown"},
                "in_app": {"supported": True, "enabled": True, "configurable": False, "locked_reason": "In-app operational notifications are required"},
                "email_summary": {"supported": False, "enabled": False, "configurable": False},
            },
            "events": events,
            "quiet_hours": {
                "supported": True, "enabled": user.quiet_hours_enabled,
                "start_local_time": user.quiet_hours_start_local, "end_local_time": user.quiet_hours_end_local,
                "timezone": user.timezone, "critical_events_bypass": True,
            },
            "version": user.notif_prefs_version,
        }

    async def update_event_preference(self, db: AsyncSession, user, tenant_id: uuid.UUID | None, *,
                                       code: str, enabled: bool, expected_version: int) -> dict:
        if user.notif_prefs_version != expected_version:
            raise ServiceOSException("CONFLICT", "Notification policy changed since you last loaded it.", status_code=409)

        group = next((g for g in EVENT_GROUPS if g["code"] == code), None)
        if not group:
            raise ServiceOSException("UNKNOWN_PREFERENCE", f"'{code}' is not a known preference.", status_code=422)

        keys = group["event_keys"]
        cfgs = [NotificationEventRegistry.get(k) for k in keys]
        mandatory = any(c.is_mandatory for c in cfgs if c) or any(k in STAFF_MANDATORY_OVERRIDE for k in keys)
        if mandatory and not enabled:
            raise ServiceOSException("MANDATORY_PREFERENCE", "This notification is required and cannot be disabled.", status_code=422)

        svc = NotificationService()
        for key in keys:
            try:
                await svc.update_preference(db, user.id, tenant_id, key, CHANNEL_IN_APP, enabled)
            except ValueError:
                # A per-key mandatory guard inside update_preference is a
                # stricter, independent check than ours above -- honor it
                # rather than partially apply the other keys in this group.
                raise ServiceOSException("MANDATORY_PREFERENCE", "This notification is required and cannot be disabled.", status_code=422)

        user.notif_prefs_version += 1
        await db.commit()
        return await self.get_preferences(db, user, tenant_id)

    async def update_quiet_hours(self, db: AsyncSession, user, *, enabled: bool,
                                  start_local: str | None, end_local: str | None,
                                  expected_version: int) -> dict:
        if user.notif_prefs_version != expected_version:
            raise ServiceOSException("CONFLICT", "Notification policy changed since you last loaded it.", status_code=409)
        if enabled:
            if not start_local or not end_local or not _TIME_RE.match(start_local) or not _TIME_RE.match(end_local):
                raise ServiceOSException("VALIDATION_ERROR", "Quiet hours require a valid start and end time (HH:MM).", status_code=422)

        user.quiet_hours_enabled = enabled
        user.quiet_hours_start_local = start_local if enabled else user.quiet_hours_start_local
        user.quiet_hours_end_local = end_local if enabled else user.quiet_hours_end_local
        user.notif_prefs_version += 1
        await db.commit()
        return await self.get_preferences(db, user, None)

    def is_within_quiet_hours(self, user, now_local: dt.time | None = None) -> bool:
        """Server-side evaluation (spec section 7: never client-only), with
        real overnight-window support (e.g. 22:00-07:00)."""
        if not user.quiet_hours_enabled or not user.quiet_hours_start_local or not user.quiet_hours_end_local:
            return False
        now_local = now_local or dt.datetime.now().time()
        start = dt.time.fromisoformat(user.quiet_hours_start_local)
        end = dt.time.fromisoformat(user.quiet_hours_end_local)
        if start <= end:
            return start <= now_local < end
        return now_local >= start or now_local < end  # overnight window
