"""MODULE-L5-14 — Customer ↔ provider chat wiring.

Two real breaks found in the Level-5 sweep, both making customer-opened chat
threads invisible to the provider:

  1. A customer-created thread was stored with tenant_id = NULL — the customer
     router never resolved the provider from the linked booking — so the provider
     (who scopes chat by tenant) could never see it.
  2. Thread listing/access was participant-gated for the provider side too, so a
     thread was only visible to the exact user who happened to be seeded as a
     participant, not to the rest of the provider's team.

Fixes: create_thread resolves the tenant (and customer) from the record and seeds
the provider owner/staff as participants; provider/staff listing + access are now
tenant-scoped. Verified end-to-end live (customer sends -> provider on the same
tenant reads and replies -> customer sees the reply).

These are source/structure guards plus a live two-way drive.
"""
from __future__ import annotations

import inspect

import pytest
import pytest_asyncio
from httpx import AsyncClient

BASE = "http://localhost:8000"


class TestChatWiringSource:
    def test_create_thread_resolves_tenant_from_record(self):
        from app.engines.platform_notifications import chat_service
        src = inspect.getsource(chat_service.ChatThreadService.create_thread)
        assert "_resolve_record_parties" in src, \
            "create_thread must resolve the provider tenant from the linked record"
        assert "_provider_participants" in src, \
            "create_thread must seed the provider side as participants"

    def test_provider_listing_is_tenant_scoped(self):
        from app.engines.platform_notifications import chat_service
        src = inspect.getsource(chat_service.ChatThreadService.list_threads)
        # Provider/staff branch must key off the tenant, not only participant rows.
        assert "ChatThread.tenant_id == tenant_id" in src

    def test_provider_access_is_tenant_scoped(self):
        from app.engines.platform_notifications import chat_service
        src = inspect.getsource(chat_service.ChatThreadService.validate_thread_access)
        assert "RECIP_PROVIDER" in src and "tenant_id" in src


class TestChatTwoWayLive:
    async def _completed_booking(self):
        import asyncpg
        c = await asyncpg.connect("postgresql://serviceos:serviceos@127.0.0.1:5432/serviceos")
        try:
            row = await c.fetchrow("""
                SELECT sb.id AS booking_id, sb.customer_id, sb.tenant_id
                FROM service_bookings sb
                WHERE sb.customer_id IS NOT NULL AND sb.tenant_id IS NOT NULL
                LIMIT 1""")
            if not row:
                return None
            cust_email = await c.fetchval("SELECT email FROM users WHERE id = $1", row["customer_id"])
            # A provider user for the same tenant who is NOT necessarily the owner.
            prov_email = await c.fetchval(
                "SELECT email FROM users WHERE tenant_id = $1 AND role LIKE 'tenant%' "
                "AND role <> 'tenant_readonly' LIMIT 1", row["tenant_id"])
            return {"booking_id": str(row["booking_id"]),
                    "cust_email": cust_email, "prov_email": prov_email}
        finally:
            await c.close()

    async def _login(self, email):
        async with AsyncClient(base_url=BASE, timeout=30) as c:
            r = await c.post("/v1/auth/login", json={"email": email, "password": "Password123!"})
            if r.status_code != 200:
                return None
            return r.json()["data"]["access_token"]

    async def test_customer_thread_is_visible_to_provider_team(self):
        info = await self._completed_booking()
        if not info or not info["cust_email"] or not info["prov_email"]:
            pytest.skip("no suitable booking / accounts in this environment")

        ctok = await self._login(info["cust_email"])
        ptok = await self._login(info["prov_email"])
        if not ctok or not ptok:
            pytest.skip("demo logins unavailable")

        # Customer opens a thread on the booking and sends a message.
        async with AsyncClient(base_url=BASE, timeout=30,
                               headers={"Authorization": f"Bearer {ctok}"}) as cust:
            r = await cust.post("/v1/customer/chat/threads",
                                json={"record_type": "service_booking", "record_id": info["booking_id"]})
            assert r.status_code in (200, 201), r.text
            thread_id = r.json()["data"]["id"]
            r = await cust.post(f"/v1/customer/chat/threads/{thread_id}/messages",
                                json={"message_text": "L5 chat test — hello"})
            assert r.status_code in (200, 201), r.text

        # A provider user of the same tenant must see the thread AND the message,
        # and be able to reply.
        async with AsyncClient(base_url=BASE, timeout=30,
                               headers={"Authorization": f"Bearer {ptok}"}) as prov:
            r = await prov.get("/v1/provider/chat/threads")
            items = r.json()["data"].get("items", r.json()["data"])
            assert any(t["id"] == thread_id for t in items), \
                "provider team cannot see the customer's thread"
            r = await prov.get(f"/v1/provider/chat/threads/{thread_id}/messages")
            msgs = r.json()["data"].get("items", r.json()["data"])
            assert any(m.get("message_text") == "L5 chat test — hello" for m in msgs)
            r = await prov.post(f"/v1/provider/chat/threads/{thread_id}/messages",
                                json={"message_text": "L5 chat test — reply"})
            assert r.status_code in (200, 201), r.text

        # Customer sees the provider's reply.
        async with AsyncClient(base_url=BASE, timeout=30,
                               headers={"Authorization": f"Bearer {ctok}"}) as cust:
            r = await cust.get(f"/v1/customer/chat/threads/{thread_id}/messages")
            msgs = r.json()["data"].get("items", r.json()["data"])
            assert any(m.get("sender_type") == "provider"
                       and m.get("message_text") == "L5 chat test — reply" for m in msgs)
