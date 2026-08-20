"""Tenant AI Assistant — tenant API (/v1/tenant/assistant/*).

Everything here is scoped by the caller's JWT tenant. No endpoint accepts a
tenant_id, and no endpoint can reach another business's data or the admin
configuration.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import P, permission_checker
from app.dependencies.auth import UserContext, get_current_user
from app.dependencies.db import get_db
from app.engines.tenant_assistant import constants as C
from app.engines.tenant_assistant import retrieval
from app.engines.tenant_assistant import service as svc
from app.schemas.base import ok

router = APIRouter(prefix="/v1/tenant/assistant", tags=["Tenant AI Assistant"])


def _tid(user: UserContext) -> uuid.UUID:
    if not user.tenant_id:
        raise HTTPException(403, "No tenant context")
    return uuid.UUID(user.tenant_id)


def _rid(request: Request) -> str:
    return getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID", "—")


def _require_use(user: UserContext) -> None:
    if not permission_checker.has(user.role, P.ASSISTANT_USE, user.permission_overrides):
        raise HTTPException(403, "You do not have access to the assistant.")


async def _config(db: AsyncSession, user: UserContext):
    cfg = await svc.resolve_config(db, tenant_id=_tid(user))
    if not cfg:
        raise HTTPException(503, "The assistant is not available right now.")
    return cfg


class AskIn(BaseModel):
    question: str = Field(min_length=1, max_length=C.MAX_QUESTION_CHARS)
    path: str | None = Field(default=None, max_length=300)


class OptionRunIn(BaseModel):
    path: str | None = Field(default=None, max_length=300)


class EscalateIn(BaseModel):
    session_id: uuid.UUID | None = None
    subject: str = Field(min_length=3, max_length=300)
    description: str = Field(min_length=10)
    category: str | None = None
    impact: str | None = None


class FeedbackIn(BaseModel):
    is_helpful: bool
    note: str | None = Field(default=None, max_length=1000)


# ══════════════════════════════════════════════════════════════════════════════
@router.get("/panel", summary="Everything the assistant shows when it opens")
async def panel(request: Request, path: str | None = Query(default=None),
                db: AsyncSession = Depends(get_db),
                user: UserContext = Depends(get_current_user)):
    _require_use(user)
    cfg = await _config(db, user)

    if not cfg.is_enabled or not svc._role_allowed(cfg, user.role):
        return ok({"enabled": False,
                   "message": cfg.disabled_message or
                              "The assistant is currently unavailable."},
                  request_id=_rid(request), engine_id=C.ENGINE_ID)

    data = await svc.build_panel(db, cfg, tenant_id=_tid(user),
                                 user_id=uuid.UUID(user.user_id),
                                 role=user.role, path=path)
    data["enabled"] = True
    await db.commit()
    return ok(data, request_id=_rid(request), engine_id=C.ENGINE_ID,
              tenant_id=user.tenant_id)


@router.post("/ask", summary="Ask a free-text question")
async def ask(request: Request, payload: AskIn,
              db: AsyncSession = Depends(get_db),
              user: UserContext = Depends(get_current_user)):
    _require_use(user)
    cfg = await _config(db, user)
    if not cfg.is_enabled:
        raise HTTPException(503, cfg.disabled_message or "The assistant is unavailable.")

    result = await svc.ask(db, cfg, question=payload.question, tenant_id=_tid(user),
                           user_id=uuid.UUID(user.user_id), role=user.role,
                           path=payload.path, request_id=_rid(request))
    await db.commit()
    return ok(result, request_id=_rid(request), engine_id=C.ENGINE_ID,
              tenant_id=user.tenant_id)


@router.post("/options/{option_id}/run", summary="Run a quick option (no LLM call)")
async def run_option(option_id: uuid.UUID, request: Request, payload: OptionRunIn,
                     db: AsyncSession = Depends(get_db),
                     user: UserContext = Depends(get_current_user)):
    _require_use(user)
    cfg = await _config(db, user)
    result = await svc.run_option(db, cfg, option_id, tenant_id=_tid(user),
                                  user_id=uuid.UUID(user.user_id), role=user.role,
                                  path=payload.path)
    await db.commit()
    return ok(result, request_id=_rid(request), engine_id=C.ENGINE_ID,
              tenant_id=user.tenant_id)


@router.get("/articles/{slug}", summary="Read one help article")
async def article(slug: str, request: Request,
                  db: AsyncSession = Depends(get_db),
                  user: UserContext = Depends(get_current_user)):
    _require_use(user)
    p = await retrieval.by_slug(db, slug)
    if not p:
        raise HTTPException(404, "That article is not available.")
    await retrieval.record_view(db, p.article_id)
    await db.commit()
    return ok({"slug": p.slug, "title": p.title, "summary": p.summary,
               "body": p.body, "product_area": p.product_area},
              request_id=_rid(request), engine_id=C.ENGINE_ID)


@router.get("/history", summary="This user's most recent assistant conversation")
async def history(request: Request, db: AsyncSession = Depends(get_db),
                  user: UserContext = Depends(get_current_user)):
    _require_use(user)
    data = await svc.history(db, tenant_id=_tid(user), user_id=uuid.UUID(user.user_id))
    return ok(data, request_id=_rid(request), engine_id=C.ENGINE_ID,
              tenant_id=user.tenant_id)


@router.post("/escalate", summary="Hand over to the ServiceOS support team")
async def escalate(request: Request, payload: EscalateIn,
                   db: AsyncSession = Depends(get_db),
                   user: UserContext = Depends(get_current_user)):
    _require_use(user)
    if not permission_checker.has(user.role, P.SUPPORT_REQUESTS_CREATE, user.permission_overrides):
        raise HTTPException(403, "You do not have permission to raise support requests.")
    cfg = await _config(db, user)
    result = await svc.escalate(
        db, cfg, session_id=payload.session_id, tenant_id=_tid(user),
        user_id=uuid.UUID(user.user_id), user_name=user.full_name,
        user_role=user.role, subject=payload.subject, description=payload.description,
        category=payload.category, impact=payload.impact,
    )
    await db.commit()
    return ok(result, request_id=_rid(request), engine_id=C.ENGINE_ID,
              tenant_id=user.tenant_id)


@router.post("/messages/{message_id}/feedback", summary="Was this answer helpful?")
async def feedback(message_id: uuid.UUID, request: Request, payload: FeedbackIn,
                   db: AsyncSession = Depends(get_db),
                   user: UserContext = Depends(get_current_user)):
    _require_use(user)
    data = await svc.rate(db, message_id=message_id, tenant_id=_tid(user),
                          user_id=uuid.UUID(user.user_id),
                          is_helpful=payload.is_helpful, note=payload.note)
    await db.commit()
    return ok(data, request_id=_rid(request), engine_id=C.ENGINE_ID,
              tenant_id=user.tenant_id)
