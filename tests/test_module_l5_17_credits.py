"""MODULE-L5-17 — Customer credits (wallet).

A customer earns service credits from dispute settlements/refunds
(customer_credits engine, /v1/me/credits) but the customer app had NO surface to
see the balance it holds. Building it surfaced a real ownership bug:

  GET /v1/me/credits/{id} compared credit.customer_id (UUID) against the
  require_customer user_id (str). A UUID != str is always True in Python, so the
  OWNER was always 404'd on its own credit. (The list works because it filters in
  SQL.) Fixed by comparing as strings.
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


class TestCustomerCredits:
    async def test_summary_and_list_are_consistent(self, customer):
        r = await customer.get("/v1/me/credits/summary")
        assert r.status_code == 200, r.text
        summary = r.json()["data"]
        assert "active_credit_balance" in summary

        r = await customer.get("/v1/me/credits")
        assert r.status_code == 200
        credits = r.json()["data"]["credits"]
        assert len(credits) == summary["total_credits"]

    async def test_owner_can_open_own_credit_detail(self, customer):
        """Regression: the owner was 404'd on its own credit (UUID vs str compare)."""
        r = await customer.get("/v1/me/credits")
        credits = r.json()["data"]["credits"]
        if not credits:
            pytest.skip("this customer holds no credits")
        credit_id = credits[0]["id"]

        r = await customer.get(f"/v1/me/credits/{credit_id}")
        assert r.status_code == 200, "owner must be able to open its own credit"
        detail = r.json()["data"]
        assert detail["id"] == credit_id
        assert "ledger" in detail

    async def test_preview_apply_computes_payable(self, customer):
        r = await customer.get("/v1/me/credits/summary")
        bal = r.json()["data"]["active_credit_balance"]
        if bal <= 0:
            pytest.skip("no credit balance to apply")
        apply = min(20, bal)
        r = await customer.post("/v1/me/credits/preview-apply",
                                json={"booking_amount": 500, "credit_amount_to_apply": apply})
        assert r.status_code == 200, r.text
        d = r.json()["data"]
        assert float(d["credit_applied"]) == float(apply)
        assert float(d["payable_to_provider"]) == 500 - float(apply)
