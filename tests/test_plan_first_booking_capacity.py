"""Plan-first onboarding capacity: real resolver behavior, without live fixtures."""
import datetime as dt
import uuid
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.engines.home_service_booking import provider_slot_service as slots
from app.engines.vertical_catalog import activation_payment_service as payments
from app.exceptions import ServiceOSException


def test_eight_hours_make_four_two_hour_windows_even_for_legacy_rules():
    rule = {"start_time": "09:00", "end_time": "17:00", "slot_duration_minutes": 60}
    assert [slots._window_label(*w) for w in slots._slots_from_rule(rule)] == [
        "09:00-11:00", "11:00-13:00", "13:00-15:00", "15:00-17:00"]
    assert slots._daily_remaining([rule], 3, {}) == 12


def test_partial_windows_and_breaks_do_not_inflate_capacity():
    rule = {"start_time": "09:00", "end_time": "17:30", "break_start_time": "12:00", "break_end_time": "13:00"}
    assert [slots._window_label(*w) for w in slots._slots_from_rule(rule)] == ["09:00-11:00", "13:00-15:00", "15:00-17:00"]
    assert slots._daily_remaining([rule, rule], 3, {}) == 9


def test_provider_daily_limit_is_a_ceiling_not_extra_capacity():
    rule = {"start_time": "09:00", "end_time": "17:00", "max_jobs_per_day": 8}
    assert slots._daily_remaining([rule], 3, {"09:00-11:00": 3, "11:00-13:00": 3}) == 2
    assert slots._daily_remaining([rule], 0, {}) == 0
    assert slots._daily_remaining([{**rule, "max_jobs_per_day": 100}], 3, {}) == 12


@pytest.mark.asyncio
@pytest.mark.parametrize("booked,limit,allowed", [
    ({"09:00-11:00": 3}, None, False),
    ({"09:00-11:00": 2}, None, True),
    ({"11:00-13:00": 3}, 3, False),
    ({"10:00-12:00": 3}, None, False),
])
async def test_confirmation_enforces_simultaneous_and_daily_capacity(booked, limit, allowed):
    rule = {"start_time": "09:00", "end_time": "17:00", "max_jobs_per_day": limit}
    with patch.object(slots, "assignable_technician_count", new=AsyncMock(return_value=3)), \
         patch.object(slots, "_provider_rules_for_day", new=AsyncMock(return_value=[rule])), \
         patch.object(slots, "_is_closed", new=AsyncMock(return_value=False)), \
         patch.object(slots, "_booked_counts", new=AsyncMock(return_value=booked)):
        assert await slots.slot_has_capacity(MagicMock(), tenant_id=uuid.uuid4(), day=dt.date(2026, 9, 8), time_window="09:00-11:00") is allowed


@pytest.mark.asyncio
async def test_checkout_uses_selected_plan_even_when_old_plan_is_funded():
    tenant_id, plan_id = uuid.uuid4(), uuid.uuid4()
    selected = {"id": str(plan_id), "seats": 3, "credited_amount": 2000, "gst_amount": 360, "total_amount": 2360}
    quote = {"suggested_plan": {"id": str(uuid.uuid4())}, "available_plans": [selected], "total_due": 0, "checkout_mode": "funded"}
    query = MagicMock()
    query.scalar_one_or_none.return_value = None
    db = MagicMock(execute=AsyncMock(return_value=query), flush=AsyncMock(), commit=AsyncMock(), refresh=AsyncMock())
    with patch.object(payments, "_resolve_vertical_and_policy", new=AsyncMock(return_value=(MagicMock(id=uuid.uuid4()), MagicMock(version_number=1)))), \
         patch.object(payments, "resolve_activation_funding_quote", new=AsyncMock(return_value=quote)), \
         patch("app.integrations.razorpay_client.create_order", new=AsyncMock(return_value={"id": "order_selected", "amount": 236000, "currency": "INR"})):
        await payments.create_activation_funding_order(db, tenant_id, plan_id=plan_id)
    record = db.add.call_args.args[0]
    assert record.topup_plan_id == plan_id
    assert record.seats_granted == 3
    assert record.amount == Decimal("2360.00")


@pytest.mark.asyncio
async def test_checkout_rejects_a_plan_not_in_live_catalogue():
    db = MagicMock()
    with patch.object(payments, "_resolve_vertical_and_policy", new=AsyncMock(return_value=(None, None))), \
         patch.object(payments, "resolve_activation_funding_quote", new=AsyncMock(return_value={"available_plans": []})):
        with pytest.raises(ServiceOSException) as error:
            await payments.create_activation_funding_order(db, uuid.uuid4(), plan_id=uuid.uuid4())
    assert error.value.error_code == "TOPUP_PLAN_UNAVAILABLE"
    db.add.assert_not_called()
