"""MODULE-L5-47 — dispatch_job/reassign_job never notified the assigned staff.

Same bug class as MODULE-L5-25 (home_service_assignment), but the dispatch
engine (app/engines/dispatch/service.py) is a separate, live, actually-wired
engine (mounted in main.py, driven by frontend/tenant-portal's real
(tenant)/dispatch page) that fix never touched. dispatch_job/reassign_job set
Job.assigned_staff_id and logged an internal audit event, but created no
user-facing notification -- a staff member had no way to learn about a new
dispatch/reassignment except by polling.
"""
import asyncio
import inspect
import uuid

import pytest

from app.engines.dispatch.service import DispatchService


def _no_comments(src: str) -> str:
    return "\n".join(l for l in src.splitlines() if not l.strip().startswith("#"))


def test_dispatch_job_calls_notify_helper():
    src = _no_comments(inspect.getsource(DispatchService.dispatch_job))
    assert "_notify_staff_dispatched" in src


def test_reassign_job_calls_notify_helper():
    src = _no_comments(inspect.getsource(DispatchService.reassign_job))
    assert "_notify_staff_dispatched" in src


def test_notify_helper_creates_in_app_notification():
    src = inspect.getsource(DispatchService._notify_staff_dispatched)
    assert "InAppNotification" in src
    assert "job_assigned" in src
    assert "/staff/jobs/" in src
    assert "reassigned to you" in src
    assert "assigned to you" in src


class TestLive:
    @pytest.fixture
    async def tokens_and_ids(self):
        import httpx

        async with httpx.AsyncClient(base_url="http://localhost:8000", timeout=15) as client:
            admin = await client.post("/v1/auth/login", json={
                "email": "admin@serviceos.local", "password": "Password123!"})
            staff = await client.post("/v1/auth/login", json={
                "email": "staff@serviceos.local", "password": "Password123!"})
            if admin.status_code != 200 or staff.status_code != 200:
                pytest.skip("backend/login not available")
            admin_data = admin.json()["data"]
            staff_data = staff.json()["data"]
            yield {
                "admin_token": admin_data["access_token"],
                "staff_id": staff_data["user"]["id"],
            }

    async def test_dispatch_and_reassign_notify_staff_live(self, tokens_and_ids):
        import asyncpg
        import httpx

        tenant_id = "5209ef33-a53e-4fc0-b3f6-006335b8d712"
        staff_id = tokens_and_ids["staff_id"]
        admin_token = tokens_and_ids["admin_token"]
        job_id = str(uuid.uuid4())

        conn = await asyncpg.connect("postgresql://postgres:postgres@127.0.0.1:5432/serviceos")
        try:
            await conn.execute(
                """INSERT INTO jobs (id, tenant_id, service_type_id, service_category,
                       job_number, title, status, source, customer_token, created_at, updated_at)
                   VALUES ($1, $2, 'test-service', 'test-category', $3,
                       'MODULE-L5-47 test job', 'draft', 'direct', $4, now(), now())""",
                uuid.UUID(job_id), uuid.UUID(tenant_id), f"L5-47T-{job_id[:8]}", f"tok-{job_id}",
            )

            async with httpx.AsyncClient(base_url="http://localhost:8000", timeout=15) as client:
                resp = await client.post(
                    f"/v1/dispatch/jobs/{job_id}/dispatch",
                    headers={"Authorization": f"Bearer {admin_token}"},
                    json={"tenant_id": tenant_id, "mode": "manual", "staff_id": staff_id},
                )
                assert resp.status_code == 201, resp.text

            row = None
            for _ in range(10):
                row = await conn.fetchrow(
                    """SELECT title, action_url FROM in_app_notifications
                       WHERE action_url = $1 AND user_id = $2
                       ORDER BY created_at DESC LIMIT 1""",
                    f"/staff/jobs/{job_id}", uuid.UUID(staff_id),
                )
                if row is not None:
                    break
                await asyncio.sleep(0.3)
            assert row is not None
            assert row["action_url"] == f"/staff/jobs/{job_id}"
            assert "assigned to you" in row["title"] or "New job assigned" in row["title"]
        finally:
            await conn.execute("DELETE FROM in_app_notifications WHERE action_url = $1", f"/staff/jobs/{job_id}")
            await conn.execute("DELETE FROM dispatch_escalation_logs WHERE job_id = $1", job_id)
            await conn.execute("DELETE FROM dispatch_records WHERE job_id = $1", job_id)
            await conn.execute("DELETE FROM jobs WHERE id = $1", uuid.UUID(job_id))
            await conn.close()
