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
            customer_id=CUSTOMER_ID, category_slug="home_services", zipcode=ZIPCODE_140412,
            service_group_slug="ac_services",
        )
        assert result["serviceable"] is True
        assert result["zipcode"] == ZIPCODE_140412
        labels = {i["label"] for i in result["issues"]}
        assert "AC is not cooling" in labels
        assert "New AC installation" in labels
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
            customer_id=CUSTOMER_ID, category_slug="home_services", zipcode="999999",
            service_group_slug="ac_services",
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
        bootstrap = await svc.get_assistant_bootstrap(
            customer_id=CUSTOMER_ID, category_slug="home_services", zipcode=ZIPCODE_140412,
            service_group_slug="ac_services",
        )
        installation = next(issue for issue in bootstrap["issues"] if issue["label"] == "New AC installation")
        draft_dict = await svc.select_issue(
            customer_id=CUSTOMER_ID, ai_session_id=None,
            category_slug="home_services", zipcode=ZIPCODE_140412, issue_id=installation["id"],
            service_group_slug="ac_services",
        )
        draft_id = uuid.UUID(draft_dict["draft_id"])

        result = await svc.get_assistant_bootstrap(
            customer_id=CUSTOMER_ID, category_slug="home_services", zipcode=ZIPCODE_140412,
            service_group_slug="ac_services",
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
        bootstrap = await svc.get_assistant_bootstrap(
            customer_id=CUSTOMER_ID, category_slug="home_services", zipcode=ZIPCODE_140412,
            service_group_slug="ac_services",
        )
        installation = next(issue for issue in bootstrap["issues"] if issue["label"] == "New AC installation")
        draft_dict = await svc.select_issue(
            customer_id=CUSTOMER_ID, ai_session_id=None,
            category_slug="home_services", zipcode=ZIPCODE_140412, issue_id=installation["id"],
            service_group_slug="ac_services",
        )
        draft_id = uuid.UUID(draft_dict["draft_id"])

        result = await svc.get_assistant_bootstrap(
            customer_id=OTHER_CUSTOMER_ID, category_slug="home_services", zipcode=ZIPCODE_140412,
            service_group_slug="ac_services",
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
            customer_id=uuid.uuid4(), category_slug="home_services", zipcode=ZIPCODE_140412,
            service_group_slug="ac_services",
        )
        assert result["resumable_draft"] is None
        assert result["current_stage"] == "issue_selection"
    finally:
        await db.close()


@pytest.mark.asyncio
async def test_home_services_bootstrap_is_strictly_scoped_to_selected_service_group():
    """A native Home tile is a service-group selection, not a request for
    every problem in the broad Home Services category. The backend must
    enforce that boundary even if a modified client calls it directly."""
    from sqlalchemy import select

    from app.engines.admin_catalog.models import MasterService, ServiceGroup, ServiceIssueMapping
    from app.engines.home_service_booking.offering_catalog_service import list_serviceable_issues

    db = await _get_db()
    try:
        result = await list_serviceable_issues(
            db, "home_services", ZIPCODE_140412, service_group_slug="ac_services",
        )
        assert result["service_group"]["slug"] == "ac_services"
        assert result["issues"], "The published 140412 AC catalog must remain bookable"

        issue_ids = [uuid.UUID(item["id"]) for item in result["issues"]]
        returned_group_slugs = set((await db.execute(
            select(ServiceGroup.slug)
            .join(MasterService, MasterService.service_group_id == ServiceGroup.id)
            .join(ServiceIssueMapping, ServiceIssueMapping.master_service_id == MasterService.id)
            .where(ServiceIssueMapping.issue_type_id.in_(issue_ids))
        )).scalars().all())
        assert returned_group_slugs == {"ac_services"}

        invalid = await list_serviceable_issues(
            db, "home_services", ZIPCODE_140412, service_group_slug="not-a-real-group",
        )
        assert invalid["issues"] == []
        assert invalid["service_group"] is None
    finally:
        await db.close()
