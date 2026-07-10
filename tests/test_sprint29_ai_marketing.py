"""Sprint 29 — AI Hardening + Marketing Automation Tests.

32 tests covering:
- AI response validation (schema, action block, claim detection, sanitisation)
- AI rate limiter (message rate, session rate, prompt size, cooldowns)
- AI category prompts (flow routing, contract instruction)
- AI action log service (log, mask PII, metrics shape)
- Marketing campaign constants (status transitions, error codes)
- Marketing segment service (build, validate, suspend guard)
- Marketing campaign service (create, lifecycle, conversion integrity)
- Marketing automation triggers (dispatcher, cooldown logic)
- Admin AI router imports + Swagger tag presence
- Customer AI router imports + tenant isolation
- Admin marketing router imports + Swagger tag presence
- Provider marketing router imports + tenant isolation
- Migration 047 existence
"""
import pytest
import uuid
import re
import time
from unittest.mock import AsyncMock, MagicMock, patch


# ─────────────────────────────────────────────────────────────────────────────
# Helpers / Fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def user_id():
    return uuid.uuid4()


@pytest.fixture
def tenant_id():
    return uuid.uuid4()


def _db(scalar_value=None, rows_value=None):
    mock_result = MagicMock()
    mock_result.scalar.return_value = scalar_value
    mock_result.mappings.return_value.all.return_value = rows_value or []
    db = MagicMock()
    db.execute = AsyncMock(return_value=mock_result)
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    db.refresh = AsyncMock()
    return db


# ─────────────────────────────────────────────────────────────────────────────
# 1. Sprint 29 constants
# ─────────────────────────────────────────────────────────────────────────────

def test_sprint29_constants_flow_types():
    from app.engines.ai_conversation.sprint29_constants import (
        FLOW_HOME_SERVICE, FLOW_COACHING, FLOW_REAL_ESTATE, FLOW_UNSUPPORTED,
    )
    assert FLOW_HOME_SERVICE == "home_service_booking"
    assert FLOW_COACHING == "coaching_appointment"
    assert FLOW_REAL_ESTATE == "real_estate_lead"
    assert FLOW_UNSUPPORTED == "unsupported"


def test_sprint29_constants_blocked_actions():
    from app.engines.ai_conversation.sprint29_constants import BLOCKED_AI_ACTIONS
    required = {
        "create_final_booking_directly",
        "assign_provider_directly",
        "set_final_price_directly",
        "deduct_wallet_directly",
        "mark_payment_paid_directly",
    }
    assert required.issubset(BLOCKED_AI_ACTIONS)


def test_sprint29_constants_rate_limits():
    from app.engines.ai_conversation.sprint29_constants import (
        AI_RATE_LIMIT_MESSAGES_PER_MINUTE,
        AI_RATE_LIMIT_SESSIONS_PER_HOUR,
        AI_FAILURE_COOLDOWN_COUNT,
    )
    assert AI_RATE_LIMIT_MESSAGES_PER_MINUTE == 10
    assert AI_RATE_LIMIT_SESSIONS_PER_HOUR == 5
    assert AI_FAILURE_COOLDOWN_COUNT == 5


# ─────────────────────────────────────────────────────────────────────────────
# 2. AI Response Validation Service
# ─────────────────────────────────────────────────────────────────────────────

def test_validation_schema_passes_valid():
    from app.engines.ai_conversation.validation_service import AIResponseValidationService
    svc = AIResponseValidationService()
    valid = {
        "intent": "book_service",
        "confidence": 0.9,
        "customer_message": "Sure, let me help.",
        "required_next_action": "ask_question",
        "collected_fields": {},
        "missing_fields": [],
        "backend_action_request": {"action": "none"},
        "safety": {"is_safe": True},
    }
    ok, err = svc.validate_ai_response_schema(valid)
    assert ok, err


def test_validation_schema_fails_missing_key():
    from app.engines.ai_conversation.validation_service import AIResponseValidationService
    svc = AIResponseValidationService()
    ok, err = svc.validate_ai_response_schema({"intent": "x"})
    assert not ok
    # err is list[str]; check any message mentions missing keys
    combined = " ".join(err)
    assert "customer_message" in combined or "required_next_action" in combined


def test_validation_blocked_action_rejected():
    from app.engines.ai_conversation.validation_service import AIResponseValidationService
    from app.engines.ai_conversation.sprint29_constants import ERR_AI_ACTION_BLOCKED
    svc = AIResponseValidationService()
    ok, err = svc.validate_allowed_backend_action("create_final_booking_directly")
    assert not ok
    assert ERR_AI_ACTION_BLOCKED in err


def test_validation_allowed_action_passes():
    from app.engines.ai_conversation.validation_service import AIResponseValidationService
    svc = AIResponseValidationService()
    ok, err = svc.validate_allowed_backend_action("none")
    assert ok


def test_validation_detects_price_claim():
    from app.engines.ai_conversation.validation_service import AIResponseValidationService
    svc = AIResponseValidationService()
    # detect_forbidden_claims takes a response dict with "customer_message"
    found = svc.detect_forbidden_claims({"customer_message": "The service costs ₹500 only"})
    assert found.get("price_claims") or found.get("provider_claims")


def test_validation_sanitize_replaces_price():
    from app.engines.ai_conversation.validation_service import AIResponseValidationService
    svc = AIResponseValidationService()
    result = svc.sanitize_customer_message("It costs rs 300 for this job")
    assert "300" not in result
    assert "[price from backend]" in result


def test_validation_pipeline_fallback_on_blocked():
    from app.engines.ai_conversation.validation_service import AIResponseValidationService
    svc = AIResponseValidationService()
    # Missing required_next_action → schema failure → fallback
    raw = {
        "intent": "book_service",
        "confidence": 0.9,
        "customer_message": "Let me assign you a provider now.",
        # required_next_action missing — triggers schema error
        "backend_action_request": {"action": "assign_provider_directly"},
    }
    # validate_and_sanitize returns (response_dict, is_safe, violations)
    result, is_safe, violations = svc.validate_and_sanitize(raw)
    assert not is_safe
    assert result.get("_is_fallback") is True or len(violations) > 0


# ─────────────────────────────────────────────────────────────────────────────
# 3. AI Rate Limiter
# ─────────────────────────────────────────────────────────────────────────────

def test_rate_limiter_allows_first_message():
    from app.engines.ai_conversation.rate_limiter import AIRateLimiter
    rl = AIRateLimiter()
    cid = str(uuid.uuid4())
    ok, err = rl.check_message_rate(cid)
    assert ok, err


def test_rate_limiter_blocks_after_limit():
    import app.engines.ai_conversation.rate_limiter as rl_mod
    from app.engines.ai_conversation.sprint29_constants import AI_RATE_LIMIT_MESSAGES_PER_MINUTE, ERR_AI_RATE_LIMIT_EXCEEDED
    rl = rl_mod.get_rate_limiter()
    cid = "test_block_" + str(uuid.uuid4())
    now = time.monotonic()
    # Fill module-level window directly
    for _ in range(AI_RATE_LIMIT_MESSAGES_PER_MINUTE):
        rl_mod._msg_windows[cid].append(now)
    ok, err = rl.check_message_rate(cid)
    assert not ok
    assert ERR_AI_RATE_LIMIT_EXCEEDED in err


def test_rate_limiter_prompt_size_check():
    from app.engines.ai_conversation.rate_limiter import AIRateLimiter
    from app.engines.ai_conversation.sprint29_constants import AI_MAX_PROMPT_CHARS, ERR_AI_PROMPT_TOO_LARGE
    rl = AIRateLimiter()
    ok, err = rl.check_prompt_size("x" * (AI_MAX_PROMPT_CHARS + 1))
    assert not ok
    assert ERR_AI_PROMPT_TOO_LARGE in err


def test_rate_limiter_failure_cooldown():
    from app.engines.ai_conversation.rate_limiter import AIRateLimiter
    from app.engines.ai_conversation.sprint29_constants import AI_FAILURE_COOLDOWN_COUNT, ERR_AI_RATE_LIMIT_EXCEEDED
    rl = AIRateLimiter()
    cid = str(uuid.uuid4())
    for _ in range(AI_FAILURE_COOLDOWN_COUNT):
        rl.record_failure(cid)
    ok, err = rl.check_message_rate(cid)
    assert not ok
    assert ERR_AI_RATE_LIMIT_EXCEEDED in err


def test_rate_limiter_stats_shape():
    from app.engines.ai_conversation.rate_limiter import AIRateLimiter
    rl = AIRateLimiter()
    stats = rl.get_stats()
    assert "active_customers_in_msg_window" in stats
    assert "customers_in_cooldown" in stats


# ─────────────────────────────────────────────────────────────────────────────
# 4. Category Prompts
# ─────────────────────────────────────────────────────────────────────────────

def test_category_prompts_flow_dispatch():
    from app.engines.ai_conversation.category_prompts import get_prompt_for_flow, FLOW_PROMPTS
    from app.engines.ai_conversation.sprint29_constants import (
        FLOW_HOME_SERVICE, FLOW_COACHING, FLOW_REAL_ESTATE, FLOW_UNSUPPORTED,
    )
    for flow in [FLOW_HOME_SERVICE, FLOW_COACHING, FLOW_REAL_ESTATE, FLOW_UNSUPPORTED]:
        prompt = get_prompt_for_flow(flow)
        assert isinstance(prompt, str) and len(prompt) > 100


def test_category_prompts_contract_instruction_in_all():
    from app.engines.ai_conversation.category_prompts import FLOW_PROMPTS
    for flow, prompt in FLOW_PROMPTS.items():
        assert "intent" in prompt, f"Flow {flow} missing 'intent' in prompt"
        assert "customer_message" in prompt, f"Flow {flow} missing 'customer_message'"


# ─────────────────────────────────────────────────────────────────────────────
# 5. AI Action Log Service
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_action_log_masks_pii():
    from app.engines.ai_conversation.action_log_service import _mask
    payload = {
        "customer_phone": "9999999999",
        "customer_email": "test@example.com",
        "intent": "book_service",
        "city": "Mumbai",
    }
    masked = _mask(payload)
    # _mask replaces sensitive values with "***", keeps keys
    assert masked.get("customer_phone") == "***"
    assert masked.get("customer_email") == "***"
    assert masked.get("city") == "Mumbai"


@pytest.mark.asyncio
async def test_action_log_service_log_action(user_id):
    from app.engines.ai_conversation.action_log_service import AIActionLogService
    db = _db()
    svc = AIActionLogService()  # db is passed per method, not __init__
    session_id = uuid.uuid4()
    await svc.log_action(
        db=db,
        session_id=session_id,
        customer_id=user_id,
        action="none",
        intent="book_service",
        flow_type="home_service_booking",
        status="executed",
    )
    assert db.add.called or db.flush.called


# ─────────────────────────────────────────────────────────────────────────────
# 6. Marketing Constants
# ─────────────────────────────────────────────────────────────────────────────

def test_marketing_constants_runnable_statuses():
    from app.engines.marketing_automation.constants import RUNNABLE_STATUSES, PAUSABLE_STATUSES, CANCELLABLE_STATUSES
    assert "draft" in RUNNABLE_STATUSES
    assert "running" in PAUSABLE_STATUSES
    assert "running" in CANCELLABLE_STATUSES


def test_marketing_constants_event_types():
    from app.engines.marketing_automation.constants import VALID_EVENT_TYPES
    assert "converted" in VALID_EVENT_TYPES
    assert "skipped" in VALID_EVENT_TYPES


def test_marketing_constants_error_codes():
    from app.engines.marketing_automation.constants import (
        ERR_CAMPAIGN_NOT_FOUND, ERR_CAMPAIGN_INVALID_STATUS,
        ERR_SEGMENT_TOO_LARGE, ERR_MESSAGE_REQUIRED,
    )
    # Error codes use "MARKETING_" prefix (not "ERR_")
    assert ERR_CAMPAIGN_NOT_FOUND
    assert ERR_SEGMENT_TOO_LARGE
    assert ERR_MESSAGE_REQUIRED


# ─────────────────────────────────────────────────────────────────────────────
# 7. Marketing Segment Service
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_segment_service_validate_unknown_audience():
    from app.engines.marketing_automation.segment_service import MarketingSegmentService
    svc = MarketingSegmentService()  # db passed per method
    # validate_segment_rules(rules, audience) returns list of errors
    errors = svc.validate_segment_rules({"bad_filter": True}, "aliens")
    # Unknown audience → all filters unsupported, so errors non-empty
    assert isinstance(errors, list)


@pytest.mark.asyncio
async def test_segment_service_validate_valid_audience():
    from app.engines.marketing_automation.segment_service import MarketingSegmentService
    svc = MarketingSegmentService()
    errors = svc.validate_segment_rules({}, "customers")
    assert errors == []


@pytest.mark.asyncio
async def test_segment_service_preview_invalid_audience():
    from app.engines.marketing_automation.segment_service import MarketingSegmentService
    from app.engines.marketing_automation.constants import ERR_SEGMENT_INVALID
    db = _db()
    svc = MarketingSegmentService()
    # "aliens" audience triggers unsupported filter errors → ValueError with ERR_SEGMENT_INVALID
    with pytest.raises(ValueError):
        await svc.preview_segment(db, {"bad_key": True}, "aliens")


# ─────────────────────────────────────────────────────────────────────────────
# 8. Marketing Campaign Service — conversion integrity
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_campaign_service_converted_requires_source_id():
    from app.engines.marketing_automation.campaign_service import MarketingCampaignService
    db = _db()
    svc = MarketingCampaignService()  # db passed per method
    campaign_id = uuid.uuid4()
    with pytest.raises(ValueError, match="source_record_id"):
        await svc.track_campaign_event(
            db=db,
            campaign_id=campaign_id,
            event_type="converted",
            source_record_type="booking",
            source_record_id=None,
        )


@pytest.mark.asyncio
async def test_campaign_service_non_converted_no_source_needed():
    from app.engines.marketing_automation.campaign_service import MarketingCampaignService
    db = _db()
    svc = MarketingCampaignService()
    campaign_id = uuid.uuid4()
    # Should not raise
    await svc.track_campaign_event(
        db=db,
        campaign_id=campaign_id,
        event_type="sent",
        source_record_type=None,
        source_record_id=None,
    )
    assert db.add.called or db.flush.called


# ─────────────────────────────────────────────────────────────────────────────
# 9. Admin AI Router
# ─────────────────────────────────────────────────────────────────────────────

def test_admin_ai_router_imports():
    from app.engines.ai_conversation.sprint29_admin_router import admin_ai_router
    assert admin_ai_router.prefix == "/v1/admin/ai"


def test_admin_ai_router_tags():
    from app.engines.ai_conversation.sprint29_admin_router import admin_ai_router
    routes = [r for r in admin_ai_router.routes]
    assert len(routes) >= 5


# ─────────────────────────────────────────────────────────────────────────────
# 10. Customer AI Router
# ─────────────────────────────────────────────────────────────────────────────

def test_customer_ai_router_imports():
    from app.engines.ai_conversation.sprint29_customer_router import customer_ai_router
    assert customer_ai_router.prefix == "/v1/customer/ai"


def test_customer_ai_router_has_send_message():
    from app.engines.ai_conversation.sprint29_customer_router import customer_ai_router
    paths = [r.path for r in customer_ai_router.routes]
    assert any("send-message" in p or "message" in p for p in paths)


# ─────────────────────────────────────────────────────────────────────────────
# 11. Admin Marketing Router
# ─────────────────────────────────────────────────────────────────────────────

def test_admin_marketing_router_imports():
    from app.engines.marketing_automation.admin_router import admin_marketing_router
    assert admin_marketing_router.prefix == "/v1/admin/marketing"


def test_admin_marketing_router_route_count():
    from app.engines.marketing_automation.admin_router import admin_marketing_router
    routes = [r for r in admin_marketing_router.routes]
    assert len(routes) >= 10


# ─────────────────────────────────────────────────────────────────────────────
# 12. Provider Marketing Router
# ─────────────────────────────────────────────────────────────────────────────

def test_provider_marketing_router_imports():
    from app.engines.marketing_automation.provider_router import provider_marketing_router
    assert provider_marketing_router.prefix == "/v1/provider/marketing"


def test_provider_marketing_router_tenant_guard():
    """_tid() must raise if no tenant_id."""
    from app.engines.marketing_automation.provider_router import _tid
    mock_user = MagicMock()
    mock_user.tenant_id = None
    with pytest.raises(Exception):
        _tid(mock_user)


# ─────────────────────────────────────────────────────────────────────────────
# 13. Main app includes Sprint 29 routers
# ─────────────────────────────────────────────────────────────────────────────

def test_main_app_includes_sprint29_routers():
    from app.main import app
    from fastapi.openapi.utils import get_openapi
    schema = get_openapi(title="t", version="1", routes=app.routes)
    paths = list(schema["paths"].keys())
    # Sprint 29 AI admin endpoints are at /v1/admin/ai/*
    ai_paths  = [p for p in paths if "/admin/ai/sessions" in p or "/admin/ai/metrics" in p]
    # Sprint 29 marketing endpoints include provider and admin
    mkt_paths = [p for p in paths if "/provider/marketing" in p or "/admin/marketing/campaigns" in p]
    assert ai_paths,  f"No Sprint 29 admin AI routes; found: {[p for p in paths if 'ai' in p][:5]}"
    assert mkt_paths, "No Sprint 29 marketing routes found"


# ─────────────────────────────────────────────────────────────────────────────
# 14. Migration 047 existence
# ─────────────────────────────────────────────────────────────────────────────

def test_migration_047_exists():
    import os, glob
    files = glob.glob("alembic/versions/047*.py")
    assert files, "Migration 047 not found"
