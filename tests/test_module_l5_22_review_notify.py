"""MODULE-L5-22 — review lifecycle notifications.

The review engine recorded reviews/replies and recomputed rating summaries but
never notified anyone: a customer's new review never reached the provider, and a
provider's (moderated) reply never reached the customer. This wires in-app
notifications on submit_review, submit_reply (auto-approved) and approve_reply.
"""
from __future__ import annotations

import inspect
import uuid

import pytest
from httpx import AsyncClient

BASE = "http://localhost:8000"


def test_review_events_notify_in_source():
    from app.engines.customer_reviews import review_service, notifications
    submit = inspect.getsource(review_service.ReviewService.submit_review)
    assert "notify_provider_new_review" in submit
    approve_reply = inspect.getsource(review_service.ReviewService.approve_reply)
    assert "notify_customer_review_reply" in approve_reply
    submit_reply = inspect.getsource(review_service.ReviewService.submit_reply)
    assert "notify_customer_review_reply" in submit_reply
    assert "InAppNotification" in inspect.getsource(notifications)


class TestReviewReplyNotifyLive:
    async def _seed_review(self):
        """A fresh approved review with no reply, owned by a loginable customer."""
        import asyncpg
        c = await asyncpg.connect("postgresql://serviceos:serviceos@127.0.0.1:5432/serviceos")
        try:
            row = await c.fetchrow(
                "SELECT u.id AS customer_id, sb.tenant_id AS tenant_id FROM users u "
                "JOIN service_bookings sb ON sb.customer_id = u.id "
                "WHERE u.role='customer' AND sb.tenant_id IS NOT NULL LIMIT 1")
            if not row:
                return None
            email = await c.fetchval("SELECT email FROM users WHERE id=$1", row["customer_id"])
            prov_email = await c.fetchval(
                "SELECT email FROM users WHERE tenant_id=$1 AND role LIKE 'tenant%' "
                "AND role<>'tenant_readonly' AND hashed_password IS NOT NULL LIMIT 1",
                row["tenant_id"])
            rid = uuid.uuid4()
            await c.execute(
                """INSERT INTO customer_reviews
                   (id,review_number,customer_id,tenant_id,record_type,record_id,overall_rating,
                    review_text,status,visibility,created_at,updated_at)
                   VALUES ($1,$2,$3,$4,'service_booking',$5,5,'Great!','approved','public',now(),now())""",
                rid, f"REV-L5T-{uuid.uuid4().hex[:6]}", row["customer_id"], row["tenant_id"], uuid.uuid4())
            return {"review_id": str(rid), "customer_id": str(row["customer_id"]),
                    "email": email, "prov_email": prov_email}
        finally:
            await c.close()

    async def _login(self, email):
        async with AsyncClient(base_url=BASE, timeout=30) as c:
            r = await c.post("/v1/auth/login", json={"email": email, "password": "Password123!"})
            return r.json()["data"]["access_token"] if r.status_code == 200 else None

    async def test_approved_reply_notifies_the_customer(self):
        info = await self._seed_review()
        if not info or not info["prov_email"]:
            pytest.skip("no suitable review/provider")
        ptok = await self._login(info["prov_email"])
        if not ptok:
            pytest.skip("provider login unavailable")

        async with AsyncClient(base_url=BASE, timeout=30,
                               headers={"Authorization": f"Bearer {ptok}"}) as prov:
            r = await prov.post(f"/v1/provider/reviews/{info['review_id']}/reply",
                                json={"reply_text": "Thank you!"})
            assert r.status_code in (200, 201), r.text

        # Reply may be auto-approved (notified now) or pending (needs admin approve).
        import asyncpg
        c = await asyncpg.connect("postgresql://serviceos:serviceos@127.0.0.1:5432/serviceos")
        try:
            reply_status = await c.fetchval(
                "SELECT status FROM review_replies WHERE review_id=$1", uuid.UUID(info["review_id"]))
            if reply_status != "approved":
                atok = await self._login("admin@serviceos.local")
                async with AsyncClient(base_url=BASE, timeout=30,
                                       headers={"Authorization": f"Bearer {atok}"}) as admin:
                    r = await admin.post(f"/v1/admin/review-replies/{info['review_id']}/approve")
                    assert r.status_code == 200, r.text
            n = await c.fetchval(
                "SELECT count(*) FROM in_app_notifications WHERE user_id=$1 "
                "AND notification_type='review.reply' AND source_record_id=$2",
                uuid.UUID(info["customer_id"]), uuid.UUID(info["review_id"]))
        finally:
            await c.close()
        assert n >= 1, "customer was not notified of the provider's reply"
