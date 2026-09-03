"""Regression coverage for the launch-readiness gaps closed after the audit."""
from datetime import time
from pathlib import Path

import pytest

from app.config import Settings
from app.engines.messaging_gateway.constants import CHANNEL_INSTAGRAM, CHANNEL_WHATSAPP
from app.engines.messaging_gateway.meta_client import parse_delivery_statuses
from app.jobs.booking_reminders import _start_time


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
