"""MODULE-L5-24 — admin complaint actions notify the customer.

The complaints engine already told the customer when a provider offered a
resolution or a settlement was proposed, but three admin actions changed
customer-facing state silently: admin_propose_resolution (the ball is now in the
customer's court to accept/reject), admin_resolve_complaint and
admin_reject_complaint. So an admin could propose a resolution and the customer
would never know it was waiting on them — the complaint stalled. Each now
notifies the customer.
"""
from __future__ import annotations

import inspect
import uuid

import pytest
from httpx import AsyncClient

BASE = "http://localhost:8000"


def test_admin_actions_notify_customer_in_source():
    from app.engines.complaints import complaint_service
    for name in ("admin_propose_resolution", "admin_resolve_complaint", "admin_reject_complaint"):
        src = inspect.getsource(getattr(complaint_service.ComplaintService, name))
        assert "notify_customer_complaint" in src, f"{name} must notify the customer"


class TestAdminResolveNotifiesLive:
    async def test_resolving_a_complaint_notifies_its_customer(self):
        import asyncpg
        c = await asyncpg.connect("postgresql://serviceos:serviceos@127.0.0.1:5432/serviceos")
        try:
            # A complaint an admin can still resolve (not already terminal).
            row = await c.fetchrow(
                "SELECT id, customer_id FROM customer_complaints "
                "WHERE status IN ('resolution_proposed','under_admin_review','awaiting_customer_response',"
                "'open','refund_requested') AND customer_id IS NOT NULL LIMIT 1")
            if not row:
                pytest.skip("no resolvable complaint available")
            before = await c.fetchval(
                "SELECT count(*) FROM in_app_notifications WHERE user_id=$1 "
                "AND notification_type='complaint.resolved'", row["customer_id"])
        finally:
            await c.close()

        async with AsyncClient(base_url=BASE, timeout=30) as anon:
            r = await anon.post("/v1/auth/login",
                                json={"email": "admin@serviceos.local", "password": "Password123!"})
            if r.status_code != 200:
                pytest.skip("admin login unavailable")
            atok = r.json()["data"]["access_token"]

        async with AsyncClient(base_url=BASE, timeout=30,
                               headers={"Authorization": f"Bearer {atok}"}) as admin:
            r = await admin.post(f"/v1/admin/complaints/{row['id']}/resolve",
                                 json={"reason": "L5 resolve probe"})
            assert r.status_code == 200, r.text

        c = await asyncpg.connect("postgresql://serviceos:serviceos@127.0.0.1:5432/serviceos")
        try:
            after = await c.fetchval(
                "SELECT count(*) FROM in_app_notifications WHERE user_id=$1 "
                "AND notification_type='complaint.resolved'", row["customer_id"])
        finally:
            await c.close()
        assert after > before, "resolving a complaint did not notify the customer"
