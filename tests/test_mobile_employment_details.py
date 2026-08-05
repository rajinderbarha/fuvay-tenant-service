"""Technician mobile app Phase S: GET /v1/staff/me/employment-details +
employment-correction-request lifecycle, composed over the canonical
ProviderTeamMember plus the two genuinely-new tables (StaffSkillRecord,
StaffCorrectionRequest) confirmed missing by audit.
"""
from __future__ import annotations

import json
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


def _tech_ctx(tenant_id, user_id=None):
    return UserContext(user_id=user_id or str(uuid.uuid4()), email="staff@serviceos.local", role="technician",
                        tenant_id=tenant_id, full_name="Demo Technician", is_verified=True)


def _owner_ctx(tenant_id, user_id=None):
    return UserContext(user_id=user_id or str(uuid.uuid4()), email="owner@serviceos.local", role="tenant_owner",
                        tenant_id=tenant_id, full_name="Demo Owner", is_verified=True)


@pytest.mark.asyncio
async def test_employment_details_denies_customer_role():
    app.dependency_overrides[get_current_user] = lambda: UserContext(
        user_id=str(uuid.uuid4()), email="customer@serviceos.local", role="customer",
        tenant_id=None, full_name="Demo Customer", is_verified=True,
    )
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/v1/staff/me/employment-details", headers={"Authorization": "Bearer x"})
        assert response.status_code == 403
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_employment_details_requires_tenant_context():
    app.dependency_overrides[get_current_user] = lambda: UserContext(
        user_id=str(uuid.uuid4()), email="staff@serviceos.local", role="technician",
        tenant_id=None, full_name="No Tenant", is_verified=True,
    )
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/v1/staff/me/employment-details", headers={"Authorization": "Bearer x"})
        assert response.status_code == 403
    finally:
        app.dependency_overrides.pop(get_current_user, None)


async def _seed_active_home_services_enrollment(db, tenant_id):
    """Every mobile-employment endpoint gates on require_tenant_vertical_active
    ("home_services") -- a real Vertical + active TenantVerticalEnrollment row
    is required for any of these calls to pass, not just a tenant row."""
    vertical_id = (await db.execute(text("SELECT id FROM verticals WHERE key='home_services'"))).scalar()
    if not vertical_id:
        vertical_id = uuid.uuid4()
        await db.execute(text(
            "INSERT INTO verticals (id, key, label, is_enabled, is_beta, created_at, updated_at) "
            "VALUES (:id, 'home_services', 'Home Services', true, false, now(), now())"
        ), {"id": vertical_id})
    await db.execute(text(
        "INSERT INTO tenant_vertical_enrollments (id, tenant_id, vertical_id, status, created_at, updated_at) "
        "VALUES (:id, :tid, :vid, 'active', now(), now())"
    ), {"id": uuid.uuid4(), "tid": tenant_id, "vid": vertical_id})
    await db.commit()
    return vertical_id


@pytest.mark.asyncio
async def test_employment_details_full_lifecycle_live():
    from app.database import get_session_factory, init_db
    from app.engines.auth.models import User

    await init_db()
    factory = get_session_factory()
    async with factory() as db:
        tenant_id = uuid.uuid4()
        offering_id = uuid.uuid4()
        staff_user_id = uuid.uuid4()
        owner_user_id = uuid.uuid4()

        await _seed_active_home_services_enrollment(db, tenant_id)

        user = User(
            id=staff_user_id, email=f"tech-{staff_user_id.hex[:8]}@serviceos.local", phone="9876543210",
            full_name="Demo Technician", role="technician", tenant_id=tenant_id,
            hashed_password="x", is_active=True, is_verified=True, is_mfa_enabled=False,
        )
        db.add(user)
        await db.flush()

        staff_id = uuid.uuid4()
        await db.execute(text(
            "INSERT INTO provider_team_members (id, tenant_id, user_id, member_type, full_name, status, "
            "designation, supported_offering_ids, max_concurrent_jobs, created_at, updated_at) "
            "VALUES (:id, :tid, :uid, 'technician', 'Demo Technician', 'active', 'Technician', "
            "CAST(:offerings AS jsonb), 4, now(), now())"
        ), {"id": staff_id, "tid": tenant_id, "uid": staff_user_id, "offerings": json.dumps([str(offering_id)])})

        # Two skills: one verified, one pending -- proves the projection never
        # claims a self-reported skill is verified.
        await db.execute(text(
            "INSERT INTO staff_skill_records (id, tenant_id, staff_member_id, skill_name, verification_status, verified_at, created_at, updated_at) "
            "VALUES (:id, :tid, :sid, 'AC diagnostics', 'verified', now(), now(), now())"
        ), {"id": uuid.uuid4(), "tid": tenant_id, "sid": staff_id})
        await db.execute(text(
            "INSERT INTO staff_skill_records (id, tenant_id, staff_member_id, skill_name, verification_status, created_at, updated_at) "
            "VALUES (:id, :tid, :sid, 'Gas line repair', 'pending', now(), now())"
        ), {"id": uuid.uuid4(), "tid": tenant_id, "sid": staff_id})
        await db.commit()

        correction_id = None
        try:
            headers = {"Authorization": "Bearer x"}
            app.dependency_overrides[get_current_user] = lambda: _tech_ctx(str(tenant_id), user_id=str(staff_user_id))
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                # 1. Real employment/assignment/skill projection -- no fabrication.
                detail = (await client.get("/v1/staff/me/employment-details", headers=headers)).json()["data"]
                assert detail["employment"]["designation"] == "Technician"
                assert detail["employment"]["status"] == "active"
                assert detail["employment"]["status_known"] is True
                skills = {s["name"]: s for s in detail["assignments"]["verified_skills"]}
                assert skills["AC diagnostics"]["verification_status"] == "verified"
                assert skills["Gas line repair"]["verification_status"] == "pending"

                # 2. Tenant-controlled fields cannot be mutated via any mobile
                #    profile-update payload -- confirm there is no PUT/PATCH
                #    route on this employment-details endpoint at all.
                mutate_attempt = await client.put(
                    "/v1/staff/me/employment-details", headers=headers, json={"designation": "Owner"},
                )
                assert mutate_attempt.status_code in (404, 405)

                # 3. Submit a correction request for designation.
                submit_resp = await client.post(
                    "/v1/staff/me/employment-correction-requests", headers=headers,
                    json={"field_key": "designation", "requested_value": "Senior Technician", "reason": "Promoted last month"},
                )
                assert submit_resp.status_code == 200
                correction_id = submit_resp.json()["data"]["id"]
                assert submit_resp.json()["data"]["status"] == "pending_review"

                # 4. Duplicate pending request for the same field is rejected.
                dup_resp = await client.post(
                    "/v1/staff/me/employment-correction-requests", headers=headers,
                    json={"field_key": "designation", "requested_value": "Lead Technician", "reason": "Also promoted"},
                )
                assert dup_resp.status_code == 409

                # 5. Technician cannot approve their own request.
                self_review = await client.post(
                    f"/v1/tenant/home-services/staff-corrections/{correction_id}/approve", headers=headers, json={},
                )
                assert self_review.status_code in (401, 403)

            # 6. Authorized tenant owner approves -- applies through the canonical service.
            app.dependency_overrides[get_current_user] = lambda: _owner_ctx(str(tenant_id), user_id=str(owner_user_id))
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                approve_resp = await client.post(
                    f"/v1/tenant/home-services/staff-corrections/{correction_id}/approve",
                    headers={"Authorization": "Bearer x"}, json={"note": "Confirmed with manager"},
                )
                assert approve_resp.status_code == 200
                assert approve_resp.json()["data"]["status"] == "applied"

            new_designation = (await db.execute(text("SELECT designation FROM provider_team_members WHERE id=:id"), {"id": staff_id})).scalar()
            assert new_designation == "Senior Technician"

            # 7. Cross-tenant technician denied -- fails closed at the vertical
            #    guard (this "other tenant" has no active Home Services
            #    enrollment at all, so the request never even reaches staff
            #    resolution). Separately confirm same-tenant staff resolution
            #    for a genuinely different, non-enrolled staff user returns no
            #    employment record rather than someone else's.
            other_tenant = uuid.uuid4()
            app.dependency_overrides[get_current_user] = lambda: _tech_ctx(str(other_tenant), user_id=str(staff_user_id))
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                cross_resp = await client.get("/v1/staff/me/employment-details", headers={"Authorization": "Bearer x"})
                assert cross_resp.status_code == 403

            app.dependency_overrides[get_current_user] = lambda: _tech_ctx(str(tenant_id), user_id=str(uuid.uuid4()))
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                unknown_staff_resp = await client.get("/v1/staff/me/employment-details", headers={"Authorization": "Bearer x"})
                assert unknown_staff_resp.json()["data"]["employment"] is None

        finally:
            app.dependency_overrides.pop(get_current_user, None)
            await db.execute(text("DELETE FROM staff_correction_requests WHERE staff_member_id=:sid"), {"sid": staff_id})
            await db.execute(text("DELETE FROM staff_skill_records WHERE staff_member_id=:sid"), {"sid": staff_id})
            await db.execute(text("DELETE FROM tenant_vertical_enrollments WHERE tenant_id=:tid"), {"tid": tenant_id})
            await db.execute(text("DELETE FROM provider_team_members WHERE id=:sid"), {"sid": staff_id})
            await db.execute(text("DELETE FROM users WHERE id=:uid"), {"uid": staff_user_id})
            await db.commit()


@pytest.mark.asyncio
async def test_reject_requires_reason_and_records_decision():
    from app.database import get_session_factory, init_db
    from app.engines.auth.models import User

    await init_db()
    factory = get_session_factory()
    async with factory() as db:
        tenant_id = uuid.uuid4()
        staff_user_id = uuid.uuid4()
        owner_user_id = uuid.uuid4()
        await _seed_active_home_services_enrollment(db, tenant_id)

        user = User(
            id=staff_user_id, email=f"tech-{staff_user_id.hex[:8]}@serviceos.local", phone="9876500000",
            full_name="Demo Tech Two", role="technician", tenant_id=tenant_id,
            hashed_password="x", is_active=True, is_verified=True, is_mfa_enabled=False,
        )
        db.add(user)
        await db.flush()
        staff_id = uuid.uuid4()
        await db.execute(text(
            "INSERT INTO provider_team_members (id, tenant_id, user_id, member_type, full_name, status, created_at, updated_at) "
            "VALUES (:id, :tid, :uid, 'technician', 'Demo Tech Two', 'active', now(), now())"
        ), {"id": staff_id, "tid": tenant_id, "uid": staff_user_id})
        await db.commit()

        correction_id = None
        try:
            app.dependency_overrides[get_current_user] = lambda: _tech_ctx(str(tenant_id), user_id=str(staff_user_id))
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                submit_resp = await client.post(
                    "/v1/staff/me/employment-correction-requests", headers={"Authorization": "Bearer x"},
                    json={"field_key": "designation", "requested_value": "Lead", "reason": "test"},
                )
                correction_id = submit_resp.json()["data"]["id"]

            app.dependency_overrides[get_current_user] = lambda: _owner_ctx(str(tenant_id), user_id=str(owner_user_id))
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                no_reason = await client.post(
                    f"/v1/tenant/home-services/staff-corrections/{correction_id}/reject",
                    headers={"Authorization": "Bearer x"}, json={},
                )
                assert no_reason.status_code == 400

                with_reason = await client.post(
                    f"/v1/tenant/home-services/staff-corrections/{correction_id}/reject",
                    headers={"Authorization": "Bearer x"}, json={"note": "Not eligible yet"},
                )
                assert with_reason.status_code == 200
                assert with_reason.json()["data"]["status"] == "rejected"

            reviewed_by = (await db.execute(text("SELECT reviewed_by_user_id FROM staff_correction_requests WHERE id=:id"), {"id": correction_id})).scalar()
            assert str(reviewed_by) == str(owner_user_id)
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            await db.execute(text("DELETE FROM staff_correction_requests WHERE staff_member_id=:sid"), {"sid": staff_id})
            await db.execute(text("DELETE FROM tenant_vertical_enrollments WHERE tenant_id=:tid"), {"tid": tenant_id})
            await db.execute(text("DELETE FROM provider_team_members WHERE id=:sid"), {"sid": staff_id})
            await db.execute(text("DELETE FROM users WHERE id=:uid"), {"uid": staff_user_id})
            await db.commit()
