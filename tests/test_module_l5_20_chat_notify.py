"""MODULE-L5-20 — Chat messages raise notifications.

The chat engine's own docstring said "All sends create audit log + notification
to other participants", but send_message only inserted the message — no
notification was ever created. So a customer's message never alerted the provider
(and a provider/technician reply never alerted the customer); the recipient only
saw it if they happened to open the thread. send_message now raises an in-app
notification for every other active participant, deep-linked to their own chat
surface.
"""
from __future__ import annotations

import inspect

import pytest
import pytest_asyncio
from httpx import AsyncClient

BASE = "http://localhost:8000"


def test_send_message_notifies_other_participants_in_source():
    from app.engines.platform_notifications import chat_service
    src = inspect.getsource(chat_service.ChatMessageService.send_message)
    assert "_notify_other_participants" in src
    helper = inspect.getsource(chat_service.ChatMessageService._notify_other_participants)
    assert "InAppNotification" in helper
    assert "chat.message" in helper


class TestChatNotifyLive:
    async def _ctx(self):
        import asyncpg
        c = await asyncpg.connect("postgresql://serviceos:serviceos@127.0.0.1:5432/serviceos")
        try:
            thread = await c.fetchrow(
                "SELECT id, tenant_id, customer_id FROM chat_threads "
                "WHERE tenant_id IS NOT NULL AND customer_id IS NOT NULL LIMIT 1")
            if not thread:
                return None
            cust_email = await c.fetchval("SELECT email FROM users WHERE id=$1", thread["customer_id"])
            prov_email = await c.fetchval(
                "SELECT email FROM users WHERE tenant_id=$1 AND role LIKE 'tenant%' "
                "AND role <> 'tenant_readonly' AND hashed_password IS NOT NULL LIMIT 1",
                thread["tenant_id"])
            return {"thread_id": str(thread["id"]),
                    "cust_email": cust_email, "prov_email": prov_email}
        finally:
            await c.close()

    async def _login(self, email):
        async with AsyncClient(base_url=BASE, timeout=30) as c:
            r = await c.post("/v1/auth/login", json={"email": email, "password": "Password123!"})
            return r.json()["data"]["access_token"] if r.status_code == 200 else None

    async def test_provider_reply_notifies_the_customer(self):
        ctx = await self._ctx()
        if not ctx or not ctx["cust_email"] or not ctx["prov_email"]:
            pytest.skip("no suitable thread/accounts")
        ctok = await self._login(ctx["cust_email"])
        ptok = await self._login(ctx["prov_email"])
        if not ctok or not ptok:
            pytest.skip("logins unavailable")

        # Baseline: customer's chat notifications.
        async with AsyncClient(base_url=BASE, timeout=30,
                               headers={"Authorization": f"Bearer {ctok}"}) as cust:
            r = await cust.get("/v1/customer/notifications")
            before = [n for n in _items(r.json()["data"])
                      if n.get("notification_type") == "chat.message"]

        # Provider posts a reply.
        async with AsyncClient(base_url=BASE, timeout=30,
                               headers={"Authorization": f"Bearer {ptok}"}) as prov:
            r = await prov.post(f"/v1/provider/chat/threads/{ctx['thread_id']}/messages",
                                json={"message_text": "L5 notify probe"})
            assert r.status_code in (200, 201), r.text

        # Customer now has one more chat notification, deep-linked to its chat.
        async with AsyncClient(base_url=BASE, timeout=30,
                               headers={"Authorization": f"Bearer {ctok}"}) as cust:
            r = await cust.get("/v1/customer/notifications")
            after = [n for n in _items(r.json()["data"])
                     if n.get("notification_type") == "chat.message"]
        assert len(after) > len(before), "provider reply did not notify the customer"
        assert any("/customer/chat/" in (n.get("action_url") or "") for n in after)


def _items(data):
    return data.get("items", data) if isinstance(data, dict) else data
