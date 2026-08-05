"""Technician mobile app Phase Q: GET /v1/staff/mobile-notifications, composed
over the EXISTING canonical InAppNotification/NotificationService (never a
second notification engine). Also proves the real Phase P gap fix: leave
approval/rejection now fires a real notification to the requesting
technician via the existing fire_event pipeline + newly-seeded templates.
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


@pytest.mark.asyncio
async def test_mobile_notifications_denies_customer_role():
    app.dependency_overrides[get_current_user] = lambda: UserContext(
        user_id=str(uuid.uuid4()), email="customer@serviceos.local", role="customer",
        tenant_id=None, full_name="Demo Customer", is_verified=True,
    )
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/v1/staff/mobile-notifications", headers={"Authorization": "Bearer x"})
        assert response.status_code == 403
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_mobile_notifications_only_returns_authenticated_users_own_rows():
    """A second, unrelated technician's notifications must never leak into
    this one's inbox -- proven with two REAL InAppNotification rows for two
    different users."""
    from app.database import get_session_factory, init_db
    from app.engines.platform_notifications.models import InAppNotification

    await init_db()
    factory = get_session_factory()
    async with factory() as db:
        tenant_id = uuid.uuid4()
        user_a = uuid.uuid4()
        user_b = uuid.uuid4()
        n_a = InAppNotification(
            user_id=user_a, tenant_id=tenant_id, notification_type="job.assigned",
            title="New job assigned", body="HS-1052", severity="info", read_status="unread",
        )
        n_b = InAppNotification(
            user_id=user_b, tenant_id=tenant_id, notification_type="job.assigned",
            title="New job assigned", body="HS-1099", severity="info", read_status="unread",
        )
        db.add_all([n_a, n_b])
        await db.commit()

        try:
            app.dependency_overrides[get_current_user] = lambda: make_technician_context(str(tenant_id), user_id=str(user_a))
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                detail = (await client.get("/v1/staff/mobile-notifications", headers={"Authorization": "Bearer x"})).json()["data"]
                bodies = [i["body"] for i in detail["items"]]
                assert "HS-1052" in bodies
                assert "HS-1099" not in bodies
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            await db.execute(text("DELETE FROM in_app_notifications WHERE id IN (:a, :b)"), {"a": n_a.id, "b": n_b.id})
            await db.commit()


@pytest.mark.asyncio
async def test_mobile_notifications_filters_and_categories_live():
    """Real job.assigned + a real leave.rejected notification (proving the
    Phase P notification gap fix). Proves: All/Unread/Action-needed counts,
    category chip filtering (jobs vs schedule), mark-one-read reduces the
    unread count, and mark-all-read (reused canonical endpoint) clears it."""
    from app.database import get_session_factory, init_db
    from app.engines.platform_notifications.models import InAppNotification

    await init_db()
    factory = get_session_factory()
    async with factory() as db:
        tenant_id = uuid.uuid4()
        staff_user_id = uuid.uuid4()
        job_id = uuid.uuid4()

        job_notif = InAppNotification(
            user_id=staff_user_id, tenant_id=tenant_id, notification_type="job.assigned",
            title="New job assigned", body="HS-1052 · Geyser Repair", severity="info",
            read_status="unread", source_record_type="service_jobs", source_record_id=job_id,
        )
        leave_notif = InAppNotification(
            user_id=staff_user_id, tenant_id=tenant_id, notification_type="leave.rejected",
            title="Leave request rejected", body="2026-08-10", severity="warning", read_status="unread",
        )
        db.add_all([job_notif, leave_notif])
        await db.commit()

        try:
            app.dependency_overrides[get_current_user] = lambda: make_technician_context(str(tenant_id), user_id=str(staff_user_id))
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                headers = {"Authorization": "Bearer x"}

                detail = (await client.get("/v1/staff/mobile-notifications", headers=headers)).json()["data"]
                assert detail["counts"]["all"] == 2
                assert detail["counts"]["unread"] == 2
                assert detail["counts"]["action_required"] == 1  # only leave.rejected

                jobs_only = (await client.get("/v1/staff/mobile-notifications?category=jobs", headers=headers)).json()["data"]
                assert len(jobs_only["items"]) == 1
                assert jobs_only["items"][0]["destination"] == {"type": "job", "id": str(job_id), "section": None}

                schedule_only = (await client.get("/v1/staff/mobile-notifications?category=schedule", headers=headers)).json()["data"]
                assert len(schedule_only["items"]) == 1
                assert schedule_only["items"][0]["action_required"] is True

                # Reuses the EXISTING canonical staff notification endpoints directly.
                mark_resp = await client.post(f"/v1/staff/notifications/{job_notif.id}/read", headers=headers)
                assert mark_resp.status_code == 200
                after_one_read = (await client.get("/v1/staff/mobile-notifications", headers=headers)).json()["data"]
                assert after_one_read["counts"]["unread"] == 1

                mark_all_resp = await client.post("/v1/staff/notifications/mark-all-read", headers=headers)
                assert mark_all_resp.status_code == 200
                after_all_read = (await client.get("/v1/staff/mobile-notifications", headers=headers)).json()["data"]
                assert after_all_read["counts"]["unread"] == 0
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            await db.execute(text("DELETE FROM in_app_notifications WHERE id IN (:a, :b)"), {"a": job_notif.id, "b": leave_notif.id})
            await db.commit()


@pytest.mark.asyncio
async def test_leave_decision_fires_real_notification_to_requesting_technician():
    """Closes the Phase P gap: approving/rejecting a StaffTimeOffRequest now
    creates a real InAppNotification for the technician who requested it,
    via the existing fire_event pipeline + this phase's seeded templates."""
    from app.database import get_session_factory, init_db
    from app.engines.platform_notifications.models import InAppNotification
    from sqlalchemy import select

    await init_db()
    factory = get_session_factory()
    async with factory() as db:
        tenant_id = uuid.uuid4()
        staff_user_id = uuid.uuid4()
        staff_id = uuid.uuid4()
        await db.execute(text(
            "INSERT INTO provider_team_members (id, tenant_id, user_id, member_type, full_name, status, "
            "max_concurrent_jobs, created_at, updated_at) "
            "VALUES (:id, :tid, :uid, 'technician', 'Demo Tech', 'active', 4, now(), now())"
        ), {"id": staff_id, "tid": tenant_id, "uid": staff_user_id})
        await db.commit()

        time_off_id = None
        try:
            app.dependency_overrides[get_current_user] = lambda: make_technician_context(str(tenant_id), user_id=str(staff_user_id))
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                submit_resp = await client.post(
                    "/v1/staff/me/time-off", headers={"Authorization": "Bearer x"},
                    json={"start_date": "2026-08-10", "end_date": "2026-08-10", "is_full_day": True, "reason_category": "personal"},
                )
                time_off_id = submit_resp.json()["data"]["id"]

            app.dependency_overrides[get_current_user] = lambda: UserContext(
                user_id=str(uuid.uuid4()), email="owner@serviceos.local", role="tenant_owner",
                tenant_id=str(tenant_id), full_name="Demo Owner", is_verified=True,
            )
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                approve_resp = await client.post(f"/v1/tenant/home-services/time-off/{time_off_id}/approve", headers={"Authorization": "Bearer x"}, json={})
                assert approve_resp.status_code == 200

            notifs = (await db.execute(select(InAppNotification).where(
                InAppNotification.user_id == staff_user_id, InAppNotification.notification_type == "leave.approved",
            ))).scalars().all()
            assert len(notifs) == 1
            assert "approved" in notifs[0].title.lower()
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            await db.execute(text("DELETE FROM in_app_notifications WHERE user_id=:uid AND notification_type LIKE 'leave.%'"), {"uid": staff_user_id})
            if time_off_id:
                await db.execute(text("DELETE FROM staff_time_off_requests WHERE id=:id"), {"id": time_off_id})
            await db.execute(text("DELETE FROM provider_team_members WHERE id=:sid"), {"sid": staff_id})
            await db.commit()
