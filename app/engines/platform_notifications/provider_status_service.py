"""NOTIFICATION-CENTER-REBUILD: Delivery & Providers tab backend.

Every field here is computed from real code/data -- there is no stored
"provider config" table to fabricate, and per the architectural rule this
tab must "show only real delivery integrations found in the codebase":

  - in_app: InAppNotificationProvider actually persists a row. Always
    "Available" -- it has no external dependency to fail.
  - email/sms/whatsapp/push (in THIS engine's dispatch path,
    channel_providers.py): all four are unconditional stubs
    (EmailNotificationProviderStub etc.) that always return
    PROVIDER_NOT_CONFIGURED. Reported honestly as "Not Configured", never
    as "Available" just because a toggle exists somewhere.
  - Real Twilio/SMTP client code DOES exist, but in the OTHER notification
    engine (app/engines/notification/dispatchers.py), which this admin
    page and the fire_event()/outbox pipeline do not call. Surfaced as a
    note, not silently merged into this channel's status.

No credentials are ever read or returned by this service.
"""
from __future__ import annotations

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.platform_notifications.constants import (
    ALL_CHANNELS, CHANNEL_IN_APP, DELIVERY_DELIVERED, DELIVERY_FAILED,
)
from app.engines.platform_notifications.channel_providers import CHANNEL_PROVIDERS
from app.engines.platform_notifications.models import NotificationOutbox

# Channels with a real, non-stub deliver() implementation in THIS engine's
# dispatch path today. Kept as an explicit allow-list (not "everything
# except in_app") so adding a genuinely-wired provider later is a one-line
# change instead of an inferred default.
_LIVE_CHANNELS = {CHANNEL_IN_APP}


class ProviderStatusService:

    async def list_channel_status(self, db: AsyncSession) -> list[dict]:
        rows = []
        for channel in ALL_CHANNELS:
            provider = CHANNEL_PROVIDERS.get(channel)
            provider_name = getattr(provider, "provider_name", None)
            is_live = channel in _LIVE_CHANNELS

            delivered = await db.scalar(select(func.count(NotificationOutbox.id)).where(
                NotificationOutbox.channel == channel, NotificationOutbox.delivery_status == DELIVERY_DELIVERED)) or 0
            failed = await db.scalar(select(func.count(NotificationOutbox.id)).where(
                NotificationOutbox.channel == channel, NotificationOutbox.delivery_status == DELIVERY_FAILED)) or 0
            total = delivered + failed
            failure_rate_pct = round(100 * failed / total, 1) if total else None

            last_success = await db.scalar(select(func.max(NotificationOutbox.sent_at)).where(
                NotificationOutbox.channel == channel, NotificationOutbox.delivery_status == DELIVERY_DELIVERED))

            if is_live:
                state = "Available"
            elif total > 0 and failed == total:
                state = "Failed"
            else:
                state = "Not Configured"

            note = None
            if channel != CHANNEL_IN_APP and not is_live:
                note = ("A real Twilio/SMTP client exists in a different, unwired engine "
                        "(app/engines/notification/dispatchers.py) -- not connected to this "
                        "fire_event()/outbox pipeline yet.")

            rows.append({
                "channel": channel,
                "provider": provider_name,
                "environment": "production" if is_live else None,
                "state": state,
                "configured": is_live,
                "verified": is_live,
                "last_health_check": None,   # no health-check job exists -- honest gap, not fabricated
                "last_successful_delivery": last_success.isoformat() if last_success else None,
                "failure_rate_pct": failure_rate_pct,
                "rate_limit": None,          # not implemented at the channel-provider level yet
                "webhook_status": None,      # no inbound delivery-webhook receiver exists yet
                "credential_reference": None,  # never populated -- no secrets exposed by this endpoint
                "note": note,
            })
        return rows
