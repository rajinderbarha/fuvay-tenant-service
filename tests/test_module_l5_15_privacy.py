"""MODULE-L5-15 — Customer data-rights (DPDP/GDPR) self-service.

The compliance customer_router (/v1/me/compliance/*) lets a customer exercise its
data rights — export, erasure, correction, consent withdrawal, grievance — but
the customer app had NO surface or client for any of it: a customer could not
exercise a single right from the app. This adds the customer surface and locks in
that the endpoints work end-to-end and reach the admin compliance queue.
"""
from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import AsyncClient

BASE = "http://localhost:8000"
CUSTOMER_EMAIL = "customer@serviceos.local"
ADMIN_EMAIL = "admin@serviceos.local"
PASSWORD = "Password123!"


async def _login(email):
    async with AsyncClient(base_url=BASE, timeout=30) as c:
        r = await c.post("/v1/auth/login", json={"email": email, "password": PASSWORD})
        if r.status_code != 200:
            return None
        return r.json()["data"]["access_token"]


@pytest_asyncio.fixture
async def customer(anyio_backend):
    tok = await _login(CUSTOMER_EMAIL)
    if not tok:
        pytest.skip("customer login unavailable")
    async with AsyncClient(base_url=BASE, timeout=30,
                           headers={"Authorization": f"Bearer {tok}"}) as c:
        yield c


class TestCustomerPrivacy:
    async def test_confirm_understanding_is_required(self, customer):
        r = await customer.post("/v1/me/compliance/requests",
                                json={"request_type": "data_export"})
        assert r.status_code == 422, "confirm_understanding must be enforced"

    async def test_invalid_request_type_rejected(self, customer):
        r = await customer.post("/v1/me/compliance/requests",
                                json={"request_type": "make_me_admin", "confirm_understanding": True})
        assert r.status_code == 422

    async def test_erasure_requires_a_reason(self, customer):
        r = await customer.post("/v1/me/compliance/requests",
                                json={"request_type": "right_to_erasure", "confirm_understanding": True})
        assert r.status_code == 422, "erasure must require a reason"

    async def test_customer_can_file_and_see_a_data_request_and_admin_receives_it(self, customer):
        # File a data-export request (idempotent-ish: duplicate open requests are
        # rejected, so tolerate that and just assert we have one either way).
        r = await customer.post("/v1/me/compliance/requests",
                                json={"request_type": "data_export", "confirm_understanding": True})
        assert r.status_code in (201, 200) or r.status_code == 409, r.text

        # Customer sees at least one request in its own list.
        r = await customer.get("/v1/me/compliance/requests")
        assert r.status_code == 200, r.text
        reqs = r.json()["data"]["requests"]
        assert len(reqs) >= 1
        assert any(rq["request_type"] == "data_export" for rq in reqs)
        number = reqs[0]["request_number"]

        # The admin compliance queue receives customer-subject requests.
        atok = await _login(ADMIN_EMAIL)
        if not atok:
            pytest.skip("admin login unavailable")
        async with AsyncClient(base_url=BASE, timeout=30,
                               headers={"Authorization": f"Bearer {atok}"}) as admin:
            r = await admin.get("/v1/admin/compliance/requests?limit=50")
            assert r.status_code == 200, r.text
            data = r.json()["data"]
            items = data.get("requests", data.get("items", data if isinstance(data, list) else []))
            assert any(str(it.get("subject_type")) == "customer" for it in items), \
                "admin compliance queue does not receive customer requests"

    async def test_consents_endpoint_is_reachable(self, customer):
        r = await customer.get("/v1/me/compliance/consents")
        assert r.status_code == 200
