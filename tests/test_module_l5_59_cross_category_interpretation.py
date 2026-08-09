"""MODULE-L5-59 — the assistant's interpreter sees the whole catalogue.

The bug: `OfferingInterpretationService.interpret` was given ONE category's issue
list, so a customer who typed "my tap is leaking" in a conversation entered from an
AC service card could not be matched against anything real -- every interpretation
came back AC-shaped. The model was not at fault; it was never shown the plumbing
catalogue.

Verified live after the fix, on the real 140412 catalogue:
    "my tap is leaking in the kitchen"  -> Plumbing / Pipe Leaking
    "there is no light in the bathroom" -> Electrical / Power Not Working
    "cockroaches everywhere"            -> Pest Control / Pest Infestation
    "my ac is not cooling"              -> Air Conditioning / AC Not Cooling
"""
from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.engines.home_service_booking.offering_interpretation_service import (
    MATCH_CONFIDENCE_THRESHOLD, OfferingInterpretationService,
)

CATALOGUE = {
    "issues": [
        {"id": "ac-1", "label": "AC Not Cooling", "category_slug": "air-conditioning",
         "category_name": "Air Conditioning", "category_id": "cat-ac"},
        {"id": "pl-1", "label": "Pipe Leaking", "category_slug": "plumbing",
         "category_name": "Plumbing", "category_id": "cat-pl"},
        {"id": "el-1", "label": "Power Not Working", "category_slug": "electrical",
         "category_name": "Electrical", "category_id": "cat-el"},
    ],
    "total": 3,
}


def _svc() -> OfferingInterpretationService:
    return OfferingInterpretationService(db=AsyncMock(), request_id="test-req")


def _deepseek(reply: dict):
    """A DeepSeek client whose one response is `reply`."""
    client = MagicMock()
    client.chat = AsyncMock(return_value={
        "choices": [{"message": {"content": json.dumps(reply)}}],
    })
    return client


async def _interpret(svc, reply, text="my tap is leaking"):
    with patch(
        "app.engines.home_service_booking.offering_interpretation_service"
        ".list_serviceable_issues_across_categories",
        AsyncMock(return_value=CATALOGUE),
    ), patch(
        "app.engines.home_service_booking.offering_interpretation_service.DeepSeekClientService",
        return_value=_deepseek(reply),
    ):
        return await svc.interpret_across_categories(zipcode="140412", text=text)


@pytest.mark.asyncio
async def test_a_match_outside_the_entered_category_is_returned_with_its_category():
    """The whole fix: the caller must be able to start the draft in the matched
    problem's OWN category, not the one the conversation happened to enter with."""
    result = await _interpret(_svc(), {
        "action": "match_option", "reply": "Got it, a leaking pipe.",
        "matched_issue_id": "pl-1", "confidence": 0.9,
    })
    assert result["action"] == "match_option"
    assert result["matched_offering"]["name"] == "Pipe Leaking"
    assert result["matched_offering"]["category_slug"] == "plumbing"
    assert result["matched_offering"]["category_name"] == "Plumbing"


@pytest.mark.asyncio
async def test_the_model_is_shown_every_category_grouped():
    """Grouped rather than flat, so "which category is this?" is answerable from
    the same structure the model matches against."""
    captured = {}

    def _capture(**kwargs):
        client = MagicMock()

        async def chat(messages):
            captured["system"] = messages[0]["content"]
            return {"choices": [{"message": {"content": json.dumps({
                "action": "cannot_answer", "reply": "?", "matched_issue_id": None, "confidence": 0,
            })}}]}

        client.chat = chat
        return client

    with patch(
        "app.engines.home_service_booking.offering_interpretation_service"
        ".list_serviceable_issues_across_categories",
        AsyncMock(return_value=CATALOGUE),
    ), patch(
        "app.engines.home_service_booking.offering_interpretation_service.DeepSeekClientService",
        _capture,
    ):
        await _svc().interpret_across_categories(zipcode="140412", text="anything")

    for category in ("Air Conditioning", "Plumbing", "Electrical"):
        assert category in captured["system"]
    # And it is told not to assume the first one.
    assert "do not assume" in captured["system"].lower()


@pytest.mark.asyncio
async def test_a_hallucinated_issue_id_cannot_start_a_draft():
    result = await _interpret(_svc(), {
        "action": "match_option", "reply": "Sure.",
        "matched_issue_id": "made-up-id", "confidence": 0.99,
    })
    assert result["action"] == "ask_clarification"
    assert result["matched_offering"] is None


@pytest.mark.asyncio
async def test_a_low_confidence_guess_becomes_a_question_rather_than_an_action():
    result = await _interpret(_svc(), {
        "action": "match_option", "reply": "Maybe the AC?",
        "matched_issue_id": "ac-1", "confidence": MATCH_CONFIDENCE_THRESHOLD - 0.1,
    })
    assert result["action"] == "ask_clarification"
    assert result["matched_offering"] is None


@pytest.mark.asyncio
async def test_an_action_the_backend_does_not_recognise_is_refused():
    result = await _interpret(_svc(), {
        "action": "book_it_now", "reply": "Booking!", "matched_issue_id": "ac-1", "confidence": 1,
    })
    assert result["action"] == "cannot_answer"
    assert result["matched_offering"] is None


@pytest.mark.asyncio
async def test_the_real_issue_list_always_comes_back_for_the_ui_to_fall_back_on():
    # So a client never has to infer what to render next from the reply text.
    result = await _interpret(_svc(), {
        "action": "ask_clarification", "reply": "Which one?",
        "matched_issue_id": None, "confidence": 0,
    })
    assert [i["name"] for i in result["offerings"]] == [
        "AC Not Cooling", "Pipe Leaking", "Power Not Working",
    ]


@pytest.mark.asyncio
async def test_an_unusable_model_response_degrades_to_a_question():
    """Transport failures, non-JSON bodies and JSON that is not an object all
    collapse to the same honest fallback rather than surfacing as an error."""
    svc = _svc()
    client = MagicMock()
    client.chat = AsyncMock(return_value={"choices": [{"message": {"content": "not json"}}]})
    with patch(
        "app.engines.home_service_booking.offering_interpretation_service"
        ".list_serviceable_issues_across_categories",
        AsyncMock(return_value=CATALOGUE),
    ), patch(
        "app.engines.home_service_booking.offering_interpretation_service.DeepSeekClientService",
        return_value=client,
    ):
        result = await svc.interpret_across_categories(zipcode="140412", text="hello")
    assert result["action"] == "cannot_answer"
    assert result["matched_offering"] is None
    assert result["offerings"]


@pytest.mark.asyncio
async def test_no_serviceable_issue_anywhere_is_refused_not_faked():
    from app.exceptions import ServiceOSException
    with patch(
        "app.engines.home_service_booking.offering_interpretation_service"
        ".list_serviceable_issues_across_categories",
        AsyncMock(return_value={"issues": [], "total": 0}),
    ):
        with pytest.raises(ServiceOSException):
            await _svc().interpret_across_categories(zipcode="999999", text="anything")
