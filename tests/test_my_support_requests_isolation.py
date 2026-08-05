"""My Support Requests phase — customer isolation proof against a real DB.

Complements the existing `test_phase2f10_customer_complaints_authorization.py`
(service-layer/mocked ownership tests) with real HTTP + real DB proof that
`GET /v1/customer/complaints` (list) never returns another customer's rows,
and that the customer identity used for every read comes from the
authenticated JWT alone -- never a client-supplied filter or query param.
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


async def _seed_complaint(customer_id, tenant_id, booking_id):
    async with _real_sessionmaker() as db:
        await db.execute(text("""
            INSERT INTO customer_complaints
              (id, complaint_number, customer_id, tenant_id, category_id, record_type, record_id,
               booking_id, complaint_type, status, priority, title, description, created_at, updated_at)
            VALUES
              (:id, :num, :cust, :tenant, :cat, 'service_booking', :booking, :booking,
               'service_quality', 'open', 'normal', NULL, 'test complaint', now(), now())
        """), {
            "id": uuid.uuid4(), "num": f"CMP-TEST-{uuid.uuid4().hex[:8]}",
            "cust": customer_id, "tenant": tenant_id, "cat": uuid.uuid4(), "booking": booking_id,
        })
        await db.commit()


async def _cleanup(*customer_ids):
    async with _real_sessionmaker() as db:
        for cid in customer_ids:
            await db.execute(text("DELETE FROM customer_complaints WHERE customer_id=:cid"), {"cid": cid})
        await db.commit()


@pytest.mark.asyncio
async def test_list_never_returns_a_foreign_customers_complaint():
    customer_a = uuid.uuid4()
    customer_b = uuid.uuid4()
    headers = {"Authorization": "Bearer x"}
    try:
        await _seed_complaint(customer_a, uuid.uuid4(), uuid.uuid4())
        await _seed_complaint(customer_b, uuid.uuid4(), uuid.uuid4())

        app.dependency_overrides[get_current_user] = lambda: _customer_ctx(customer_a)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/v1/customer/complaints", headers=headers)
        assert resp.status_code == 200
        rows = resp.json()["data"]
        assert len(rows) == 1
        assert all(str(customer_b) not in str(r) for r in rows)
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        await _cleanup(customer_a, customer_b)


@pytest.mark.asyncio
async def test_customer_identity_comes_from_jwt_not_a_query_param():
    """There is no `customer_id` (or similar) query param on the list route
    at all -- confirms a customer cannot override whose requests they see
    by crafting a request; the route signature only accepts `status`."""
    customer_a = uuid.uuid4()
    headers = {"Authorization": "Bearer x"}
    try:
        await _seed_complaint(customer_a, uuid.uuid4(), uuid.uuid4())
        other_id = uuid.uuid4()

        app.dependency_overrides[get_current_user] = lambda: _customer_ctx(customer_a)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get(f"/v1/customer/complaints?customer_id={other_id}", headers=headers)
        assert resp.status_code == 200
        rows = resp.json()["data"]
        # The bogus `customer_id` query param is silently ignored (not a
        # real field on the route) -- the authenticated customer's own
        # complaint is still the only one returned.
        assert len(rows) == 1
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        await _cleanup(customer_a)


@pytest.mark.asyncio
async def test_list_response_never_leaks_internal_admin_identity():
    """Live proof of this phase's model-level fix
    (`CustomerComplaint.to_customer_dict`)."""
    customer_a = uuid.uuid4()
    headers = {"Authorization": "Bearer x"}
    try:
        await _seed_complaint(customer_a, uuid.uuid4(), uuid.uuid4())
        app.dependency_overrides[get_current_user] = lambda: _customer_ctx(customer_a)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/v1/customer/complaints", headers=headers)
        rows = resp.json()["data"]
        assert len(rows) == 1
        assert "assigned_admin_user_id" not in rows[0]
        assert "internal_admin_notes" not in rows[0]
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        await _cleanup(customer_a)
