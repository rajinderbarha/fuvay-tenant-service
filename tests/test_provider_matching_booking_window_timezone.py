from datetime import datetime

import pytest

from app.engines.home_service_booking import provider_slot_service
from app.engines.provider_portal.router import _minutes_until_requested_at


def test_naive_requested_slot_uses_tenant_local_clock(monkeypatch):
    """The timeout worker sends a naive local slot timestamp to matching."""
    monkeypatch.setattr(
        provider_slot_service,
        "_tenant_now",
        lambda settings: datetime(2026, 9, 13, 12, 0),
    )

    minutes = _minutes_until_requested_at(
        "2026-09-13T14:30", "Asia/Kolkata"
    )

    assert minutes == pytest.approx(150)


def test_explicit_offset_requested_slot_remains_supported():
    minutes = _minutes_until_requested_at(
        "2099-09-13T14:30:00+05:30", "Asia/Kolkata"
    )

    assert minutes > 0
