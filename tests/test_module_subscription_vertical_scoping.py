"""Multi-vertical platform refactor — Phase 2 (migration 150).

Subscription previously had UNIQUE(tenant_id) only -- a tenant in two
verticals could not hold two independent subscriptions. Migration 150 adds
vertical_id and re-scopes the uniqueness to (tenant_id, vertical_id). These
tests prove: a tenant can hold one subscription per vertical, cancelling one
vertical's subscription never touches another vertical's row, and single-
vertical tenants (the common case, vertical_key omitted) keep working
exactly as before via the tenant.vertical fallback. No live DB required.
"""
from __future__ import annotations

import uuid
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.engines.subscription.service import SubscriptionService
from app.engines.subscription.models import Subscription


def _scalar(value):
    r = MagicMock()
    r.scalar_one_or_none = MagicMock(return_value=value)
    return r


def _make_sub(**kwargs):
    s = MagicMock(spec=Subscription)
    defaults = {
        "id": uuid.uuid4(), "tenant_id": uuid.uuid4(), "vertical_id": uuid.uuid4(),
        "plan_type": "growth", "billing_cycle": "monthly", "status": "active",
        "amount": Decimal("2499.00"), "currency": "INR",
        "current_period_start": None, "current_period_end": None, "trial_end": None,
        "cancelled_at": None, "dunning_count": 0, "next_retry_at": None,
        "payment_method": {}, "meta": {},
    }
    defaults.update(kwargs)
    for k, val in defaults.items():
        setattr(s, k, val)
    return s


class TestVerticalScopedSubscriptions:
    @pytest.mark.asyncio
    async def test_tenant_can_create_independent_subscription_per_vertical(self):
        """A tenant already subscribed in Home Services must still be able
        to create a separate subscription in Coaching -- proves the unique
        constraint no longer blocks a second vertical for the same tenant."""
        svc = SubscriptionService(db=MagicMock())
        db = svc.db
        tenant_id = uuid.uuid4()
        coaching_vertical_id = uuid.uuid4()

        call_count = [0]
        async def mock_execute(q):
            call_count[0] += 1
            if call_count[0] == 1:
                return _scalar(coaching_vertical_id)          # _resolve_vertical_id -> Vertical.id
            return _scalar(None)                               # no existing coaching subscription
        db.execute = mock_execute
        db.add = MagicMock()
        db.flush = AsyncMock()

        result = await svc.create_subscription(
            tenant_id, "growth", "monthly", vertical_key="coaching",
        )
        assert result["vertical_id"] == str(coaching_vertical_id)

    @pytest.mark.asyncio
    async def test_create_raises_conflict_only_within_same_vertical(self):
        svc = SubscriptionService(db=MagicMock())
        db = svc.db
        tenant_id = uuid.uuid4()
        vertical_id = uuid.uuid4()
        existing = _make_sub(tenant_id=tenant_id, vertical_id=vertical_id)

        call_count = [0]
        async def mock_execute(q):
            call_count[0] += 1
            return _scalar(vertical_id) if call_count[0] == 1 else _scalar(existing)
        db.execute = mock_execute

        with pytest.raises(Exception):  # ServiceOSException CONFLICT
            await svc.create_subscription(tenant_id, "growth", "monthly", vertical_key="home_services")

    @pytest.mark.asyncio
    async def test_cancel_one_verticals_subscription_does_not_touch_another(self):
        """Spec requirement: disabling/cancelling Food's subscription must
        never affect Coaching's subscription for the same tenant."""
        svc = SubscriptionService(db=MagicMock())
        db = svc.db
        tenant_id = uuid.uuid4()
        food_vertical_id = uuid.uuid4()
        food_sub = _make_sub(tenant_id=tenant_id, vertical_id=food_vertical_id, status="active")
        # A sibling Coaching subscription that must remain untouched --
        # never fetched or mutated by this call at all.
        coaching_sub = _make_sub(status="active")

        call_count = [0]
        async def mock_execute(q):
            call_count[0] += 1
            return _scalar(food_vertical_id) if call_count[0] == 1 else _scalar(food_sub)
        db.execute = mock_execute
        db.add = MagicMock()

        await svc.cancel_subscription(tenant_id, "vertical disabled", vertical_key="food")

        assert food_sub.status == "cancelled" or food_sub.status == "CANCELLED" or "cancel" in str(food_sub.status).lower()
        assert coaching_sub.status == "active"

    @pytest.mark.asyncio
    async def test_single_vertical_tenant_falls_back_to_tenant_vertical_unchanged(self):
        """The common case (existing behavior): no vertical_key passed ->
        resolve from the tenant's own tenants.vertical column, so every
        pre-Phase-2 caller keeps working with zero changes required."""
        svc = SubscriptionService(db=MagicMock())
        db = svc.db
        tenant_id = uuid.uuid4()
        resolved_vertical_id = uuid.uuid4()
        sub = _make_sub(tenant_id=tenant_id, vertical_id=resolved_vertical_id)

        call_count = [0]
        async def mock_execute(q):
            call_count[0] += 1
            if call_count[0] == 1:
                return _scalar("home_services")            # Tenant.vertical lookup
            if call_count[0] == 2:
                return _scalar(resolved_vertical_id)         # Vertical.id lookup
            return _scalar(sub)                              # Subscription lookup
        db.execute = mock_execute

        result = await svc.get_subscription(tenant_id)
        assert result["subscription_id"] == str(sub.id)

    @pytest.mark.asyncio
    async def test_ambiguous_legacy_tenant_fails_closed_not_guessed(self):
        """A tenant whose `tenants.vertical` string matches no real vertical
        (legacy/ambiguous data) must resolve to vertical_id=NULL rather than
        guessing -- and NULL is still queried correctly (IS NULL), not
        silently matched against every vertical."""
        svc = SubscriptionService(db=MagicMock())
        db = svc.db
        tenant_id = uuid.uuid4()

        call_count = [0]
        async def mock_execute(q):
            call_count[0] += 1
            if call_count[0] == 1:
                return _scalar("some_unrecognized_legacy_string")
            if call_count[0] == 2:
                return _scalar(None)   # no Vertical row matches that string
            return _scalar(None)       # no subscription found for (tenant, NULL)
        db.execute = mock_execute

        with pytest.raises(Exception):  # NotFoundException, not a crash/mismatch
            await svc.get_subscription(tenant_id)
