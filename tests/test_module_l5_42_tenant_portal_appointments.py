"""MODULE-L5-42 — the tenant-portal Appointments page showed nothing (called a
route that requires a path param it never supplied), and the whole appointmentApi
client used wrong routes.

Found via the openapi-vs-frontend audit (L5-39/40/41 lineage). The Appointments
page (frontend/tenant-portal/app/(tenant)/appointments/page.tsx) fetched
GET /v1/appointments/staff?... -- but the real appointment engine only lists
per staff (/v1/appointments/staff/{staff_id}) or per customer, with no
tenant-wide list. The correct tenant-wide list is
GET /v1/provider/my-records/appointments (final_records/provider_router),
returning {items, total, limit, offset}. The page also read `.appointments`
off the response (real key is `.items`) and rendered columns that don't exist
on CoachingAppointment (appointment_type/scheduled_date/scheduled_time/
duration_minutes vs the real student_name/target_exam/selected_date/
selected_time_start).

Separately, the entire appointmentApi object in lib/api.ts (unused by any
page, but a latent trap) called 6 nonexistent routes -- staff/customer list,
slots, calendar block/unblock, working-hours -- all corrected to the real
path-param routes.

Fixed the page's fetchFn/wrapLegacy/columns and every appointmentApi route.
Verified live: the real /v1/provider/my-records/appointments returns
{items,total,limit,offset}; the old /v1/appointments/staff query call fails.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from httpx import AsyncClient

ROOT = Path(__file__).resolve().parents[1]
API_TS = ROOT / "frontend/tenant-portal/lib/api.ts"
PAGE = ROOT / "frontend/tenant-portal/app/(tenant)/appointments/page.tsx"

BASE = "http://localhost:8000"
PROVIDER_EMAIL = "provider@serviceos.local"
PASSWORD = "Password123!"


def _live(text: str) -> str:
    return "\n".join(l for l in text.splitlines()
                      if not l.strip().startswith("//") and not l.strip().startswith("*"))


def test_page_uses_the_real_tenant_wide_list():
    src = _live(PAGE.read_text(encoding="utf-8"))
    assert "/v1/provider/my-records/appointments" in src
    assert "/v1/appointments/staff?" not in src
    # reads the real response key + real record fields
    assert "?.items ?? d" in src
    for real in ("student_name", "target_exam", "selected_date", "selected_time_start"):
        assert real in src
    for dead in ("appointment_type", "scheduled_time", "duration_minutes"):
        assert dead not in src


def test_appointment_api_routes_carry_path_params():
    block = _live(API_TS.read_text(encoding="utf-8").split("export const appointmentApi")[1].split("\n};")[0])
    assert "/v1/appointments/staff/${staffId}" in block
    assert "/v1/appointments/customers/${customerId}" in block
    assert "/v1/appointments/staff/${staffId}/slots" in block
    assert "/v1/appointments/calendar/blocks/${blockId}" in block
    # dead route forms gone
    for dead in ("/v1/appointments/staff?", "/v1/appointments/customer?",
                 "/v1/appointments/slots/available", "/v1/appointments/working-hours\"",
                 "/v1/appointments/calendar/block\"", "/v1/appointments/calendar/block/${"):
        assert dead not in block, f"dead route still present: {dead}"


async def _login(email):
    async with AsyncClient(base_url=BASE, timeout=30) as c:
        r = await c.post("/v1/auth/login", json={"email": email, "password": PASSWORD})
        return r.json()["data"]["access_token"] if r.status_code == 200 else None


class TestLive:
    async def test_real_appointments_list_endpoint(self):
        tok = await _login(PROVIDER_EMAIL)
        if not tok:
            pytest.skip("provider login unavailable")
        async with AsyncClient(base_url=BASE, timeout=30,
                               headers={"Authorization": f"Bearer {tok}"}) as c:
            real = await c.get("/v1/provider/my-records/appointments?limit=5&offset=0")
            assert real.status_code == 200, real.text
            d = real.json()["data"]
            for k in ("items", "total", "limit", "offset"):
                assert k in d

            # the old page call did not return a valid appointments list
            dead = await c.get("/v1/appointments/staff?tenant_id=5209ef33-a53e-4fc0-b3f6-006335b8d712")
            assert dead.status_code != 200
