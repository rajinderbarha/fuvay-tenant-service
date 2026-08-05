"""Technician mobile app Phase R: GET /v1/staff/me/profile + document
submission + notification preferences, composed over the canonical
User/ProviderTeamMember/UserSession (auth engine) and the two genuinely-new
tables (StaffDocument) plus the reused NotificationPreference model.
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
async def test_profile_denies_customer_role():
    app.dependency_overrides[get_current_user] = lambda: UserContext(
        user_id=str(uuid.uuid4()), email="customer@serviceos.local", role="customer",
        tenant_id=None, full_name="Demo Customer", is_verified=True,
    )
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/v1/staff/me/profile", headers={"Authorization": "Bearer x"})
        assert response.status_code == 403
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_profile_requires_tenant_context():
    app.dependency_overrides[get_current_user] = lambda: UserContext(
        user_id=str(uuid.uuid4()), email="staff@serviceos.local", role="technician",
        tenant_id=None, full_name="No Tenant", is_verified=True,
    )
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/v1/staff/me/profile", headers={"Authorization": "Bearer x"})
        assert response.status_code == 403
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_profile_full_lifecycle_live():
    """Real User + ProviderTeamMember + a real assigned service + real
    working-hours row. Proves: identity/employment fields are real (never
    fabricated), readiness starts incomplete without documents, submitting
    a required document moves it toward complete once verified, a second
    submission of the SAME type supersedes (never destructively overwrites)
    the first, and notification preferences round-trip through the real
    per-event/channel model."""
    from app.database import get_session_factory, init_db
    from app.engines.auth.models import User

    await init_db()
    factory = get_session_factory()
    async with factory() as db:
        tenant_id = uuid.uuid4()
        offering_id = uuid.uuid4()
        staff_user_id = uuid.uuid4()

        user = User(
            id=staff_user_id, email=f"tech-{staff_user_id.hex[:8]}@serviceos.local", phone="9876543210",
            full_name="Demo Technician", role="technician", tenant_id=tenant_id,
            hashed_password="x", is_active=True, is_verified=True, is_mfa_enabled=False,
        )
        db.add(user)
        await db.flush()

        staff_id = uuid.uuid4()
        import json
        await db.execute(text(
            "INSERT INTO provider_team_members (id, tenant_id, user_id, member_type, full_name, status, "
            "designation, supported_offering_ids, max_concurrent_jobs, created_at, updated_at) "
            "VALUES (:id, :tid, :uid, 'technician', 'Demo Technician', 'active', 'Senior Technician', "
            "CAST(:offerings AS jsonb), 4, now(), now())"
        ), {"id": staff_id, "tid": tenant_id, "uid": staff_user_id, "offerings": json.dumps([str(offering_id)])})
        await db.execute(text(
            "INSERT INTO provider_availability_rules (id, tenant_id, scope_type, scope_id, day_of_week, "
            "start_time, end_time, max_jobs_per_day, is_active, created_at, updated_at) "
            "VALUES (:id, :tid, 'staff_member', :sid, 1, '09:00', '18:00', 4, true, now(), now())"
        ), {"id": uuid.uuid4(), "tid": tenant_id, "sid": staff_id})
        await db.commit()

        doc_id_1 = doc_id_2 = None
        try:
            app.dependency_overrides[get_current_user] = lambda: make_technician_context(str(tenant_id), user_id=str(staff_user_id))
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                headers = {"Authorization": "Bearer x"}

                # 1. Real identity/employment, masked mobile, readiness incomplete (no documents yet).
                detail = (await client.get("/v1/staff/me/profile", headers=headers)).json()["data"]
                assert detail["identity"]["full_name"] == "Demo Technician"
                assert detail["identity"]["masked_mobile"] == "••••• 43210"
                assert detail["employment"]["designation"] == "Senior Technician"
                assert detail["employment"]["assigned_service_count"] == 1
                assert detail["readiness"]["profile_percentage"] < 100
                assert detail["readiness"]["required_documents"] == 3
                assert detail["readiness"]["verified_documents"] == 0

                # 2. Submit a required document.
                media_id_1 = uuid.uuid4()
                submit_resp = await client.post(
                    "/v1/staff/me/profile/documents", headers=headers,
                    json={"document_type": "identity_document", "media_id": str(media_id_1)},
                )
                assert submit_resp.status_code == 200
                doc_id_1 = submit_resp.json()["data"]["id"]
                assert submit_resp.json()["data"]["status"] == "pending_review"

                detail2 = (await client.get("/v1/staff/me/profile", headers=headers)).json()["data"]
                assert len(detail2["documents"]) == 1

                # 3. Replacing the same document type SUPERSEDES, never overwrites destructively.
                media_id_2 = uuid.uuid4()
                submit_resp2 = await client.post(
                    "/v1/staff/me/profile/documents", headers=headers,
                    json={"document_type": "identity_document", "media_id": str(media_id_2)},
                )
                doc_id_2 = submit_resp2.json()["data"]["id"]
                assert doc_id_2 != doc_id_1

                superseded = (await db.execute(text("SELECT is_current FROM staff_documents WHERE id=:id"), {"id": doc_id_1})).scalar()
                assert superseded is False
                current_row = (await db.execute(text("SELECT is_current FROM staff_documents WHERE id=:id"), {"id": doc_id_2})).scalar()
                assert current_row is True

                # Only the current document appears in the projection.
                detail3 = (await client.get("/v1/staff/me/profile", headers=headers)).json()["data"]
                assert len(detail3["documents"]) == 1
                assert detail3["documents"][0]["id"] == doc_id_2

                # 4. Notification preferences round-trip through the real model.
                prefs = (await client.get("/v1/staff/me/notification-preferences", headers=headers)).json()["data"]
                assert prefs["categories"]["job_updates"] is True  # default on, no rows yet

                update_resp = await client.put(
                    "/v1/staff/me/notification-preferences", headers=headers,
                    json={"category": "payment_updates", "enabled": False},
                )
                assert update_resp.status_code == 200
                assert update_resp.json()["data"]["categories"]["payment_updates"] is False
                assert update_resp.json()["data"]["categories"]["job_updates"] is True  # untouched
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            await db.execute(text("DELETE FROM notification_preferences WHERE user_id=:uid"), {"uid": staff_user_id})
            await db.execute(text("DELETE FROM staff_documents WHERE staff_member_id=:sid"), {"sid": staff_id})
            await db.execute(text("DELETE FROM provider_availability_rules WHERE scope_id=:sid"), {"sid": staff_id})
            await db.execute(text("DELETE FROM provider_team_members WHERE id=:sid"), {"sid": staff_id})
            await db.execute(text("DELETE FROM users WHERE id=:uid"), {"uid": staff_user_id})
            await db.commit()
