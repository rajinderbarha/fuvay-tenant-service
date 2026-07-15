"""MODULE-L5-16 — Customer quote approval.

When a job needs extra work/parts the provider sends the customer a quote
(quote_checklist engine). The customer_router (/customer/quotes/*) lets the
customer approve/reject/request-revision — but:

  1. The customer app had NO surface for any of it, so a quote-gated job stalled.
  2. Every quote-event insert failed with UndefinedColumnError because the
     service_job_quote_events table was missing the updated_at column its model
     (ServiceOSBase) declares — so approve/reject/revision all 500'd. Dormant only
     because no quote had been driven end-to-end. Fixed by migration 142.

Also verifies the customer booking detail exposes job_id (the app needs it to
reach the job's quotes).
"""
from __future__ import annotations

import uuid

import pytest
import pytest_asyncio
from httpx import AsyncClient

BASE = "http://localhost:8000"
CUSTOMER_EMAIL = "customer@serviceos.local"
PASSWORD = "Password123!"


async def _login(email):
    async with AsyncClient(base_url=BASE, timeout=30) as c:
        r = await c.post("/v1/auth/login", json={"email": email, "password": PASSWORD})
        return r.json()["data"]["access_token"] if r.status_code == 200 else None


def test_quote_event_table_has_updated_at():
    """The model inherits ServiceOSBase (created_at + updated_at); the table must
    match or every quote-event insert fails."""
    import asyncio, asyncpg

    async def check():
        c = await asyncpg.connect("postgresql://serviceos:serviceos@127.0.0.1:5432/serviceos")
        try:
            return await c.fetchval(
                "SELECT 1 FROM information_schema.columns "
                "WHERE table_name='service_job_quote_events' AND column_name='updated_at'")
        finally:
            await c.close()

    assert asyncio.get_event_loop().run_until_complete(check()), \
        "service_job_quote_events.updated_at is missing (migration 142)"


class TestCustomerQuoteFlow:
    async def _seed_sent_quote(self):
        """Put a fresh sent_to_customer quote on a real customer's job."""
        import asyncpg
        c = await asyncpg.connect("postgresql://serviceos:serviceos@127.0.0.1:5432/serviceos")
        try:
            job = await c.fetchrow(
                "SELECT id, booking_id, tenant_id, customer_id FROM service_jobs "
                "WHERE customer_id IS NOT NULL AND booking_id IS NOT NULL LIMIT 1")
            if not job:
                return None
            email = await c.fetchval("SELECT email FROM users WHERE id=$1", job["customer_id"])
            qid = uuid.uuid4()
            await c.execute(
                """INSERT INTO service_job_quotes
                   (id,quote_number,booking_id,job_id,tenant_id,customer_id,status,quote_type,
                    currency,labour_amount,parts_amount,service_amount,discount_amount,tax_amount,
                    total_amount,customer_payable_amount,created_at,updated_at)
                   VALUES ($1,$2,$3,$4,$5,$6,'sent_to_customer','repair','INR',
                    500,300,0,0,144,944,944,now(),now())""",
                qid, f"QT-L5T-{uuid.uuid4().hex[:6]}", job["booking_id"], job["id"],
                job["tenant_id"], job["customer_id"])
            return {"quote_id": str(qid), "job_id": str(job["id"]),
                    "booking_id": str(job["booking_id"]), "email": email}
        finally:
            await c.close()

    async def test_customer_can_approve_a_quote_and_job_syncs(self):
        info = await self._seed_sent_quote()
        if not info or not info["email"]:
            pytest.skip("no suitable job/customer available")
        tok = await _login(info["email"])
        if not tok:
            pytest.skip("customer login unavailable")

        async with AsyncClient(base_url=BASE, timeout=30,
                               headers={"Authorization": f"Bearer {tok}"}) as cust:
            # Customer sees the quote on the job.
            r = await cust.get(f"/customer/quotes/jobs/{info['job_id']}")
            assert r.status_code == 200, r.text
            quotes = r.json()["data"]
            assert any(q["id"] == info["quote_id"] for q in quotes)

            # Approve (idempotency key required) — must NOT 500 (the updated_at bug).
            r = await cust.post(f"/customer/quotes/{info['quote_id']}/approve",
                                headers={"Idempotency-Key": f"k-{info['quote_id']}"})
            assert r.status_code == 200, r.text
            assert r.json()["data"]["status"] == "customer_approved"

            # Idempotent re-approve with same key returns cleanly.
            r2 = await cust.post(f"/customer/quotes/{info['quote_id']}/approve",
                                 headers={"Idempotency-Key": f"k-{info['quote_id']}"})
            assert r2.status_code == 200

        # The job status followed the approval, and an event was logged.
        import asyncpg
        c = await asyncpg.connect("postgresql://serviceos:serviceos@127.0.0.1:5432/serviceos")
        try:
            job_status = await c.fetchval(
                "SELECT status FROM service_jobs WHERE id=$1", uuid.UUID(info["job_id"]))
            events = await c.fetchval(
                "SELECT count(*) FROM service_job_quote_events WHERE quote_id=$1",
                uuid.UUID(info["quote_id"]))
        finally:
            await c.close()
        assert job_status == "quote_approved"
        assert events >= 1

    async def test_booking_detail_exposes_job_id(self):
        info = await self._seed_sent_quote()
        if not info or not info["email"]:
            pytest.skip("no suitable job/customer available")
        tok = await _login(info["email"])
        if not tok:
            pytest.skip("customer login unavailable")
        async with AsyncClient(base_url=BASE, timeout=30,
                               headers={"Authorization": f"Bearer {tok}"}) as cust:
            r = await cust.get(f"/v1/customer/bookings/{info['booking_id']}")
            assert r.status_code == 200, r.text
            assert r.json()["data"].get("job_id"), "booking detail must expose job_id"
