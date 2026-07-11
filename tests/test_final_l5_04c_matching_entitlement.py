"""FINAL-L5-04C — Matching, Customer Availability, Booking Confirmation
entitlement enforcement tests.

Unlike most of this repo's tests, these are real-database integration
tests (not mocked) — the entitlement bulk-resolution query and the
matching-engine gate it feeds are SQL-shape-sensitive (joins across
tenant_category_entitlements/tenant_module_entitlements/verticals/
service_categories), and mocking that away would only prove the mock
is self-consistent, not that the real query is correct. These tests
bypass the repo's autouse mock_database fixture by initializing a real
session factory against the live dev database for their own duration.

Uses the real canonical seeded tenants (demo-ac-services /
isolation-test-services) and restores their entitlement state at the
end of each test that mutates it, so it composes safely with the rest
of the suite and with manual live testing done elsewhere.
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text

from app.database import get_session_factory, init_db

TENANT_ONE_ID = uuid.UUID("5209ef33-a53e-4fc0-b3f6-006335b8d712")   # demo-ac-services
TENANT_TWO_ID = uuid.UUID("f45664c1-50b7-42c5-a115-37fed1bbaf53")   # isolation-test-services
AC_CATEGORY_ID = uuid.UUID("4488cc1f-12f9-420f-94c1-d566e9de74e9")  # AC & HVAC service_group
PLUMBING_CATEGORY_ID = uuid.UUID("6ac63e65-ac90-4f0e-96f9-3c98b5d824a7")  # Plumbing service_group


@pytest.fixture
async def real_db():
    """A real AsyncSession against the live dev database, bypassing the
    autouse mock_database fixture's monkeypatched session factory for the
    duration of this fixture only."""
    await init_db()
    factory = get_session_factory()
    async with factory() as session:
        yield session


@pytest.mark.asyncio
class TestBulkEntitlementResolution:
    async def test_entitled_tenant_ids_for_ac_category_includes_only_tenant_one(self, real_db):
        from app.engines.entitlement.service import entitlement_service
        entitled = await entitlement_service.get_entitled_tenant_ids_for_category(
            real_db, AC_CATEGORY_ID, tenant_ids=[TENANT_ONE_ID, TENANT_TWO_ID]
        )
        assert TENANT_ONE_ID in entitled
        assert TENANT_TWO_ID not in entitled

    async def test_entitled_tenant_ids_for_plumbing_category_includes_only_tenant_two(self, real_db):
        from app.engines.entitlement.service import entitlement_service
        entitled = await entitlement_service.get_entitled_tenant_ids_for_category(
            real_db, PLUMBING_CATEGORY_ID, tenant_ids=[TENANT_ONE_ID, TENANT_TWO_ID]
        )
        assert TENANT_TWO_ID in entitled
        assert TENANT_ONE_ID not in entitled

    async def test_single_bulk_query_not_one_per_candidate(self, real_db):
        """Regression guard for the N+1 rule: resolving entitlement for N
        candidate tenants must not scale linearly in query count. Proven by
        asserting the real function issues exactly one SELECT regardless of
        how many tenant_ids are passed, via SQLAlchemy's engine echo hook."""
        from app.engines.entitlement.service import entitlement_service
        queries: list[str] = []
        bind = real_db.get_bind()
        target = getattr(bind, "sync_engine", bind)

        def _before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            queries.append(statement)

        from sqlalchemy import event
        event.listen(target, "before_cursor_execute", _before_cursor_execute)
        try:
            many_ids = [TENANT_ONE_ID, TENANT_TWO_ID] * 10  # simulate a larger candidate pool
            await entitlement_service.get_entitled_tenant_ids_for_category(
                real_db, AC_CATEGORY_ID, tenant_ids=many_ids
            )
        finally:
            event.remove(target, "before_cursor_execute", _before_cursor_execute)
        entitlement_queries = [q for q in queries if "tenant_category_entitlements" in q]
        assert len(entitlement_queries) == 1, f"expected exactly 1 query, got {len(entitlement_queries)}"

    async def test_disable_then_reenable_reflected_immediately_in_bulk_resolution(self, real_db):
        from app.engines.entitlement.service import entitlement_service
        try:
            await entitlement_service.disable_category_entitlement(
                real_db, tenant_id=TENANT_ONE_ID, category_id=AC_CATEGORY_ID,
                actor_id=None, actor_role="pytest", reason="test_final_l5_04c disable/reenable check",
            )
            entitled = await entitlement_service.get_entitled_tenant_ids_for_category(
                real_db, AC_CATEGORY_ID, tenant_ids=[TENANT_ONE_ID]
            )
            assert TENANT_ONE_ID not in entitled
        finally:
            await entitlement_service.reenable_category_entitlement(
                real_db, tenant_id=TENANT_ONE_ID, category_id=AC_CATEGORY_ID,
                actor_id=None, actor_role="pytest",
            )
        entitled_after = await entitlement_service.get_entitled_tenant_ids_for_category(
            real_db, AC_CATEGORY_ID, tenant_ids=[TENANT_ONE_ID]
        )
        assert TENANT_ONE_ID in entitled_after


@pytest.mark.asyncio
class TestMatchingEngineExclusionReasons:
    async def test_plumbing_service_excludes_tenant_one_with_entitlement_reason(self, real_db):
        """Real matching-engine call: Tenant One (AC-only) is the sole
        candidate in this seed's coverage area (Ludhiana) but must still be
        excluded from Plumbing-service matching with the entitlement reason
        code, not silently matched or excluded for an unrelated reason."""
        result = (await real_db.execute(text(
            "SELECT id FROM master_services WHERE service_group_id = :gid AND is_active = true LIMIT 1"
        ), {"gid": str(PLUMBING_CATEGORY_ID)})).fetchone()
        if not result:
            pytest.skip("no active Plumbing master_service seeded in this environment")
        from app.engines.home_service_booking.matching_engine import select_best_provider
        match = await select_best_provider(
            real_db, category_id=uuid.UUID("0888d283-9a52-4d7b-8612-9f47fa8357a1"),
            offering_id=result.id, city="Ludhiana", zipcode=None,
        )
        assert match["candidate_count"] >= 1, "expected at least Tenant One in the Ludhiana coverage pool"
        reasons = {e["reason_code"] for e in match["excluded_providers"]}
        assert "TENANT_CATEGORY_NOT_ENTITLED" in reasons
        assert match["signals"] is None, "no candidate should have passed to the scoring stage"


@pytest.mark.asyncio
class TestBookingConfirmationEntitlementGuard:
    async def test_confirm_draft_rejects_when_entitlement_disabled_after_match(self, real_db):
        """Part 6 — booking confirmation must re-validate entitlement, not
        just trust the earlier matching result. Creates a real minimal
        draft already 'matched' to Tenant One for an AC service, disables
        Tenant One's AC entitlement (simulating an admin action in the
        window between match and confirm), and asserts confirm_draft
        returns the controlled PROVIDER_ENTITLEMENT_CHANGED 409 rather than
        succeeding or 500ing."""
        from app.engines.home_service_booking.models import HomeServiceBookingDraft
        from app.engines.home_service_booking.service import HomeServiceChatbotBookingService
        from app.engines.home_service_booking.constants import ERR_PROVIDER_ENTITLEMENT_CHANGED
        from app.engines.entitlement.service import entitlement_service
        from app.exceptions import ServiceOSException

        ac_service = (await real_db.execute(text(
            "SELECT id FROM master_services WHERE service_group_id = :gid AND is_active = true LIMIT 1"
        ), {"gid": str(AC_CATEGORY_ID)})).fetchone()
        if not ac_service:
            pytest.skip("no active AC master_service seeded in this environment")

        draft = HomeServiceBookingDraft(
            category_id=uuid.UUID("0888d283-9a52-4d7b-8612-9f47fa8357a1"),
            offering_id=ac_service.id,
            selected_tenant_id=TENANT_ONE_ID,
            status="ready_for_confirmation",
        )
        real_db.add(draft)
        await real_db.flush()
        draft_id = draft.id

        try:
            await entitlement_service.disable_category_entitlement(
                real_db, tenant_id=TENANT_ONE_ID, category_id=AC_CATEGORY_ID,
                actor_id=None, actor_role="pytest", reason="test_final_l5_04c confirm-draft guard",
            )
            svc = HomeServiceChatbotBookingService(db=real_db)
            with pytest.raises(ServiceOSException) as exc:
                await svc.confirm_draft(draft_id)
            assert exc.value.error_code == ERR_PROVIDER_ENTITLEMENT_CHANGED
            assert exc.value.status_code == 409
        finally:
            await entitlement_service.reenable_category_entitlement(
                real_db, tenant_id=TENANT_ONE_ID, category_id=AC_CATEGORY_ID,
                actor_id=None, actor_role="pytest",
            )
            await real_db.execute(text("DELETE FROM home_service_booking_draft_events WHERE draft_id = :id"), {"id": str(draft_id)})
            await real_db.execute(text("DELETE FROM home_service_booking_drafts WHERE id = :id"), {"id": str(draft_id)})
            await real_db.commit()

    async def test_confirm_draft_succeeds_when_still_entitled(self, real_db):
        """Positive case: an entitled tenant's draft confirms normally."""
        from app.engines.home_service_booking.models import HomeServiceBookingDraft
        from app.engines.home_service_booking.service import HomeServiceChatbotBookingService

        ac_service = (await real_db.execute(text(
            "SELECT id FROM master_services WHERE service_group_id = :gid AND is_active = true LIMIT 1"
        ), {"gid": str(AC_CATEGORY_ID)})).fetchone()
        if not ac_service:
            pytest.skip("no active AC master_service seeded in this environment")

        draft = HomeServiceBookingDraft(
            category_id=uuid.UUID("0888d283-9a52-4d7b-8612-9f47fa8357a1"),
            offering_id=ac_service.id,
            selected_tenant_id=TENANT_ONE_ID,
            status="ready_for_confirmation",
        )
        real_db.add(draft)
        await real_db.flush()
        draft_id = draft.id

        try:
            svc = HomeServiceChatbotBookingService(db=real_db)
            result = await svc.confirm_draft(draft_id)
            assert result["data"]["status"] == "confirmed"
        finally:
            await real_db.execute(text("DELETE FROM home_service_booking_draft_events WHERE draft_id = :id"), {"id": str(draft_id)})
            await real_db.execute(text("DELETE FROM home_service_booking_drafts WHERE id = :id"), {"id": str(draft_id)})
            await real_db.commit()
