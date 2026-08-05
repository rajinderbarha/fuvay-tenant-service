"""MODULE-L5-29 — customer self-service cancel/reschedule of a confirmed booking.

Flagged in the L5-00 gap register as MODULE-L5-00-005 ("customer cancellation/
reschedule reported as disconnected from the canonical booking pipeline",
severity CRITICAL if confirmed) and never independently re-verified by any
later module.

Confirmed genuinely broken: BOOKING_STATUS_CANCELLED / JOB_STATUS_CANCELLED
existed as constants and the DB columns accepted the value, but no live code
path ever wrote them for a real (post-confirmation) booking — cancel_draft only
covered PRE-confirmation drafts, /v1/bookings/{id}/cancel lived only on the
legacy `booking` engine (0 rows, dead), and the customer app's own
cancelCustomerBooking was a stub that threw "not wired to a real backend
endpoint yet". A customer who wanted to cancel or reschedule after confirmation
had no path except contacting support for an admin force-void.

Fix: HomeServiceJobAssignmentService.customer_cancel_booking /
customer_reschedule_booking, exposed at POST /v1/customer/bookings/{id}/cancel
and /reschedule. Allowed only while the job hasn't progressed past
assignment/scheduling (pending_assignment/assigned/accepted/scheduled) — once a
quote is approved or invoiced, the customer must raise a complaint instead so a
human resolves money already owed. Notifies the provider owner + assigned
technician.
"""
from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient

BASE = "http://localhost:8000"
CUSTOMER_EMAIL = "customer@serviceos.local"
PASSWORD = "Password123!"


async def _login(email):
    async with AsyncClient(base_url=BASE, timeout=30) as c:
        r = await c.post("/v1/auth/login", json={"email": email, "password": PASSWORD})
        return r.json()["data"]["access_token"] if r.status_code == 200 else None


def test_cancellable_statuses_stop_before_real_work_begins():
    from app.engines.home_service_assignment.constants import CUSTOMER_CANCELLABLE_JOB_STATUSES
    # Once a quote is approved or invoiced, self-service cancel must be refused.
    assert "quote_approved" not in CUSTOMER_CANCELLABLE_JOB_STATUSES
    assert "invoice_issued" not in CUSTOMER_CANCELLABLE_JOB_STATUSES
    assert "completed" not in CUSTOMER_CANCELLABLE_JOB_STATUSES
    assert "pending_assignment" in CUSTOMER_CANCELLABLE_JOB_STATUSES
    assert "assigned" in CUSTOMER_CANCELLABLE_JOB_STATUSES


class TestCancelRescheduleLive:
    async def _seed_cancellable(self):
        """A fresh pending_assignment job/booking for a real customer."""
        import asyncpg
        c = await asyncpg.connect("postgresql://serviceos:serviceos@127.0.0.1:5432/serviceos")
        try:
            tmpl = await c.fetchrow(
                "SELECT sj.booking_id, sj.tenant_id, sj.customer_id, sb.category_id, sb.offering_id "
                "FROM service_jobs sj JOIN service_bookings sb ON sb.id = sj.booking_id "
                "WHERE sj.customer_id IS NOT NULL LIMIT 1")
            if not tmpl:
                return None
            email = await c.fetchval("SELECT email FROM users WHERE id=$1", tmpl["customer_id"])
            owner = await c.fetchval("SELECT owner_user_id FROM tenants WHERE id=$1", tmpl["tenant_id"])
            jid, bid = uuid.uuid4(), uuid.uuid4()
            await c.execute(
                """INSERT INTO service_bookings
                   (id,booking_number,draft_id,customer_id,tenant_id,category_id,offering_id,
                    status,assignment_status,created_at,updated_at)
                   VALUES ($1,$2,$3,$4,$5,$6,$7,'pending_assignment','unassigned',now(),now())""",
                bid, f"BK-L5T-{uuid.uuid4().hex[:6]}", uuid.uuid4(), tmpl["customer_id"],
                tmpl["tenant_id"], tmpl["category_id"], tmpl["offering_id"])
            await c.execute(
                """INSERT INTO service_jobs
                   (id,job_number,booking_id,customer_id,tenant_id,category_id,offering_id,
                    status,assignment_status,created_at,updated_at)
                   VALUES ($1,$2,$3,$4,$5,$6,$7,'pending_assignment','unassigned',now(),now())""",
                jid, f"JOB-L5T-{uuid.uuid4().hex[:6]}", bid, tmpl["customer_id"],
                tmpl["tenant_id"], tmpl["category_id"], tmpl["offering_id"])
            return {"booking_id": str(bid), "job_id": str(jid), "email": email, "owner_id": owner}
        finally:
            await c.close()

    async def test_customer_can_reschedule_then_cancel(self):
        info = await self._seed_cancellable()
        if not info or not info["email"]:
            pytest.skip("no suitable job/customer/schema to seed against")
        tok = await _login(info["email"])
        if not tok:
            pytest.skip("customer login unavailable")

        async with AsyncClient(base_url=BASE, timeout=30,
                               headers={"Authorization": f"Bearer {tok}"}) as cust:
            r = await cust.post(f"/v1/customer/bookings/{info['booking_id']}/reschedule",
                                json={"scheduled_date": "2026-09-01",
                                     "scheduled_time_window": "2pm-4pm",
                                     "reason": "conflict"})
            assert r.status_code == 200, r.text
            assert r.json()["data"]["scheduled_date"] == "2026-09-01"

            r = await cust.post(f"/v1/customer/bookings/{info['booking_id']}/cancel",
                                json={"reason": "changed my mind"})
            assert r.status_code == 200, r.text
            assert r.json()["data"]["status"] == "cancelled"

            # Cancelling again must fail — it is now terminal.
            r2 = await cust.post(f"/v1/customer/bookings/{info['booking_id']}/cancel",
                                 json={"reason": "again"})
            assert r2.status_code == 409

        if info["owner_id"]:
            import asyncpg
            c = await asyncpg.connect("postgresql://serviceos:serviceos@127.0.0.1:5432/serviceos")
            try:
                n = await c.fetchval(
                    "SELECT count(*) FROM in_app_notifications WHERE user_id=$1 "
                    "AND notification_type IN ('booking.cancelled','booking.rescheduled')",
                    info["owner_id"])
            finally:
                await c.close()
            assert n >= 2, "provider was not notified of the reschedule and cancellation"

    async def test_cancel_requires_a_reason(self):
        info = await self._seed_cancellable()
        if not info or not info["email"]:
            pytest.skip("no suitable job/customer to seed against")
        tok = await _login(info["email"])
        if not tok:
            pytest.skip("customer login unavailable")
        async with AsyncClient(base_url=BASE, timeout=30,
                               headers={"Authorization": f"Bearer {tok}"}) as cust:
            r = await cust.post(f"/v1/customer/bookings/{info['booking_id']}/cancel", json={})
            assert r.status_code == 422

    async def test_eligibility_reflects_real_state(self):
        """CANCEL-RESCHEDULE-FOUNDATION: the eligibility endpoint must be the
        single source of truth the mobile app reads — no client-side
        reproduction of CUSTOMER_CANCELLABLE_JOB_STATUSES/MAX_RESCHEDULE_COUNT."""
        info = await self._seed_cancellable()
        if not info or not info["email"]:
            pytest.skip("no suitable job/customer to seed against")
        tok = await _login(info["email"])
        if not tok:
            pytest.skip("customer login unavailable")
        async with AsyncClient(base_url=BASE, timeout=30,
                               headers={"Authorization": f"Bearer {tok}"}) as cust:
            r = await cust.get(f"/v1/customer/bookings/{info['booking_id']}/cancel-reschedule-eligibility")
            assert r.status_code == 200, r.text
            data = r.json()["data"]
            assert data["can_cancel"] is True
            assert data["can_reschedule"] is True
            assert data["remaining_reschedule_allowance"] == 3
            assert data["requires_provider_approval"] is False
            assert data["cancellation_fee"] is None
            assert "version" in data and data["version"]

    async def test_reschedule_limit_is_enforced(self):
        """Policy decision 2026-08-02: cap customer reschedules at 3."""
        info = await self._seed_cancellable()
        if not info or not info["email"]:
            pytest.skip("no suitable job/customer to seed against")
        tok = await _login(info["email"])
        if not tok:
            pytest.skip("customer login unavailable")
        async with AsyncClient(base_url=BASE, timeout=30,
                               headers={"Authorization": f"Bearer {tok}"}) as cust:
            for i in range(3):
                r = await cust.post(f"/v1/customer/bookings/{info['booking_id']}/reschedule",
                                    json={"scheduled_date": f"2026-09-{10+i:02d}",
                                         "reason": f"attempt {i}"})
                assert r.status_code == 200, r.text
            # 4th reschedule must be refused — limit reached.
            r4 = await cust.post(f"/v1/customer/bookings/{info['booking_id']}/reschedule",
                                 json={"scheduled_date": "2026-09-20", "reason": "one more"})
            assert r4.status_code == 409
            elig = await cust.get(f"/v1/customer/bookings/{info['booking_id']}/cancel-reschedule-eligibility")
            assert elig.json()["data"]["remaining_reschedule_allowance"] == 0
            assert elig.json()["data"]["can_reschedule"] is False

    async def test_reschedule_rejects_past_date(self):
        info = await self._seed_cancellable()
        if not info or not info["email"]:
            pytest.skip("no suitable job/customer to seed against")
        tok = await _login(info["email"])
        if not tok:
            pytest.skip("customer login unavailable")
        async with AsyncClient(base_url=BASE, timeout=30,
                               headers={"Authorization": f"Bearer {tok}"}) as cust:
            r = await cust.post(f"/v1/customer/bookings/{info['booking_id']}/reschedule",
                                json={"scheduled_date": "2020-01-01", "reason": "test"})
            assert r.status_code == 422

    async def test_cancel_rejects_stale_version(self):
        info = await self._seed_cancellable()
        if not info or not info["email"]:
            pytest.skip("no suitable job/customer to seed against")
        tok = await _login(info["email"])
        if not tok:
            pytest.skip("customer login unavailable")
        async with AsyncClient(base_url=BASE, timeout=30,
                               headers={"Authorization": f"Bearer {tok}"}) as cust:
            r = await cust.post(f"/v1/customer/bookings/{info['booking_id']}/cancel",
                                json={"reason": "test", "expected_version": "2000-01-01T00:00:00+00:00"})
            assert r.status_code == 409

    async def test_cancel_is_blocked_once_invoiced(self):
        import asyncpg
        c = await asyncpg.connect("postgresql://serviceos:serviceos@127.0.0.1:5432/serviceos")
        try:
            row = await c.fetchrow(
                "SELECT sj.booking_id, u.email FROM service_jobs sj "
                "JOIN users u ON u.id = sj.customer_id "
                "WHERE sj.status IN ('invoice_issued','quote_approved','completed') LIMIT 1")
        finally:
            await c.close()
        if not row:
            pytest.skip("no invoiced/quote-approved/completed job available")
        tok = await _login(row["email"])
        if not tok:
            pytest.skip("customer login unavailable")
        async with AsyncClient(base_url=BASE, timeout=30,
                               headers={"Authorization": f"Bearer {tok}"}) as cust:
            r = await cust.post(f"/v1/customer/bookings/{row['booking_id']}/cancel",
                                json={"reason": "too late attempt"})
            assert r.status_code == 409, "cancel must be refused once real work has progressed"
