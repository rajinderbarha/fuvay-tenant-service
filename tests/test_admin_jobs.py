"""
Phase 2 gap fix: Super Admin had no cross-tenant job queue endpoint.
GET /v1/jobs returned data for exactly one tenant_id (required query param);
there was no platform-wide view. This verifies the new admin endpoint exists,
is super-admin gated, and aggregates across tenants.
"""
import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.dependencies.auth import get_current_user, UserContext


def make_super_admin():
    return UserContext(user_id=str(uuid.uuid4()), email="admin@serviceos.io", role="super_admin",
                        tenant_id=None, full_name="Admin", is_verified=True)


def make_tenant_owner():
    return UserContext(user_id=str(uuid.uuid4()), email="owner@biz.io", role="tenant_owner",
                        tenant_id=str(uuid.uuid4()), full_name="Owner", is_verified=True)


@pytest.mark.asyncio
async def test_admin_jobs_endpoint_rejects_non_super_admin():
    app.dependency_overrides[get_current_user] = lambda: make_tenant_owner()
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/v1/jobs/admin/all", headers={"Authorization": "Bearer x"})
        assert response.status_code == 403
        assert response.json()["error_code"] == "PERMISSION_DENIED"
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_admin_jobs_endpoint_allows_super_admin_and_calls_service():
    app.dependency_overrides[get_current_user] = lambda: make_super_admin()
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/v1/jobs/admin/all", headers={"Authorization": "Bearer x"})
        assert response.status_code == 200
        data = response.json()["data"]
        assert "jobs" in data and "has_next" in data
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_list_jobs_admin_service_aggregates_across_tenants():
    from app.engines.field_ops.service import FieldOpsService

    job_a = MagicMock(id=uuid.uuid4(), job_number="JOB-1", tenant_id=uuid.uuid4(), status="assigned",
                       title="t", description=None, service_type_id=None, service_category=None,
                       assigned_staff_id=None, customer_id=None, address=None, pincode=None,
                       scheduled_at=None, started_at=None, completed_at=None, quoted_price=None,
                       final_price=None, commission_deducted=False, commission_amount=None,
                       sla_breach=False, customer_rating=None, tags=None, created_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc))
    job_b = MagicMock(**{k: v for k, v in vars(job_a).items() if not k.startswith("_")})
    job_b.tenant_id = uuid.uuid4()
    job_b.job_number = "JOB-2"

    mock_result = MagicMock()
    # list_jobs_admin now returns 4-tuples: (job, tenant_name, customer_name, staff_name)
    mock_result.all.return_value = [
        (job_a, "Tenant A", "Alice Smith", None),
        (job_b, "Tenant B", "Bob Jones", "Staff X"),
    ]
    db = MagicMock()
    db.execute = AsyncMock(return_value=mock_result)

    svc = FieldOpsService(db=db, actor_id=uuid.uuid4(), actor_role="super_admin")
    result = await svc.list_jobs_admin(tenant_id=None, status=None, limit=50, cursor=None)

    tenant_names = {j["tenant_name"] for j in result["jobs"]}
    assert tenant_names == {"Tenant A", "Tenant B"}
    customer_names = {j["customer_name"] for j in result["jobs"]}
    assert "Alice Smith" in customer_names


@pytest.mark.asyncio
async def test_admin_summary_endpoint():
    app.dependency_overrides[get_current_user] = lambda: make_super_admin()
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/v1/jobs/admin/summary", headers={"Authorization": "Bearer x"})
        assert response.status_code == 200
        data = response.json()["data"]
        for key in ("total_active", "in_progress", "sla_breached", "unassigned",
                    "rework_required", "completed_today"):
            assert key in data, f"Missing key: {key}"
    finally:
        app.dependency_overrides.pop(get_current_user, None)
