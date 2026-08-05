"""Data Export Request phase — idempotent submission.

`POST /v1/me/compliance/requests` had no idempotency contract at all: a
network retry after a timeout could only be distinguished from a genuine
new submission by the duplicate-open-request check, which only fires
after the first request has already committed. This adds a caller-
supplied `idempotency_key`, scoped to customer + request_type, reusing
the existing `metadata_json` JSONB column (no migration).
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


def _customer_ctx(user_id):
    return UserContext(user_id=str(user_id), email="customer@serviceos.local", role="customer",
                        tenant_id=None, full_name="Demo Customer", is_verified=True)


async def _cleanup(*user_ids):
    async with _real_sessionmaker() as db:
        for uid in user_ids:
            await db.execute(text("DELETE FROM compliance_exports WHERE subject_id=:uid"), {"uid": uid})
            await db.execute(text("DELETE FROM compliance_audit_logs WHERE actor_id=:uid"), {"uid": uid})
            await db.execute(text("DELETE FROM compliance_requests WHERE subject_id=:uid"), {"uid": uid})
        await db.commit()


@pytest.mark.asyncio
async def test_repeated_idempotency_key_returns_the_original_request_not_a_duplicate():
    user_id = uuid.uuid4()
    headers = {"Authorization": "Bearer x"}
    key = str(uuid.uuid4())
    try:
        app.dependency_overrides[get_current_user] = lambda: _customer_ctx(user_id)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            first = await client.post("/v1/me/compliance/requests", headers=headers, json={
                "request_type": "data_export", "confirm_understanding": True, "idempotency_key": key,
            })
            assert first.status_code == 201
            first_id = first.json()["data"]["request_id"]

            second = await client.post("/v1/me/compliance/requests", headers=headers, json={
                "request_type": "data_export", "confirm_understanding": True, "idempotency_key": key,
            })
            assert second.status_code == 201
            assert second.json()["data"]["request_id"] == first_id

            listing = await client.get("/v1/me/compliance/requests", headers=headers)
            assert listing.json()["data"]["meta"]["total"] == 1
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        await _cleanup(user_id)


@pytest.mark.asyncio
async def test_idempotency_key_never_leaks_to_the_customer_response():
    user_id = uuid.uuid4()
    headers = {"Authorization": "Bearer x"}
    key = str(uuid.uuid4())
    try:
        app.dependency_overrides[get_current_user] = lambda: _customer_ctx(user_id)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            submit = await client.post("/v1/me/compliance/requests", headers=headers, json={
                "request_type": "data_export", "confirm_understanding": True, "idempotency_key": key,
            })
            assert "idempotency_key" not in submit.json()["data"]
            assert "metadata_json" not in submit.json()["data"]

            request_id = submit.json()["data"]["request_id"]
            detail = await client.get(f"/v1/me/compliance/requests/{request_id}", headers=headers)
            assert "idempotency_key" not in detail.json()["data"]
            assert "metadata_json" not in detail.json()["data"]
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        await _cleanup(user_id)


@pytest.mark.asyncio
async def test_different_idempotency_keys_are_treated_as_a_duplicate_open_request():
    """Two DIFFERENT keys for the same customer + request_type must still
    hit the real duplicate-open-request rule -- idempotency only protects
    against retries of the SAME attempt, never a bypass of the one-active-
    request-per-type policy."""
    user_id = uuid.uuid4()
    headers = {"Authorization": "Bearer x"}
    try:
        app.dependency_overrides[get_current_user] = lambda: _customer_ctx(user_id)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            first = await client.post("/v1/me/compliance/requests", headers=headers, json={
                "request_type": "data_export", "confirm_understanding": True,
                "idempotency_key": str(uuid.uuid4()),
            })
            assert first.status_code == 201

            second = await client.post("/v1/me/compliance/requests", headers=headers, json={
                "request_type": "data_export", "confirm_understanding": True,
                "idempotency_key": str(uuid.uuid4()),
            })
            assert second.status_code >= 400
            assert second.json()["error_code"] == "DUPLICATE_OPEN_REQUEST"
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        await _cleanup(user_id)


@pytest.mark.asyncio
async def test_omitting_idempotency_key_still_works_exactly_as_before():
    user_id = uuid.uuid4()
    headers = {"Authorization": "Bearer x"}
    try:
        app.dependency_overrides[get_current_user] = lambda: _customer_ctx(user_id)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            submit = await client.post("/v1/me/compliance/requests", headers=headers, json={
                "request_type": "data_export", "confirm_understanding": True,
            })
            assert submit.status_code == 201
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        await _cleanup(user_id)
