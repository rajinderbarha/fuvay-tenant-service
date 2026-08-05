"""MANAGE-SESSIONS (2026-08-01) — customer Manage Sessions screen phase.

Real defects found and fixed in `AuthService` during audit:

1. `list_sessions` identified "current session" by comparing the caller's
   `device_id` against each stored session's `device_id` -- multiple
   sessions can legitimately share a device_id (reinstall, cleared app
   storage), so this was never a reliable signal. Now uses the
   authoritative `session_id` claim carried in the access token itself.
2. `list_sessions` returned the full `ip_address` in the customer-facing
   payload -- removed; no geo-lookup capability exists in this codebase,
   so no approximate-location field is fabricated in its place either.
3. `logout_all` had no way to exclude the caller's own session from
   revocation -- `POST /v1/auth/sessions/revoke-all-other`'s own
   docstring promised "except the current one" while the underlying query
   had no exclusion filter at all, silently revoking literally every
   session including the caller's own. Added a real `exclude_session_id`
   parameter; the revoke-all-other endpoint now passes it.
"""
from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.engines.auth.service import AuthService
from app.exceptions import ServiceOSException


def _exec_result(*, scalars_all=None):
    res = MagicMock()
    scalars = MagicMock()
    scalars.all = MagicMock(return_value=scalars_all or [])
    res.scalars = MagicMock(return_value=scalars)
    return res


def _db():
    db = MagicMock()
    db.execute = AsyncMock()
    db.commit = AsyncMock()
    db.add = MagicMock()
    return db


def _svc(db=None):
    db = db or _db()
    svc = AuthService(db=db, ip_address="127.0.0.1")
    svc._audit = AsyncMock()
    svc._publish_event = AsyncMock()
    svc._blacklist = AsyncMock()
    return svc, db


def _session(**overrides):
    from datetime import datetime, timezone
    defaults = dict(
        id=uuid.uuid4(), user_id=uuid.uuid4(), device_id="device-x",
        device_name="iPhone", device_type="mobile", ip_address="203.0.113.5",
        is_trusted=False, is_approved=True, revoked_at=None,
        last_active_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


class TestCurrentSessionIdentification:
    @pytest.mark.asyncio
    async def test_current_session_identified_by_session_id_not_device_id(self):
        """Two sessions sharing the same device_id (reinstall scenario) --
        only the one matching the token's real session_id is current."""
        user_id = uuid.uuid4()
        real_current = _session(user_id=user_id, device_id="device-shared")
        stale_other = _session(user_id=user_id, device_id="device-shared")
        svc, db = _svc()
        db.execute.return_value = _exec_result(scalars_all=[real_current, stale_other])

        result = await svc.list_sessions(user_id, real_current.id)

        current_flags = {str(s["session_id"]): s["is_current"] for s in result}
        assert current_flags[str(real_current.id)] is True
        assert current_flags[str(stale_other.id)] is False

    @pytest.mark.asyncio
    async def test_no_session_marked_current_when_session_id_is_none(self):
        user_id = uuid.uuid4()
        svc, db = _svc()
        db.execute.return_value = _exec_result(scalars_all=[_session(user_id=user_id)])

        result = await svc.list_sessions(user_id, None)

        assert all(s["is_current"] is False for s in result)


class TestCustomerSafeFields:
    @pytest.mark.asyncio
    async def test_full_ip_address_is_never_returned(self):
        user_id = uuid.uuid4()
        svc, db = _svc()
        db.execute.return_value = _exec_result(scalars_all=[_session(user_id=user_id, ip_address="203.0.113.5")])

        result = await svc.list_sessions(user_id, None)

        assert "ip_address" not in result[0]
        assert "203.0.113.5" not in str(result[0])

    @pytest.mark.asyncio
    async def test_no_token_values_are_ever_present(self):
        user_id = uuid.uuid4()
        svc, db = _svc()
        db.execute.return_value = _exec_result(scalars_all=[_session(user_id=user_id)])

        result = await svc.list_sessions(user_id, None)

        blob = str(result[0]).lower()
        assert "token" not in blob and "secret" not in blob

    @pytest.mark.asyncio
    async def test_channel_is_derived_from_real_device_type_not_fabricated(self):
        user_id = uuid.uuid4()
        svc, db = _svc()
        db.execute.return_value = _exec_result(scalars_all=[
            _session(user_id=user_id, device_type="mobile"),
        ])

        result = await svc.list_sessions(user_id, None)

        assert result[0]["channel"] == "Mobile"


class TestRevokeAllOtherSessions:
    @pytest.mark.asyncio
    async def test_excludes_the_current_session_from_revocation(self):
        user_id = uuid.uuid4()
        current = _session(user_id=user_id)
        other = _session(user_id=user_id)
        svc, db = _svc()
        # Query filters out the excluded session at the DB layer -- only
        # `other` comes back from the mocked execute.
        db.execute.return_value = _exec_result(scalars_all=[other])

        count = await svc.logout_all(str(user_id), "", exclude_session_id=current.id)

        assert count == 1
        assert other.revoked_at is not None
        assert current.revoked_at is None

    @pytest.mark.asyncio
    async def test_does_not_blacklist_any_jti_when_excluding_current(self):
        user_id = uuid.uuid4()
        svc, db = _svc()
        db.execute.return_value = _exec_result(scalars_all=[])

        await svc.logout_all(str(user_id), "", exclude_session_id=uuid.uuid4())

        svc._blacklist.assert_not_called()

    @pytest.mark.asyncio
    async def test_full_global_logout_still_blacklists_and_revokes_everything(self):
        user_id = uuid.uuid4()
        svc, db = _svc()
        db.execute.return_value = _exec_result(scalars_all=[_session(user_id=user_id), _session(user_id=user_id)])

        count = await svc.logout_all(str(user_id), "real-jti", exclude_session_id=None)

        assert count == 2
        svc._blacklist.assert_awaited_once_with("real-jti")


class TestSessionEnumerationSafety:
    @pytest.mark.asyncio
    async def test_missing_session_returns_generic_404(self):
        svc, db = _svc()
        res = MagicMock()
        res.scalar_one_or_none = MagicMock(return_value=None)
        db.execute.return_value = res

        with pytest.raises(ServiceOSException) as exc_info:
            await svc.revoke_session(uuid.uuid4(), uuid.uuid4())

        assert exc_info.value.error_code == "SESSION_NOT_FOUND"
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_foreign_session_returns_identical_shape_to_missing(self):
        owner_id = uuid.uuid4()
        other_session = _session(user_id=owner_id)
        svc, db = _svc()
        res = MagicMock()
        res.scalar_one_or_none = MagicMock(return_value=other_session)
        db.execute.return_value = res

        with pytest.raises(ServiceOSException) as exc_info:
            await svc.revoke_session(other_session.id, uuid.uuid4())

        assert exc_info.value.error_code == "SESSION_NOT_FOUND"
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_revocation_is_idempotent(self):
        owner_id = uuid.uuid4()
        session = _session(user_id=owner_id, revoked_at=None)
        svc, db = _svc()
        res = MagicMock()
        res.scalar_one_or_none = MagicMock(return_value=session)
        db.execute.return_value = res

        await svc.revoke_session(session.id, owner_id)
        first_revoked_at = session.revoked_at
        await svc.revoke_session(session.id, owner_id)

        assert session.revoked_at is not None
        assert session.revoked_at >= first_revoked_at
