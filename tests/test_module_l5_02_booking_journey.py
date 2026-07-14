"""MODULE-L5-02 — customer booking journey crash fixes.

Live end-to-end verification of the customer booking journey found two 500s
(both fixed): the draft PUT stored preferred_date as a raw string into a DATE
column (asyncpg DataError), and match-and-price crashed with a NoneType
.strip() when the draft had no city. These tests pin the source-level fixes.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SVC = (ROOT / "app/engines/home_service_booking/service.py").read_text(encoding="utf-8")
ME = (ROOT / "app/engines/home_service_booking/matching_engine.py").read_text(encoding="utf-8")


def test_update_draft_parses_preferred_date():
    idx = SVC.index("async def update_draft_fields(")
    body = SVC[idx:idx + 2000]
    assert 'field == "preferred_date"' in body
    assert "date.fromisoformat" in body


def test_match_requires_city_cleanly():
    idx = SVC.index("async def match_provider_and_price(")
    body = SVC[idx:idx + 3000]
    assert "HOME_BOOKING_ADDRESS_REQUIRED" in body


def test_matching_engine_defensive_on_none_city():
    idx = ME.index("def select_best_provider(")
    body = ME[idx:idx + 2500]
    assert '(city or "").strip()' in body


def test_coverage_treats_null_brand_type_as_wildcard():
    """MODULE-L5-02: a service-level coverage row (brand_id/service_type_id NULL)
    must cover ANY brand/type. The exact-match-only check + the (area,service,
    job_type) duplicate constraint meant a brand-required service with only
    service-level coverage could never match (BRAND_NOT_COVERED_IN_AREA), making
    it unbookable. Coverage checks now treat NULL as wildcard."""
    ME = (ROOT / "app/engines/home_service_booking/matching_engine.py").read_text(encoding="utf-8")
    assert "tsas.brand_id=:bid OR tsas.brand_id IS NULL" in ME
    assert "tsas.service_type_id=:stid OR tsas.service_type_id IS NULL" in ME
