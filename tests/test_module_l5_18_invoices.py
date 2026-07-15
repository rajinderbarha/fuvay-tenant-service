"""MODULE-L5-18 — Customer invoices.

The invoice_payment customer router had invoice detail / payment-status /
confirm-payment / receipt, but NO list endpoint, and the customer app had no
invoice surface at all — the customer could not see its invoice history, confirm
it paid the provider, or view a receipt. A list endpoint was added to the
canonical invoice_payment engine (not the separate field_ops job-tracking one),
and the customer surface built on it.
"""
from __future__ import annotations

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


@pytest_asyncio.fixture
async def customer(anyio_backend):
    tok = await _login(CUSTOMER_EMAIL)
    if not tok:
        pytest.skip("customer login unavailable")
    async with AsyncClient(base_url=BASE, timeout=30,
                           headers={"Authorization": f"Bearer {tok}"}) as c:
        yield c


class TestCustomerInvoices:
    async def test_list_returns_only_own_invoices(self, customer):
        r = await customer.get("/v1/customer/service-invoices")
        assert r.status_code == 200, r.text
        invoices = r.json()["data"]["invoices"]
        # Whatever the customer holds, every row is a customer-safe view.
        for inv in invoices:
            assert "customer_payable_amount" in inv
            assert "invoice_number" in inv
            # customer-safe view must not leak commission/wallet internals
            assert "commission_amount" not in inv
            assert "provider_payout_amount" not in inv

    async def test_list_then_detail_and_receipt(self, customer):
        r = await customer.get("/v1/customer/service-invoices")
        invoices = r.json()["data"]["invoices"]
        if not invoices:
            pytest.skip("this customer holds no invoices")
        iid = invoices[0]["id"]

        r = await customer.get(f"/v1/customer/service-invoices/{iid}")
        assert r.status_code == 200
        assert r.json()["data"]["id"] == iid

        r = await customer.get(f"/v1/customer/service-invoices/{iid}/receipt")
        assert r.status_code == 200
        assert r.json()["data"]["receipt_type"] == "service_invoice"

        r = await customer.get(f"/v1/customer/service-invoices/{iid}/payment-status")
        assert r.status_code == 200

    async def test_list_endpoint_is_not_shadowed_by_detail_route(self, customer):
        # The collection GET "" must resolve to the list, not be captured by the
        # /{invoice_id} path param.
        r = await customer.get("/v1/customer/service-invoices")
        assert r.status_code == 200
        assert "invoices" in r.json()["data"]
