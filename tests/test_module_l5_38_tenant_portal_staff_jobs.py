"""MODULE-L5-38 — the tenant-portal's technician web pages showed zero jobs
(pointed at the dead field_ops staff router), the direct parallel of the
staff-app mobile fix in MODULE-L5-36.

The tenant-portal /staff/* section (technician self-service web UI) called
staffSelfApi.getMyJobs / getJobDetail -> /v1/staff/me/jobs, the field_ops
staff router whose `jobs` table has 0 rows platform-wide. A technician logging
into the web portal saw zero jobs, an all-disabled "Job Actions" card, and
stale "not certified for this app yet" copy. The real, live-verified
/v1/staff/service-jobs pipeline (home_service_assignment + execution) was
already exposed as homeServiceStaffJobsApi -- the pages just weren't using it.

Also fixed a latent bug in the parallel /staff/home-services/jobs/[job_id]
page: it already called homeServiceStaffJobsApi.get() but treated the response
as a flat job, while the endpoint returns {job, assignment, booking} -- so
every job field rendered undefined at runtime. Corrected the .get() TS type to
HomeServiceJobDetail and derived the job from it.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from httpx import AsyncClient

ROOT = Path(__file__).resolve().parents[1]
API_TS = ROOT / "frontend/tenant-portal/lib/api.ts"
JOBS_PAGE = ROOT / "frontend/tenant-portal/app/staff/jobs/page.tsx"
DETAIL_PAGE = ROOT / "frontend/tenant-portal/app/staff/jobs/[job_id]/page.tsx"
DASH_PAGE = ROOT / "frontend/tenant-portal/app/staff/dashboard/page.tsx"

BASE = "http://localhost:8000"
STAFF_EMAIL = "staff@serviceos.local"
PASSWORD = "Password123!"


def _live(text: str) -> str:
    return "\n".join(l for l in text.splitlines()
                      if not l.strip().startswith("//") and not l.strip().startswith("*"))


def test_staff_web_pages_use_real_service_jobs_api():
    for page in (JOBS_PAGE, DETAIL_PAGE, DASH_PAGE):
        src = _live(page.read_text(encoding="utf-8"))
        assert "homeServiceStaffJobsApi" in src, f"{page} not repointed"
        assert "staffSelfApi.getMyJobs" not in src, f"{page} still calls dead field_ops list"
        assert "staffSelfApi.getJobDetail" not in src, f"{page} still calls dead field_ops detail"


def test_detail_page_wires_real_lifecycle_actions():
    src = DETAIL_PAGE.read_text(encoding="utf-8")
    # the disabled "not certified" placeholder actions are gone
    assert "Not certified in this phase" not in src
    for action in ("accept", "onTheWay", "reachedSite", "startService", "complete"):
        assert action in src


def test_get_returns_the_nested_detail_shape():
    src = API_TS.read_text(encoding="utf-8")
    assert "HomeServiceJobDetail" in src
    assert "unwrapStaffJobResult" in src


async def _login(email):
    async with AsyncClient(base_url=BASE, timeout=30) as c:
        r = await c.post("/v1/auth/login", json={"email": email, "password": PASSWORD})
        return r.json()["data"]["access_token"] if r.status_code == 200 else None


class TestLive:
    async def test_dead_and_real_staff_job_endpoints(self):
        tok = await _login(STAFF_EMAIL)
        if not tok:
            pytest.skip("staff login unavailable")
        async with AsyncClient(base_url=BASE, timeout=30,
                               headers={"Authorization": f"Bearer {tok}"}) as staff:
            me = await staff.get("/v1/auth/me")
            tid = me.json()["data"]["tenant_id"]

            # dead field_ops endpoint: always empty
            dead = await staff.get(f"/v1/staff/me/jobs?tenant_id={tid}")
            assert dead.status_code == 200
            assert dead.json()["data"]["jobs"] == []

            # real endpoint: the live-connected one the pages now use
            real = await staff.get("/v1/staff/service-jobs")
            assert real.status_code == 200
            assert "jobs" in real.json()["data"]
            assert "count" in real.json()["data"]
