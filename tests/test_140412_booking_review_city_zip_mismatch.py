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


AC_GAS_REFILLING_ID = uuid.UUID("b54e5517-ec51-4694-899b-04307e7f95bf")
AC_CATEGORY_ID = uuid.UUID("59d8f3aa-932d-429e-93bd-8d4f2ed615c3")
GURAMRIT_TENANT_ID = uuid.UUID("244beeec-fedc-452e-8054-317e45557d4d")
ZIPCODE_140412 = "140412"


async def _get_db():
    from app.database import get_session_factory, init_db
    await init_db()
    return get_session_factory()()


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
        result = await svc.check(
            category_id=AC_CATEGORY_ID, offering_id=AC_GAS_REFILLING_ID,
            city="Bassi pathana", zipcode=ZIPCODE_140412,
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
        match = await select_best_provider(
            db, category_id=AC_CATEGORY_ID, offering_id=AC_GAS_REFILLING_ID,
            city="Bassi pathana", zipcode=ZIPCODE_140412,
        )
        assert match is not None and match.get("signals") is not None, (
            "Expected a real eligible candidate (Guramrit) via zipcode match "
            "despite city-string mismatch; got no signals -- this is the "
            "exact HOME_BOOKING_NO_PROVIDER_AVAILABLE regression."
        )
        assert match["signals"].tenant_id == str(GURAMRIT_TENANT_ID)
    finally:
        await db.close()
