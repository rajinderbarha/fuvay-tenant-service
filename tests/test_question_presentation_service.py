"""CUSTOMER-ASSISTANT-UX-04 Parts 3/4 — DeepSeek presents, the backend decides.

Every test here exists to prove ONE property: DeepSeek can change how a
question is WORDED, and nothing else. It can never change which question
is active, which options exist, their ids, their order, or the language
the customer chose -- and any attempt to do so (or any malformed/timed-out
response) fails closed to the canonical backend question rather than
showing the customer something wrong.
"""
import json
from unittest.mock import AsyncMock, patch

import pytest

from app.engines.home_service_booking.question_presentation_service import (
    QuestionPresentationService, present_envelope, _validate, _canonical,
    _PRESENTATION_CACHE,
)


QUESTION = {
    "question_id": "q-brand",
    "question_key": "brand",
    "question_type": "single_select",
    "text": "Which AC brand do you have?",
    "required": True,
    "options": [
        {"id": "lg-id", "label": "LG"},
        {"id": "samsung-id", "label": "Samsung"},
        {"id": "voltas-id", "label": "Voltas"},
    ],
}


def _deepseek(payload: dict):
    """Patches the real DeepSeek client to return one structured payload."""
    return patch(
        "app.engines.ai_conversation.deepseek_client.DeepSeekClientService.chat",
        new=AsyncMock(return_value={"choices": [{"message": {"content": json.dumps(payload)}}]}),
    )


def _pa_payload(**overrides) -> dict:
    payload = {
        "question_id": "q-brand",
        "language": "pa",
        "message": "ਤੁਹਾਡੇ ਏਸੀ ਦਾ ਬ੍ਰਾਂਡ ਕਿਹੜਾ ਹੈ?",
        "options": [
            {"id": "lg-id", "label": "LG"},
            {"id": "samsung-id", "label": "Samsung"},
            {"id": "voltas-id", "label": "Voltas"},
        ],
    }
    payload.update(overrides)
    return payload


@pytest.fixture(autouse=True)
def _clear_cache():
    _PRESENTATION_CACHE.clear()
    yield
    _PRESENTATION_CACHE.clear()


# ── Validation: the mandatory checks from the spec ───────────────────────────

def test_valid_punjabi_presentation_is_accepted_with_canonical_option_ids():
    result = _validate(_pa_payload(), QUESTION, "pa")
    assert result is not None
    assert result["message"] == "ਤੁਹਾਡੇ ਏਸੀ ਦਾ ਬ੍ਰਾਂਡ ਕਿਹੜਾ ਹੈ?"
    assert [o["id"] for o in result["options"]] == ["lg-id", "samsung-id", "voltas-id"]


def test_a_different_question_id_is_rejected():
    assert _validate(_pa_payload(question_id="some-other-question"), QUESTION, "pa") is None


def test_a_different_language_is_rejected():
    assert _validate(_pa_payload(language="hi"), QUESTION, "pa") is None


def test_an_added_option_is_rejected():
    payload = _pa_payload()
    payload["options"].append({"id": "invented-id", "label": "Blue Star"})
    assert _validate(payload, QUESTION, "pa") is None


def test_a_removed_option_is_rejected():
    payload = _pa_payload()
    payload["options"].pop()
    assert _validate(payload, QUESTION, "pa") is None


def test_a_duplicated_option_is_rejected():
    payload = _pa_payload()
    payload["options"][1] = {"id": "lg-id", "label": "LG"}
    assert _validate(payload, QUESTION, "pa") is None


def test_reordered_options_are_rejected():
    payload = _pa_payload()
    payload["options"].reverse()
    assert _validate(payload, QUESTION, "pa") is None


def test_an_empty_message_is_rejected():
    assert _validate(_pa_payload(message="   "), QUESTION, "pa") is None


def test_a_blank_option_label_falls_back_to_the_canonical_label_for_that_option():
    payload = _pa_payload()
    payload["options"][0]["label"] = ""
    result = _validate(payload, QUESTION, "pa")
    assert result is not None
    assert result["options"][0] == {"id": "lg-id", "label": "LG"}


# ── Service behaviour: fail-closed, English passthrough, caching ─────────────

@pytest.mark.asyncio
async def test_english_is_presented_canonically_without_calling_deepseek():
    svc = QuestionPresentationService(db=None)
    with patch(
        "app.engines.ai_conversation.deepseek_client.DeepSeekClientService.chat",
        new=AsyncMock(side_effect=AssertionError("DeepSeek must not be called for English")),
    ):
        result = await svc.present(question=QUESTION, language="en")
    assert result["presented_by"] == "canonical"
    assert result["message"] == QUESTION["text"]


@pytest.mark.asyncio
async def test_an_unsupported_language_presents_canonically_rather_than_guessing():
    svc = QuestionPresentationService(db=None)
    result = await svc.present(question=QUESTION, language="fr")
    assert result["presented_by"] == "canonical"
    assert result["message"] == QUESTION["text"]


@pytest.mark.asyncio
async def test_punjabi_presentation_is_returned_when_deepseek_is_valid():
    svc = QuestionPresentationService(db=None)
    with _deepseek(_pa_payload()):
        result = await svc.present(question=QUESTION, language="pa")
    assert result["presented_by"] == "deepseek"
    assert result["message"] == "ਤੁਹਾਡੇ ਏਸੀ ਦਾ ਬ੍ਰਾਂਡ ਕਿਹੜਾ ਹੈ?"
    assert [o["id"] for o in result["options"]] == ["lg-id", "samsung-id", "voltas-id"]


@pytest.mark.asyncio
async def test_hindi_presentation_is_returned_when_deepseek_is_valid():
    svc = QuestionPresentationService(db=None)
    hindi = _pa_payload(language="hi", message="आपके एसी का ब्रांड कौन सा है?")
    with _deepseek(hindi):
        result = await svc.present(question=QUESTION, language="hi")
    assert result["presented_by"] == "deepseek"
    assert result["message"] == "आपके एसी का ब्रांड कौन सा है?"


@pytest.mark.asyncio
async def test_an_invented_option_fails_closed_to_the_canonical_question():
    payload = _pa_payload()
    payload["options"].append({"id": "invented", "label": "Blue Star"})
    svc = QuestionPresentationService(db=None)
    with _deepseek(payload):
        result = await svc.present(question=QUESTION, language="pa")
    assert result["presented_by"] == "canonical"
    assert result["message"] == QUESTION["text"]
    assert [o["id"] for o in result["options"]] == ["lg-id", "samsung-id", "voltas-id"]


@pytest.mark.asyncio
async def test_a_deepseek_failure_fails_closed_without_surfacing_an_error():
    from app.exceptions import ServiceOSException
    svc = QuestionPresentationService(db=None)
    with patch(
        "app.engines.ai_conversation.deepseek_client.DeepSeekClientService.chat",
        new=AsyncMock(side_effect=ServiceOSException("DEEPSEEK_TIMEOUT", "timeout", status_code=504)),
    ):
        result = await svc.present(question=QUESTION, language="pa")
    assert result["presented_by"] == "canonical"
    assert result["message"] == QUESTION["text"]


@pytest.mark.asyncio
async def test_malformed_json_fails_closed():
    svc = QuestionPresentationService(db=None)
    with patch(
        "app.engines.ai_conversation.deepseek_client.DeepSeekClientService.chat",
        new=AsyncMock(return_value={"choices": [{"message": {"content": "not json at all"}}]}),
    ):
        result = await svc.present(question=QUESTION, language="pa")
    assert result["presented_by"] == "canonical"


@pytest.mark.asyncio
async def test_a_validated_presentation_is_cached_and_not_re_requested():
    svc = QuestionPresentationService(db=None)
    chat = AsyncMock(return_value={"choices": [{"message": {"content": json.dumps(_pa_payload())}}]})
    with patch("app.engines.ai_conversation.deepseek_client.DeepSeekClientService.chat", new=chat):
        first = await svc.present(question=QUESTION, language="pa")
        second = await svc.present(question=QUESTION, language="pa")
    assert first["presented_by"] == "deepseek"
    assert second["presented_by"] == "cache"
    assert second["message"] == first["message"]
    assert chat.await_count == 1


@pytest.mark.asyncio
async def test_editing_the_catalog_question_invalidates_the_cached_presentation():
    """Admin edits must never keep serving a stale translation."""
    svc = QuestionPresentationService(db=None)
    chat = AsyncMock(return_value={"choices": [{"message": {"content": json.dumps(_pa_payload())}}]})
    with patch("app.engines.ai_conversation.deepseek_client.DeepSeekClientService.chat", new=chat):
        await svc.present(question=QUESTION, language="pa")
        edited = {**QUESTION, "text": "Which brand is your air conditioner?"}
        await svc.present(question=edited, language="pa")
    assert chat.await_count == 2


@pytest.mark.asyncio
async def test_the_same_question_in_a_different_language_is_a_separate_cache_entry():
    svc = QuestionPresentationService(db=None)
    chat = AsyncMock(side_effect=[
        {"choices": [{"message": {"content": json.dumps(_pa_payload())}}]},
        {"choices": [{"message": {"content": json.dumps(_pa_payload(language="hi", message="हिन्दी"))}}]},
    ])
    with patch("app.engines.ai_conversation.deepseek_client.DeepSeekClientService.chat", new=chat):
        await svc.present(question=QUESTION, language="pa")
        await svc.present(question=QUESTION, language="hi")
    assert chat.await_count == 2


# ── Envelope integration: semantics survive presentation untouched ──────────

@pytest.mark.asyncio
async def test_present_envelope_translates_display_text_only_and_preserves_every_semantic_field():
    envelope = {
        "envelope_version": 1,
        "draft_id": "draft-1",
        "question_flow_version": 3,
        "current_question": QUESTION,
        "progress": {"answered_count": 1, "remaining_count": 2, "complete": False},
        "next_permitted_actions": ["submit_answer"],
    }
    with _deepseek(_pa_payload()):
        result = await present_envelope(db=None, envelope=envelope, language="pa")

    q = result["current_question"]
    # Display changed...
    assert q["text"] == "ਤੁਹਾਡੇ ਏਸੀ ਦਾ ਬ੍ਰਾਂਡ ਕਿਹੜਾ ਹੈ?"
    assert q["canonical_text"] == "Which AC brand do you have?"
    # ...every semantic field did not.
    assert q["question_id"] == "q-brand"
    assert q["question_key"] == "brand"
    assert q["question_type"] == "single_select"
    assert q["required"] is True
    assert [o["id"] for o in q["options"]] == ["lg-id", "samsung-id", "voltas-id"]
    assert result["question_flow_version"] == 3
    assert result["progress"] == {"answered_count": 1, "remaining_count": 2, "complete": False}
    assert result["next_permitted_actions"] == ["submit_answer"]


@pytest.mark.asyncio
async def test_present_envelope_returns_the_envelope_unchanged_when_no_language_is_given():
    envelope = {"current_question": QUESTION, "progress": {"complete": False}}
    result = await present_envelope(db=None, envelope=envelope, language=None)
    assert result is envelope


@pytest.mark.asyncio
async def test_present_envelope_leaves_a_completed_flow_untouched():
    """No active question means nothing to present -- never an error."""
    envelope = {"current_question": None, "progress": {"complete": True}}
    result = await present_envelope(db=None, envelope=envelope, language="pa")
    assert result is envelope
