"""MODULE-L5-21 — quote lifecycle notifications.

The quote engine changed job/quote state and logged events but never told the
other party. A provider sending a quote left the customer unaware one was waiting
(the job silently stalled at "awaiting quote approval"), and a customer's
approve/reject/revision never reached the provider. This wires in-app
notifications on each transition.
"""
from __future__ import annotations

import inspect
import uuid

import pytest
import pytest_asyncio
from httpx import AsyncClient

BASE = "http://localhost:8000"


def test_quote_transitions_notify_in_source():
    from app.engines.quote_checklist import quote_service, notifications
    send = inspect.getsource(quote_service.ServiceJobQuoteService.send_to_customer)
    assert "notify_customer_quote_sent" in send
    approve = inspect.getsource(quote_service.ServiceJobQuoteService.customer_approve)
    assert "notify_provider_quote_decision" in approve
    reject = inspect.getsource(quote_service.ServiceJobQuoteService.customer_reject)
    assert "notify_provider_quote_decision" in reject
    revision = inspect.getsource(quote_service.ServiceJobQuoteService.customer_request_revision)
    assert "notify_provider_quote_decision" in revision
    # The helpers create the shared InAppNotification.
    assert "InAppNotification" in inspect.getsource(notifications)


class TestQuoteNotifyLive:
    async def _seed_sent_quote(self):
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
                    400,0,0,0,72,472,472,now(),now())""",
                qid, f"QT-L5-21L-{uuid.uuid4().hex[:6]}", job["booking_id"], job["id"],
                job["tenant_id"], job["customer_id"])
            return {"quote_id": str(qid), "email": email}
        finally:
            await c.close()

    async def test_customer_approval_notifies_the_provider(self):
        info = await self._seed_sent_quote()
        if not info or not info["email"]:
            pytest.skip("no suitable job/customer")
        async with AsyncClient(base_url=BASE, timeout=30) as anon:
            r = await anon.post("/v1/auth/login", json={"email": info["email"], "password": "Password123!"})
            if r.status_code != 200:
                pytest.skip("customer login unavailable")
            ctok = r.json()["data"]["access_token"]

        # Count provider-side quote.decision notifications before.
        import asyncpg
        c = await asyncpg.connect("postgresql://serviceos:serviceos@127.0.0.1:5432/serviceos")
        try:
            q = await c.fetchrow("SELECT tenant_id, job_id FROM service_job_quotes WHERE id=$1",
                                 uuid.UUID(info["quote_id"]))
            owner = await c.fetchval("SELECT owner_user_id FROM tenants WHERE id=$1", q["tenant_id"])
            before = await c.fetchval(
                "SELECT count(*) FROM in_app_notifications WHERE user_id=$1 "
                "AND notification_type='quote.decision'", owner) if owner else 0
        finally:
            await c.close()

        async with AsyncClient(base_url=BASE, timeout=30,
                               headers={"Authorization": f"Bearer {ctok}"}) as cust:
            r = await cust.post(f"/customer/quotes/{info['quote_id']}/approve",
                                headers={"Idempotency-Key": f"n-{info['quote_id']}"})
            assert r.status_code == 200, r.text

        c = await asyncpg.connect("postgresql://serviceos:serviceos@127.0.0.1:5432/serviceos")
        try:
            after = await c.fetchval(
                "SELECT count(*) FROM in_app_notifications WHERE user_id=$1 "
                "AND notification_type='quote.decision'", owner) if owner else 0
        finally:
            await c.close()
        if owner:
            assert after > before, "provider was not notified of the customer's approval"
