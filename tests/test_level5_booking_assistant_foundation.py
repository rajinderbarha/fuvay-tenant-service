"""BOOKING-ASSISTANT FOUNDATION (2026-08-01) — backend additions:

1. CustomerHomeService._get_bookable_categories now forwards `slug`
   (was silently forwarding a nonexistent `code` key, always None).
2. HomeServiceChatbotBookingService.get_draft_by_ai_session — resolves a
   non-terminal draft linked to an AI session, enforcing ownership.
3. app.engines.ai_conversation.regional_language — pure ZIP-prefix to
   backend-authoritative regional-language resolution (no ZIP-to-language
   mapping lives in the mobile client).
"""
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.engines.ai_conversation.regional_language import (
    build_language_options, resolve_regional_language,
)
from app.engines.home_service_booking.service import HomeServiceChatbotBookingService
from app.engines.home_service_booking.models import HomeServiceBookingDraft


# ── regional_language (pure) ────────────────────────────────────────────────

def test_resolve_regional_language_for_configured_punjab_pin():
    assert resolve_regional_language("141002") == {"code": "pa", "label": "ਪੰਜਾਬੀ"}


def test_resolve_regional_language_returns_none_for_unconfigured_pin():
    assert resolve_regional_language("560001") is None


def test_resolve_regional_language_returns_none_for_missing_zipcode():
    assert resolve_regional_language(None) is None
    assert resolve_regional_language("") is None


def test_build_language_options_always_includes_english_and_hindi():
    options = build_language_options(None)
    codes = [o["code"] for o in options]
    assert codes == ["en", "hi"]


def test_build_language_options_includes_regional_only_when_configured():
    options = build_language_options("141002")
    assert options[-1] == {"code": "pa", "label": "ਪੰਜਾਬੀ"}

    options_unconfigured = build_language_options("560001")
    assert all(o["code"] != "pa" for o in options_unconfigured)


def test_build_language_options_never_suggests_an_unsupported_code():
    # Every code returned must already be a real ALLOWED_LANGUAGES member --
    # this is enforced structurally by resolve_regional_language's own
    # membership check, verified here as a regression guard.
    from app.engines.profile.schemas import ALLOWED_LANGUAGES
    for option in build_language_options("141002"):
        assert option["code"] in ALLOWED_LANGUAGES


# ── get_draft_by_ai_session ──────────────────────────────────────────────────

def make_draft(**overrides):
    d = MagicMock(spec=HomeServiceBookingDraft)
    d.id = overrides.get("id", uuid.uuid4())
    d.ai_session_id = overrides.get("ai_session_id")
    d.customer_id = overrides.get("customer_id")
    d.status = overrides.get("status", "draft")
    return d


@pytest.mark.asyncio
async def test_get_draft_by_ai_session_returns_none_when_no_draft_exists():
    db = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalars.return_value.first.return_value = None
    db.execute.return_value = result_mock

    svc = HomeServiceChatbotBookingService(db=db, request_id="test")
    result = await svc.get_booking_draft_by_ai_session(ai_session_id=uuid.uuid4(), customer_id=uuid.uuid4())

    assert result is None


@pytest.mark.asyncio
async def test_get_draft_by_ai_session_returns_the_enriched_draft_when_found():
    session_id = uuid.uuid4()
    customer_id = uuid.uuid4()
    draft = make_draft(ai_session_id=session_id, customer_id=customer_id)

    db = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalars.return_value.first.return_value = draft
    db.execute.return_value = result_mock

    svc = HomeServiceChatbotBookingService(db=db, request_id="test")
    svc._enrich_draft = AsyncMock(return_value={"id": str(draft.id), "status": "draft"})

    result = await svc.get_booking_draft_by_ai_session(ai_session_id=session_id, customer_id=customer_id)

    assert result == {"id": str(draft.id), "status": "draft"}
    svc._enrich_draft.assert_awaited_once_with(draft)
