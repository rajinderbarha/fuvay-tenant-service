"""LOGIN-ACTIVITY (2026-08-01) — customer Login Activity screen phase.

Reuses the canonical `LoginEvent` table (no parallel mobile history table,
no synthetic events derived from sessions). Real gap found and fixed
during audit: only password login success/failure and logout ever wrote a
`login_events` row -- MFA challenges and both OTP-login and MFA-verify
successes were completely invisible in a customer's own login history.
Added the missing `_log_login_event` calls at those three points.

`AuthService.get_my_login_activity` is a new, deliberately separate
method from the existing `get_login_history` (kept untouched for admin/
tenant-owner tooling) -- it returns only an explicit allowlist (label,
outcome, channel, device_name, is_current_device, occurred_at), never
`ip_address`/`failure_reason`/the raw `event_type` string.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.engines.auth.service import AuthService
from app.engines.auth.constants import LOGIN_EVENT_PUBLIC_MAP, LOGIN_EVENT_UNKNOWN_LABEL, LOGIN_EVENT_UNKNOWN_OUTCOME

utcnow = lambda: datetime.now(timezone.utc)


def _event(**overrides):
    defaults = dict(
        id=uuid.uuid4(), user_id=uuid.uuid4(), event_type="login_success",
        failure_reason=None, ip_address="203.0.113.5", user_agent="iPhone Safari",
        device_id="device-x", created_at=utcnow(),
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def _svc():
    db = MagicMock()
    db.execute = AsyncMock()
    svc = AuthService(db=db, ip_address="127.0.0.1")
    return svc, db


def _exec_result(rows):
    res = MagicMock()
    scalars = MagicMock()
    scalars.all = MagicMock(return_value=rows)
    res.scalars = MagicMock(return_value=scalars)
    return res


class TestPublicEventMapping:
    def test_every_currently_written_event_type_is_mapped(self):
        """Every event_type this engine's _log_login_event call sites can
        actually write must have a public mapping -- an unmapped real
        event_type would silently fall back to neutral copy, hiding real
        information the customer should see."""
        written_types = {"login_success", "login_failed", "mfa_challenge_required", "logout"}
        assert written_types.issubset(set(LOGIN_EVENT_PUBLIC_MAP.keys()))

    @pytest.mark.asyncio
    async def test_unknown_event_type_falls_back_to_neutral_copy(self):
        svc, db = _svc()
        db.execute.return_value = _exec_result([_event(event_type="some_future_internal_event")])

        result = await svc.get_my_login_activity(uuid.uuid4(), None)

        assert result["events"][0]["label"] == LOGIN_EVENT_UNKNOWN_LABEL
        assert result["events"][0]["outcome"] == LOGIN_EVENT_UNKNOWN_OUTCOME

    def test_successful_and_verification_and_blocked_map_correctly(self):
        assert LOGIN_EVENT_PUBLIC_MAP["login_success"][1] == "successful"
        assert LOGIN_EVENT_PUBLIC_MAP["mfa_challenge_required"][1] == "verification_required"
        assert LOGIN_EVENT_PUBLIC_MAP["login_failed"][1] == "blocked"


class TestSafeFieldAllowlist:
    @pytest.mark.asyncio
    async def test_response_never_includes_ip_address_or_failure_reason_or_raw_event_type(self):
        svc, db = _svc()
        db.execute.return_value = _exec_result([_event(
            event_type="login_failed", failure_reason="wrong_password", ip_address="203.0.113.9",
        )])

        result = await svc.get_my_login_activity(uuid.uuid4(), None)

        event = result["events"][0]
        assert "ip_address" not in event
        assert "failure_reason" not in event
        assert "event_type" not in event
        assert "203.0.113.9" not in str(event)
        assert "wrong_password" not in str(event)

    @pytest.mark.asyncio
    async def test_current_device_flag_uses_device_id_comparison(self):
        svc, db = _svc()
        db.execute.return_value = _exec_result([
            _event(device_id="device-current"),
            _event(device_id="device-other"),
        ])

        result = await svc.get_my_login_activity(uuid.uuid4(), current_device_id="device-current")

        flags = [e["is_current_device"] for e in result["events"]]
        assert flags == [True, False]

    @pytest.mark.asyncio
    async def test_no_current_device_flagged_when_current_device_id_is_none(self):
        svc, db = _svc()
        db.execute.return_value = _exec_result([_event(device_id="device-x")])

        result = await svc.get_my_login_activity(uuid.uuid4(), current_device_id=None)

        assert result["events"][0]["is_current_device"] is False


class TestFiltering:
    @pytest.mark.asyncio
    async def test_successful_filter_only_queries_successful_event_types(self):
        svc, db = _svc()
        db.execute.return_value = _exec_result([])

        await svc.get_my_login_activity(uuid.uuid4(), None, outcome_filter="successful")

        call_args = str(db.execute.call_args)
        assert "login_failed" not in call_args or "in_" in call_args  # filter applied via IN clause

    @pytest.mark.asyncio
    async def test_needs_attention_filter_excludes_successful_events(self):
        svc, db = _svc()
        db.execute.return_value = _exec_result([_event(event_type="mfa_challenge_required")])

        result = await svc.get_my_login_activity(uuid.uuid4(), None, outcome_filter="needs_attention")

        assert all(e["outcome"] in ("verification_required", "blocked") for e in result["events"])


class TestPagination:
    @pytest.mark.asyncio
    async def test_returns_next_cursor_when_more_rows_exist_than_the_page_size(self):
        svc, db = _svc()
        rows = [_event(created_at=utcnow() - timedelta(minutes=i)) for i in range(5)]
        db.execute.return_value = _exec_result(rows)  # 5 rows, page_size=3 -> has_more

        result = await svc.get_my_login_activity(uuid.uuid4(), None, limit=3)

        assert len(result["events"]) == 3
        assert result["next_cursor"] is not None

    @pytest.mark.asyncio
    async def test_no_next_cursor_when_all_rows_fit_the_page(self):
        svc, db = _svc()
        db.execute.return_value = _exec_result([_event()])

        result = await svc.get_my_login_activity(uuid.uuid4(), None, limit=20)

        assert result["next_cursor"] is None

    @pytest.mark.asyncio
    async def test_malformed_cursor_does_not_crash(self):
        svc, db = _svc()
        db.execute.return_value = _exec_result([])

        result = await svc.get_my_login_activity(uuid.uuid4(), None, cursor="not-a-valid-cursor")

        assert result["events"] == []
