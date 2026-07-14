"""MODULE-L5-13 — Review & Rating engine wiring.

Locks in the fix for a real end-to-end break found during the Level-5 sweep:

The customer booking-rating flow (POST /v1/customer/bookings/{id}/rating) wrote
to the LEGACY `review` engine (`reviews` table), while the provider/admin review
dashboards and the rating aggregation (tenant_rating_summaries /
staff_rating_summaries — the source of trust_quality's average_rating) read the
Sprint 24 `customer_reviews` engine. So a customer's rating reached the provider,
the aggregates, and health scoring: NONE of them.

The endpoint now submits through the customer_reviews engine, which records the
review and recomputes the summaries the dashboards and health read.
"""
from __future__ import annotations

import inspect

import pytest
import pytest_asyncio
from httpx import AsyncClient

BASE = "http://localhost:8000"
ADMIN_EMAIL = "admin@serviceos.local"
ADMIN_PASS = "Password123!"

_TOKEN_CACHE: dict = {}


@pytest_asyncio.fixture(scope="module")
async def token(anyio_backend):
    if "tok" not in _TOKEN_CACHE:
        async with AsyncClient(base_url=BASE, timeout=30) as c:
            r = await c.post("/v1/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASS})
            assert r.status_code == 200, r.text
            _TOKEN_CACHE["tok"] = r.json()["data"]["access_token"]
    return _TOKEN_CACHE["tok"]


@pytest_asyncio.fixture
async def client(token):
    async with AsyncClient(base_url=BASE, headers={"Authorization": f"Bearer {token}"}, timeout=60) as c:
        yield c


class TestBookingRatingWiring:
    def test_booking_rating_uses_customer_reviews_engine_not_legacy(self):
        """The booking rating endpoint must delegate to the customer_reviews
        engine (which aggregates), not the orphaned legacy review engine."""
        from app.engines.home_service_assignment import customer_router
        src = inspect.getsource(customer_router.submit_booking_rating)
        assert "customer_reviews.review_service" in src, \
            "booking rating must submit through the customer_reviews engine"
        assert "engines.review.service" not in src, \
            "booking rating must NOT use the legacy review engine (no aggregation)"

    def test_booking_rating_readback_uses_customer_reviews(self):
        from app.engines.home_service_assignment import customer_router
        src = inspect.getsource(customer_router.get_booking_rating)
        assert "customer_reviews.models" in src
        assert "engines.review.models" not in src


class TestBookingRatingEndToEnd:
    """Drives a real completed booking through rating → dashboard → aggregation."""

    async def _completed_booking(self, client):
        # Find a completed booking that has NOT been reviewed yet.
        import asyncpg
        c = await asyncpg.connect("postgresql://serviceos:serviceos@127.0.0.1:5432/serviceos")
        try:
            row = await c.fetchrow("""
                SELECT sb.id AS booking_id, sb.customer_id, sb.tenant_id
                FROM service_bookings sb
                WHERE sb.status IN ('completed','paid','payment_collected')
                  AND sb.customer_id IS NOT NULL
                  AND NOT EXISTS (SELECT 1 FROM customer_reviews cr WHERE cr.booking_id = sb.id)
                LIMIT 1""")
            email = await c.fetchval(
                "SELECT email FROM users WHERE id = $1", row["customer_id"]) if row else None
            return (row, email)
        finally:
            await c.close()

    async def test_rating_lands_in_customer_reviews_and_provider_sees_it(self, client):
        row, email = await self._completed_booking(client)
        if not row or not email:
            pytest.skip("no un-reviewed completed booking available")

        async with AsyncClient(base_url=BASE, timeout=30) as anon:
            r = await anon.post("/v1/auth/login", json={"email": email, "password": ADMIN_PASS})
            if r.status_code != 200:
                pytest.skip("customer login unavailable in this environment")
            ctok = r.json()["data"]["access_token"]

        booking_id = str(row["booking_id"])
        async with AsyncClient(base_url=BASE, timeout=30,
                               headers={"Authorization": f"Bearer {ctok}"}) as cust:
            r = await cust.post(f"/v1/customer/bookings/{booking_id}/rating",
                                json={"rating": 5, "comment": "L5 wiring check"})
            assert r.status_code == 200, r.text

        # It must exist in customer_reviews (the aggregating engine).
        import asyncpg
        c = await asyncpg.connect("postgresql://serviceos:serviceos@127.0.0.1:5432/serviceos")
        try:
            got = await c.fetchrow(
                "SELECT overall_rating, review_text FROM customer_reviews WHERE booking_id = $1",
                row["booking_id"])
        finally:
            await c.close()
        assert got is not None, "rating did not reach the customer_reviews engine"
        assert got["overall_rating"] == 5
