"""Operational status for the canonical notification delivery providers."""
from __future__ import annotations

from sqlalchemy import and_, or_, select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.platform_notifications.constants import (
    ALL_CHANNELS, CHANNEL_IN_APP, DELIVERY_DELIVERED, DELIVERY_FAILED,
)
from app.engines.platform_notifications.channel_providers import CHANNEL_PROVIDERS
from app.engines.platform_notifications.models import NotificationOutbox
from app.engines.notification.models import NotificationChannelConfig
from app.engines.platform_notifications.channel_config_service import channel_config_service, PLATFORM_CONFIG_TENANT_ID

# Always-live built-in channels. External providers are resolved dynamically
# from encrypted database configuration.
_LIVE_CHANNELS = {CHANNEL_IN_APP}


class ProviderStatusService:

    async def list_channel_status(self, db: AsyncSession) -> list[dict]:
        # One grouped aggregate keeps this admin health panel constant-query as
        # the outbox grows; the previous implementation issued three queries
        # for every configured channel.
        aggregate_query = select(
                NotificationOutbox.channel,
                func.count(NotificationOutbox.id).filter(
                    NotificationOutbox.delivery_status == DELIVERY_DELIVERED
                ).label("delivered"),
                func.count(NotificationOutbox.id).filter(
                    NotificationOutbox.delivery_status == DELIVERY_FAILED
                ).label("failed"),
                func.max(NotificationOutbox.sent_at).filter(
                    NotificationOutbox.delivery_status == DELIVERY_DELIVERED
                ).label("last_success"),
            ).group_by(NotificationOutbox.channel).subquery()
        result = await db.execute(select(
            NotificationChannelConfig,
            aggregate_query.c.channel.label("aggregate_channel"),
            aggregate_query.c.delivered,
            aggregate_query.c.failed,
            aggregate_query.c.last_success,
        ).select_from(NotificationChannelConfig).join(
            aggregate_query,
            and_(
                NotificationChannelConfig.channel == aggregate_query.c.channel,
                NotificationChannelConfig.tenant_id == PLATFORM_CONFIG_TENANT_ID,
            ),
            full=True,
        ).where(or_(
            NotificationChannelConfig.tenant_id == PLATFORM_CONFIG_TENANT_ID,
            NotificationChannelConfig.tenant_id.is_(None),
        )))
        aggregates, config_rows = {}, {}
        for row in result.all():
            config = row[0]
            aggregate_channel = row.aggregate_channel
            if config is not None:
                config_rows[config.channel] = config
            if aggregate_channel:
                aggregates[aggregate_channel] = row

        rows = []
        for channel in ALL_CHANNELS:
            channel_config = channel_config_service.public_item(channel, config_rows.get(channel))
            provider = CHANNEL_PROVIDERS.get(channel)
            provider_name = getattr(provider, "provider_name", None)
            is_live = bool(channel_config["configured"])
            aggregate = aggregates.get(channel)
            delivered = int(aggregate.delivered or 0) if aggregate else 0
            failed = int(aggregate.failed or 0) if aggregate else 0
            total = delivered + failed
            failure_rate_pct = round(100 * failed / total, 1) if total else None
            last_success = aggregate.last_success if aggregate else None

            if is_live:
                state = "Available"
            elif channel_config.get("last_test_status") == "failed":
                state = "Failed"
            elif channel_config.get("setup_complete"):
                state = "Ready to enable"
            else:
                state = "Not Configured"

            rows.append({
                "channel": channel,
                "provider": provider_name,
                "description": channel_config["description"],
                "managed": channel_config["managed"],
                "environment": "platform" if is_live else None,
                "state": state,
                "configured": is_live,
                "setup_complete": channel_config["setup_complete"],
                "enabled": channel_config["enabled"],
                "verified": channel_config["verified"],
                "fields": channel_config["fields"],
                "last_health_check": channel_config["last_tested_at"],
                "last_test_status": channel_config["last_test_status"],
                "last_test_message": channel_config["last_test_message"],
                "last_successful_delivery": last_success.isoformat() if last_success else None,
                "failure_rate_pct": failure_rate_pct,
                "rate_limit": None,
                # In-app delivery is final when persisted and has no provider
                # callback. Stub external channels cannot receive callbacks.
                "webhook_status": "Not required" if is_live else "Unavailable",
                "credential_reference": None,
                "note": None,
            })
        return rows
