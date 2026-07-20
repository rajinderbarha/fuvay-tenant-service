"""MODULE-L5-19 — Staff (technician) chat.

staff_chat_router (/v1/staff/chat) let the technician read/reply on a job's
customer conversation, but staff had NO chat surface at all. This adds the staff
UI (tenant-portal /staff/chat) and verifies the technician — a tenant-scoped
staff user, not a thread participant — can see and reply on the tenant's customer
threads (which relies on the MODULE-L5-14 tenant-scoping).
"""
from __future__ import annotations

import inspect

import pytest
import pytest_asyncio
from httpx import AsyncClient

BASE = "http://localhost:8000"


class TestStaffChatSource:
    def test_staff_chat_router_exists_and_is_tenant_scoped(self):
        from app.engines.platform_notifications import provider_router
        # The staff chat list must pass tenant_id (tenant-scoped visibility).
        # Slice 2F-18A: the literal actor_type is now derived per-caller via
        # _staff_actor_type(u) (staff vs technician persona split) rather
        # than a hardcoded RECIP_STAFF constant.
        src = inspect.getsource(provider_router.staff_list_threads)
        assert "_staff_actor_type(u)" in src and "_tid(u)" in src


class TestStaffChatLive:
    async def _ctx(self):
        """A tenant thread + a staff user of that tenant + the customer."""
        import asyncpg
        c = await asyncpg.connect("postgresql://serviceos:serviceos@127.0.0.1:5432/serviceos")
        try:
            thread = await c.fetchrow(
                "SELECT id, tenant_id, customer_id FROM chat_threads "
                "WHERE tenant_id IS NOT NULL AND customer_id IS NOT NULL LIMIT 1")
            if not thread:
                return None
            staff_email = await c.fetchval(
                "SELECT email FROM users WHERE tenant_id=$1 AND role='staff' "
                "AND hashed_password IS NOT NULL LIMIT 1", thread["tenant_id"])
            cust_email = await c.fetchval(
                "SELECT email FROM users WHERE id=$1", thread["customer_id"])
            return {"thread_id": str(thread["id"]),
                    "staff_email": staff_email, "cust_email": cust_email}
        finally:
            await c.close()

    async def _login(self, email):
        async with AsyncClient(base_url=BASE, timeout=30) as c:
            r = await c.post("/v1/auth/login", json={"email": email, "password": "Password123!"})
            return r.json()["data"]["access_token"] if r.status_code == 200 else None

    async def test_staff_sees_tenant_thread_and_can_reply(self):
        ctx = await self._ctx()
        if not ctx or not ctx["staff_email"] or not ctx["cust_email"]:
            pytest.skip("no tenant thread / staff / customer available")
        stok = await self._login(ctx["staff_email"])
        if not stok:
            pytest.skip("staff login unavailable (non-default password)")

        async with AsyncClient(base_url=BASE, timeout=30,
                               headers={"Authorization": f"Bearer {stok}"}) as staff:
            # Tenant-scoped: the staff user sees the tenant's thread even though it
            # is not individually a participant.
            r = await staff.get("/v1/staff/chat/threads")
            assert r.status_code == 200, r.text
            data = r.json()["data"]
            items = data.get("items", data)
            assert any(t["id"] == ctx["thread_id"] for t in items), \
                "staff cannot see its tenant's customer thread"

            # And can post a reply.
            r = await staff.post(f"/v1/staff/chat/threads/{ctx['thread_id']}/messages",
                                 json={"message_text": "L5 staff chat reply", "message_type": "text"})
            assert r.status_code in (200, 201), r.text
            assert r.json()["data"]["sender_type"] == "staff"

        # The customer sees the staff message.
        ctok = await self._login(ctx["cust_email"])
        if not ctok:
            pytest.skip("customer login unavailable")
        async with AsyncClient(base_url=BASE, timeout=30,
                               headers={"Authorization": f"Bearer {ctok}"}) as cust:
            r = await cust.get(f"/v1/customer/chat/threads/{ctx['thread_id']}/messages")
            msgs = r.json()["data"]["items"]
            assert any(m["sender_type"] == "staff" and m["message_text"] == "L5 staff chat reply"
                       for m in msgs)
