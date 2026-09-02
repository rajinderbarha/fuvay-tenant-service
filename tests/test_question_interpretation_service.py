"""Backend-first-with-DeepSeek-on-demand: `QuestionInterpretationService` is
the ONLY place DeepSeek is consulted while a canonical question is active,
and it must never be able to write to the draft directly, invent an
option, change which question is active, or advance the flow. These tests
mock `DeepSeekClientService.chat` (never a real network call) and use the
real, live 140412/Guramrit AC Installation data so `QuestionFlowService`
itself is exercised for real -- only the DeepSeek call is faked.
"""
import json
import uuid
from unittest.mock import AsyncMock, patch

import pytest

pytestmark = pytest.mark.skip(
    reason="legacy test depended on deleted Guramrit/140412 AC demo catalog data",
)


AC_INSTALLATION_ID = uuid.UUID("b598ad10-938e-4754-83bd-63b2fe626f20")
AC_CATEGORY_ID = uuid.UUID("59d8f3aa-932d-429e-93bd-8d4f2ed615c3")
CUSTOMER_ID = uuid.UUID("fa198861-455b-43f2-a426-47da0a8811af")
ZIPCODE_140412 = "140412"


async def _get_db():
    from app.database import get_session_factory, init_db
    await init_db()
    return get_session_factory()()


def _deepseek_response(payload: dict) -> dict:
    return {"choices": [{"message": {"content": json.dumps(payload)}}]}


async def _make_ac_installation_draft(db):
    from app.engines.home_service_booking.service import HomeServiceChatbotBookingService
    svc = HomeServiceChatbotBookingService(db=db)
    draft_dict = await svc.start_booking_draft(
        customer_id=CUSTOMER_ID, ai_session_id=None,
        category_slug="air-conditioning", offering_slug="ac-installation",
    )
    draft_id = uuid.UUID(draft_dict["id"])

    from sqlalchemy import select
    from app.engines.admin_catalog.models import MasterIssueType
    issue = (await db.execute(
        select(MasterIssueType).where(MasterIssueType.master_service_id == AC_INSTALLATION_ID)
    )).scalars().first()
    await svc.update_draft_fields(draft_id=draft_id, customer_id=CUSTOMER_ID, payload={"selected_problem_id": str(issue.id)})
    return draft_id


async def _cleanup(db, draft_id):
    from sqlalchemy import text
    await db.rollback()
    async with db.begin():
        await db.execute(text("DELETE FROM home_service_booking_drafts WHERE id = :id"), {"id": draft_id})


@pytest.mark.asyncio
async def test_free_text_matches_the_correct_option_and_submits_through_canonical_path():
    """'Mine is a Samsung.' against the real Brand question must resolve
    to the real Samsung option id and submit it through QuestionFlowService
    -- never write to the draft any other way."""
    from app.engines.home_service_booking.question_interpretation_service import QuestionInterpretationService
    from app.engines.home_service_booking.question_flow_service import QuestionFlowService

    db = await _get_db()
    draft_id = None
    try:
        draft_id = await _make_ac_installation_draft(db)
        qf = QuestionFlowService(db=db)
        envelope = await qf.get_current_question(draft_id=draft_id, customer_id=CUSTOMER_ID)
        question = envelope["current_question"]
        assert question["question_key"] == "brand"
        samsung = next(o for o in question["options"] if o["label"] == "Samsung")

        qi = QuestionInterpretationService(db=db)
        with patch(
            "app.engines.ai_conversation.deepseek_client.DeepSeekClientService.chat",
            new=AsyncMock(return_value=_deepseek_response({
                "action": "match_option", "reply": "Samsung",
                "current_question_id": question["question_id"],
                "matched_option_id": samsung["id"], "confidence": 0.95,
            })),
        ):
            result = await qi.interpret(draft_id=draft_id, customer_id=CUSTOMER_ID, text="Mine is a Samsung.")

        assert result["action"] == "match_option"
        # The question flow must have genuinely advanced -- Samsung is no
        # longer the active question once submitted.
        assert result["envelope"]["current_question"]["question_id"] != question["question_id"]

        # Independently re-fetch to prove the answer really persisted via
        # the canonical service, not just echoed in the response.
        after = await qf.get_current_question(draft_id=draft_id, customer_id=CUSTOMER_ID)
        answered_keys = {a["question_key"] for a in after["answered_questions"]}
        assert "brand" in answered_keys
    finally:
        if draft_id is not None:
            await _cleanup(db, draft_id)
        await db.close()


@pytest.mark.asyncio
async def test_invented_option_is_rejected_and_canonical_question_repeats():
    """An option id DeepSeek invents (not in the real allowed list) must
    never reach submit_answer -- the same canonical question is returned
    unchanged instead."""
    from app.engines.home_service_booking.question_interpretation_service import QuestionInterpretationService
    from app.engines.home_service_booking.question_flow_service import QuestionFlowService

    db = await _get_db()
    draft_id = None
    try:
        draft_id = await _make_ac_installation_draft(db)
        qf = QuestionFlowService(db=db)
        envelope = await qf.get_current_question(draft_id=draft_id, customer_id=CUSTOMER_ID)
        question = envelope["current_question"]

        qi = QuestionInterpretationService(db=db)
        with patch(
            "app.engines.ai_conversation.deepseek_client.DeepSeekClientService.chat",
            new=AsyncMock(return_value=_deepseek_response({
                "action": "match_option", "reply": "Sure, Daikin it is!",
                "current_question_id": question["question_id"],
                "matched_option_id": "invented-option-id-not-real", "confidence": 0.99,
            })),
        ):
            result = await qi.interpret(draft_id=draft_id, customer_id=CUSTOMER_ID, text="I have a Daikin.")

        assert result["action"] == "ask_clarification"
        assert result["envelope"]["current_question"]["question_id"] == question["question_id"]

        after = await qf.get_current_question(draft_id=draft_id, customer_id=CUSTOMER_ID)
        assert after["current_question"]["question_id"] == question["question_id"]
        assert after["answered_questions"] == []
    finally:
        if draft_id is not None:
            await _cleanup(db, draft_id)
        await db.close()


@pytest.mark.asyncio
async def test_low_confidence_match_repeats_the_current_question_instead_of_guessing():
    from app.engines.home_service_booking.question_interpretation_service import QuestionInterpretationService
    from app.engines.home_service_booking.question_flow_service import QuestionFlowService

    db = await _get_db()
    draft_id = None
    try:
        draft_id = await _make_ac_installation_draft(db)
        qf = QuestionFlowService(db=db)
        envelope = await qf.get_current_question(draft_id=draft_id, customer_id=CUSTOMER_ID)
        question = envelope["current_question"]
        lg = next(o for o in question["options"] if o["label"] == "LG")

        qi = QuestionInterpretationService(db=db)
        with patch(
            "app.engines.ai_conversation.deepseek_client.DeepSeekClientService.chat",
            new=AsyncMock(return_value=_deepseek_response({
                "action": "match_option", "reply": "Maybe LG?",
                "current_question_id": question["question_id"],
                "matched_option_id": lg["id"], "confidence": 0.2,
            })),
        ):
            result = await qi.interpret(draft_id=draft_id, customer_id=CUSTOMER_ID, text="not sure, maybe some brand")

        assert result["action"] == "ask_clarification"
        after = await qf.get_current_question(draft_id=draft_id, customer_id=CUSTOMER_ID)
        assert after["answered_questions"] == []
    finally:
        if draft_id is not None:
            await _cleanup(db, draft_id)
        await db.close()


@pytest.mark.asyncio
async def test_relevant_question_is_answered_and_same_canonical_question_repeats():
    """'Why do you need the brand?' must not advance the flow -- the same
    Brand question stays active after DeepSeek's explanation."""
    from app.engines.home_service_booking.question_interpretation_service import QuestionInterpretationService
    from app.engines.home_service_booking.question_flow_service import QuestionFlowService

    db = await _get_db()
    draft_id = None
    try:
        draft_id = await _make_ac_installation_draft(db)
        qf = QuestionFlowService(db=db)
        envelope = await qf.get_current_question(draft_id=draft_id, customer_id=CUSTOMER_ID)
        question = envelope["current_question"]

        qi = QuestionInterpretationService(db=db)
        with patch(
            "app.engines.ai_conversation.deepseek_client.DeepSeekClientService.chat",
            new=AsyncMock(return_value=_deepseek_response({
                "action": "answer_and_repeat_question",
                "reply": "The brand helps us match the correct installation requirements and technician.",
                "current_question_id": question["question_id"],
                "matched_option_id": None, "confidence": 0.0,
            })),
        ):
            result = await qi.interpret(draft_id=draft_id, customer_id=CUSTOMER_ID, text="Why do you need the brand?")

        assert result["action"] == "answer_and_repeat_question"
        assert "brand" in result["reply"].lower()
        assert result["envelope"]["current_question"]["question_id"] == question["question_id"]
    finally:
        if draft_id is not None:
            await _cleanup(db, draft_id)
        await db.close()


@pytest.mark.asyncio
async def test_unrelated_message_is_redirected_to_the_current_question():
    from app.engines.home_service_booking.question_interpretation_service import QuestionInterpretationService
    from app.engines.home_service_booking.question_flow_service import QuestionFlowService

    db = await _get_db()
    draft_id = None
    try:
        draft_id = await _make_ac_installation_draft(db)
        qf = QuestionFlowService(db=db)
        envelope = await qf.get_current_question(draft_id=draft_id, customer_id=CUSTOMER_ID)
        question = envelope["current_question"]

        qi = QuestionInterpretationService(db=db)
        with patch(
            "app.engines.ai_conversation.deepseek_client.DeepSeekClientService.chat",
            new=AsyncMock(return_value=_deepseek_response({
                "action": "out_of_scope",
                "reply": "I can help with your AC booking. Which AC brand do you have?",
                "current_question_id": question["question_id"],
                "matched_option_id": None, "confidence": 0.0,
            })),
        ):
            result = await qi.interpret(draft_id=draft_id, customer_id=CUSTOMER_ID, text="What is today's cricket score?")

        assert result["action"] == "out_of_scope"
        assert result["envelope"]["current_question"]["question_id"] == question["question_id"]
    finally:
        if draft_id is not None:
            await _cleanup(db, draft_id)
        await db.close()


@pytest.mark.asyncio
async def test_deepseek_cannot_change_the_active_question_id():
    """A structured response claiming a different current_question_id (a
    stale/mismatched turn) must be rejected -- never applied against
    whatever question happens to be active now."""
    from app.engines.home_service_booking.question_interpretation_service import QuestionInterpretationService
    from app.engines.home_service_booking.question_flow_service import QuestionFlowService

    db = await _get_db()
    draft_id = None
    try:
        draft_id = await _make_ac_installation_draft(db)
        qf = QuestionFlowService(db=db)
        envelope = await qf.get_current_question(draft_id=draft_id, customer_id=CUSTOMER_ID)
        question = envelope["current_question"]
        lg = next(o for o in question["options"] if o["label"] == "LG")

        qi = QuestionInterpretationService(db=db)
        with patch(
            "app.engines.ai_conversation.deepseek_client.DeepSeekClientService.chat",
            new=AsyncMock(return_value=_deepseek_response({
                "action": "match_option", "reply": "LG",
                "current_question_id": "some-other-stale-question-id",
                "matched_option_id": lg["id"], "confidence": 0.99,
            })),
        ):
            result = await qi.interpret(draft_id=draft_id, customer_id=CUSTOMER_ID, text="LG")

        assert result["action"] == "cannot_answer"
        after = await qf.get_current_question(draft_id=draft_id, customer_id=CUSTOMER_ID)
        assert after["current_question"]["question_id"] == question["question_id"]
        assert after["answered_questions"] == []
    finally:
        if draft_id is not None:
            await _cleanup(db, draft_id)
        await db.close()


@pytest.mark.asyncio
async def test_malformed_deepseek_output_fails_closed_to_canonical_question():
    from app.engines.home_service_booking.question_interpretation_service import QuestionInterpretationService
    from app.engines.home_service_booking.question_flow_service import QuestionFlowService

    db = await _get_db()
    draft_id = None
    try:
        draft_id = await _make_ac_installation_draft(db)
        qf = QuestionFlowService(db=db)
        envelope = await qf.get_current_question(draft_id=draft_id, customer_id=CUSTOMER_ID)
        question = envelope["current_question"]

        qi = QuestionInterpretationService(db=db)
        with patch(
            "app.engines.ai_conversation.deepseek_client.DeepSeekClientService.chat",
            new=AsyncMock(return_value={"choices": [{"message": {"content": "not valid json at all"}}]}),
        ):
            result = await qi.interpret(draft_id=draft_id, customer_id=CUSTOMER_ID, text="hmm")

        assert result["action"] == "cannot_answer"
        assert result["envelope"]["current_question"]["question_id"] == question["question_id"]
    finally:
        if draft_id is not None:
            await _cleanup(db, draft_id)
        await db.close()


@pytest.mark.asyncio
async def test_no_active_question_raises_instead_of_calling_deepseek():
    from app.engines.home_service_booking.question_interpretation_service import QuestionInterpretationService
    from app.exceptions import ServiceOSException

    db = await _get_db()
    draft_id = None
    try:
        draft_id = await _make_ac_installation_draft(db)
        from app.engines.home_service_booking.question_flow_service import QuestionFlowService
        qf = QuestionFlowService(db=db)
        for _ in range(10):
            envelope = await qf.get_current_question(draft_id=draft_id, customer_id=CUSTOMER_ID)
            q = envelope["current_question"]
            if q is None:
                break
            opt = q["options"][0]["id"] if q["options"] else None
            await qf.submit_answer(draft_id=draft_id, customer_id=CUSTOMER_ID, question_id=q["question_id"], option_id=opt, value=None if opt else "x")

        qi = QuestionInterpretationService(db=db)
        with patch(
            "app.engines.ai_conversation.deepseek_client.DeepSeekClientService.chat",
            new=AsyncMock(side_effect=AssertionError("DeepSeek must not be called with no active question")),
        ):
            with pytest.raises(ServiceOSException):
                await qi.interpret(draft_id=draft_id, customer_id=CUSTOMER_ID, text="anything")
    finally:
        if draft_id is not None:
            await _cleanup(db, draft_id)
        await db.close()
