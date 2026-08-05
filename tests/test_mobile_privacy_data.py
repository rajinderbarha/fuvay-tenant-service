"""Technician mobile app Phase X: GET/PATCH/POST /v1/me/privacy/* -- extends
the SAME canonical global compliance/DPDP system (ComplianceRequest,
ComplianceEnterpriseService, ConsentRecord) used by the tenant/customer
routers, adding the technician self-service entry point confirmed missing
by audit (subject_type="tenant_staff" requests could previously only be
viewed/responded-to by a tenant owner, never created by the technician
themselves).
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


def _ctx(user_id, tenant_id=None):
    return UserContext(user_id=str(user_id), email="tech@serviceos.local", role="technician",
                        tenant_id=str(tenant_id) if tenant_id else None, full_name="Demo Technician", is_verified=True)


@pytest.mark.asyncio
async def test_privacy_denies_customer_role():
    app.dependency_overrides[get_current_user] = lambda: UserContext(
        user_id=str(uuid.uuid4()), email="customer@serviceos.local", role="customer",
        tenant_id=None, full_name="Demo Customer", is_verified=True,
    )
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/v1/me/privacy/summary", headers={"Authorization": "Bearer x"})
        assert resp.status_code == 403
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_privacy_full_lifecycle_live_and_visible_to_tenant_owner():
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()

    try:
        headers = {"Authorization": "Bearer x"}
        app.dependency_overrides[get_current_user] = lambda: _ctx(user_id, tenant_id)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # 1. Default summary -- up to date, no fabricated status.
            initial = (await client.get("/v1/me/privacy/summary", headers=headers)).json()["data"]
            assert initial["privacy_status"]["code"] == "up_to_date"
            assert initial["request_counts"]["open"] == 0

            # 2. Required consent cannot be disabled.
            forged = await client.patch("/v1/me/privacy/consents/service_communications", headers=headers, json={"enabled": False})
            assert forged.status_code == 422

            # 3. Unknown purpose rejected.
            unknown = await client.patch("/v1/me/privacy/consents/not_a_real_purpose", headers=headers, json={"enabled": False})
            assert unknown.status_code == 422

            # 4. Optional consent withdrawal persists and is visible in the consent ledger (never destructive).
            withdraw = await client.patch("/v1/me/privacy/consents/product_improvement", headers=headers, json={"enabled": False})
            assert withdraw.status_code == 200
            consents_after = (await client.get("/v1/me/privacy/consents", headers=headers)).json()["data"]["consents"]
            product = next(c for c in consents_after if c["purpose_code"] == "product_improvement")
            assert product["enabled"] is False
            assert product["last_changed_at"] is not None

            # 5. Invalid request_type rejected.
            bad_type = await client.post("/v1/me/privacy/requests", headers=headers, json={
                "request_type": "not_a_real_type", "reason": "test", "confirm_understanding": True,
            })
            assert bad_type.status_code == 422

            # 6. Submit a real Correction request (data_correction).
            submit = await client.post("/v1/me/privacy/requests", headers=headers, json={
                "request_type": "data_correction", "reason": "My designation is wrong.", "confirm_understanding": True,
            })
            assert submit.status_code == 201
            request_id = submit.json()["data"]["request_id"]
            assert submit.json()["data"]["status"] == "submitted"

            # 7. Duplicate open request of the same type rejected.
            dup = await client.post("/v1/me/privacy/requests", headers=headers, json={
                "request_type": "data_correction", "reason": "Same thing again.", "confirm_understanding": True,
            })
            assert dup.status_code == 409

            # 8. Detail view shows the request and a safe audit trail.
            detail = (await client.get(f"/v1/me/privacy/requests/{request_id}", headers=headers)).json()["data"]
            assert detail["request_type"] == "data_correction"
            assert isinstance(detail["audit_trail"], list)

            # 9. Summary now reflects the open request.
            after_submit = (await client.get("/v1/me/privacy/summary", headers=headers)).json()["data"]
            assert after_submit["privacy_status"]["code"] == "request_in_progress"
            assert after_submit["request_counts"]["open"] == 1

            # 10. Withdraw the request.
            withdraw_req = await client.post(f"/v1/me/privacy/requests/{request_id}/withdraw", headers=headers)
            assert withdraw_req.status_code == 200
            re_withdraw = await client.post(f"/v1/me/privacy/requests/{request_id}/withdraw", headers=headers)
            assert re_withdraw.status_code == 422  # already cancelled -- INVALID_STATE

        # 11. GLOBAL INTEGRATION PROOF: the request is visible through the
        # EXISTING tenant owner staff-requests endpoint -- confirms this is
        # the one real system, not a parallel one.
        owner_id = uuid.uuid4()
        app.dependency_overrides[get_current_user] = lambda: UserContext(
            user_id=str(owner_id), email="owner@serviceos.local", role="tenant_owner",
            tenant_id=str(tenant_id), full_name="Demo Owner", is_verified=True,
        )
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            staff_view = (await client.get("/v1/provider/compliance/staff-requests", headers=headers)).json()["data"]
            assert any(r["id"] == request_id for r in staff_view["requests"])
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        async with _real_sessionmaker() as db:
            await db.execute(text("DELETE FROM compliance_audit_logs WHERE actor_id=:uid"), {"uid": user_id})
            await db.execute(text("DELETE FROM compliance_requests WHERE subject_id=:uid"), {"uid": user_id})
            await db.execute(text("DELETE FROM consent_records WHERE user_id=:uid"), {"uid": user_id})
            await db.commit()


@pytest.mark.asyncio
async def test_cross_person_request_denied():
    user_a = uuid.uuid4()
    user_b = uuid.uuid4()
    tenant_id = uuid.uuid4()

    try:
        app.dependency_overrides[get_current_user] = lambda: _ctx(user_a, tenant_id)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            submit = await client.post("/v1/me/privacy/requests", headers={"Authorization": "Bearer x"}, json={
                "request_type": "grievance", "reason": "test grievance", "confirm_understanding": True,
            })
            request_id = submit.json()["data"]["request_id"]

        app.dependency_overrides[get_current_user] = lambda: _ctx(user_b, tenant_id)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            cross_get = await client.get(f"/v1/me/privacy/requests/{request_id}", headers={"Authorization": "Bearer x"})
            assert cross_get.status_code == 404
            cross_withdraw = await client.post(f"/v1/me/privacy/requests/{request_id}/withdraw", headers={"Authorization": "Bearer x"})
            assert cross_withdraw.status_code == 404
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        async with _real_sessionmaker() as db:
            await db.execute(text("DELETE FROM compliance_audit_logs WHERE actor_id=:uid"), {"uid": user_a})
            await db.execute(text("DELETE FROM compliance_requests WHERE subject_id=:uid"), {"uid": user_a})
            await db.commit()


@pytest.mark.asyncio
async def test_export_requires_approval_and_correct_request_type():
    user_id = uuid.uuid4()
    tenant_id = uuid.uuid4()
    try:
        app.dependency_overrides[get_current_user] = lambda: _ctx(user_id, tenant_id)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            headers = {"Authorization": "Bearer x"}
            submit = await client.post("/v1/me/privacy/requests", headers=headers, json={
                "request_type": "staff_data_export", "reason": "Want a copy of my data.", "confirm_understanding": True,
            })
            request_id = submit.json()["data"]["request_id"]

            # Not yet approved -- export generation blocked.
            blocked = await client.post(f"/v1/me/privacy/requests/{request_id}/generate-export", headers=headers)
            assert blocked.status_code == 422

            # Wrong request type rejected for export generation.
            grievance = await client.post("/v1/me/privacy/requests", headers=headers, json={
                "request_type": "grievance", "reason": "unrelated", "confirm_understanding": True,
            })
            grievance_id = grievance.json()["data"]["request_id"]
            wrong_type = await client.post(f"/v1/me/privacy/requests/{grievance_id}/generate-export", headers=headers)
            assert wrong_type.status_code == 422
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        async with _real_sessionmaker() as db:
            await db.execute(text("DELETE FROM compliance_audit_logs WHERE actor_id=:uid"), {"uid": user_id})
            await db.execute(text("DELETE FROM compliance_requests WHERE subject_id=:uid"), {"uid": user_id})
            await db.commit()
