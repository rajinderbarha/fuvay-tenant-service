"""Current geography authority and tenant pagination regression tests.

The old ``location_engine`` was intentionally removed because its four
normalised tables were never migrated. Provider-declared service areas and
customer addresses are the canonical pincode/city/state source.
"""
from __future__ import annotations

import pathlib
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest


ROOT = pathlib.Path(__file__).resolve().parents[1]


def _make_tenant_svc():
    from app.engines.tenant_engine.admin_service import AdminTenantService

    db = AsyncMock()
    svc = AdminTenantService.__new__(AdminTenantService)
    svc.db = db
    svc.request_id = "test-req"
    svc.actor_id = str(uuid.uuid4())
    svc.actor_role = "super_admin"
    svc.ip_address = "127.0.0.1"
    return svc, db


def _empty_page_results(total: int = 0):
    count_result = MagicMock()
    count_result.scalar_one.return_value = total
    items_result = MagicMock()
    items_result.scalars.return_value.all.return_value = []
    return [count_result, items_result]


def test_serviceability_is_the_canonical_geography_surface():
    source = (ROOT / "app/engines/serviceability/router.py").read_text(encoding="utf-8-sig")
    assert '"zipcode_matching"' in source
    assert '"customer_addresses"' in source
    assert '"/v1/tenant/service-areas"' in source


def test_removed_location_engine_is_not_mounted_as_second_authority():
    removed_dir = ROOT / "app/engines/location_engine"
    assert not removed_dir.exists() or not any(removed_dir.glob("*.py"))
    main = (ROOT / "app/main.py").read_text(encoding="utf-8-sig")
    assert "The location engine was removed" in main


@pytest.mark.asyncio
async def test_list_tenants_returns_server_pagination():
    svc, db = _make_tenant_svc()
    db.execute.side_effect = _empty_page_results(total=5)
    result = await svc.list_tenants({"page": 1, "page_size": 25})
    assert result["items"] == []
    assert result["pagination"]["total_items"] == 5
    assert result["pagination"]["page"] == 1


@pytest.mark.asyncio
async def test_list_tenants_rejects_oversized_page():
    from app.exceptions import ServiceOSException

    svc, _ = _make_tenant_svc()
    with pytest.raises(ServiceOSException) as exc:
        await svc.list_tenants({"page": 1, "page_size": 101})
    assert exc.value.error_code == "PAGE_SIZE_TOO_LARGE"


@pytest.mark.asyncio
async def test_list_tenants_rejects_unknown_sort_field():
    from app.exceptions import ServiceOSException

    svc, _ = _make_tenant_svc()
    with pytest.raises(ServiceOSException) as exc:
        await svc.list_tenants({"sort_by": "password_hash"})
    assert exc.value.error_code == "SORT_FIELD_NOT_ALLOWED"


@pytest.mark.asyncio
@pytest.mark.parametrize("field,value", [
    ("state", "Punjab"),
    ("district", "Ludhiana"),
    ("city_tier", "metro"),
    ("zipcode", "141002"),
])
async def test_list_tenants_reports_geography_filters(field: str, value: str):
    svc, db = _make_tenant_svc()
    db.execute.side_effect = _empty_page_results()
    result = await svc.list_tenants({"page": 1, "page_size": 10, field: value})
    assert result["filters_applied"][field] == value


def test_current_pagination_error_codes_are_registered():
    from app.schemas.base import ERROR_CODES

    for code in ("PAGE_SIZE_TOO_LARGE", "SORT_FIELD_NOT_ALLOWED", "FILTER_FIELD_NOT_ALLOWED"):
        assert code in ERROR_CODES
