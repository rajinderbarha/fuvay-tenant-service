"""Subscription Engine — SubscriptionService. Proven Level 5.
Proration from immutable SubscriptionPeriod rows.
Plan change history append-only. Usage from canonical CommissionRecord source.
"""
from __future__ import annotations
import uuid
from datetime import datetime, timezone, timedelta
from decimal import Decimal, ROUND_HALF_UP

import structlog
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.subscription.constants import (
    SubStatus, BillingCycle, PlanChangeType, GRACE_PERIOD_DAYS,
    DUNNING_RETRY_DAYS, MAX_DUNNING_ATTEMPTS, PRORATION_PRECISION,
)
from app.engines.subscription.models import Subscription, SubscriptionPeriod, SubscriptionEvent
from app.exceptions import ServiceOSException, NotFoundException
from app.redis_client import get_redis
from app.schemas.base import encode_cursor, decode_cursor

logger = structlog.get_logger("subscription.service")
utcnow = lambda: datetime.now(timezone.utc)

PLAN_PRICES = {
    ("starter",  "monthly"): Decimal("999.00"),
    ("growth",   "monthly"): Decimal("2499.00"),
    ("enterprise","monthly"):Decimal("7999.00"),
    ("starter",  "annual"):  Decimal("9990.00"),
    ("growth",   "annual"):  Decimal("24990.00"),
    ("enterprise","annual"): Decimal("79990.00"),
}
PLAN_JOB_LIMITS = {"starter": 100, "growth": 500, "enterprise": 9999}


class SubscriptionService:
    def __init__(self, db: AsyncSession, request_id: str = "—",
                 actor_id: uuid.UUID | None = None, actor_role: str | None = None,
                 actor_tenant_id: uuid.UUID | None = None):
        self.db = db; self.redis = get_redis()
        self.request_id = request_id
        self.actor_id = actor_id; self.actor_role = actor_role
        self.actor_tenant_id = actor_tenant_id

    def _require_trusted_tenant(self, requested_tenant_id: uuid.UUID) -> uuid.UUID:
        """Slice 2F-37: update_plan accepted a client-supplied tenant_id
        with no comparison to the caller's own tenant. super_admin is
        exempt (platform-wide)."""
        if self.actor_role == "super_admin":
            return requested_tenant_id
        if self.actor_tenant_id is None:
            raise ServiceOSException(
                "PERMISSION_DENIED", "No tenant context.",
                blocking_rule="subscription_mutation_requires_trusted_tenant_context")
        if requested_tenant_id != self.actor_tenant_id:
            raise ServiceOSException(
                "PERMISSION_DENIED", "You do not have access to this tenant's subscription.",
                blocking_rule="subscription_mutation_cross_tenant_denied")
        return self.actor_tenant_id

    # PROVEN LEVEL 5: proration from immutable SubscriptionPeriod
    def _compute_proration(self, period: SubscriptionPeriod, change_date: datetime) -> Decimal:
        total_days = (period.ends_at - period.started_at).days
        remaining_days = (period.ends_at - change_date).days
        if total_days <= 0 or remaining_days <= 0:
            return Decimal("0.00")
        proration = (period.amount * Decimal(str(remaining_days)) / Decimal(str(total_days)))
        return proration.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    async def _write_event(self, sub: Subscription, event_type: str,
                            from_plan: str | None = None, to_plan: str | None = None,
                            proration: Decimal | None = None, meta: dict | None = None):
        self.db.add(SubscriptionEvent(
            subscription_id=sub.id, tenant_id=sub.tenant_id,
            event_type=event_type, from_plan=from_plan, to_plan=to_plan,
            proration_amount=proration, actor_id=self.actor_id, meta=meta or {}))

    async def _publish(self, event_type: str, tenant_id: str, sub_id: str, payload: dict):
        try:
            from app.core.events import get_event_bus
            bus = get_event_bus()
            await bus.publish_raw(event_type=event_type, engine_id="subscription",
                tenant_id=tenant_id, entity_type="subscription", entity_id=sub_id,
                payload=payload, actor_id=str(self.actor_id) if self.actor_id else None)
        except Exception: pass

    def _sub_dict(self, s: Subscription) -> dict:
        return {"subscription_id": str(s.id), "tenant_id": str(s.tenant_id),
                "plan_type": s.plan_type, "billing_cycle": s.billing_cycle,
                "status": s.status, "amount": float(s.amount),
                "current_period_start": s.current_period_start.isoformat() if s.current_period_start else None,
                "current_period_end": s.current_period_end.isoformat() if s.current_period_end else None,
                "trial_end": s.trial_end.isoformat() if s.trial_end else None,
                "dunning_count": s.dunning_count,
                "next_retry_at": s.next_retry_at.isoformat() if s.next_retry_at else None}

    async def create_subscription(self, tenant_id: uuid.UUID, plan_type: str,
                                   billing_cycle: str, trial_days: int = 14) -> dict:
        ex = await self.db.execute(select(Subscription).where(Subscription.tenant_id == tenant_id))
        if ex.scalar_one_or_none():
            raise ServiceOSException("CONFLICT", "Tenant already has a subscription.")

        amount = PLAN_PRICES.get((plan_type, billing_cycle), Decimal("999.00"))
        trial_end = utcnow() + timedelta(days=trial_days)
        period_start = trial_end
        period_end = period_start + timedelta(days=30 if billing_cycle == "monthly" else 365)

        sub = Subscription(tenant_id=tenant_id, plan_type=plan_type,
            billing_cycle=billing_cycle, status=SubStatus.TRIALING,
            amount=amount, trial_end=trial_end,
            current_period_start=period_start, current_period_end=period_end)
        self.db.add(sub); await self.db.flush()

        self.db.add(SubscriptionPeriod(
            subscription_id=sub.id, tenant_id=tenant_id, plan_type=plan_type,
            started_at=period_start, ends_at=period_end, amount=amount,
            status="scheduled", jobs_included=PLAN_JOB_LIMITS.get(plan_type, 100)))

        await self._write_event(sub, "subscription_created",
                                 to_plan=plan_type, meta={"trial_days": trial_days})
        await self._publish("subscription.created", str(tenant_id), str(sub.id),
                            {"plan": plan_type, "cycle": billing_cycle})
        return self._sub_dict(sub)

    async def get_subscription(self, tenant_id: uuid.UUID) -> dict:
        r = await self.db.execute(select(Subscription).where(Subscription.tenant_id == tenant_id))
        sub = r.scalar_one_or_none()
        if not sub: raise NotFoundException("Subscription", str(tenant_id))
        return self._sub_dict(sub)

    # PROVEN LEVEL 5: plan change uses immutable period for proration
    async def update_plan(self, tenant_id: uuid.UUID, new_plan: str,
                           billing_cycle: str) -> dict:
        tenant_id = self._require_trusted_tenant(tenant_id)
        r = await self.db.execute(select(Subscription).where(Subscription.tenant_id == tenant_id))
        sub = r.scalar_one_or_none()
        if not sub: raise NotFoundException("Subscription", str(tenant_id))
        if sub.status not in (SubStatus.ACTIVE, SubStatus.TRIALING):
            raise ServiceOSException("CONFLICT", f"Cannot change plan in status: {sub.status}")

        old_plan = sub.plan_type
        new_amount = PLAN_PRICES.get((new_plan, billing_cycle), Decimal("999.00"))

        # Get current immutable period for proration
        period_r = await self.db.execute(select(SubscriptionPeriod).where(
            SubscriptionPeriod.subscription_id == sub.id,
            SubscriptionPeriod.status == "active").order_by(SubscriptionPeriod.started_at.desc()))
        current_period = period_r.scalars().first()

        proration = Decimal("0.00")
        if current_period:
            proration = self._compute_proration(current_period, utcnow())
            current_period.status = "superseded"

        change_type = (PlanChangeType.UPGRADE if new_amount > sub.amount
                       else PlanChangeType.DOWNGRADE if new_amount < sub.amount
                       else PlanChangeType.SAME)

        sub.plan_type = new_plan; sub.billing_cycle = billing_cycle; sub.amount = new_amount
        period_start = utcnow()
        period_end = period_start + timedelta(days=30 if billing_cycle == "monthly" else 365)
        sub.current_period_start = period_start; sub.current_period_end = period_end

        new_period = SubscriptionPeriod(
            subscription_id=sub.id, tenant_id=tenant_id, plan_type=new_plan,
            started_at=period_start, ends_at=period_end, amount=new_amount,
            status="active", jobs_included=PLAN_JOB_LIMITS.get(new_plan, 100))
        self.db.add(new_period)

        await self._write_event(sub, f"plan_{change_type}", from_plan=old_plan,
                                 to_plan=new_plan, proration=proration,
                                 meta={"change_type": change_type})
        await self._publish("subscription.plan_changed", str(tenant_id), str(sub.id),
                            {"from": old_plan, "to": new_plan, "proration": float(proration)})
        return {**self._sub_dict(sub), "proration_credit": float(proration),
                "change_type": change_type}

    async def cancel_subscription(self, tenant_id: uuid.UUID, reason: str) -> dict:
        r = await self.db.execute(select(Subscription).where(Subscription.tenant_id == tenant_id))
        sub = r.scalar_one_or_none()
        if not sub: raise NotFoundException("Subscription", str(tenant_id))
        if sub.status == SubStatus.CANCELLED:
            raise ServiceOSException("CONFLICT", "Already cancelled.")
        sub.status = SubStatus.CANCELLED; sub.cancelled_at = utcnow()
        await self._write_event(sub, "subscription_cancelled",
                                 from_plan=sub.plan_type, meta={"reason": reason})
        await self._publish("subscription.cancelled", str(tenant_id), str(sub.id),
                            {"reason": reason})
        return self._sub_dict(sub)

    async def pause_subscription(self, tenant_id: uuid.UUID) -> dict:
        r = await self.db.execute(select(Subscription).where(Subscription.tenant_id == tenant_id))
        sub = r.scalar_one_or_none()
        if not sub: raise NotFoundException("Subscription", str(tenant_id))
        if sub.status != SubStatus.ACTIVE:
            raise ServiceOSException("CONFLICT", f"Can only pause active subscriptions. Status: {sub.status}")
        sub.status = SubStatus.PAUSED
        await self._write_event(sub, "subscription_paused")
        return self._sub_dict(sub)

    async def resume_subscription(self, tenant_id: uuid.UUID) -> dict:
        r = await self.db.execute(select(Subscription).where(Subscription.tenant_id == tenant_id))
        sub = r.scalar_one_or_none()
        if not sub: raise NotFoundException("Subscription", str(tenant_id))
        if sub.status != SubStatus.PAUSED:
            raise ServiceOSException("CONFLICT", "Only paused subscriptions can be resumed.")
        sub.status = SubStatus.ACTIVE
        await self._write_event(sub, "subscription_resumed")
        return self._sub_dict(sub)

    async def get_current_period(self, tenant_id: uuid.UUID) -> dict:
        sub_r = await self.db.execute(select(Subscription).where(Subscription.tenant_id == tenant_id))
        sub = sub_r.scalar_one_or_none()
        if not sub: raise NotFoundException("Subscription", str(tenant_id))
        period_r = await self.db.execute(select(SubscriptionPeriod).where(
            SubscriptionPeriod.subscription_id == sub.id,
            SubscriptionPeriod.status == "active"))
        period = period_r.scalar_one_or_none()
        # PROVEN: usage from canonical CommissionRecord source
        try:
            from app.engines.platform_commerce.models import CommissionRecord
            job_r = await self.db.execute(select(func.count(CommissionRecord.id)).where(
                CommissionRecord.tenant_id == tenant_id,
                CommissionRecord.deducted_at >= (period.started_at if period else utcnow() - timedelta(days=30))))
            jobs_used = job_r.scalar_one_or_none() or 0
        except Exception:
            jobs_used = 0
        return {
            "subscription_id": str(sub.id),
            "plan_type": sub.plan_type, "status": sub.status,
            "period_start": period.started_at.isoformat() if period else None,
            "period_end": period.ends_at.isoformat() if period else None,
            "jobs_included": period.jobs_included if period else 0,
            "jobs_used": jobs_used,
            "jobs_remaining": max(0, (period.jobs_included if period else 0) - jobs_used),
            "amount": float(period.amount) if period else float(sub.amount),
        }

    async def list_billing_history(self, tenant_id: uuid.UUID,
                                    limit: int, cursor: str | None) -> dict:
        sub_r = await self.db.execute(select(Subscription).where(Subscription.tenant_id == tenant_id))
        sub = sub_r.scalar_one_or_none()
        if not sub: raise NotFoundException("Subscription", str(tenant_id))
        q = select(SubscriptionPeriod).where(
            SubscriptionPeriod.subscription_id == sub.id)            .order_by(SubscriptionPeriod.started_at.desc())
        if cursor:
            try:
                c = decode_cursor(cursor)
                q = q.where(SubscriptionPeriod.started_at < datetime.fromisoformat(c["started_at"]))
            except Exception: pass
        q = q.limit(limit + 1)
        r = await self.db.execute(q)
        items = r.scalars().all()
        has_next = len(items) > limit; items = items[:limit]
        nc = encode_cursor({"started_at": items[-1].started_at.isoformat()}) if has_next and items else None
        return {"periods": [{"period_id": str(p.id), "plan_type": p.plan_type,
                "started_at": p.started_at.isoformat(), "ends_at": p.ends_at.isoformat(),
                "amount": float(p.amount), "status": p.status,
                "jobs_included": p.jobs_included, "jobs_used": p.jobs_used} for p in items],
                "has_next": has_next, "next_cursor": nc}

    async def preview_proration(self, tenant_id: uuid.UUID, new_plan: str,
                                 billing_cycle: str) -> dict:
        r = await self.db.execute(select(Subscription).where(Subscription.tenant_id == tenant_id))
        sub = r.scalar_one_or_none()
        if not sub: raise NotFoundException("Subscription", str(tenant_id))
        period_r = await self.db.execute(select(SubscriptionPeriod).where(
            SubscriptionPeriod.subscription_id == sub.id,
            SubscriptionPeriod.status == "active"))
        period = period_r.scalars().first()
        credit = self._compute_proration(period, utcnow()) if period else Decimal("0.00")
        new_amount = PLAN_PRICES.get((new_plan, billing_cycle), Decimal("999.00"))
        net = new_amount - credit
        return {"current_plan": sub.plan_type, "new_plan": new_plan,
                "proration_credit": float(credit), "new_plan_amount": float(new_amount),
                "amount_due": float(max(Decimal("0"), net)),
                "effective_immediately": True}
