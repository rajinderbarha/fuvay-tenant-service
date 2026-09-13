"""Runtime and UI regression guards for the Security Policies workspace."""
from __future__ import annotations

import base64
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.engines.auth.service import AuthService
from app.engines.auth.constants import REDIS_FAILED_ATTEMPTS_PREFIX
from app.engines.auth.utils import create_access_token, validate_password_strength
from app.engines.security.admin_service import (
    POLICY_DEFAULTS, POLICY_RECOMMENDED, POLICY_RULES, SecurityAdminService,
)
from app.exceptions import ServiceOSException


ROOT = Path(__file__).resolve().parents[1]
NEW_CONTROLS = {
    "temporary_lockout_minutes", "access_token_lifetime_minutes",
    "refresh_token_lifetime_days", "password_min_length",
    "password_history_count",
}


def test_migration_and_ui_expose_only_runtime_controls():
    migration = (ROOT / "alembic/versions/362_security_policy_enterprise_controls.py").read_text()
    page = (ROOT / "frontend/super-admin/app/admin/security/page.tsx").read_text()
    assert NEW_CONTROLS <= set(POLICY_RULES) == set(POLICY_DEFAULTS) == set(POLICY_RECOMMENDED)
    for key in NEW_CONTROLS:
        assert key in migration
        assert key in page
    assert 'down_revision = "361"' in migration
    assert "Use recommended value" in page
    assert "Change reason" in page
    assert "MFA scopes enabled" in page
    assert "mfa_required_tenant_owner" not in page


def test_password_minimum_is_configurable_without_weakening_baseline():
    assert not validate_password_strength("Password123!", min_length=12)
    assert any("at least 16" in error for error in validate_password_strength(
        "Password123!", min_length=16))
    assert any("at least 8" in error for error in validate_password_strength(
        "Ab1!", min_length=2))


def test_access_token_expiry_is_capped_by_session_expiry():
    deadline = datetime.now(timezone.utc) + timedelta(seconds=40)
    token, _ = create_access_token(
        user_id="user", email="user@example.com", role="staff",
        tenant_id=None, tenant_name=None, plan_type=None,
        session_id="session", device_id="web", is_mfa_enabled=False,
        onboarding_complete=True, enabled_engines=[],
        expires_minutes=60, expires_at=deadline,
    )
    payload = token.split(".")[1]
    claims = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
    assert claims["exp"] <= int(deadline.timestamp())
    assert claims["exp"] > int(datetime.now(timezone.utc).timestamp())


@pytest.mark.asyncio
async def test_refresh_and_access_lifetime_cannot_exceed_session():
    service = AuthService.__new__(AuthService)
    values = {"access_token_lifetime_minutes": 120, "refresh_token_lifetime_days": 7}
    service._security_policy_value = AsyncMock(side_effect=lambda key, default: values[key])
    deadline = datetime.now(timezone.utc) + timedelta(minutes=12)
    minutes, refresh_expires = await service._token_lifetimes(
        SimpleNamespace(expires_at=deadline))
    assert minutes <= 12
    assert refresh_expires == deadline


@pytest.mark.asyncio
async def test_failed_login_counter_uses_configured_lock_duration():
    service = AuthService.__new__(AuthService)
    service.redis = MagicMock(
        incr=AsyncMock(return_value=3), expire=AsyncMock()
    )
    count = await service._increment_failed("Owner@Example.com", 45)
    assert count == 3
    service.redis.expire.assert_awaited_once_with(
        f"{REDIS_FAILED_ATTEMPTS_PREFIX}owner@example.com", 45 * 60
    )


@pytest.mark.asyncio
async def test_policy_update_rejects_out_of_range_and_boolean_as_number():
    service = SecurityAdminService(MagicMock())
    with pytest.raises(ServiceOSException):
        await service.update_policy("password_min_length", 7, "security review")
    with pytest.raises(ServiceOSException):
        await service.update_policy("temporary_lockout_minutes", True, "security review")
    with pytest.raises(ServiceOSException):
        await service.update_policy("access_token_lifetime_minutes", 481, "security review")


@pytest.mark.asyncio
async def test_policy_api_returns_baseline_and_recommended_values():
    row = MagicMock()
    row.to_dict.return_value = {
        "id": "policy", "policy_key": "password_min_length",
        "policy_value": 8,
    }
    db = MagicMock()
    db.execute = AsyncMock(return_value=MagicMock(
        scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[row])))))
    result = await SecurityAdminService(db).get_policies()
    policy = result["policies"][0]
    assert policy["default_value"] == 8
    assert policy["recommended_value"] == 12
    assert policy["is_default"] is True
    assert policy["is_recommended"] is False


def test_all_password_creation_paths_read_the_runtime_minimum():
    paths = (
        "app/engines/auth/service.py",
        "app/engines/public_registration/service.py",
        "app/engines/provider_portal/router.py",
    )
    for path in paths:
        source = (ROOT / path).read_text(encoding="utf-8")
        assert "min_length=minimum_length" in source
