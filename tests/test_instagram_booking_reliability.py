"""Regressions for ZIP-first booking and reliable Instagram artwork."""
from unittest.mock import AsyncMock

import pytest

from app.engines.messaging_gateway.constants import CHANNEL_INSTAGRAM
from app.engines.messaging_gateway.problem_cards import (
    DEFAULT_CARD_BASE_URL,
    INSTAGRAM_CARD_TRANSFORMATION,
    instagram_card_image_url,
)

# The hosted card, padded square for Meta.
HOSTED_LEAK = (
    "https://res.cloudinary.com/dr1b4ezct/image/upload/"
    f"{INSTAGRAM_CARD_TRANSFORMATION}/serviceos/social-problem-cards/leak.png"
)


def test_cloudinary_artwork_is_normalized_for_meta():
    original = "https://res.cloudinary.com/demo/image/upload/v123/catalog/large.webp"

    normalized = instagram_card_image_url(original, fallback_name="AC not cooling")

    assert f"/image/upload/{INSTAGRAM_CARD_TRANSFORMATION}/v123/" in normalized
    assert normalized.endswith("large.webp")


def test_old_cropped_card_url_is_replaced_with_padding():
    original = (
        "https://res.cloudinary.com/demo/image/upload/"
        "c_fill,g_auto,h_960,w_960,q_auto:good,f_jpg/v123/catalog/logo.png"
    )
    normalized = instagram_card_image_url(original, fallback_name="Logo")
    assert f"/image/upload/{INSTAGRAM_CARD_TRANSFORMATION}/v123/" in normalized
    assert "c_fill" not in normalized


def test_missing_artwork_gets_a_public_https_fallback():
    """Seen live: the fallback pointed at api.fuvay.in, which is routed to
    Vercel and answers 404, so every card without its own picture rendered
    blank. The same PNGs are hosted on Cloudinary and fetch fine."""
    assert instagram_card_image_url(None, fallback_name="Water leakage") == HOSTED_LEAK
    assert DEFAULT_CARD_BASE_URL.startswith("https://res.cloudinary.com/")


@pytest.mark.parametrize("url", [
    "http://192.168.1.9:8000/uploads/card.png",
    "https://192.168.1.9/uploads/card.png",
    "https://localhost/uploads/card.png",
    "https://",
    "https://cdn.example/has a space.png",
])
def test_unfetchable_artwork_uses_the_bundled_png(url):
    assert instagram_card_image_url(url, fallback_name="Water leakage") == HOSTED_LEAK


def test_a_saved_cropped_card_url_is_rebuilt_with_padding():
    """Old picker/booking context can carry the card with the c_fill crop."""
    old = (
        "https://res.cloudinary.com/dr1b4ezct/image/upload/"
        "c_fill,g_auto,h_960,w_960,q_auto:good,f_jpg/"
        "serviceos/social-problem-cards/leak.png"
    )
    assert instagram_card_image_url(old, fallback_name="Booking status") == HOSTED_LEAK


@pytest.mark.parametrize("override", [
    "http://129.121.137.155:8000/assets/social-problem-cards",
    "https://localhost/assets/social-problem-cards",
    "",
])
def test_a_card_host_meta_cannot_reach_falls_back_to_the_hosted_copy(monkeypatch, override):
    from app.engines.messaging_gateway import problem_cards

    monkeypatch.setattr(problem_cards, "get_settings",
                        lambda: type("S", (), {"INSTAGRAM_CARD_PUBLIC_BASE_URL": override})())
    assert instagram_card_image_url(None, fallback_name="Water leakage") == HOSTED_LEAK


def test_a_public_https_card_host_is_honoured(monkeypatch):
    from app.engines.messaging_gateway import problem_cards

    monkeypatch.setattr(problem_cards, "get_settings", lambda: type("S", (), {
        "INSTAGRAM_CARD_PUBLIC_BASE_URL": "https://cards.example.com/art/",
    })())
    assert problem_cards.problem_card_image("Water leakage") == (
        "https://cards.example.com/art/leak.png"
    )


def test_bundled_instagram_card_is_served_as_png():
    from fastapi.testclient import TestClient
    from app.main import create_app

    response = TestClient(create_app()).get("/assets/social-problem-cards/leak.png")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert response.content.startswith(b"\x89PNG\r\n\x1a\n")


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
