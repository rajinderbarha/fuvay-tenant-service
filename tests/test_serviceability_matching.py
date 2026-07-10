"""
Step 3 — Serviceability Check + Matching Logic (36 tests).

Covers:
  - Helper methods: _norm, _strip_zip, _haversine_km
  - Request validation: _validate_check_request
  - Service resolution: _resolve_service_type_id
  - City / zipcode / zone / radius coverage matching
  - Deduplication and full ranking chain
  - Cross-tenant service_type_id resolution
  - check_serviceability, get_matching_tenants, get_available_services_for_address
  - admin_serviceability_test debug endpoint
  - Permission filtering: tenant_owner sees only own tenant
"""
import math
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.engines.serviceability.service import ServiceabilityService
from app.engines.serviceability.constants import (
    MatchLevel, MATCH_LEVEL_PRIORITY,
    ERR_SERVICE_NOT_FOUND, ERR_SERVICE_NOT_ACTIVE,
    ERR_SERVICE_ID_REQUIRED, ERR_INVALID_JOB_TYPE,
    ERR_CHECK_CITY_REQUIRED, ERR_CHECK_STATE_REQUIRED,
    ERR_LOCATION_REQUIRED,
)
from app.exceptions import ServiceOSException, NotFoundException


# ── Fixed UUIDs for test stability ────────────────────────────────────────────
CUSTOMER_ID = uuid.UUID("aaaaaaaa-0000-0000-0000-000000000001")
TENANT_A    = uuid.UUID("bbbbbbbb-0000-0000-0000-000000000001")
TENANT_B    = uuid.UUID("bbbbbbbb-0000-0000-0000-000000000002")
SERVICE_UUID = uuid.UUID("cccccccc-0000-0000-0000-000000000001")
AREA_A       = uuid.UUID("dddddddd-0000-0000-0000-000000000001")
AREA_B       = uuid.UUID("dddddddd-0000-0000-0000-000000000002")
MAPPING_A    = uuid.UUID("eeeeeeee-0000-0000-0000-000000000001")
MAPPING_B    = uuid.UUID("eeeeeeee-0000-0000-0000-000000000002")
ZONE_ID      = uuid.UUID("ffffffff-0000-0000-0000-000000000001")
SERVICE_TYPE = "ac_repair"


# ── Mock helpers ──────────────────────────────────────────────────────────────

def make_db() -> MagicMock:
    db = MagicMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.get = AsyncMock(return_value=None)
    db.execute = AsyncMock()
    return db


def make_svc(db, role="customer", actor_id=None, actor_tenant_id=None):
    return ServiceabilityService(
        db=db, request_id="test",
        actor_id=actor_id or CUSTOMER_ID,
        actor_role=role,
        actor_tenant_id=actor_tenant_id,
    )


def exec_rows(*rows):
    """Mock: (await db.execute(...)).all() → list of rows."""
    m = MagicMock()
    m.all.return_value = list(rows)
    return m


def exec_scalars(*items):
    """Mock: (await db.execute(...)).scalars().all() → list of items."""
    m = MagicMock()
    m.scalars.return_value.all.return_value = list(items)
    return m


def exec_scalar_one(val):
    m = MagicMock()
    m.scalar_one.return_value = val
    return m


def make_catalog_item(stype=SERVICE_TYPE, name="AC Repair", category="appliance", active=True):
    item = MagicMock()
    item.service_type_id = stype
    item.name = name
    item.category = category
    item.is_active = active
    return item


def make_area_row(
    tenant_id=TENANT_A, tenant_name="TechFix", health_score=80.0,
    area_id=AREA_A, coverage_type="city", area_city="Mumbai",
    area_zipcode=None, zone_id=None,
    area_lat=None, area_lng=None, radius_km=None,
    mapping_id=MAPPING_A, sla_minutes=120,
    base_price=500.0, min_price=400.0, max_price=800.0,
    service_name="AC Repair", category="appliance",
):
    r = MagicMock()
    r.tenant_id = tenant_id
    r.tenant_name = tenant_name
    r.health_score = health_score
    r.area_id = area_id
    r.coverage_type = coverage_type
    r.area_city = area_city
    r.area_zipcode = area_zipcode
    r.zone_id = zone_id
    r.area_lat = area_lat
    r.area_lng = area_lng
    r.radius_km = radius_km
    r.mapping_id = mapping_id
    r.sla_minutes = sla_minutes
    r.base_price = base_price
    r.min_price = min_price
    r.max_price = max_price
    r.service_name = service_name
    r.category = category
    return r


def make_zone(zone_id=ZONE_ID, zone_type="pincode", identifiers=None, zone_name="Z1", active=True):
    z = MagicMock()
    z.id = zone_id
    z.zone_type = zone_type
    z.identifiers = identifiers or []
    z.zone_name = zone_name
    z.is_active = active
    return z


def make_agg_row(entity_id: str, avg_composite: float):
    r = MagicMock()
    r.entity_id = entity_id
    r.avg_composite = avg_composite
    return r


def make_staff_row(tenant_id: uuid.UUID, cnt: int):
    r = MagicMock()
    r.tenant_id = tenant_id
    r.cnt = cnt
    return r


def make_address(**kwargs):
    addr = MagicMock()
    addr.id = uuid.uuid4()
    addr.customer_id = CUSTOMER_ID
    addr.city = "Mumbai"
    addr.state = "Maharashtra"
    addr.zipcode = "400001"
    addr.latitude = None
    addr.longitude = None
    addr.is_active = True
    for k, v in kwargs.items():
        setattr(addr, k, v)
    return addr


# Convenience: set up execute for a standard city-only matching run
def setup_city_match(db, city_rows, agg_rows=None, staff_rows=None):
    db.execute.side_effect = [
        exec_rows(*city_rows),
        exec_rows(*(agg_rows or [])),
        exec_rows(*(staff_rows or [])),
    ]


# ══════════════════════════════════════════════════════════════════════════════
# Tests 1–3: Helper methods
# ══════════════════════════════════════════════════════════════════════════════

def test_01_norm_strips_and_lowercases():
    svc = ServiceabilityService.__new__(ServiceabilityService)
    assert svc._norm("  Mumbai  ") == "mumbai"
    assert svc._norm("NEW DELHI") == "new delhi"
    assert svc._norm(None) == ""


def test_02_strip_zip_trims_whitespace():
    svc = ServiceabilityService.__new__(ServiceabilityService)
    assert svc._strip_zip("  400001  ") == "400001"
    assert svc._strip_zip(None) == ""


def test_03_haversine_known_distance():
    svc = ServiceabilityService.__new__(ServiceabilityService)
    # Mumbai (19.076, 72.877) to Pune (18.520, 73.856) ≈ 120 km
    dist = svc._haversine_km(19.076, 72.877, 18.520, 73.856)
    assert 115 < dist < 135


# ══════════════════════════════════════════════════════════════════════════════
# Tests 4–8: _validate_check_request
# ══════════════════════════════════════════════════════════════════════════════

def test_04_validate_missing_service_id():
    svc = make_svc(make_db())
    with pytest.raises(ServiceOSException) as exc:
        svc._validate_check_request(None, "Mumbai", "MH", None, None, "repair")
    assert exc.value.error_code == ERR_SERVICE_ID_REQUIRED


def test_05_validate_missing_job_type():
    svc = make_svc(make_db())
    with pytest.raises(ServiceOSException) as exc:
        svc._validate_check_request(None, "Mumbai", "MH", None, str(SERVICE_UUID), None)
    assert exc.value.error_code == ERR_INVALID_JOB_TYPE


def test_06_validate_invalid_job_type():
    svc = make_svc(make_db())
    with pytest.raises(ServiceOSException) as exc:
        svc._validate_check_request(None, "Mumbai", "MH", None, str(SERVICE_UUID), "painting")
    assert exc.value.error_code == ERR_INVALID_JOB_TYPE


def test_07_validate_missing_city_no_address_id():
    svc = make_svc(make_db())
    with pytest.raises(ServiceOSException) as exc:
        svc._validate_check_request(None, None, "MH", None, str(SERVICE_UUID), "repair")
    assert exc.value.error_code == ERR_CHECK_CITY_REQUIRED


def test_08_validate_missing_state_no_address_id():
    svc = make_svc(make_db())
    with pytest.raises(ServiceOSException) as exc:
        svc._validate_check_request(None, "Mumbai", None, None, str(SERVICE_UUID), "repair")
    assert exc.value.error_code == ERR_CHECK_STATE_REQUIRED


# ══════════════════════════════════════════════════════════════════════════════
# Tests 9–11: _resolve_service_type_id + address not found
# ══════════════════════════════════════════════════════════════════════════════

async def test_09_resolve_service_type_id_not_found():
    db = make_db()
    db.get.return_value = None
    svc = make_svc(db)
    with pytest.raises(ServiceOSException) as exc:
        await svc._resolve_service_type_id(str(SERVICE_UUID))
    assert exc.value.error_code == ERR_SERVICE_NOT_FOUND


async def test_10_resolve_service_type_id_inactive():
    db = make_db()
    db.get.return_value = make_catalog_item(active=False)
    svc = make_svc(db)
    with pytest.raises(ServiceOSException) as exc:
        await svc._resolve_service_type_id(str(SERVICE_UUID))
    assert exc.value.error_code == ERR_SERVICE_NOT_ACTIVE


async def test_11_resolve_service_type_id_success():
    db = make_db()
    db.get.return_value = make_catalog_item(stype="plumbing_fix", name="Pipe Repair", category="plumbing")
    svc = make_svc(db)
    stype, name, cat = await svc._resolve_service_type_id(str(SERVICE_UUID))
    assert stype == "plumbing_fix"
    assert name == "Pipe Repair"
    assert cat == "plumbing"


# ══════════════════════════════════════════════════════════════════════════════
# Tests 12–14: City coverage matching
# ══════════════════════════════════════════════════════════════════════════════

async def test_12_city_match_returns_tenant():
    db = make_db()
    row = make_area_row(coverage_type="city", area_city="Mumbai")
    setup_city_match(db, [row])
    svc = make_svc(db)
    result = await svc.match_tenants_for_location(
        "Mumbai", "MH", None, None, None, SERVICE_TYPE, "repair")
    assert len(result) == 1
    assert result[0]["tenant_id"] == str(TENANT_A)
    assert result[0]["coverage_match_level"] == MatchLevel.CITY


async def test_13_city_match_is_case_insensitive():
    db = make_db()
    row = make_area_row(coverage_type="city", area_city="mumbai")
    setup_city_match(db, [row])
    svc = make_svc(db)
    result = await svc.match_tenants_for_location(
        "MUMBAI", "MH", None, None, None, SERVICE_TYPE, "repair")
    assert len(result) == 1
    assert result[0]["coverage_match_level"] == MatchLevel.CITY


async def test_14_city_mismatch_excluded():
    db = make_db()
    row = make_area_row(coverage_type="city", area_city="Pune")
    setup_city_match(db, [row])
    svc = make_svc(db)
    result = await svc.match_tenants_for_location(
        "Mumbai", "MH", None, None, None, SERVICE_TYPE, "repair")
    assert result == []


# ══════════════════════════════════════════════════════════════════════════════
# Tests 15–17: Zipcode coverage matching
# ══════════════════════════════════════════════════════════════════════════════

async def test_15_zipcode_match_correct_city_and_zip():
    db = make_db()
    row = make_area_row(coverage_type="zipcode", area_city="Mumbai", area_zipcode="400001")
    setup_city_match(db, [row])
    svc = make_svc(db)
    result = await svc.match_tenants_for_location(
        "Mumbai", "MH", "400001", None, None, SERVICE_TYPE, "repair")
    assert len(result) == 1
    assert result[0]["coverage_match_level"] == MatchLevel.ZIPCODE


async def test_16_zipcode_excluded_when_city_mismatches():
    db = make_db()
    row = make_area_row(coverage_type="zipcode", area_city="Pune", area_zipcode="400001")
    setup_city_match(db, [row])
    svc = make_svc(db)
    result = await svc.match_tenants_for_location(
        "Mumbai", "MH", "400001", None, None, SERVICE_TYPE, "repair")
    assert result == []


async def test_17_zipcode_excluded_when_zip_mismatches():
    db = make_db()
    row = make_area_row(coverage_type="zipcode", area_city="Mumbai", area_zipcode="400002")
    setup_city_match(db, [row])
    svc = make_svc(db)
    result = await svc.match_tenants_for_location(
        "Mumbai", "MH", "400001", None, None, SERVICE_TYPE, "repair")
    assert result == []


# ══════════════════════════════════════════════════════════════════════════════
# Tests 18–20: Zone coverage matching
# ══════════════════════════════════════════════════════════════════════════════

async def test_18_zone_pincode_match():
    db = make_db()
    row = make_area_row(coverage_type="zone", zone_id=ZONE_ID)
    zone = make_zone(zone_type="pincode", identifiers=["400001", "400002"])
    db.execute.side_effect = [
        exec_rows(row),          # main query
        exec_scalars(zone),       # zone batch load
        exec_rows(),              # agg
        exec_rows(),              # staff
    ]
    svc = make_svc(db)
    result = await svc.match_tenants_for_location(
        "Mumbai", "MH", "400001", None, None, SERVICE_TYPE, "repair")
    assert len(result) == 1
    assert result[0]["coverage_match_level"] == MatchLevel.ZONE
    assert "pincode" in result[0]["match_reason"]


async def test_19_zone_area_name_match():
    db = make_db()
    row = make_area_row(coverage_type="zone", zone_id=ZONE_ID)
    zone = make_zone(zone_type="area_name", identifiers=["mumbai", "Thane"])
    db.execute.side_effect = [
        exec_rows(row),
        exec_scalars(zone),
        exec_rows(),
        exec_rows(),
    ]
    svc = make_svc(db)
    result = await svc.match_tenants_for_location(
        "Mumbai", "MH", None, None, None, SERVICE_TYPE, "repair")
    assert len(result) == 1
    assert result[0]["coverage_match_level"] == MatchLevel.ZONE


async def test_20_zone_pincode_no_match():
    db = make_db()
    row = make_area_row(coverage_type="zone", zone_id=ZONE_ID)
    zone = make_zone(zone_type="pincode", identifiers=["411001", "411002"])
    db.execute.side_effect = [
        exec_rows(row),
        exec_scalars(zone),
        exec_rows(),
        exec_rows(),
    ]
    svc = make_svc(db)
    result = await svc.match_tenants_for_location(
        "Mumbai", "MH", "400001", None, None, SERVICE_TYPE, "repair")
    assert result == []


# ══════════════════════════════════════════════════════════════════════════════
# Tests 21–23: Radius coverage matching
# ══════════════════════════════════════════════════════════════════════════════

async def test_21_radius_match_within_range():
    db = make_db()
    # Center: Mumbai (19.076, 72.877), radius 50 km
    row = make_area_row(
        coverage_type="radius",
        area_lat=19.076, area_lng=72.877, radius_km=50.0)
    setup_city_match(db, [row])
    svc = make_svc(db)
    # Customer at 19.100, 72.900 — very close, ~3 km
    result = await svc.match_tenants_for_location(
        "Mumbai", "MH", None, 19.100, 72.900, SERVICE_TYPE, "repair")
    assert len(result) == 1
    assert result[0]["coverage_match_level"] == MatchLevel.RADIUS
    assert result[0]["distance_km"] is not None
    assert result[0]["distance_km"] < 50.0


async def test_22_radius_no_match_outside_range():
    db = make_db()
    row = make_area_row(
        coverage_type="radius",
        area_lat=19.076, area_lng=72.877, radius_km=5.0)
    setup_city_match(db, [row])
    svc = make_svc(db)
    # Pune coordinates — ~120 km away
    result = await svc.match_tenants_for_location(
        "Pune", "MH", None, 18.520, 73.856, SERVICE_TYPE, "repair")
    assert result == []


async def test_23_radius_skipped_without_customer_coords():
    db = make_db()
    row = make_area_row(
        coverage_type="radius",
        area_lat=19.076, area_lng=72.877, radius_km=50.0)
    setup_city_match(db, [row])
    svc = make_svc(db)
    result = await svc.match_tenants_for_location(
        "Mumbai", "MH", None, None, None, SERVICE_TYPE, "repair")
    assert result == []


# ══════════════════════════════════════════════════════════════════════════════
# Tests 24–27: Deduplication and ranking
# ══════════════════════════════════════════════════════════════════════════════

async def test_24_dedup_keeps_best_match_level_per_tenant():
    db = make_db()
    city_row = make_area_row(tenant_id=TENANT_A, area_id=AREA_A, coverage_type="city",
                              area_city="Mumbai", mapping_id=MAPPING_A)
    zip_row  = make_area_row(tenant_id=TENANT_A, area_id=AREA_B, coverage_type="zipcode",
                              area_city="Mumbai", area_zipcode="400001", mapping_id=MAPPING_B)
    setup_city_match(db, [city_row, zip_row])
    svc = make_svc(db)
    result = await svc.match_tenants_for_location(
        "Mumbai", "MH", "400001", None, None, SERVICE_TYPE, "repair")
    # Only one entry for TENANT_A — the zipcode match (rank 1)
    assert len(result) == 1
    assert result[0]["coverage_match_level"] == MatchLevel.ZIPCODE


async def test_25_ranking_zipcode_before_city():
    db = make_db()
    city_row = make_area_row(tenant_id=TENANT_A, coverage_type="city",
                              area_city="Mumbai", health_score=99.0)
    zip_row  = make_area_row(tenant_id=TENANT_B, coverage_type="zipcode",
                              area_city="Mumbai", area_zipcode="400001", health_score=10.0)
    setup_city_match(db, [city_row, zip_row])
    svc = make_svc(db)
    result = await svc.match_tenants_for_location(
        "Mumbai", "MH", "400001", None, None, SERVICE_TYPE, "repair")
    assert result[0]["tenant_id"] == str(TENANT_B)  # zipcode wins despite lower health_score
    assert result[1]["tenant_id"] == str(TENANT_A)


async def test_26_ranking_health_score_tiebreak():
    db = make_db()
    low_health  = make_area_row(tenant_id=TENANT_A, coverage_type="city",
                                 area_city="Mumbai", health_score=60.0, mapping_id=MAPPING_A)
    high_health = make_area_row(tenant_id=TENANT_B, coverage_type="city",
                                 area_city="Mumbai", health_score=95.0, mapping_id=MAPPING_B)
    agg_rows = [make_agg_row(str(TENANT_A), 4.5), make_agg_row(str(TENANT_B), 3.0)]
    db.execute.side_effect = [
        exec_rows(low_health, high_health),
        exec_rows(*agg_rows),
        exec_rows(),
    ]
    svc = make_svc(db)
    result = await svc.match_tenants_for_location(
        "Mumbai", "MH", None, None, None, SERVICE_TYPE, "repair")
    # Both city level; TENANT_B has higher health_score (95 > 60)
    assert result[0]["tenant_id"] == str(TENANT_B)


async def test_27_ranking_rating_tiebreak():
    db = make_db()
    row_a = make_area_row(tenant_id=TENANT_A, coverage_type="city",
                           area_city="Mumbai", health_score=80.0, mapping_id=MAPPING_A)
    row_b = make_area_row(tenant_id=TENANT_B, coverage_type="city",
                           area_city="Mumbai", health_score=80.0, mapping_id=MAPPING_B)
    # TENANT_B has higher rating
    agg_rows = [make_agg_row(str(TENANT_A), 3.0), make_agg_row(str(TENANT_B), 4.8)]
    db.execute.side_effect = [
        exec_rows(row_a, row_b),
        exec_rows(*agg_rows),
        exec_rows(),
    ]
    svc = make_svc(db)
    result = await svc.match_tenants_for_location(
        "Mumbai", "MH", None, None, None, SERVICE_TYPE, "repair")
    assert result[0]["tenant_id"] == str(TENANT_B)
    assert result[0]["rating"] == 4.8


# ══════════════════════════════════════════════════════════════════════════════
# Tests 28–29: Cross-tenant service_type_id resolution
# ══════════════════════════════════════════════════════════════════════════════

async def test_28_cross_tenant_service_type_id_used_in_query():
    """_resolve_service_type_id returns the string stype from the catalog item."""
    db = make_db()
    db.get.return_value = make_catalog_item(stype="electrical_fix", name="Wiring Fix")
    svc = make_svc(db)
    stype, name, _ = await svc._resolve_service_type_id(str(SERVICE_UUID))
    assert stype == "electrical_fix"
    assert name == "Wiring Fix"


async def test_29_two_tenants_different_catalog_uuids_same_stype_both_match():
    db = make_db()
    row_a = make_area_row(tenant_id=TENANT_A, coverage_type="city",
                           area_city="Mumbai", mapping_id=MAPPING_A)
    row_b = make_area_row(tenant_id=TENANT_B, coverage_type="city",
                           area_city="Mumbai", mapping_id=MAPPING_B)
    setup_city_match(db, [row_a, row_b])
    svc = make_svc(db)
    result = await svc.match_tenants_for_location(
        "Mumbai", "MH", None, None, None, SERVICE_TYPE, "repair")
    tenant_ids = {r["tenant_id"] for r in result}
    assert str(TENANT_A) in tenant_ids
    assert str(TENANT_B) in tenant_ids


# ══════════════════════════════════════════════════════════════════════════════
# Tests 30–31: check_serviceability
# ══════════════════════════════════════════════════════════════════════════════

async def test_30_check_serviceability_available():
    db = make_db()
    catalog = make_catalog_item()
    db.get.return_value = catalog
    row = make_area_row(coverage_type="zipcode", area_city="Mumbai", area_zipcode="400001")
    db.execute.side_effect = [
        exec_rows(row),     # match query
        exec_rows(),        # agg
        exec_rows(),        # staff
        exec_scalar_one(0), # audit log commit — not a db.execute call actually
    ]
    svc = make_svc(db)
    resp = await svc.check_serviceability(
        address_id=None, city="Mumbai", state="MH", zipcode="400001",
        latitude=None, longitude=None, service_id=str(SERVICE_UUID), job_type="repair",
    )
    assert resp["service_available"] is True
    assert resp["matches"]["zipcode_level"] == 1
    assert resp["matches"]["city_level"] == 0
    assert resp["matches"]["zone_level"] == 0
    assert resp["service_type_id"] == SERVICE_TYPE


async def test_31_check_serviceability_unavailable_returns_message():
    db = make_db()
    db.get.return_value = make_catalog_item()
    db.execute.side_effect = [
        exec_rows(),    # no matches
        exec_rows(),    # agg (empty)
        exec_rows(),    # staff (empty)
    ]
    svc = make_svc(db)
    resp = await svc.check_serviceability(
        address_id=None, city="Kolkata", state="WB", zipcode=None,
        latitude=None, longitude=None, service_id=str(SERVICE_UUID), job_type="repair",
    )
    assert resp["service_available"] is False
    assert "not available" in resp["message"]
    assert resp["matched_tenants_count"] == 0


# ══════════════════════════════════════════════════════════════════════════════
# Tests 32–33: get_matching_tenants
# ══════════════════════════════════════════════════════════════════════════════

async def test_32_get_matching_tenants_full_structure():
    db = make_db()
    db.get.return_value = make_catalog_item()
    row = make_area_row(coverage_type="city", area_city="Mumbai")
    setup_city_match(db, [row])
    svc = make_svc(db)
    resp = await svc.get_matching_tenants(
        address_id=None, city="Mumbai", state="MH", zipcode=None,
        latitude=None, longitude=None, service_id=str(SERVICE_UUID), job_type="repair",
    )
    assert "matched_tenants" in resp
    assert resp["total_matched"] == 1
    assert resp["service_type_id"] == SERVICE_TYPE
    match = resp["matched_tenants"][0]
    assert "coverage_rank" in match
    assert "match_reason" in match
    assert "staff_capacity" in match


async def test_33_get_matching_tenants_tenant_owner_filtered_to_own_tenant():
    db = make_db()
    db.get.return_value = make_catalog_item()
    row_a = make_area_row(tenant_id=TENANT_A, coverage_type="city",
                           area_city="Mumbai", mapping_id=MAPPING_A)
    row_b = make_area_row(tenant_id=TENANT_B, coverage_type="city",
                           area_city="Mumbai", mapping_id=MAPPING_B)
    # match_tenants_for_location will be called with filter_tenant_id=TENANT_A
    # In the mock, we return both rows — but the WHERE filter would exclude TENANT_B in real DB.
    # Since we mock execute, we simulate the WHERE working by returning only TENANT_A's row.
    db.execute.side_effect = [
        exec_rows(row_a),   # main query (DB WHERE filters TENANT_B out)
        exec_rows(),        # agg
        exec_rows(),        # staff
    ]
    svc = make_svc(db, role="tenant_owner", actor_tenant_id=TENANT_A)
    resp = await svc.get_matching_tenants(
        address_id=None, city="Mumbai", state="MH", zipcode=None,
        latitude=None, longitude=None, service_id=str(SERVICE_UUID), job_type="repair",
    )
    # tenant_owner role → filter_tenant_id=TENANT_A passed to match_tenants_for_location
    assert resp["total_matched"] == 1
    assert resp["matched_tenants"][0]["tenant_id"] == str(TENANT_A)


# ══════════════════════════════════════════════════════════════════════════════
# Tests 34–35: get_available_services_for_address
# ══════════════════════════════════════════════════════════════════════════════

async def test_34_available_services_groups_by_service_type_id():
    db = make_db()
    # Two rows with same service_type_id from two tenants
    r1 = MagicMock()
    r1.service_type_id = "ac_repair"
    r1.service_name = "AC Service"
    r1.category = "appliance"
    r1.coverage_type = "city"
    r1.area_city = "Mumbai"
    r1.area_zipcode = None
    r1.zone_id = None
    r1.area_lat = None
    r1.area_lng = None
    r1.radius_km = None
    r1.job_type = "repair"
    r1.sla_minutes = 120
    r1.base_price = 500.0
    r1.tenant_id = TENANT_A

    r2 = MagicMock()
    r2.service_type_id = "ac_repair"  # same type, different tenant
    r2.service_name = "AC Service"
    r2.category = "appliance"
    r2.coverage_type = "city"
    r2.area_city = "mumbai"
    r2.area_zipcode = None
    r2.zone_id = None
    r2.area_lat = None
    r2.area_lng = None
    r2.radius_km = None
    r2.job_type = "service"
    r2.sla_minutes = 90
    r2.base_price = 400.0
    r2.tenant_id = TENANT_B

    db.execute.return_value = exec_rows(r1, r2)
    svc = make_svc(db)
    resp = await svc.get_available_services_for_address(
        address_id=None, city="Mumbai", state="MH")

    # Should have ONE service_type_id = "ac_repair"
    all_stypes = [s["service_type_id"]
                  for cat in resp["categories"]
                  for s in cat["services"]]
    assert len(all_stypes) == 1
    assert "ac_repair" in all_stypes
    assert resp["total_services"] == 1
    # Both tenants counted
    ac_svc = resp["categories"][0]["services"][0]
    assert ac_svc["available_tenants"] == 2


async def test_35_available_services_location_required():
    db = make_db()
    svc = make_svc(db)
    with pytest.raises(ServiceOSException) as exc:
        await svc.get_available_services_for_address(address_id=None, city=None)
    assert exc.value.error_code == ERR_LOCATION_REQUIRED


# ══════════════════════════════════════════════════════════════════════════════
# Test 36: admin_serviceability_test debug categories
# ══════════════════════════════════════════════════════════════════════════════

async def test_36_admin_test_classifies_non_matching_tenants():
    db = make_db()
    db.get.return_value = make_catalog_item()

    # match_tenants_for_location: TENANT_A matches, TENANT_B doesn't
    match_row = make_area_row(tenant_id=TENANT_A, coverage_type="city", area_city="Mumbai")

    # make_tenant rows for all_tenants query
    t_a = MagicMock()
    t_a.id = TENANT_A
    t_a.tenant_name = "TechFix A"

    t_b = MagicMock()
    t_b.id = TENANT_B
    t_b.tenant_name = "TechFix B"

    # raw_debug_row: TENANT_B has an active mapping but wrong city → coverage_mismatch
    debug_row = MagicMock()
    debug_row.tid = TENANT_B

    db.execute.side_effect = [
        exec_rows(match_row),       # match_tenants_for_location: main query
        exec_rows(),                # agg
        exec_rows(),                # staff
        exec_rows(t_a, t_b),        # all_tenants query
        exec_rows(debug_row),       # non-matched with active mapping (coverage_mismatch)
    ]

    svc = make_svc(db, role="super_admin")
    resp = await svc.admin_serviceability_test(
        city="Mumbai", state="MH", zipcode="400001",
        latitude=None, longitude=None,
        service_id=str(SERVICE_UUID), job_type="repair",
    )

    assert resp["total_matched"] == 1
    assert resp["matched_tenants"][0]["tenant_id"] == str(TENANT_A)

    non_match_reasons = {d["tenant_id"]: d["reason"] for d in resp["non_matching_debug"]}
    assert str(TENANT_B) in non_match_reasons
    assert non_match_reasons[str(TENANT_B)] == "coverage_mismatch"

    assert "query" in resp
    assert resp["query"]["service_type_id"] == SERVICE_TYPE
    assert resp["total_non_matching"] == 1
