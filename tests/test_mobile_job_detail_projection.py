"""
Technician mobile app Phase J: GET /v1/staff/service-jobs/{job_id}/mobile-detail
+ /mobile-timeline. `_build_workflow_stages` is tested directly (pure,
no DB). Router-level tests exercise the real endpoints against the live
dev DB (same pattern as test_mobile_home_projection.py / test_mobile_jobs_projection.py).
"""
import uuid
from types import SimpleNamespace
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool

from app.main import app
from app.dependencies.auth import get_current_user, UserContext
from app.dependencies.db import get_db
from app.config import get_settings
from app.engines.execution.mobile_job_detail_service import TechnicianJobDetailService

_real_engine = create_async_engine(get_settings().DATABASE_URL, poolclass=NullPool)
_real_sessionmaker = async_sessionmaker(_real_engine, expire_on_commit=False)


async def _override_get_db():
    async with _real_sessionmaker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@pytest.fixture(autouse=True)
def _use_real_db():
    app.dependency_overrides[get_db] = _override_get_db
    yield
    app.dependency_overrides.pop(get_db, None)


def make_technician_context(tenant_id):
    return UserContext(user_id=str(uuid.uuid4()), email="staff@serviceos.local", role="technician",
                        tenant_id=tenant_id, full_name="Demo Staff", is_verified=True)


def make_customer_context():
    return UserContext(user_id=str(uuid.uuid4()), email="customer@serviceos.local", role="customer",
                        tenant_id=None, full_name="Demo Customer", is_verified=True)


def fake_job(status: str):
    return SimpleNamespace(status=status)


class TestBuildWorkflowStages:
    svc = TechnicianJobDetailService()

    def test_repair_sequence_marks_completed_current_and_upcoming_correctly(self):
        stages = self.svc._build_workflow_stages(fake_job("inspection_started"), {"quote_approval_required": True})
        by_key = {s["key"]: s["state"] for s in stages}
        assert by_key["assigned"] == "completed"
        assert by_key["accepted"] == "completed"
        assert by_key["on_the_way"] == "completed"
        assert by_key["reached_site"] == "completed"
        assert by_key["inspection_started"] == "current"
        assert by_key["inspection_done"] == "upcoming"
        assert by_key["completed"] == "upcoming"

    def test_estimate_stage_dropped_when_quote_approval_not_required(self):
        stages = self.svc._build_workflow_stages(fake_job("inspection_started"), {"quote_approval_required": False})
        keys = [s["key"] for s in stages]
        assert "quote_required" not in keys

    def test_estimate_stage_present_when_quote_approval_required(self):
        stages = self.svc._build_workflow_stages(fake_job("assigned"), {"quote_approval_required": True})
        keys = [s["key"] for s in stages]
        assert "quote_required" in keys

    def test_terminal_completed_status_marks_every_stage_completed(self):
        stages = self.svc._build_workflow_stages(fake_job("completed"), {"quote_approval_required": True})
        assert all(s["state"] == "completed" for s in stages)

    def test_unknown_status_never_crashes_and_defaults_stages_to_upcoming(self):
        stages = self.svc._build_workflow_stages(fake_job("some_future_status_not_yet_known"), {"quote_approval_required": True})
        assert all(s["state"] == "upcoming" for s in stages)


@pytest.mark.asyncio
async def test_job_detail_unknown_job_id_fails_closed_with_404():
    tenant_id = str(uuid.uuid4())
    app.dependency_overrides[get_current_user] = lambda: make_technician_context(tenant_id)
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(f"/v1/staff/service-jobs/{uuid.uuid4()}/mobile-detail", headers={"Authorization": "Bearer x"})
        assert response.status_code == 404
        # No existence leak: the error message must not distinguish
        # "doesn't exist" from "exists but belongs to another tenant".
        assert "tenant" not in response.json()["detail"].lower()
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_job_timeline_unknown_job_id_fails_closed_with_404():
    tenant_id = str(uuid.uuid4())
    app.dependency_overrides[get_current_user] = lambda: make_technician_context(tenant_id)
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(f"/v1/staff/service-jobs/{uuid.uuid4()}/mobile-timeline", headers={"Authorization": "Bearer x"})
        assert response.status_code == 404
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_job_detail_denies_customer_role():
    app.dependency_overrides[get_current_user] = make_customer_context
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(f"/v1/staff/service-jobs/{uuid.uuid4()}/mobile-detail", headers={"Authorization": "Bearer x"})
        assert response.status_code == 403
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_job_detail_requires_tenant_context():
    app.dependency_overrides[get_current_user] = lambda: UserContext(
        user_id=str(uuid.uuid4()), email="staff@serviceos.local", role="technician",
        tenant_id=None, full_name="No Tenant", is_verified=True,
    )
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(f"/v1/staff/service-jobs/{uuid.uuid4()}/mobile-detail", headers={"Authorization": "Bearer x"})
        assert response.status_code == 403
    finally:
        app.dependency_overrides.pop(get_current_user, None)
