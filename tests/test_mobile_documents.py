"""Technician mobile app Phase T: GET/POST /v1/staff/me/documents + tenant
review, composed over the CANONICAL `TenantDocument` model (already used by
the tenant documents workspace) and `resolve_technician_requirements()` --
never a second document/media system.
"""
from __future__ import annotations

import datetime as dt
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


async def _seed_active_home_services_enrollment(db, tenant_id):
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


@pytest.mark.asyncio
async def test_documents_denies_customer_role():
    app.dependency_overrides[get_current_user] = lambda: UserContext(
        user_id=str(uuid.uuid4()), email="customer@serviceos.local", role="customer",
        tenant_id=None, full_name="Demo Customer", is_verified=True,
    )
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/v1/staff/me/documents", headers={"Authorization": "Bearer x"})
        assert response.status_code == 403
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_documents_full_lifecycle_live():
    from app.database import get_session_factory, init_db
    from app.engines.auth.models import User
    from app.engines.media.models import MediaAsset

    await init_db()
    factory = get_session_factory()
    async with factory() as db:
        tenant_id = uuid.uuid4()
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
            "INSERT INTO provider_team_members (id, tenant_id, user_id, member_type, full_name, status, created_at, updated_at) "
            "VALUES (:id, :tid, :uid, 'technician', 'Demo Technician', 'active', now(), now())"
        ), {"id": staff_id, "tid": tenant_id, "uid": staff_user_id})

        media_id = uuid.uuid4()
        await db.execute(text(
            "INSERT INTO media_assets (id, tenant_id, media_context, owner_type, owner_id, uploaded_by_user_id, status, "
            "storage_driver, storage_key, file_name_original, file_name_stored, mime_type, file_extension, "
            "file_size_bytes, checksum, created_at, updated_at) "
            "VALUES (:id, :tid, 'provider_document', 'user', :uid, :uid, 'active', 'local', 'test/key.pdf', "
            "'id.pdf', 'key.pdf', 'application/pdf', 'pdf', 1024, 'abc', now(), now())"
        ), {"id": media_id, "tid": tenant_id, "uid": str(staff_user_id)})
        await db.commit()

        doc_id = None
        try:
            headers = {"Authorization": "Bearer x"}
            app.dependency_overrides[get_current_user] = lambda: _tech_ctx(str(tenant_id), user_id=str(staff_user_id))
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                # 1. Initial projection: required manifest, nothing complete yet.
                initial = (await client.get("/v1/staff/me/documents", headers=headers)).json()["data"]
                assert initial["readiness"]["required"] == 2  # technician_identity_proof + technician_background_check
                assert initial["readiness"]["complete"] == 0
                req_codes = {r["code"] for r in initial["requirements"]}
                assert "technician_identity_proof" in req_codes

                # 2. Reject an unknown doc_type.
                bad_submit = await client.post(
                    "/v1/staff/me/documents", headers=headers,
                    json={"doc_type": "not_a_real_requirement", "media_asset_id": str(media_id)},
                )
                assert bad_submit.status_code == 422

                # 3. Submit a real requirement -- becomes pending_review, never Verified.
                submit_resp = await client.post(
                    "/v1/staff/me/documents", headers=headers,
                    json={"doc_type": "technician_identity_proof", "media_asset_id": str(media_id)},
                )
                assert submit_resp.status_code == 200
                doc_id = submit_resp.json()["data"]["id"]
                assert submit_resp.json()["data"]["status"] == "pending_review"

                after_submit = (await client.get("/v1/staff/me/documents", headers=headers)).json()["data"]
                identity_req = next(r for r in after_submit["requirements"] if r["code"] == "technician_identity_proof")
                assert identity_req["review_status"] == "pending_review"
                assert identity_req["current_version"] == 1

                # 4. Technician cannot review (route requires tenant_owner).
                self_review = await client.post(
                    f"/v1/tenant/documents/technicians/{doc_id}/review", headers=headers, json={"decision": "verified"},
                )
                assert self_review.status_code in (401, 403)

            # 5. Tenant owner approves.
            app.dependency_overrides[get_current_user] = lambda: _owner_ctx(str(tenant_id), user_id=str(owner_user_id))
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                approve_resp = await client.post(
                    f"/v1/tenant/documents/technicians/{doc_id}/review",
                    headers={"Authorization": "Bearer x"}, json={"decision": "verified"},
                )
                assert approve_resp.status_code == 200
                assert approve_resp.json()["data"]["status"] == "verified"

                # 6. Re-deciding an already-decided document is rejected (concurrency-safe).
                redecide = await client.post(
                    f"/v1/tenant/documents/technicians/{doc_id}/review",
                    headers={"Authorization": "Bearer x"}, json={"decision": "rejected", "reason": "test"},
                )
                assert redecide.status_code == 409

            # 7. Readiness recalculates for the technician.
            app.dependency_overrides[get_current_user] = lambda: _tech_ctx(str(tenant_id), user_id=str(staff_user_id))
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                after_verify = (await client.get("/v1/staff/me/documents", headers=headers)).json()["data"]
                assert after_verify["readiness"]["complete"] == 1
                identity_req2 = next(r for r in after_verify["requirements"] if r["code"] == "technician_identity_proof")
                assert identity_req2["review_status"] == "verified"

                # 8. Replace the verified document -- new version created, old preserved.
                media_id_2 = uuid.uuid4()
                await db.execute(text(
                    "INSERT INTO media_assets (id, tenant_id, media_context, owner_type, owner_id, uploaded_by_user_id, status, "
                    "storage_driver, storage_key, file_name_original, file_name_stored, mime_type, file_extension, "
                    "file_size_bytes, checksum, created_at, updated_at) "
                    "VALUES (:id, :tid, 'provider_document', 'user', :uid, :uid, 'active', 'local', 'test/key2.pdf', "
                    "'id2.pdf', 'key2.pdf', 'application/pdf', 'pdf', 1024, 'def', now(), now())"
                ), {"id": media_id_2, "tid": tenant_id, "uid": str(staff_user_id)})
                await db.commit()

                replace_resp = await client.post(
                    "/v1/staff/me/documents", headers=headers,
                    json={"doc_type": "technician_identity_proof", "media_asset_id": str(media_id_2)},
                )
                new_doc_id = replace_resp.json()["data"]["id"]
                assert new_doc_id != doc_id
                assert replace_resp.json()["data"]["version"] == 2
                assert replace_resp.json()["data"]["status"] == "pending_review"

                history = (await client.get("/v1/staff/me/documents/technician_identity_proof/history", headers=headers)).json()["data"]["versions"]
                assert len(history) == 2
                old_version = next(v for v in history if v["id"] == doc_id)
                assert old_version["is_current"] is False

                # 9. A PENDING replacement does not falsely make the requirement Verified.
                after_replace = (await client.get("/v1/staff/me/documents", headers=headers)).json()["data"]
                identity_req3 = next(r for r in after_replace["requirements"] if r["code"] == "technician_identity_proof")
                assert identity_req3["review_status"] == "pending_review"
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            await db.execute(text("DELETE FROM tenant_documents WHERE staff_member_id=:sid"), {"sid": staff_id})
            await db.execute(text("DELETE FROM media_assets WHERE owner_id=:uid"), {"uid": str(staff_user_id)})
            await db.execute(text("DELETE FROM tenant_vertical_enrollments WHERE tenant_id=:tid"), {"tid": tenant_id})
            await db.execute(text("DELETE FROM provider_team_members WHERE id=:sid"), {"sid": staff_id})
            await db.execute(text("DELETE FROM users WHERE id=:uid"), {"uid": staff_user_id})
            await db.commit()


@pytest.mark.asyncio
async def test_reject_requires_reason_and_cross_tenant_denied():
    from app.database import get_session_factory, init_db
    from app.engines.auth.models import User

    await init_db()
    factory = get_session_factory()
    async with factory() as db:
        tenant_id = uuid.uuid4()
        other_tenant_id = uuid.uuid4()
        staff_user_id = uuid.uuid4()
        owner_user_id = uuid.uuid4()
        await _seed_active_home_services_enrollment(db, tenant_id)

        user = User(
            id=staff_user_id, email=f"tech-{staff_user_id.hex[:8]}@serviceos.local", phone="9876500001",
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
        media_id = uuid.uuid4()
        await db.execute(text(
            "INSERT INTO media_assets (id, tenant_id, media_context, owner_type, owner_id, uploaded_by_user_id, status, "
            "storage_driver, storage_key, file_name_original, file_name_stored, mime_type, file_extension, "
            "file_size_bytes, checksum, created_at, updated_at) "
            "VALUES (:id, :tid, 'provider_document', 'user', :uid, :uid, 'active', 'local', 'test/key3.pdf', "
            "'id3.pdf', 'key3.pdf', 'application/pdf', 'pdf', 1024, 'ghi', now(), now())"
        ), {"id": media_id, "tid": tenant_id, "uid": str(staff_user_id)})
        await db.commit()

        doc_id = None
        try:
            app.dependency_overrides[get_current_user] = lambda: _tech_ctx(str(tenant_id), user_id=str(staff_user_id))
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                submit_resp = await client.post(
                    "/v1/staff/me/documents", headers={"Authorization": "Bearer x"},
                    json={"doc_type": "technician_background_check", "media_asset_id": str(media_id)},
                )
                doc_id = submit_resp.json()["data"]["id"]

            # Cross-tenant reviewer denied.
            app.dependency_overrides[get_current_user] = lambda: _owner_ctx(str(other_tenant_id), user_id=str(uuid.uuid4()))
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                cross_resp = await client.post(
                    f"/v1/tenant/documents/technicians/{doc_id}/review",
                    headers={"Authorization": "Bearer x"}, json={"decision": "verified"},
                )
                assert cross_resp.status_code == 404

            # Real tenant owner: reject without reason fails, with reason succeeds.
            app.dependency_overrides[get_current_user] = lambda: _owner_ctx(str(tenant_id), user_id=str(owner_user_id))
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                no_reason = await client.post(
                    f"/v1/tenant/documents/technicians/{doc_id}/review",
                    headers={"Authorization": "Bearer x"}, json={"decision": "rejected"},
                )
                assert no_reason.status_code == 400

                with_reason = await client.post(
                    f"/v1/tenant/documents/technicians/{doc_id}/review",
                    headers={"Authorization": "Bearer x"}, json={"decision": "rejected", "reason": "Blurry photo"},
                )
                assert with_reason.status_code == 200
                assert with_reason.json()["data"]["status"] == "rejected"
                assert with_reason.json()["data"]["rejection_reason"] == "Blurry photo"
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            await db.execute(text("DELETE FROM tenant_documents WHERE staff_member_id=:sid"), {"sid": staff_id})
            await db.execute(text("DELETE FROM media_assets WHERE owner_id=:uid"), {"uid": str(staff_user_id)})
            await db.execute(text("DELETE FROM tenant_vertical_enrollments WHERE tenant_id=:tid"), {"tid": tenant_id})
            await db.execute(text("DELETE FROM provider_team_members WHERE id=:sid"), {"sid": staff_id})
            await db.execute(text("DELETE FROM users WHERE id=:uid"), {"uid": staff_user_id})
            await db.commit()
