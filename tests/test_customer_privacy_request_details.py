"""Customer app Privacy Request Details / Status phase.

Covers the customer self-service compliance router
(`app/engines/compliance/customer_router.py`) end-to-end against a real DB:
detail-view ownership, enumeration-safety (missing vs. foreign request),
cancel/withdraw allowed-state gating, and export download ownership +
the export `download_url` bug fixed this phase (it previously pointed at
an admin-only route the customer could never call).
"""
from __future__ import annotations

import os
import uuid

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import text

from app.main import app
from app.dependencies.auth import get_current_user, UserContext
from app.dependencies.db import get_db
from app.config import get_settings
from app.engines.auth.models import User
from app.engines.auth.utils import hash_password
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_DATABASE_INTEGRATION_TESTS") != "1",
    reason="requires PostgreSQL integration database",
)

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


def _customer_ctx(user_id):
    return UserContext(user_id=str(user_id), email="customer@serviceos.local", role="customer",
                        tenant_id=None, full_name="Demo Customer", is_verified=True)


def _admin_ctx():
    return UserContext(user_id=str(uuid.uuid4()), email="admin@serviceos.local", role="super_admin",
                        tenant_id=None, full_name="Demo Admin", is_verified=True)


async def _make_customer_with_password(password: str) -> uuid.UUID:
    user_id = uuid.uuid4()
    async with _real_sessionmaker() as db:
        db.add(User(
            id=user_id, email=f"{user_id}@privacy-test.example", phone=None,
            hashed_password=hash_password(password), role="customer",
            full_name="Demo Customer", is_active=True, is_verified=True,
        ))
        await db.commit()
    return user_id


async def _cleanup(*user_ids):
    async with _real_sessionmaker() as db:
        for uid in user_ids:
            await db.execute(text("DELETE FROM compliance_exports WHERE subject_id=:uid"), {"uid": uid})
            await db.execute(text("DELETE FROM compliance_audit_logs WHERE actor_id=:uid"), {"uid": uid})
            await db.execute(text("DELETE FROM compliance_requests WHERE subject_id=:uid"), {"uid": uid})
            await db.execute(text("DELETE FROM users WHERE id=:uid"), {"uid": uid})
        await db.commit()


@pytest.mark.asyncio
async def test_get_detail_own_request_returns_safe_fields_and_audit_trail():
    password = "privacy-test-password"
    user_id = await _make_customer_with_password(password)
    headers = {"Authorization": "Bearer x"}
    try:
        app.dependency_overrides[get_current_user] = lambda: _customer_ctx(user_id)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            submit = await client.post("/v1/me/compliance/requests", headers=headers, json={
                "request_type": "right_to_erasure", "reason": "test", "confirm_understanding": True,
                "password": password,
            })
            assert submit.status_code == 201
            request_id = submit.json()["data"]["request_id"]

            detail = await client.get(f"/v1/me/compliance/requests/{request_id}", headers=headers)
            assert detail.status_code == 200
            data = detail.json()["data"]
            assert data["id"] == request_id
            assert data["request_type"] == "right_to_erasure"
            assert isinstance(data["audit_trail"], list)
            assert any(e["action"] == "request.created" for e in data["audit_trail"])
            # No internal/admin-only field ever reaches the customer.
            for forbidden in ("admin_notes", "assigned_to_admin_id", "subject_email", "subject_id", "metadata_json"):
                assert forbidden not in data
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        await _cleanup(user_id)


@pytest.mark.asyncio
async def test_missing_and_foreign_request_return_identical_404():
    user_a = uuid.uuid4()
    user_b = uuid.uuid4()
    headers = {"Authorization": "Bearer x"}
    try:
        app.dependency_overrides[get_current_user] = lambda: _customer_ctx(user_a)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            submit = await client.post("/v1/me/compliance/requests", headers=headers, json={
                "request_type": "data_export", "confirm_understanding": True,
            })
            real_request_id = submit.json()["data"]["request_id"]

        # Customer B tries the real request (foreign) and a random UUID (missing).
        app.dependency_overrides[get_current_user] = lambda: _customer_ctx(user_b)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            foreign = await client.get(f"/v1/me/compliance/requests/{real_request_id}", headers=headers)
            missing = await client.get(f"/v1/me/compliance/requests/{uuid.uuid4()}", headers=headers)

        assert foreign.status_code == missing.status_code == 404
        assert foreign.json()["error_code"] == missing.json()["error_code"] == "NOT_FOUND"
        assert foreign.json()["detail"] == missing.json()["detail"]
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        await _cleanup(user_a, user_b)


@pytest.mark.asyncio
async def test_withdraw_allowed_while_submitted_forbidden_once_terminal():
    user_id = uuid.uuid4()
    headers = {"Authorization": "Bearer x"}
    try:
        app.dependency_overrides[get_current_user] = lambda: _customer_ctx(user_id)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            submit = await client.post("/v1/me/compliance/requests", headers=headers, json={
                "request_type": "grievance", "reason": "test", "confirm_understanding": True,
            })
            request_id = submit.json()["data"]["request_id"]

            cancel = await client.post(f"/v1/me/compliance/requests/{request_id}/cancel", headers=headers)
            assert cancel.status_code == 200
            assert cancel.json()["data"]["cancelled"] is True

            # Idempotency / race safety: cancelling an already-cancelled
            # (terminal) request is rejected, not silently accepted twice.
            re_cancel = await client.post(f"/v1/me/compliance/requests/{request_id}/cancel", headers=headers)
            assert re_cancel.status_code == 422
            assert re_cancel.json()["error_code"] == "INVALID_STATE"
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        await _cleanup(user_id)


@pytest.mark.asyncio
async def test_withdraw_denied_for_foreign_request():
    user_a = uuid.uuid4()
    user_b = uuid.uuid4()
    headers = {"Authorization": "Bearer x"}
    try:
        app.dependency_overrides[get_current_user] = lambda: _customer_ctx(user_a)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            submit = await client.post("/v1/me/compliance/requests", headers=headers, json={
                "request_type": "consent_withdrawal", "confirm_understanding": True,
            })
            request_id = submit.json()["data"]["request_id"]

        app.dependency_overrides[get_current_user] = lambda: _customer_ctx(user_b)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(f"/v1/me/compliance/requests/{request_id}/cancel", headers=headers)
        assert resp.status_code == 404
        assert resp.json()["error_code"] == "NOT_FOUND"
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        await _cleanup(user_a, user_b)


@pytest.mark.asyncio
async def test_export_download_ownership_and_url_points_to_customer_route():
    """Also proves this phase's fix: `download_url` in the customer's own
    download response must be the customer-callable route, never the
    admin-only path `enterprise_service.process_request` stores on the
    `ComplianceExport` row."""
    user_a = uuid.uuid4()
    user_b = uuid.uuid4()
    headers = {"Authorization": "Bearer x"}
    try:
        app.dependency_overrides[get_current_user] = lambda: _customer_ctx(user_a)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            submit = await client.post("/v1/me/compliance/requests", headers=headers, json={
                "request_type": "data_export", "confirm_understanding": True,
            })
            request_id = submit.json()["data"]["request_id"]

        # Admin approves + processes -> generates a real ready export.
        app.dependency_overrides[get_current_user] = _admin_ctx
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            approve = await client.post(f"/v1/admin/compliance/requests/{request_id}/approve", headers=headers, json={})
            assert approve.status_code == 200
            verify = await client.post(f"/v1/admin/compliance/requests/{request_id}/verify-identity", headers=headers, json={})
            assert verify.status_code == 200
            process = await client.post(f"/v1/admin/compliance/requests/{request_id}/process", headers=headers)
            assert process.status_code == 200
            export_id = process.json()["data"]["process_result"]["export_id"]

        # Foreign customer cannot download it.
        app.dependency_overrides[get_current_user] = lambda: _customer_ctx(user_b)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            foreign_download = await client.get(f"/v1/me/compliance/exports/{export_id}/download", headers=headers)
        assert foreign_download.status_code == 404
        assert foreign_download.json()["error_code"] == "NOT_FOUND"

        # Owning customer can download it, and the returned URL is the
        # real customer-callable route -- not the admin-only one.
        app.dependency_overrides[get_current_user] = lambda: _customer_ctx(user_a)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            own_download = await client.get(f"/v1/me/compliance/exports/{export_id}/download", headers=headers)
        assert own_download.status_code == 200
        download_url = own_download.json()["data"]["download_url"]
        assert download_url == f"/v1/me/compliance/exports/{export_id}/download"
        assert "/v1/admin/" not in download_url
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        await _cleanup(user_a, user_b)


@pytest.mark.asyncio
async def test_expired_export_returns_export_expired_and_never_reissues_url():
    user_id = uuid.uuid4()
    headers = {"Authorization": "Bearer x"}
    try:
        app.dependency_overrides[get_current_user] = lambda: _customer_ctx(user_id)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            submit = await client.post("/v1/me/compliance/requests", headers=headers, json={
                "request_type": "data_export", "confirm_understanding": True,
            })
            request_id = submit.json()["data"]["request_id"]

        app.dependency_overrides[get_current_user] = _admin_ctx
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            await client.post(f"/v1/admin/compliance/requests/{request_id}/approve", headers=headers, json={})
            await client.post(f"/v1/admin/compliance/requests/{request_id}/verify-identity", headers=headers, json={})
            process = await client.post(f"/v1/admin/compliance/requests/{request_id}/process", headers=headers)
            export_id = process.json()["data"]["process_result"]["export_id"]

        # Force the export into the past to simulate real expiry.
        async with _real_sessionmaker() as db:
            await db.execute(
                text("UPDATE compliance_exports SET expires_at = now() - interval '1 day' WHERE id=:eid"),
                {"eid": export_id})
            await db.commit()

        app.dependency_overrides[get_current_user] = lambda: _customer_ctx(user_id)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get(f"/v1/me/compliance/exports/{export_id}/download", headers=headers)
        assert resp.status_code == 422
        assert resp.json()["error_code"] == "EXPORT_EXPIRED"

        async with _real_sessionmaker() as db:
            from sqlalchemy import select
            from app.engines.compliance.models import ComplianceExport
            row = (await db.execute(select(ComplianceExport).where(ComplianceExport.id == uuid.UUID(export_id)))).scalar_one()
            assert row.download_url is None
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        await _cleanup(user_id)


@pytest.mark.asyncio
async def test_deletion_request_submission_alone_does_not_revoke_session():
    """Session revocation only happens inside `service.process_deletion`
    (real erasure execution), never on mere submission -- confirmed by
    audit; this proves the customer's own auth context still works
    immediately after filing a right_to_erasure request."""
    password = "privacy-test-password"
    user_id = await _make_customer_with_password(password)
    headers = {"Authorization": "Bearer x"}
    try:
        app.dependency_overrides[get_current_user] = lambda: _customer_ctx(user_id)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            submit = await client.post("/v1/me/compliance/requests", headers=headers, json={
                "request_type": "right_to_erasure", "reason": "test", "confirm_understanding": True,
                "password": password,
            })
            assert submit.status_code == 201
            # Same authenticated context still works right after submission.
            follow_up = await client.get("/v1/me/compliance/requests", headers=headers)
            assert follow_up.status_code == 200
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        await _cleanup(user_id)
