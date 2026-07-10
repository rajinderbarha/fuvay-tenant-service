"""Step 6 manual smoke test — permission gating across new endpoints, run via
pytest so the autouse DB/Redis mocks from conftest.py apply."""
import uuid
from unittest.mock import AsyncMock, patch
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.dependencies.auth import get_current_user, UserContext


@pytest.mark.asyncio
async def test_step6_smoke_flow():
    tenant_id = str(uuid.uuid4())
    job_id = str(uuid.uuid4())
    staff_id = str(uuid.uuid4())

    owner = UserContext(user_id=str(uuid.uuid4()), email="o@x.io", role="tenant_owner",
                         tenant_id=tenant_id, full_name="Owner", is_verified=True)
    staff = UserContext(user_id=staff_id, email="s@x.io", role="staff",
                         tenant_id=tenant_id, full_name="Staff", is_verified=True)
    customer = UserContext(user_id=str(uuid.uuid4()), email="c@x.io", role="customer",
                            tenant_id=None, full_name="Cust", is_verified=True)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        app.dependency_overrides[get_current_user] = lambda: owner
        with patch("app.engines.field_ops.service.FieldOpsService.assign_staff", new=AsyncMock(
                return_value={"job_id": job_id, "status": "assigned", "assigned_staff_id": staff_id,
                              "assigned_staff_name": "Staff", "message": "Job assigned successfully"})):
            r = await client.post(f"/v1/jobs/{job_id}/assign", json={"staff_id": staff_id})
            assert r.status_code == 200, r.text
            assert r.json()["data"]["status"] == "assigned"

        app.dependency_overrides[get_current_user] = lambda: customer
        r = await client.post(f"/v1/jobs/{job_id}/assign", json={"staff_id": staff_id})
        assert r.status_code == 403

        app.dependency_overrides[get_current_user] = lambda: staff
        with patch("app.engines.field_ops.service.FieldOpsService.accept_job", new=AsyncMock(
                return_value={"job_id": job_id, "status": "accepted"})):
            r = await client.post(f"/v1/jobs/{job_id}/accept", json={"notes": "on it"})
            assert r.status_code == 200, r.text
            assert r.json()["data"]["status"] == "accepted"

        app.dependency_overrides[get_current_user] = lambda: owner
        r = await client.post(f"/v1/jobs/{job_id}/accept", json={"notes": "x"})
        assert r.status_code == 403

        app.dependency_overrides[get_current_user] = lambda: customer
        r = await client.put(f"/v1/jobs/{job_id}/status", json={"to_status": "en_route"})
        assert r.status_code == 403

        app.dependency_overrides[get_current_user] = lambda: owner
        r = await client.get("/v1/staff/me/jobs", params={"tenant_id": tenant_id})
        assert r.status_code == 403

        app.dependency_overrides[get_current_user] = lambda: staff
        r = await client.get("/v1/customer/jobs")
        assert r.status_code == 403

    app.dependency_overrides.pop(get_current_user, None)
