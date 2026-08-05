"""CUSTOMER-CHAT-UX-04 -- every ac-service (diagnostic) booking reached
Booking Review as "This isn't ready to review yet" and never showed a
price, because `select_best_provider` excluded Guramrit -- the only
covering tenant -- with `TENANT_CATEGORY_NOT_ENTITLED`.

Root cause: Guramrit had ZERO rows in `tenant_module_entitlements` and
`tenant_category_entitlements`. `ac-installation`/`ac-gas-refilling` have
`service_group_id = NULL`, so matching_engine's entitlement gate is
skipped entirely for them and they always worked -- masking the gap.
`ac-service` is the only AC master service WITH a service_group_id, so it
was the only one the gate ever applied to, and it failed closed for every
diagnostic issue.

Exercised against real live 140412/Guramrit data (no mocks), so the exact
entitlement chain that matters in production is actually verified.
"""
import uuid

import pytest


GURAMRIT_TENANT_ID = uuid.UUID("244beeec-fedc-452e-8054-317e45557d4d")
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
async def test_guramrit_holds_an_effective_entitlement_for_the_ac_service_group():
    """The two-level (module -> category) entitlement the canonical
    resolver requires must actually exist -- this is what
    `ensure_guramrit_ac_service_entitlement` provisions."""
    from sqlalchemy import select
    from app.engines.admin_catalog.models import MasterService
    from app.engines.entitlement.service import entitlement_service

    db = await _get_db()
    try:
        ac_service = (await db.execute(
            select(MasterService).where(MasterService.slug == "ac-service")
        )).scalars().first()
        assert ac_service is not None
        assert ac_service.service_group_id is not None, (
            "ac-service must keep a real service_group_id -- the entitlement "
            "gate only applies to master services that have one."
        )

        entitled = await entitlement_service.get_entitled_tenant_ids_for_category(
            db, ac_service.service_group_id, tenant_ids=[GURAMRIT_TENANT_ID],
        )
        assert GURAMRIT_TENANT_ID in entitled
    finally:
        await db.close()


@pytest.mark.asyncio
async def test_ac_service_diagnostic_draft_matches_a_real_provider():
    """The exact failure the customer hit: a diagnostic issue's draft must
    resolve a real selected provider, never `TENANT_CATEGORY_NOT_ENTITLED`
    -> HOME_BOOKING_NO_PROVIDER_AVAILABLE."""
    from app.engines.home_service_booking.service import HomeServiceChatbotBookingService
    from app.engines.home_service_booking.offering_catalog_service import list_serviceable_issues
    from app.engines.home_service_booking.matching_engine import select_best_provider
    from app.engines.home_service_booking.models import HomeServiceBookingDraft

    db = await _get_db()
    draft_id = None
    try:
        svc = HomeServiceChatbotBookingService(db=db)
        issues = (await list_serviceable_issues(db, "air-conditioning", ZIPCODE_140412))["issues"]
        cooling = next(i for i in issues if i["label"] == "AC Not Cooling")

        result = await svc.select_issue(
            customer_id=CUSTOMER_ID, ai_session_id=None,
            category_slug="air-conditioning", zipcode=ZIPCODE_140412, issue_id=cooling["id"],
        )
        draft_id = uuid.UUID(result["draft_id"])
        draft = await db.get(HomeServiceBookingDraft, draft_id)

        match = await select_best_provider(
            db, category_id=draft.category_id, offering_id=draft.offering_id,
            city=draft.city, zipcode=draft.zipcode, job_type_id=draft.job_type_id,
        )
        excluded_codes = {e.get("reason_code") for e in (match.get("excluded_providers") or [])}
        assert "TENANT_CATEGORY_NOT_ENTITLED" not in excluded_codes
        assert match.get("signals") is not None, (
            f"No provider selected for a diagnostic AC draft; exclusions: {match.get('excluded_providers')}"
        )
    finally:
        if draft_id is not None:
            await _cleanup(db, draft_id)
        await db.close()


@pytest.mark.asyncio
async def test_ac_service_draft_resolves_a_real_inspection_price():
    """"Price does not show": ac-service is `visit_fee_plus_quote`, so its
    real customer-facing price is the ₹299 visit fee with
    `requires_inspection_estimate` -- never a null/zero price."""
    from app.engines.home_service_booking.service import HomeServiceChatbotBookingService
    from app.engines.home_service_booking.offering_catalog_service import list_serviceable_issues

    db = await _get_db()
    draft_id = None
    try:
        svc = HomeServiceChatbotBookingService(db=db)
        issues = (await list_serviceable_issues(db, "air-conditioning", ZIPCODE_140412))["issues"]
        cooling = next(i for i in issues if i["label"] == "AC Not Cooling")

        result = await svc.select_issue(
            customer_id=CUSTOMER_ID, ai_session_id=None,
            category_slug="air-conditioning", zipcode=ZIPCODE_140412, issue_id=cooling["id"],
        )
        draft_id = uuid.UUID(result["draft_id"])

        estimate = await svc.resolve_price_estimate(draft_id=draft_id, customer_id=CUSTOMER_ID)
        snapshot = estimate["price_snapshot"]
        assert snapshot.get("requires_inspection_estimate") is True
        assert snapshot.get("visit_fee") == 299.0
        assert snapshot.get("pricing_mode") == "inspection"
    finally:
        if draft_id is not None:
            await _cleanup(db, draft_id)
        await db.close()
