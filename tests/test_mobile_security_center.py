"""Technician mobile app Phase V: GET /v1/auth/me/mobile-security-summary,
composed entirely over the EXISTING real security-overview/security-activity/
session-list projections (never a second security-status calculation), plus
two real gaps this phase's audit confirmed and fixed:
  - disable_mfa never checked User.mfa_required, so a policy-required MFA
    could be disabled anyway given the correct password+code.
  - change_password never revoked other sessions, so a stolen refresh token
    survived a password change indefinitely.
"""
from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import text

from app.main import app
from app.dependencies.auth import get_current_user, UserContext
from app.dependencies.db import get_db
from app.config import get_settings
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool

_real_engine = create_async_engine(get_settings().DATABASE_URL, poolclass=NullPool)
_real_sessionmaker = async_sessionmaker(_real_engine, expire_on_commit=False)


async def _override_get_db():
    async with _real_sessionmaker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@pytest.fixture(autouse=True)
def _use_real_db():
    app.dependency_overrides[get_db] = _override_get_db
    yield
    app.dependency_overrides.pop(get_db, None)


def _ctx(user_id, device_id=None, session_id=None):
    return UserContext(user_id=str(user_id), email="tech@serviceos.local", role="technician",
                        tenant_id=None, full_name="Demo Technician", is_verified=True,
                        device_id=device_id, session_id=session_id)


@pytest.mark.asyncio
async def test_mobile_security_summary_live_shape_and_masking():
    from app.database import get_session_factory, init_db
    from app.engines.auth.models import User, UserSession

    await init_db()
    factory = get_session_factory()
    async with factory() as db:
        user_id = uuid.uuid4()
        user = User(
            id=user_id, email="priya.sharma@serviceos.local", phone="9876543210",
            full_name="Priya Sharma", role="technician", tenant_id=None,
            hashed_password="x", is_active=True, is_verified=True, is_mfa_enabled=False,
        )
        db.add(user)
        await db.flush()

        current_session_id = uuid.uuid4()
        other_session_id = uuid.uuid4()
        db.add(UserSession(id=current_session_id, user_id=user_id, device_id="device-current",
                            device_name="Pixel 8", device_type="android", is_trusted=True, last_active_at=None))
        db.add(UserSession(id=other_session_id, user_id=user_id, device_id="device-other",
                            device_name="Old Phone", device_type="android", is_trusted=False, last_active_at=None))
        await db.commit()
        await db.execute(text("UPDATE user_sessions SET last_active_at = now() WHERE user_id=:uid"), {"uid": user_id})
        await db.commit()

        try:
            app.dependency_overrides[get_current_user] = lambda: _ctx(user_id, device_id="device-current", session_id=str(current_session_id))
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.get("/v1/auth/me/mobile-security-summary", headers={"Authorization": "Bearer x"})
                assert resp.status_code == 200
                data = resp.json()["data"]

                assert data["verified_contacts"]["masked_mobile"] == "••••• 43210"
                assert data["verified_contacts"]["masked_email"].startswith("p")
                assert "@" in data["verified_contacts"]["masked_email"]
                assert "priya.sharma" not in data["verified_contacts"]["masked_email"]  # never the full local-part

                assert data["mfa"]["enabled"] is False
                assert data["current_device"]["trusted"] is True
                assert data["current_device"]["session_id"] == str(current_session_id)
                assert data["active_session_count"] == 2
                # Real security-status vocabulary from get_security_overview,
                # not a fabricated "Protected because the page loaded".
                assert data["security_status"]["level"] in ("protected", "protection_recommended", "action_required", "unavailable")
                assert isinstance(data["security_status"]["reasons"], list)
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            await db.execute(text("DELETE FROM user_sessions WHERE user_id=:uid"), {"uid": user_id})
            await db.execute(text("DELETE FROM users WHERE id=:uid"), {"uid": user_id})
            await db.commit()


@pytest.mark.asyncio
async def test_disable_mfa_rejects_when_policy_required():
    from app.database import get_session_factory, init_db
    from app.engines.auth.models import User, MFASecret
    from app.engines.auth.utils import hash_password
    import pyotp

    await init_db()
    factory = get_session_factory()
    async with factory() as db:
        user_id = uuid.uuid4()
        password = "Correcthorse123!"
        user = User(
            id=user_id, email=f"pol-{user_id.hex[:8]}@serviceos.local", phone="9876500000",
            full_name="Policy Tech", role="technician", tenant_id=None,
            hashed_password=hash_password(password), is_active=True, is_verified=True,
            is_mfa_enabled=True, mfa_required=True,
        )
        db.add(user)
        secret = pyotp.random_base32()
        db.add(MFASecret(user_id=user_id, encrypted_secret=secret, is_confirmed=True, confirmed_at=None))
        await db.commit()

        try:
            app.dependency_overrides[get_current_user] = lambda: _ctx(user_id, device_id="device-x")
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                code = pyotp.TOTP(secret).now()
                resp = await client.post(
                    "/v1/auth/mfa/disable", headers={"Authorization": "Bearer x"},
                    json={"password": password, "code": code},
                )
                assert resp.status_code == 422
                assert resp.json()["error_code"] == "MFA_POLICY_REQUIRED"

            # MFA is still enabled -- the forged disable request had zero effect.
            still_enabled = (await db.execute(text("SELECT is_mfa_enabled FROM users WHERE id=:uid"), {"uid": user_id})).scalar()
            assert still_enabled is True
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            await db.execute(text("DELETE FROM mfa_secrets WHERE user_id=:uid"), {"uid": user_id})
            await db.execute(text("DELETE FROM users WHERE id=:uid"), {"uid": user_id})
            await db.commit()


@pytest.mark.asyncio
async def test_password_change_revokes_other_sessions_but_preserves_current():
    from app.database import get_session_factory, init_db
    from app.engines.auth.models import User, UserSession
    from app.engines.auth.utils import hash_password

    await init_db()
    factory = get_session_factory()
    async with factory() as db:
        user_id = uuid.uuid4()
        old_password = "OldCorrect123!"
        user = User(
            id=user_id, email=f"pwd-{user_id.hex[:8]}@serviceos.local", phone="9876500001",
            full_name="Password Tech", role="technician", tenant_id=None,
            hashed_password=hash_password(old_password), is_active=True, is_verified=True, is_mfa_enabled=False,
        )
        db.add(user)
        await db.flush()
        current_session_id = uuid.uuid4()
        other_session_id = uuid.uuid4()
        db.add(UserSession(id=current_session_id, user_id=user_id, device_id="d1", device_name="This phone", device_type="android", is_trusted=False, last_active_at=None))
        db.add(UserSession(id=other_session_id, user_id=user_id, device_id="d2", device_name="Other phone", device_type="android", is_trusted=False, last_active_at=None))
        await db.commit()
        await db.execute(text("UPDATE user_sessions SET last_active_at = now() WHERE user_id=:uid"), {"uid": user_id})
        await db.commit()

        try:
            app.dependency_overrides[get_current_user] = lambda: _ctx(user_id, device_id="d1", session_id=str(current_session_id))
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.put(
                    "/v1/auth/password/change", headers={"Authorization": "Bearer x"},
                    json={"current_password": old_password, "new_password": "NewCorrect456!", "confirm_password": "NewCorrect456!"},
                )
                assert resp.status_code == 200
                assert resp.json()["data"]["other_sessions_revoked"] == 1

            current_revoked = (await db.execute(text("SELECT revoked_at FROM user_sessions WHERE id=:id"), {"id": current_session_id})).scalar()
            other_revoked = (await db.execute(text("SELECT revoked_at FROM user_sessions WHERE id=:id"), {"id": other_session_id})).scalar()
            assert current_revoked is None  # current session preserved
            assert other_revoked is not None  # other session revoked
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            await db.execute(text("DELETE FROM user_sessions WHERE user_id=:uid"), {"uid": user_id})
            await db.execute(text("DELETE FROM users WHERE id=:uid"), {"uid": user_id})
            await db.commit()


def test_new_rate_limit_types_registered():
    from app.core.security import RATE_LIMITS
    assert "auth:password_change" in RATE_LIMITS
    assert "auth:mfa_confirm" in RATE_LIMITS
    assert "auth:mfa_disable" in RATE_LIMITS
