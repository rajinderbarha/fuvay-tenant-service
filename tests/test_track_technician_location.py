"""TRACK-TECHNICIAN — real technician GPS location, submitted by the
assigned technician and read only by the owning customer while the job is
in an active-tracking status.

Confirmed via audit before this module: no live-location capability existed
anywhere in the canonical ServiceBooking/ServiceJob pipeline (only a
one-shot lat/lng capture on the disconnected/dead field_ops.Job table, and
no realtime/WebSocket/SSE infrastructure exists in this backend at all —
everything is HTTP polling). No ETA/routing service exists either, so none
is computed or exposed.

Fix: new `technician_live_locations` table (migration 225, one row per job,
overwritten in place — no position history). Submission:
PUT /v1/staff/service-jobs/{job_id}/location (technician's own device, only
while job.status is in TRACKING_ACTIVE_JOB_STATUSES). Read:
GET /v1/customer/bookings/{booking_id}/tracking-location (ownership-checked,
returns available=false with a reason whenever the job isn't actively
trackable or no location has been submitted yet — never a stale/fabricated
position).
"""
from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient

BASE = "http://localhost:8000"
CUSTOMER_EMAIL = "customer@serviceos.local"
STAFF_EMAIL = "staff@serviceos.local"
PASSWORD = "Password123!"


async def _login(email):
    async with AsyncClient(base_url=BASE, timeout=30) as c:
        r = await c.post("/v1/auth/login", json={"email": email, "password": PASSWORD})
        return r.json()["data"]["access_token"] if r.status_code == 200 else None


def test_tracking_active_statuses_are_real_execution_engine_values():
    """on_the_way must be the exact literal execution/constants.py JS_ON_THE_WAY
    writes to ServiceJob.status — not a guessed value."""
    from app.engines.home_service_assignment.constants import TRACKING_ACTIVE_JOB_STATUSES
    from app.engines.execution.constants import JS_ON_THE_WAY
    assert JS_ON_THE_WAY in TRACKING_ACTIVE_JOB_STATUSES
    assert "completed" not in TRACKING_ACTIVE_JOB_STATUSES
    assert "cancelled" not in TRACKING_ACTIVE_JOB_STATUSES


class TestTrackTechnicianLive:
    async def _seed(self, job_status: str):
        import asyncpg
        c = await asyncpg.connect("postgresql://serviceos:serviceos@127.0.0.1:5432/serviceos")
        try:
            tmpl = await c.fetchrow(
                "SELECT sj.booking_id, sj.tenant_id, sj.customer_id, sb.category_id, sb.offering_id "
                "FROM service_jobs sj JOIN service_bookings sb ON sb.id = sj.booking_id "
                "WHERE sj.customer_id IS NOT NULL LIMIT 1")
            if not tmpl:
                return None
            cust_email = await c.fetchval("SELECT email FROM users WHERE id=$1", tmpl["customer_id"])
            staff_id = await c.fetchval("SELECT id FROM users WHERE email=$1", STAFF_EMAIL)
            if not staff_id:
                return None
            jid, bid = uuid.uuid4(), uuid.uuid4()
            await c.execute(
                """INSERT INTO service_bookings
                   (id,booking_number,draft_id,customer_id,tenant_id,category_id,offering_id,
                    status,assignment_status,created_at,updated_at)
                   VALUES ($1,$2,$3,$4,$5,$6,$7,$8,'accepted',now(),now())""",
                bid, f"BK-TRK-{uuid.uuid4().hex[:6]}", uuid.uuid4(), tmpl["customer_id"],
                tmpl["tenant_id"], tmpl["category_id"], tmpl["offering_id"], job_status)
            await c.execute(
                """INSERT INTO service_jobs
                   (id,job_number,booking_id,customer_id,tenant_id,category_id,offering_id,
                    assigned_staff_id,status,assignment_status,created_at,updated_at)
                   VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,'accepted',now(),now())""",
                jid, f"JOB-TRK-{uuid.uuid4().hex[:6]}", bid, tmpl["customer_id"],
                tmpl["tenant_id"], tmpl["category_id"], tmpl["offering_id"], staff_id, job_status)
            return {"booking_id": str(bid), "job_id": str(jid), "customer_email": cust_email}
        finally:
            await c.close()

    async def test_no_location_yet_is_available_false(self):
        info = await self._seed("accepted")
        if not info or not info["customer_email"]:
            pytest.skip("no suitable job/customer/staff to seed against")
        tok = await _login(info["customer_email"])
        if not tok:
            pytest.skip("customer login unavailable")
        async with AsyncClient(base_url=BASE, timeout=30,
                               headers={"Authorization": f"Bearer {tok}"}) as cust:
            r = await cust.get(f"/v1/customer/bookings/{info['booking_id']}/tracking-location")
            assert r.status_code == 200, r.text
            data = r.json()["data"]
            assert data["available"] is False
            assert data["reason"] == "location_unavailable"

    async def test_technician_submits_then_customer_reads_real_location(self):
        info = await self._seed("accepted")
        if not info or not info["customer_email"]:
            pytest.skip("no suitable job/customer/staff to seed against")
        staff_tok = await _login(STAFF_EMAIL)
        cust_tok = await _login(info["customer_email"])
        if not staff_tok or not cust_tok:
            pytest.skip("staff or customer login unavailable")

        async with AsyncClient(base_url=BASE, timeout=30,
                               headers={"Authorization": f"Bearer {staff_tok}"}) as staff:
            r = await staff.put(f"/v1/staff/service-jobs/{info['job_id']}/location",
                                json={"latitude": 12.9716, "longitude": 77.5946, "accuracy_meters": 8.5})
            assert r.status_code == 200, r.text

        async with AsyncClient(base_url=BASE, timeout=30,
                               headers={"Authorization": f"Bearer {cust_tok}"}) as cust:
            r = await cust.get(f"/v1/customer/bookings/{info['booking_id']}/tracking-location")
            assert r.status_code == 200, r.text
            data = r.json()["data"]
            assert data["available"] is True
            assert abs(data["latitude"] - 12.9716) < 1e-4
            assert abs(data["longitude"] - 77.5946) < 1e-4
            assert data["is_stale"] is False
            assert "recorded_at" in data

    async def test_location_not_available_once_job_completed(self):
        info = await self._seed("completed")
        if not info or not info["customer_email"]:
            pytest.skip("no suitable job/customer/staff to seed against")
        tok = await _login(info["customer_email"])
        if not tok:
            pytest.skip("customer login unavailable")
        async with AsyncClient(base_url=BASE, timeout=30,
                               headers={"Authorization": f"Bearer {tok}"}) as cust:
            r = await cust.get(f"/v1/customer/bookings/{info['booking_id']}/tracking-location")
            assert r.status_code == 200, r.text
            data = r.json()["data"]
            assert data["available"] is False
            assert data["reason"] == "tracking_ended"

    async def test_technician_cannot_submit_location_for_completed_job(self):
        info = await self._seed("completed")
        if not info or not info["customer_email"]:
            pytest.skip("no suitable job/customer/staff to seed against")
        staff_tok = await _login(STAFF_EMAIL)
        if not staff_tok:
            pytest.skip("staff login unavailable")
        async with AsyncClient(base_url=BASE, timeout=30,
                               headers={"Authorization": f"Bearer {staff_tok}"}) as staff:
            r = await staff.put(f"/v1/staff/service-jobs/{info['job_id']}/location",
                                json={"latitude": 12.97, "longitude": 77.59})
            assert r.status_code == 200, r.text
            # Router wraps domain errors in a 200 envelope (ok(_err(...))) —
            # assert on the envelope's success flag, not HTTP status.
            body = r.json()["data"]
            assert body.get("success") is False
            assert body["error"]["code"] == "JOB_ASSIGNMENT_LOCATION_NOT_TRACKABLE"

    async def test_foreign_customer_denied(self):
        info = await self._seed("accepted")
        if not info or not info["customer_email"]:
            pytest.skip("no suitable job/customer/staff to seed against")
        # Any other real customer account, if one exists distinct from the seeded one.
        import asyncpg
        c = await asyncpg.connect("postgresql://serviceos:serviceos@127.0.0.1:5432/serviceos")
        try:
            other = await c.fetchval(
                "SELECT email FROM users WHERE role='customer' AND email != $1 LIMIT 1",
                info["customer_email"])
        finally:
            await c.close()
        if not other:
            pytest.skip("no second customer account available")
        tok = await _login(other)
        if not tok:
            pytest.skip("second customer login unavailable")
        async with AsyncClient(base_url=BASE, timeout=30,
                               headers={"Authorization": f"Bearer {tok}"}) as cust:
            r = await cust.get(f"/v1/customer/bookings/{info['booking_id']}/tracking-location")
            assert r.status_code == 404
