"""
Technician mobile app Phase H: GET /v1/staff/mobile-home + PUT /v1/staff/me/availability.

`_select_current_job` is the deterministic priority function (spec section
5) -- tested directly, in isolation, with fixture job rows (no DB needed).
The router-level tests exercise the real endpoints against the live dev DB
(dependency_overrides only for auth, matching tests/test_staff_roster.py and
tests/test_mfa_trusted_device.py's existing pattern).
"""
import uuid
from datetime import date
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool

from app.main import app
from app.dependencies.auth import get_current_user, UserContext
from app.dependencies.db import get_db
from app.config import get_settings
from app.engines.execution.mobile_home_service import _select_current_job

# tests/conftest.py's autouse `mock_database` fixture monkeypatches
# app.database._async_session_factory to an AsyncMock for every test (so
# unit tests that only mock specific service methods never touch a real
# connection). This module's tests exercise the real router+service+DB
# stack end to end, so they need a REAL session -- built independently of
# app.database's (patched) module state and wired in via dependency_overrides,
# which always wins over whatever get_db's internals would otherwise return.
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


def job(id_="j1", status="assigned", scheduled_date=None, scheduled_time_window=None, updated_at=None):
    return {
        "id": id_, "job_number": f"HS-{id_}", "status": status,
        "scheduled_date": scheduled_date, "scheduled_time_window": scheduled_time_window,
        "updated_at": updated_at, "city": "Model Town", "zipcode": "141001",
    }


class TestSelectCurrentJob:
    def test_active_execution_job_wins_over_everything_else(self):
        jobs = [
            job("scheduled_today", status="scheduled", scheduled_date="2026-07-31", scheduled_time_window="09:00"),
            job("active", status="inspection_started", updated_at="2026-07-31T10:00:00Z"),
            job("assigned_pending", status="assigned"),
        ]
        assert _select_current_job(jobs)["id"] == "active"

    def test_most_recently_updated_active_job_wins_among_multiple_active(self):
        jobs = [
            job("older", status="on_the_way", updated_at="2026-07-31T08:00:00Z"),
            job("newer", status="service_started", updated_at="2026-07-31T10:00:00Z"),
        ]
        assert _select_current_job(jobs)["id"] == "newer"

    def test_immediate_action_job_wins_over_scheduled_today_when_no_active_job(self):
        jobs = [
            job("scheduled_today", status="scheduled", scheduled_date="2026-07-31", scheduled_time_window="09:00"),
            job("needs_accept", status="assigned", scheduled_date="2026-07-31"),
        ]
        assert _select_current_job(jobs)["id"] == "needs_accept"

    def test_earliest_scheduled_today_job_when_no_active_or_immediate_action_job(self):
        today = date.today().isoformat()
        jobs = [
            job("later", status="scheduled", scheduled_date=today, scheduled_time_window="15:00"),
            job("earlier", status="scheduled", scheduled_date=today, scheduled_time_window="09:00"),
        ]
        assert _select_current_job(jobs)["id"] == "earlier"

    def test_none_when_no_active_immediate_or_scheduled_today_job(self):
        jobs = [job("future", status="scheduled", scheduled_date="2099-01-01")]
        assert _select_current_job(jobs) is None

    def test_none_for_an_all_terminal_job_list(self):
        jobs = [job("done", status="completed"), job("gone", status="cancelled")]
        assert _select_current_job(jobs) is None

    def test_cancelled_and_completed_jobs_never_selected_as_current(self):
        today = date.today().isoformat()
        jobs = [
            job("cancelled", status="cancelled", scheduled_date=today, scheduled_time_window="08:00"),
            job("completed", status="completed", scheduled_date=today, scheduled_time_window="07:00"),
            job("real", status="scheduled", scheduled_date=today, scheduled_time_window="09:00"),
        ]
        assert _select_current_job(jobs)["id"] == "real"

    def test_empty_job_list_returns_none(self):
        assert _select_current_job([]) is None


def make_technician_context(tenant_id, user_id=None):
    return UserContext(
        user_id=user_id or str(uuid.uuid4()), email="staff@serviceos.local", role="technician",
        tenant_id=tenant_id, full_name="Demo Staff", is_verified=True,
    )


def make_customer_context():
    return UserContext(
        user_id=str(uuid.uuid4()), email="customer@serviceos.local", role="customer",
        tenant_id=None, full_name="Demo Customer", is_verified=True,
    )


@pytest.mark.asyncio
async def test_mobile_home_returns_full_projection_shape_for_a_real_technician():
    tenant_id = str(uuid.uuid4())
    app.dependency_overrides[get_current_user] = lambda: make_technician_context(tenant_id)
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/v1/staff/mobile-home", headers={"Authorization": "Bearer x"})
        assert response.status_code == 200
        data = response.json()["data"]
        for key in ("technician", "availability", "shift_summary", "current_job",
                    "today_schedule", "action_required", "unread_notification_count", "server_timestamp"):
            assert key in data
        assert data["shift_summary"]["jobs_today"] >= 0
        assert data["current_job"] is None or "job_id" in data["current_job"]
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_mobile_home_denies_customer_role():
    app.dependency_overrides[get_current_user] = make_customer_context
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/v1/staff/mobile-home", headers={"Authorization": "Bearer x"})
        assert response.status_code == 403
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_update_availability_rejects_unknown_state():
    tenant_id = str(uuid.uuid4())
    app.dependency_overrides[get_current_user] = lambda: make_technician_context(tenant_id)
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.put("/v1/staff/me/availability", json={"state": "on_vacation"}, headers={"Authorization": "Bearer x"})
        assert response.status_code == 422
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_update_availability_denies_customer_role():
    app.dependency_overrides[get_current_user] = make_customer_context
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.put("/v1/staff/me/availability", json={"state": "busy"}, headers={"Authorization": "Bearer x"})
        assert response.status_code == 403
    finally:
        app.dependency_overrides.pop(get_current_user, None)
