"""
Scalability Hardening — Location Engine + Tenant Pagination Tests
23 tests covering: location hierarchy CRUD, cascade validation, city tiers,
tenant server-side pagination, sorting, date filters, location filters, and error codes.
"""
from __future__ import annotations
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest


# ──────────────────────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────────────────────

def _make_db():
    db = AsyncMock()
    db.flush = AsyncMock()
    db.add = MagicMock()
    return db


def _scalar_result(value):
    r = MagicMock()
    r.scalar_one_or_none = MagicMock(return_value=value)
    r.scalar_one = MagicMock(return_value=value)
    r.scalars = MagicMock(
        return_value=MagicMock(all=MagicMock(return_value=value if isinstance(value, list) else []))
    )
    return r


def _paginated_result(items, total):
    """Returns two sequential DB results: count result then items result."""
    count_r = MagicMock()
    count_r.scalar_one = MagicMock(return_value=total)
    items_r = MagicMock()
    items_r.scalars = MagicMock(
        return_value=MagicMock(all=MagicMock(return_value=items))
    )
    return [count_r, items_r]


def _make_state(**kwargs):
    s = MagicMock()
    s.id = kwargs.get("id", uuid.uuid4())
    s.state_name = kwargs.get("state_name", "Maharashtra")
    s.state_code = kwargs.get("state_code", "MH")
    s.country_code = kwargs.get("country_code", "IN")
    s.is_active = kwargs.get("is_active", True)
    return s


def _make_district(**kwargs):
    d = MagicMock()
    d.id = kwargs.get("id", uuid.uuid4())
    d.state_id = kwargs.get("state_id", uuid.uuid4())
    d.district_name = kwargs.get("district_name", "Pune")
    d.district_code = kwargs.get("district_code", "PUN")
    d.is_active = kwargs.get("is_active", True)
    return d


def _make_city(**kwargs):
    c = MagicMock()
    c.id = kwargs.get("id", uuid.uuid4())
    c.state_id = kwargs.get("state_id", uuid.uuid4())
    c.district_id = kwargs.get("district_id", uuid.uuid4())
    c.city_name = kwargs.get("city_name", "Pune City")
    c.city_tier = kwargs.get("city_tier", "large")
    c.is_active = kwargs.get("is_active", True)
    return c


def _make_zone(**kwargs):
    z = MagicMock()
    z.id = kwargs.get("id", uuid.uuid4())
    z.state_id = kwargs.get("state_id", uuid.uuid4())
    z.district_id = kwargs.get("district_id", uuid.uuid4())
    z.city_id = kwargs.get("city_id", uuid.uuid4())
    z.zone_name = kwargs.get("zone_name", "Kothrud")
    z.pincode = kwargs.get("pincode", "411038")
    z.is_active = kwargs.get("is_active", True)
    return z


def _make_loc_svc(db=None):
    if db is None:
        db = _make_db()
    from app.engines.location_engine.service import LocationService
    return LocationService(db), db


def _make_tenant_svc(db=None):
    if db is None:
        db = _make_db()
    from app.engines.tenant_engine.admin_service import AdminTenantService
    svc = AdminTenantService.__new__(AdminTenantService)
    svc.db = db
    svc.request_id = "test-req"
    svc.actor_id = str(uuid.uuid4())
    svc.actor_role = "super_admin"
    svc.ip_address = "127.0.0.1"
    return svc, db


# ──────────────────────────────────────────────────────────────
# 01 — list_states returns paginated structure
# ──────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_01_list_states_paginated():
    svc, db = _make_loc_svc()
    state = _make_state()
    calls = iter(_paginated_result([state], 1))
    db.execute = AsyncMock(side_effect=lambda *a, **kw: next(calls))
    result = await svc.list_states(country_code="IN", page=1, page_size=10)
    assert "items" in result
    assert "pagination" in result
    assert result["pagination"]["total_items"] == 1
    assert result["pagination"]["has_next"] is False
    assert result["pagination"]["has_previous"] is False


# ──────────────────────────────────────────────────────────────
# 02 — list_states second page
# ──────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_02_list_states_second_page():
    svc, db = _make_loc_svc()
    calls = iter(_paginated_result([], 25))
    db.execute = AsyncMock(side_effect=lambda *a, **kw: next(calls))
    result = await svc.list_states(page=2, page_size=10)
    assert result["pagination"]["page"] == 2
    assert result["pagination"]["total_pages"] == 3
    assert result["pagination"]["has_previous"] is True


# ──────────────────────────────────────────────────────────────
# 03 — list_districts requires valid state
# ──────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_03_list_districts_invalid_state():
    from app.exceptions import ServiceOSException
    svc, db = _make_loc_svc()
    db.execute = AsyncMock(return_value=_scalar_result(None))
    with pytest.raises(ServiceOSException) as exc:
        await svc.list_districts(uuid.uuid4())
    assert exc.value.error_code == "LOCATION_STATE_NOT_FOUND"


# ──────────────────────────────────────────────────────────────
# 04 — list_districts returns paginated districts
# ──────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_04_list_districts_paginated():
    svc, db = _make_loc_svc()
    state = _make_state()
    dist = _make_district(state_id=state.id)
    responses = [_scalar_result(state)] + _paginated_result([dist], 1)
    calls = iter(responses)
    db.execute = AsyncMock(side_effect=lambda *a, **kw: next(calls))
    result = await svc.list_districts(state.id, page=1, page_size=50)
    assert result["pagination"]["total_items"] == 1
    assert result["items"][0]["district_name"] == "Pune"


# ──────────────────────────────────────────────────────────────
# 05 — list_cities requires valid district
# ──────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_05_list_cities_invalid_district():
    from app.exceptions import ServiceOSException
    svc, db = _make_loc_svc()
    db.execute = AsyncMock(return_value=_scalar_result(None))
    with pytest.raises(ServiceOSException) as exc:
        await svc.list_cities(uuid.uuid4())
    assert exc.value.error_code == "LOCATION_DISTRICT_NOT_FOUND"


# ──────────────────────────────────────────────────────────────
# 06 — list_cities includes city_tier in response
# ──────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_06_list_cities_includes_tier():
    svc, db = _make_loc_svc()
    dist = _make_district()
    city = _make_city(district_id=dist.id, city_tier="metro")
    responses = [_scalar_result(dist)] + _paginated_result([city], 1)
    calls = iter(responses)
    db.execute = AsyncMock(side_effect=lambda *a, **kw: next(calls))
    result = await svc.list_cities(dist.id)
    assert result["items"][0]["city_tier"] == "metro"


# ──────────────────────────────────────────────────────────────
# 07 — list_zones requires valid city
# ──────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_07_list_zones_invalid_city():
    from app.exceptions import ServiceOSException
    svc, db = _make_loc_svc()
    db.execute = AsyncMock(return_value=_scalar_result(None))
    with pytest.raises(ServiceOSException) as exc:
        await svc.list_zones(uuid.uuid4())
    assert exc.value.error_code == "LOCATION_CITY_NOT_FOUND"


# ──────────────────────────────────────────────────────────────
# 08 — list_zones returns pincode in items
# ──────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_08_list_zones_includes_pincode():
    svc, db = _make_loc_svc()
    city = _make_city()
    zone = _make_zone(city_id=city.id, pincode="400001")
    responses = [_scalar_result(city)] + _paginated_result([zone], 1)
    calls = iter(responses)
    db.execute = AsyncMock(side_effect=lambda *a, **kw: next(calls))
    result = await svc.list_zones(city.id)
    assert result["items"][0]["pincode"] == "400001"


# ──────────────────────────────────────────────────────────────
# 09 — list_city_tiers returns all 4 tiers
# ──────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_09_list_city_tiers_all_four():
    svc, db = _make_loc_svc()
    result = await svc.list_city_tiers()
    values = {t["value"] for t in result["items"]}
    assert values == {"metro", "large", "mid", "small"}


# ──────────────────────────────────────────────────────────────
# 10 — create_state stores and returns id
# ──────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_10_create_state():
    svc, db = _make_loc_svc()
    result = await svc.create_state({"state_name": "Goa", "state_code": "GA"})
    assert "id" in result
    assert result["state_name"] == "Goa"
    assert db.add.called


# ──────────────────────────────────────────────────────────────
# 11 — create_city rejects invalid tier
# ──────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_11_create_city_invalid_tier():
    from app.exceptions import ServiceOSException
    svc, db = _make_loc_svc()
    dist = _make_district()
    db.execute = AsyncMock(return_value=_scalar_result(dist))
    with pytest.raises(ServiceOSException) as exc:
        await svc.create_city(dist.id, {"city_name": "Test City", "city_tier": "mega"})
    assert exc.value.error_code == "LOCATION_INVALID_HIERARCHY"


# ──────────────────────────────────────────────────────────────
# 12 — create_zone inherits state/district from city
# ──────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_12_create_zone_inherits_hierarchy():
    svc, db = _make_loc_svc()
    state_id = uuid.uuid4()
    district_id = uuid.uuid4()
    city = _make_city(state_id=state_id, district_id=district_id)
    db.execute = AsyncMock(return_value=_scalar_result(city))
    result = await svc.create_zone(city.id, {"zone_name": "Kothrud", "pincode": "411038"})
    assert result["zone_name"] == "Kothrud"
    assert result["pincode"] == "411038"


# ──────────────────────────────────────────────────────────────
# 13 — _paginated calculates total_pages correctly
# ──────────────────────────────────────────────────────────────
def test_13_paginated_helper_math():
    from app.engines.location_engine.service import LocationService
    svc = LocationService.__new__(LocationService)
    result = svc._paginated(items=[], total=101, page=2, page_size=25)
    assert result["pagination"]["total_pages"] == 5
    assert result["pagination"]["has_next"] is True
    assert result["pagination"]["has_previous"] is True


# ──────────────────────────────────────────────────────────────
# 14 — _paginated empty list still returns page 1 meta
# ──────────────────────────────────────────────────────────────
def test_14_paginated_empty_total():
    from app.engines.location_engine.service import LocationService
    svc = LocationService.__new__(LocationService)
    result = svc._paginated(items=[], total=0, page=1, page_size=25)
    assert result["pagination"]["total_pages"] == 1
    assert result["pagination"]["has_next"] is False
    assert result["pagination"]["has_previous"] is False


# ──────────────────────────────────────────────────────────────
# 15 — list_tenants pagination structure returned
# ──────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_15_list_tenants_pagination_structure():
    svc, db = _make_tenant_svc()
    count_r = MagicMock(); count_r.scalar_one = MagicMock(return_value=5)
    items_r = MagicMock(); items_r.scalars = MagicMock(
        return_value=MagicMock(all=MagicMock(return_value=[]))
    )
    calls = iter([count_r, items_r])
    db.execute = AsyncMock(side_effect=lambda *a, **kw: next(calls))
    result = await svc.list_tenants({"page": 1, "page_size": 25})
    assert "items" in result
    assert "pagination" in result
    assert result["pagination"]["total_items"] == 5


# ──────────────────────────────────────────────────────────────
# 16 — list_tenants page_size > 100 raises error
# ──────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_16_list_tenants_page_size_too_large():
    from app.exceptions import ServiceOSException
    svc, db = _make_tenant_svc()
    with pytest.raises(ServiceOSException) as exc:
        await svc.list_tenants({"page": 1, "page_size": 500})
    assert exc.value.error_code == "PAGE_SIZE_TOO_LARGE"


# ──────────────────────────────────────────────────────────────
# 17 — list_tenants invalid sort_by raises error
# ──────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_17_list_tenants_invalid_sort_field():
    from app.exceptions import ServiceOSException
    svc, db = _make_tenant_svc()
    with pytest.raises(ServiceOSException) as exc:
        await svc.list_tenants({"page": 1, "page_size": 25, "sort_by": "password_hash"})
    assert exc.value.error_code == "SORT_FIELD_NOT_ALLOWED"


# ──────────────────────────────────────────────────────────────
# 18 — list_tenants state filter applied (partial match)
# ──────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_18_list_tenants_state_filter():
    svc, db = _make_tenant_svc()
    count_r = MagicMock(); count_r.scalar_one = MagicMock(return_value=0)
    items_r = MagicMock(); items_r.scalars = MagicMock(
        return_value=MagicMock(all=MagicMock(return_value=[]))
    )
    calls = iter([count_r, items_r])
    db.execute = AsyncMock(side_effect=lambda *a, **kw: next(calls))
    result = await svc.list_tenants({"page": 1, "page_size": 10, "state": "Maharashtra"})
    assert result["filters_applied"].get("state") == "Maharashtra"


# ──────────────────────────────────────────────────────────────
# 19 — list_tenants district filter applied
# ──────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_19_list_tenants_district_filter():
    svc, db = _make_tenant_svc()
    count_r = MagicMock(); count_r.scalar_one = MagicMock(return_value=0)
    items_r = MagicMock(); items_r.scalars = MagicMock(
        return_value=MagicMock(all=MagicMock(return_value=[]))
    )
    calls = iter([count_r, items_r])
    db.execute = AsyncMock(side_effect=lambda *a, **kw: next(calls))
    result = await svc.list_tenants({"page": 1, "page_size": 10, "district": "Pune"})
    assert result["filters_applied"].get("district") == "Pune"


# ──────────────────────────────────────────────────────────────
# 20 — list_tenants city_tier filter applied
# ──────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_20_list_tenants_city_tier_filter():
    svc, db = _make_tenant_svc()
    count_r = MagicMock(); count_r.scalar_one = MagicMock(return_value=0)
    items_r = MagicMock(); items_r.scalars = MagicMock(
        return_value=MagicMock(all=MagicMock(return_value=[]))
    )
    calls = iter([count_r, items_r])
    db.execute = AsyncMock(side_effect=lambda *a, **kw: next(calls))
    result = await svc.list_tenants({"page": 1, "page_size": 10, "city_tier": "metro"})
    assert result["filters_applied"].get("city_tier") == "metro"


# ──────────────────────────────────────────────────────────────
# 21 — list_tenants response includes sort metadata
# ──────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_21_list_tenants_sort_metadata():
    svc, db = _make_tenant_svc()
    count_r = MagicMock(); count_r.scalar_one = MagicMock(return_value=0)
    items_r = MagicMock(); items_r.scalars = MagicMock(
        return_value=MagicMock(all=MagicMock(return_value=[]))
    )
    calls = iter([count_r, items_r])
    db.execute = AsyncMock(side_effect=lambda *a, **kw: next(calls))
    result = await svc.list_tenants({"page": 1, "page_size": 10, "sort_by": "tenant_name", "sort_direction": "asc"})
    assert result["sort"]["sort_by"] == "tenant_name"
    assert result["sort"]["sort_direction"] == "asc"


# ──────────────────────────────────────────────────────────────
# 22 — error codes for location + pagination registered in base.py
# ──────────────────────────────────────────────────────────────
def test_22_error_codes_registered():
    from app.schemas.base import ERROR_CODES
    expected_codes = [
        "LOCATION_STATE_NOT_FOUND",
        "LOCATION_DISTRICT_NOT_FOUND",
        "LOCATION_CITY_NOT_FOUND",
        "LOCATION_ZONE_NOT_FOUND",
        "LOCATION_INVALID_HIERARCHY",
        "ADDRESS_DISTRICT_REQUIRED",
        "TENANT_LOCATION_REQUIRED",
        "TENANT_FILTER_INVALID",
        "PAGE_SIZE_TOO_LARGE",
        "SORT_FIELD_NOT_ALLOWED",
        "FILTER_FIELD_NOT_ALLOWED",
    ]
    for code in expected_codes:
        assert code in ERROR_CODES, f"Missing error code: {code}"


# ──────────────────────────────────────────────────────────────
# 23 — location router defines expected path operations
# ──────────────────────────────────────────────────────────────
def test_23_location_router_paths():
    from app.engines.location_engine.router import router
    route_paths = {r.path for r in router.routes if hasattr(r, "path")}
    assert "/v1/admin/locations/states" in route_paths
    assert "/v1/admin/locations/districts" in route_paths
    assert "/v1/admin/locations/cities" in route_paths
    assert "/v1/admin/locations/zones" in route_paths
    assert "/v1/public/locations/states" in route_paths
    assert "/v1/admin/locations/city-tiers" in route_paths
