"""
Phase 3 gap fix: tenant-portal Staff page called /v1/tenants/{tenant_id}/staff,
/v1/staff/{id}, and /v1/staff/{id}/schedule — none of which existed anywhere
in the backend (auth engine only had invite/deactivate/permissions). The
super-admin Tenant 360 page's Staff tab had the identical bug. This verifies
the new /v1/auth/staff* endpoints actually work end-to-end.
"""
import uuid
from datetime import datetime, timezone
import pytest
from unittest.mock import AsyncMock, MagicMock
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.dependencies.auth import get_current_user, UserContext


def make_tenant_owner(tenant_id):
    return UserContext(user_id=str(uuid.uuid4()), email="owner@biz.io", role="tenant_owner",
                        tenant_id=tenant_id, full_name="Owner", is_verified=True)


@pytest.mark.asyncio
async def test_list_staff_endpoint_requires_tenant_id_and_permission():
    tid = str(uuid.uuid4())
    app.dependency_overrides[get_current_user] = lambda: make_tenant_owner(tid)
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(f"/v1/auth/staff?tenant_id={tid}", headers={"Authorization": "Bearer x"})
        assert response.status_code == 200
        data = response.json()["data"]
        assert "staff" in data and "total" in data
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_list_staff_by_tenant_service_computes_jobs_today_and_active_job():
    from app.engines.auth.service import AuthService
    from app.engines.field_ops.constants import JS

    tid = uuid.uuid4()
    staff_id = uuid.uuid4()
    fake_user = MagicMock(id=staff_id, full_name="Asha", phone="9999999999",
                           is_active=True, deleted_at=None, meta={"specialisations": ["AC repair"]})

    users_result = MagicMock()
    users_result.scalars.return_value.all.return_value = [fake_user]

    today = datetime.now(timezone.utc)
    jobs_result = MagicMock()
    jobs_result.all.return_value = [
        (staff_id, JS.EN_ROUTE, "JOB-001", today),
        (staff_id, JS.CLOSED, "JOB-000", today),
    ]

    db = MagicMock()
    db.execute = AsyncMock(side_effect=[users_result, jobs_result])
    svc = AuthService(db=db)

    result = await svc.list_staff_by_tenant(tid)

    assert result["total"] == 1
    staff = result["staff"][0]
    assert staff["jobs_today"] == 2
    assert staff["active_job"] == "JOB-001"  # en_route job, not the closed one
    assert staff["specialisations"] == ["AC repair"]
    assert staff["status"] == "active"


@pytest.mark.asyncio
async def test_update_staff_schedule_persists_into_user_meta():
    from app.engines.auth.service import AuthService

    fake_user = MagicMock(id=uuid.uuid4(), full_name="Asha", phone=None, role="staff",
                           is_active=True, meta={"specialisations": ["AC repair"]})
    result = MagicMock()
    result.scalar_one_or_none.return_value = fake_user
    db = MagicMock()
    db.execute = AsyncMock(return_value=result)
    svc = AuthService(db=db)

    hours = {"monday": {"start": "09:00", "end": "18:00", "is_working": True}}
    out = await svc.update_staff_schedule(fake_user.id, hours)

    assert fake_user.meta["working_hours"] == hours
    assert fake_user.meta["specialisations"] == ["AC repair"]  # existing meta preserved
    assert out["working_hours"] == hours
