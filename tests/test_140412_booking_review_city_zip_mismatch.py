"""Regression test for the real defect behind the customer's report "The
booking-review screen also does not work after this flow".

Root cause: Guramrit's real TenantServiceArea row for 140412 stores
`city = "BASSIPATHANA"` (no space), while the customer's own saved address
city is `"Bassi pathana"` (with space) -- both genuinely describe the same
place, but two independent queries required an EXACT city-string match on
top of the zipcode match:

  1. HomeServiceServiceabilityService.check() -- made `checkServiceability`
     report `NO_PROVIDER_IN_ZIPCODE` for a zipcode a real, active tenant
     does cover, permanently blocking Booking Review at its first gate.
  2. select_best_provider() (matching_engine.py) -- excluded the same
     tenant from its own candidate pool even after gate #1 was fixed, so
     `match-and-price` still 422'd with HOME_BOOKING_NO_PROVIDER_AVAILABLE.

Both are fixed by accepting a zipcode match on its own (a zipcode is
already a unique geographic identifier) rather than AND-ing it with a
free-text city string. This test exercises both real functions directly
against the live 140412/Guramrit/AC-Gas-Refilling data -- no mocks -- since
the bug only reproduces with genuine city-string formatting drift between
two real tables.
"""
import uuid

import pytest


ZIPCODE_140412 = "140412"


async def _get_db():
    from app.database import get_session_factory, init_db
    await init_db()
    return get_session_factory()()


async def _live_ac_target(db):
    """Resolve the active catalog instead of pinning disposable seed UUIDs."""
    from app.engines.home_service_booking.offering_catalog_service import list_serviceable_issues

    catalog = await list_serviceable_issues(
        db, "home_services", ZIPCODE_140412, service_group_slug="ac_services",
    )
    assert catalog["issues"], "140412 must retain at least one bookable AC service"
    return uuid.UUID(catalog["category_id"]), uuid.UUID(catalog["issues"][0]["master_service_id"])


@pytest.mark.asyncio
async def test_serviceability_check_accepts_zipcode_match_despite_city_string_mismatch():
    """Guramrit's coverage row is stored as city='BASSIPATHANA' (no space).
    A customer whose own address city is the differently-formatted
    'Bassi pathana' must still be reported serviceable purely on the
    zipcode match -- this is the exact defect the physical-device report
    traced back to."""
    from app.engines.home_service_booking.serviceability_service import HomeServiceServiceabilityService

    db = await _get_db()
    try:
        svc = HomeServiceServiceabilityService(db=db)
        category_id, offering_id = await _live_ac_target(db)
        result = await svc.check(
            category_id=category_id, offering_id=offering_id,
            city="A differently formatted city label", zipcode=ZIPCODE_140412,
        )
        assert result["serviceable"] is True, (
            f"Expected serviceable=True via zipcode match despite city-string "
            f"mismatch; got {result}"
        )
        assert result["matched_by"] == "zipcode"
    finally:
        await db.close()


@pytest.mark.asyncio
async def test_select_best_provider_includes_zipcode_matched_tenant_despite_city_string_mismatch():
    """The second, independent bug: even after serviceability_service.py was
    fixed, the provider-matching candidate pool query had the exact same
    city-equality mistake, so match-and-price still excluded Guramrit."""
    from app.engines.home_service_booking.matching_engine import select_best_provider

    db = await _get_db()
    try:
        from app.engines.home_service_booking.offering_catalog_service import list_serviceable_issues

        catalog = await list_serviceable_issues(
            db, "home_services", ZIPCODE_140412, service_group_slug="ac_services",
        )
        category_id = uuid.UUID(catalog["category_id"])
        match = None
        for offering_id in dict.fromkeys(issue["master_service_id"] for issue in catalog["issues"]):
            candidate = await select_best_provider(
                db, category_id=category_id, offering_id=uuid.UUID(offering_id),
                city="A differently formatted city label", zipcode=ZIPCODE_140412,
            )
            if candidate.get("signals") is not None:
                match = candidate
                break
        assert match is not None and match.get("signals") is not None, (
            "Expected a real eligible candidate (Guramrit) via zipcode match "
            "despite city-string mismatch; got no signals -- this is the "
            "exact HOME_BOOKING_NO_PROVIDER_AVAILABLE regression."
        )
        assert match["signals"].tenant_id
    finally:
        await db.close()
