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


# ── Artwork Meta cannot fetch ────────────────────────────────────────────────
#
# Every check above is URL syntax, and syntax is not enough: Meta fetches the
# picture itself, renders a blank card when that fails, and still answers the
# send with 200. These cover the fetch-time verdict that replaces such a URL
# before it is sent.

IG_CONFIG = {"access_token": "ig-token", "instagram_account_id": "17890001",
             "api_version": "v26.0"}


def _capture_sends(monkeypatch):
    """Record the outbound Meta payloads instead of posting them."""
    import json

    from app.engines.messaging_gateway import meta_client

    sent = []

    class Response:
        status_code = 200
        text = json.dumps({"id": "sent"})

    class Client:
        def __init__(self, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def post(self, url, **kwargs):
            sent.append(kwargs["json"])
            return Response()

    monkeypatch.setattr(meta_client.httpx, "AsyncClient", Client)
    return sent


async def _send_carousel(rows):
    from app.engines.messaging_gateway import meta_client

    return await meta_client.send_options(
        "igsid-1", "Which service?", rows,
        channel=CHANNEL_INSTAGRAM, config=IG_CONFIG, presentation="carousel",
    )


@pytest.mark.asyncio
async def test_reachable_artwork_is_sent_unchanged(monkeypatch, verify_card_artwork):
    sent = _capture_sends(monkeypatch)
    art = "https://res.cloudinary.com/demo/image/upload/v1/catalog/ac.png"
    normalized = instagram_card_image_url(art, fallback_name="AC Repair")
    verify_card_artwork[normalized] = (200, "image/png")

    await _send_carousel([{"id": "of|ac", "title": "AC Repair", "image_url": art}])

    element = sent[0]["message"]["attachment"]["payload"]["elements"][0]
    assert element["image_url"] == normalized


@pytest.mark.asyncio
async def test_artwork_that_404s_falls_back_to_the_bundled_card(
    monkeypatch, verify_card_artwork,
):
    """Seen live: a catalog icon saved one extension short of its Cloudinary
    delivery id. The URL is faultless public https and answers 404, so the
    card rendered blank with nothing in any log."""
    sent = _capture_sends(monkeypatch)
    missing = "https://res.cloudinary.com/dr1b4ezct/image/upload/v1/gone.webp"
    verify_card_artwork[HOSTED_LEAK] = (200, "image/jpeg")

    await _send_carousel([
        {"id": "pb|1", "title": "Water leakage", "image_url": missing},
    ])

    element = sent[0]["message"]["attachment"]["payload"]["elements"][0]
    assert element["image_url"] == HOSTED_LEAK


@pytest.mark.asyncio
async def test_an_svg_icon_is_replaced_even_though_it_loads(
    monkeypatch, verify_card_artwork,
):
    """Instagram renders no SVG in a template. A 200 is not enough."""
    sent = _capture_sends(monkeypatch)
    art = "https://cdn.example/icons/leak.svg"
    verify_card_artwork[art] = (200, "image/svg+xml")
    verify_card_artwork[HOSTED_LEAK] = (200, "image/jpeg")

    await _send_carousel([
        {"id": "pb|1", "title": "Water leakage", "image_url": art},
    ])

    element = sent[0]["message"]["attachment"]["payload"]["elements"][0]
    assert element["image_url"] == HOSTED_LEAK


@pytest.mark.asyncio
async def test_a_card_with_no_working_artwork_is_sent_without_a_picture(
    monkeypatch, verify_card_artwork,
):
    """Nothing in the ladder answers, so the element goes out with its title,
    subtitle and button and no image field — Meta then lays it out as a text
    card instead of reserving an empty grey panel."""
    sent = _capture_sends(monkeypatch)

    await _send_carousel([
        {"id": "pb|1", "title": "Water leakage",
         "image_url": "https://cdn.example/leak.png"},
    ])

    element = sent[0]["message"]["attachment"]["payload"]["elements"][0]
    assert "image_url" not in element
    assert element["title"] == "Water leakage"
    assert element["buttons"][0]["payload"] == "pb|1"


@pytest.mark.asyncio
async def test_one_bad_card_does_not_disturb_the_others(
    monkeypatch, verify_card_artwork,
):
    sent = _capture_sends(monkeypatch)
    good = "https://res.cloudinary.com/demo/image/upload/v1/catalog/ac.png"
    normalized = instagram_card_image_url(good, fallback_name="AC Repair")
    verify_card_artwork[normalized] = (200, "image/png")
    verify_card_artwork[HOSTED_LEAK] = (200, "image/jpeg")

    await _send_carousel([
        {"id": "of|ac", "title": "AC Repair", "image_url": good},
        {"id": "pb|1", "title": "Water leakage",
         "image_url": "https://cdn.example/dead.png"},
    ])

    elements = sent[0]["message"]["attachment"]["payload"]["elements"]
    assert [e["image_url"] for e in elements] == [normalized, HOSTED_LEAK]


@pytest.mark.asyncio
async def test_a_verdict_is_reused_rather_than_refetched(
    monkeypatch, verify_card_artwork,
):
    """The same handful of cards is sent to every customer all day. Checking
    each URL once per carousel would add a round trip to every reply."""
    sent = _capture_sends(monkeypatch)
    art = "https://res.cloudinary.com/demo/image/upload/v1/catalog/ac.png"
    normalized = instagram_card_image_url(art, fallback_name="AC Repair")
    verify_card_artwork[normalized] = (200, "image/png")

    rows = [{"id": "of|ac", "title": "AC Repair", "image_url": art}]
    await _send_carousel(rows)
    await _send_carousel(rows)

    assert verify_card_artwork.fetched == [normalized]
    assert len(sent) == 2


@pytest.mark.asyncio
async def test_the_tracking_status_card_is_checked_too(
    monkeypatch, verify_card_artwork,
):
    sent = _capture_sends(monkeypatch)
    verify_card_artwork[HOSTED_LEAK] = (200, "image/jpeg")

    from app.engines.messaging_gateway import meta_client

    await meta_client.send_options(
        "igsid-1", "Your booking is with us.",
        [{"id": "tr|BK-1", "title": "Refresh status"}],
        channel=CHANNEL_INSTAGRAM, config=IG_CONFIG, presentation="status_card",
        card={"title": "Water leakage · Assigned", "subtitle": "Assigned",
              "image_url": "https://cdn.example/technician.jpg"},
    )

    card = sent[0]["message"]["attachment"]["payload"]["elements"][0]
    assert card["image_url"] == HOSTED_LEAK


@pytest.mark.asyncio
async def test_verification_off_sends_the_url_unchecked(monkeypatch):
    """The `offline_card_artwork` default: with the budget at zero nothing is
    fetched and the previous behaviour is kept exactly."""
    sent = _capture_sends(monkeypatch)
    art = "https://res.cloudinary.com/demo/image/upload/v1/catalog/ac.png"

    await _send_carousel([{"id": "of|ac", "title": "AC Repair", "image_url": art}])

    element = sent[0]["message"]["attachment"]["payload"]["elements"][0]
    assert element["image_url"] == instagram_card_image_url(
        art, fallback_name="AC Repair",
    )


@pytest.mark.asyncio
async def test_a_slow_host_does_not_hold_up_the_reply(monkeypatch, verify_card_artwork):
    """The whole carousel shares one budget. A host that never answers must
    cost that budget once and then get our own card, not stall the chat."""
    import asyncio

    from app.config import get_settings
    from app.engines.messaging_gateway import problem_cards

    sent = _capture_sends(monkeypatch)
    monkeypatch.setattr(get_settings(), "INSTAGRAM_CARD_VERIFY_TIMEOUT_SECONDS", 0.2)

    class Stalling:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def get(self, url, **kwargs):
            await asyncio.sleep(30)

    monkeypatch.setattr(problem_cards, "_artwork_client", lambda timeout: Stalling())

    started = asyncio.get_running_loop().time()
    await _send_carousel([
        {"id": "pb|1", "title": "Water leakage",
         "image_url": "https://cdn.example/slow.png"},
    ])
    elapsed = asyncio.get_running_loop().time() - started

    assert elapsed < 5
    element = sent[0]["message"]["attachment"]["payload"]["elements"][0]
    assert element["image_url"] == HOSTED_LEAK
