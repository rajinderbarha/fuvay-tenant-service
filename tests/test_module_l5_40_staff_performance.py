"""MODULE-L5-40 — staff performance was broken on two surfaces (wrong route +
wrong shape), found via the same openapi-vs-frontend audit as L5-39.

Both the tenant-portal manager staff-detail page (staffApi.getPerformance)
and the staff-app mobile Profile screen (staffApi.performance) called
GET /v1/ds/staff/{id}/performance -- a route that does not exist (404). The
real route is /v1/ds/tenants/{tenant_id}/staff/{staff_id}/score. The
StaffPerformance TS interface was also wrong on both: it modeled
{signals, job_count, avg_rating, dispute_rate, on_time_rate}, but the real
get_staff_score returns {signal_values, jobs_completed, avg_customer_rating,
sla_adherence_rate, rank, composite_score, observation_mode, computed_at}.

Fixed the route (adds tenant_id) and the interface + every consumer field on
both surfaces. Verified live: seeded a staff_performance_scores row and
confirmed the real /score endpoint returns exactly the corrected shape.
"""
from __future__ import annotations

import os
import uuid
from pathlib import Path

import pytest
from httpx import AsyncClient

ROOT = Path(__file__).resolve().parents[1]
TP_API = ROOT / "frontend/tenant-portal/lib/api.ts"
MOBILE_API = ROOT / "mobile/staff-app/src/lib/api.ts"
TP_PAGE = ROOT / "frontend/tenant-portal/app/(tenant)/staff/[id]/page.tsx"
MOBILE_PROFILE = ROOT / "mobile/staff-app/src/screens/profile/ProfileScreen.tsx"

BASE = "http://localhost:8000"
STAFF_EMAIL = "staff@serviceos.local"
PASSWORD = "Password123!"
STAFF_ID = "22d123b7-2962-4d7f-9678-24510683b1af"
TENANT_ID = "5209ef33-a53e-4fc0-b3f6-006335b8d712"


def _live(text: str) -> str:
    return "\n".join(l for l in text.splitlines()
                      if not l.strip().startswith("//") and not l.strip().startswith("*"))


def test_both_clients_use_the_real_score_route():
    for api in (TP_API, MOBILE_API):
        src = _live(api.read_text(encoding="utf-8"))
        assert "/staff/${id}/score" in src or "/staff/${id}/score`" in src or "staff/${id}/score" in src
        assert "/ds/staff/${id}/performance" not in src


def test_staff_performance_interface_matches_backend():
    for api in (TP_API, MOBILE_API):
        src = api.read_text(encoding="utf-8")
        block = src.split("interface StaffPerformance")[1].split("}")[0]
        for real in ("signal_values", "jobs_completed", "avg_customer_rating", "sla_adherence_rate"):
            assert real in block, f"{api}: missing {real}"
        for dead in ("on_time_rate", "job_count", "dispute_rate"):
            assert dead not in block, f"{api}: still has {dead}"


def test_tenant_performance_consumer_uses_real_fields():
    src = _live(TP_PAGE.read_text(encoding="utf-8"))
    assert "signal_values" in src
    for dead in (".on_time_rate", ".job_count", ".avg_rating", ".dispute_rate", ".signals"):
        assert dead not in src


def test_mobile_profile_does_not_fabricate_performance_fields():
    src = _live(MOBILE_PROFILE.read_text(encoding="utf-8"))
    for dead in (".on_time_rate", ".job_count", ".avg_rating", ".dispute_rate", ".signals"):
        assert dead not in src


async def _login(email):
    async with AsyncClient(base_url=BASE, timeout=30) as c:
        r = await c.post("/v1/auth/login", json={"email": email, "password": PASSWORD})
        return r.json()["data"]["access_token"] if r.status_code == 200 else None


@pytest.mark.skipif(
    os.getenv("RUN_LIVE_SERVER_TESTS") != "1",
    reason="requires the API and PostgreSQL services to be running",
)
class TestLive:
    async def test_dead_route_404s_and_real_route_returns_the_shape(self):
        tok = await _login(STAFF_EMAIL)
        if not tok:
            pytest.skip("staff login unavailable")
        import asyncpg
        conn = await asyncpg.connect("postgresql://serviceos:serviceos@127.0.0.1:5432/serviceos")
        import json
        try:
            await conn.execute(
                """INSERT INTO staff_performance_scores
                   (id, staff_id, tenant_id, composite_score, rank_in_tenant, signal_values,
                    jobs_completed, avg_customer_rating, sla_adherence_rate, observation_mode,
                    computed_at, created_at, updated_at)
                   VALUES ($1,$2,$3,82.5,2,$4,14,4.6,91.0,false,now(),now(),now())
                   ON CONFLICT DO NOTHING""",
                uuid.uuid4(), uuid.UUID(STAFF_ID), uuid.UUID(TENANT_ID),
                json.dumps({"quality": 80.0}))
            async with AsyncClient(base_url=BASE, timeout=30,
                                   headers={"Authorization": f"Bearer {tok}"}) as staff:
                dead = await staff.get(f"/v1/ds/staff/{STAFF_ID}/performance")
                assert dead.status_code == 404

                real = await staff.get(f"/v1/ds/tenants/{TENANT_ID}/staff/{STAFF_ID}/score")
                assert real.status_code == 200
                d = real.json()["data"]
                for k in ("composite_score", "signal_values", "jobs_completed",
                          "avg_customer_rating", "sla_adherence_rate", "rank"):
                    assert k in d
        finally:
            await conn.execute("DELETE FROM staff_performance_scores WHERE staff_id=$1",
                               uuid.UUID(STAFF_ID))
            await conn.close()
