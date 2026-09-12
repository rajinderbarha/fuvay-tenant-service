"""Regression tests for the public booking and OTP abuse controls."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
import uuid
from datetime import date

import pytest
from starlette.requests import Request

from app.exceptions import ServiceOSException


def _request(peer: str, headers: list[tuple[bytes, bytes]]) -> Request:
    return Request({
        "type": "http",
        "method": "POST",
        "path": "/",
        "headers": headers,
        "client": (peer, 43210),
        "server": ("test", 443),
        "scheme": "https",
        "query_string": b"",
    })


def test_direct_client_cannot_spoof_forwarded_ip():
    from app.core import security

    request = _request("198.51.100.20", [(b"x-forwarded-for", b"1.2.3.4")])
    with patch.object(
        security, "get_settings", return_value=SimpleNamespace(TRUSTED_PROXY_CIDRS=["172.16.0.0/12"])
    ):
        assert security.get_client_ip(request) == "198.51.100.20"


def test_trusted_proxy_can_forward_valid_ip_but_not_garbage():
    from app.core import security

    settings = SimpleNamespace(TRUSTED_PROXY_CIDRS=["172.16.0.0/12"])
    with patch.object(security, "get_settings", return_value=settings):
        forwarded = _request("172.18.0.4", [(b"x-real-ip", b"203.0.113.7")])
        invalid = _request("172.18.0.4", [(b"x-real-ip", b"not-an-ip")])
        assert security.get_client_ip(forwarded) == "203.0.113.7"
        assert security.get_client_ip(invalid) == "172.18.0.4"


@pytest.mark.asyncio
async def test_sensitive_rate_limit_fails_closed_when_redis_is_down():
    from app.core.security import RateLimiter

    limiter = RateLimiter()
    limiter._get_redis = AsyncMock(side_effect=RuntimeError("redis down"))
    with pytest.raises(ServiceOSException) as exc:
        await limiter.check("otp", "auth:otp_send", "opaque", fail_closed=True)
    assert exc.value.error_code == "SECURITY_CONTROL_UNAVAILABLE"
    assert exc.value.status_code == 503

    allowed, headers = await limiter.check("ordinary", "api:read", "opaque")
    assert allowed is True
    assert headers == {}


@pytest.mark.asyncio
async def test_auth_service_enforces_limits_before_twilio_delivery():
    from app.engines.auth.service import AuthService

    db = MagicMock()
    guard = AsyncMock()
    with patch("app.engines.auth.service.enforce_otp_send_limits", guard), \
         patch("app.twilio_client.is_verify_configured", return_value=True), \
         patch("app.twilio_client.verify_send", AsyncMock(return_value=True)) as send:
        service = AuthService(db, ip_address="203.0.113.8")
        await service.send_phone_otp(
            "+919876543210", "messaging_link", source_id="instagram:sender-1"
        )

    guard.assert_awaited_once_with(
        "+919876543210",
        ip_address="203.0.113.8",
        source_id="instagram:sender-1",
    )
    send.assert_awaited_once_with("+919876543210")


@pytest.mark.asyncio
async def test_phone_otp_fallback_exposes_code_only_in_explicit_nonproduction_mode():
    from app.engines.auth.service import AuthService

    db = MagicMock()
    db.add = MagicMock()
    guard = AsyncMock()
    with patch("app.engines.auth.service.enforce_otp_send_limits", guard), \
         patch("app.twilio_client.is_verify_configured", return_value=False):
        service = AuthService(db)
        service.settings = SimpleNamespace(
            DEBUG=False, APP_ENV="staging", MESSAGING_DEV_OTP_ENABLED=True,
        )
        staging = await service.send_phone_otp(
            "+919876543210", "messaging_link", source_id="instagram:sender-1",
        )

        service.settings = SimpleNamespace(
            DEBUG=False, APP_ENV="production", MESSAGING_DEV_OTP_ENABLED=True,
        )
        production = await service.send_phone_otp(
            "+919876543211", "messaging_link", source_id="instagram:sender-2",
        )

    assert staging["otp_hint"].isdigit() and len(staging["otp_hint"]) == 6
    assert "otp_hint" not in production


@pytest.mark.asyncio
async def test_instagram_identity_link_returns_the_staging_code_to_the_chat():
    from app.engines.messaging_gateway.service import MessagingGatewayService

    class Result:
        def scalar(self):
            return 0

        def scalars(self):
            return self

        def first(self):
            return None

    db = MagicMock()
    db.execute = AsyncMock(return_value=Result())
    db.flush = AsyncMock()
    thread = SimpleNamespace(
        id=uuid.uuid4(), channel="instagram", channel_user_id="sender-1",
        pending_customer_id=None, pending_phone_ciphertext=None,
    )

    with patch(
        "app.engines.auth.service.AuthService.send_phone_otp",
        AsyncMock(return_value={"message": "OTP sent.", "otp_hint": "123456"}),
    ):
        message = await MessagingGatewayService(db)._start_identity_link(
            thread, "+919876543210",
        )

    assert "Development code: 123456." in message
    assert thread.pending_phone_ciphertext


@pytest.mark.asyncio
async def test_unknown_password_reset_cannot_consume_paid_sms_budget():
    from app.engines.auth.service import AuthService

    service = AuthService(MagicMock(), ip_address="203.0.113.8")
    service._get_user_by_phone = AsyncMock(return_value=None)
    attempt_guard = AsyncMock()
    delivery_budget = AsyncMock()
    with patch("app.engines.auth.service.enforce_otp_send_limits", attempt_guard), \
         patch("app.engines.auth.service.enforce_otp_delivery_budget", delivery_budget):
        result = await service.request_password_reset(
            email=None, phone="+919876543210"
        )

    assert "If an account exists" in result["message"]
    attempt_guard.assert_awaited_once()
    delivery_budget.assert_not_awaited()


@pytest.mark.asyncio
async def test_real_phone_password_reset_consumes_budget_before_delivery():
    from app.engines.auth.service import AuthService

    user = SimpleNamespace(id=uuid.uuid4(), tenant_id=None)
    service = AuthService(MagicMock(), ip_address="203.0.113.8")
    service._get_user_by_phone = AsyncMock(return_value=user)
    service._audit = AsyncMock()
    attempt_guard = AsyncMock()
    delivery_budget = AsyncMock()
    send = AsyncMock(return_value=True)
    with patch("app.engines.auth.service.enforce_otp_send_limits", attempt_guard), \
         patch("app.engines.auth.service.enforce_otp_delivery_budget", delivery_budget), \
         patch("app.twilio_client.is_verify_configured", return_value=True), \
         patch("app.twilio_client.verify_send", send):
        await service.request_password_reset(email=None, phone="+919876543210")

    delivery_budget.assert_awaited_once_with(ip_address="203.0.113.8")
    send.assert_awaited_once_with("+919876543210")


@pytest.mark.asyncio
async def test_social_otp_without_ip_is_scoped_by_sender_not_shared_unknown_ip():
    from app.core import security

    check = AsyncMock(return_value={})
    with patch.object(security.rate_limiter, "check_and_raise", check), \
         patch.object(
             security, "get_settings", return_value=SimpleNamespace(APP_ENV="production")
         ):
        await security.enforce_otp_send_limits(
            "+919876543210",
            ip_address=None,
            source_id="instagram:sender-1",
            costed_delivery=False,
        )

    limit_types = [call.kwargs["limit_type"] for call in check.await_args_list]
    assert "auth:otp_send_ip" not in limit_types
    assert "auth:otp_daily_ip" not in limit_types
    assert "auth:otp_send_source" in limit_types
    assert "auth:otp_daily_source" in limit_types


@pytest.mark.asyncio
async def test_turnstile_requires_token_when_enabled():
    from app.core import abuse_protection

    settings = SimpleNamespace(
        TURNSTILE_REQUIRED=True,
        TURNSTILE_SECRET_KEY="secret",
        TURNSTILE_ALLOWED_HOSTNAMES=["signup.example.com"],
    )
    with patch.object(abuse_protection, "get_settings", return_value=settings):
        with pytest.raises(ServiceOSException) as exc:
            await abuse_protection.verify_turnstile(
                None, remote_ip="203.0.113.9", expected_action="provider_signup"
            )
    assert exc.value.error_code == "BOT_CHALLENGE_REQUIRED"


@pytest.mark.asyncio
async def test_turnstile_checks_action_and_hostname():
    from app.core import abuse_protection

    settings = SimpleNamespace(
        TURNSTILE_REQUIRED=True,
        TURNSTILE_SECRET_KEY="secret",
        TURNSTILE_ALLOWED_HOSTNAMES=["signup.example.com"],
    )
    response = MagicMock()
    response.raise_for_status.return_value = None
    response.json.return_value = {
        "success": True,
        "action": "provider_signup",
        "hostname": "signup.example.com",
    }
    client = AsyncMock()
    client.post = AsyncMock(return_value=response)
    context = AsyncMock()
    context.__aenter__.return_value = client
    context.__aexit__.return_value = None

    with patch.object(abuse_protection, "get_settings", return_value=settings), \
         patch.object(abuse_protection.httpx, "AsyncClient", return_value=context):
        await abuse_protection.verify_turnstile(
            "valid-token", remote_ip="203.0.113.9", expected_action="provider_signup"
        )
        response.json.return_value["hostname"] = "attacker.example"
        with pytest.raises(ServiceOSException) as exc:
            await abuse_protection.verify_turnstile(
                "other-token", remote_ip="203.0.113.9", expected_action="provider_signup"
            )
    assert exc.value.error_code == "BOT_CHALLENGE_FAILED"


def test_production_config_requires_bot_protection_settings():
    from app.config import Settings

    with pytest.raises(ValueError) as exc:
        Settings(
            APP_ENV="production",
            SECRET_KEY="x" * 64,
            JWT_SECRET_KEY="y" * 64,
            DATABASE_URL="postgresql+asyncpg://u:p@db/prod",
            ALLOWED_ORIGINS=["https://example.com"],
            TRUSTED_PROXY_CIDRS=["172.16.0.0/12"],
            TURNSTILE_REQUIRED=False,
        )
    assert "TURNSTILE_REQUIRED" in str(exc.value)


def test_production_bot_protection_configuration_can_start():
    from app.config import Settings

    settings = Settings(
        APP_ENV="production",
        SECRET_KEY="x" * 64,
        JWT_SECRET_KEY="y" * 64,
        DATABASE_URL="postgresql+asyncpg://app:secret@db/prod",
        ALLOWED_ORIGINS=["https://example.com"],
        TRUSTED_PROXY_CIDRS=["172.16.0.0/12"],
        TURNSTILE_REQUIRED=True,
        TURNSTILE_SECRET_KEY="turnstile-secret",
        TURNSTILE_ALLOWED_HOSTNAMES=["example.com"],
    )
    assert settings.TURNSTILE_REQUIRED is True


def test_invalid_trusted_proxy_cidr_fails_configuration():
    from app.config import Settings

    with pytest.raises(ValueError, match="Invalid trusted proxy CIDR"):
        Settings(TRUSTED_PROXY_CIDRS=["not-a-network"])


def test_production_rejects_debug_otp_behavior():
    from app.config import Settings

    with pytest.raises(ValueError, match="DEBUG must be false"):
        Settings(
            APP_ENV="production",
            DEBUG=True,
            SECRET_KEY="x" * 64,
            JWT_SECRET_KEY="y" * 64,
            DATABASE_URL="postgresql+asyncpg://app:secret@db/prod",
            ALLOWED_ORIGINS=["https://example.com"],
            TRUSTED_PROXY_CIDRS=["172.16.0.0/12"],
            TURNSTILE_REQUIRED=True,
            TURNSTILE_SECRET_KEY="turnstile-secret",
            TURNSTILE_ALLOWED_HOSTNAMES=["example.com"],
        )


def _scalars_first(value):
    result = MagicMock()
    result.scalars.return_value.first.return_value = value
    return result


@pytest.mark.asyncio
async def test_fourth_active_booking_draft_is_rejected():
    from app.engines.home_service_booking.service import HomeServiceChatbotBookingService

    category = MagicMock(id=uuid.uuid4(), name="AC", slug="ac")
    offering = MagicMock(id=uuid.uuid4(), service_name="AC Repair", slug="repair")
    count_result = MagicMock()
    count_result.scalar_one.return_value = 3
    db = MagicMock()
    db.execute = AsyncMock(side_effect=[
        _scalars_first(category),
        _scalars_first(offering),
        _scalars_first(uuid.uuid4()),
        _scalars_first(uuid.uuid4()),
        count_result,
    ])

    with patch(
        "app.dependencies.vertical_guard._load_vertical",
        AsyncMock(return_value=SimpleNamespace(is_enabled=True)),
    ), patch(
        "app.engines.home_service_booking.service.enforce_booking_action_limits",
        AsyncMock(),
    ):
        with pytest.raises(ServiceOSException) as exc:
            await HomeServiceChatbotBookingService(db).start_booking_draft(
                customer_id=uuid.uuid4(),
                ai_session_id=None,
                category_slug="ac",
                offering_slug="repair",
            )
    assert exc.value.error_code == "ACTIVE_BOOKING_DRAFT_LIMIT"
    assert exc.value.status_code == 429


@pytest.mark.asyncio
async def test_different_draft_cannot_duplicate_active_booking():
    from app.engines.final_records.creation_service import HomeServiceFinalCreationService
    from app.engines.final_records.models import ServiceBooking
    from app.engines.home_service_booking.models import HomeServiceBookingDraft

    customer_id = uuid.uuid4()
    draft = MagicMock(spec=HomeServiceBookingDraft)
    draft.id = uuid.uuid4()
    draft.customer_id = customer_id
    draft.ai_session_id = uuid.uuid4()
    draft.status = "ready_for_confirmation"
    draft.offering_id = uuid.uuid4()
    draft.selected_problem_id = uuid.uuid4()
    draft.booking_summary = None
    draft.zipcode = "140001"
    draft.preferred_date = date(2026, 9, 4)
    draft.preferred_time_window = "10:00-11:00"
    existing = MagicMock(spec=ServiceBooking)
    existing.id = uuid.uuid4()
    existing.booking_number = "BK-EXISTING"

    db = MagicMock()
    db.execute = AsyncMock(side_effect=[_scalars_first(draft), _scalars_first(existing)])
    service = HomeServiceFinalCreationService(db)
    service.lock.check_and_raise_if_duplicate = AsyncMock(return_value=None)

    with patch(
        "app.engines.final_records.creation_service.enforce_booking_action_limits",
        AsyncMock(),
    ):
        with pytest.raises(ServiceOSException) as exc:
            await service.finalize(draft.id, customer_id=customer_id)
    assert exc.value.error_code == "DUPLICATE_ACTIVE_BOOKING"
    assert exc.value.context["booking_number"] == "BK-EXISTING"
    duplicate_query = db.execute.await_args_list[1].args[0]
    assert draft.selected_problem_id.hex in str(duplicate_query.compile(
        compile_kwargs={"literal_binds": True},
    ))


@pytest.mark.asyncio
async def test_issue_selection_warns_only_for_same_active_problem():
    from app.engines.home_service_booking.service import HomeServiceChatbotBookingService

    customer_id = uuid.uuid4()
    offering_id = uuid.uuid4()
    existing = SimpleNamespace(
        id=uuid.uuid4(),
        booking_number="BK-ACTIVE",
        status="confirmed",
    )
    db = MagicMock()
    db.execute = AsyncMock(return_value=_scalars_first(existing))
    service = HomeServiceChatbotBookingService(db)
    service.start_booking_draft = AsyncMock()

    issue_id = uuid.uuid4()
    issue = {
        "id": str(issue_id),
        "label": "AC not cooling",
        "selection_mode": "compatible",
        "compatibility_group": "ac-repair",
        "master_service_id": str(offering_id),
        "master_service_slug": "ac-repair",
    }
    with patch(
        "app.engines.home_service_booking.offering_catalog_service.list_serviceable_issues",
        AsyncMock(return_value={"issues": [issue]}),
    ):
        with pytest.raises(ServiceOSException) as exc:
            await service.select_issue(
                customer_id=customer_id,
                ai_session_id=None,
                category_slug="ac",
                zipcode="140001",
                issue_id=issue["id"],
            )

    assert exc.value.error_code == "DUPLICATE_ACTIVE_BOOKING"
    assert exc.value.status_code == 409
    assert exc.value.context["booking_number"] == "BK-ACTIVE"
    assert exc.value.context["confirmation_required"] is True
    duplicate_query = db.execute.await_args.args[0]
    assert issue_id.hex in str(duplicate_query.compile(
        compile_kwargs={"literal_binds": True},
    ))
    service.start_booking_draft.assert_not_awaited()


@pytest.mark.asyncio
async def test_issue_selection_allows_confirmed_same_problem_rebooking():
    from app.engines.home_service_booking.service import HomeServiceChatbotBookingService
    from app.engines.home_service_booking.question_flow_service import QuestionFlowService

    customer_id = uuid.uuid4()
    offering_id = uuid.uuid4()
    issue_id = uuid.uuid4()
    draft_id = uuid.uuid4()
    existing = SimpleNamespace(id=uuid.uuid4(), booking_number="BK-ACTIVE")
    draft = SimpleNamespace(booking_summary=None, updated_at=None)
    db = MagicMock(commit=AsyncMock())
    db.execute = AsyncMock(return_value=_scalars_first(existing))
    service = HomeServiceChatbotBookingService(db)
    service.start_booking_draft = AsyncMock(return_value={"id": str(draft_id)})
    service.update_draft_fields = AsyncMock(return_value={"updated": True})
    service._require_draft = AsyncMock(return_value=draft)
    issue = {
        "id": str(issue_id), "label": "AC not cooling",
        "selection_mode": "compatible", "compatibility_group": "ac-repair",
        "master_service_id": str(offering_id),
        "master_service_slug": "ac-repair",
    }

    with patch(
        "app.engines.home_service_booking.offering_catalog_service.list_serviceable_issues",
        AsyncMock(return_value={"issues": [issue]}),
    ), patch.object(
        QuestionFlowService, "get_current_question", AsyncMock(return_value={}),
    ):
        result = await service.select_issue(
            customer_id=customer_id, ai_session_id=None,
            category_slug="ac", zipcode="140001", issue_id=str(issue_id),
            allow_duplicate=True,
        )

    assert result["draft_id"] == str(draft_id)
    assert draft.booking_summary["duplicate_booking_override"] is True
    assert draft.booking_summary["duplicate_problem_id"] == str(issue_id)


@pytest.mark.asyncio
async def test_social_confirmation_uses_sender_quota_not_customer_app_quota():
    from app.engines.final_records.creation_service import HomeServiceFinalCreationService
    from app.engines.home_service_booking.models import HomeServiceBookingDraft

    draft = MagicMock(spec=HomeServiceBookingDraft)
    draft.id = uuid.uuid4()
    draft.customer_id = uuid.uuid4()
    draft.ai_session_id = uuid.uuid4()
    draft.status = "ready_for_confirmation"

    db = MagicMock()
    db.execute = AsyncMock(return_value=_scalars_first(draft))
    service = HomeServiceFinalCreationService(db)
    service.lock.check_and_raise_if_duplicate = AsyncMock(return_value=None)
    social_limit = AsyncMock(side_effect=ServiceOSException(
        "RATE_LIMITED", "Rate limit exceeded.", status_code=429,
    ))
    app_limit = AsyncMock()

    with patch(
        "app.engines.final_records.creation_service.enforce_social_confirmation_limit",
        social_limit,
    ), patch(
        "app.engines.final_records.creation_service.enforce_booking_action_limits",
        app_limit,
    ):
        with pytest.raises(ServiceOSException) as exc:
            await service.finalize(
                draft.id,
                customer_id=draft.customer_id,
                source_channel="instagram",
                source_actor_id="page-scoped-sender-1",
            )

    assert exc.value.error_code == "RATE_LIMITED"
    social_limit.assert_awaited_once_with(
        "instagram:page-scoped-sender-1",
    )
    app_limit.assert_not_awaited()
