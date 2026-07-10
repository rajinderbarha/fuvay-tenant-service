"""Sprint 29 — Customer AI Session Router (extends Sprint 15).

New endpoints:
  POST /v1/customer/ai/sessions                           — create session (with rate limit)
  GET  /v1/customer/ai/sessions/{session_id}              — get own session only
  POST /v1/customer/ai/sessions/{session_id}/messages     — send message (rate limited)
  POST /v1/customer/ai/sessions/{session_id}/reset        — reset collected fields
  POST /v1/customer/ai/sessions/{session_id}/handoff      — request human handoff
  GET  /v1/customer/ai/sessions/{session_id}/draft-status — draft status from backend
"""
from __future__ import annotations
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import get_current_user, UserContext
from app.dependencies.db import get_db
from app.engines.ai_conversation.models import AIConversationSession, AIConversationMessage
from app.engines.ai_conversation.rate_limiter import get_rate_limiter
from app.engines.ai_conversation.sprint29_constants import (
    ERR_AI_RATE_LIMIT_EXCEEDED,
    ERR_AI_SESSION_ACCESS_DENIED,
    AI_SAFE_FALLBACK_MESSAGE,
)
from app.schemas.base import ok

customer_ai_router = APIRouter(
    prefix="/v1/customer/ai",
    tags=["Customer AI Sessions"],
)


def _rid(r: Request) -> str:
    return getattr(r.state, "request_id", "—")


def _assert_owns(session: AIConversationSession, u: UserContext) -> None:
    """Raises if the session does not belong to this customer."""
    if session.customer_id and str(session.customer_id) != str(u.user_id):
        raise ValueError(ERR_AI_SESSION_ACCESS_DENIED)


@customer_ai_router.post("/sessions", summary="Create new AI conversation session")
async def create_ai_session(
    body: dict,
    r: Request,
    u: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    limiter = get_rate_limiter()
    ok_flag, err = limiter.check_session_rate(u.user_id)
    if not ok_flag:
        raise ValueError(ERR_AI_RATE_LIMIT_EXCEEDED)

    from app.engines.ai_conversation.service import AIConversationService
    svc  = AIConversationService(db=db, request_id=_rid(r))
    data = await svc.create_session(
        customer_id  = uuid.UUID(u.user_id),
        category_id  = uuid.UUID(body["category_id"]) if body.get("category_id") else None,
        context_data = body.get("context_data"),
    )
    return ok(data, _rid(r), "customer.ai.sessions.create")


@customer_ai_router.get("/sessions/{session_id}", summary="Get own AI session")
async def get_ai_session(
    session_id: str,
    r: Request,
    u: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(AIConversationSession).where(AIConversationSession.id == uuid.UUID(session_id))
    )
    session = result.scalars().first()
    if not session:
        raise ValueError("AI_SESSION_NOT_FOUND")
    _assert_owns(session, u)
    return ok(session.to_dict(), _rid(r), "customer.ai.sessions.get")


@customer_ai_router.post("/sessions/{session_id}/messages", summary="Send message in AI session")
async def send_ai_message(
    session_id: str,
    body: dict,
    r: Request,
    u: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    limiter = get_rate_limiter()
    ok_flag, err = limiter.check_message_rate(u.user_id)
    if not ok_flag:
        return ok({
            "customer_message": AI_SAFE_FALLBACK_MESSAGE,
            "rate_limited": True,
            "error_code": ERR_AI_RATE_LIMIT_EXCEEDED,
        }, _rid(r), "customer.ai.sessions.messages.rate_limited")

    # Verify session ownership
    result = await db.execute(
        select(AIConversationSession).where(AIConversationSession.id == uuid.UUID(session_id))
    )
    session = result.scalars().first()
    if not session:
        raise ValueError("AI_SESSION_NOT_FOUND")
    _assert_owns(session, u)

    message = body.get("message", "")
    ok_size, size_err = limiter.check_prompt_size(message)
    if not ok_size:
        raise ValueError(size_err)

    from app.engines.ai_conversation.service import AIConversationService
    svc  = AIConversationService(db=db, request_id=_rid(r))
    try:
        data = await svc.send_message(
            session_id  = uuid.UUID(session_id),
            customer_id = uuid.UUID(u.user_id),
            message     = message,
        )
        limiter.record_success(u.user_id)
    except Exception as e:
        limiter.record_failure(u.user_id)
        return ok({
            "customer_message": AI_SAFE_FALLBACK_MESSAGE,
            "error": str(e),
            "_is_fallback": True,
        }, _rid(r), "customer.ai.sessions.messages.fallback")

    return ok(data, _rid(r), "customer.ai.sessions.messages.send")


@customer_ai_router.post("/sessions/{session_id}/reset", summary="Reset AI session collected fields")
async def reset_ai_session(
    session_id: str,
    r: Request,
    u: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(AIConversationSession).where(AIConversationSession.id == uuid.UUID(session_id))
    )
    session = result.scalars().first()
    if not session:
        raise ValueError("AI_SESSION_NOT_FOUND")
    _assert_owns(session, u)
    session.collected_fields = {}
    session.current_intent   = "unknown"
    await db.commit()
    return ok(session.to_dict(), _rid(r), "customer.ai.sessions.reset")


@customer_ai_router.post("/sessions/{session_id}/handoff", summary="Request handoff to human agent")
async def request_handoff(
    session_id: str,
    r: Request,
    u: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(AIConversationSession).where(AIConversationSession.id == uuid.UUID(session_id))
    )
    session = result.scalars().first()
    if not session:
        raise ValueError("AI_SESSION_NOT_FOUND")
    _assert_owns(session, u)
    session.workflow_status = "handed_off"
    session.is_active = False
    await db.commit()
    return ok({
        "session_id": str(session.id),
        "status": "handed_off",
        "message": "A human agent will be with you shortly.",
    }, _rid(r), "customer.ai.sessions.handoff")


@customer_ai_router.get("/sessions/{session_id}/draft-status", summary="Get backend draft status for session")
async def get_draft_status(
    session_id: str,
    r: Request,
    u: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(AIConversationSession).where(AIConversationSession.id == uuid.UUID(session_id))
    )
    session = result.scalars().first()
    if not session:
        raise ValueError("AI_SESSION_NOT_FOUND")
    _assert_owns(session, u)

    collected = session.collected_fields or {}
    context   = session.context_data or {}
    draft_id  = context.get("draft_id") or context.get("current_draft_id")

    return ok({
        "session_id":       str(session.id),
        "workflow_status":  session.workflow_status,
        "current_intent":   session.current_intent,
        "collected_fields": collected,
        "draft_id":         draft_id,
        "is_confirm_ready": session.workflow_status == "confirm_ready",
    }, _rid(r), "customer.ai.sessions.draft_status")
