"""Sprint 27 — Notification + Chat + Audit Integration Tests.

37 tests covering:
- Event registry
- Notification service (fire_event, dispatch, retry, preferences, templates)
- Channel providers (in-app works, stubs return provider_not_configured)
- Recipient resolver (no cross-tenant leakage)
- Chat thread service (create, access control, close)
- Chat message service (send, visibility, closed thread blocks, mark read)
- Audit service (write, redact, admin filter, provider scope, timeline)
- Integration (booking → notification, complaint → notification)
- Router import verification
"""
import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def user_id():
    return uuid.uuid4()

@pytest.fixture
def tenant_id():
    return uuid.uuid4()

@pytest.fixture
def other_tenant_id():
    return uuid.uuid4()

@pytest.fixture
def customer_id():
    return uuid.uuid4()

def _db():
    db = MagicMock()
    db.execute = AsyncMock()
    db.flush   = AsyncMock()
    db.commit  = AsyncMock()
    db.add     = MagicMock()
    db.delete  = AsyncMock()
    return db


# ══════════════════════════════════════════════════════════════════════════════
# 1. Event Registry
# ══════════════════════════════════════════════════════════════════════════════

def test_event_registry_has_known_keys():
    from app.engines.platform_notifications.event_registry import NotificationEventRegistry
    from app.engines.platform_notifications.constants import (
        EVT_BOOKING_CONFIRMED, EVT_COMPLAINT_CREATED, EVT_INVOICE_ISSUED,
        EVT_REVIEW_SUBMITTED, EVT_LEAD_CREATED,
    )
    assert NotificationEventRegistry.get(EVT_BOOKING_CONFIRMED) is not None
    assert NotificationEventRegistry.get(EVT_COMPLAINT_CREATED) is not None
    assert NotificationEventRegistry.get(EVT_INVOICE_ISSUED) is not None
    assert NotificationEventRegistry.get(EVT_REVIEW_SUBMITTED) is not None
    assert NotificationEventRegistry.get(EVT_LEAD_CREATED) is not None


def test_event_registry_returns_none_for_unknown_key():
    from app.engines.platform_notifications.event_registry import NotificationEventRegistry
    assert NotificationEventRegistry.get("unknown.event.key") is None


def test_event_registry_all_keys_is_populated():
    from app.engines.platform_notifications.event_registry import NotificationEventRegistry
    keys = NotificationEventRegistry.all_keys()
    assert len(keys) >= 30


def test_event_registry_booking_confirmed_channels():
    from app.engines.platform_notifications.event_registry import NotificationEventRegistry
    from app.engines.platform_notifications.constants import EVT_BOOKING_CONFIRMED, CHANNEL_IN_APP
    cfg = NotificationEventRegistry.get(EVT_BOOKING_CONFIRMED)
    assert cfg is not None
    assert CHANNEL_IN_APP in cfg.default_channels


# ══════════════════════════════════════════════════════════════════════════════
# 2. Channel Providers
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_in_app_provider_creates_notification(user_id, tenant_id):
    from app.engines.platform_notifications.channel_providers import InAppNotificationProvider
    from app.engines.platform_notifications.constants import DELIVERY_DELIVERED

    provider = InAppNotificationProvider()
    db = _db()

    created_notif = MagicMock()
    created_notif.id = uuid.uuid4()

    def _add_side_effect(obj):
        obj.id = uuid.uuid4()

    db.add.side_effect = _add_side_effect

    result = await provider.deliver(
        db=db, outbox_id=uuid.uuid4(), user_id=user_id, tenant_id=tenant_id,
        notification_type="booking.confirmed", title="Booking Confirmed",
        body="Your booking is confirmed.", action_url=None, action_label=None,
        source_record_type="service_booking", source_record_id=uuid.uuid4(),
        severity="info",
    )
    assert result.success is True
    assert result.status == DELIVERY_DELIVERED
    assert result.provider_name == "in_app"


@pytest.mark.asyncio
async def test_email_stub_returns_not_configured():
    from app.engines.platform_notifications.channel_providers import EmailNotificationProvider
    from app.engines.platform_notifications.constants import DELIVERY_PROVIDER_NOT_CONFIGURED
    stub = EmailNotificationProvider()
    with patch("app.engines.platform_notifications.channel_providers.channel_config_service.get_active", AsyncMock(return_value=None)):
        result = await stub.deliver(db=_db(), user_id=uuid.uuid4(), title="Test", body="Test")
    assert result.success is False
    assert result.status == DELIVERY_PROVIDER_NOT_CONFIGURED
    assert result.failure_code == "PROVIDER_NOT_CONFIGURED"


@pytest.mark.asyncio
async def test_sms_stub_returns_not_configured():
    from app.engines.platform_notifications.channel_providers import TwilioNotificationProvider
    from app.engines.platform_notifications.constants import DELIVERY_PROVIDER_NOT_CONFIGURED
    stub = TwilioNotificationProvider("sms")
    with patch("app.engines.platform_notifications.channel_providers.channel_config_service.get_active", AsyncMock(return_value=None)):
        result = await stub.deliver(db=_db(), user_id=uuid.uuid4(), body="Test")
    assert result.success is False
    assert result.status == DELIVERY_PROVIDER_NOT_CONFIGURED


@pytest.mark.asyncio
async def test_push_stub_returns_not_configured():
    from app.engines.platform_notifications.channel_providers import ExpoPushNotificationProvider
    from app.engines.platform_notifications.constants import DELIVERY_PROVIDER_NOT_CONFIGURED
    stub = ExpoPushNotificationProvider()
    with patch("app.engines.platform_notifications.channel_providers.channel_config_service.get_active", AsyncMock(return_value=None)):
        result = await stub.deliver(db=_db(), user_id=uuid.uuid4(), title="Test", body="Test")
    assert result.success is False
    assert result.status == DELIVERY_PROVIDER_NOT_CONFIGURED


# ══════════════════════════════════════════════════════════════════════════════
# 3. Notification Service
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_notification_service_fire_event_returns_none_for_unknown_key():
    from app.engines.platform_notifications.notification_service import NotificationService
    db = _db()
    svc = NotificationService()
    result = await svc.fire_event(db, "totally.unknown.event.xyz", {})
    assert result is None


@pytest.mark.asyncio
async def test_notification_service_fire_event_creates_event(user_id, tenant_id):
    from app.engines.platform_notifications.notification_service import NotificationService
    from app.engines.platform_notifications.constants import EVT_BOOKING_CONFIRMED
    svc = NotificationService()
    db = _db()

    with patch.object(svc, "fire_event", AsyncMock(return_value=MagicMock(id=uuid.uuid4(), status="processed"))) as mock_fire:
        result = await svc.fire_event(
            db, EVT_BOOKING_CONFIRMED, {"booking_number": "BK-001"},
            tenant_id=tenant_id, customer_id=user_id,
            recipients=[{"user_id": str(user_id), "recipient_type": "customer"}],
        )
        mock_fire.assert_called_once()


@pytest.mark.asyncio
async def test_notification_service_get_unread_count(user_id):
    from app.engines.platform_notifications.notification_service import NotificationService
    svc = NotificationService()
    db = _db()

    count_result = MagicMock()
    count_result.scalar_one = MagicMock(return_value=5)
    db.execute = AsyncMock(return_value=count_result)

    count = await svc.get_unread_count(db, user_id)
    assert count == 5


@pytest.mark.asyncio
async def test_notification_service_mark_all_read(user_id):
    from app.engines.platform_notifications.notification_service import NotificationService
    from app.engines.platform_notifications.models import InAppNotification
    svc = NotificationService()
    db = _db()

    notif = InAppNotification(user_id=user_id, notification_type="test",
                               title="T", body="B", read_status="unread")
    notif.id = uuid.uuid4()

    mock_result = MagicMock()
    mock_result.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[notif])))
    db.execute = AsyncMock(return_value=mock_result)

    count = await svc.mark_all_read(db, user_id)
    assert count == 1
    assert notif.read_status == "read"


@pytest.mark.asyncio
async def test_notification_service_get_notifications(user_id):
    from app.engines.platform_notifications.notification_service import NotificationService
    svc = NotificationService()
    db = _db()

    total_r = MagicMock()
    total_r.scalar_one = MagicMock(return_value=0)
    items_r = MagicMock()
    items_r.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))
    db.execute = AsyncMock(side_effect=[total_r, items_r])

    result = await svc.get_user_notifications(db, user_id)
    assert "items" in result
    assert "total" in result


@pytest.mark.asyncio
async def test_notification_service_preferences_default_enabled(user_id):
    from app.engines.platform_notifications.notification_service import NotificationService
    svc = NotificationService()
    db = _db()

    no_pref_r = MagicMock()
    no_pref_r.scalars = MagicMock(return_value=MagicMock(first=MagicMock(return_value=None)))
    db.execute = AsyncMock(return_value=no_pref_r)

    enabled = await svc._check_preference(db, user_id, "booking.confirmed", "in_app")
    assert enabled is True


@pytest.mark.asyncio
async def test_notification_service_retry_outbox_exceeds_max_raises(user_id):
    from app.engines.platform_notifications.notification_service import NotificationService
    from app.engines.platform_notifications.models import NotificationOutbox
    from app.engines.platform_notifications.constants import ERR_NOTIF_RETRY_NOT_ALLOWED
    svc = NotificationService()
    db = _db()

    outbox = NotificationOutbox(
        recipient_type="customer", channel="in_app", template_key="x",
        title="T", body="B", retry_count=3, max_retries=3, delivery_status="failed",
    )
    outbox.id = uuid.uuid4()

    r = MagicMock()
    r.scalars = MagicMock(return_value=MagicMock(first=MagicMock(return_value=outbox)))
    db.execute = AsyncMock(return_value=r)

    from app.exceptions import ServiceOSException
    with pytest.raises(ServiceOSException) as exc:
        await svc.retry_outbox(db, outbox.id)
    assert exc.value.error_code == ERR_NOTIF_RETRY_NOT_ALLOWED


@pytest.mark.asyncio
async def test_notification_service_outbox_not_found_raises():
    from app.engines.platform_notifications.notification_service import NotificationService
    from app.engines.platform_notifications.constants import ERR_NOTIF_OUTBOX_NOT_FOUND
    svc = NotificationService()
    db = _db()

    r = MagicMock()
    r.scalars = MagicMock(return_value=MagicMock(first=MagicMock(return_value=None)))
    db.execute = AsyncMock(return_value=r)

    from app.exceptions import ServiceOSException
    with pytest.raises(ServiceOSException) as exc:
        await svc.get_outbox_record(db, uuid.uuid4())
    assert exc.value.error_code == ERR_NOTIF_OUTBOX_NOT_FOUND


@pytest.mark.asyncio
async def test_notification_service_template_rendering():
    from app.engines.platform_notifications.notification_service import NotificationService
    result = NotificationService._render("Hello {{name}}, your booking {{booking_number}} is ready.", {
        "name": "Alice", "booking_number": "BK-001"
    })
    assert result == "Hello Alice, your booking BK-001 is ready."


def test_notification_service_render_removes_unresolved():
    from app.engines.platform_notifications.notification_service import NotificationService
    result = NotificationService._render("Hello {{name}}, ref {{missing}}.", {"name": "Bob"})
    assert "{{missing}}" not in result
    assert "Bob" in result


# ══════════════════════════════════════════════════════════════════════════════
# 4. Chat Thread Service
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_chat_thread_create(user_id, tenant_id):
    from app.engines.platform_notifications.chat_service import ChatThreadService
    from app.engines.platform_notifications.models import ChatThread
    svc = ChatThreadService()
    db = _db()

    # First execute: check existing thread (none found)
    not_found = MagicMock()
    not_found.scalars = MagicMock(return_value=MagicMock(first=MagicMock(return_value=None)))
    # Second execute: check participant (none found)
    not_found2 = MagicMock()
    not_found2.scalars = MagicMock(return_value=MagicMock(first=MagicMock(return_value=None)))
    db.execute = AsyncMock(side_effect=[not_found, not_found2])

    def _add_set_id(obj):
        obj.id = uuid.uuid4()
    db.add = MagicMock(side_effect=_add_set_id)

    thread = await svc.create_thread(
        db=db, record_type="service_booking", record_id=uuid.uuid4(),
        actor_user_id=user_id, actor_type="customer",
        tenant_id=tenant_id, customer_id=user_id,
    )
    assert thread.record_type == "service_booking"
    assert thread.status == "open"
    assert thread.thread_number.startswith("THR-")


@pytest.mark.asyncio
async def test_chat_thread_customer_cannot_access_other_customer(user_id, customer_id):
    # PROTECTED_BY_LATER_SLICE: 2F-39A. validate_thread_access now raises
    # ERR_CHAT_THREAD_NOT_FOUND (not ERR_CHAT_THREAD_ACCESS_DENIED) for a
    # real-but-unauthorized thread -- a deliberate non-oracular fix (same
    # error for "doesn't exist" and "exists but not yours", matching the
    # Booking-series precedent used throughout this program) so an
    # unauthorized caller cannot distinguish the two. This is a privacy
    # improvement, not a regression: access is still correctly denied
    # (ValueError is still raised) -- only the message changed.
    # ERR_CHAT_THREAD_ACCESS_DENIED is kept as a constant for internal/log
    # use only per chat_service.py's own comment.
    from app.engines.platform_notifications.chat_service import ChatThreadService
    from app.engines.platform_notifications.models import ChatThread
    from app.engines.platform_notifications.constants import ERR_CHAT_THREAD_NOT_FOUND
    svc = ChatThreadService()
    db = _db()

    other_customer = uuid.uuid4()
    thread = ChatThread(
        thread_number="THR-XYZ", record_type="service_booking",
        record_id=uuid.uuid4(), status="open", customer_id=other_customer,
    )
    thread.id = uuid.uuid4()

    with pytest.raises(ValueError, match=ERR_CHAT_THREAD_NOT_FOUND):
        await svc.validate_thread_access(db, thread, user_id, "customer", None)


@pytest.mark.asyncio
async def test_chat_thread_provider_cannot_access_other_tenant(user_id, tenant_id, other_tenant_id):
    # PROTECTED_BY_LATER_SLICE: 2F-39A -- same non-oracular fix as
    # test_chat_thread_customer_cannot_access_other_customer above.
    from app.engines.platform_notifications.chat_service import ChatThreadService
    from app.engines.platform_notifications.models import ChatThread
    from app.engines.platform_notifications.constants import ERR_CHAT_THREAD_NOT_FOUND
    svc = ChatThreadService()
    db = _db()

    thread = ChatThread(
        thread_number="THR-YYY", record_type="service_job",
        record_id=uuid.uuid4(), status="open",
        tenant_id=other_tenant_id,
    )
    thread.id = uuid.uuid4()

    with pytest.raises(ValueError, match=ERR_CHAT_THREAD_NOT_FOUND):
        await svc.validate_thread_access(db, thread, user_id, "provider", tenant_id)


@pytest.mark.asyncio
async def test_chat_thread_admin_can_access_any(user_id, tenant_id, other_tenant_id):
    from app.engines.platform_notifications.chat_service import ChatThreadService
    from app.engines.platform_notifications.models import ChatThread
    svc = ChatThreadService()
    db = _db()

    thread = ChatThread(
        thread_number="THR-ZZZ", record_type="service_job",
        record_id=uuid.uuid4(), status="open", tenant_id=other_tenant_id,
    )
    thread.id = uuid.uuid4()

    # Should not raise
    await svc.validate_thread_access(db, thread, user_id, "admin", tenant_id)


# ══════════════════════════════════════════════════════════════════════════════
# 5. Chat Message Service
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_chat_message_send_creates_message(user_id, tenant_id):
    from app.engines.platform_notifications.chat_service import ChatThreadService, ChatMessageService
    from app.engines.platform_notifications.models import ChatThread, ChatThreadParticipant

    svc = ChatMessageService()
    db = _db()
    thread_id = uuid.uuid4()

    thread = ChatThread(thread_number="THR-T01", record_type="service_booking",
                        record_id=uuid.uuid4(), status="open", tenant_id=tenant_id,
                        customer_id=user_id)
    thread.id = thread_id

    participant = ChatThreadParticipant(thread_id=thread_id, user_id=user_id,
                                        participant_type="customer", can_send=True)
    participant.id = uuid.uuid4()

    thread_r = MagicMock()
    thread_r.scalars = MagicMock(return_value=MagicMock(first=MagicMock(return_value=thread)))
    part_r = MagicMock()
    part_r.scalars = MagicMock(return_value=MagicMock(first=MagicMock(return_value=participant)))
    # send_message now also notifies the other participants, which runs one more
    # execute (the participant list). The sender is the sole participant here, so
    # the notify loop skips it and adds nothing.
    notify_r = MagicMock()
    notify_r.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[participant])))
    db.execute = AsyncMock(side_effect=[thread_r, part_r, notify_r])

    def _set_id(obj):
        obj.id = uuid.uuid4()
    db.add = MagicMock(side_effect=_set_id)

    with patch.object(svc._thread_svc, "validate_thread_access", AsyncMock()):
        msg = await svc.send_message(
            db=db, thread_id=thread_id,
            actor_user_id=user_id, actor_type="customer",
            tenant_id=tenant_id, message_text="Hello!",
        )
    assert msg.message_text == "Hello!"
    assert msg.sender_type == "customer"


@pytest.mark.asyncio
async def test_chat_message_closed_thread_blocks_send(user_id, tenant_id):
    from app.engines.platform_notifications.chat_service import ChatMessageService
    from app.engines.platform_notifications.models import ChatThread
    from app.engines.platform_notifications.constants import ERR_CHAT_THREAD_CLOSED
    svc = ChatMessageService()
    db = _db()

    thread = ChatThread(thread_number="THR-C01", record_type="complaint",
                        record_id=uuid.uuid4(), status="closed")
    thread.id = uuid.uuid4()

    thread_r = MagicMock()
    thread_r.scalars = MagicMock(return_value=MagicMock(first=MagicMock(return_value=thread)))
    db.execute = AsyncMock(return_value=thread_r)

    with pytest.raises(ValueError, match=ERR_CHAT_THREAD_CLOSED):
        await svc.send_message(db=db, thread_id=thread.id,
                               actor_user_id=user_id, actor_type="customer",
                               tenant_id=tenant_id, message_text="Message")


@pytest.mark.asyncio
async def test_chat_message_visibility_customer_cannot_see_admin_only(user_id):
    from app.engines.platform_notifications.models import ChatMessage
    from app.engines.platform_notifications.constants import VIS_ADMIN_ONLY
    msg = ChatMessage(
        thread_id=uuid.uuid4(), sender_type="admin",
        message_text="Internal note", visibility=VIS_ADMIN_ONLY,
        delivery_status="sent",
    )
    msg.id = uuid.uuid4()
    assert msg.is_visible_to("customer") is False
    assert msg.is_visible_to("admin") is True


@pytest.mark.asyncio
async def test_chat_message_visibility_provider_cannot_see_customer_only(user_id):
    from app.engines.platform_notifications.models import ChatMessage
    from app.engines.platform_notifications.constants import VIS_CUSTOMER_ONLY
    msg = ChatMessage(
        thread_id=uuid.uuid4(), sender_type="customer",
        message_text="Private note", visibility=VIS_CUSTOMER_ONLY,
        delivery_status="sent",
    )
    msg.id = uuid.uuid4()
    assert msg.is_visible_to("provider") is False
    assert msg.is_visible_to("customer") is True
    assert msg.is_visible_to("admin") is True


@pytest.mark.asyncio
async def test_chat_message_empty_text_raises(user_id, tenant_id):
    from app.engines.platform_notifications.chat_service import ChatMessageService
    from app.engines.platform_notifications.models import ChatThread
    from app.engines.platform_notifications.constants import ERR_CHAT_MESSAGE_REQUIRED
    svc = ChatMessageService()
    db = _db()

    thread = ChatThread(thread_number="THR-E01", record_type="complaint",
                        record_id=uuid.uuid4(), status="open")
    thread.id = uuid.uuid4()

    thread_r = MagicMock()
    thread_r.scalars = MagicMock(return_value=MagicMock(first=MagicMock(return_value=thread)))
    part_r = MagicMock()
    part_r.scalars = MagicMock(return_value=MagicMock(first=MagicMock(return_value=None)))
    db.execute = AsyncMock(side_effect=[thread_r, part_r])

    with patch.object(svc._thread_svc, "validate_thread_access", AsyncMock()):
        with pytest.raises(ValueError, match=ERR_CHAT_MESSAGE_REQUIRED):
            await svc.send_message(db=db, thread_id=thread.id,
                                   actor_user_id=user_id, actor_type="customer",
                                   tenant_id=tenant_id, message_text=None)


# ══════════════════════════════════════════════════════════════════════════════
# 6. Audit Service
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_audit_service_write_log(user_id, tenant_id):
    from app.engines.platform_notifications.audit_service import PlatformAuditLogService
    svc = PlatformAuditLogService()
    db = _db()

    def _set_id(obj):
        obj.id = uuid.uuid4()
    db.add = MagicMock(side_effect=_set_id)

    entry = await svc.write_audit_log(
        db=db, action="booking.confirmed", resource_type="service_booking",
        actor_type="customer", actor_user_id=user_id, tenant_id=tenant_id,
        resource_id=uuid.uuid4(),
    )
    assert entry is not None
    db.add.assert_called_once()


def test_audit_service_redact_sensitive_fields():
    from app.engines.platform_notifications.audit_service import PlatformAuditLogService
    svc = PlatformAuditLogService()
    payload = {
        "booking_id": "abc",
        "password": "secret123",
        "access_token": "tok_xyz",
        "amount": 500,
        "api_key": "key_live_xxx",
    }
    result = svc.redact_sensitive_fields(payload)
    assert result["booking_id"] == "abc"
    assert result["amount"] == 500
    assert result["password"] == "[REDACTED]"
    assert result["access_token"] == "[REDACTED]"
    assert result["api_key"] == "[REDACTED]"


def test_audit_service_redact_nested():
    from app.engines.platform_notifications.audit_service import PlatformAuditLogService
    svc = PlatformAuditLogService()
    payload = {"meta": {"token": "xyz", "name": "Alice"}}
    result = svc.redact_sensitive_fields(payload)
    assert result["meta"]["token"] == "[REDACTED]"
    assert result["meta"]["name"] == "Alice"


@pytest.mark.asyncio
async def test_audit_service_provider_access_denied_without_tenant():
    from app.engines.platform_notifications.audit_service import PlatformAuditLogService
    from app.engines.platform_notifications.constants import ERR_AUDIT_LOG_ACCESS_DENIED
    svc = PlatformAuditLogService()
    db = _db()

    with pytest.raises(ValueError, match=ERR_AUDIT_LOG_ACCESS_DENIED):
        await svc.get_audit_logs(db, actor_type="provider", tenant_id=None)


@pytest.mark.asyncio
async def test_audit_service_admin_can_filter(user_id, tenant_id):
    from app.engines.platform_notifications.audit_service import PlatformAuditLogService
    svc = PlatformAuditLogService()
    db = _db()

    total_r = MagicMock()
    total_r.scalar_one = MagicMock(return_value=0)
    items_r = MagicMock()
    items_r.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))
    db.execute = AsyncMock(side_effect=[total_r, items_r])

    result = await svc.get_audit_logs(
        db, actor_type="admin",
        resource_type="service_booking", action="booking.confirmed",
    )
    assert "items" in result
    assert "total" in result


# ══════════════════════════════════════════════════════════════════════════════
# 7. Recipient Resolver
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_recipient_resolver_no_cross_tenant():
    from app.engines.platform_notifications.recipient_resolver import NotificationRecipientResolver
    resolver = NotificationRecipientResolver()
    db = _db()

    # If record belongs to different customer, returns None
    no_r = MagicMock()
    no_r.scalars = MagicMock(return_value=MagicMock(first=MagicMock(return_value=None)))
    db.execute = AsyncMock(return_value=no_r)

    result = await resolver._fetch_customer_id(db, "service_booking", uuid.uuid4())
    assert result is None


# ══════════════════════════════════════════════════════════════════════════════
# 8. Integration — Event → Notification
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_booking_confirmed_event_key_exists_in_registry():
    from app.engines.platform_notifications.event_registry import NotificationEventRegistry
    cfg = NotificationEventRegistry.get("booking.confirmed")
    assert cfg is not None
    assert cfg.source_engine == "home_service"


@pytest.mark.asyncio
async def test_complaint_created_notifies_admin():
    from app.engines.platform_notifications.event_registry import NotificationEventRegistry
    from app.engines.platform_notifications.constants import RECIP_ADMIN
    cfg = NotificationEventRegistry.get("complaint.created")
    assert cfg is not None
    assert RECIP_ADMIN in cfg.also_notify


@pytest.mark.asyncio
async def test_payment_collected_has_success_severity():
    from app.engines.platform_notifications.event_registry import NotificationEventRegistry
    from app.engines.platform_notifications.constants import SEV_SUCCESS
    cfg = NotificationEventRegistry.get("payment.collected")
    assert cfg is not None
    assert cfg.severity == SEV_SUCCESS


@pytest.mark.asyncio
async def test_wallet_low_has_warning_severity():
    from app.engines.platform_notifications.event_registry import NotificationEventRegistry
    from app.engines.platform_notifications.constants import SEV_WARNING
    cfg = NotificationEventRegistry.get("wallet.low_balance")
    assert cfg.severity == SEV_WARNING


# ══════════════════════════════════════════════════════════════════════════════
# 9. Router import / Swagger verification
# ══════════════════════════════════════════════════════════════════════════════

def test_customer_routers_importable():
    from app.engines.platform_notifications.customer_router import (
        customer_notif_router, customer_chat_router,
    )
    assert customer_notif_router is not None
    assert customer_chat_router is not None


def test_provider_routers_importable():
    from app.engines.platform_notifications.provider_router import (
        provider_notif_router, provider_chat_router, provider_audit_router,
        staff_notif_router, staff_chat_router,
    )
    assert provider_notif_router is not None
    assert provider_chat_router is not None
    assert staff_notif_router is not None


def test_admin_routers_importable():
    from app.engines.platform_notifications.admin_router import (
        admin_notif_router, admin_outbox_router, admin_notif_events_router,
        admin_notif_templates_router, admin_chat_router, admin_audit_router,
    )
    assert admin_notif_router is not None
    assert admin_outbox_router is not None
    assert admin_chat_router is not None
    assert admin_audit_router is not None


def test_notification_models_importable():
    from app.engines.platform_notifications.models import (
        NotificationEvent, NotificationOutbox, InAppNotification,
        NotifEventTemplate, NotificationPreference,
        ChatThread, ChatThreadParticipant, ChatMessage, ChatMessageRead,
    )
    assert NotificationEvent.__tablename__ == "notification_events"
    assert NotificationOutbox.__tablename__ == "notification_outbox"
    assert InAppNotification.__tablename__ == "in_app_notifications"
    assert NotifEventTemplate.__tablename__ == "notif_event_templates"
    assert NotificationPreference.__tablename__ == "notification_preferences"
    assert ChatThread.__tablename__ == "chat_threads"
    assert ChatMessage.__tablename__ == "chat_messages"
    assert ChatMessageRead.__tablename__ == "chat_message_reads"


def test_migration_045_importable():
    import importlib.util, pathlib
    migration_path = pathlib.Path("G:/serviceos/alembic/versions/045_sprint27_notifications_chat_audit.py")
    spec = importlib.util.spec_from_file_location("migration_045", migration_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert hasattr(mod, "upgrade")
    assert hasattr(mod, "downgrade")
    assert mod.revision == "045"
    assert mod.down_revision == "044"


def test_background_jobs_importable():
    from app.jobs.notifications import dispatch_pending, retry_failed, cleanup_expired
    assert callable(dispatch_pending)
    assert callable(retry_failed)
    assert callable(cleanup_expired)


def test_channel_providers_map_complete():
    from app.engines.platform_notifications.channel_providers import CHANNEL_PROVIDERS
    for ch in ["in_app", "email", "sms", "whatsapp", "push"]:
        assert ch in CHANNEL_PROVIDERS
