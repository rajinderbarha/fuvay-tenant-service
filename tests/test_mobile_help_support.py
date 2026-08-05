"""Technician mobile app Phase Y: reuses the EXISTING, real Tenant Help &
Support engine (app/engines/support/) end-to-end for a technician caller --
confirmed by audit that `get_current_user` (any authenticated role,
including technician) already reaches `/v1/tenant/support/*` with the
"technician" role already granted `SUPPORT_REQUESTS_*` permissions. This
phase adds ZERO new backend routes -- only migration 218 seeding real,
technician-scoped knowledge-base content into the existing model.
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


def _ctx(user_id, tenant_id):
    return UserContext(user_id=str(user_id), email="tech@serviceos.local", role="technician",
                        tenant_id=str(tenant_id), full_name="Demo Technician", is_verified=True)


@pytest.mark.asyncio
async def test_workspace_denies_no_tenant_context():
    app.dependency_overrides[get_current_user] = lambda: UserContext(
        user_id=str(uuid.uuid4()), email="tech@serviceos.local", role="technician",
        tenant_id=None, full_name="No Tenant", is_verified=True,
    )
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/v1/tenant/support/workspace", headers={"Authorization": "Bearer x"})
        assert resp.status_code == 403
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_seeded_technician_knowledge_articles_are_real_and_published():
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    try:
        app.dependency_overrides[get_current_user] = lambda: _ctx(user_id, tenant_id)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/v1/tenant/support/knowledge?role=technician", headers={"Authorization": "Bearer x"})
            assert resp.status_code == 200
            data = resp.json()["data"]
            slugs = {a["slug"] for a in data["articles"]}
            assert "tech-sign-in-mfa" in slugs
            assert "tech-schedule-leave" in slugs
            assert len(data["featured"]) > 0
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_technician_full_ticket_lifecycle_live():
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    ticket_id = None
    try:
        headers = {"Authorization": "Bearer x"}
        app.dependency_overrides[get_current_user] = lambda: _ctx(user_id, tenant_id)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # 1. Workspace load -- real quick-help/service-status/form-options for a technician.
            workspace = (await client.get("/v1/tenant/support/workspace", headers=headers)).json()["data"]
            assert workspace["service_status"]["state"] in ("operational", "degraded", "major_incident", "maintenance", "unavailable")
            assert any(c["key"] == "bookings_jobs" for c in workspace["quick_help"])
            assert workspace["permissions"]["can_create"] is True

            # 2. Submit a real technical-problem ticket.
            submit = await client.post("/v1/tenant/support/requests", headers=headers, json={
                "category": "technical", "subject": "Job photo upload failed",
                "description": "Photo upload keeps failing on job completion.",
                "impact": "one_user_affected",
            })
            assert submit.status_code == 200
            ticket_id = submit.json()["data"]["id"]

            # 3. Detail view real, shows the ticket the technician created.
            detail = (await client.get(f"/v1/tenant/support/requests/{ticket_id}", headers=headers)).json()["data"]
            assert detail["subject"] == "Job photo upload failed"

            # 4. Technician can reply on their own ticket.
            reply = await client.post(f"/v1/tenant/support/requests/{ticket_id}/messages", headers=headers, json={"body": "Still failing after retry."})
            assert reply.status_code == 200

            # 5. Technician CANNOT confirm a resolution that hasn't happened -- self-resolve is not possible.
            premature_confirm = await client.post(f"/v1/tenant/support/requests/{ticket_id}/confirm-resolution", headers=headers)
            assert premature_confirm.status_code == 409

        # 6. Cross-tenant technician denied (404, not a hint the ticket exists).
        other_tenant = uuid.uuid4()
        other_user = uuid.uuid4()
        app.dependency_overrides[get_current_user] = lambda: _ctx(other_user, other_tenant)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            cross = await client.get(f"/v1/tenant/support/requests/{ticket_id}", headers=headers)
            assert cross.status_code == 404
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        if ticket_id:
            async with _real_sessionmaker() as db:
                await db.execute(text("DELETE FROM support_ticket_messages WHERE ticket_id=:tid"), {"tid": ticket_id})
                await db.execute(text("DELETE FROM support_ticket_events WHERE ticket_id=:tid"), {"tid": ticket_id})
                await db.execute(text("DELETE FROM support_tickets WHERE id=:tid"), {"tid": ticket_id})
                await db.commit()
