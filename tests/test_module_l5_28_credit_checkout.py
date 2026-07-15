"""MODULE-L5-28 — apply service credit to an invoice at checkout.

Customers earned service credits but could not use them: apply_credit_to_booking
targeted the legacy `booking` table (empty, unused) while real bookings are billed
via service_invoices, which had no field to record applied credit. This adds
credit_applied_amount to service_invoices (migration 143) and
CustomerCreditService.apply_credit_to_invoice, exposed at
POST /v1/customer/service-invoices/{id}/apply-credit.

Crucially the new path is applied-once: a second call is rejected, so a retry or
double-tap can never double-spend the credit — the flaw the booking path had
(it overwrote booking.credit_applied while deducting credit every call).
"""
from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient

BASE = "http://localhost:8000"
CUSTOMER_EMAIL = "customer@serviceos.local"
PASSWORD = "Password123!"


def test_invoice_has_credit_column():
    import asyncio, asyncpg

    async def check():
        c = await asyncpg.connect("postgresql://serviceos:serviceos@127.0.0.1:5432/serviceos")
        try:
            return await c.fetchval(
                "SELECT 1 FROM information_schema.columns "
                "WHERE table_name='service_invoices' AND column_name='credit_applied_amount'")
        finally:
            await c.close()

    assert asyncio.get_event_loop().run_until_complete(check())


class TestApplyCreditLive:
    async def _login(self, email):
        async with AsyncClient(base_url=BASE, timeout=30) as c:
            r = await c.post("/v1/auth/login", json={"email": email, "password": PASSWORD})
            return r.json()["data"]["access_token"] if r.status_code == 200 else None

    async def _seed(self):
        """A fresh issued invoice for a customer who holds credit."""
        import asyncpg
        c = await asyncpg.connect("postgresql://serviceos:serviceos@127.0.0.1:5432/serviceos")
        try:
            row = await c.fetchrow(
                "SELECT csc.customer_id, sum(csc.remaining_amount) AS bal "
                "FROM customer_service_credits csc "
                "WHERE csc.status IN ('active','partially_used') "
                "GROUP BY csc.customer_id HAVING sum(csc.remaining_amount) > 0 LIMIT 1")
            if not row:
                return None
            email = await c.fetchval("SELECT email FROM users WHERE id=$1", row["customer_id"])
            tmpl = await c.fetchrow(
                "SELECT category_id, offering_id, booking_id, job_id, tenant_id "
                "FROM service_invoices LIMIT 1")
            iid = uuid.uuid4()
            await c.execute(
                """INSERT INTO service_invoices
                   (id,invoice_number,booking_id,job_id,tenant_id,customer_id,category_id,offering_id,
                    status,currency,subtotal_amount,labour_amount,parts_amount,service_amount,
                    discount_amount,tax_amount,total_amount,customer_payable_amount,credit_applied_amount,
                    payment_mode,payment_status,commission_status,invoice_source,platform_fee_amount,
                    created_at,updated_at)
                   VALUES ($1,$2,$3,$4,$5,$6,$7,$8,'issued','INR',500,500,0,0,0,90,590,590,0,
                    'onsite','pending','pending','manual',0,now(),now())""",
                iid, f"INV-L5T-{uuid.uuid4().hex[:6]}", tmpl["booking_id"], tmpl["job_id"],
                tmpl["tenant_id"], row["customer_id"], tmpl["category_id"], tmpl["offering_id"])
            return {"invoice_id": str(iid), "email": email,
                    "customer_id": str(row["customer_id"]), "balance": float(row["bal"])}
        finally:
            await c.close()

    async def test_apply_reduces_payable_and_is_applied_once(self):
        info = await self._seed()
        if not info or not info["email"]:
            pytest.skip("no customer holding credit / no invoice template")
        tok = await self._login(info["email"])
        if not tok:
            pytest.skip("customer login unavailable")
        use = min(20, info["balance"])

        async with AsyncClient(base_url=BASE, timeout=30,
                               headers={"Authorization": f"Bearer {tok}"}) as cust:
            r = await cust.post(
                f"/v1/customer/service-invoices/{info['invoice_id']}/apply-credit",
                json={"credit_amount_to_apply": use})
            assert r.status_code == 200, r.text
            d = r.json()["data"]
            assert d["original_payable"] == 590.0
            assert d["credit_applied"] == use
            assert d["new_payable"] == 590.0 - use

            # The invoice now reflects it.
            r = await cust.get(f"/v1/customer/service-invoices/{info['invoice_id']}")
            inv = r.json()["data"]
            assert float(inv["customer_payable_amount"]) == 590.0 - use
            assert float(inv["credit_applied_amount"]) == use

            # Applied ONCE: a second application is rejected (no double-spend).
            r2 = await cust.post(
                f"/v1/customer/service-invoices/{info['invoice_id']}/apply-credit",
                json={"credit_amount_to_apply": 5})
            assert r2.status_code == 409, "double-apply must be rejected"

    async def test_credit_cannot_exceed_payable(self):
        info = await self._seed()
        if not info or not info["email"]:
            pytest.skip("no customer holding credit")
        tok = await self._login(info["email"])
        if not tok:
            pytest.skip("customer login unavailable")
        async with AsyncClient(base_url=BASE, timeout=30,
                               headers={"Authorization": f"Bearer {tok}"}) as cust:
            r = await cust.post(
                f"/v1/customer/service-invoices/{info['invoice_id']}/apply-credit",
                json={"credit_amount_to_apply": 999999})
            assert r.status_code == 422
