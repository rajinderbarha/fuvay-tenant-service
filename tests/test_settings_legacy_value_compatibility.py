"""Regression tests for settings saved before the value-wrapper migration."""
from types import SimpleNamespace

import pytest

from app.engines.settings_engine.service import SettingsService


@pytest.fixture
def service():
    return SettingsService(db=SimpleNamespace())


@pytest.mark.parametrize(
    ("stored", "expected"),
    [
        ({"v": False}, False),
        ({"v": 0}, 0),
        ({"v": ""}, ""),
        (False, False),
        (0, 0),
        ("legacy", "legacy"),
        (["one", "two"], ["one", "two"]),
        ({"legacy": True}, {"legacy": True}),
        (None, None),
    ],
)
def test_unwrap_supports_wrapped_and_legacy_json_values(service, stored, expected):
    assert service._unwrap(SimpleNamespace(value=stored)) == expected


def test_unwrap_supports_missing_setting(service):
    assert service._unwrap(None) is None


def test_setting_serialization_keeps_falsey_legacy_values(service):
    setting = SimpleNamespace(
        key="payment_collection_enabled",
        label="Payment collection",
        value=False,
        setting_type="boolean",
        description="Whether the platform collects payment.",
        is_public=False,
        category="pricing",
        allowed_values_json=None,
        is_secret=False,
        risk_level="high",
        requires_approval=True,
        requires_restart=False,
        is_runtime_editable=True,
        owner_module="settings",
        status="active",
        updated_at=None,
    )

    result = service._setting_to_dict(setting)

    assert result["value"] is False
