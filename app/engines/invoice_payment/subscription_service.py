"""Sprint 23 — ProviderSubscriptionStatusService: wraps existing subscriptions table."""
from __future__ import annotations
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.subscription.models import Subscription
from app.engines.invoice_payment.constants import ERR_SUBSCRIPTION_NOT_FOUND, ERR_SUBSCRIPTION_INACTIVE


class ProviderSubscriptionStatusService:

    async def get_provider_subscription_status(
        self, db: AsyncSession, tenant_id: str, category_id: str | None = None,
    ) -> dict:
        res = await db.execute(
            select(Subscription).where(Subscription.tenant_id == uuid.UUID(tenant_id))
        )
        sub = res.scalar_one_or_none()
        if not sub:
            return {
                "tenant_id":  tenant_id,
                "status":     "no_subscription",
                "plan_type":  None,
                "is_active":  False,
                "expires_at": None,
                "message":    "No subscription found for this provider.",
            }
        now = datetime.now(timezone.utc)
        is_active = (
            sub.status == "active"
            and (sub.current_period_end is None or sub.current_period_end > now)
        )
        expiring_soon = (
            sub.current_period_end is not None
            and (sub.current_period_end - now).days <= 7
            and is_active
        )
        return {
            "tenant_id":       tenant_id,
            "status":          sub.status,
            "plan_type":       sub.plan_type,
            "billing_cycle":   sub.billing_cycle,
            "amount":          str(sub.amount),
            "currency":        sub.currency,
            "is_active":       is_active,
            "current_period_start": sub.current_period_start.isoformat() if sub.current_period_start else None,
            "expires_at":      sub.current_period_end.isoformat() if sub.current_period_end else None,
            "expiring_soon":   expiring_soon,
            "renewal_required":expiring_soon or not is_active,
        }

    async def validate_subscription_active(
        self, db: AsyncSession, tenant_id: str,
    ) -> bool:
        res = await db.execute(
            select(Subscription).where(Subscription.tenant_id == uuid.UUID(tenant_id))
        )
        sub = res.scalar_one_or_none()
        if not sub:
            return False
        now = datetime.now(timezone.utc)
        return (
            sub.status == "active"
            and (sub.current_period_end is None or sub.current_period_end > now)
        )

    async def list_all_subscription_statuses(self, db: AsyncSession, limit: int = 200, offset: int = 0) -> list[dict]:
        limit = min(limit, 500)
        res = await db.execute(select(Subscription).order_by(Subscription.created_at.desc()).limit(limit).offset(offset))
        now = datetime.now(timezone.utc)
        out = []
        for sub in res.scalars().all():
            is_active = (
                sub.status == "active"
                and (sub.current_period_end is None or sub.current_period_end > now)
            )
            out.append({
                "tenant_id":  str(sub.tenant_id),
                "status":     sub.status,
                "plan_type":  sub.plan_type,
                "is_active":  is_active,
                "expires_at": sub.current_period_end.isoformat() if sub.current_period_end else None,
            })
        return out
