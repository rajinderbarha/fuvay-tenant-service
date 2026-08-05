"""Technician mobile app Phase U: GET/PATCH /v1/staff/notification-preferences
+ push-device lifecycle, composed over the canonical NotificationService/
NotificationPreference (already real, already gated at dispatch) plus two
genuinely-new pieces confirmed missing by audit: per-user quiet hours and a
real Expo push-device registration table.
"""
from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import text

from app.main import app
from app.dependencies.auth import get_current_user, UserContext
from app.dependencies.db import get_db
from app.config import get_settings
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool

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


def _tech_ctx(tenant_id, user_id):
    return UserContext(user_id=user_id, email="staff@serviceos.local", role="technician",
                        tenant_id=tenant_id, full_name="Demo Technician", is_verified=True)


@pytest.mark.asyncio
async def test_preferences_denies_customer_role():
    app.dependency_overrides[get_current_user] = lambda: UserContext(
        user_id=str(uuid.uuid4()), email="customer@serviceos.local", role="customer",
        tenant_id=None, full_name="Demo Customer", is_verified=True,
    )
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/v1/staff/notification-preferences", headers={"Authorization": "Bearer x"})
        assert response.status_code == 403
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_preferences_full_lifecycle_live():
    from app.database import get_session_factory, init_db
    from app.engines.auth.models import User

    await init_db()
    factory = get_session_factory()
    async with factory() as db:
        tenant_id = uuid.uuid4()
        user_id = uuid.uuid4()
        user = User(
            id=user_id, email=f"tech-{user_id.hex[:8]}@serviceos.local", phone="9876543210",
            full_name="Demo Technician", role="technician", tenant_id=tenant_id,
            hashed_password="x", is_active=True, is_verified=True, is_mfa_enabled=False,
        )
        db.add(user)
        await db.commit()

        try:
            headers = {"Authorization": "Bearer x"}
            app.dependency_overrides[get_current_user] = lambda: _tech_ctx(str(tenant_id), str(user_id))
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                # 1. Default resolution: everything enabled, mandatory job.assigned locked.
                initial = (await client.get("/v1/staff/notification-preferences", headers=headers)).json()["data"]
                assert initial["delivery"]["in_app"]["configurable"] is False
                assert initial["delivery"]["email_summary"]["supported"] is False  # confirmed no real wiring -- never fabricated
                jobs_event = next(e for e in initial["events"] if e["code"] == "job.assigned")
                assert jobs_event["mandatory"] is True
                assert jobs_event["configurable"] is False
                schedule_event = next(e for e in initial["events"] if e["code"] == "schedule.leave_decision")
                assert schedule_event["mandatory"] is False
                version = initial["version"]

                # 2. Cannot disable the mandatory event -- backend rejects even a forged request.
                forged = await client.patch(
                    "/v1/staff/notification-preferences", headers=headers,
                    json={"code": "job.assigned", "enabled": False, "version": version},
                )
                assert forged.status_code == 422

                # 3. Disable an optional event -- persists.
                disable_resp = await client.patch(
                    "/v1/staff/notification-preferences", headers=headers,
                    json={"code": "schedule.leave_decision", "enabled": False, "version": version},
                )
                assert disable_resp.status_code == 200
                new_version = disable_resp.json()["data"]["version"]
                assert new_version == version + 1
                schedule_event2 = next(e for e in disable_resp.json()["data"]["events"] if e["code"] == "schedule.leave_decision")
                assert schedule_event2["push_enabled"] is False

                # 4. Reusing the stale version fails with a version conflict.
                stale_resp = await client.patch(
                    "/v1/staff/notification-preferences", headers=headers,
                    json={"code": "account.document_reminders", "enabled": False, "version": version},
                )
                assert stale_resp.status_code == 409

                # 5. Unknown preference code rejected.
                unknown_resp = await client.patch(
                    "/v1/staff/notification-preferences", headers=headers,
                    json={"code": "not_a_real_code", "enabled": False, "version": new_version},
                )
                assert unknown_resp.status_code == 422

                # 6. Quiet hours: invalid time rejected, valid overnight window accepted.
                bad_quiet = await client.patch(
                    "/v1/staff/notification-preferences", headers=headers,
                    json={"quiet_hours": {"enabled": True, "start_local_time": "25:99", "end_local_time": "07:00"}, "version": new_version},
                )
                assert bad_quiet.status_code == 422

                good_quiet = await client.patch(
                    "/v1/staff/notification-preferences", headers=headers,
                    json={"quiet_hours": {"enabled": True, "start_local_time": "22:00", "end_local_time": "07:00"}, "version": new_version},
                )
                assert good_quiet.status_code == 200
                assert good_quiet.json()["data"]["quiet_hours"]["enabled"] is True
                assert good_quiet.json()["data"]["quiet_hours"]["start_local_time"] == "22:00"

            # 7. Server-side overnight quiet-hours evaluation is correct.
            from app.engines.home_service_assignment.mobile_notification_preferences_service import MobileNotificationPreferencesService
            import datetime as dt
            db.expire_all()
            fresh_user = await db.get(User, user_id)
            svc = MobileNotificationPreferencesService()
            assert svc.is_within_quiet_hours(fresh_user, now_local=dt.time(23, 30)) is True   # inside overnight window
            assert svc.is_within_quiet_hours(fresh_user, now_local=dt.time(6, 30)) is True    # inside overnight window
            assert svc.is_within_quiet_hours(fresh_user, now_local=dt.time(12, 0)) is False    # outside window
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            await db.execute(text("DELETE FROM notification_preferences WHERE user_id=:uid"), {"uid": user_id})
            await db.execute(text("DELETE FROM staff_push_devices WHERE user_id=:uid"), {"uid": user_id})
            await db.execute(text("DELETE FROM users WHERE id=:uid"), {"uid": user_id})
            await db.commit()


@pytest.mark.asyncio
async def test_push_device_lifecycle_and_cross_user_isolation():
    from app.database import get_session_factory, init_db
    from app.engines.auth.models import User

    await init_db()
    factory = get_session_factory()
    async with factory() as db:
        tenant_id = uuid.uuid4()
        user_a = uuid.uuid4()
        user_b = uuid.uuid4()
        db.add(User(id=user_a, email=f"a-{user_a.hex[:8]}@serviceos.local", phone="9000000001", full_name="Tech A",
                     role="technician", tenant_id=tenant_id, hashed_password="x", is_active=True, is_verified=True, is_mfa_enabled=False))
        db.add(User(id=user_b, email=f"b-{user_b.hex[:8]}@serviceos.local", phone="9000000002", full_name="Tech B",
                     role="technician", tenant_id=tenant_id, hashed_password="x", is_active=True, is_verified=True, is_mfa_enabled=False))
        await db.commit()

        shared_token = f"ExponentPushToken[{uuid.uuid4().hex[:12]}]"
        try:
            headers = {"Authorization": "Bearer x"}
            # 1. User A registers a device.
            app.dependency_overrides[get_current_user] = lambda: _tech_ctx(str(tenant_id), str(user_a))
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                reg1 = await client.post("/v1/staff/push-devices", headers=headers, json={"device_id": "device-1", "expo_push_token": shared_token, "platform": "android"})
                assert reg1.status_code == 200

            active_a = (await db.execute(text(
                "SELECT count(*) FROM staff_push_devices WHERE user_id=:uid AND revoked_at IS NULL"
            ), {"uid": user_a})).scalar()
            assert active_a == 1

            # 2. User B registers the SAME physical token (device handed off) -- must not leak to A.
            app.dependency_overrides[get_current_user] = lambda: _tech_ctx(str(tenant_id), str(user_b))
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                reg2 = await client.post("/v1/staff/push-devices", headers=headers, json={"device_id": "device-1", "expo_push_token": shared_token, "platform": "android"})
                assert reg2.status_code == 200

            a_still_active = (await db.execute(text(
                "SELECT revoked_at FROM staff_push_devices WHERE user_id=:uid AND device_id='device-1'"
            ), {"uid": user_a})).scalar()
            assert a_still_active is not None  # user A's binding on that token was revoked once B claimed it

            # 3. Revoking the current device for user B.
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                revoke_resp = await client.request("DELETE", "/v1/staff/push-devices/current", headers=headers, json={"device_id": "device-1"})
                assert revoke_resp.status_code == 200
                assert revoke_resp.json()["data"]["revoked"] is True

            b_revoked = (await db.execute(text(
                "SELECT revoked_at FROM staff_push_devices WHERE user_id=:uid AND device_id='device-1'"
            ), {"uid": user_b})).scalar()
            assert b_revoked is not None
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            await db.execute(text("DELETE FROM staff_push_devices WHERE user_id IN (:a, :b)"), {"a": user_a, "b": user_b})
            await db.execute(text("DELETE FROM users WHERE id IN (:a, :b)"), {"a": user_a, "b": user_b})
            await db.commit()
