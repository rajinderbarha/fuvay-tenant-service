"""Technician Mobile App Phase R — Notification Preferences.

Reuses the EXISTING per-event/per-channel `NotificationPreference` model +
`NotificationService.get_preferences`/`update_preference` (already used by
the customer/provider/admin preference screens) -- never a second
preferences store. This module adds only the technician-facing category
grouping (Push/Job updates/Schedule updates/Payment updates/Account &
security) the mobile UI needs, mapped onto the real underlying event keys.

Mandatory events (account suspension, security alerts, critical assignment
cancellation) are never exposed as togglable here -- `update_preference`
itself already rejects disabling a mandatory event's in_app channel; this
module only ever touches the `push` channel, which is never mandatory.
"""
from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

# Real bug fixed here: three of these keys were not registered event keys at
# all -- "payment.confirmation_requested", "payment.mismatch_reported" and
# "auth.login_success" do not exist in the NotificationEventRegistry. Because
# update_preference() raises ValueError for an unknown key and the loop below
# swallowed it, the "payment_updates" toggle was COMPLETELY inert (both of its
# keys were bogus) and "account_updates" was too: the read below reports a
# category as ON if ANY key is not disabled, and a key that can never be
# written is never disabled. Turning either off returned 200 and changed
# nothing. The registered keys are "payment.collected" and
# "auth.login_failed".
CATEGORY_EVENT_KEYS: dict[str, list[str]] = {
    "job_updates": ["job.assigned", "quote.revision_requested", "quote.sent_to_customer"],
    "schedule_updates": ["leave.approved", "leave.rejected"],
    "payment_updates": ["payment.collected"],
    "account_updates": ["auth.login_failed", "tenant.suspended"],
}
CHANNEL_PUSH = "push"


class MobilePreferencesService:
    async def get_preferences(self, db: AsyncSession, user_id: uuid.UUID) -> dict:
        from app.engines.platform_notifications.notification_service import NotificationService
        rows = await NotificationService().get_preferences(db, user_id)
        disabled_keys = {(r.event_key, r.channel) for r in rows if not r.is_enabled}

        categories = {}
        for category, keys in CATEGORY_EVENT_KEYS.items():
            # A category is "on" unless the technician has explicitly
            # disabled push for every one of its representative event keys.
            categories[category] = any((k, CHANNEL_PUSH) not in disabled_keys for k in keys)

        return {"push_enabled": any(categories.values()), "categories": categories}

    async def update_preference(self, db: AsyncSession, user_id: uuid.UUID, tenant_id: uuid.UUID, category: str, enabled: bool) -> dict:
        from app.exceptions import ServiceOSException
        from app.engines.platform_notifications.notification_service import NotificationService
        if category not in CATEGORY_EVENT_KEYS:
            raise ServiceOSException("VALIDATION_ERROR", "Unknown preference category.", status_code=422)
        svc = NotificationService()
        for key in CATEGORY_EVENT_KEYS[category]:
            try:
                await svc.update_preference(db, user_id, tenant_id, key, CHANNEL_PUSH, enabled)
            except ValueError as exc:
                # This means the key above is not in the event registry -- a
                # configuration bug in CATEGORY_EVENT_KEYS, not something the
                # caller did. Swallowing it is what let a toggle silently do
                # nothing for so long, so it is surfaced instead.
                raise ServiceOSException(
                    "NOTIFICATION_CATEGORY_MISCONFIGURED",
                    f"Notification category '{category}' maps to unknown event key '{key}'.",
                    status_code=500,
                ) from exc
        return await self.get_preferences(db, user_id)
