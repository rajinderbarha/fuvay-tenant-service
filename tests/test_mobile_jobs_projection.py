"""
Technician mobile app Phase I: GET /v1/staff/mobile-jobs.

`_job_views` is the deterministic view-bucketing function -- tested
directly in isolation (spec section 4). Router-level tests exercise the
real endpoint against the live dev DB (same dependency_overrides pattern
established in test_mobile_home_projection.py), since this projection's
value is in composing several real joined tables correctly, which a
mocked session cannot meaningfully verify.
"""
import uuid
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool

from app.main import app
from app.dependencies.auth import get_current_user, UserContext
from app.dependencies.db import get_db
from app.config import get_settings
from app.engines.execution.mobile_jobs_service import _job_views

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


TODAY = "2026-07-31"


class TestJobViews:
    def test_completed_job_is_only_in_completed_view(self):
        assert _job_views("completed", TODAY, TODAY) == {"completed"}

    def test_cancelled_job_is_only_in_archive_view(self):
        assert _job_views("cancelled", TODAY, TODAY) == {"archive"}

    def test_closed_estimate_declined_is_archive_not_completed(self):
        assert _job_views("closed_estimate_declined", None, TODAY) == {"archive"}

    def test_failed_job_is_archive(self):
        assert _job_views("failed", TODAY, TODAY) == {"archive"}

    def test_job_scheduled_today_is_in_today_and_active(self):
        views = _job_views("scheduled", TODAY, TODAY)
        assert "today" in views
        assert "active" in views
        assert "upcoming" not in views

    def test_job_scheduled_in_future_is_only_upcoming(self):
        views = _job_views("scheduled", "2099-01-01", TODAY)
        assert views == {"upcoming"}

    def test_carry_over_active_status_is_today_and_active_even_without_a_scheduled_date(self):
        views = _job_views("inspection_started", None, TODAY)
        assert "today" in views
        assert "active" in views

    def test_carry_over_active_status_with_a_past_scheduled_date_still_shows_today(self):
        views = _job_views("on_the_way", "2026-01-01", TODAY)
        assert "today" in views

    def test_unknown_quote_driven_status_never_becomes_invisible(self):
        views = _job_views("awaiting_customer_quote_approval", None, TODAY)
        assert "active" in views

    def test_assigned_job_with_no_date_defaults_into_active(self):
        assert "active" in _job_views("assigned", None, TODAY)


@pytest.mark.asyncio
async def test_mobile_jobs_returns_full_response_shape():
    tenant_id = str(uuid.uuid4())
    app.dependency_overrides[get_current_user] = lambda: make_technician_context(tenant_id)
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/v1/staff/mobile-jobs?view=today", headers={"Authorization": "Bearer x"})
        assert response.status_code == 200
        data = response.json()["data"]
        for key in ("results", "next_cursor", "has_more", "counts_by_view", "applied_filters", "server_timestamp"):
            assert key in data
        assert set(data["counts_by_view"].keys()) == {"today", "active", "upcoming", "completed", "archive"}
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_mobile_jobs_rejects_unknown_view():
    tenant_id = str(uuid.uuid4())
    app.dependency_overrides[get_current_user] = lambda: make_technician_context(tenant_id)
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/v1/staff/mobile-jobs?view=dispatch_board", headers={"Authorization": "Bearer x"})
        assert response.status_code == 422
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_mobile_jobs_denies_customer_role():
    app.dependency_overrides[get_current_user] = make_customer_context
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/v1/staff/mobile-jobs", headers={"Authorization": "Bearer x"})
        assert response.status_code == 403
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_mobile_jobs_isolated_per_tenant_returns_empty_for_a_fresh_random_tenant():
    """Assignment isolation: a brand-new random tenant_id/user_id combination
    (never assigned any real job) must return zero results, never another
    tenant's or technician's jobs."""
    tenant_id = str(uuid.uuid4())
    app.dependency_overrides[get_current_user] = lambda: make_technician_context(tenant_id)
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/v1/staff/mobile-jobs?view=active", headers={"Authorization": "Bearer x"})
        assert response.status_code == 200
        assert response.json()["data"]["results"] == []
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_mobile_jobs_accepts_search_and_action_required_params_without_error():
    tenant_id = str(uuid.uuid4())
    app.dependency_overrides[get_current_user] = lambda: make_technician_context(tenant_id)
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(
                "/v1/staff/mobile-jobs?view=active&search=HS-&action_required=true&limit=5",
                headers={"Authorization": "Bearer x"},
            )
        assert response.status_code == 200
    finally:
        app.dependency_overrides.pop(get_current_user, None)
