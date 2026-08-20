"""Tenant AI Assistant — admin configuration API (/v1/admin/assistant/*).

The whole assistant is configured from here: whether it runs at all, its
persona and copy, which tools it may call, how strict the retrieval gate is,
what the opening menu contains, and when it hands over to a human.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import P, permission_checker
from app.dependencies.auth import UserContext, get_current_user
from app.dependencies.db import get_db
from app.engines.tenant_assistant import constants as C
from app.engines.tenant_assistant import retrieval
from app.engines.tenant_assistant import service as svc
from app.engines.tenant_assistant.models import (
    TenantAssistantConfig, TenantAssistantOption,
)
from app.schemas.base import ok

router = APIRouter(prefix="/v1/admin/assistant", tags=["Admin — Tenant AI Assistant"])


def _rid(request: Request) -> str:
    return getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID", "—")


def _require_config(user: UserContext) -> None:
    if not permission_checker.has(user.role, P.ASSISTANT_ADMIN_CONFIGURE, user.permission_overrides):
        raise HTTPException(403, "You cannot configure the assistant.")


def _require_view(user: UserContext) -> None:
    if not permission_checker.has(user.role, P.ASSISTANT_ADMIN_VIEW, user.permission_overrides):
        raise HTTPException(403, "You cannot view the assistant configuration.")


class ConfigIn(BaseModel):
    is_enabled: bool | None = None
    display_name: str | None = Field(default=None, max_length=80)
    tagline: str | None = Field(default=None, max_length=160)
    avatar_emoji: str | None = Field(default=None, max_length=16)
    greeting: str | None = None
    input_placeholder: str | None = Field(default=None, max_length=160)
    disabled_message: str | None = None

    llm_enabled: bool | None = None
    model: str | None = Field(default=None, max_length=60)
    temperature: float | None = Field(default=None, ge=0, le=2)
    max_tokens: int | None = Field(default=None, ge=64, le=4000)
    max_tool_iterations: int | None = Field(default=None, ge=0, le=10)
    system_prompt: str | None = None

    retrieval_top_k: int | None = Field(default=None, ge=1, le=20)
    retrieval_min_score: float | None = Field(default=None, ge=0, le=1)
    require_citation: bool | None = None
    allowed_product_areas: list[str] | None = None
    allowed_tools: list[str] | None = None

    out_of_scope_message: str | None = None
    no_answer_message: str | None = None

    show_categories: bool | None = None
    show_most_asked: bool | None = None
    show_live_state: bool | None = None
    show_recent_requests: bool | None = None
    show_page_context: bool | None = None
    show_announcements: bool | None = None
    max_options_total: int | None = Field(default=None, ge=1, le=60)
    max_options_per_group: int | None = Field(default=None, ge=1, le=20)

    escalation_enabled: bool | None = None
    auto_escalate_after_unresolved: int | None = Field(default=None, ge=1, le=10)
    escalation_category: str | None = Field(default=None, max_length=60)
    escalation_impact: str | None = Field(default=None, max_length=40)
    escalation_include_transcript: bool | None = None
    email_on_escalation: bool | None = None

    rate_limit_per_hour: int | None = Field(default=None, ge=1, le=1000)
    session_idle_minutes: int | None = Field(default=None, ge=5, le=1440)
    allowed_roles: list[str] | None = None


class OptionIn(BaseModel):
    group_key: str = Field(max_length=60)
    label: str = Field(max_length=160)
    description: str | None = Field(default=None, max_length=300)
    icon: str | None = Field(default=None, max_length=60)
    action_type: str
    action_target: str | None = None
    role_keys: list[str] | None = None
    vertical_keys: list[str] | None = None
    page_prefixes: list[str] | None = None
    display_order: int = 100
    is_enabled: bool = True
    is_featured: bool = False


class OptionPatch(BaseModel):
    group_key: str | None = Field(default=None, max_length=60)
    label: str | None = Field(default=None, max_length=160)
    description: str | None = Field(default=None, max_length=300)
    icon: str | None = Field(default=None, max_length=60)
    action_type: str | None = None
    action_target: str | None = None
    role_keys: list[str] | None = None
    vertical_keys: list[str] | None = None
    page_prefixes: list[str] | None = None
    display_order: int | None = None
    is_enabled: bool | None = None
    is_featured: bool | None = None


class PreviewIn(BaseModel):
    question: str = Field(min_length=1, max_length=C.MAX_QUESTION_CHARS)
    tenant_id: uuid.UUID


def _validate_option(action_type: str, target: str | None) -> None:
    if action_type not in C.ACTION_TYPES:
        raise HTTPException(400, f"Unknown action type '{action_type}'. "
                                 f"Use one of: {', '.join(C.ACTION_TYPES)}")
    if action_type == C.ACTION_TOOL and target not in C.TOOL_NAMES:
        raise HTTPException(400, f"'{target}' is not a known tool. "
                                 f"Available: {', '.join(C.TOOL_NAMES)}")
    if action_type == C.ACTION_LINK and target not in C.PORTAL_ROUTES:
        raise HTTPException(400, f"'{target}' is not a known portal route. "
                                 f"Available: {', '.join(C.PORTAL_ROUTES)}")
    if action_type in (C.ACTION_ARTICLE, C.ACTION_TOPIC, C.ACTION_PROMPT) and not target:
        raise HTTPException(400, f"Action type '{action_type}' needs a target.")


# ══════════════════════════════════════════════════════════════════════════════
# Configuration
# ══════════════════════════════════════════════════════════════════════════════
@router.get("/config", summary="Current assistant configuration")
async def get_config(request: Request, db: AsyncSession = Depends(get_db),
                     user: UserContext = Depends(get_current_user)):
    _require_view(user)
    cfg = await svc.get_or_create_global_config(db)
    return ok(cfg.to_dict(), request_id=_rid(request), engine_id=C.ENGINE_ID)


@router.put("/config", summary="Update the assistant configuration")
async def update_config(request: Request, payload: ConfigIn,
                        db: AsyncSession = Depends(get_db),
                        user: UserContext = Depends(get_current_user)):
    _require_config(user)
    cfg = await svc.get_or_create_global_config(db)

    updates = payload.model_dump(exclude_unset=True)
    if "allowed_tools" in updates and updates["allowed_tools"] is not None:
        unknown = [t for t in updates["allowed_tools"] if t not in C.TOOL_NAMES]
        if unknown:
            raise HTTPException(400, f"Unknown tools: {', '.join(unknown)}")
    if "system_prompt" in updates and not (updates["system_prompt"] or "").strip():
        raise HTTPException(400, "The system prompt cannot be empty.")

    for field, value in updates.items():
        setattr(cfg, field, value)
    cfg.updated_by_user_id = uuid.UUID(user.user_id)
    await db.commit()
    await db.refresh(cfg)
    return ok(cfg.to_dict(), request_id=_rid(request), engine_id=C.ENGINE_ID)


@router.get("/capabilities", summary="Tools, routes and areas an admin can choose from")
async def capabilities(request: Request, db: AsyncSession = Depends(get_db),
                       user: UserContext = Depends(get_current_user)):
    _require_view(user)
    return ok({
        "tools": [{"name": t["function"]["name"],
                   "description": t["function"]["description"]} for t in C.TOOL_SPECS],
        "action_types": C.ACTION_TYPES,
        "portal_routes": [{"key": k, "route": v[0], "label": v[1]}
                          for k, v in C.PORTAL_ROUTES.items()],
        "groups": [{"key": k, "label": v} for k, v in C.GROUP_LABELS.items()],
        "knowledge_areas": await retrieval.areas_available(db),
    }, request_id=_rid(request), engine_id=C.ENGINE_ID)


# ══════════════════════════════════════════════════════════════════════════════
# Quick options
# ══════════════════════════════════════════════════════════════════════════════
@router.get("/options", summary="All quick options, including disabled ones")
async def list_options(request: Request, db: AsyncSession = Depends(get_db),
                       user: UserContext = Depends(get_current_user)):
    _require_view(user)
    rows = (await db.execute(
        select(TenantAssistantOption)
        .order_by(TenantAssistantOption.group_key, TenantAssistantOption.display_order)
    )).scalars().all()
    return ok({"options": [o.to_dict() for o in rows], "count": len(rows)},
              request_id=_rid(request), engine_id=C.ENGINE_ID)


@router.post("/options", summary="Add a quick option")
async def create_option(request: Request, payload: OptionIn,
                        db: AsyncSession = Depends(get_db),
                        user: UserContext = Depends(get_current_user)):
    _require_config(user)
    _validate_option(payload.action_type, payload.action_target)
    cfg = await svc.get_or_create_global_config(db)
    o = TenantAssistantOption(config_id=cfg.id, **payload.model_dump())
    db.add(o)
    await db.commit()
    await db.refresh(o)
    return ok(o.to_dict(), request_id=_rid(request), engine_id=C.ENGINE_ID)


@router.put("/options/{option_id}", summary="Edit a quick option")
async def update_option(option_id: uuid.UUID, request: Request, payload: OptionPatch,
                        db: AsyncSession = Depends(get_db),
                        user: UserContext = Depends(get_current_user)):
    _require_config(user)
    o = (await db.execute(select(TenantAssistantOption)
                          .where(TenantAssistantOption.id == option_id))).scalars().first()
    if not o:
        raise HTTPException(404, "Option not found.")
    updates = payload.model_dump(exclude_unset=True)
    if "action_type" in updates or "action_target" in updates:
        _validate_option(updates.get("action_type", o.action_type),
                         updates.get("action_target", o.action_target))
    for field, value in updates.items():
        setattr(o, field, value)
    await db.commit()
    await db.refresh(o)
    return ok(o.to_dict(), request_id=_rid(request), engine_id=C.ENGINE_ID)


@router.delete("/options/{option_id}", summary="Remove a quick option")
async def delete_option(option_id: uuid.UUID, request: Request,
                        db: AsyncSession = Depends(get_db),
                        user: UserContext = Depends(get_current_user)):
    _require_config(user)
    o = (await db.execute(select(TenantAssistantOption)
                          .where(TenantAssistantOption.id == option_id))).scalars().first()
    if not o:
        raise HTTPException(404, "Option not found.")
    await db.delete(o)
    await db.commit()
    return ok({"deleted": True, "id": str(option_id)},
              request_id=_rid(request), engine_id=C.ENGINE_ID)


# ══════════════════════════════════════════════════════════════════════════════
# Observability
# ══════════════════════════════════════════════════════════════════════════════
@router.get("/analytics", summary="Answer rate, escalations and content gaps")
async def analytics(request: Request, days: int = Query(default=30, ge=1, le=365),
                    db: AsyncSession = Depends(get_db),
                    user: UserContext = Depends(get_current_user)):
    _require_view(user)
    return ok(await svc.analytics(db, days=days),
              request_id=_rid(request), engine_id=C.ENGINE_ID)


@router.post("/preview", summary="Ask as if you were a tenant, without leaving a trace")
async def preview(request: Request, payload: PreviewIn,
                  db: AsyncSession = Depends(get_db),
                  user: UserContext = Depends(get_current_user)):
    """Runs the real pipeline against a chosen tenant so an admin can see what
    a business would actually get back. Rolled back, so it never pollutes that
    tenant's conversation history or analytics."""
    _require_config(user)
    cfg = await svc.get_or_create_global_config(db)
    result = await svc.ask(db, cfg, question=payload.question,
                           tenant_id=payload.tenant_id,
                           user_id=uuid.UUID(user.user_id), role="tenant_owner",
                           request_id=_rid(request))
    await db.rollback()
    return ok({**result, "preview": True},
              request_id=_rid(request), engine_id=C.ENGINE_ID)
