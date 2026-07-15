"""MODULE-L5-31 — large-row-count exports were permanently failed instead of
queued for the async worker that already exists.

Gap register carried forward "async export worker" as NOT_RE-VERIFIED.
Investigation found the worker itself (app/jobs/export_worker.py, started in
main.py's lifespan) is real and running — it claims pending jobs via
`SELECT ... FOR UPDATE SKIP LOCKED`, generates the file, and every resource
adapter query is capped at MAX_EXPORT_ROWS=5000 regardless of what the caller
estimates. But ExportService.create_export_job still contained an older gate
(predating the worker) that immediately set status=failed with
EXPORT_ASYNC_REQUIRED whenever estimated_row_count exceeded 5000 — a request
that could always be safely processed (since the adapter caps it anyway) was
permanently rejected before it ever reached the worker's pending queue.

Fix: removed the dead gate. Every export now queues as pending; the already-
running worker picks it up regardless of the caller's row estimate.
"""
from __future__ import annotations

import asyncio
import uuid

import pytest
from httpx import AsyncClient

BASE = "http://localhost:8000"
ADMIN_EMAIL = "admin@serviceos.local"
PASSWORD = "Password123!"


def test_large_estimate_no_longer_fails_the_job_closed():
    import inspect
    from app.engines.enterprise_grid import services
    src = inspect.getsource(services.ExportService.create_export_job)
    # the old dead gate raised this code; it must no longer be reachable code
    # (only comment text explaining the historical bug may mention it)
    live_lines = [l for l in src.splitlines() if not l.strip().startswith("#")]
    assert not any("EXPORT_ASYNC_REQUIRED" in l for l in live_lines)
    assert any("EXPORT_PENDING" in l for l in live_lines)


async def _login(email):
    async with AsyncClient(base_url=BASE, timeout=30) as c:
        r = await c.post("/v1/auth/login", json={"email": email, "password": PASSWORD})
        return r.json()["data"]["access_token"] if r.status_code == 200 else None


class TestExportWorkerLive:
    async def test_large_export_is_picked_up_and_completed_by_the_worker(self):
        tok = await _login(ADMIN_EMAIL)
        if not tok:
            pytest.skip("admin login unavailable")
        async with AsyncClient(base_url=BASE, timeout=30,
                               headers={"Authorization": f"Bearer {tok}"}) as admin:
            r = await admin.post("/v1/enterprise/exports", json={
                "resource_key": "admin_tenants",
                "filters": {},
                "columns": [],
                "export_format": "csv",
                "estimated_row_count": 999999,
                "idempotency_key": f"l5-31-{uuid.uuid4().hex}",
            })
            if r.status_code == 429:
                pytest.skip("export rate/concurrency limit hit — not this test's concern")
            assert r.status_code == 201, r.text
            job = r.json()["data"]
            assert job["status"] == "pending"

            final = None
            for _ in range(20):
                await asyncio.sleep(1)
                s = await admin.get(f"/v1/enterprise/exports/{job['id']}")
                assert s.status_code == 200
                final = s.json()["data"]
                if final["status"] in ("completed", "failed"):
                    break

            assert final is not None
            assert final["status"] != "pending", "worker never picked up the job within 20s"
            assert final["status"] == "completed", final.get("failure_reason")
            assert final.get("downloadable") is True
