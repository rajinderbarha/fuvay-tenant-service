"""Sprint 29 — Admin AI Monitoring Router (extends Sprint 15).

New endpoints:
  GET /v1/admin/ai/sessions              — list sessions (with flow_type/status filters)
  GET /v1/admin/ai/sessions/{session_id} — session detail
  GET /v1/admin/ai/action-logs           — all ai_action_logs
  GET /v1/admin/ai/failed-actions        — blocked + failed ai_action_logs
  GET /v1/admin/ai/metrics               — aggregate AI metrics
  POST /v1/admin/ai/sessions/{session_id}/handoff — mark session as handed off
  POST /v1/admin/ai/sessions/{session_id}/close   — close session
"""
from __future__ import annotations
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import select, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import get_current_user, UserContext, require_super_admin
from app.dependencies.db import get_db
from app.engines.ai_conversation.action_log_service import AIActionLogService
from app.engines.ai_conversation.models import AIConversationSession, AIConversationMessage
from app.schemas.base import ok

_action_svc = AIActionLogService()


def _rid(r: Request) -> str:
    return getattr(r.state, "request_id", "—")


admin_ai_router = APIRouter(
    prefix="/v1/admin/ai",
    tags=["Admin AI Monitoring"],
    dependencies=[Depends(require_super_admin)],
)


@admin_ai_router.get("/sessions", summary="List all AI sessions with filters")
async def admin_list_ai_sessions(
    r: Request,
    flow_type:         Optional[str] = Query(None),
    status:            Optional[str] = Query(None),
    customer_id:       Optional[str] = Query(None),
    intent:            Optional[str] = Query(None),
    limit:             int           = Query(20, ge=1, le=100),
    offset:            int           = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    filters = []
    if status:
        filters.append(AIConversationSession.workflow_status == status)
    if intent:
        filters.append(AIConversationSession.current_intent == intent)
    if customer_id:
        filters.append(AIConversationSession.customer_id == uuid.UUID(customer_id))

    stmt = (select(AIConversationSession)
            .order_by(desc(AIConversationSession.created_at))
            .limit(limit).offset(offset))
    if filters:
        stmt = stmt.where(and_(*filters))

    result = await db.execute(stmt)
    sessions = [s.to_dict() for s in result.scalars().all()]
    return ok(sessions, _rid(r), "admin.ai.sessions.list")


@admin_ai_router.get("/sessions/{session_id}", summary="Get AI session detail")
async def admin_get_ai_session(
    session_id: str,
    r: Request,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(AIConversationSession).where(AIConversationSession.id == uuid.UUID(session_id))
    )
    session = result.scalars().first()
    if not session:
        raise ValueError("AI_SESSION_NOT_FOUND")

    msgs_result = await db.execute(
        select(AIConversationMessage)
        .where(AIConversationMessage.session_id == uuid.UUID(session_id))
        .order_by(AIConversationMessage.created_at)
        .limit(100)
    )
    data = session.to_dict()
    data["messages"] = [m.to_dict() for m in msgs_result.scalars().all()]
    return ok(data, _rid(r), "admin.ai.sessions.get")


@admin_ai_router.get("/action-logs", summary="List AI action logs")
async def admin_list_action_logs(
    r: Request,
    session_id: Optional[str] = Query(None),
    status:     Optional[str] = Query(None),
    limit:      int           = Query(50, ge=1, le=200),
    offset:     int           = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    sid = uuid.UUID(session_id) if session_id else None
    data = await _action_svc.list_action_logs(db, limit=limit, offset=offset,
                                               session_id=sid, status=status)
    return ok(data, _rid(r), "admin.ai.action_logs.list")


@admin_ai_router.get("/failed-actions", summary="List blocked and failed AI actions")
async def admin_failed_actions(
    r: Request,
    session_id:  Optional[str] = Query(None),
    customer_id: Optional[str] = Query(None),
    limit:       int           = Query(50, ge=1, le=200),
    offset:      int           = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    sid = uuid.UUID(session_id)  if session_id  else None
    cid = uuid.UUID(customer_id) if customer_id else None
    data = await _action_svc.list_failed_actions(db, limit=limit, offset=offset,
                                                   session_id=sid, customer_id=cid)
    return ok(data, _rid(r), "admin.ai.failed_actions.list")


@admin_ai_router.get("/metrics", summary="Aggregate AI action metrics")
async def admin_ai_metrics(r: Request, db: AsyncSession = Depends(get_db)):
    data = await _action_svc.get_metrics(db)
    from app.engines.ai_conversation.rate_limiter import get_rate_limiter
    data["rate_limiter"] = get_rate_limiter().get_stats()
    return ok(data, _rid(r), "admin.ai.metrics")


@admin_ai_router.post("/sessions/{session_id}/handoff", summary="Mark session as handed off to human")
async def admin_handoff_session(
    session_id: str,
    r: Request,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(AIConversationSession).where(AIConversationSession.id == uuid.UUID(session_id))
    )
    session = result.scalars().first()
    if not session:
        raise ValueError("AI_SESSION_NOT_FOUND")
    session.workflow_status = "handed_off"
    session.is_active = False
    await db.commit()
    return ok(session.to_dict(), _rid(r), "admin.ai.sessions.handoff")


@admin_ai_router.post("/sessions/{session_id}/close", summary="Close AI session")
async def admin_close_session(
    session_id: str,
    r: Request,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(AIConversationSession).where(AIConversationSession.id == uuid.UUID(session_id))
    )
    session = result.scalars().first()
    if not session:
        raise ValueError("AI_SESSION_NOT_FOUND")
    session.workflow_status = "completed"
    session.is_active = False
    from datetime import datetime, timezone
    session.completed_at = datetime.now(timezone.utc)
    await db.commit()
    return ok(session.to_dict(), _rid(r), "admin.ai.sessions.close")
