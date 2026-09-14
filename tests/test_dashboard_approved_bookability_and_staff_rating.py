"""Regression coverage for admin readiness and legacy Home Services staff ratings."""
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
import uuid

import pytest

from app.engines.dashboard_command_center import service as dashboard_module
from app.engines.customer_reviews import hs_review_router
from app.engines.vertical_directory.service import VerticalStaffDirectoryService
from app.exceptions import ServiceOSException


@pytest.mark.asyncio
async def test_bookability_health_excludes_active_but_unverified_provider(monkeypatch):
    queries = []

    async def count(_db, query):
        queries.append(query)
        if "SELECT COUNT(*) FROM tenants" in query and "verification_status" not in query:
            return 4
        if "SELECT COUNT(*) FROM tenants" in query and "verification_status" in query:
            return 3
        if "pvs.is_bookable = true" in query:
            return 3
        return 1

    monkeypatch.setattr(dashboard_module, "_safe_count", count)
    result = await dashboard_module.DashboardCommandCenterService(MagicMock()).get_home_services_summary()
    assert result["home_services_providers"] == 4
    assert result["approved_home_services_providers"] == 3
    assert result["awaiting_verification_providers"] == 1
    assert result["provider_bookability_health"] == {
        "status": "healthy", "bookable_providers": 3,
        "not_bookable_providers": 0, "eligible_providers": 3,
    }
    assert any("verification_status IN ('approved', 'verified')" in q and "pvs.is_bookable = true" in q for q in queries)


@pytest.mark.asyncio
async def test_lifecycle_non_bookable_uses_same_approved_pool(monkeypatch):
    async def count(_db, query):
        if "p.is_bookable=true" in query:
            assert "t.verification_status IN ('approved','verified')" in query
            return 3
        if "vertical='home_services' AND status='active'" in query:
            assert "verification_status IN ('approved','verified')" in query
            return 3
        return 0

    monkeypatch.setattr(dashboard_module, "_safe_count", count)
    result = await dashboard_module.DashboardCommandCenterService(MagicMock()).get_tenant_lifecycle()
    assert result["bookable_tenants"] == 3
    assert result["non_bookable_tenants"] == 0


def _result(value):
    result = MagicMock()
    result.scalars.return_value.first.return_value = value
    result.scalars.return_value.all.return_value = value
    return result


@pytest.mark.asyncio
async def test_legacy_staff_rating_uses_provider_vertical_and_tenant(monkeypatch):
    staff_id, tenant_id = uuid.uuid4(), uuid.uuid4()
    member = SimpleNamespace(id=staff_id, tenant_id=tenant_id)
    summary = SimpleNamespace(to_dict=lambda: {"average_rating": "4.50", "total_reviews": 2})
    db = SimpleNamespace(execute=AsyncMock(side_effect=[_result(member), _result(summary), _result([])]))
    scope = SimpleNamespace(vertical_key="home_services", vertical=SimpleNamespace(id=uuid.uuid4()))

    async def member_tenants(_self, _db, _scope):
        from sqlalchemy import select, literal
        return select(literal(tenant_id).label("id"))

    monkeypatch.setattr(VerticalStaffDirectoryService, "_member_tenant_ids", member_tenants)
    request = SimpleNamespace(state=SimpleNamespace(request_id="test"))
    response = await hs_review_router.staff_review_summary(staff_id, request, db, scope)
    assert response.data["summary"]["average_rating"] == "4.50"
    statements = [str(call.args[0].compile(compile_kwargs={"literal_binds": True})) for call in db.execute.await_args_list]
    assert tenant_id.hex in statements[1] and tenant_id.hex in statements[2]
    assert "provider_team_members.deleted_at IS NULL" in statements[0]


@pytest.mark.asyncio
async def test_staff_rating_still_rejects_cross_vertical_member(monkeypatch):
    async def member_tenants(_self, _db, _scope):
        from sqlalchemy import select, literal
        return select(literal(uuid.uuid4()).label("id"))

    monkeypatch.setattr(VerticalStaffDirectoryService, "_member_tenant_ids", member_tenants)
    db = SimpleNamespace(execute=AsyncMock(return_value=_result(None)))
    scope = SimpleNamespace(vertical_key="home_services", vertical=SimpleNamespace(id=uuid.uuid4()))
    with pytest.raises(ServiceOSException) as exc:
        await hs_review_router.staff_review_summary(
            uuid.uuid4(), SimpleNamespace(state=SimpleNamespace(request_id="test")), db, scope,
        )
    assert exc.value.status_code == 403
    assert db.execute.await_count == 1
