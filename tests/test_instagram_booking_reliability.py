"""Regressions for ZIP-first booking and reliable Instagram artwork."""
from unittest.mock import AsyncMock

import pytest

from app.engines.messaging_gateway.constants import CHANNEL_INSTAGRAM
from app.engines.messaging_gateway.problem_cards import (
    INSTAGRAM_CARD_TRANSFORMATION,
    instagram_card_image_url,
)


def test_cloudinary_artwork_is_normalized_for_meta():
    original = "https://res.cloudinary.com/demo/image/upload/v123/catalog/large.webp"

    normalized = instagram_card_image_url(original, fallback_name="AC not cooling")

    assert f"/image/upload/{INSTAGRAM_CARD_TRANSFORMATION}/v123/" in normalized
    assert normalized.endswith("large.webp")


def test_missing_artwork_gets_a_public_https_fallback():
    assert instagram_card_image_url(None, fallback_name="Water leakage").startswith(
        "https://res.cloudinary.com/"
    )


@pytest.mark.asyncio
async def test_provider_and_slots_are_checked_before_street_address(monkeypatch):
    from app.engines.messaging_gateway import flow

    class Thread:
        customer_id = None
        zipcode = "140412"
        city = "Bassi Pathana"
        channel = CHANNEL_INSTAGRAM

    draft = {
        "id": "draft-1",
        "job_type_id": "job-type-1",
        "selected_tenant_id": None,
        "address_snapshot": {},
    }
    monkeypatch.setattr(flow.pickers, "build_picker", AsyncMock(return_value=None))
    match = AsyncMock(return_value=flow.Turn("provider checked"))
    monkeypatch.setattr(flow, "_match_step", match)
    coverage = AsyncMock(return_value=[object()])
    monkeypatch.setattr(flow, "_serviceable_categories", coverage)

    turn = await flow._next_step(
        None, Thread(), object(), draft, CHANNEL_INSTAGRAM, 0,
    )

    assert turn.text == "provider checked"
    match.assert_awaited_once()
    coverage.assert_not_awaited()


@pytest.mark.asyncio
async def test_street_address_is_requested_after_provider_and_slot_exist(monkeypatch):
    from app.engines.messaging_gateway import flow

    class Thread:
        customer_id = None
        zipcode = "140412"
        city = "Bassi Pathana"
        channel = CHANNEL_INSTAGRAM

    draft = {
        "id": "draft-1",
        "job_type_id": "job-type-1",
        "selected_tenant_id": "tenant-1",
        "preferred_date": "2026-09-20",
        "preferred_time_window": "10:00-12:00",
        "address_snapshot": {},
    }
    monkeypatch.setattr(flow.pickers, "build_picker", AsyncMock(return_value=None))
    coverage = AsyncMock(return_value=[object()])
    monkeypatch.setattr(flow, "_serviceable_categories", coverage)

    turn = await flow._next_step(
        None, Thread(), object(), draft, CHANNEL_INSTAGRAM, 0,
    )

    assert turn.text == flow.ASK_ADDRESS
    # ZIP coverage was already settled before this draft was created. The
    # address stage must not cause another broad availability lookup.
    coverage.assert_not_awaited()
