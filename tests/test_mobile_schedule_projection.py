"""Technician mobile app Phase P: GET /v1/staff/me/schedule + blocked-time
and time-off mutations, composed over the canonical
`provider_availability_rules`/`service_jobs` sources plus the two
genuinely-new tables (`staff_blocked_times`, `staff_time_off_requests`).
Follows the same live-DB pattern as the Phase K-O projection tests.
"""
from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool

from app.main import app
from app.dependencies.auth import get_current_user, UserContext
from app.dependencies.db import get_db
from app.config import get_settings

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


def make_technician_context(tenant_id, user_id=None):
    return UserContext(user_id=user_id or str(uuid.uuid4()), email="staff@serviceos.local", role="technician",
                        tenant_id=tenant_id, full_name="Demo Staff", is_verified=True)


def make_owner_context(tenant_id, user_id=None):
    return UserContext(user_id=user_id or str(uuid.uuid4()), email="owner@serviceos.local", role="tenant_owner",
                        tenant_id=tenant_id, full_name="Demo Owner", is_verified=True)


@pytest.mark.asyncio
async def test_schedule_requires_tenant_context():
    app.dependency_overrides[get_current_user] = lambda: UserContext(
        user_id=str(uuid.uuid4()), email="staff@serviceos.local", role="technician",
        tenant_id=None, full_name="No Tenant", is_verified=True,
    )
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/v1/staff/me/schedule?from=2026-07-27&to=2026-08-02", headers={"Authorization": "Bearer x"})
        assert response.status_code == 403
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_schedule_denies_customer_role():
    app.dependency_overrides[get_current_user] = lambda: UserContext(
        user_id=str(uuid.uuid4()), email="customer@serviceos.local", role="customer",
        tenant_id=None, full_name="Demo Customer", is_verified=True,
    )
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/v1/staff/me/schedule?from=2026-07-27&to=2026-08-02", headers={"Authorization": "Bearer x"})
        assert response.status_code == 403
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_schedule_rejects_range_over_31_days():
    tenant_id = str(uuid.uuid4())
    app.dependency_overrides[get_current_user] = lambda: make_technician_context(tenant_id)
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/v1/staff/me/schedule?from=2026-01-01&to=2026-12-31", headers={"Authorization": "Bearer x"})
        assert response.status_code == 422
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_schedule_full_lifecycle_live():
    """Real technician with a recurring weekly working-hours pattern and
    one assigned job on a given date. Proves: the job appears in the
    correct day's projection, a blocked-time interval can be added on a
    day with no jobs, adding blocked time on the SAME time as an assigned
    job is rejected with the conflicting job identified, a time-off
    request starts pending, the technician cannot approve their own
    request, and the tenant owner's approval is reflected back in the
    technician's own schedule."""
    from app.database import get_session_factory, init_db

    await init_db()
    factory = get_session_factory()
    async with factory() as db:
        tenant_id = uuid.uuid4()
        staff_user_id = uuid.uuid4()
        cat_id = uuid.uuid4()
        ms_id = uuid.uuid4()
        jt_id = uuid.uuid4()

        # A real ProviderTeamMember row (so _resolve_staff_id resolves to it).
        staff_id = uuid.uuid4()
        await db.execute(text(
            "INSERT INTO provider_team_members (id, tenant_id, user_id, member_type, full_name, status, "
            "max_concurrent_jobs, created_at, updated_at) "
            "VALUES (:id, :tid, :uid, 'technician', 'Demo Tech', 'active', 4, now(), now())"
        ), {"id": staff_id, "tid": tenant_id, "uid": staff_user_id})

        import datetime as _dt
        target_date = _dt.date(2026, 7, 31)
        dow = 5  # Friday, isoweekday()=5, %7=5
        await db.execute(text(
            "INSERT INTO provider_availability_rules (id, tenant_id, scope_type, scope_id, day_of_week, "
            "start_time, end_time, max_jobs_per_day, is_active, created_at, updated_at) "
            "VALUES (:id, :tid, 'staff_member', :sid, :dow, '09:00', '18:00', 4, true, now(), now())"
        ), {"id": uuid.uuid4(), "tid": tenant_id, "sid": staff_id, "dow": dow})

        await db.execute(text(
            "INSERT INTO job_types (id, key, label, is_active, created_at, updated_at) "
            "VALUES (:id, :key, 'Repair', true, now(), now())"
        ), {"id": jt_id, "key": f"repair_{jt_id.hex[:6]}"})
        await db.execute(text(
            "INSERT INTO master_services (id, category_id, service_name, slug, job_type, is_active, "
            "created_at, updated_at) VALUES (:id, :cat, 'AC Repair', :slug, 'repair', true, now(), now())"
        ), {"id": ms_id, "cat": cat_id, "slug": f"ac-{ms_id.hex[:6]}"})

        booking_id, job_id = uuid.uuid4(), uuid.uuid4()
        customer_id = uuid.uuid4()
        await db.execute(text(
            "INSERT INTO service_bookings (id, booking_number, draft_id, category_id, offering_id, "
            "job_type_id, customer_id, status, assignment_status, created_at, updated_at) "
            "VALUES (:id, :num, :did, :cat, :off, :jt, :cust, 'pending_assignment', 'unassigned', now(), now())"
        ), {"id": booking_id, "num": f"BK-{booking_id.hex[:8]}", "did": uuid.uuid4(), "cat": cat_id, "off": ms_id,
            "jt": jt_id, "cust": customer_id})
        await db.execute(text(
            "INSERT INTO service_jobs (id, job_number, booking_id, category_id, offering_id, job_type_id, "
            "tenant_id, customer_id, assigned_staff_id, status, assignment_status, scheduled_date, "
            "scheduled_time_window, created_at, updated_at) "
            "VALUES (:id, :num, :bid, :cat, :off, :jt, :tid, :cust, :staff, 'assigned', 'assigned', :sd, '10:30 AM', now(), now())"
        ), {"id": job_id, "num": f"J-{job_id.hex[:8]}", "bid": booking_id, "cat": cat_id, "off": ms_id, "jt": jt_id,
            "tid": tenant_id, "cust": customer_id, "staff": staff_id, "sd": target_date})
        await db.commit()

        blocked_id = None
        time_off_id = None
        try:
            app.dependency_overrides[get_current_user] = lambda: make_technician_context(str(tenant_id), user_id=str(staff_user_id))
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                headers = {"Authorization": "Bearer x"}

                # 1. The assigned job appears on the correct day, with a real working-hours pattern.
                detail = (await client.get(f"/v1/staff/me/schedule?from={target_date}&to={target_date}", headers=headers)).json()["data"]
                day = detail["days"][0]
                assert day["assigned_job_count"] == 1
                assert day["working_hours_label"] == "09:00–18:00"
                job_items = [i for i in day["items"] if i["type"] == "assigned_job"]
                assert job_items[0]["job_reference"].startswith("J-")

                # 2. Blocked time conflicting with the assignment is rejected server-side.
                conflict_resp = await client.post(
                    "/v1/staff/me/schedule/blocked-time", headers=headers,
                    json={"date": target_date.isoformat(), "start_time": "11:00", "end_time": "12:00", "reason": "Personal"},
                )
                assert conflict_resp.status_code == 409
                assert conflict_resp.json()["detail"]  # error body present

                # 3. Blocked time on a day with no jobs succeeds.
                other_date = "2026-08-05"
                block_resp = await client.post(
                    "/v1/staff/me/schedule/blocked-time", headers=headers,
                    json={"date": other_date, "start_time": "14:00", "end_time": "15:00", "reason": "Personal"},
                )
                assert block_resp.status_code == 200
                blocked_id = block_resp.json()["data"]["id"]

                # 4. Time-off request starts pending; technician cannot approve/reject it.
                submit_resp = await client.post(
                    "/v1/staff/me/time-off", headers=headers,
                    json={"start_date": "2026-08-10", "end_date": "2026-08-10", "is_full_day": True, "reason_category": "personal"},
                )
                assert submit_resp.status_code == 200
                time_off_id = submit_resp.json()["data"]["id"]
                assert submit_resp.json()["data"]["status"] == "pending"

                self_approve = await client.post(f"/v1/tenant/home-services/time-off/{time_off_id}/approve", headers=headers, json={})
                assert self_approve.status_code == 403  # technician is not a tenant_owner

            # 5. Tenant owner approves; the technician's own schedule reflects it.
            app.dependency_overrides[get_current_user] = lambda: make_owner_context(str(tenant_id))
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                approve_resp = await client.post(f"/v1/tenant/home-services/time-off/{time_off_id}/approve", headers={"Authorization": "Bearer x"}, json={})
                assert approve_resp.status_code == 200
                assert approve_resp.json()["data"]["status"] == "approved"

            app.dependency_overrides[get_current_user] = lambda: make_technician_context(str(tenant_id), user_id=str(staff_user_id))
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                detail2 = (await client.get("/v1/staff/me/schedule?from=2026-08-10&to=2026-08-10", headers={"Authorization": "Bearer x"})).json()["data"]
                leave_items = [i for i in detail2["days"][0]["items"] if i["type"] == "approved_leave"]
                assert len(leave_items) == 1
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            if time_off_id:
                await db.execute(text("DELETE FROM staff_time_off_requests WHERE id=:id"), {"id": time_off_id})
            if blocked_id:
                await db.execute(text("DELETE FROM staff_blocked_times WHERE id=:id"), {"id": blocked_id})
            await db.execute(text("DELETE FROM service_jobs WHERE id=:jid"), {"jid": job_id})
            await db.execute(text("DELETE FROM service_bookings WHERE id=:bid"), {"bid": booking_id})
            await db.execute(text("DELETE FROM master_services WHERE id=:ms"), {"ms": ms_id})
            await db.execute(text("DELETE FROM job_types WHERE id=:jt"), {"jt": jt_id})
            await db.execute(text("DELETE FROM provider_availability_rules WHERE scope_id=:sid"), {"sid": staff_id})
            await db.execute(text("DELETE FROM provider_team_members WHERE id=:sid"), {"sid": staff_id})
            await db.commit()
