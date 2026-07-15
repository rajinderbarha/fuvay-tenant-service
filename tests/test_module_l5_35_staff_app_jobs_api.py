"""MODULE-L5-35 — staff-app mobile jobsApi had confirmed mismatches against
the field_ops backend (missing tenant_id, wrong body field names on
status/close).

Superseded by MODULE-L5-36: field_ops was subsequently confirmed to be dead
scaffolding (0 rows platform-wide) and the entire jobsApi surface was
rewired to the real service_jobs pipeline (see
tests/test_module_l5_36_staff_app_service_jobs.py for current source-level
assertions). The field_ops-specific fixes this file asserted (myJobs
tenant_id/staff_id params, updateStatus to_status/reason, close
closure_notes) no longer apply since those functions don't exist anymore.

The live backend behavior confirmed here (GET /v1/jobs, field_ops' own list
endpoint, still 422s TENANT_REQUIRED without tenant_id) remains true of that
endpoint in isolation and is kept as a historical confirmation, though the
mobile app itself no longer calls it.
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient

BASE = "http://localhost:8000"
STAFF_EMAIL = "staff@serviceos.local"
PASSWORD = "Password123!"


async def _login(email):
    async with AsyncClient(base_url=BASE, timeout=30) as c:
        r = await c.post("/v1/auth/login", json={"email": email, "password": PASSWORD})
        return r.json()["data"]["access_token"] if r.status_code == 200 else None


class TestLive:
    async def test_field_ops_jobs_list_422s_without_tenant_id_and_succeeds_with_it(self):
        tok = await _login(STAFF_EMAIL)
        if not tok:
            pytest.skip("staff login unavailable")
        async with AsyncClient(base_url=BASE, timeout=30,
                               headers={"Authorization": f"Bearer {tok}"}) as staff:
            without = await staff.get("/v1/jobs?limit=5")
            assert without.status_code == 422
            assert without.json()["error_code"] == "TENANT_REQUIRED"

            me = await staff.get("/v1/auth/me")
            tenant_id = me.json()["data"]["tenant_id"]
            withit = await staff.get(f"/v1/jobs?tenant_id={tenant_id}&limit=5")
            assert withit.status_code == 200
