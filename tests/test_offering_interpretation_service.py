"""Backend-first Booking Assistant Phase 10: constrained issue-selection
interpretation (`OfferingInterpretationService` now resolves over the
real, zipcode-serviceable ISSUE catalog -- see offering_catalog_service.
list_serviceable_issues -- not bare offerings, per the "Brand appears
before any real issue selection" root-cause fix). Mocks
`DeepSeekClientService.chat` only -- exercises the real, live
140412/Guramrit issue catalog for validation.
"""
import json
from unittest.mock import AsyncMock, patch

import pytest


ZIPCODE_140412 = "140412"

_ISSUES = [
    {"id": "gas-refill", "label": "Gas Refill Needed"},
    {"id": "new-installation", "label": "New AC Installation"},
]


async def _catalog(*_args, **_kwargs):
    return {"category": "Air Conditioning", "issues": _ISSUES}


async def _get_db():
    from app.database import get_session_factory, init_db
    await init_db()
    return get_session_factory()()


def _deepseek_response(payload: dict) -> dict:
    return {"choices": [{"message": {"content": json.dumps(payload)}}]}


@pytest.mark.asyncio
async def test_free_text_matches_the_correct_issue():
    from app.engines.home_service_booking.offering_interpretation_service import OfferingInterpretationService
    from app.engines.home_service_booking.offering_catalog_service import list_serviceable_issues

    db = await _get_db()
    try:
        gas = _ISSUES[0]

        svc = OfferingInterpretationService(db=db)
        with patch("app.engines.home_service_booking.offering_interpretation_service.list_serviceable_issues", new=_catalog), patch(
            "app.engines.ai_conversation.deepseek_client.DeepSeekClientService.chat",
            new=AsyncMock(return_value=_deepseek_response({
                "action": "match_option", "reply": "Gas refilling it is.",
                "matched_issue_id": gas["id"], "confidence": 0.95,
            })),
        ):
            result = await svc.interpret(category_slug="air-conditioning", zipcode=ZIPCODE_140412, text="I need gas in my AC.")

        assert result["action"] == "match_option"
        assert result["matched_offering"]["id"] == gas["id"]
    finally:
        await db.close()


@pytest.mark.asyncio
async def test_invented_issue_id_is_rejected():
    from app.engines.home_service_booking.offering_interpretation_service import OfferingInterpretationService

    db = await _get_db()
    try:
        svc = OfferingInterpretationService(db=db)
        with patch("app.engines.home_service_booking.offering_interpretation_service.list_serviceable_issues", new=_catalog), patch(
            "app.engines.ai_conversation.deepseek_client.DeepSeekClientService.chat",
            new=AsyncMock(return_value=_deepseek_response({
                "action": "match_option", "reply": "Sure!",
                "matched_issue_id": "invented-issue-id", "confidence": 0.99,
            })),
        ):
            result = await svc.interpret(category_slug="air-conditioning", zipcode=ZIPCODE_140412, text="I need something weird.")

        assert result["action"] == "ask_clarification"
        assert result["matched_offering"] is None
    finally:
        await db.close()


@pytest.mark.asyncio
async def test_low_confidence_match_repeats_issue_prompt():
    from app.engines.home_service_booking.offering_interpretation_service import OfferingInterpretationService
    from app.engines.home_service_booking.offering_catalog_service import list_serviceable_issues

    db = await _get_db()
    try:
        install = _ISSUES[1]

        svc = OfferingInterpretationService(db=db)
        with patch("app.engines.home_service_booking.offering_interpretation_service.list_serviceable_issues", new=_catalog), patch(
            "app.engines.ai_conversation.deepseek_client.DeepSeekClientService.chat",
            new=AsyncMock(return_value=_deepseek_response({
                "action": "match_option", "reply": "Maybe installation?",
                "matched_issue_id": install["id"], "confidence": 0.3,
            })),
        ):
            result = await svc.interpret(category_slug="air-conditioning", zipcode=ZIPCODE_140412, text="not sure what I need")

        assert result["action"] == "ask_clarification"
        assert result["matched_offering"] is None
    finally:
        await db.close()


@pytest.mark.asyncio
async def test_unrelated_message_is_redirected_to_issue_choices():
    from app.engines.home_service_booking.offering_interpretation_service import OfferingInterpretationService

    db = await _get_db()
    try:
        svc = OfferingInterpretationService(db=db)
        with patch("app.engines.home_service_booking.offering_interpretation_service.list_serviceable_issues", new=_catalog), patch(
            "app.engines.ai_conversation.deepseek_client.DeepSeekClientService.chat",
            new=AsyncMock(return_value=_deepseek_response({
                "action": "out_of_scope",
                "reply": "I can help with your AC booking. What do you need help with?",
                "matched_issue_id": None, "confidence": 0.0,
            })),
        ):
            result = await svc.interpret(category_slug="air-conditioning", zipcode=ZIPCODE_140412, text="What is today's cricket score?")

        assert result["action"] == "out_of_scope"
        assert len(result["offerings"]) >= 2
    finally:
        await db.close()


@pytest.mark.asyncio
async def test_out_of_area_zipcode_raises_instead_of_calling_deepseek():
    from app.engines.home_service_booking.offering_interpretation_service import OfferingInterpretationService
    from app.exceptions import ServiceOSException

    db = await _get_db()
    try:
        svc = OfferingInterpretationService(db=db)
        async def empty_catalog(*_args, **_kwargs):
            return {"category": "Air Conditioning", "issues": []}
        with patch("app.engines.home_service_booking.offering_interpretation_service.list_serviceable_issues", new=empty_catalog), patch(
            "app.engines.ai_conversation.deepseek_client.DeepSeekClientService.chat",
            new=AsyncMock(side_effect=AssertionError("DeepSeek must not be called with zero real issues")),
        ):
            with pytest.raises(ServiceOSException):
                await svc.interpret(category_slug="air-conditioning", zipcode="999999", text="AC gas refill please")
    finally:
        await db.close()


@pytest.mark.asyncio
async def test_malformed_deepseek_output_fails_closed():
    from app.engines.home_service_booking.offering_interpretation_service import OfferingInterpretationService

    db = await _get_db()
    try:
        svc = OfferingInterpretationService(db=db)
        with patch("app.engines.home_service_booking.offering_interpretation_service.list_serviceable_issues", new=_catalog), patch(
            "app.engines.ai_conversation.deepseek_client.DeepSeekClientService.chat",
            new=AsyncMock(return_value={"choices": [{"message": {"content": "not json"}}]}),
        ):
            result = await svc.interpret(category_slug="air-conditioning", zipcode=ZIPCODE_140412, text="hmm")
        assert result["action"] == "cannot_answer"
        assert result["matched_offering"] is None
    finally:
        await db.close()
