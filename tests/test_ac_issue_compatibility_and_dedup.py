"""AC-ISSUE-DATA-01: Gas Refill deduplication, compatibility classification,
and select_issue's hardened validation. Real live 140412/Guramrit data.
"""
import uuid

import pytest


AC_CATEGORY_ID = uuid.UUID("59d8f3aa-932d-429e-93bd-8d4f2ed615c3")
AC_GAS_REFILLING_ID = uuid.UUID("b54e5517-ec51-4694-899b-04307e7f95bf")
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


# ── Deduplication ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_gas_refill_appears_exactly_once():
    from app.engines.home_service_booking.offering_catalog_service import list_serviceable_issues

    db = await _get_db()
    try:
        result = await list_serviceable_issues(db, "air-conditioning", ZIPCODE_140412)
        gas_labels = [i for i in result["issues"] if "gas refill" in i["label"].lower()]
        assert len(gas_labels) == 1, f"Expected exactly one Gas Refill choice, got {gas_labels}"
        assert gas_labels[0]["label"] == "Gas Refill Needed"
    finally:
        await db.close()


@pytest.mark.asyncio
async def test_cooling_low_remains_a_distinct_visible_issue():
    """'Cooling Low' is a real, distinct symptom label from 'Gas Refill
    Needed' -- both stay visible, since they are genuinely different
    customer-reported symptoms (not deduplicated against each other)."""
    from app.engines.home_service_booking.offering_catalog_service import list_serviceable_issues

    db = await _get_db()
    try:
        result = await list_serviceable_issues(db, "air-conditioning", ZIPCODE_140412)
        labels = {i["label"] for i in result["issues"]}
        assert "Cooling Low" in labels
        assert "Gas Refill Needed" in labels
    finally:
        await db.close()


@pytest.mark.asyncio
async def test_legacy_ac_gas_refilling_issue_hidden_from_new_selection():
    from app.engines.home_service_booking.offering_catalog_service import list_serviceable_issues

    db = await _get_db()
    try:
        result = await list_serviceable_issues(db, "air-conditioning", ZIPCODE_140412)
        slugs = {i["master_service_slug"] for i in result["issues"]}
        assert "ac-gas-refilling" not in slugs
    finally:
        await db.close()


@pytest.mark.asyncio
async def test_deprecated_duplicate_cannot_be_selected_for_a_new_draft():
    from app.engines.home_service_booking.service import HomeServiceChatbotBookingService
    from app.engines.admin_catalog.models import MasterIssueType
    from sqlalchemy import select
    from app.exceptions import ServiceOSException

    db = await _get_db()
    try:
        legacy_issue = (await db.execute(
            select(MasterIssueType).where(MasterIssueType.master_service_id == AC_GAS_REFILLING_ID)
        )).scalars().first()
        assert legacy_issue is not None

        svc = HomeServiceChatbotBookingService(db=db)
        with pytest.raises(ServiceOSException):
            await svc.select_issue(
                customer_id=CUSTOMER_ID, ai_session_id=None,
                category_slug="air-conditioning", zipcode=ZIPCODE_140412, issue_id=str(legacy_issue.id),
            )
    finally:
        await db.close()


@pytest.mark.asyncio
async def test_legacy_draft_referencing_the_hidden_issue_still_resolves():
    """A historical draft that already selected the (now-hidden) legacy
    gas-refill issue must remain fully readable -- hiding it from NEW
    selection never breaks an EXISTING draft's own state."""
    from app.engines.home_service_booking.service import HomeServiceChatbotBookingService
    from app.engines.admin_catalog.models import MasterIssueType
    from sqlalchemy import select

    db = await _get_db()
    draft_id = None
    try:
        legacy_issue = (await db.execute(
            select(MasterIssueType).where(MasterIssueType.master_service_id == AC_GAS_REFILLING_ID)
        )).scalars().first()

        svc = HomeServiceChatbotBookingService(db=db)
        draft_dict = await svc.start_booking_draft(
            customer_id=CUSTOMER_ID, ai_session_id=None,
            category_slug="air-conditioning", offering_slug="ac-gas-refilling",
        )
        draft_id = uuid.UUID(draft_dict["id"])
        await svc.update_draft_fields(
            draft_id=draft_id, customer_id=CUSTOMER_ID, payload={"selected_problem_id": str(legacy_issue.id)},
        )
        refreshed = await svc.get_booking_draft(draft_id=draft_id, customer_id=CUSTOMER_ID)
        assert refreshed["selected_problem_id"] == str(legacy_issue.id)
    finally:
        if draft_id is not None:
            await _cleanup(db, draft_id)
        await db.close()


# ── Compatibility ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_two_compatible_diagnostic_issues_can_be_selected_together():
    from app.engines.home_service_booking.service import HomeServiceChatbotBookingService

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
    finally:
        if draft_id is not None:
            await _cleanup(db, draft_id)
        await db.close()


@pytest.mark.asyncio
async def test_installation_plus_repair_is_rejected():
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
async def test_exclusive_issue_plus_any_second_issue_is_rejected_even_within_its_own_group():
    """An exclusive issue can never combine with ANYTHING else -- not just
    a different group. New AC Installation is the only exclusive issue
    today, so this proves the exclusivity rule itself (not merely the
    cross-group rule)."""
    from app.engines.home_service_booking.service import HomeServiceChatbotBookingService
    from app.exceptions import ServiceOSException

    db = await _get_db()
    try:
        svc = HomeServiceChatbotBookingService(db=db)
        bootstrap = await svc.get_assistant_bootstrap(customer_id=CUSTOMER_ID, category_slug="air-conditioning", zipcode=ZIPCODE_140412)
        install = next(i for i in bootstrap["issues"] if i["label"] == "New AC Installation")
        gas = next(i for i in bootstrap["issues"] if i["label"] == "Gas Refill Needed")

        with pytest.raises(ServiceOSException):
            await svc.select_issue(
                customer_id=CUSTOMER_ID, ai_session_id=None,
                category_slug="air-conditioning", zipcode=ZIPCODE_140412,
                issue_id=install["id"], additional_issue_ids=[gas["id"]],
            )
    finally:
        await db.close()


@pytest.mark.asyncio
async def test_hidden_issue_used_alongside_a_real_one_fails():
    from app.engines.home_service_booking.service import HomeServiceChatbotBookingService
    from app.engines.admin_catalog.models import MasterIssueType
    from sqlalchemy import select
    from app.exceptions import ServiceOSException

    db = await _get_db()
    try:
        legacy_issue = (await db.execute(
            select(MasterIssueType).where(MasterIssueType.master_service_id == AC_GAS_REFILLING_ID)
        )).scalars().first()

        svc = HomeServiceChatbotBookingService(db=db)
        bootstrap = await svc.get_assistant_bootstrap(customer_id=CUSTOMER_ID, category_slug="air-conditioning", zipcode=ZIPCODE_140412)
        cooling = next(i for i in bootstrap["issues"] if i["label"] == "AC Not Cooling")

        with pytest.raises(ServiceOSException):
            await svc.select_issue(
                customer_id=CUSTOMER_ID, ai_session_id=None,
                category_slug="air-conditioning", zipcode=ZIPCODE_140412,
                issue_id=cooling["id"], additional_issue_ids=[str(legacy_issue.id)],
            )
    finally:
        await db.close()


@pytest.mark.asyncio
async def test_duplicate_issue_id_is_rejected():
    from app.engines.home_service_booking.service import HomeServiceChatbotBookingService
    from app.exceptions import ServiceOSException

    db = await _get_db()
    try:
        svc = HomeServiceChatbotBookingService(db=db)
        bootstrap = await svc.get_assistant_bootstrap(customer_id=CUSTOMER_ID, category_slug="air-conditioning", zipcode=ZIPCODE_140412)
        cooling = next(i for i in bootstrap["issues"] if i["label"] == "AC Not Cooling")

        with pytest.raises(ServiceOSException):
            await svc.select_issue(
                customer_id=CUSTOMER_ID, ai_session_id=None,
                category_slug="air-conditioning", zipcode=ZIPCODE_140412,
                issue_id=cooling["id"], additional_issue_ids=[cooling["id"]],
            )
    finally:
        await db.close()


@pytest.mark.asyncio
async def test_compatibility_result_is_deterministic_across_repeated_calls():
    from app.engines.home_service_booking.offering_catalog_service import list_serviceable_issues

    db = await _get_db()
    try:
        first = await list_serviceable_issues(db, "air-conditioning", ZIPCODE_140412)
        second = await list_serviceable_issues(db, "air-conditioning", ZIPCODE_140412)
        first_map = {i["id"]: (i["selection_mode"], i["compatibility_group"]) for i in first["issues"]}
        second_map = {i["id"]: (i["selection_mode"], i["compatibility_group"]) for i in second["issues"]}
        assert first_map == second_map
    finally:
        await db.close()


# ── Pricing/readiness (regression guard for the shared-workflow fix) ──────

@pytest.mark.asyncio
async def test_diagnostic_issue_via_ac_service_still_uses_inspection_mode_and_299_visit_fee():
    from app.engines.home_service_booking.service import HomeServiceChatbotBookingService
    from app.engines.home_service_booking.offering_catalog_service import list_serviceable_issues

    db = await _get_db()
    draft_id = None
    try:
        svc = HomeServiceChatbotBookingService(db=db)
        catalog = await list_serviceable_issues(db, "air-conditioning", ZIPCODE_140412)
        gas = next(i for i in catalog["issues"] if i["label"] == "Gas Refill Needed")

        result = await svc.select_issue(
            customer_id=CUSTOMER_ID, ai_session_id=None,
            category_slug="air-conditioning", zipcode=ZIPCODE_140412, issue_id=gas["id"],
        )
        draft_id = uuid.UUID(result["draft_id"])
        offering = await svc._get_offering(uuid.UUID(gas["master_service_id"]))
        assert offering.pricing_model == "visit_fee_plus_quote"
        assert float(offering.visit_fee) == 299.0
    finally:
        if draft_id is not None:
            await _cleanup(db, draft_id)
        await db.close()
