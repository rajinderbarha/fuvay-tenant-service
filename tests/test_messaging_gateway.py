"""Focused contract tests for Meta social booking channels."""
from __future__ import annotations

import hashlib
import hmac
import json
import uuid
from datetime import datetime, timedelta, timezone

import pytest

from app.engines.ai_conversation.constants import BACKEND_TOOLS
from app.engines.ai_conversation.backend_tools import BackendToolExecutor
from app.engines.messaging_gateway import meta_client, pickers
from app.engines.messaging_gateway.constants import (
    CHANNEL_INSTAGRAM, CHANNEL_WHATSAPP, PICK_RESTART,
)
from app.engines.messaging_gateway.service import parse_command


def test_signature_can_use_admin_stored_secret():
    body = b'{"object":"instagram"}'
    signature = "sha256=" + hmac.new(b"stored-secret", body, hashlib.sha256).hexdigest()
    assert meta_client.verify_signature(body, signature, app_secret="stored-secret") is True
    assert meta_client.verify_signature(body, signature, app_secret="wrong-secret") is False


def test_parse_whatsapp_messages_and_skip_delivery_receipts():
    payload = {
        "object": "whatsapp_business_account",
        "entry": [{"id": "waba", "changes": [{"field": "messages", "value": {
            "metadata": {"phone_number_id": "10001"},
            "contacts": [{"wa_id": "919999999999", "profile": {"name": "Amit"}}],
            "messages": [{"id": "wamid.1", "from": "919999999999", "type": "text", "text": {"body": "AC not cooling"}}],
        }}, {"field": "messages", "value": {"statuses": [{"id": "wamid.1", "status": "read"}]}}]}],
    }
    messages = meta_client.parse_inbound(payload, expected_channel=CHANNEL_WHATSAPP)
    assert len(messages) == 1
    assert messages[0].channel == CHANNEL_WHATSAPP
    assert messages[0].business_id == "10001"
    assert messages[0].display_name == "Amit"
    assert messages[0].text == "AC not cooling"


def test_parse_instagram_text_postback_and_skip_echo():
    payload = {"object": "instagram", "entry": [{"id": "17890001", "messaging": [
        {"sender": {"id": "igsid-1"}, "recipient": {"id": "17890001"}, "timestamp": 1, "message": {"mid": "igmid-1", "text": "Book AC service"}},
        {"sender": {"id": "igsid-1"}, "recipient": {"id": "17890001"}, "timestamp": 2, "postback": {"mid": "igmid-2", "title": "Track booking", "payload": "TRACK"}},
        {"sender": {"id": "igsid-1"}, "recipient": {"id": "17890001"}, "timestamp": 3, "postback": {"mid": "igmid-ice", "title": "Book a home service", "payload": "/fuvay"}},
        {"sender": {"id": "17890001"}, "recipient": {"id": "igsid-1"}, "timestamp": 4, "message": {"mid": "igmid-3", "text": "echo", "is_echo": True}},
    ]}]}
    messages = meta_client.parse_inbound(payload, expected_channel=CHANNEL_INSTAGRAM)
    assert [(item.provider_message_id, item.text) for item in messages] == [
        ("igmid-1", "Book AC service"), ("igmid-2", "Track booking"),
        ("igmid-ice", "/fuvay"),
    ]
    assert messages[2].reply_id is None
    assert all(item.business_id == "17890001" for item in messages)


@pytest.mark.asyncio
async def test_channel_specific_outbound_payloads(monkeypatch):
    calls = []

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
            calls.append((url, kwargs["json"]))
            return Response()

    monkeypatch.setattr(meta_client.httpx, "AsyncClient", Client)
    await meta_client.send_text("919999999999", "Hello", channel=CHANNEL_WHATSAPP, config={
        "access_token": "wa-token", "phone_number_id": "10001", "api_version": "v26.0",
    })
    await meta_client.send_text("igsid-1", "Hello", channel=CHANNEL_INSTAGRAM, config={
        "access_token": "ig-token", "instagram_account_id": "17890001", "api_version": "v26.0",
    })
    assert calls[0][0] == "https://graph.facebook.com/v26.0/10001/messages"
    assert calls[0][1]["messaging_product"] == "whatsapp"
    assert calls[1][0] == "https://graph.instagram.com/v26.0/17890001/messages"
    assert calls[1][1] == {"recipient": {"id": "igsid-1"}, "message": {"text": "Hello"}}


def test_tracking_and_end_to_end_booking_tools_are_registered():
    names = {tool["function"]["name"] for tool in BACKEND_TOOLS}
    assert {
        "get_booking_tracking",
        "get_available_home_service_slots",
        "select_home_service_slot",
        "get_home_service_booking_summary",
        "confirm_home_service_booking",
    }.issubset(names)
    assert parse_command("/track") == "track"
    assert parse_command("/link +919876543210") == "link"
    assert parse_command("/verify 123456") == "verify"


@pytest.mark.asyncio
async def test_booking_confirmation_requires_exact_phrase():
    result = await BackendToolExecutor(db=None, customer_id=None)._tool_confirm_home_service_booking(
        "not-used", "yes please",
    )
    assert result == {
        "confirmed": False,
        "error": "Ask the customer to reply exactly CONFIRM BOOKING first.",
    }


def test_social_chat_requires_deliverable_address_but_native_app_does_not():
    draft = {
        "required_fields": ["issue_summary", "city"],
        "issue_summary": "AC not cooling",
        "city": "Ludhiana",
        "zipcode": "140001",
        "address_snapshot": None,
    }
    native = BackendToolExecutor(db=None, customer_id=None)
    whatsapp = BackendToolExecutor(db=None, customer_id=None, channel="whatsapp")
    assert native._still_needed(draft) == []
    assert whatsapp._still_needed(draft) == ["address_line_1"]


def test_update_draft_tool_accepts_complete_social_address():
    tool = next(item for item in BACKEND_TOOLS if item["function"]["name"] == "update_home_service_draft")
    fields = tool["function"]["parameters"]["properties"]
    assert {
        "address_line_1", "address_line_2", "landmark", "city",
        "state", "zipcode", "country",
    }.issubset(fields)


# ── In-chat pickers ──────────────────────────────────────────────────────────


def test_tapped_option_id_survives_parsing():
    """A tap must carry its option id: two brands can share a clipped label."""
    payload = {"object": "whatsapp_business_account", "entry": [{"id": "waba", "changes": [
        {"field": "messages", "value": {
            "metadata": {"phone_number_id": "10001"},
            "messages": [{"id": "wamid.2", "from": "919999999999", "type": "interactive",
                          "interactive": {"type": "list_reply", "list_reply": {
                              "id": "qf|q-1|opt-7", "title": "Split AC"}}}],
        }}]}]}
    msg = meta_client.parse_inbound(payload, expected_channel=CHANNEL_WHATSAPP)[0]
    assert msg.reply_id == "qf|q-1|opt-7"
    assert msg.text == "Split AC"
    assert pickers.is_picker_reply(msg.reply_id) is True
    assert pickers.is_picker_reply("SOME_TEMPLATE_BUTTON") is False


def test_instagram_quick_reply_payload_is_the_option_id():
    payload = {"object": "instagram", "entry": [{"id": "17890001", "messaging": [
        {"sender": {"id": "igsid-1"}, "recipient": {"id": "17890001"}, "timestamp": 1,
         "message": {"mid": "igmid-9", "text": "Window AC",
                     "quick_reply": {"payload": "qf|q-1|opt-8"}}},
    ]}]}
    msg = meta_client.parse_inbound(payload)[0]
    assert msg.reply_id == "qf|q-1|opt-8"


def test_pagination_reserves_a_row_for_show_more_and_one_for_starting_over():
    """Meta rejects an 11-row list outright, so a long list must page — and
    two of those ten rows are navigation: "Show more" and "Start over"."""
    rows = [{"id": f"qf|q|{i}", "title": f"Brand {i}"} for i in range(23)]
    first = pickers._paginate(rows, "Pick a brand", CHANNEL_WHATSAPP, 0,
                              kind="qf", list_button="Choose", section_title="Brands")
    assert len(first["rows"]) == 10
    assert [r["id"] for r in first["rows"][-2:]] == ["more|qf|1", "rs|1"]
    assert [r["title"] for r in first["rows"][:8]] == [f"Brand {i}" for i in range(8)]

    second = pickers._paginate(rows, "Pick a brand", CHANNEL_WHATSAPP, 1,
                               kind="qf", list_button="Choose", section_title="Brands")
    assert second["rows"][0]["title"] == "Brand 8"
    assert [r["id"] for r in second["rows"][-2:]] == ["more|qf|2", "rs|1"]

    last = pickers._paginate(rows, "Pick a brand", CHANNEL_WHATSAPP, 2,
                             kind="qf", list_button="Choose", section_title="Brands")
    assert [r["title"] for r in last["rows"][:-1]] == [f"Brand {i}" for i in range(16, 23)]
    assert last["rows"][-1]["id"] == "rs|1"
    assert all(not r["id"].startswith("more|") for r in last["rows"])


def test_short_option_sets_fit_on_one_page():
    rows = [{"id": "qf|q|a", "title": "Yes"}, {"id": "qf|q|b", "title": "No"}]
    page = pickers._paginate(rows, "Under warranty?", CHANNEL_WHATSAPP, 0,
                             kind="qf", list_button="Choose", section_title="Warranty")
    # Every list carries a way back, however short it is.
    assert [r["id"] for r in page["rows"]] == ["qf|q|a", "qf|q|b", "rs|1"]


@pytest.mark.asyncio
async def test_option_message_shapes_per_channel_and_size(monkeypatch):
    calls = []

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
            calls.append((url, kwargs["json"]))
            return Response()

    monkeypatch.setattr(meta_client.httpx, "AsyncClient", Client)
    wa = {"access_token": "wa-token", "phone_number_id": "10001", "api_version": "v26.0"}

    # Three or fewer options render as reply buttons.
    await meta_client.send_options("919999999999", "Under warranty?", [
        {"id": "qf|q|a", "title": "Yes"}, {"id": "qf|q|b", "title": "No"},
    ], channel=CHANNEL_WHATSAPP, config=wa)
    assert calls[0][1]["interactive"]["type"] == "button"
    assert calls[0][1]["interactive"]["action"]["buttons"][0]["reply"]["id"] == "qf|q|a"

    # More than three render as a list, and over-long titles are clipped to
    # Meta's 24 characters rather than rejected.
    await meta_client.send_options("919999999999", "Pick a brand", [
        {"id": f"qf|q|{i}", "title": "A brand with a very long marketing name"}
        for i in range(5)
    ], channel=CHANNEL_WHATSAPP, config=wa, list_button="Choose", section_title="Brands")
    section = calls[1][1]["interactive"]["action"]["sections"][0]
    assert calls[1][1]["interactive"]["type"] == "list"
    assert len(section["rows"]) == 5
    assert all(len(r["title"]) <= 24 for r in section["rows"])
    assert section["rows"][0]["id"] == "qf|q|0"

    # Instagram has no list message, and its quick replies render as one
    # horizontal strip that scrolls out of view — so options go out as a
    # numbered, stacked text list answered with a number.
    await meta_client.send_options("igsid-1", "Pick a brand", [
        {"id": "qf|q|a", "title": "LG"}, {"id": "qf|q|b", "title": "Samsung"},
        {"id": "qf|q|c", "title": "Voltas"}, {"id": "qf|q|d", "title": "Daikin"},
    ], channel=CHANNEL_INSTAGRAM, config={
        "access_token": "ig-token", "instagram_account_id": "17890001", "api_version": "v26.0",
    })
    message = calls[2][1]["message"]
    # Readable AND tappable: the numbered lines stack, the same options ride
    # along as quick replies carrying the id.
    assert message["text"] == "Pick a brand"
    assert [q["payload"] for q in message["quick_replies"]] == [
        "qf|q|a", "qf|q|b", "qf|q|c", "qf|q|d"]


@pytest.mark.asyncio
async def test_show_more_is_not_an_answer():
    """Paging must not spend an agent turn or touch the draft."""
    outcome = await pickers.apply_reply(None, "more|qf|2", {"id": "irrelevant"},
                                        customer_id=None)
    assert outcome == {"applied": False, "note": None, "page": 2}


# ── The scripted flow ────────────────────────────────────────────────────────


def test_no_model_is_reachable_from_the_flow():
    """The customer conversation must not depend on an LLM at all.

    `ai_conversation` is still imported for two non-conversational things —
    the session row a draft hangs off, and BackendToolExecutor's backend calls
    — but `AIConversationService.send_message`, the DeepSeek round trip, must
    not be called from the gateway any more.
    """
    from pathlib import Path

    engine = Path("app/engines/messaging_gateway")
    for module in ("service.py", "flow.py", "pickers.py"):
        source = (engine / module).read_text(encoding="utf-8")
        assert "send_message" not in source, f"{module} still talks to the agent"
        assert "deepseek" not in source.lower(), f"{module} references DeepSeek"


@pytest.mark.asyncio
async def test_category_tap_shows_that_category_and_pages_without_state():
    """A category records nothing, so its offering list must be rebuildable
    from the tap alone — including page two."""
    from app.engines.messaging_gateway import flow

    seen = {}

    class Executor:
        async def _tool_get_category_offerings(self, category_slug):
            seen["slug"] = category_slug
            return {"offerings": [
                {"slug": f"svc-{i}", "name": f"Service {i}", "description": None}
                for i in range(14)
            ]}

    turn = await flow._navigate(None, Executor(), "cat|home_services", None, None, CHANNEL_WHATSAPP)
    assert seen["slug"] == "home_services"
    assert turn.picker["rows"][0]["id"] == "of|home_services|svc-0"
    # The "Show more" row carries the category, or page two could not be built.
    assert [r["id"] for r in turn.picker["rows"][-2:]] == [
        "more|of|1|home_services", "rs|1"]

    turn2 = await flow._navigate(None, Executor(), "more|of|1|home_services", None, None,
                                 CHANNEL_WHATSAPP)
    assert turn2.picker["rows"][0]["id"] == "of|home_services|svc-8"


@pytest.mark.asyncio
async def test_the_area_is_settled_before_anything_else_and_stays_changeable():
    """The pincode is asked first and lives on the THREAD, because it is asked
    before a draft exists. A 6-digit number stays a pincode change until a
    provider is matched, so an uncovered area is never a dead end — and a new
    pincode re-asks the city, since it is a different place."""
    from app.engines.messaging_gateway import flow

    class Thread:
        zipcode = None
        city = None
        ai_session_id = None      # no draft exists yet
        customer_id = None

    class Executor:
        def __init__(self):
            self.applied = {}

        async def _tool_update_home_service_draft(self, draft_id, **fields):
            self.applied.update(fields)
            return {"updated": True}

    thread, executor = Thread(), Executor()

    async def _no_coverage_row(db, zipcode):
        return None                       # no covering area names a city

    flow._area_city, original_city = _no_coverage_row, flow._area_city

    # Nothing is typed onto a draft because there is no draft yet. The first
    # explicit question is the pincode, so a non-pincode answer is corrected.
    note, draft = await flow._apply_text(None, thread, executor, "not a pincode", None)
    assert note == flow.BAD_PINCODE and thread.zipcode is None
    note, draft = await flow._apply_text(None, thread, executor, "1234", None)
    assert note == flow.BAD_PINCODE

    await flow._apply_text(None, thread, executor, "141001", None)
    assert thread.zipcode == "141001"
    await flow._apply_text(None, thread, executor, "Ludhiana", None)
    assert thread.city == "Ludhiana"

    # No coverage there: a second pincode must be readable, and the city with
    # it, or the customer is stuck answering a question nobody is reading.
    await flow._apply_text(None, thread, executor, "140412", None)
    assert (thread.zipcode, thread.city) == ("140412", None)
    assert executor.applied == {}

    # Once a provider is matched to the area, a stray number is not a pincode.
    matched = {"id": "d-1", "selected_tenant_id": "t-1",
               "address_snapshot": {"address_line_1": "House 12"}}
    await flow._apply_text(None, thread, executor, "140406", matched)
    assert thread.zipcode == "140412"
    flow._area_city = original_city


@pytest.mark.asyncio
async def test_a_category_with_no_local_coverage_says_so_and_reoffers():
    """"Not available in your city" is a different answer from "nothing to
    book at all", and must leave the customer on the list that IS covered."""
    from app.engines.messaging_gateway import flow

    class Thread:
        zipcode = "140412"
        city = "Bassi Pathana"

    class Category:
        def __init__(self, slug, name):
            self.slug, self.name = slug, name

    class Executor:
        async def _tool_get_category_offerings(self, category_slug):
            return {"offerings": []}          # covered elsewhere, not here

    async def _categories(db, zipcode):
        return [Category("home_services", "Home Services")]

    original, flow._serviceable_categories = flow._serviceable_categories, _categories
    try:
        turn = await flow._offering_step(None, Executor(), "salon", CHANNEL_WHATSAPP, 0, Thread())
    finally:
        flow._serviceable_categories = original

    assert "not available in Bassi Pathana" in turn.text
    assert turn.picker["rows"][0]["id"] == "cat|home_services"


@pytest.mark.asyncio
async def test_instagram_offering_step_uses_catalog_cards_without_guessing_price():
    """Catalog cards use real service content but no pre-match price."""
    from app.engines.messaging_gateway import flow

    class Thread:
        zipcode = "140412"
        city = "Bassi Pathana"

    class Executor:
        async def _tool_get_category_offerings(self, category_slug):
            assert category_slug == "ac-services"
            return {"offerings": [{
                "slug": "ac-repair",
                "name": "AC Repair",
                "description": "Diagnosis and repair",
                "image_url": "https://cdn.example/ac.jpg",
            }]}

    turn = await flow._offering_step(
        None, Executor(), "ac-services", CHANNEL_INSTAGRAM, 0, Thread(),
    )

    assert turn.text == flow.ASK_OFFERING
    assert turn.picker["presentation"] == "carousel"
    assert turn.picker["rows"][0] == {
        "id": "of|ac-services|ac-repair",
        "title": "AC Repair",
        "description": "Diagnosis and repair",
        "image_url": "https://cdn.example/ac.jpg",
        "button_title": "Select service",
    }
    assert "price" not in turn.picker["rows"][0]


class _Category:
    """The fields `_category_step` reads off a ServiceCategory row."""

    def __init__(self, slug, name, image_url=None, icon_url=None, description=None):
        self.slug, self.name = slug, name
        self.image_url, self.icon_url = image_url, icon_url
        self.description = description


def test_instagram_category_step_shows_the_admins_uploaded_icon():
    """An icon set on a category in the admin catalog is what the customer
    sees against that option — the whole point of uploading one. Instagram
    can only carry a picture on a generic card, so the list becomes cards."""
    from app.engines.messaging_gateway import flow

    turn = flow._category_step(
        [_Category("air-conditioning", "Air Conditioning",
                   icon_url="https://cdn.example/ac-icon.png",
                   description="Repair, service and installation"),
         _Category("plumbing", "Plumbing")],
        CHANNEL_INSTAGRAM, 0,
    )

    assert turn.text == flow.ASK_CATEGORY   # cards carry no prompt of their own
    assert turn.picker["presentation"] == "carousel"
    assert turn.picker["rows"][0] == {
        "id": "cat|air-conditioning",
        "title": "Air Conditioning",
        "image_url": "https://cdn.example/ac-icon.png",
        "description": "Repair, service and installation",
        "button_title": "Select",
    }
    # A category with no artwork still renders, just without a picture.
    assert turn.picker["rows"][1]["image_url"] is None
    # And the navigation card says what it does rather than inheriting the
    # generic "choose this service" subtitle.
    assert turn.picker["rows"][-1]["id"].split("|", 1)[0] == PICK_RESTART
    assert turn.picker["rows"][-1]["description"] == "Begin again from the first question."


def test_category_image_is_preferred_over_icon_and_must_be_public():
    """Meta fetches the artwork itself, so a relative upload path or a plain
    -http host can never render — those stay the numbered list rather than
    becoming a carousel of blank cards."""
    from app.engines.messaging_gateway import flow

    both = flow._category_step(
        [_Category("air-conditioning", "Air Conditioning",
                   image_url="https://cdn.example/ac.jpg",
                   icon_url="https://cdn.example/ac-icon.png")],
        CHANNEL_INSTAGRAM, 0,
    )
    assert both.picker["rows"][0]["image_url"] == "https://cdn.example/ac.jpg"

    unreachable = flow._category_step(
        [_Category("air-conditioning", "Air Conditioning",
                   icon_url="/uploads/category_icon/ac.png")],
        CHANNEL_INSTAGRAM, 0,
    )
    assert unreachable.picker["presentation"] == "quick_replies"
    assert "image_url" not in unreachable.picker["rows"][0]


def test_whatsapp_category_list_is_unchanged_by_category_artwork():
    """WhatsApp list rows cannot carry a picture at all, so an icon upload
    must not quietly rewrite what WhatsApp customers already see."""
    from app.engines.messaging_gateway import flow

    turn = flow._category_step(
        [_Category("air-conditioning", "Air Conditioning",
                   image_url="https://cdn.example/ac.jpg", description="Cooling")],
        CHANNEL_WHATSAPP, 0,
    )

    assert turn.text is None
    assert turn.picker["presentation"] == "quick_replies"
    assert turn.picker["rows"][0] == {"id": "cat|air-conditioning",
                                      "title": "Air Conditioning"}


def test_category_page_leaves_room_for_a_prepended_track_row():
    """`_next_step` puts "Track my booking" in front of the categories for a
    customer mid-booking. Meta fails a whole message that runs one row over
    its cap, so the page has to be cut short enough to hold it."""
    from app.engines.messaging_gateway import flow
    from app.engines.messaging_gateway.pickers import channel_capacity

    categories = [_Category(f"c{i}", f"Category {i}") for i in range(20)]

    step = flow._category_step(categories, CHANNEL_WHATSAPP, 0, reserve=1)
    assert len(step.picker["rows"]) + 1 <= channel_capacity(CHANNEL_WHATSAPP)

    # Without the reservation the page fills the cap exactly, as before.
    unreserved = flow._category_step(categories, CHANNEL_WHATSAPP, 0)
    assert len(unreserved.picker["rows"]) == channel_capacity(CHANNEL_WHATSAPP)


@pytest.mark.asyncio
async def test_a_confirmed_booking_cannot_be_changed_by_tapping_an_old_message():
    """WhatsApp keeps every earlier message tappable. Once the booking exists a
    provider has been allocated, so an old slot or brand row must be refused
    with a reason — not silently applied, and not silently ignored either."""
    from app.engines.messaging_gateway import flow

    class Thread:
        ai_session_id = None
        customer_id = None

    confirmed = {"id": "d-1", "status": "confirmed",
                 "selected_tenant_id": "t-1", "job_type_id": "j-1"}

    note, page, _ = await flow._apply_tap(
        None, Thread(), None, "sl|2026-09-02|09:00-10:00", confirmed)
    assert page == flow.BOOKED              # terminal, and a booking exists
    assert "already confirmed" in note

    # And the same for any later turn, tapped or typed. With no way to ask
    # what is live (no identity), the menu offers only the thing that is
    # always true — booking something else.
    turn = await flow._next_step(None, Thread(), None, confirmed, CHANNEL_WHATSAPP, 0)
    assert "already confirmed" in turn.text
    assert [r["id"] for r in turn.picker["rows"]] == ["rs|1"]


@pytest.mark.asyncio
async def test_an_emergency_slot_is_recorded_as_one():
    """`select_promised_slot(emergency=True)` is what writes `is_emergency` and
    prices the surcharge, so the row the customer tapped has to carry which
    list it came from."""
    from app.engines.messaging_gateway import pickers

    slot = [{"date": "2026-09-01", "time_window": "09:00-10:00"}]
    rows = pickers._slot_rows(slot, emergency=True, section="Emergency +₹200",
                              note="+₹200")
    assert rows[0]["id"] == "sl|2026-09-01|09:00-10:00|e"
    # The row says what it costs and which group it belongs to.
    assert rows[0]["description"] == "+₹200"
    assert rows[0]["section"] == "Emergency +₹200"

    normal = pickers._slot_rows(slot, emergency=False, section="Standard slots")
    assert normal[0]["id"] == "sl|2026-09-01|09:00-10:00"
    assert normal[0]["description"] is None
    assert normal[0]["section"] == "Standard slots"

    captured = {}

    class Service:
        async def select_promised_slot(self, **kwargs):
            captured.update(kwargs)
            return {}

    import app.engines.home_service_booking.service as booking
    original = booking.HomeServiceChatbotBookingService
    booking.HomeServiceChatbotBookingService = lambda db: Service()
    try:
        out = await pickers.apply_reply(
            None, "sl|2026-09-01|09:00-10:00|e", {"id": str(uuid.uuid4())},
            customer_id=None)
    finally:
        booking.HomeServiceChatbotBookingService = original

    assert captured["emergency"] is True
    assert out["applied"] is True and "Emergency time selected" in out["note"]


@pytest.mark.asyncio
async def test_both_instagram_ids_for_one_account_are_accepted():
    """Instagram names the same account two ways — the app-scoped id the send
    API uses, and the professional-account id a webhook can arrive with.
    Matching only the first silently drops real messages."""
    from app.engines.messaging_gateway.config_service import messaging_channel_config_service as svc

    config = {"instagram_account_id": "27972467659071830",
              "alternate_business_ids": ["17841477924025554"]}

    async def _get(db, channel, require_enabled=False):
        return config

    original, svc.get = svc.get, _get
    try:
        assert await svc.accepts_business_id(None, CHANNEL_INSTAGRAM, "27972467659071830")
        assert await svc.accepts_business_id(None, CHANNEL_INSTAGRAM, "17841477924025554")
        assert not await svc.accepts_business_id(None, CHANNEL_INSTAGRAM, "99999999999")
        assert not await svc.accepts_business_id(None, CHANNEL_INSTAGRAM, None)
    finally:
        svc.get = original


def test_instagram_receipts_are_not_customer_messages():
    """Read/delivery receipts arrive on the same webhook with no `message`.

    Answering one sends a reply, which produces another receipt, which is
    answered again — an endless loop, seen live at ~1 message every 2.5s. The
    timestamp fallback made it worse: it gave every receipt a unique id, so
    the duplicate guard could never catch them either.
    """
    payload = {"object": "instagram", "entry": [{"id": "17841477924025554", "messaging": [
        {"read": {"mid": "ig-read-1"}, "sender": {"id": "1355726243215412"},
         "recipient": {"id": "17841477924025554"}, "timestamp": 1788185591587},
        {"delivery": {"mids": ["ig-1"]}, "sender": {"id": "1355726243215412"},
         "recipient": {"id": "17841477924025554"}, "timestamp": 1788185591588},
        {"reaction": {"mid": "ig-1", "action": "react"}, "sender": {"id": "1355726243215412"},
         "recipient": {"id": "17841477924025554"}, "timestamp": 1788185591589},
        {"sender": {"id": "1355726243215412"}, "recipient": {"id": "17841477924025554"},
         "timestamp": 1788185591590, "message": {"mid": "ig-real", "text": "hi"}},
    ]}]}
    messages = meta_client.parse_inbound(payload, expected_channel=CHANNEL_INSTAGRAM)
    assert [m.provider_message_id for m in messages] == ["ig-real"]

    # A message with no usable id is dropped rather than given the timestamp:
    # an unstable id defeats the duplicate guard on every redelivery.
    idless = {"object": "instagram", "entry": [{"id": "17841477924025554", "messaging": [
        {"sender": {"id": "u"}, "recipient": {"id": "17841477924025554"},
         "timestamp": 123, "message": {"text": "no mid"}},
    ]}]}
    assert meta_client.parse_inbound(idless, expected_channel=CHANNEL_INSTAGRAM) == []


@pytest.mark.asyncio
async def test_an_uncovered_pincode_is_refused_before_any_other_question():
    """Providers are matched on the pincode, so coverage is knowable at the
    very first answer. Asking for a city — or a service, a problem and its
    catalog questions — before saying "we don't cover you" wastes the
    customer's time and tells us nothing we did not already know."""
    from app.engines.messaging_gateway import flow

    class Thread:
        zipcode = "141001"
        city = None
        ai_session_id = None
        customer_id = "c-1"      # WhatsApp identity is already established
        channel = "whatsapp"

    asked = []

    async def _none(db, zipcode):
        asked.append(zipcode)
        return []                      # nothing bookable at this pincode

    original, flow._serviceable_categories = flow._serviceable_categories, _none
    try:
        turn = await flow._next_step(None, Thread(), None, None, CHANNEL_WHATSAPP, 0)
    finally:
        flow._serviceable_categories = original

    assert asked == ["141001"]
    assert turn.picker is None
    assert turn.text == flow.NOT_IN_CITY.format(area="141001")
    assert flow.ASK_CITY not in turn.text


@pytest.mark.asyncio
async def test_a_typed_number_selects_from_the_list_that_was_actually_sent():
    """A number is resolved against the ids last SENT, never a rebuilt step.

    Several lists exist only as the result of an earlier choice — a category's
    offerings, any "Show more" page — so rebuilding the current step resolves
    the number against the wrong list and silently repeats it.
    """
    from app.engines.messaging_gateway import flow

    class Thread:
        id = "t"
        last_options = ["of|home_services|ac_repair",
                        "of|home_services|geyser_repair",
                        "more|of|1|home_services"]

    resolve = flow._resolve_numbered_choice
    assert await resolve(Thread(), "2") == "of|home_services|geyser_repair"
    assert await resolve(Thread(), " 3 ") == "more|of|1|home_services"
    # Out of range, non-numeric, and a pincode all stay ordinary text.
    assert await resolve(Thread(), "9") is None
    assert await resolve(Thread(), "AC Repair") is None
    assert await resolve(Thread(), "140412") is None

    class Closed:
        id = "t"
        last_options = None      # last turn offered nothing to choose from
    assert await resolve(Closed(), "2") is None


@pytest.mark.asyncio
async def test_a_booking_confirms_the_phone_number_before_it_can_be_placed():
    """A booking has to reach a real person.

    WhatsApp hands us a Meta-verified number, so it goes straight to Confirm.
    Every other channel collects one and confirms it by one-time code as a
    step of the booking — the booking services refuse to create final records
    without a verified account, so showing Confirm first would put a button in
    front of the customer that fails when tapped.
    """
    from app.engines.messaging_gateway import flow

    class Instagram:
        channel = "instagram"
        customer_id = None
        pending_phone_ciphertext = None
        zipcode = "140412"
        city = "Bassi Pathana"

    class Executor:
        customer_id = None

        async def _tool_get_home_service_booking_summary(self, draft_id):
            return {"summary": {"booking_summary": {"offering_name": "AC Repair"}}}

    # Once the address is retained, the next thing owed is the phone number.
    ready = {"id": "d-1", "status": "provider_matched", "job_type_id": "j-1",
             "selected_tenant_id": "t-1", "preferred_date": "2026-09-02",
             "zipcode": "140412",
             "address_snapshot": {"address_line_1": "House 4", "latitude": 30.7}}

    async def _no_picker(*args, **kwargs):
        return None

    async def _covered(db, zipcode):
        return ["home_services"]

    original, pickers.build_picker = pickers.build_picker, _no_picker
    categories, flow._serviceable_categories = flow._serviceable_categories, _covered
    try:
        thread = Instagram()
        turn = await flow._next_step(None, thread, Executor(), ready, CHANNEL_INSTAGRAM, 0)
        assert turn.text == flow.ASK_PHONE and turn.picker is None

        # Once a code is outstanding, the step asks for the OTP instead — and
        # names the number it went to, so a mistyped digit is visible.
        thread.pending_phone_ciphertext = "cipher"
        turn = await flow._next_step(None, thread, Executor(), ready, CHANNEL_INSTAGRAM, 0)
        assert turn.text is None
        assert turn.picker["body"] == flow.ASK_OTP.format(number="your number")
        assert turn.picker["rows"] == [{
            "id": "phone|change", "title": "Use another number",
        }]

        # A verified thread reaches the summary and the Confirm button.
        thread.customer_id = uuid.uuid4()
        turn = await flow._next_step(None, thread, Executor(), ready, CHANNEL_INSTAGRAM, 0)
        assert [r["id"] for r in turn.picker["rows"]] == ["cf|yes", "rs|1"]
    finally:
        pickers.build_picker = original
        flow._serviceable_categories = categories


@pytest.mark.asyncio
async def test_the_number_and_the_code_are_read_at_the_right_moment():
    """The number and its code are typed, so each must be recognised only at
    the step that is waiting for it — and a code must never be mistaken for a
    pincode, nor a number for an address."""
    from app.engines.messaging_gateway import flow

    class Thread:
        channel = "instagram"
        customer_id = None
        zipcode = "140412"
        city = "Bassi Pathana"
        pending_phone_ciphertext = None
        ai_session_id = None

    calls = []

    class Identity:
        def __init__(self):
            self.awaiting_confirmation = False
            self.phone = None

        async def stage_phone_verification(self, thread, phone):
            calls.append(("stage", phone))
            self.phone = phone
            self.awaiting_confirmation = True
            thread.pending_phone_ciphertext = "confirm:cipher"

        def phone_verification_requires_confirmation(self, thread):
            return self.awaiting_confirmation

        def pending_number(self, thread):
            return self.phone

        async def confirm_phone_verification(self, thread):
            calls.append(("send", self.phone))
            self.awaiting_confirmation = False
            thread.pending_phone_ciphertext = "cipher"
            return "code sent"

        async def start_phone_verification(self, thread, phone):
            calls.append(("start", phone))
            thread.pending_phone_ciphertext = "cipher"
            return "code sent"

        async def finish_phone_verification(self, thread, code):
            calls.append(("finish", code))
            return "verified"

    # The phone step opens only once the booking itself is complete — a slot
    # included — so nothing typed here can still be an address or a pincode.
    booked = {"id": "d-1", "selected_tenant_id": "t-1",
              "preferred_date": "2026-09-02",
              "address_snapshot": {"address_line_1": "House 4", "latitude": 30.7}}
    thread = Thread()
    identity = Identity()

    note, _ = await flow._apply_text(None, thread, None, "12345", booked, identity=identity)
    assert note == flow.BAD_PHONE and calls == []

    await flow._apply_text(None, thread, None, "+919876543210", booked, identity=identity)
    assert calls == [("stage", "+919876543210")]
    confirmation = flow._phone_confirmation_step(identity, thread)
    assert confirmation.text is None
    assert "******3210" in confirmation.picker["body"]
    assert [row["id"] for row in confirmation.picker["rows"]] == [
        "phone|send", "phone|change",
    ]

    # Only this explicit tap incurs the OTP send.
    await flow._navigate(None, None, "phone|send", booked, thread,
                         CHANNEL_INSTAGRAM, identity)
    assert calls[-1] == ("send", "+919876543210")

    await flow._apply_text(None, thread, None, "123456", booked, identity=identity)
    assert calls[-1] == ("finish", "123456")


@pytest.mark.asyncio
async def test_start_over_works_from_any_message_including_after_booking():
    """"Start over" is answered ahead of every other tap — and ahead of the
    confirmed-booking guard, which refuses everything else. A customer who
    picked the wrong service six questions ago, or who has just booked and
    wants another, must not need to remember a command."""
    from app.engines.messaging_gateway import flow

    class Thread:
        id = "t"
        channel = "whatsapp"
        customer_id = None
        zipcode = "140412"
        city = "Bassi Pathana"
        ai_session_id = "session-1"
        last_options = ["cf|yes", "rs|1"]

    async def _categories(db, zipcode):
        class Category:
            slug, name = "home_services", "Home Services"
        return [Category()]

    confirmed = {"id": "d-1", "status": "confirmed", "job_type_id": "j-1"}
    thread = Thread()

    original, flow._serviceable_categories = flow._serviceable_categories, _categories
    try:
        turn = await flow._navigate(None, None, "rs|1", confirmed, thread, CHANNEL_WHATSAPP)
    finally:
        flow._serviceable_categories = original

    assert turn.text.startswith(flow.RESTARTED)
    assert turn.text.endswith(flow.ASK_PINCODE)
    assert turn.picker is None
    # A new booking always re-confirms its serviceability key.
    assert thread.ai_session_id is None and thread.last_options is None
    assert (thread.zipcode, thread.city) == (None, None)


def test_typed_prompts_are_plain_text_with_no_button():
    """Every OPTIONS message carries a "Start over" row. A prompt that asks
    for something typed — an address, a phone number, a code — deliberately
    does not: a button under a question the customer is about to answer in
    words is clutter beside the thing they were asked for."""
    from app.engines.messaging_gateway import service

    assert not hasattr(service, "as_restartable")
    assert not hasattr(service, "with_restart_hint")
    assert "/fuvay" not in service.UNSUPPORTED_TEXT




@pytest.mark.asyncio
async def test_a_live_booking_is_trackable_from_the_chat_on_both_channels():
    """A customer with a booking in progress should not have to remember
    /track. The option leads the first list, and tapping it answers with the
    real status — asking WHICH booking only when there is a real choice."""
    from app.engines.messaging_gateway import flow

    class Thread:
        id = "t"
        channel = "whatsapp"
        customer_id = "c-1"
        zipcode = "140412"
        city = "Bassi Pathana"
        ai_session_id = None

    class Identity:
        def __init__(self, bookings, can_cancel=False):
            self.bookings = bookings
            self.can_cancel = can_cancel

        async def cancel_options(self, thread, booking_number):
            return {"can_cancel": self.can_cancel,
                    "reasons": ["changed_mind", "no_longer_needed"]}

        async def live_booking(self, thread):
            return bool(self.bookings)

        async def live_bookings(self, thread):
            return self.bookings

        async def booking_status(self, thread, booking_number=""):
            number = booking_number or self.bookings[0]["number"]
            return f"Booking {number}\nStatus: Accepted"

    one = [{"number": "BK-1", "service": "AC Repair", "status": "Accepted"}]
    two = one + [{"number": "BK-2", "service": "Geyser Repair", "status": "Assigned"}]

    async def _categories(db, zipcode):
        class Category:
            slug, name = "home_services", "Home Services"
        return [Category()]

    original, flow._serviceable_categories = flow._serviceable_categories, _categories
    try:
        for channel in (CHANNEL_WHATSAPP, CHANNEL_INSTAGRAM):
            step = await flow._next_step(None, Thread(), None, None, channel, 0,
                                         Identity(one))
            assert step.picker["rows"][0]["id"] == "tr|"

            # Nothing live: the option is not offered, because it would be noise.
            quiet = await flow._next_step(None, Thread(), None, None, channel, 0,
                                          Identity([]))
            assert all(not r["id"].startswith("tr|") for r in quiet.picker["rows"])
    finally:
        flow._serviceable_categories = original

    # One booking: answer, do not ask which.
    tracked = await flow._navigate(None, None, "tr|", None, Thread(),
                                   CHANNEL_WHATSAPP, Identity(one))
    assert "BK-1" in tracked.text
    assert [r["id"] for r in tracked.picker["rows"]] == ["tr|", "rs|1"]

    # Two: ask which, naming the service rather than the number.
    choose = await flow._navigate(None, None, "tr|", None, Thread(),
                                  CHANNEL_WHATSAPP, Identity(two))
    assert [r["title"] for r in choose.picker["rows"][:2]] == ["AC Repair", "Geyser Repair"]
    assert choose.picker["rows"][1]["id"] == "tr|BK-2"

    picked = await flow._navigate(None, None, "tr|BK-2", None, Thread(),
                                  CHANNEL_WHATSAPP, Identity(two))
    assert "BK-2" in picked.text


@pytest.mark.asyncio
async def test_instagram_uses_stacked_buttons_for_durable_actions(monkeypatch):
    """Instagram has no list message. Its one STACKED control is the button
    template, capped at three — so short sets get buttons in a column, and
    longer sets get numbered lines plus tappable chips, because chips alone
    scroll out of view and text alone cannot be tapped."""
    calls = []

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
            calls.append(kwargs["json"])
            return Response()

    monkeypatch.setattr(meta_client.httpx, "AsyncClient", Client)
    ig = {"access_token": "ig-token", "instagram_account_id": "17890001",
          "api_version": "v26.0"}

    await meta_client.send_options("igsid-1", "Shall I confirm?", [
        {"id": "cf|yes", "title": "Confirm booking"},
        {"id": "rs|1", "title": "Start over"},
    ], channel=CHANNEL_INSTAGRAM, config=ig, presentation="buttons")
    buttons = calls[0]["message"]["attachment"]["payload"]["buttons"]
    assert [b["payload"] for b in buttons] == ["cf|yes", "rs|1"]
    assert all(b["type"] == "postback" for b in buttons)

    await meta_client.send_options("igsid-1", "Pick a time", [
        {"id": "sl|d|09:00-10:00", "title": "Thu 09:00-10:00",
         "section": "Standard slots"},
        {"id": "sl|d|10:00-11:00", "title": "Thu 10:00-11:00",
         "section": "Standard slots"},
        {"id": "sl|d|08:00-09:00|e", "title": "Thu 08:00-09:00",
         "section": "Emergency +₹200", "description": "+₹200"},
        {"id": "rs|1", "title": "Start over"},
    ], channel=CHANNEL_INSTAGRAM, config=ig)
    text = calls[1]["message"]["text"]
    # Instagram has no section headings, so the groups are announced inline —
    # otherwise a standard and an emergency slot look identical in a list.
    assert "Standard slots:" in text and "Emergency +₹200:" in text
    assert "3. Thu 08:00-09:00 (+₹200)" in text
    assert [q["payload"] for q in calls[1]["message"]["quick_replies"]][-1] == "rs|1"

    await meta_client.send_options("igsid-1", "Which service?", [
        {"id": "of|ac|repair", "title": "AC Repair",
         "description": "Diagnosis and repair",
         "image_url": "https://cdn.example/ac.jpg",
         "button_title": "Select service"},
        {"id": "rs|1", "title": "Start over", "button_title": "Start over"},
    ], channel=CHANNEL_INSTAGRAM, config=ig, presentation="carousel")
    elements = calls[2]["message"]["attachment"]["payload"]["elements"]
    assert elements[0]["image_url"] == "https://cdn.example/ac.jpg"
    assert elements[0]["buttons"][0] == {
        "type": "postback", "title": "Select service", "payload": "of|ac|repair",
    }
    assert "image_url" not in elements[1]


@pytest.mark.asyncio
async def test_a_plain_http_card_image_is_dropped_rather_than_sent(monkeypatch):
    """Meta fetches card artwork itself and accepts only public https, so a
    local-disk upload served over http can never render. It must not be sent
    as if it could."""
    calls = []

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
            calls.append(kwargs["json"])
            return Response()

    monkeypatch.setattr(meta_client.httpx, "AsyncClient", Client)
    ig = {"access_token": "ig-token", "instagram_account_id": "17890001",
          "api_version": "v26.0"}

    await meta_client.send_options("igsid-1", "Which service?", [
        {"id": "of|home_services|air-conditioner", "title": "Air Conditioner",
         "image_url": "http://129.121.137.155:8000/uploads/service_icon/a.png",
         "button_title": "Select service"},
    ], channel=CHANNEL_INSTAGRAM, config=ig, presentation="carousel")

    element = calls[0]["message"]["attachment"]["payload"]["elements"][0]
    assert "image_url" not in element
    assert element["title"] == "Air Conditioner"


@pytest.mark.asyncio
async def test_instagram_profile_sync_publishes_four_working_icebreakers(monkeypatch):
    calls = []

    class Response:
        status_code = 200
        text = json.dumps({"result": "success"})

    class Client:
        def __init__(self, **kwargs):
            pass
        async def __aenter__(self):
            return self
        async def __aexit__(self, *args):
            return None
        async def post(self, url, **kwargs):
            calls.append((url, kwargs["json"]))
            return Response()

    monkeypatch.setattr(meta_client.httpx, "AsyncClient", Client)
    result = await meta_client.sync_instagram_profile({
        "access_token": "ig-token", "instagram_account_id": "17890001",
        "api_version": "v26.0",
    })
    assert result["sent"] is True
    assert calls[0][0].endswith("/v26.0/17890001/messenger_profile")
    assert calls[0][1]["platform"] == "instagram"
    assert len(calls[0][1]["ice_breakers"]) == 4
    assert {item["payload"] for item in calls[0][1]["ice_breakers"]} <= {
        "/fuvay", "/track", "/human",
    }


def test_whatsapp_flow_completion_is_parsed_as_untrusted_structured_input():
    response = {
        "flow_token": "sos1.payload.signature",
        "slot_id": "sl|2026-09-03|10:00-11:00",
    }
    payload = {
        "object": "whatsapp_business_account",
        "entry": [{"id": "waba", "changes": [{"field": "messages", "value": {
            "metadata": {"phone_number_id": "10001"},
            "messages": [{
                "id": "wamid.flow", "from": "919999999999", "type": "interactive",
                "interactive": {"type": "nfm_reply", "nfm_reply": {
                    "response_json": json.dumps(response),
                }},
            }],
        }}]}],
    }

    message = meta_client.parse_inbound(
        payload, expected_channel=CHANNEL_WHATSAPP,
    )[0]
    assert message.flow_response == response
    assert message.reply_id is None
    assert message.text == "Booking form completed"


@pytest.mark.asyncio
async def test_whatsapp_flow_payload_and_location_cta(monkeypatch):
    calls = []

    class Response:
        status_code = 200
        text = json.dumps({"messages": [{"id": "wamid.sent"}]})

    class Client:
        def __init__(self, **kwargs):
            pass
        async def __aenter__(self):
            return self
        async def __aexit__(self, *args):
            return None
        async def post(self, url, **kwargs):
            calls.append(kwargs["json"])
            return Response()

    monkeypatch.setattr(meta_client.httpx, "AsyncClient", Client)
    config = {"access_token": "token", "phone_number_id": "10001", "api_version": "v26.0"}
    result = await meta_client.send_options(
        "919999999999", "Choose a live appointment", [
            {"id": "sl|2026-09-03|10:00-11:00", "title": "Thu 10:00-11:00"},
        ], channel=CHANNEL_WHATSAPP, config=config, presentation="flow", flow={
            "id": "987654321", "token": "signed-token", "screen": "BOOKING_SLOT",
            "cta": "Complete booking", "data": {"available_slots": []},
        },
    )
    assert result["flow_sent"] is True
    parameters = calls[0]["interactive"]["action"]["parameters"]
    assert parameters["flow_id"] == "987654321"
    assert parameters["flow_token"] == "signed-token"
    assert parameters["flow_action_payload"]["screen"] == "BOOKING_SLOT"

    await meta_client.send_cta_url(
        "919999999999", "Check the service address.", "Open location",
        "https://maps.google.com/?q=30.7,76.7", config=config,
    )
    assert calls[1]["interactive"] == {
        "type": "cta_url",
        "body": {"text": "Check the service address."},
        "action": {"name": "cta_url", "parameters": {
            "display_text": "Open location",
            "url": "https://maps.google.com/?q=30.7,76.7",
        }},
    }
    rejected = await meta_client.send_cta_url(
        "919999999999", "Unsafe", "Open", "http://example.com", config=config,
    )
    assert rejected == {"sent": False, "reason": "invalid_cta_url"}


@pytest.mark.asyncio
async def test_rejected_whatsapp_flow_falls_back_to_the_slot_list(monkeypatch):
    calls = []

    class Response:
        def __init__(self, status_code):
            self.status_code = status_code
            self.text = json.dumps({"error": {"message": "Flow unavailable"}})

    class Client:
        def __init__(self, **kwargs):
            pass
        async def __aenter__(self):
            return self
        async def __aexit__(self, *args):
            return None
        async def post(self, url, **kwargs):
            calls.append(kwargs["json"])
            return Response(400 if len(calls) == 1 else 200)

    monkeypatch.setattr(meta_client.httpx, "AsyncClient", Client)
    result = await meta_client.send_options(
        "919999999999", "Pick a time", [
            {"id": "sl|2026-09-03|10:00-11:00", "title": "Thu 10:00-11:00"},
            {"id": "rs|1", "title": "Start over"},
        ], channel=CHANNEL_WHATSAPP,
        config={"access_token": "token", "phone_number_id": "10001"},
        presentation="flow",
        flow={"id": "987", "token": "signed", "data": {}},
    )
    assert result["sent"] is True
    assert calls[0]["interactive"]["type"] == "flow"
    assert calls[1]["interactive"]["type"] == "button"


@pytest.mark.asyncio
async def test_connection_verifies_configured_whatsapp_flow_is_published(monkeypatch):
    calls = []

    class Response:
        status_code = 200
        def __init__(self, body):
            self.text = json.dumps(body)

    class Client:
        def __init__(self, **kwargs):
            pass
        async def __aenter__(self):
            return self
        async def __aexit__(self, *args):
            return None
        async def get(self, url, **kwargs):
            calls.append(url)
            if url.endswith("/10001"):
                return Response({
                    "id": "10001", "verified_name": "Fuvay Services",
                })
            return Response({
                "id": "987", "name": "Complete booking", "status": "PUBLISHED",
                "whatsapp_business_account": {"id": "555"},
            })

    monkeypatch.setattr(meta_client.httpx, "AsyncClient", Client)
    passed, message, _ = await meta_client.test_connection(
        CHANNEL_WHATSAPP, {
            "access_token": "token", "phone_number_id": "10001",
            "business_account_id": "555", "booking_flow_id": "987",
            "api_version": "v26.0",
        },
    )
    assert passed is True
    assert "Complete booking is published" in message
    assert calls[-1].endswith("/v26.0/987")


@pytest.mark.asyncio
async def test_whatsapp_flow_token_is_bound_to_thread_and_current_draft(monkeypatch):
    from app.engines.messaging_gateway import flow
    from app.engines.messaging_gateway.service import MessagingGatewayService

    thread_id, draft_id = uuid.uuid4(), uuid.uuid4()

    class Thread:
        id = thread_id

    async def current_draft(db, thread):
        return {"id": str(draft_id)}

    monkeypatch.setattr(flow, "_draft", current_draft)
    service = MessagingGatewayService(
        object(), channel_config={"app_secret": "a-real-app-secret"},
    )
    token = service._flow_token(Thread(), str(draft_id))
    slot = "sl|2026-09-03|10:00-11:00"
    assert await service._validated_flow_reply(
        Thread(), {"flow_token": token, "slot_id": slot},
    ) == slot
    assert await service._validated_flow_reply(
        Thread(), {"flow_token": token + "x", "slot_id": slot},
    ) is None

    class OtherThread:
        id = uuid.uuid4()

    assert await service._validated_flow_reply(
        OtherThread(), {"flow_token": token, "slot_id": slot},
    ) is None


@pytest.mark.asyncio
async def test_slot_picker_is_upgraded_to_flow_with_server_owned_booking_data(monkeypatch):
    from app.engines.messaging_gateway import flow
    from app.engines.messaging_gateway.service import MessagingGatewayService

    draft_id, offering_id, thread_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    draft = {
        "id": str(draft_id), "offering_id": str(offering_id),
        "preferred_date": None,
        "selected_provider_snapshot": {"provider_name": "Trusted Services"},
        "price_snapshot": {"display_price": "₹1,499"},
        "address_snapshot": {"address_line_1": "House 12"},
        "city": "Ludhiana", "zipcode": "141001",
    }
    full_rows = [
        {"id": "sl|2026-09-03|10:00-11:00", "title": "Thu 10:00-11:00",
         "section": "Standard slots"},
        {"id": "rs|1", "title": "Start over"},
    ]

    async def current_draft(db, thread):
        return draft

    async def full_picker(*args, **kwargs):
        assert kwargs["capacity_override"] == 200
        return {"rows": full_rows}

    class DB:
        async def get(self, model, record_id):
            assert record_id == offering_id
            return type("Offering", (), {"service_name": "AC Repair"})()

    class Thread:
        id = thread_id
        customer_id = uuid.uuid4()

    monkeypatch.setattr(flow, "_draft", current_draft)
    monkeypatch.setattr(pickers, "build_picker", full_picker)
    service = MessagingGatewayService(DB(), channel_config={
        "app_secret": "a-real-app-secret", "booking_flow_id": "987654321",
    })
    upgraded = await service._as_whatsapp_flow(Thread(), {
        "body": "Pick a time", "rows": full_rows,
        "list_button": "Pick", "section_title": "Slots",
    })

    assert upgraded["presentation"] == "flow"
    payload = upgraded["flow"]
    assert payload["id"] == "987654321"
    assert payload["data"]["service"] == "AC Repair"
    assert "Trusted Services" in payload["data"]["booking_details"]
    assert "₹1,499" in payload["data"]["booking_details"]
    assert payload["data"]["available_slots"] == [{
        "id": "sl|2026-09-03|10:00-11:00",
        "title": "Thu 10:00-11:00",
        "description": "Standard slots",
    }]


@pytest.mark.asyncio
async def test_social_chat_handles_handover_then_direct_payment_to_job_done():
    """The customer actions required by staff closure are available in chat."""
    from app.engines.messaging_gateway import flow

    class Thread:
        id = "thread-closure"
        customer_id = "customer-1"

    class Identity:
        def __init__(self):
            self.actions = [
                {"kind": "handover", "job_id": "job-1", "booking_number": "BK-1",
                 "service": "AC Repair"},
                {"kind": "payment", "payment_id": "payment-1", "job_id": "job-1",
                 "job_ref": "JOB-1", "provider": "Good Service Co",
                 "amount": "1499", "currency": "INR", "method": "UPI"},
            ]
            self.payment_decisions = []

        async def pending_closure_actions(self, thread):
            return list(self.actions)

        async def acknowledge_handover(self, thread, job_id):
            assert job_id == "job-1"
            self.actions.pop(0)
            return flow.HANDOVER_ACKNOWLEDGED

        async def decide_payment(self, thread, payment_id, decision):
            self.payment_decisions.append((payment_id, decision))
            self.actions = []
            return (flow.PAYMENT_CONFIRMED if decision == "confirm"
                    else flow.PAYMENT_MISMATCH_REPORTED)

        async def live_bookings(self, thread):
            return []

    for channel in (CHANNEL_WHATSAPP, CHANNEL_INSTAGRAM):
        identity = Identity()
        handover = await flow._closure_step(identity, Thread(), channel)
        assert handover.picker["presentation"] == "buttons"
        assert handover.picker["rows"][0]["id"] == "ho|job-1|acknowledge"

        payment = await flow._navigate(
            None, None, "ho|job-1|acknowledge", None, Thread(), channel, identity,
        )
        assert "₹1,499" in payment.text
        assert [row["id"] for row in payment.picker["rows"]] == [
            "pay|payment-1|confirm", "pay|payment-1|review_not_paid",
        ]

        warning = await flow._navigate(
            None, None, "pay|payment-1|review_not_paid", None, Thread(), channel,
            identity,
        )
        assert identity.payment_decisions == []
        assert "Confirm not paid" == warning.picker["rows"][0]["title"]

        done = await flow._navigate(
            None, None, "pay|payment-1|confirm", None, Thread(), channel, identity,
        )
        assert identity.payment_decisions == [("payment-1", "confirm")]
        assert flow.PAYMENT_CONFIRMED in done.text


@pytest.mark.asyncio
async def test_type_and_brand_answers_bridge_by_dimension_not_by_question_name():
    """Which column an answer belongs to is decided by the dimension the
    question draws its options from, not by what the question is called.

    Matching on names was a real bug: the list was ac_type/service_type/
    offering_type, while the catalog names the same dimension-backed question
    `equipment_type` on 14 of the 18 published services — so offering_type_id
    was never written and every chimney, geyser, RO, washing-machine and
    refrigerator booking failed confirmation with "Missing required fields:
    offering_type_id". Confirmed live on a WhatsApp booking for Chimney Repair.
    """
    from app.engines.home_service_booking.question_flow_service import QuestionFlowService

    class Result:
        def __init__(self, value):
            self.value = value

        def scalars(self):
            return self

        def first(self):
            return self.value

    class DB:
        def __init__(self, dimension_source):
            self.dimension_source = dimension_source

        async def execute(self, *args, **kwargs):
            return Result(self.dimension_source)

    class Draft:
        offering_id = uuid.uuid4()

    service = QuestionFlowService.__new__(QuestionFlowService)

    # A dimension-backed question maps by its source, whatever it is called.
    service.db = DB("service_types")
    assert await service._answer_target(Draft(), "equipment_type") == "service_types"
    assert await service._answer_target(Draft(), "anything_an_admin_names_it") == "service_types"
    service.db = DB("brands")
    assert await service._answer_target(Draft(), "brand") == "brands"

    # No dimension: the two legacy names still bridge, everything else is
    # simply an answer and must not touch a structured column.
    service.db = DB(None)
    assert await service._answer_target(Draft(), "ac_type") == "service_types"
    assert await service._answer_target(Draft(), "brand") == "brands"
    assert await service._answer_target(Draft(), "issue_duration") is None


@pytest.mark.asyncio
async def test_the_explicit_first_pincode_question_rejects_non_pincodes():
    """Serviceability is tied to zipcode, so every new booking asks for the
    six digits before showing any service or catalog choice."""
    from app.engines.messaging_gateway import flow

    class Thread:
        channel = "whatsapp"
        customer_id = "c-1"
        zipcode = None
        city = None
        ai_session_id = None

    async def _no_city(db, zipcode):
        return "Bassi Pathana"

    original, flow._area_city = flow._area_city, _no_city
    try:
        thread = Thread()
        note, _ = await flow._apply_text(None, thread, None, "hi", None)
        assert note == flow.BAD_PINCODE and thread.zipcode is None

        note, _ = await flow._apply_text(None, thread, None, "hello there", None)
        assert note == flow.BAD_PINCODE

        # A number that is nearly a pincode IS an attempt, and is corrected.
        note, _ = await flow._apply_text(None, thread, None, "12345", None)
        assert note == flow.BAD_PINCODE

        # And a real one is taken, so typing still works for anyone who does.
        await flow._apply_text(None, thread, None, "140412", None)
        assert thread.zipcode == "140412"
    finally:
        flow._area_city = original


@pytest.mark.asyncio
async def test_a_new_booking_asks_for_zipcode_before_any_service_question():
    from app.engines.messaging_gateway import flow

    class Thread:
        channel = CHANNEL_INSTAGRAM
        customer_id = None
        zipcode = None
        city = None

    turn = await flow._next_step(
        None, Thread(), None, None, CHANNEL_INSTAGRAM, 0,
    )
    assert turn.text == flow.ASK_PINCODE
    assert turn.picker is None


@pytest.mark.asyncio
async def test_area_selection_keeps_the_pincode_because_a_city_is_too_coarse():
    """Coverage is keyed on the pincode, and a city can hold dozens of them —
    so a city with several is narrowed to its pincodes, while a city with one
    is selected outright rather than asking a question with a single answer."""
    from app.engines.messaging_gateway import flow

    async def _areas(db, city):
        rows = [
            ("bassi pathana", "140412", None),
            ("ludhiana", "141001", "Civil Lines"),
            ("ludhiana", "141002", "Model Town"),
            ("ludhiana", "141003", None),
        ]
        return [r for r in rows if not city or r[0] == city.lower()]

    original, flow._covered_areas = flow._covered_areas, _areas
    try:
        step = await flow._area_step(None, CHANNEL_WHATSAPP, 0)
        by_title = {r["title"]: r for r in step.picker["rows"]}
        # One pincode: the tap IS the answer.
        assert by_title["Bassi Pathana"]["id"] == "ar|140412"
        assert by_title["Bassi Pathana"]["description"] == "140412"
        # Several: narrow first, and say how many there are.
        assert by_title["Ludhiana"]["id"] == "ac|ludhiana"
        assert by_title["Ludhiana"]["description"] == "3 areas"

        narrowed = await flow._area_step(None, CHANNEL_WHATSAPP, 0, city="ludhiana")
        assert narrowed.picker["body"] == flow.ASK_AREA_PINCODE.format(city="ludhiana")
        assert [r["id"] for r in narrowed.picker["rows"][:3]] == [
            "ar|141001", "ar|141002", "ar|141003"]
        # A locality name is friendlier than a number, with the number kept.
        assert narrowed.picker["rows"][0]["title"] == "Civil Lines"
        assert narrowed.picker["rows"][0]["description"] == "141001"
        # One with no locality falls back to the pincode itself.
        assert narrowed.picker["rows"][2]["title"] == "141003"
    finally:
        flow._covered_areas = original


@pytest.mark.asyncio
async def test_cancelling_asks_why_and_never_decides_eligibility_itself():
    """A booking is cancellable while no technician is doing the work, and the
    SERVER decides that — the chat renders `get_customer_eligibility`, it does
    not reproduce the status rules. One stray tap must not cancel anything
    either, so a reason is asked for first."""
    from app.engines.messaging_gateway import flow

    class Thread:
        id = "t"
        channel = "whatsapp"
        customer_id = "c-1"

    class Identity:
        def __init__(self, can_cancel):
            self.can_cancel = can_cancel
            self.cancelled = None

        async def cancel_options(self, thread, booking_number):
            return {"can_cancel": self.can_cancel,
                    "reasons": ["changed_mind", "price_concern", "other"]}

        async def cancel_booking(self, thread, booking_number, reason):
            self.cancelled = (booking_number, reason)
            return flow.CANCELLED.format(number=booking_number)

        async def booking_status(self, thread, booking_number=""):
            return "Booking BK-1"

        async def live_bookings(self, thread):
            return [{"number": "BK-1", "service": "AC Repair", "status": "Accepted"}]

    # Cancellable: the first tap asks why, in the words a customer would use.
    identity = Identity(can_cancel=True)
    asked = await flow._cancel_step(Thread(), identity, "BK-1", CHANNEL_WHATSAPP)
    assert identity.cancelled is None
    assert [r["title"] for r in asked.picker["rows"][:3]] == [
        "Changed my mind", "Too expensive", "Another reason"]
    assert asked.picker["rows"][0]["id"] == "cx|BK-1|changed_mind"

    # The second tap carries the reason through to the booking service.
    done = await flow._cancel_step(Thread(), identity, "BK-1|price_concern",
                                   CHANNEL_WHATSAPP)
    assert identity.cancelled == ("BK-1", "price_concern")
    assert "cancelled" in done.text

    # Not cancellable any more: say so, and do not offer the row at all.
    blocked = Identity(can_cancel=False)
    turn = await flow._cancel_step(Thread(), blocked, "BK-1", CHANNEL_WHATSAPP)
    assert turn.text == flow.CANCEL_NOT_ALLOWED
    assert all(not r["id"].startswith("cx|") for r in turn.picker["rows"])

    tracked = await flow._track_step(Thread(), Identity(can_cancel=True), "",
                                     CHANNEL_WHATSAPP)
    assert [r["id"] for r in tracked.picker["rows"]] == [
        "tr|", "cx|BK-1", "rs|1"]


def test_an_indian_mobile_is_taken_without_a_country_code():
    """India-only product: a customer types the ten digits they know. Prefixes
    people habitually type are accepted, and the 6-9 leading digit is what
    separates a real mobile from a pincode typed at the wrong moment."""
    from app.engines.messaging_gateway.flow import _indian_mobile

    assert _indian_mobile("9876543210") == "+919876543210"
    assert _indian_mobile("919876543210") == "+919876543210"
    assert _indian_mobile("09876543210") == "+919876543210"
    assert _indian_mobile("1234567890") is None      # not a mobile prefix
    assert _indian_mobile("140412") is None          # a pincode
    assert _indian_mobile("98765") is None


@pytest.mark.asyncio
async def test_a_new_number_does_not_resend_otp_until_confirmed():
    """Seen live: a thread sat on "send the code" for a number whose OTP never
    arrived, and the step accepted nothing but six digits — so there was no
    way back to entering a different number. Entering a replacement stages it
    for confirmation without paying for another OTP."""
    from app.engines.messaging_gateway import flow

    class Thread:
        channel = "instagram"
        customer_id = None
        pending_phone_ciphertext = "cipher"
        zipcode = "140412"
        city = "Bassi Pathana"

    class Identity:
        def __init__(self):
            self.sent = []
            self.staged = []

        def pending_number(self, thread):
            return "+919041624576"

        async def start_phone_verification(self, thread, phone):
            self.sent.append(phone)
            return "sent"

        async def stage_phone_verification(self, thread, phone):
            self.staged.append(phone)
            thread.pending_phone_ciphertext = "confirm:new"

        async def finish_phone_verification(self, thread, code):
            return "verified"

    booked = {"id": "d-1", "selected_tenant_id": "t-1", "preferred_date": "2026-09-02",
              "address_snapshot": {"address_line_1": "House 4", "latitude": 30.7}}
    identity = Identity()

    note, _ = await flow._apply_text(None, Thread(), None, "9876543210", booked,
                                     identity=identity)
    assert identity.staged == ["+919876543210"]
    assert identity.sent == []
    assert note is None

    # Anything that is not a number and not a code is not an error — the step
    # simply asks again, naming the number the OTP went to so a mistyped digit
    # is visible.
    note, _ = await flow._apply_text(None, Thread(), None, "abc", booked,
                                     identity=identity)
    assert note is None
    prompt = flow._otp_step(identity, Thread()).picker["body"]
    assert "OTP we just sent to ******4576" in prompt
    assert "type the new 10-digit number" in prompt


@pytest.mark.asyncio
async def test_instagram_can_tap_use_another_number_without_losing_booking():
    from app.engines.messaging_gateway import flow

    class Thread:
        channel = CHANNEL_INSTAGRAM
        customer_id = None
        pending_customer_id = "customer-old"
        pending_phone_ciphertext = "encrypted-old-number"

    thread = Thread()
    turn = await flow._navigate(
        None, None, "phone|change", {"id": "draft-stays"}, thread,
        CHANNEL_INSTAGRAM,
    )

    assert turn.text == flow.ASK_PHONE
    assert turn.picker is None
    assert thread.pending_customer_id is None
    assert thread.pending_phone_ciphertext is None


@pytest.mark.asyncio
async def test_a_shared_location_is_stored_where_the_technician_reads_it():
    """A pin is what actually gets a technician to the door where street
    addresses are approximate. It goes onto the draft's `address_snapshot`,
    which `creation_service` copies onto the booking and the job — the same
    object the provider and technician surfaces already render — along with a
    maps link, because a link is what someone can act on from a job screen."""
    from app.engines.messaging_gateway import flow

    merged = {}

    async def _merge(db, draft, values):
        merged.update(values)

    original, flow._merge_address = flow._merge_address, _merge
    try:
        note, _ = await flow._apply_location(None, {"id": "d-1"}, {
            "latitude": 30.7046, "longitude": 76.7179,
            "name": "Home", "address": "New Sarian", "source": "shared_pin",
        })
    finally:
        flow._merge_address = original

    assert note == flow.LOCATION_SAVED
    assert merged["latitude"] == 30.7046 and merged["longitude"] == 76.7179
    assert merged["maps_url"] == "https://maps.google.com/?q=30.7046,76.7179"
    assert merged["location_label"] == "Home"
    assert merged["location_source"] == "shared_pin"
    assert merged["address_line_1"] == "New Sarian"


@pytest.mark.asyncio
async def test_instagram_has_no_map_link_location_step(monkeypatch):
    """Instagram relies on the validated address and does not collect a pin."""
    from app.engines.messaging_gateway import flow

    class Thread:
        channel = CHANNEL_INSTAGRAM
        zipcode = "140412"
        city = "Bassi Pathana"
        customer_id = "c-1"

    draft = {
        "id": "d-1", "selected_tenant_id": None,
        "address_snapshot": {"address_line_1": "House 4, Main Road"},
    }
    async def must_not_parse(text):
        raise AssertionError("Instagram must not enter the location-link path")

    monkeypatch.setattr(flow, "_coordinates_from_text", must_not_parse)

    note, unchanged = await flow._apply_text(
        None, Thread(), None,
        "https://maps.google.com/?q=30.7046,76.7179", draft,
    )
    assert note is None
    assert unchanged == draft


@pytest.mark.asyncio
async def test_complete_instagram_address_is_validated_and_persisted(monkeypatch):
    from app.engines.messaging_gateway import flow

    class Thread:
        channel = CHANNEL_INSTAGRAM
        zipcode = "140412"
        city = "Bassi Pathana"
        customer_id = "c-1"

    class Executor:
        def __init__(self):
            self.fields = None

        async def _tool_update_home_service_draft(self, draft_id, **fields):
            self.fields = fields
            return {"updated": True}

    draft = {"id": "d-1", "address_snapshot": {}}
    executor = Executor()

    async def current_draft(db, thread):
        return {**draft, "address_snapshot": executor.fields or {}}

    monkeypatch.setattr(flow, "_draft", current_draft)

    note, _ = await flow._apply_text(None, Thread(), executor, "hi", draft)
    assert note == flow.BAD_ADDRESS and executor.fields is None

    note, updated = await flow._apply_text(
        None, Thread(), executor,
        "Flat 12, Sunrise Building, Main Road, near Bus Stand", draft,
    )
    assert note is None
    assert executor.fields == {
        "address_line_1": "Flat 12, Sunrise Building, Main Road, near Bus Stand",
    }
    assert updated["address_snapshot"] == executor.fields


def test_whatsapp_location_pins_and_pasted_map_links_are_both_understood():
    """WhatsApp sends a real location message and map links remain usable."""
    payload = {"object": "whatsapp_business_account", "entry": [{"id": "w", "changes": [
        {"field": "messages", "value": {
            "metadata": {"phone_number_id": "10001"},
            "messages": [{"id": "wamid.loc", "from": "919999999999", "type": "location",
                          "location": {"latitude": 30.7046, "longitude": 76.7179,
                                       "name": "Home", "address": "New Sarian"}}],
        }}]}]}
    msg = meta_client.parse_inbound(payload, expected_channel=CHANNEL_WHATSAPP)[0]
    assert msg.location == {"latitude": 30.7046, "longitude": 76.7179,
                            "name": "Home", "address": "New Sarian"}

    # An ordinary message carries no location, and must not invent one.
    text_payload = {"object": "whatsapp_business_account", "entry": [{"id": "w", "changes": [
        {"field": "messages", "value": {
            "metadata": {"phone_number_id": "10001"},
            "messages": [{"id": "wamid.t", "from": "91", "type": "text",
                          "text": {"body": "hi"}}],
        }}]}]}
    assert meta_client.parse_inbound(text_payload, expected_channel=CHANNEL_WHATSAPP)[0].location is None

    from app.engines.messaging_gateway.flow import _maps_coordinates

    for link in ("https://www.google.com/maps/@30.7046,76.7179,17z",
                 "https://maps.google.com/?q=30.7046,76.7179",
                 "30.7046, 76.7179"):
        found = _maps_coordinates(link)
        assert (found["latitude"], found["longitude"]) == (30.7046, 76.7179)
    assert _maps_coordinates("no link here") is None


def test_confirmed_booking_location_cta_uses_pin_or_encoded_address():
    from app.engines.messaging_gateway.flow import _location_cta

    pinned = _location_cta({
        "address_snapshot": {
            "address_line_1": "House 12",
            "maps_url": "https://maps.google.com/?q=30.7046,76.7179",
        },
        "city": "Bassi Pathana", "zipcode": "140412",
    })
    assert pinned["display_text"] == "Open location"
    assert pinned["url"] == "https://maps.google.com/?q=30.7046,76.7179"

    typed = _location_cta({
        "address_snapshot": {"address_line_1": "House 12, Main Road"},
        "city": "Ludhiana", "zipcode": "141001",
    })
    assert typed["url"].startswith("https://www.google.com/maps/search/?api=1&query=")
    assert "House+12%2C+Main+Road" in typed["url"]


def test_instagram_attachment_only_events_are_ignored():
    """Phone contact cards and location attachments are not customer answers."""
    empty_pin = {"object": "instagram", "entry": [{"id": "17890001", "messaging": [{
        "sender": {"id": "igsid-1"}, "recipient": {"id": "17890001"},
        "message": {"mid": "igmid.location.empty", "attachments": [{
            "type": "template", "payload": {"generic": {"elements": []}},
        }]},
    }]}]}
    assert meta_client.parse_inbound(
        empty_pin, expected_channel=CHANNEL_INSTAGRAM,
    ) == []

    coordinate_pin = {"object": "instagram", "entry": [{"id": "17890001", "messaging": [{
        "sender": {"id": "igsid-1"}, "recipient": {"id": "17890001"},
        "message": {"mid": "igmid.location.coordinates", "attachments": [{
            "type": "location", "payload": {
                "coordinates": {"lat": 30.7046, "long": 76.7179,
                                "name": "Home", "address": "New Sarian"},
            },
        }]},
    }]}]}
    assert meta_client.parse_inbound(
        coordinate_pin, expected_channel=CHANNEL_INSTAGRAM,
    ) == []


def test_instagram_phone_contact_card_does_not_duplicate_the_phone_answer():
    """Observed live: one typed number creates a text event and an empty
    generic-template contact card with a different mid. Only the text is real
    booking input, so only one confirmation card may be produced."""
    payload = {"object": "instagram", "entry": [{
        "id": "17890001", "messaging": [
            {
                "sender": {"id": "igsid-1"},
                "recipient": {"id": "17890001"},
                "message": {"mid": "igmid.phone.text", "text": "9041624576"},
            },
            {
                "sender": {"id": "igsid-1"},
                "recipient": {"id": "17890001"},
                "message": {"mid": "igmid.phone.card", "attachments": [{
                    "type": "template", "payload": {"generic": {"elements": []}},
                }]},
            },
        ],
    }]}

    messages = meta_client.parse_inbound(payload, expected_channel=CHANNEL_INSTAGRAM)
    assert len(messages) == 1
    assert messages[0].provider_message_id == "igmid.phone.text"
    assert messages[0].text == "9041624576"


@pytest.mark.asyncio
async def test_instagram_empty_location_keeps_the_customer_on_the_right_step(monkeypatch):
    """An old/empty attachment simply returns to the typed-address step."""
    from app.engines.messaging_gateway import flow

    class Thread:
        pass

    async def draft(_db, _thread):
        return {"id": "draft-1", "status": "collecting"}

    async def next_step(*args, **kwargs):
        return flow.Turn(flow.ASK_ADDRESS)

    monkeypatch.setattr(flow, "_executor", lambda db, thread: None)
    monkeypatch.setattr(flow, "_draft", draft)
    monkeypatch.setattr(flow, "_next_step", next_step)
    turn = await flow.advance(
        None, Thread(), text="", reply_id=None, channel=CHANNEL_INSTAGRAM,
        location_unavailable=True,
    )
    assert turn.text == flow.ASK_ADDRESS


@pytest.mark.asyncio
async def test_address_is_not_followed_by_a_second_location_prompt():
    """Both channels proceed after the one validated address question."""
    from app.engines.messaging_gateway import flow

    class Thread:
        id = "t"
        customer_id = "c-1"
        zipcode = "140412"
        city = "Bassi Pathana"
        ai_session_id = None

    # Address given, no pin: neither channel repeats the request as location.
    draft = {"id": "d-1", "job_type_id": "j-1", "zipcode": "140412",
             "address_snapshot": {"address_line_1": "House 4"}}

    async def _no_picker(*args, **kwargs):
        return None

    async def _match(*args, **kwargs):
        return flow.Turn("matched")

    async def _categories(db, zipcode):
        class Category:
            slug, name = "home_services", "Home Services"
        return [Category()]

    picker, flow.pickers.build_picker = flow.pickers.build_picker, _no_picker
    match, flow._match_step = flow._match_step, _match
    cats, flow._serviceable_categories = flow._serviceable_categories, _categories
    try:
        wa = await flow._next_step(None, Thread(), None, draft, CHANNEL_WHATSAPP, 0)
        assert wa.text == "matched"

        ig = await flow._next_step(None, Thread(), None, draft, CHANNEL_INSTAGRAM, 0)
        assert ig.text == "matched"
    finally:
        flow.pickers.build_picker = picker
        flow._match_step = match
        flow._serviceable_categories = cats


@pytest.mark.asyncio
async def test_whatsapp_combines_address_and_location_in_one_prompt(monkeypatch):
    from app.engines.messaging_gateway import flow

    class Thread:
        id = "t"
        customer_id = "c-1"
        zipcode = "140412"
        city = "Bassi Pathana"

    draft = {"id": "d-1", "job_type_id": "j-1", "zipcode": "140412",
             "address_snapshot": {}}

    async def no_picker(*args, **kwargs):
        return None

    async def covered(db, zipcode):
        return [object()]

    monkeypatch.setattr(flow.pickers, "build_picker", no_picker)
    monkeypatch.setattr(flow, "_serviceable_categories", covered)

    turn = await flow._next_step(None, Thread(), None, draft, CHANNEL_WHATSAPP, 0)
    assert turn.text == flow.ASK_ADDRESS_WHATSAPP
    assert "complete service address" in turn.text
    assert "location pin" in turn.text
    assert turn.picker is None


@pytest.mark.asyncio
async def test_booking_confirmation_does_not_append_location_cta(monkeypatch):
    from app.engines.messaging_gateway import flow

    class Thread:
        zipcode = "140412"
        customer_id = "c-1"

    draft = {"id": "d-1", "status": "collecting"}

    async def load_draft(*args, **kwargs):
        return draft

    async def no_navigation(*args, **kwargs):
        return None

    async def confirm(*args, **kwargs):
        return flow.CONFIRMED.format(number="BK-1"), flow.BOOKED, {
            **draft, "status": "confirmed",
        }

    async def booked_menu(*args, **kwargs):
        return flow.Turn(args[-1], {"body": "Next", "rows": []})

    monkeypatch.setattr(flow, "_executor", lambda db, thread: None)
    monkeypatch.setattr(flow, "_draft", load_draft)
    monkeypatch.setattr(flow, "_navigate", no_navigation)
    monkeypatch.setattr(flow, "_apply_tap", confirm)
    monkeypatch.setattr(flow, "_booked_menu_for", booked_menu)

    turn = await flow.advance(
        None, Thread(), text="", reply_id="cf|yes",
        channel=CHANNEL_WHATSAPP,
    )
    assert "BK-1" in turn.text
    assert "cta_url" not in turn.picker


@pytest.mark.asyncio
async def test_the_menu_only_offers_what_is_actually_open():
    """Seen live: cancelling the only booking still offered "Track my
    booking", a row whose whole answer was "there is no booking". Track and
    Cancel appear only while something is genuinely live; booking another
    service always is."""
    from app.engines.messaging_gateway import flow

    class Thread:
        id = "t"
        channel = "whatsapp"
        customer_id = "c-1"

    class Identity:
        def __init__(self, bookings):
            self.bookings = bookings

        async def live_bookings(self, thread):
            return self.bookings

        async def cancel_options(self, thread, booking_number):
            return {"can_cancel": True, "reasons": ["changed_mind"]}

        async def cancel_booking(self, thread, booking_number, reason):
            self.bookings = [b for b in self.bookings if b["number"] != booking_number]
            return flow.CANCELLED.format(number=booking_number)

    one = [{"number": "BK-1", "service": "AC Repair", "status": "Accepted"}]
    identity = Identity(list(one))

    # Cancelling the last booking leaves nothing to track.
    done = await flow._cancel_step(Thread(), identity, "BK-1|changed_mind",
                                   CHANNEL_WHATSAPP)
    assert "cancelled" in done.text
    assert [r["id"] for r in done.picker["rows"]] == ["rs|1"]

    # With something live, both Track and Cancel are there.
    open_menu = await flow._booked_menu_for(Identity(list(one)), Thread(), "", "hi")
    assert [r["id"] for r in open_menu.picker["rows"]] == ["tr|", "cx|", "rs|1"]


@pytest.mark.asyncio
async def test_cancelling_with_several_open_asks_which_service():
    """With more than one booking open, "Cancel booking" must name them —
    cancelling the newest by assumption is how the wrong job gets cancelled."""
    from app.engines.messaging_gateway import flow

    class Thread:
        id = "t"
        channel = "whatsapp"
        customer_id = "c-1"

    class Identity:
        bookings = [
            {"number": "BK-1", "service": "AC Repair", "status": "Accepted",
             "when": "Wed 02 Sep"},
            {"number": "BK-2", "service": "Geyser Repair", "status": "Assigned",
             "when": "Thu 03 Sep"},
        ]

        async def live_bookings(self, thread):
            return self.bookings

        async def cancel_options(self, thread, booking_number):
            return {"can_cancel": True, "reasons": ["changed_mind", "other"]}

    which = await flow._cancel_step(Thread(), Identity(), "", CHANNEL_WHATSAPP)
    assert which.picker["body"] == flow.ASK_WHICH_CANCEL
    assert [(r["title"], r["id"]) for r in which.picker["rows"][:2]] == [
        ("AC Repair", "cx|BK-1"), ("Geyser Repair", "cx|BK-2")]
    # Two bookings for the SAME service are only distinguishable by the visit,
    # so the row carries status, date and number rather than status alone.
    assert which.picker["rows"][0]["description"] == "Accepted · Wed 02 Sep · BK-1"

    # Naming one then moves on to why — the booking is still not cancelled.
    why = await flow._cancel_step(Thread(), Identity(), "BK-2", CHANNEL_WHATSAPP)
    assert why.picker["body"] == flow.ASK_CANCEL_REASON.format(number="BK-2")
    assert why.picker["rows"][0]["id"] == "cx|BK-2|changed_mind"


@pytest.mark.asyncio
async def test_a_parts_request_is_answered_in_chat_and_leads_the_conversation():
    """A technician who needs a part has stopped work, and the answer changes
    what the customer pays — so it outranks everything else in the chat and is
    decided with two taps, one request at a time."""
    from app.engines.messaging_gateway import flow

    class Thread:
        id = "t"
        channel = "whatsapp"
        customer_id = "c-1"

    class Identity:
        def __init__(self, pending):
            self.pending = pending
            self.decided = []

        async def pending_parts(self, thread):
            return self.pending

        async def parts_totals(self, thread, job_id):
            return {"currency": "INR", "previous_estimated_total": "849",
                    "new_estimated_total": "1299"}

        async def decide_parts(self, thread, parts_request_id, decision):
            self.decided.append((parts_request_id, decision))
            self.pending = self.pending[1:]
            return flow.PARTS_APPROVED if decision == "approve" else flow.PARTS_DECLINED

        async def live_bookings(self, thread):
            return []

    pending = [
        {"id": "pr-1", "job_id": "j-1", "booking_number": "BK-1",
         "part_name": "Compressor capacitor", "quantity": 1,
         "line_total": "450", "reason": "Original has failed"},
        {"id": "pr-2", "job_id": "j-1", "booking_number": "BK-1",
         "part_name": "Gas top-up", "quantity": 1, "line_total": "600",
         "reason": "Low pressure"},
    ]
    identity = Identity(list(pending))

    card = await flow._parts_step(identity, Thread(), CHANNEL_WHATSAPP)
    assert "Compressor capacitor × 1 — ₹450" in card.text
    assert "Why: Original has failed" in card.text
    # The customer is told what it does to the bill BEFORE deciding.
    assert "₹849 → ₹1,299" in card.text
    assert "1 more to review" in card.text
    assert [r["id"] for r in card.picker["rows"]] == [
        "pt|pr-1|approve", "pt|pr-1|decline"]

    # Approving moves straight to the next one rather than going quiet.
    nxt = await flow._navigate(None, None, "pt|pr-1|approve", None, Thread(),
                               CHANNEL_WHATSAPP, identity)
    assert identity.decided == [("pr-1", "approve")]
    assert nxt.text.startswith(flow.PARTS_APPROVED)
    assert "Gas top-up" in nxt.text
    assert nxt.picker["rows"][0]["id"] == "pt|pr-2|approve"

    # With none left, the conversation returns to the ordinary menu.
    last = await flow._navigate(None, None, "pt|pr-2|decline", None, Thread(),
                                CHANNEL_WHATSAPP, identity)
    assert last.text == flow.PARTS_DECLINED
    assert [r["id"] for r in last.picker["rows"]] == ["rs|1"]


@pytest.mark.asyncio
async def test_a_part_requested_before_any_quote_does_not_invent_a_prior_price():
    """`previous_estimated_total` is 0 when no quote exists yet — a real
    state, since a part can be requested before any estimate is sent. Showing
    "₹0 → ₹450" would quote a price we never gave."""
    from app.engines.messaging_gateway import flow

    class Thread:
        id = "t"
        channel = "whatsapp"
        customer_id = "c-1"

    class Identity:
        async def pending_parts(self, thread):
            return [{"id": "pr-1", "job_id": "j-1", "booking_number": None,
                     "part_name": "Capacitor", "quantity": 1,
                     "line_total": "450", "reason": None}]

        async def parts_totals(self, thread, job_id):
            return {"currency": "INR", "previous_estimated_total": "0",
                    "new_estimated_total": "450"}

    card = await flow._parts_step(Identity(), Thread(), CHANNEL_WHATSAPP)
    assert flow.PARTS_ADDS.format(total="₹450") in card.text
    assert "₹0" not in card.text


def test_every_real_non_terminal_execution_status_remains_trackable():
    """Tracking must survive the full field workflow, not only assignment."""
    from app.engines.execution.constants import (
        JS_ACCEPTED, JS_ASSIGNED, JS_CUSTOMER_NOT_AVAIL, JS_INSPECTION_DONE,
        JS_INSPECTION_STARTED, JS_ON_THE_WAY, JS_PENDING_ASSIGNMENT,
        JS_QUOTE_REQUIRED, JS_REACHED_SITE, JS_SCHEDULED, JS_SERVICE_STARTED,
        JS_WORK_DONE,
    )
    from app.engines.messaging_gateway.constants import LIVE_BOOKING_STATUSES

    assert {
        JS_PENDING_ASSIGNMENT, JS_ASSIGNED, JS_ACCEPTED, JS_SCHEDULED,
        JS_ON_THE_WAY, JS_REACHED_SITE, JS_INSPECTION_STARTED,
        JS_INSPECTION_DONE, JS_QUOTE_REQUIRED, JS_SERVICE_STARTED,
        JS_WORK_DONE, JS_CUSTOMER_NOT_AVAIL,
    }.issubset(set(LIVE_BOOKING_STATUSES))
    assert not {"en_route", "arrived", "in_progress", "on_hold"}.intersection(
        LIVE_BOOKING_STATUSES
    )


@pytest.mark.asyncio
async def test_a_stopped_thread_does_not_advance_silently(monkeypatch):
    """After /stop only explicit /fuvay may opt in and mutate a draft."""
    from unittest.mock import AsyncMock, MagicMock

    from app.engines.messaging_gateway.meta_client import InboundMessage
    from app.engines.messaging_gateway.service import MessagingGatewayService

    db = MagicMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    thread = MagicMock()
    thread.id = uuid.uuid4()
    thread.opted_out = True
    thread.human_handoff = False
    thread.blocked_until = None
    thread.last_inbound_at = None
    thread.last_options = None
    service = MessagingGatewayService(db, channel_config={})
    service.get_or_create_thread = AsyncMock(return_value=thread)
    service.resolve_customer = AsyncMock(return_value=None)
    service._advance = AsyncMock(return_value=("should not be sent", None))
    send = AsyncMock(return_value={"sent": True})
    monkeypatch.setattr("app.engines.messaging_gateway.meta_client.send_text", send)

    result = await service.handle_inbound(InboundMessage(
        channel="whatsapp", provider_message_id="wamid.stop.1",
        from_id="919876543210", business_id="123", message_type="text",
        text="hello again",
    ))

    service._advance.assert_not_awaited()
    send.assert_not_awaited()
    assert result["reply_sent"] is False


@pytest.mark.asyncio
async def test_instagram_fuvay_clears_old_area_and_sends_zipcode_prompt(monkeypatch):
    """The first step is plain text, so /fuvay must not discard it."""
    from unittest.mock import AsyncMock, MagicMock

    from app.engines.messaging_gateway import flow
    from app.engines.messaging_gateway.meta_client import InboundMessage
    from app.engines.messaging_gateway.service import MessagingGatewayService

    db = MagicMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    thread = MagicMock()
    thread.id = uuid.uuid4()
    thread.display_name = "Aman Customer"
    thread.zipcode = "140412"
    thread.city = "Bassi Pathana"
    thread.pending_customer_id = "old-customer"
    thread.pending_phone_ciphertext = "old-phone"
    thread.last_options = ["cat|home_services"]
    thread.opted_out = False
    thread.human_handoff = False
    thread.blocked_until = None
    thread.last_inbound_at = None

    service = MessagingGatewayService(db, channel_config={})
    service.get_or_create_thread = AsyncMock(return_value=thread)
    service.resolve_customer = AsyncMock(return_value=None)
    service._advance = AsyncMock(return_value=(flow.ASK_PINCODE, None))
    send = AsyncMock(return_value={"sent": True})
    monkeypatch.setattr("app.engines.messaging_gateway.meta_client.send_text", send)

    await service.handle_inbound(InboundMessage(
        channel=CHANNEL_INSTAGRAM, provider_message_id="igmid.start.zip",
        from_id="igsid-1", business_id="17890001", message_type="text",
        text="/fuvay",
    ))

    assert (thread.zipcode, thread.city, thread.last_options) == (None, None, None)
    assert thread.pending_customer_id is None
    assert thread.pending_phone_ciphertext is None
    sent_text = send.await_args.args[1]
    assert flow.ASK_PINCODE in sent_text
    service._advance.assert_awaited_once()


@pytest.mark.asyncio
async def test_old_instagram_service_button_cannot_skip_zipcode(monkeypatch):
    from app.engines.messaging_gateway import flow

    class Thread:
        zipcode = None
        city = None
        customer_id = None
        last_options = None

    async def no_draft(db, thread):
        return None

    monkeypatch.setattr(flow, "_executor", lambda db, thread: None)
    monkeypatch.setattr(flow, "_draft", no_draft)

    turn = await flow.advance(
        None, Thread(), text="", reply_id="cat|home_services",
        channel=CHANNEL_INSTAGRAM,
    )
    assert turn.text == flow.ASK_PINCODE
    assert turn.picker is None


@pytest.mark.asyncio
async def test_finished_booking_rejects_old_navigation_controls(monkeypatch):
    """Old category/area controls cannot reopen or alter a confirmed flow."""
    from app.engines.messaging_gateway import flow

    class Thread:
        id = "thread-1"
        channel = "whatsapp"
        channel_user_id = "919876543210"
        display_name = "Customer"
        customer_id = None
        ai_session_id = None
        zipcode = "141001"
        city = "Ludhiana"
        last_options = None

    async def finished(_db, _thread):
        return {"id": "draft-1", "status": "confirmed"}

    monkeypatch.setattr(flow, "_draft", finished)
    turn = await flow.advance(
        None, Thread(), text="", reply_id="cat|home_services",
        channel=CHANNEL_WHATSAPP,
    )
    assert "already confirmed" in turn.text
    assert [row["id"] for row in turn.picker["rows"]] == ["rs|1"]


@pytest.mark.asyncio
async def test_pending_quote_is_actionable_on_both_channels():
    """A chat-booked diagnostic job must not stall at quote_required."""
    from app.engines.messaging_gateway import flow

    quote = {
        "id": str(uuid.uuid4()), "quote_number": "QT-1001",
        "booking_number": "BK-1001", "currency": "INR", "amount": "1450",
        "notes": "Cooling circuit repair.",
        "items": [{"item_name": "Repair labour", "line_total": "1450"}],
    }

    class Thread:
        id = "thread-quote"
        customer_id = "customer-1"

    class Identity:
        def __init__(self):
            self.quotes = [quote]
            self.decision = None

        async def pending_quotes(self, thread):
            return self.quotes

        async def decide_quote(self, thread, quote_id, decision):
            self.decision = (quote_id, decision)
            self.quotes = []
            return flow.QUOTE_APPROVED

        async def live_bookings(self, thread):
            return []

    for channel in (CHANNEL_WHATSAPP, CHANNEL_INSTAGRAM):
        identity = Identity()
        card = await flow._quote_step(identity, Thread(), channel)
        assert "QT-1001" in card.text
        assert "Repair labour" in card.text
        assert [row["title"] for row in card.picker["rows"]] == [
            "Approve estimate", "Decline estimate", "Ask for changes",
        ]
        done = await flow._navigate(
            None, None, card.picker["rows"][0]["id"], None, Thread(),
            channel, identity,
        )
        assert identity.decision == (quote["id"], "approve")
        assert "approved" in done.text.lower()


# ── Opening a conversation ────────────────────────────────────────────────────
# Confirmed live on Instagram: a first message got no welcome, and a message
# sent hours later was answered with the previous conversation's coverage
# verdict, because the thread remembers its zipcode indefinitely.
#
# The trigger is the GAP, not a greeting word: a new or long-idle thread
# treats whatever arrives next as an opener. Inside the window only /fuvay
# and /reset restart, so a mid-booking "hi" is ordinary text.


def test_every_path_that_starts_a_booking_forgets_the_same_things():
    """One definition of what a new booking forgets. Three callers need it —
    /fuvay, the Start over tap and the idle reset — and while each inlined its
    own list the remembered zipcode survived one path and not another.

    opted_out and human_handoff are NOT in it: an hour of silence must not undo
    a /stop, nor hand an agent-owned thread back to the bot."""
    from app.engines.messaging_gateway import flow

    class Thread:
        ai_session_id = "s-1"
        zipcode = "160055"
        city = "Chandigarh"
        pending_customer_id = "c-1"
        pending_phone_ciphertext = "cipher"
        last_options = ["cat|home_services"]
        opted_out = True
        human_handoff = True

    thread = Thread()
    flow.reset_booking_state(thread)

    assert (thread.ai_session_id, thread.zipcode, thread.city) == (None, None, None)
    assert thread.pending_customer_id is None
    assert thread.pending_phone_ciphertext is None
    assert thread.last_options is None
    assert thread.opted_out and thread.human_handoff


def test_an_uncovered_area_says_how_to_reach_a_covered_one():
    """The flow already re-reads a bare 6-digit reply as a new pincode, so an
    uncovered area was never technically a dead end — but the message did not
    say so, which made it one in practice."""
    from app.engines.messaging_gateway import flow

    said = flow.NOT_IN_CITY.format(area="160055")
    assert "160055" in said
    assert "6-digit pincode" in said and "start again" in said


class _FakeResult:
    """Every read handle_inbound makes here is stubbed away, so it returns
    nothing rather than pretending to be a row."""

    def scalars(self):
        return self

    def first(self):
        return None

    def all(self):
        return []

    def scalar(self):
        return 0


class _FakeDB:
    """Enough AsyncSession for handle_inbound to run without a database."""

    def __init__(self):
        self.committed = 0

    def add(self, _obj):
        pass

    async def flush(self):
        pass

    async def commit(self):
        self.committed += 1

    async def rollback(self):
        pass

    async def execute(self, _stmt):
        return _FakeResult()


class _Thread:
    """A MessagingThread's fields without its mapper."""

    def __init__(self, **kw):
        self.id = uuid.uuid4()
        self.channel = CHANNEL_INSTAGRAM
        self.channel_user_id = "ig-1"
        self.display_name = None
        self.customer_id = None
        self.pending_customer_id = None
        self.pending_phone_ciphertext = None
        self.zipcode = None
        self.city = None
        self.last_options = None
        self.ai_session_id = None
        self.opted_out = False
        self.human_handoff = False
        self.blocked_until = None
        self.blocked_reason = None
        self.last_inbound_at = None
        self.last_outbound_at = None
        self.session_count = 0
        self.__dict__.update(kw)


def _inbound(text):
    from app.engines.messaging_gateway.meta_client import InboundMessage

    return InboundMessage(
        channel=CHANNEL_INSTAGRAM,
        provider_message_id=f"mid-{uuid.uuid4()}",
        from_id="ig-1",
        business_id="page-1",
        message_type="text",
        text=text,
    )


def _gateway(thread, monkeypatch, advance_reply):
    """A service wired to one thread, with the network and the flow stubbed.

    Only the parts handle_inbound is being tested for are real: the greeting
    decision, the staleness decision, and what the flow is handed.
    """
    from app.engines.messaging_gateway import meta_client, service as service_mod

    sent = []

    async def _send_text(to, text, channel, config):
        sent.append(text)
        return {"sent": True}

    async def _allow(**_kwargs):
        return True, {}

    monkeypatch.setattr(meta_client, "send_text", _send_text)
    monkeypatch.setattr(service_mod.rate_limiter, "check", _allow)

    gw = service_mod.MessagingGatewayService(_FakeDB())

    async def _thread(_msg):
        return thread

    async def _customer(_thread):
        return None

    async def _not_limited(_thread):
        return False

    async def _advance(passed, _msg, ignore_input=False):
        return advance_reply(passed, ignore_input), None

    gw.get_or_create_thread = _thread
    gw.resolve_customer = _customer
    gw._rate_limited = _not_limited
    gw._advance = _advance
    return gw, sent


@pytest.mark.asyncio
@pytest.mark.parametrize("opener", ["hi", "Hello", "🙏", "my AC is not cooling",
                                    "??", "kitna charge hoga"])
async def test_any_first_message_opens_the_conversation(monkeypatch, opener):
    """A new thread's first message is an OPENER, whatever it says. Matching a
    greeting word list missed the customer who starts with an emoji or states
    the problem outright, and both deserve the same welcome."""
    from app.engines.messaging_gateway.service import GREETING

    thread = _Thread()
    gw, sent = _gateway(thread, monkeypatch,
                        lambda _t, ignore_input: "Which pincode?")

    await gw.handle_inbound(_inbound(opener))

    assert len(sent) == 1
    # The welcome leads and carries the first question, so the customer does
    # not have to send a second message to get going.
    assert sent[0].startswith(GREETING.format(name=""))
    assert sent[0].endswith("Which pincode?")


@pytest.mark.asyncio
async def test_the_opening_message_is_not_read_as_an_answer(monkeypatch):
    """The opener is a knock on the door, not an answer. Feeding "hi" to the
    flow is what produced "that does not look like a pincode" as the very
    first thing a new customer was ever told."""
    thread = _Thread()
    seen = {}

    def _reply(_passed, ignore_input):
        seen["ignored"] = ignore_input
        return "Which pincode?"

    gw, sent = _gateway(thread, monkeypatch, _reply)
    await gw.handle_inbound(_inbound("hi"))

    assert seen["ignored"] is True


@pytest.mark.asyncio
async def test_a_message_after_an_hour_opens_a_new_conversation(monkeypatch):
    """THE reported bug. The thread remembers its zipcode indefinitely, so a
    customer whose pincode was uncovered yesterday was answered with that same
    verdict this morning. After the idle window the area is cleared before the
    message is read, so the reply is about this conversation, not the last."""
    from app.engines.messaging_gateway.constants import SESSION_IDLE_TIMEOUT_HOURS
    from app.engines.messaging_gateway.service import GREETING

    stale = datetime.now(timezone.utc) - timedelta(
        hours=SESSION_IDLE_TIMEOUT_HOURS, minutes=1)
    thread = _Thread(zipcode="160055", city="Chandigarh",
                     ai_session_id=uuid.uuid4(), last_options=["cat|x"],
                     last_inbound_at=stale)

    seen = {}

    def _reply(passed, _ignore):
        seen["zipcode"] = passed.zipcode
        return "Which pincode?"

    gw, sent = _gateway(thread, monkeypatch, _reply)
    await gw.handle_inbound(_inbound("hi"))

    # Cleared BEFORE the flow runs, so coverage cannot be re-checked against a
    # pincode from a finished conversation.
    assert seen["zipcode"] is None
    assert (thread.zipcode, thread.city) == (None, None)
    assert thread.last_options is None
    assert sent[0].startswith(GREETING.format(name=""))


@pytest.mark.asyncio
@pytest.mark.parametrize("text", ["hi", "hello", "start", "menu"])
async def test_a_greeting_mid_conversation_is_ordinary_text(monkeypatch, text):
    """Inside the window nothing restarts. Someone six questions into a
    booking who types "hi" as a filler line must not lose the booking -- that
    is what a greeting-word trigger got wrong."""
    recent = datetime.now(timezone.utc) - timedelta(minutes=10)
    session = uuid.uuid4()
    thread = _Thread(zipcode="141001", city="Ludhiana",
                     ai_session_id=session, last_inbound_at=recent)

    gw, sent = _gateway(thread, monkeypatch,
                        lambda _t, ignore_input: "Which slot?")

    result = await gw.handle_inbound(_inbound(text))

    assert result["command"] is None          # not routed as a start-over
    assert (thread.zipcode, thread.city) == ("141001", "Ludhiana")
    assert thread.ai_session_id == session
    assert sent == ["Which slot?"]            # no welcome, nothing lost


@pytest.mark.asyncio
@pytest.mark.parametrize("command", ["/fuvay", "/reset"])
async def test_only_an_explicit_command_restarts_inside_the_window(monkeypatch, command):
    """The one way to start over mid-conversation."""
    from app.engines.messaging_gateway.service import GREETING

    recent = datetime.now(timezone.utc) - timedelta(minutes=10)
    thread = _Thread(zipcode="141001", city="Ludhiana", last_inbound_at=recent)

    gw, sent = _gateway(thread, monkeypatch,
                        lambda _t, ignore_input: "Which pincode?")

    await gw.handle_inbound(_inbound(command))

    assert (thread.zipcode, thread.city) == (None, None)
    assert sent[0].startswith(GREETING.format(name=""))


@pytest.mark.asyncio
@pytest.mark.parametrize("tap", ["pt|req-1|approve", "qt|q-1|approve",
                                  "tr|BK-1", "cx|BK-1", "pay|p-1|confirm",
                                  "ho|j-1|acknowledge"])
async def test_a_durable_action_tap_is_never_swallowed_by_a_welcome(monkeypatch, tap):
    """A parts approval raised at 2pm and tapped at 5pm is the normal case.
    Answering it with a welcome would approve nothing and leave the technician
    waiting, so these taps are not openers however long the gap."""
    stale = datetime.now(timezone.utc) - timedelta(hours=9)
    thread = _Thread(zipcode="141001", city="Ludhiana", last_inbound_at=stale)

    gw, sent = _gateway(thread, monkeypatch,
                        lambda _t, ignore_input: "Approved.")

    msg = _inbound("Approve")
    msg.reply_id = tap
    await gw.handle_inbound(msg)

    # The tap reached the flow, and the booking context it refers to survives.
    assert sent == ["Approved."]
    assert thread.zipcode == "141001"


@pytest.mark.asyncio
async def test_an_ordinary_booking_tap_after_the_window_is_an_opener(monkeypatch):
    """A category tap from yesterday's list is not a pending question -- it is
    a new conversation, and must not resume a draft the customer has forgotten
    about."""
    from app.engines.messaging_gateway.service import GREETING

    stale = datetime.now(timezone.utc) - timedelta(hours=9)
    thread = _Thread(zipcode="160055", last_inbound_at=stale)

    gw, sent = _gateway(thread, monkeypatch,
                        lambda _t, ignore_input: "Which pincode?")

    msg = _inbound("Home Services")
    msg.reply_id = "cat|home_services"
    await gw.handle_inbound(msg)

    assert thread.zipcode is None
    assert sent[0].startswith(GREETING.format(name=""))


@pytest.mark.asyncio
async def test_going_quiet_does_not_undo_a_stop(monkeypatch):
    """/stop is durable. STOP_TEXT names /fuvay as the way back, so silence
    alone must not reopen the channel."""
    stale = datetime.now(timezone.utc) - timedelta(hours=9)
    thread = _Thread(zipcode="160055", opted_out=True, last_inbound_at=stale)

    gw, sent = _gateway(thread, monkeypatch,
                        lambda _t, ignore_input: "Which pincode?")

    await gw.handle_inbound(_inbound("hello"))

    assert sent == []
    assert thread.opted_out is True


@pytest.mark.asyncio
async def test_going_quiet_does_not_talk_over_a_human_agent(monkeypatch):
    """An agent owns the thread. Timing it out would wipe the context they are
    working from and put the bot back in the chat."""
    stale = datetime.now(timezone.utc) - timedelta(hours=9)
    thread = _Thread(zipcode="160055", city="Chandigarh",
                     human_handoff=True, last_inbound_at=stale)

    gw, sent = _gateway(thread, monkeypatch,
                        lambda _t, ignore_input: "Which pincode?")

    await gw.handle_inbound(_inbound("any update?"))

    assert sent == []
    assert (thread.zipcode, thread.city) == ("160055", "Chandigarh")
    assert thread.human_handoff is True


@pytest.mark.asyncio
async def test_an_explicit_command_is_answered_not_welcomed(monkeypatch):
    """A command carries its own answer. /help after a week is still help."""
    from app.engines.messaging_gateway.constants import HELP_TEXT

    stale = datetime.now(timezone.utc) - timedelta(days=7)
    thread = _Thread(last_inbound_at=stale)

    gw, sent = _gateway(thread, monkeypatch,
                        lambda _t, ignore_input: "Which pincode?")

    await gw.handle_inbound(_inbound("/help"))

    assert sent == [HELP_TEXT]


# ── Blueprint dimensions: type and brand, asked before the problem ─────────
def _dimension_rows(turn) -> list[dict]:
    """The picker's own options, without the trailing "Start over" row."""
    return [r for r in turn.picker["rows"] if str(r["id"]).startswith("dim|")]


class _DimensionDB:
    """Answers `_pending_dimension`'s queries by matching on the SQL text.

    Sequencing on call order would break the moment a query is added; matching
    on the table being read survives that.
    """

    def __init__(self, *, dimensions=None, types=None, brands=None, job_types=None):
        self.dimensions = dimensions if dimensions is not None else [
            ("type", "Type"), ("brand", "Brand"),
        ]
        self.types = types if types is not None else [("t-1", "Window AC"), ("t-2", "Split AC")]
        self.brands = brands if brands is not None else [("b-1", "Voltas")]
        self.job_types = job_types if job_types is not None else [("job-1",)]

    async def execute(self, clause, params=None):
        sql = str(clause)
        if "master_service_job_types" in sql:
            rows = self.job_types
        elif "service_job_dimensions" in sql:
            rows = self.dimensions
        elif "master_service_types" in sql:
            rows = self.types
        elif "master_service_brands" in sql:
            rows = self.brands
        else:
            rows = []
        return type("R", (), {"all": lambda _self, r=rows: list(r)})()


@pytest.mark.asyncio
async def test_type_is_asked_before_brand_and_both_before_the_problem():
    """Blueprint order drives the questions: type, then brand, then problem."""
    from app.engines.messaging_gateway import flow

    draft = {"id": "d-1", "offering_id": "svc-1"}

    turn = await flow._dimension_step(_DimensionDB(), draft, CHANNEL_INSTAGRAM, 0)
    assert _dimension_rows(turn) == [
        {"id": "dim|type|t-1", "title": "Window AC"},
        {"id": "dim|type|t-2", "title": "Split AC"},
    ]

    # Type answered -> brand is next, NOT the problem. Every picker carries a
    # trailing "Start over" row, so compare only the dimension's own options.
    draft["offering_type_id"] = "t-2"
    turn = await flow._dimension_step(_DimensionDB(), draft, CHANNEL_INSTAGRAM, 0)
    assert _dimension_rows(turn) == [{"id": "dim|brand|b-1", "title": "Voltas"}]

    # Both answered -> nothing outstanding, so the flow moves on to the problem.
    draft["brand_id"] = "b-1"
    assert await flow._dimension_step(_DimensionDB(), draft, CHANNEL_INSTAGRAM, 0) is None


@pytest.mark.asyncio
async def test_a_required_dimension_with_no_values_does_not_dead_end_the_booking():
    """A dimension nobody configured values for is skipped, not asked empty."""
    from app.engines.messaging_gateway import flow

    db = _DimensionDB(types=[])  # 'type' required, zero options to offer
    turn = await flow._dimension_step(db, {"id": "d-1", "offering_id": "svc-1"},
                                      CHANNEL_INSTAGRAM, 0)
    # Falls through to brand rather than rendering a question with no answers.
    assert _dimension_rows(turn) == [{"id": "dim|brand|b-1", "title": "Voltas"}]


@pytest.mark.asyncio
async def test_ambiguous_blueprint_leaves_the_problem_step_to_resolve_the_job_type():
    """Dimensions are keyed per job type, so two of them cannot be resolved
    from the service alone — the problem step must run first."""
    from app.engines.messaging_gateway import flow

    db = _DimensionDB(job_types=[("job-1",), ("job-2",)])
    assert await flow._dimension_step(db, {"id": "d-1", "offering_id": "svc-1"},
                                      CHANNEL_INSTAGRAM, 0) is None


@pytest.mark.asyncio
async def test_dimension_tap_writes_the_matching_draft_column():
    """`dim|brand|<id>` lands in brand_id, not in a generic answers blob."""
    from app.engines.messaging_gateway import flow

    written = {}

    class Executor:
        async def _tool_update_home_service_draft(self, draft_id, **fields):
            written.update(fields)
            return {"updated": True}

    async def _draft(_db, _thread):
        return {"id": "d-1", "brand_id": "b-9"}

    original, flow._draft = flow._draft, _draft
    try:
        await flow._apply_dimension(None, None, Executor(), "brand|b-9", {"id": "d-1"})
    finally:
        flow._draft = original

    assert written == {"brand_id": "b-9"}


# ── Flood controls ───────────────────────────────────────────────────────────
# Everything below is about the cheap abuse a booking flow invites: a sender
# who never books, but keeps the gateway working and keeps us paying Meta to
# answer. The expensive paths are a restart (two outbound messages plus a
# catalog read) and a reply of any kind, so each test asserts on what was SENT,
# not merely on the returned status.

def _limited_gateway(monkeypatch, thread=None, *, allow, advance_reply=None):
    """A gateway whose rate limiter answers per limit_type.

    `allow` maps a limit_type to True/False, or to an exception instance to
    simulate the limiter itself being unavailable. Anything unnamed is allowed.
    """
    from app.engines.messaging_gateway import meta_client, service as service_mod

    sent = []
    advanced = []

    async def _send_text(to, text, channel, config):
        sent.append(text)
        return {"sent": True}

    async def _check(*, limit_type, **_kwargs):
        verdict = allow.get(limit_type, True)
        if isinstance(verdict, Exception):
            raise verdict
        return verdict, {}

    async def _no_abuse_event(*_a, **_kw):
        return None

    monkeypatch.setattr(meta_client, "send_text", _send_text)
    monkeypatch.setattr(service_mod.rate_limiter, "check", _check)
    monkeypatch.setattr(service_mod, "record_abuse_event", _no_abuse_event)

    gw = service_mod.MessagingGatewayService(_FakeDB(), channel_config={})
    thread = thread if thread is not None else _Thread()

    async def _thread(_msg):
        return thread

    async def _customer(_thread):
        return None

    async def _not_limited(_thread):
        return False

    async def _advance(passed, _msg, ignore_input=False):
        advanced.append(ignore_input)
        return (advance_reply or "Which pincode?"), None

    gw.get_or_create_thread = _thread
    gw.resolve_customer = _customer
    gw._rate_limited = _not_limited
    gw._advance = _advance
    return gw, sent, advanced


@pytest.mark.asyncio
async def test_a_blocked_sender_is_read_but_never_answered(monkeypatch):
    """The operator block is the only silencer a spammer cannot lift.

    /stop is theirs and any /fuvay clears it, so before this the only way to
    stop a flood was to block the account in the Meta inbox -- outside the
    product, and invisible to our own inbound log. The message is still
    recorded here, on purpose: the flood has to stay visible to whoever set
    the block.
    """
    from app.engines.messaging_gateway import service as service_mod

    thread = _Thread(blocked_until=datetime.now(timezone.utc) + timedelta(hours=2))
    gw, sent, advanced = _limited_gateway(monkeypatch, thread, allow={})

    result = await gw.handle_inbound(_inbound("hello?"))

    assert result["blocked"] is True
    assert result["reply_sent"] is False
    assert sent == []
    # Never reached the flow: a block must not advance a draft either.
    assert advanced == []


@pytest.mark.asyncio
async def test_a_block_that_has_run_out_lets_the_customer_back_in(monkeypatch):
    """Blocks expire so an incident-time block does not become permanent."""
    thread = _Thread(blocked_until=datetime.now(timezone.utc) - timedelta(minutes=1))
    gw, sent, _ = _limited_gateway(monkeypatch, thread, allow={})

    result = await gw.handle_inbound(_inbound("hi"))

    assert result.get("blocked") is None
    assert len(sent) == 1


@pytest.mark.asyncio
async def test_a_naive_blocked_until_does_not_break_the_webhook(monkeypatch):
    """A timestamp read back naive must not raise.

    The column is timezone-aware, but this comparison sits in the webhook
    path -- an exception here is a non-200 to Meta, which redelivers the same
    message forever.
    """
    naive = (datetime.now(timezone.utc) + timedelta(hours=1)).replace(tzinfo=None)
    thread = _Thread(blocked_until=naive)
    gw, sent, _ = _limited_gateway(monkeypatch, thread, allow={})

    result = await gw.handle_inbound(_inbound("hello?"))

    assert result["blocked"] is True
    assert sent == []


@pytest.mark.asyncio
async def test_a_restart_loop_is_capped_without_resetting_the_draft(monkeypatch):
    """/fuvay is the expensive message, so it has its own cap.

    A restart drops the draft, re-reads the serviceable catalog and sends two
    outbound messages, and the per-message limit leaves room for dozens an
    hour. When the session cap trips, the customer keeps the conversation they
    already had -- the remembered service area in particular must survive, or
    the limit would itself do the damage the flood was after.
    """
    from app.engines.messaging_gateway import service as service_mod

    thread = _Thread(zipcode="140412", city="Bassi Pathana")
    gw, sent, advanced = _limited_gateway(
        monkeypatch, thread, allow={"booking:social_session": False})

    await gw.handle_inbound(_inbound("/fuvay"))

    assert sent == [service_mod.BUSY_TEXT]
    assert advanced == []
    assert thread.zipcode == "140412"
    assert thread.city == "Bassi Pathana"


@pytest.mark.asyncio
async def test_a_restart_inside_the_cap_still_works(monkeypatch):
    """The cap must not be so eager that an ordinary second booking trips it."""
    thread = _Thread(zipcode="140412")
    gw, sent, advanced = _limited_gateway(monkeypatch, thread, allow={})

    await gw.handle_inbound(_inbound("/fuvay"))

    assert advanced == [True]
    assert sent and sent[0].endswith("Which pincode?")


@pytest.mark.asyncio
async def test_a_flooding_sender_is_told_once_and_then_ignored(monkeypatch):
    """Dropping a flood in total silence reads as a dead bot, and a dead bot
    gets retried harder. One notice per window costs one message; the retries
    it prevents cost more. The notice limit is what makes it one."""
    from app.engines.messaging_gateway import service as service_mod

    gw, sent, _ = _limited_gateway(monkeypatch, allow={
        "booking:social_message": False,
        "booking:social_notice": True,
    })
    first = await gw.handle_inbound(_inbound("spam"))

    assert first["rate_limited"] is True
    assert sent == [service_mod.THROTTLE_TEXT]

    # Same window, notice budget now spent: the rest of the flood is silent.
    gw2, sent2, _ = _limited_gateway(monkeypatch, allow={
        "booking:social_message": False,
        "booking:social_notice": False,
    })
    second = await gw2.handle_inbound(_inbound("spam"))

    assert second["rate_limited"] is True
    assert second["reply_sent"] is False
    assert sent2 == []


@pytest.mark.asyncio
async def test_a_limiter_outage_never_messages_the_sender(monkeypatch):
    """When the limiter is down every message is refused -- and the notice
    throttle is down with it. Sending here would message every customer on
    every message for as long as Redis stayed away."""
    from app.exceptions import ServiceOSException

    gw, sent, _ = _limited_gateway(monkeypatch, allow={
        "booking:social_message": ServiceOSException("X", "limiter down"),
    })

    result = await gw.handle_inbound(_inbound("hello"))

    assert result["rate_limited"] is True
    assert sent == []


@pytest.mark.asyncio
async def test_the_channel_ceiling_drops_a_flood_without_replying(monkeypatch):
    """Every other limit is per sender, and an Instagram id is free to make.

    At the whole-channel ceiling the traffic is no longer one sender, so
    replying is exactly the amplification the ceiling exists to prevent.
    """
    gw, sent, _ = _limited_gateway(monkeypatch, allow={
        "booking:social_channel": False,
        "booking:social_notice": True,
    })

    result = await gw.handle_inbound(_inbound("spam"))

    assert result["rate_limited"] is True
    assert sent == []


@pytest.mark.asyncio
async def test_the_channel_ceiling_fails_open(monkeypatch):
    """A Redis blip must not take the page down for real customers. This is a
    backstop against a coordinated flood; failing closed on it would be a
    worse outage than the one it guards against."""
    from app.exceptions import ServiceOSException

    gw, sent, _ = _limited_gateway(monkeypatch, allow={
        "booking:social_channel": ServiceOSException("X", "limiter down"),
    })

    result = await gw.handle_inbound(_inbound("hi"))

    assert result.get("rate_limited") is None
    assert len(sent) == 1
