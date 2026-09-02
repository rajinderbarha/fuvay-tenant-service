"""Slice 2F-18 — Platform Notifications Provider/Staff Messaging Authorization.

Covers:
- Router guard sources (dependency-level RBAC on all 10 selected mutations
  plus the 10 associated GET reads and the customer_router alternate-route
  fix).
- Chat record ownership (create_thread rejects nonexistent/cross-tenant/
  cross-customer record substitution).
- Message visibility integrity (invalid values rejected, non-admin senders
  cannot set a restricted visibility, unknown visibility fails closed on read).
- Notification preference validation (unknown event_key/channel rejected).
- No-partial-persistence proof for every rejected mutation.
"""
from __future__ import annotations

import uuid
import inspect
from unittest.mock import AsyncMock, MagicMock

import pytest


def _db():
    db = MagicMock()
    db.execute = AsyncMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.add = MagicMock()
    db.get = AsyncMock(return_value=None)
    return db


# ══════════════════════════════════════════════════════════════════════════════
# 1. Router guard sources — every selected mutation route now carries a real
#    role-scope dependency, not just get_current_user.
# ══════════════════════════════════════════════════════════════════════════════

class TestRouterGuardSources:
    def _routes(self, router):
        return {r.name: r for r in router.routes}

    def _dep_names(self, route):
        names = set()

        def walk(dependant):
            if dependant.call is not None and hasattr(dependant.call, "__name__"):
                names.add(dependant.call.__name__)
            for sub in dependant.dependencies:
                walk(sub)

        walk(route.dependant)
        return names

    @pytest.mark.parametrize("fn_name", [
        "provider_list_notifications", "provider_unread_count",
        "provider_mark_read", "provider_mark_all_read",
        "provider_get_prefs", "provider_update_pref",
    ])
    def test_provider_notif_router_uses_office_staff_mutation_guard(self, fn_name):
        from app.engines.platform_notifications.provider_router import provider_notif_router
        routes = self._routes(provider_notif_router)
        assert fn_name in routes
        deps = self._dep_names(routes[fn_name])
        assert "require_owner_or_office_staff_mutation" in deps
        assert "get_current_user" not in deps or "require_owner_or_office_staff_mutation" in deps

    @pytest.mark.parametrize("fn_name", [
        "provider_list_threads", "provider_create_thread", "provider_get_thread",
        "provider_list_messages", "provider_send_message", "provider_mark_thread_read",
    ])
    def test_provider_chat_router_uses_office_staff_mutation_guard(self, fn_name):
        from app.engines.platform_notifications.provider_router import provider_chat_router
        routes = self._routes(provider_chat_router)
        assert fn_name in routes
        deps = self._dep_names(routes[fn_name])
        assert "require_owner_or_office_staff_mutation" in deps

    @pytest.mark.parametrize("fn_name", ["provider_list_audit", "provider_record_timeline"])
    def test_provider_audit_router_uses_office_staff_mutation_guard(self, fn_name):
        from app.engines.platform_notifications.provider_router import provider_audit_router
        routes = self._routes(provider_audit_router)
        assert fn_name in routes
        deps = self._dep_names(routes[fn_name])
        assert "require_owner_or_office_staff_mutation" in deps

    @pytest.mark.parametrize("fn_name", [
        "staff_list_notifications", "staff_unread_count", "staff_mark_read", "staff_mark_all_read",
    ])
    def test_staff_notif_router_uses_staff_or_technician_guard(self, fn_name):
        from app.engines.platform_notifications.provider_router import staff_notif_router
        routes = self._routes(staff_notif_router)
        assert fn_name in routes
        deps = self._dep_names(routes[fn_name])
        assert "require_staff_or_technician_only" in deps

    @pytest.mark.parametrize("fn_name", [
        "staff_list_threads", "staff_get_thread", "staff_list_messages",
        "staff_send_message", "staff_mark_thread_read",
    ])
    def test_staff_chat_router_uses_staff_or_technician_guard(self, fn_name):
        from app.engines.platform_notifications.provider_router import staff_chat_router
        routes = self._routes(staff_chat_router)
        assert fn_name in routes
        deps = self._dep_names(routes[fn_name])
        assert "require_staff_or_technician_only" in deps

    def test_no_route_left_on_bare_get_current_user(self):
        from app.engines.platform_notifications import provider_router as m
        for router in (m.provider_notif_router, m.provider_chat_router,
                       m.provider_audit_router, m.staff_notif_router, m.staff_chat_router):
            for route in router.routes:
                deps = self._dep_names(route)
                assert deps & {
                    "require_owner_or_office_staff_mutation",
                    "require_staff_or_technician_only",
                }, f"{route.name} has no role-scope guard: {deps}"

    @pytest.mark.parametrize("fn_name", [
        "list_notifications", "unread_count", "mark_read", "mark_all_read",
        "get_preferences", "update_preference",
        "list_threads", "create_thread", "get_thread", "list_messages",
        "send_message", "mark_thread_read",
    ])
    def test_customer_router_alternate_route_now_uses_require_customer(self, fn_name):
        # Workstream 19: customer_router.py reaches the SAME ChatThread/
        # InAppNotification records via the same service methods, and was
        # found to be an equally weak get_current_user-only alternate route.
        # Fixed in this slice alongside provider_router (same module).
        from app.engines.platform_notifications import customer_router as m
        found = False
        for router in (m.customer_notif_router, m.customer_chat_router):
            for route in router.routes:
                if route.name == fn_name:
                    found = True
                    names = set()

                    def walk(dependant):
                        if dependant.call is not None and hasattr(dependant.call, "__name__"):
                            names.add(dependant.call.__name__)
                        for sub in dependant.dependencies:
                            walk(sub)
                    walk(route.dependant)
                    assert "require_customer" in names
        assert found


# ══════════════════════════════════════════════════════════════════════════════
# 2. Chat record ownership — create_thread rejects nonexistent / cross-tenant
#    / cross-customer record substitution instead of silently orphaning.
# ══════════════════════════════════════════════════════════════════════════════

class TestChatThreadRecordOwnership:
    @pytest.mark.asyncio
    async def test_provider_create_thread_rejects_nonexistent_service_job(self):
        from app.engines.platform_notifications.chat_service import ChatThreadService
        from app.engines.platform_notifications.constants import ERR_CHAT_RECORD_NOT_FOUND
        svc = ChatThreadService()
        db = _db()
        db.get = AsyncMock(return_value=None)  # ServiceJob lookup finds nothing

        with pytest.raises(ValueError, match=ERR_CHAT_RECORD_NOT_FOUND):
            await svc.create_thread(
                db=db, record_type="service_job", record_id=uuid.uuid4(),
                actor_user_id=uuid.uuid4(), actor_type="provider",
                tenant_id=uuid.uuid4(),
            )
        db.add.assert_not_called()
        db.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_provider_create_thread_rejects_foreign_tenant_booking(self):
        from app.engines.platform_notifications.chat_service import ChatThreadService
        from app.engines.platform_notifications.constants import ERR_CHAT_RECORD_ACCESS_DENIED

        svc = ChatThreadService()
        db = _db()
        foreign_tenant = uuid.uuid4()
        booking = MagicMock(tenant_id=foreign_tenant, customer_id=uuid.uuid4())
        db.get = AsyncMock(return_value=booking)

        caller_tenant = uuid.uuid4()
        with pytest.raises(ValueError, match=ERR_CHAT_RECORD_ACCESS_DENIED):
            await svc.create_thread(
                db=db, record_type="service_booking", record_id=uuid.uuid4(),
                actor_user_id=uuid.uuid4(), actor_type="provider",
                tenant_id=caller_tenant,
            )
        db.add.assert_not_called()
        db.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_customer_create_thread_rejects_foreign_customer_booking(self):
        from app.engines.platform_notifications.chat_service import ChatThreadService
        from app.engines.platform_notifications.constants import ERR_CHAT_RECORD_ACCESS_DENIED

        svc = ChatThreadService()
        db = _db()
        real_customer = uuid.uuid4()
        booking = MagicMock(tenant_id=uuid.uuid4(), customer_id=real_customer)
        db.get = AsyncMock(return_value=booking)

        caller_customer_id = uuid.uuid4()  # not the booking's actual customer
        with pytest.raises(ValueError, match=ERR_CHAT_RECORD_ACCESS_DENIED):
            await svc.create_thread(
                db=db, record_type="service_booking", record_id=uuid.uuid4(),
                actor_user_id=caller_customer_id, actor_type="customer",
                customer_id=caller_customer_id,
            )
        db.add.assert_not_called()
        db.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_unresolvable_record_type_is_not_blocked(self):
        # record_type outside the resolvable set legitimately resolves to
        # (None, None) -- must not be treated as "not found".
        from app.engines.platform_notifications.chat_service import ChatThreadService
        svc = ChatThreadService()
        db = _db()

        not_found = MagicMock()
        not_found.scalars = MagicMock(return_value=MagicMock(first=MagicMock(return_value=None)))
        db.execute = AsyncMock(return_value=not_found)

        def _add_set_id(obj):
            obj.id = uuid.uuid4()
        db.add = MagicMock(side_effect=_add_set_id)

        thread = await svc.create_thread(
            db=db, record_type="admin_internal", record_id=uuid.uuid4(),
            actor_user_id=uuid.uuid4(), actor_type="provider",
            tenant_id=uuid.uuid4(),
        )
        assert thread.record_type == "admin_internal"


# ══════════════════════════════════════════════════════════════════════════════
# 3. Message visibility integrity
# ══════════════════════════════════════════════════════════════════════════════

class TestMessageVisibilityIntegrity:
    @pytest.mark.asyncio
    async def test_invalid_visibility_value_rejected(self):
        from app.engines.platform_notifications.chat_service import ChatMessageService
        from app.engines.platform_notifications.models import ChatThread, ChatThreadParticipant
        from app.engines.platform_notifications.constants import ERR_CHAT_INVALID_VISIBILITY

        svc = ChatMessageService()
        db = _db()
        thread = ChatThread(record_type="service_job", record_id=uuid.uuid4(),
                             status="open", tenant_id=uuid.uuid4())
        thread_r = MagicMock()
        thread_r.scalars = MagicMock(return_value=MagicMock(first=MagicMock(return_value=thread)))
        part_r = MagicMock()
        part_r.scalars = MagicMock(return_value=MagicMock(first=MagicMock(return_value=None)))
        db.execute = AsyncMock(side_effect=[thread_r, part_r])

        with pytest.raises(ValueError, match=ERR_CHAT_INVALID_VISIBILITY):
            await svc.send_message(
                db=db, thread_id=uuid.uuid4(), actor_user_id=uuid.uuid4(),
                actor_type="provider", tenant_id=thread.tenant_id,
                message_text="hi", visibility="totally_not_a_real_value",
            )
        db.add.assert_not_called()
        db.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_non_admin_cannot_set_restricted_visibility(self):
        from app.engines.platform_notifications.chat_service import ChatMessageService
        from app.engines.platform_notifications.models import ChatThread
        from app.engines.platform_notifications.constants import ERR_CHAT_INVALID_VISIBILITY

        svc = ChatMessageService()
        db = _db()
        thread = ChatThread(record_type="service_job", record_id=uuid.uuid4(),
                             status="open", tenant_id=uuid.uuid4())
        thread_r = MagicMock()
        thread_r.scalars = MagicMock(return_value=MagicMock(first=MagicMock(return_value=thread)))
        part_r = MagicMock()
        part_r.scalars = MagicMock(return_value=MagicMock(first=MagicMock(return_value=None)))
        db.execute = AsyncMock(side_effect=[thread_r, part_r])

        with pytest.raises(ValueError, match=ERR_CHAT_INVALID_VISIBILITY):
            await svc.send_message(
                db=db, thread_id=uuid.uuid4(), actor_user_id=uuid.uuid4(),
                actor_type="provider", tenant_id=thread.tenant_id,
                message_text="secret admin note", visibility="admin_only",
            )
        db.add.assert_not_called()

    def test_unrecognized_visibility_fails_closed_on_read(self):
        from app.engines.platform_notifications.models import ChatMessage
        msg = ChatMessage(thread_id=uuid.uuid4(), sender_type="provider",
                           visibility="some_garbage_value", message_text="x")
        # Previously fell through to `return True` (visible to everyone).
        assert msg.is_visible_to("customer") is False
        assert msg.is_visible_to("provider") is False
        assert msg.is_visible_to("admin") is True

    def test_known_visibility_values_unaffected(self):
        from app.engines.platform_notifications.models import ChatMessage
        msg = ChatMessage(thread_id=uuid.uuid4(), sender_type="provider",
                           visibility="thread", message_text="x")
        assert msg.is_visible_to("customer") is True
        assert msg.is_visible_to("provider") is True


# ══════════════════════════════════════════════════════════════════════════════
# 4. Notification preference validation
# ══════════════════════════════════════════════════════════════════════════════

class TestPreferenceValidation:
    @pytest.mark.asyncio
    async def test_unknown_channel_rejected(self):
        from app.engines.platform_notifications.notification_service import NotificationService
        from app.engines.platform_notifications.constants import ERR_NOTIF_INVALID_PREFERENCE
        svc = NotificationService()
        db = _db()
        from app.exceptions import ServiceOSException
        with pytest.raises(ServiceOSException) as exc:
            await svc.update_preference(
                db, uuid.uuid4(), uuid.uuid4(), "chat.new_message", "carrier_pigeon", True,
            )
        assert exc.value.error_code == ERR_NOTIF_INVALID_PREFERENCE
        db.add.assert_not_called()
        db.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_unknown_event_key_rejected(self):
        from app.engines.platform_notifications.notification_service import NotificationService
        from app.engines.platform_notifications.constants import ERR_NOTIF_INVALID_PREFERENCE
        svc = NotificationService()
        db = _db()
        from app.exceptions import ServiceOSException
        with pytest.raises(ServiceOSException) as exc:
            await svc.update_preference(
                db, uuid.uuid4(), uuid.uuid4(), "not.a.real.event", "in_app", True,
            )
        assert exc.value.error_code == ERR_NOTIF_INVALID_PREFERENCE
        db.add.assert_not_called()
        db.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_known_event_and_channel_accepted(self):
        from app.engines.platform_notifications.notification_service import NotificationService
        svc = NotificationService()
        db = _db()
        none_r = MagicMock()
        none_r.scalars = MagicMock(return_value=MagicMock(first=MagicMock(return_value=None)))
        db.execute = AsyncMock(return_value=none_r)
        pref = await svc.update_preference(
            db, uuid.uuid4(), uuid.uuid4(), "chat.new_message", "in_app", False,
        )
        assert pref.event_key == "chat.new_message"
        assert pref.channel == "in_app"


# ══════════════════════════════════════════════════════════════════════════════
# 5. Sender identity — already server-derived, direct proof no impersonation
#    field exists on the request schema.
# ══════════════════════════════════════════════════════════════════════════════

class TestSenderIdentityServerDerived:
    def test_send_msg_schema_has_no_sender_or_tenant_field(self):
        from app.engines.platform_notifications.provider_router import SendMsgIn
        fields = set(SendMsgIn.model_fields.keys())
        assert "sender_id" not in fields
        assert "sender_user_id" not in fields
        assert "tenant_id" not in fields
        assert "created_by" not in fields

    def test_create_thread_schema_has_no_tenant_or_customer_override(self):
        from app.engines.platform_notifications.provider_router import CreateThreadIn
        fields = set(CreateThreadIn.model_fields.keys())
        assert "tenant_id" not in fields
        assert "customer_id" not in fields
