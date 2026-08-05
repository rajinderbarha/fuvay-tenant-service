"""PERSONAL-DETAILS-PHONE-SECURITY (2026-08-01) — `PUT /v1/customer/profile`
(and every other role sharing `ProfileService.update_user_profile`)
previously accepted a `phone` field and mutated it with only a
uniqueness check, despite no authenticated contact-change OTP flow
existing anywhere in this codebase (confirmed: only pre-auth LOGIN
phone-OTP endpoints exist in app/engines/auth/router.py). An
authenticated customer's own access token could silently take over a
phone number's association with their account without ever proving they
controlled it.

Fixed: `phone` is now rejected outright (`PHONE_CHANGE_REQUIRES_
VERIFICATION`, 422) BEFORE any other field on the request is applied --
verified below to be atomic (a request combining `full_name` + `phone`
changes neither).
"""
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.engines.profile.service import ProfileService
from app.engines.profile.schemas import UpdateUserProfileRequest
from app.exceptions import ServiceOSException


def _user(**overrides):
    defaults = dict(
        id=uuid.uuid4(), email="rajinder@example.com", phone="+919900024102",
        full_name="Rajinder Singh", display_name="Rajinder", language="en", timezone="Asia/Kolkata",
        role="customer", tenant_id=None, is_active=True, is_verified=True, is_mfa_enabled=False,
        avatar_url=None, profile_photo_media_id=None, last_login_at=None,
        created_at=SimpleNamespace(isoformat=lambda: "2026-01-01T00:00:00Z"),
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def _service(user):
    db = MagicMock()
    db.execute = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    actor = SimpleNamespace(user_id=str(user.id), role="customer", tenant_id=None)
    svc = ProfileService(db=db, actor=actor)
    svc._load_user = AsyncMock(return_value=user)
    return svc, db


class TestPhoneMutationRejected:
    @pytest.mark.asyncio
    async def test_full_name_alone_updates_successfully(self):
        user = _user()
        svc, db = _service(user)

        result = await svc.update_user_profile(UpdateUserProfileRequest(full_name="Rajinder Kaur"))

        assert user.full_name == "Rajinder Kaur"
        assert result["full_name"] == "Rajinder Kaur"

    @pytest.mark.asyncio
    async def test_phone_alone_is_rejected_and_the_phone_remains_unchanged(self):
        user = _user()
        svc, db = _service(user)
        original_phone = user.phone

        with pytest.raises(ServiceOSException) as exc_info:
            await svc.update_user_profile(UpdateUserProfileRequest(phone="+919999999999"))

        assert exc_info.value.error_code == "PHONE_CHANGE_REQUIRES_VERIFICATION"
        assert exc_info.value.status_code == 422
        assert user.phone == original_phone
        db.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_combined_full_name_and_phone_request_is_rejected_atomically(self):
        """Neither field changes -- the request fails as a whole rather
        than partially applying full_name while rejecting phone."""
        user = _user()
        svc, db = _service(user)
        original_name, original_phone = user.full_name, user.phone

        with pytest.raises(ServiceOSException) as exc_info:
            await svc.update_user_profile(UpdateUserProfileRequest(full_name="Someone Else", phone="+919999999999"))

        assert exc_info.value.error_code == "PHONE_CHANGE_REQUIRES_VERIFICATION"
        assert user.full_name == original_name
        assert user.phone == original_phone

    @pytest.mark.asyncio
    async def test_verification_state_is_never_touched_by_a_rejected_or_accepted_update(self):
        user = _user(is_verified=True)
        svc, _ = _service(user)

        with pytest.raises(ServiceOSException):
            await svc.update_user_profile(UpdateUserProfileRequest(phone="+919999999999"))
        assert user.is_verified is True

        user2 = _user(is_verified=True)
        svc2, _ = _service(user2)
        await svc2.update_user_profile(UpdateUserProfileRequest(full_name="New Name"))
        assert user2.is_verified is True

    @pytest.mark.asyncio
    async def test_login_identifying_fields_are_untouched_by_a_name_only_update(self):
        """Role/tenant/active-session-relevant fields are never part of
        `changed` for a full_name-only update -- update_user_profile has
        no code path that could touch them regardless of request shape."""
        user = _user()
        svc, _ = _service(user)
        original_role, original_tenant = user.role, user.tenant_id

        await svc.update_user_profile(UpdateUserProfileRequest(full_name="New Name"))

        assert user.role == original_role
        assert user.tenant_id == original_tenant

    @pytest.mark.asyncio
    async def test_the_pydantic_schema_itself_cannot_be_bypassed_by_a_raw_service_call(self):
        """Even a caller that constructs UpdateUserProfileRequest directly
        (bypassing the FastAPI request-body validation layer entirely)
        still hits the same service-level rejection -- the guard lives in
        ProfileService.update_user_profile, not only in request parsing."""
        user = _user()
        svc, _ = _service(user)
        raw_body = UpdateUserProfileRequest.model_construct(phone="+919999999999")

        with pytest.raises(ServiceOSException) as exc_info:
            await svc.update_user_profile(raw_body)
        assert exc_info.value.error_code == "PHONE_CHANGE_REQUIRES_VERIFICATION"
