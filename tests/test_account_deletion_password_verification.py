"""Account Deletion Final Confirmation phase.

`right_to_erasure` requires current-password confirmation, validated
server-side in the SAME call that creates the request
(`app/engines/compliance/customer_router.py::create_my_request`). No
separate challenge/proof-issuance endpoint exists -- this is a real,
atomic verify-then-create step, not a placeholder.
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
from app.engines.auth.utils import hash_password
from app.engines.auth.models import User

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


async def _make_customer_with_password(password: str) -> uuid.UUID:
    user_id = uuid.uuid4()
    async with _real_sessionmaker() as db:
        db.add(User(
            id=user_id, email=f"{user_id}@test.example", phone=None,
            hashed_password=hash_password(password), role="customer",
            full_name="Demo Customer", is_active=True, is_verified=True,
        ))
        await db.commit()
    return user_id


async def _cleanup(*user_ids):
    async with _real_sessionmaker() as db:
        for uid in user_ids:
            await db.execute(text("DELETE FROM compliance_audit_logs WHERE actor_id=:uid"), {"uid": uid})
            await db.execute(text("DELETE FROM compliance_requests WHERE subject_id=:uid"), {"uid": uid})
            await db.execute(text("DELETE FROM users WHERE id=:uid"), {"uid": uid})
        await db.commit()


@pytest.mark.asyncio
async def test_correct_password_creates_a_verified_erasure_request():
    user_id = await _make_customer_with_password("correct-horse-battery")
    headers = {"Authorization": "Bearer x"}
    try:
        app.dependency_overrides[get_current_user] = lambda: _customer_ctx(user_id)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            res = await client.post("/v1/me/compliance/requests", headers=headers, json={
                "request_type": "right_to_erasure", "reason": "test", "confirm_understanding": True,
                "password": "correct-horse-battery",
            })
            assert res.status_code == 201
            request_id = res.json()["data"]["request_id"]

            detail = await client.get(f"/v1/me/compliance/requests/{request_id}", headers=headers)
            assert detail.json()["data"]["verification_status"] == "verified"
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        await _cleanup(user_id)


@pytest.mark.asyncio
async def test_wrong_password_rejected_and_no_request_created():
    user_id = await _make_customer_with_password("correct-horse-battery")
    headers = {"Authorization": "Bearer x"}
    try:
        app.dependency_overrides[get_current_user] = lambda: _customer_ctx(user_id)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            res = await client.post("/v1/me/compliance/requests", headers=headers, json={
                "request_type": "right_to_erasure", "reason": "test", "confirm_understanding": True,
                "password": "totally-wrong",
            })
            assert res.status_code != 201
            assert res.json()["error_code"] == "INVALID_PASSWORD"

            listing = await client.get("/v1/me/compliance/requests", headers=headers,
                                        params={"request_type": "right_to_erasure"})
            assert listing.json()["data"]["meta"]["total"] == 0
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        await _cleanup(user_id)


@pytest.mark.asyncio
async def test_missing_password_rejected_for_erasure():
    user_id = await _make_customer_with_password("correct-horse-battery")
    headers = {"Authorization": "Bearer x"}
    try:
        app.dependency_overrides[get_current_user] = lambda: _customer_ctx(user_id)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            res = await client.post("/v1/me/compliance/requests", headers=headers, json={
                "request_type": "right_to_erasure", "reason": "test", "confirm_understanding": True,
            })
            assert res.status_code != 201
            assert res.json()["error_code"] == "VALIDATION_ERROR"
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        await _cleanup(user_id)


@pytest.mark.asyncio
async def test_password_never_required_for_other_request_types():
    user_id = await _make_customer_with_password("correct-horse-battery")
    headers = {"Authorization": "Bearer x"}
    try:
        app.dependency_overrides[get_current_user] = lambda: _customer_ctx(user_id)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            res = await client.post("/v1/me/compliance/requests", headers=headers, json={
                "request_type": "data_export", "confirm_understanding": True,
            })
            assert res.status_code == 201
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        await _cleanup(user_id)


@pytest.mark.asyncio
async def test_idempotent_retry_with_password_returns_same_request_not_duplicate():
    user_id = await _make_customer_with_password("correct-horse-battery")
    headers = {"Authorization": "Bearer x"}
    key = str(uuid.uuid4())
    try:
        app.dependency_overrides[get_current_user] = lambda: _customer_ctx(user_id)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            first = await client.post("/v1/me/compliance/requests", headers=headers, json={
                "request_type": "right_to_erasure", "reason": "test", "confirm_understanding": True,
                "password": "correct-horse-battery", "idempotency_key": key,
            })
            assert first.status_code == 201
            first_id = first.json()["data"]["request_id"]

            second = await client.post("/v1/me/compliance/requests", headers=headers, json={
                "request_type": "right_to_erasure", "reason": "test", "confirm_understanding": True,
                "password": "correct-horse-battery", "idempotency_key": key,
            })
            assert second.status_code == 201
            assert second.json()["data"]["request_id"] == first_id
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        await _cleanup(user_id)
