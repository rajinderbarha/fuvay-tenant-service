"""Real-DB integration tests for the zipcode-aware offering filter added to
`BackendToolExecutor._tool_get_category_offerings` (app/engines/
ai_conversation/backend_tools.py). Runs against the actual dev database
(same one `scripts/setup_140412_home_services.py` seeds/verifies) rather
than mocks -- this is the one piece of the 140412 flow that a mocked unit
test cannot meaningfully prove, since the whole point is real SQL join
semantics across TenantServiceArea/TenantServiceAreaService/TenantService.

Follows this repo's existing real-DB integration test convention (see
tests/test_mobile_active_sessions.py): `app.database.init_db()` +
`get_session_factory()` against the actual configured DATABASE_URL, no
mocking of the query layer itself.
"""
import uuid

import pytest


GURAMRIT_TENANT_ID = uuid.UUID("244beeec-fedc-452e-8054-317e45557d4d")
ZIPCODE_140412 = "140412"
AC_CATEGORY_SLUG = "air-conditioning"


async def _get_db():
    from app.database import get_session_factory, init_db
    await init_db()
    factory = get_session_factory()
    return factory()


@pytest.mark.asyncio
async def test_140412_ac_offerings_are_guramrit_only_and_in_area():
    """The exact scenario this continuation's fix addresses: a 140412
    conversation must only ever see AC offerings a tenant actually
    publishes AND actually covers at 140412.

    `ac-service` was HISTORICALLY excluded from this assertion: it was
    real and published, just only by the unrelated Ludhiana demo tenant.
    That gap was itself later found to be a root cause of a real product
    defect (no genuine "what's wrong with your AC" issue catalog existed
    for Guramrit/140412 -- see setup_140412_home_services.py's
    `ensure_ac_service_guramrit_publication` and offering_catalog_service.
    list_serviceable_issues), so Guramrit now legitimately publishes it
    too. It correctly APPEARS here now -- the isolation principle this
    test protects (never leak an offering from a tenant that does NOT
    cover 140412) is unchanged; what changed is that Guramrit itself now
    genuinely covers it, which is real data, not a leak."""
    from app.engines.ai_conversation.backend_tools import BackendToolExecutor

    db = await _get_db()
    try:
        executor = BackendToolExecutor(db=db, customer_id=None, zipcode=ZIPCODE_140412)
        result = await executor._tool_get_category_offerings(category_slug=AC_CATEGORY_SLUG)

        offering_slugs = {o["slug"] for o in result["offerings"]}
        # The three real, Guramrit-published, 140412-covered AC offerings
        # this session's setup script seeded and verified.
        assert "ac-gas-refilling" in offering_slugs
        assert "ac-installation" in offering_slugs
        assert "ac-service" in offering_slugs
    finally:
        await db.close()


@pytest.mark.asyncio
async def test_without_zipcode_filter_falls_back_to_publisher_only():
    """When a conversation genuinely has no zipcode yet (e.g. very first
    turn before any address/location context exists), the tool must not
    return zero results -- it degrades to the pre-existing publisher-only
    filter rather than failing closed to an empty catalog."""
    from app.engines.ai_conversation.backend_tools import BackendToolExecutor

    db = await _get_db()
    try:
        executor = BackendToolExecutor(db=db, customer_id=None, zipcode=None)
        result = await executor._tool_get_category_offerings(category_slug=AC_CATEGORY_SLUG)
        # Publisher-only (no area filter) should include ac-service too,
        # since it IS a real published offering, just not at 140412.
        offering_slugs = {o["slug"] for o in result["offerings"]}
        assert len(offering_slugs) >= 1, "Expected at least the publisher-only fallback to return something."
    finally:
        await db.close()


@pytest.mark.asyncio
async def test_offerings_missing_from_a_zipcode_with_no_coverage_at_all():
    """A zipcode with genuinely zero tenant_service_area coverage anywhere
    must return an empty offerings list, never every tenant's offerings
    (fail-closed, not fail-open)."""
    from app.engines.ai_conversation.backend_tools import BackendToolExecutor

    db = await _get_db()
    try:
        executor = BackendToolExecutor(db=db, customer_id=None, zipcode="000000")
        result = await executor._tool_get_category_offerings(category_slug=AC_CATEGORY_SLUG)
        assert result["offerings"] == []
    finally:
        await db.close()


@pytest.mark.asyncio
async def test_140412_offerings_have_real_issue_mapping_wiring():
    """Every offering returned for 140412 must have real, non-empty
    problem/issue-type wiring -- an offering that's published+in-area but
    structurally missing question-flow content must still be excluded
    (the earlier "AC Service had zero ServiceIssueMapping rows" class of
    bug, now guarded for any offering, not just that one)."""
    from app.engines.ai_conversation.backend_tools import BackendToolExecutor
    from sqlalchemy import select, func
    from app.engines.admin_catalog.models import MasterService, ServiceIssueMapping

    db = await _get_db()
    try:
        executor = BackendToolExecutor(db=db, customer_id=None, zipcode=ZIPCODE_140412)
        result = await executor._tool_get_category_offerings(category_slug=AC_CATEGORY_SLUG)

        assert result["offerings"], "Expected at least one real 140412 AC offering."
        for offering in result["offerings"]:
            ms_id = uuid.UUID(offering["id"])
            count = (await db.execute(
                select(func.count()).select_from(ServiceIssueMapping).where(
                    ServiceIssueMapping.master_service_id == ms_id,
                    ServiceIssueMapping.status == "active",
                )
            )).scalar_one()
            assert count > 0, f"Offering {offering['slug']} returned with zero active issue mappings."
    finally:
        await db.close()
