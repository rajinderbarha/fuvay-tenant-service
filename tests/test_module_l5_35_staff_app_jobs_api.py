"""MODULE-L5-35 — staff-app mobile jobsApi had three confirmed mismatches
against the real field_ops backend.

Continuation of MODULE-L5-00-004 (staff_app_mobile least-certified surface),
following MODULE-L5-33 (earnings) and MODULE-L5-34 (chat).

1. jobsApi.myJobs() never sent tenant_id. GET /v1/jobs 422s with
   TENANT_REQUIRED for any non-super_admin caller that omits it (the router
   gates on its mere presence before the service ever runs, even though the
   service then re-derives both tenant_id and staff scoping from the
   authenticated actor for staff/technician roles and ignores whatever the
   client sent). Verified live: 422 without tenant_id, 200 with it.
2. The query param name was assigned_staff_id; the real param is staff_id
   (silently dropped by the server rather than erroring -- moot for staff
   role since the server always overrides it, but wrong).
3. jobsApi.updateStatus() sent {status, notes}; the router does
   `body["to_status"]` (a raw dict index, not .get() -- KeyError on any
   request missing that exact key) and reads body.get("reason"), not
   "notes". Every status-transition attempt from this app would raise.
4. jobsApi.close() sent {closing_notes}; the router reads
   body.get("closure_notes") -- didn't crash (safe .get()) but silently
   dropped every closing note the technician typed.

Fix: corrected all four in mobile/staff-app/src/lib/api.ts.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from httpx import AsyncClient

API_TS = Path("mobile/staff-app/src/lib/api.ts")
BASE = "http://localhost:8000"
STAFF_EMAIL = "staff@serviceos.local"
PASSWORD = "Password123!"


def _job_block(src: str) -> str:
    block = src.split("export const jobsApi")[1].split("\n};")[0]
    return "\n".join(l for l in block.splitlines() if not l.strip().startswith("//"))


def test_myjobs_sends_tenant_id_and_correct_staff_param():
    block = _job_block(API_TS.read_text(encoding="utf-8"))
    assert "getTenantId" in block
    assert "staff_id:id" in block
    assert "assigned_staff_id" not in block


def test_update_status_uses_the_real_field_names():
    block = _job_block(API_TS.read_text(encoding="utf-8"))
    assert "to_status:status" in block
    assert "reason:notes" in block


def test_close_uses_the_real_field_name():
    block = _job_block(API_TS.read_text(encoding="utf-8"))
    assert "closure_notes:notes" in block
    assert "closing_notes:notes" not in block


async def _login(email):
    async with AsyncClient(base_url=BASE, timeout=30) as c:
        r = await c.post("/v1/auth/login", json={"email": email, "password": PASSWORD})
        return r.json()["data"]["access_token"] if r.status_code == 200 else None


class TestLive:
    async def test_jobs_list_422s_without_tenant_id_and_succeeds_with_it(self):
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
