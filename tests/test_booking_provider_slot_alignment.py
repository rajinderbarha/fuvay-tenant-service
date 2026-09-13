"""Provider selection and customer slot picking share one availability truth."""

import uuid

import pytest


def test_matching_requires_the_exact_customer_selected_slot():
    from app.engines.home_service_booking.matching_engine import _select_matching_slot

    slots = [
        {"date": "2026-09-15", "time_window": "09:00-11:00"},
        {"date": "2026-09-15", "time_window": "11:00-13:00"},
    ]

    assert _select_matching_slot(
        slots, "2026-09-15T09:00", "09:00-11:00",
    ) == slots[0]
    assert _select_matching_slot(
        slots, "2026-09-15T10:00", "10:00-12:00",
    ) is None


def test_requested_timestamp_without_window_still_requires_exact_capacity():
    from app.engines.home_service_booking.matching_engine import _select_matching_slot

    slots = [
        {
            "date": "2026-09-15",
            "time_window": "11:00-13:00",
            "starts_at": "2026-09-15T11:00:00",
        },
    ]
    assert _select_matching_slot(slots, "2026-09-15T11:00", None) == slots[0]
    assert _select_matching_slot(slots, "2026-09-15T09:00", None) is None


def test_matching_without_a_prior_choice_uses_first_live_picker_slot():
    from app.engines.home_service_booking.matching_engine import _select_matching_slot

    slots = [{"date": "2026-09-15", "time_window": "11:00-13:00"}]
    assert _select_matching_slot(slots, None, None) == slots[0]
    assert _select_matching_slot([], None, None) is None


@pytest.mark.asyncio
async def test_picker_only_calls_explicit_capacity_failure_slot_unavailable(monkeypatch):
    from app.engines.home_service_booking import service as booking_service
    from app.engines.messaging_gateway import pickers

    class FullSlotService:
        async def select_promised_slot(self, **_kwargs):
            raise ValueError("SLOT_NO_LONGER_AVAILABLE")

    monkeypatch.setattr(
        booking_service, "HomeServiceChatbotBookingService",
        lambda _db: FullSlotService(),
    )
    result = await pickers._apply_slot(
        None, uuid.uuid4(), None, "2026-09-15", "09:00-11:00",
    )
    assert result["applied"] is False
    assert "just been taken" in result["note"]


@pytest.mark.asyncio
async def test_picker_does_not_misreport_backend_failure_as_full_slot(monkeypatch):
    from app.engines.home_service_booking import service as booking_service
    from app.engines.messaging_gateway import pickers

    class BrokenService:
        async def select_promised_slot(self, **_kwargs):
            raise RuntimeError("temporary database failure")

    monkeypatch.setattr(
        booking_service, "HomeServiceChatbotBookingService",
        lambda _db: BrokenService(),
    )
    result = await pickers._apply_slot(
        None, uuid.uuid4(), None, "2026-09-15", "09:00-11:00",
    )
    assert result["applied"] is False
    assert "try again" in result["note"].lower()
    assert "taken" not in result["note"].lower()
