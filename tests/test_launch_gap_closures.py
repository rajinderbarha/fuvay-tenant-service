"""Regression coverage for the launch-readiness gaps closed after the audit."""
from datetime import time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
import uuid

import pytest

from app.config import Settings
from app.engines.messaging_gateway.constants import CHANNEL_INSTAGRAM, CHANNEL_WHATSAPP
from app.engines.messaging_gateway.meta_client import parse_delivery_statuses
from app.jobs.booking_reminders import _operational_recipients, _start_time


ROOT = Path(__file__).resolve().parents[1]


def test_whatsapp_delivery_and_failure_statuses_are_normalized():
    payload = {
        "object": "whatsapp_business_account",
        "entry": [{"id": "waba-1", "changes": [{"value": {
            "metadata": {"phone_number_id": "phone-1"},
            "statuses": [
                {"id": "wamid.1", "status": "delivered", "timestamp": "1788432000", "recipient_id": "91999"},
                {"id": "wamid.2", "status": "failed", "timestamp": "1788432060", "recipient_id": "91999"},
            ],
        }}]}],
    }
    events = parse_delivery_statuses(payload, expected_channel=CHANNEL_WHATSAPP)
    assert [(event.provider_message_id, event.status) for event in events] == [
        ("wamid.1", "delivered"), ("wamid.2", "failed")
    ]
    assert all(event.business_id == "phone-1" for event in events)


def test_instagram_read_watermark_is_normalized_without_becoming_inbound_chat():
    payload = {"object": "instagram", "entry": [{
        "id": "page-1",
        "messaging": [{
            "recipient": {"id": "page-1"},
            "timestamp": 1788432000000,
            "read": {"watermark": 1788431999000},
        }],
    }]}
    events = parse_delivery_statuses(payload, expected_channel=CHANNEL_INSTAGRAM)
    assert len(events) == 1
    assert events[0].status == "read"
    assert events[0].provider_message_id == "watermark:1788431999000"


@pytest.mark.parametrize(("window", "expected"), [
    ("10:00-11:00", time(10, 0)),
    ("18.30 - 19.30", time(18, 30)),
    ("2:30 PM - 3:30 PM", time(14, 30)),
    (None, None),
    ("your scheduled time", None),
])
def test_booking_reminder_parses_supported_time_windows(window, expected):
    assert _start_time(window) == expected


def test_booking_reminder_locks_only_the_non_nullable_job_row():
    source = (ROOT / "app/jobs/booking_reminders.py").read_text(encoding="utf-8")
    assert ".with_for_update(of=ServiceJob, skip_locked=True)" in source


def test_operational_visit_reminder_is_role_aware_and_idempotent():
    worker = (ROOT / "app/jobs/booking_reminders.py").read_text(encoding="utf-8")
    model = (ROOT / "app/engines/final_records/models.py").read_text(encoding="utf-8")
    reschedule = (ROOT / "app/engines/home_service_assignment/service.py").read_text(encoding="utf-8")
    migration = (ROOT / "alembic/versions/361_provider_staff_visit_reminders.py").read_text(encoding="utf-8")
    registry = (ROOT / "app/engines/platform_notifications/event_registry.py").read_text(encoding="utf-8")

    assert "0 < minutes_until <= 30" in worker
    assert '"recipient_type": "provider"' in worker
    assert '"recipient_type": "staff"' in worker
    assert 'f"/staff/jobs/{job.id}"' in worker
    assert 'f"/home-services/bookings-jobs?job_id={job.id}"' in worker
    assert "_existing_operational_reminder" in worker
    assert "NotificationOutbox.recipient_type == recipient_type" in worker
    for marker in ("provider_reminder_30m_sent_at", "staff_reminder_30m_sent_at"):
        assert marker in worker
        assert marker in model
        assert f"job.{marker} = None" in reschedule
        assert marker in migration
    assert "EVT_JOB_VISIT_REMINDER_30M" in registry
    assert "CHANNEL_IN_APP, CHANNEL_PUSH" in registry
    assert "is_mandatory=True" in registry
    notification_service = (ROOT / "app/engines/platform_notifications/notification_service.py").read_text(encoding="utf-8")
    assert "cfg.is_mandatory and channel == CHANNEL_IN_APP" in notification_service


@pytest.mark.asyncio
async def test_operational_recipient_resolution_maps_team_member_to_login_user():
    tenant_id = uuid.uuid4()
    owner_id = uuid.uuid4()
    staff_member_id = uuid.uuid4()
    staff_user_id = uuid.uuid4()
    job = SimpleNamespace(tenant_id=tenant_id, assigned_staff_id=staff_member_id)

    owner_result = MagicMock()
    owner_result.scalars.return_value.all.return_value = [owner_id, owner_id]
    member_result = MagicMock()
    member_result.scalar_one_or_none.return_value = staff_user_id
    user_result = MagicMock()
    user_result.scalar_one_or_none.return_value = staff_user_id
    db = SimpleNamespace(execute=AsyncMock(side_effect=[owner_result, member_result, user_result]))

    providers, staff = await _operational_recipients(db, job)

    assert providers == [{"user_id": str(owner_id), "recipient_type": "provider"}]
    assert staff == [{"user_id": str(staff_user_id), "recipient_type": "staff"}]


def test_operational_visit_event_is_mandatory_in_app_with_push_fanout():
    from app.engines.platform_notifications.constants import (
        CHANNEL_IN_APP,
        CHANNEL_PUSH,
        EVT_JOB_VISIT_REMINDER_30M,
    )
    from app.engines.platform_notifications.event_registry import NotificationEventRegistry

    cfg = NotificationEventRegistry.get(EVT_JOB_VISIT_REMINDER_30M)
    assert cfg is not None
    assert cfg.default_channels == [CHANNEL_IN_APP, CHANNEL_PUSH]
    assert cfg.is_mandatory is True


def test_provider_media_workspace_exposes_quota_and_deletion_controls():
    layout = (ROOT / "frontend/tenant-portal/components/layout/TenantLayout.tsx").read_text(encoding="utf-8")
    media_page = (ROOT / "frontend/tenant-portal/app/(tenant)/media/page.tsx").read_text(encoding="utf-8")
    dashboard = (ROOT / "frontend/tenant-portal/app/(tenant)/dashboard/page.tsx").read_text(encoding="utf-8")
    api = (ROOT / "frontend/tenant-portal/lib/api.ts").read_text(encoding="utf-8")
    asset_service = (ROOT / "app/engines/media/asset_service.py").read_text(encoding="utf-8")
    assert 'href: "/media"' in layout
    assert "mediaApi.getQuota" in media_page
    assert "mediaAssetApi.delete" in media_page
    assert "Your 1 GB media storage is full" in media_page
    assert "Media storage is full" in dashboard
    assert asset_service.index("assert_storage_capacity") < asset_service.index("store_file")
    assert "/v1/media" in api


def test_removed_pricing_modules_and_admin_routes_cannot_return():
    assert not (ROOT / "app/engines/admin_catalog/bargain_engine.py").exists()
    assert not (ROOT / "app/engines/admin_catalog/bargain_schemas.py").exists()
    router = (ROOT / "app/engines/admin_catalog/admin_router.py").read_text(encoding="utf-8")
    service = (ROOT / "app/engines/admin_catalog/service.py").read_text(encoding="utf-8")
    assert "/pricing/bargain-rules" not in router
    assert "/pricing/provider-overrides" not in router
    assert "class BargainRule" not in (ROOT / "app/engines/admin_catalog/models.py").read_text(encoding="utf-8")
    assert "evaluate_bargain" not in service


def test_masked_calling_cannot_be_half_configured():
    with pytest.raises(ValueError, match="Masked calling is enabled but missing"):
        Settings(
            APP_ENV="testing",
            MASKED_CALLING_PROVIDER="http",
            MASKED_CALLING_API_BASE="https://calling.example",
            MASKED_CALLING_API_KEY="key",
        )
