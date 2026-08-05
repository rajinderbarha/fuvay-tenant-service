"""Root-cause fix: "Brand appears before any real issue selection". Proves
the full issue-first backend flow against real, live 140412/Guramrit data:
`list_serviceable_issues`, `get_assistant_bootstrap` (issue-first), and
`select_issue` (canonical issue -> draft -> question-flow resolution).
"""
import uuid

import pytest


AC_CATEGORY_ID = uuid.UUID("59d8f3aa-932d-429e-93bd-8d4f2ed615c3")
CUSTOMER_ID = uuid.UUID("fa198861-455b-43f2-a426-47da0a8811af")
ZIPCODE_140412 = "140412"


async def _get_db():
    from app.database import get_session_factory, init_db
    await init_db()
    return get_session_factory()()


async def _cleanup(db, draft_id):
    from sqlalchemy import text
    await db.rollback()
    async with db.begin():
        await db.execute(text("DELETE FROM home_service_booking_drafts WHERE id = :id"), {"id": draft_id})


@pytest.mark.asyncio
async def test_bootstrap_returns_issues_first_not_brand():
    """The bootstrap manifest's `issues` list is the real customer-intent
    catalog -- it must include genuine diagnostic issues (Not Cooling,
    Water Leakage, ...), not just the two bare offerings, and must never
    surface "Brand" as an issue."""
    from app.engines.home_service_booking.service import HomeServiceChatbotBookingService

    db = await _get_db()
    try:
        svc = HomeServiceChatbotBookingService(db=db)
        result = await svc.get_assistant_bootstrap(customer_id=uuid.uuid4(), category_slug="air-conditioning", zipcode=ZIPCODE_140412)
        assert result["current_stage"] == "issue_selection"
        labels = {i["label"] for i in result["issues"]}
        assert "AC Not Cooling" in labels
        assert "Water Leakage" in labels
        assert "New AC Installation" in labels
        assert "Brand" not in labels
        for issue in result["issues"]:
            assert set(issue.keys()) == {"id", "label", "selection_mode", "compatibility_group"}
    finally:
        await db.close()


@pytest.mark.asyncio
async def test_out_of_area_tenant_ac_service_issues_excluded_before_guramrit_publishes():
    """Sanity check on the isolation guard itself: an unreachable zipcode
    must report zero issues, never leak another tenant's coverage gap."""
    from app.engines.home_service_booking.service import HomeServiceChatbotBookingService

    db = await _get_db()
    try:
        svc = HomeServiceChatbotBookingService(db=db)
        result = await svc.get_assistant_bootstrap(customer_id=uuid.uuid4(), category_slug="air-conditioning", zipcode="999999")
        assert result["issues"] == []
        assert result["serviceable"] is False
    finally:
        await db.close()


@pytest.mark.asyncio
async def test_selecting_installation_issue_returns_brand_as_first_question():
    """Brand is a real, legitimate FIRST question only AFTER "Install a
    new AC" is selected -- never before."""
    from app.engines.home_service_booking.service import HomeServiceChatbotBookingService

    db = await _get_db()
    draft_id = None
    try:
        svc = HomeServiceChatbotBookingService(db=db)
        bootstrap = await svc.get_assistant_bootstrap(customer_id=CUSTOMER_ID, category_slug="air-conditioning", zipcode=ZIPCODE_140412)
        install_issue = next(i for i in bootstrap["issues"] if i["label"] == "New AC Installation")

        result = await svc.select_issue(
            customer_id=CUSTOMER_ID, ai_session_id=None,
            category_slug="air-conditioning", zipcode=ZIPCODE_140412, issue_id=install_issue["id"],
        )
        draft_id = uuid.UUID(result["draft_id"])
        question = result["envelope"]["current_question"]
        assert question is not None
        assert question["question_key"] == "brand"
        assert question["text"] == "Which AC brand?"
    finally:
        if draft_id is not None:
            await _cleanup(db, draft_id)
        await db.close()


@pytest.mark.asyncio
async def test_selecting_cooling_issue_never_asks_what_is_wrong_again():
    """Selecting "AC Not Cooling" already answers "what's wrong" -- the
    first follow-up question must be a genuinely different, remaining
    diagnostic detail, never a repeat of the issue itself."""
    from app.engines.home_service_booking.service import HomeServiceChatbotBookingService

    db = await _get_db()
    draft_id = None
    try:
        svc = HomeServiceChatbotBookingService(db=db)
        bootstrap = await svc.get_assistant_bootstrap(customer_id=CUSTOMER_ID, category_slug="air-conditioning", zipcode=ZIPCODE_140412)
        cooling_issue = next(i for i in bootstrap["issues"] if i["label"] == "AC Not Cooling")

        result = await svc.select_issue(
            customer_id=CUSTOMER_ID, ai_session_id=None,
            category_slug="air-conditioning", zipcode=ZIPCODE_140412, issue_id=cooling_issue["id"],
        )
        draft_id = uuid.UUID(result["draft_id"])
        question = result["envelope"]["current_question"]
        if question is not None:
            assert "wrong" not in question["text"].lower()
            assert question["question_key"] != "cooling_symptom"
    finally:
        if draft_id is not None:
            await _cleanup(db, draft_id)
        await db.close()


@pytest.mark.asyncio
async def test_invalid_issue_id_is_rejected():
    from app.engines.home_service_booking.service import HomeServiceChatbotBookingService
    from app.exceptions import ServiceOSException

    db = await _get_db()
    try:
        svc = HomeServiceChatbotBookingService(db=db)
        with pytest.raises(ServiceOSException):
            await svc.select_issue(
                customer_id=CUSTOMER_ID, ai_session_id=None,
                category_slug="air-conditioning", zipcode=ZIPCODE_140412, issue_id="invented-issue-id",
            )
    finally:
        await db.close()


@pytest.mark.asyncio
async def test_every_returned_issue_has_valid_lineage_and_is_selectable():
    """Test every AC issue in the live manifest, not just one happy path --
    each must resolve to a real draft + a real question-flow envelope (or
    a genuinely complete flow), never an exception."""
    from app.engines.home_service_booking.service import HomeServiceChatbotBookingService

    db = await _get_db()
    created_draft_ids = []
    try:
        svc = HomeServiceChatbotBookingService(db=db)
        bootstrap = await svc.get_assistant_bootstrap(customer_id=CUSTOMER_ID, category_slug="air-conditioning", zipcode=ZIPCODE_140412)
        assert len(bootstrap["issues"]) > 0

        for issue in bootstrap["issues"]:
            result = await svc.select_issue(
                customer_id=CUSTOMER_ID, ai_session_id=None,
                category_slug="air-conditioning", zipcode=ZIPCODE_140412, issue_id=issue["id"],
            )
            created_draft_ids.append(uuid.UUID(result["draft_id"]))
            assert result["envelope"] is not None
    finally:
        for did in created_draft_ids:
            await _cleanup(db, did)
        await db.close()


@pytest.mark.asyncio
async def test_selecting_multiple_issues_from_the_same_service_stores_all_of_them():
    """A customer may report more than one real issue at once (e.g. both
    "AC Not Cooling" and "Water Leakage" on the same unit) -- both must be
    stored on the draft, and the first one drives job-type resolution."""
    from app.engines.home_service_booking.service import HomeServiceChatbotBookingService
    from app.engines.home_service_booking.models import HomeServiceBookingDraft

    db = await _get_db()
    draft_id = None
    try:
        svc = HomeServiceChatbotBookingService(db=db)
        bootstrap = await svc.get_assistant_bootstrap(customer_id=CUSTOMER_ID, category_slug="air-conditioning", zipcode=ZIPCODE_140412)
        cooling = next(i for i in bootstrap["issues"] if i["label"] == "AC Not Cooling")
        leaking = next(i for i in bootstrap["issues"] if i["label"] == "Water Leakage")

        result = await svc.select_issue(
            customer_id=CUSTOMER_ID, ai_session_id=None,
            category_slug="air-conditioning", zipcode=ZIPCODE_140412,
            issue_id=cooling["id"], additional_issue_ids=[leaking["id"]],
        )
        draft_id = uuid.UUID(result["draft_id"])
        assert set(result["selected_issue_ids"]) == {cooling["id"], leaking["id"]}

        draft = await db.get(HomeServiceBookingDraft, draft_id)
        assert set(draft.service_option_ids_json) == {cooling["id"], leaking["id"]}
        assert str(draft.selected_problem_id) == cooling["id"]
    finally:
        if draft_id is not None:
            await _cleanup(db, draft_id)
        await db.close()


@pytest.mark.asyncio
async def test_selecting_issues_across_different_services_is_rejected():
    """"New AC Installation" (ac-installation) and "AC Not Cooling"
    (ac-service) have no shared workflow -- must be rejected, never
    silently merged or silently dropped."""
    from app.engines.home_service_booking.service import HomeServiceChatbotBookingService
    from app.exceptions import ServiceOSException

    db = await _get_db()
    try:
        svc = HomeServiceChatbotBookingService(db=db)
        bootstrap = await svc.get_assistant_bootstrap(customer_id=CUSTOMER_ID, category_slug="air-conditioning", zipcode=ZIPCODE_140412)
        install = next(i for i in bootstrap["issues"] if i["label"] == "New AC Installation")
        cooling = next(i for i in bootstrap["issues"] if i["label"] == "AC Not Cooling")

        with pytest.raises(ServiceOSException):
            await svc.select_issue(
                customer_id=CUSTOMER_ID, ai_session_id=None,
                category_slug="air-conditioning", zipcode=ZIPCODE_140412,
                issue_id=install["id"], additional_issue_ids=[cooling["id"]],
            )
    finally:
        await db.close()


@pytest.mark.asyncio
async def test_deepseek_cannot_invent_an_issue():
    """OfferingInterpretationService (now issue-scoped) must reject a
    matched_issue_id DeepSeek invents."""
    import json
    from unittest.mock import AsyncMock, patch
    from app.engines.home_service_booking.offering_interpretation_service import OfferingInterpretationService

    db = await _get_db()
    try:
        svc = OfferingInterpretationService(db=db)
        with patch(
            "app.engines.ai_conversation.deepseek_client.DeepSeekClientService.chat",
            new=AsyncMock(return_value={"choices": [{"message": {"content": json.dumps({
                "action": "match_option", "reply": "Sure!",
                "matched_issue_id": "invented-issue-id", "confidence": 0.99,
            })}}]}),
        ):
            result = await svc.interpret(category_slug="air-conditioning", zipcode=ZIPCODE_140412, text="something weird")
        assert result["action"] == "ask_clarification"
        assert result["matched_offering"] is None
    finally:
        await db.close()
