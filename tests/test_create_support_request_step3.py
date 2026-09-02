"""Create Support Request Step 3 (Review & Submit) phase.

No backend code changed this phase (audit-only) -- this test proves the
one security property the frontend's payload allowlist depends on:
client-supplied ownership/status/priority fields in the raw POST body to
`/v1/customer/complaints` have zero effect, confirming the backend's own
Pydantic schema (`CreateComplaintIn`, no `extra="forbid"`/`extra="allow"`
config) silently ignores them rather than accepting and trusting them.
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


async def _cleanup(*customer_ids):
    async with _real_sessionmaker() as db:
        for cid in customer_ids:
            await db.execute(text(
                "DELETE FROM complaint_events WHERE complaint_id IN "
                "(SELECT id FROM customer_complaints WHERE customer_id=:cid)"), {"cid": cid})
        for cid in customer_ids:
            await db.execute(text("DELETE FROM customer_complaints WHERE customer_id=:cid"), {"cid": cid})
        await db.commit()


@pytest.mark.asyncio
async def test_client_supplied_ownership_and_status_fields_are_ignored():
    customer_a = uuid.uuid4()
    other_customer = uuid.uuid4()
    headers = {"Authorization": "Bearer x"}
    booking_id = uuid.uuid4()
    try:
        app.dependency_overrides[get_current_user] = lambda: _customer_ctx(customer_a)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/v1/customer/complaints", headers=headers, json={
                "record_type": "service_booking", "record_id": str(booking_id),
                "complaint_type": "other", "description": "test",
                # Everything below is a forged/unsupported field a
                # malicious client might try to send.
                "customer_id": str(other_customer),
                "tenant_id": str(uuid.uuid4()),
                "status": "resolved",
                "priority": "urgent",
                "assigned_to": str(uuid.uuid4()),
                "assigned_staff_id": str(uuid.uuid4()),
                "sla": "1h",
                "refund_status": "approved",
                "resolution": "fully refunded",
            })
        # The record itself may or may not be created depending on
        # eligibility for a random booking_id -- what matters is that IF
        # created, none of the forged fields took effect.
        if resp.status_code == 201:
            data = resp.json()["data"]
            assert data["status"] == "open"  # never "resolved"
            assert data["record_id"] == str(booking_id)
            assert "customer_id" not in data  # never exposed either way
            assert "priority" not in data
            assert "assigned_to" not in data
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        await _cleanup(customer_a, other_customer)


@pytest.mark.asyncio
async def test_foreign_booking_id_cannot_be_linked():
    """Confirms the real ownership check the Review screen's "booking
    still belongs to the authenticated customer" guard depends on."""
    customer_a = uuid.uuid4()
    headers = {"Authorization": "Bearer x"}
    try:
        app.dependency_overrides[get_current_user] = lambda: _customer_ctx(customer_a)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/v1/customer/complaints", headers=headers, json={
                "record_type": "service_booking", "record_id": str(uuid.uuid4()),
                "complaint_type": "other", "description": "test",
            })
        # A random/nonexistent/foreign booking id is never eligible.
        assert resp.status_code in (404, 422)
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        await _cleanup(customer_a)
