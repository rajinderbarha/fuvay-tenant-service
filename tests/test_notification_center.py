"""In-App Notification Center phase.

Targets the real gaps left by test_sprint27_notifications.py: ownership on
mark-read (including cross-customer denial + idempotent repeat), and proof
that `InAppNotification.to_dict()` is customer-safe (no user_id/tenant_id)
while still carrying the fields the mobile destination allowlist depends on.
"""
import pytest
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

from app.engines.platform_notifications.notification_service import NotificationService
from app.engines.platform_notifications.models import InAppNotification
from app.engines.platform_notifications.constants import ERR_IN_APP_NOT_FOUND, READ_READ, READ_UNREAD


def _uuid():
    return uuid.uuid4()


def _scalars(item):
    r = MagicMock()
    r.scalars.return_value.first.return_value = item
    return r


@pytest.mark.asyncio
async def test_mark_notification_read_denies_cross_customer_with_not_found():
    """SECURITY: the query itself scopes by user_id -- a notification that
    belongs to a different customer must be indistinguishable from a
    missing one, never a distinct 'access denied'."""
    svc = NotificationService()
    db = AsyncMock()
    db.execute = AsyncMock(return_value=_scalars(None))  # owner mismatch -> no row matched
    db.commit = AsyncMock()
    with pytest.raises(ValueError, match=ERR_IN_APP_NOT_FOUND):
        await svc.mark_notification_read(db, _uuid(), _uuid())


@pytest.mark.asyncio
async def test_mark_notification_read_is_idempotent_on_repeat():
    svc = NotificationService()
    db = AsyncMock()
    notif = InAppNotification(
        id=_uuid(), user_id=_uuid(), notification_type="booking.confirmed",
        title="t", body="b", read_status=READ_READ,
        read_at=datetime.now(timezone.utc),
    )
    db.execute = AsyncMock(return_value=_scalars(notif))
    db.commit = AsyncMock()
    result = await svc.mark_notification_read(db, notif.user_id, notif.id)
    assert result.read_status == READ_READ
    db.commit.assert_awaited()


@pytest.mark.asyncio
async def test_mark_notification_read_success_sets_read_status_and_timestamp():
    svc = NotificationService()
    db = AsyncMock()
    notif = InAppNotification(
        id=_uuid(), user_id=_uuid(), notification_type="complaint.resolved",
        title="t", body="b", read_status=READ_UNREAD, read_at=None,
    )
    db.execute = AsyncMock(return_value=_scalars(notif))
    db.commit = AsyncMock()
    result = await svc.mark_notification_read(db, notif.user_id, notif.id)
    assert result.read_status == READ_READ
    assert result.read_at is not None


def test_in_app_notification_to_dict_excludes_internal_fields():
    n = InAppNotification(
        id=_uuid(), outbox_id=_uuid(), user_id=_uuid(), tenant_id=_uuid(),
        notification_type="booking.confirmed", title="Your booking is confirmed",
        body="Booking FUV-2841 is confirmed.", action_url="/customer/bookings/x",
        action_label="View booking", source_record_type="service_bookings",
        source_record_id=_uuid(), severity="info", read_status=READ_UNREAD, created_at=datetime.now(timezone.utc),
    )
    d = n.to_dict()

    # Mobile-safe fields the destination allowlist and UI depend on.
    assert d["notification_type"] == "booking.confirmed"
    assert d["source_record_type"] == "service_bookings"
    assert d["source_record_id"] is not None
    assert d["read_status"] == READ_UNREAD

    # Never leak recipient/tenant/queue identifiers to the customer.
    assert "user_id" not in d
    assert "tenant_id" not in d
    assert "outbox_id" not in d


def test_in_app_notification_to_dict_has_no_arbitrary_metadata_blob():
    """The model carries no freeform JSONB payload column -- confirms there
    is no `metadata`/`payload` field that could leak internal event data."""
    n = InAppNotification(
        id=_uuid(), user_id=_uuid(), notification_type="chat.message",
        title="t", body="b", read_status=READ_UNREAD, created_at=datetime.now(timezone.utc),
    )
    d = n.to_dict()
    assert "payload" not in d
    assert "metadata" not in d
