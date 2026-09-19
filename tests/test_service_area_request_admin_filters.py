import uuid
from types import SimpleNamespace

import pytest

from app.engines.serviceability.service import ServiceabilityService


class _Result:
    def __init__(self, *, scalar=None, scalars=None, rows=None):
        self._scalar = scalar
        self._scalars = scalars or []
        self._rows = rows or []

    def scalar_one(self):
        return self._scalar

    def scalars(self):
        return self

    def all(self):
        return self._rows or self._scalars


@pytest.mark.asyncio
async def test_admin_request_list_filters_on_city_and_zipcode_from_same_item():
    statements = []

    class _DB:
        async def execute(self, statement):
            statements.append(str(statement))
            return _Result(scalar=0)

    result = await ServiceabilityService(
        _DB(), actor_role="super_admin",
    ).list_service_area_requests(city="Bassi Pathana", zipcode="140412")

    assert result == {"requests": [], "total": 0, "next_cursor": None}
    count_sql = statements[0].lower()
    assert "tenant_service_area_request_items.city" in count_sql
    assert "tenant_service_area_request_items.zipcode" in count_sql
    assert "tenant_service_area_request_items.request_id" in count_sql


@pytest.mark.asyncio
async def test_admin_request_list_returns_real_provider_location_and_service_summary():
    request_id = uuid.uuid4()
    tenant_id = uuid.uuid4()
    category_id = uuid.uuid4()
    request = SimpleNamespace(
        id=request_id,
        tenant_id=tenant_id,
        category_id=category_id,
        to_dict=lambda: {
            "id": str(request_id),
            "tenant_id": str(tenant_id),
            "category_id": str(category_id),
            "status": "SUBMITTED",
        },
    )
    responses = iter([
        _Result(scalar=1),
        _Result(scalars=[request]),
        _Result(rows=[SimpleNamespace(
            request_id=request_id,
            city="Bassi Pathana",
            zipcode="140412",
            decision_status="PENDING",
            service_name="Air Conditioner",
        )]),
        _Result(rows=[SimpleNamespace(
            id=tenant_id,
            business_name="Test AC Service",
            tenant_name="Test tenant",
        )]),
        _Result(rows=[SimpleNamespace(id=category_id, name="Home Services")]),
    ])

    class _DB:
        async def execute(self, _statement):
            return next(responses)

    result = await ServiceabilityService(
        _DB(), actor_role="super_admin",
    ).list_service_area_requests(city="Bassi Pathana", zipcode="140412")

    row = result["requests"][0]
    assert row["tenant_name"] == "Test AC Service"
    assert row["category_name"] == "Home Services"
    assert row["cities"] == ["Bassi Pathana"]
    assert row["zipcodes"] == ["140412"]
    assert row["service_names"] == ["Air Conditioner"]
    assert row["item_count"] == 1
    assert row["pending_item_count"] == 1


def test_admin_page_forwards_dashboard_location_filters_to_api():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    page = (root / "frontend/super-admin/app/admin/service-area-requests/page.tsx").read_text(
        encoding="utf-8",
    )
    api = (root / "frontend/super-admin/lib/api.ts").read_text(encoding="utf-8")

    assert 'params.get("city")' in page
    assert 'params.get("zipcode")' in page
    assert "city: city || undefined" in page
    assert "zipcode: zipcode || undefined" in page
    assert "tenant_name?:string|null" in api
    assert "city?:string; zipcode?:string" in api
