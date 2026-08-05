"""Backend-first Booking Assistant bootstrap -- `HomeServiceChatbotBookingService
.get_assistant_bootstrap` (customer_router.get_assistant_bootstrap) is the
one authoritative source the Customer App calls to render the FIRST
booking screen without any DeepSeek call. Bootstrap is ISSUE-first (real
customer intent -- "what's wrong with your AC" -- per the root-cause fix
for "Brand appears before any real issue selection"). Exercised against
real live 140412/Guramrit data (no mocks) so the exact zipcode-isolation
and draft-resume rules that matter in production are actually verified.
"""
import uuid

import pytest


AC_CATEGORY_ID = uuid.UUID("59d8f3aa-932d-429e-93bd-8d4f2ed615c3")
AC_GAS_REFILLING_ID = uuid.UUID("b54e5517-ec51-4694-899b-04307e7f95bf")
CUSTOMER_ID = uuid.UUID("fa198861-455b-43f2-a426-47da0a8811af")
OTHER_CUSTOMER_ID = uuid.uuid4()
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
async def test_bootstrap_returns_only_140412_serviceable_issues():
    from app.engines.home_service_booking.service import HomeServiceChatbotBookingService

    db = await _get_db()
    try:
        svc = HomeServiceChatbotBookingService(db=db)
        result = await svc.get_assistant_bootstrap(
            customer_id=CUSTOMER_ID, category_slug="air-conditioning", zipcode=ZIPCODE_140412,
        )
        assert result["serviceable"] is True
        assert result["zipcode"] == ZIPCODE_140412
        labels = {i["label"] for i in result["issues"]}
        assert "AC Not Cooling" in labels
        assert "New AC Installation" in labels
        for issue in result["issues"]:
            assert set(issue.keys()) == {"id", "label", "selection_mode", "compatibility_group"}
    finally:
        await db.close()


@pytest.mark.asyncio
async def test_bootstrap_reports_unserviceable_for_an_unreachable_zipcode():
    from app.engines.home_service_booking.service import HomeServiceChatbotBookingService

    db = await _get_db()
    try:
        svc = HomeServiceChatbotBookingService(db=db)
        result = await svc.get_assistant_bootstrap(
            customer_id=CUSTOMER_ID, category_slug="air-conditioning", zipcode="999999",
        )
        assert result["serviceable"] is False
        assert result["issues"] == []
    finally:
        await db.close()


@pytest.mark.asyncio
async def test_bootstrap_resumes_the_customers_own_valid_draft():
    """Uses `ac-installation` -- `ac-gas-refilling` is no longer a valid
    NEW resume target (AC-ISSUE-DATA-01: its own issue is now the hidden,
    deduplicated legacy Gas Refill entry point; a draft against it can no
    longer appear in `list_serviceable_issues`'s master_service_id set,
    so it correctly stops being offered as resumable -- covered by the
    dedup test suite instead)."""
    from app.engines.home_service_booking.service import HomeServiceChatbotBookingService

    db = await _get_db()
    draft_id = None
    try:
        svc = HomeServiceChatbotBookingService(db=db)
        draft_dict = await svc.start_booking_draft(
            customer_id=CUSTOMER_ID, ai_session_id=None,
            category_slug="air-conditioning", offering_slug="ac-installation",
        )
        draft_id = uuid.UUID(draft_dict["id"])

        result = await svc.get_assistant_bootstrap(
            customer_id=CUSTOMER_ID, category_slug="air-conditioning", zipcode=ZIPCODE_140412,
        )
        assert result["resumable_draft"] is not None
        assert result["resumable_draft"]["id"] == str(draft_id)
        assert result["current_stage"] == "questions"
    finally:
        if draft_id is not None:
            await _cleanup(db, draft_id)
        await db.close()


@pytest.mark.asyncio
async def test_bootstrap_never_resumes_another_customers_draft():
    from app.engines.home_service_booking.service import HomeServiceChatbotBookingService

    db = await _get_db()
    draft_id = None
    try:
        svc = HomeServiceChatbotBookingService(db=db)
        draft_dict = await svc.start_booking_draft(
            customer_id=CUSTOMER_ID, ai_session_id=None,
            category_slug="air-conditioning", offering_slug="ac-gas-refilling",
        )
        draft_id = uuid.UUID(draft_dict["id"])

        result = await svc.get_assistant_bootstrap(
            customer_id=OTHER_CUSTOMER_ID, category_slug="air-conditioning", zipcode=ZIPCODE_140412,
        )
        assert result["resumable_draft"] is None
        assert result["current_stage"] == "issue_selection"
    finally:
        if draft_id is not None:
            await _cleanup(db, draft_id)
        await db.close()


@pytest.mark.asyncio
async def test_bootstrap_reports_issue_selection_stage_with_no_prior_draft():
    from app.engines.home_service_booking.service import HomeServiceChatbotBookingService

    db = await _get_db()
    try:
        svc = HomeServiceChatbotBookingService(db=db)
        result = await svc.get_assistant_bootstrap(
            customer_id=uuid.uuid4(), category_slug="air-conditioning", zipcode=ZIPCODE_140412,
        )
        assert result["resumable_draft"] is None
        assert result["current_stage"] == "issue_selection"
    finally:
        await db.close()
