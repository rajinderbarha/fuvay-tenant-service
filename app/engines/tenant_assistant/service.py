"""Tenant AI Assistant — answering pipeline, options panel and escalation.

The answering contract, in order:

    1. scope guard      — deterministic pattern check, no LLM call
    2. retrieve         — help centre passages scored 0..1
    3. tools            — tenant-scoped live data, if the config allows
    4. gate             — nothing retrieved AND no tool data  ->  refuse
    5. render           — LLM turns context into prose, or a deterministic
                          fallback answer if llm_enabled is off
    6. validate         — citation required, forbidden fields stripped
    7. record           — message row with resolution, used by auto-escalation

Every branch persists a message, so the admin console can see exactly what the
assistant did and how often it failed to answer.
"""
from __future__ import annotations

import time
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import structlog
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.support import constants as SC
from app.engines.support import service as support_svc
from app.engines.tenant_assistant import constants as C
from app.engines.tenant_assistant import retrieval
from app.engines.tenant_assistant.models import (
    TenantAssistantConfig, TenantAssistantFeedback, TenantAssistantMessage,
    TenantAssistantOption, TenantAssistantSession,
)
from app.engines.tenant_assistant.tools import TenantAssistantTools
from app.exceptions import ServiceOSException

logger = structlog.get_logger("tenant_assistant")

utcnow = lambda: datetime.now(timezone.utc)


class AssistantError(ServiceOSException):
    def __init__(self, code: str, message: str, status_code: int = 400):
        super().__init__(code, message, status_code=status_code)


# ══════════════════════════════════════════════════════════════════════════════
# Configuration
# ══════════════════════════════════════════════════════════════════════════════
async def resolve_config(db: AsyncSession, *, tenant_id: uuid.UUID | None = None,
                         vertical_key: str | None = None) -> TenantAssistantConfig | None:
    """Most specific configuration wins: tenant > vertical > global."""
    rows = (await db.execute(select(TenantAssistantConfig))).scalars().all()
    by_scope = {"tenant": None, "vertical": None, "global": None}
    for row in rows:
        if row.scope == "tenant" and tenant_id and row.scope_id == tenant_id:
            by_scope["tenant"] = row
        elif row.scope == "vertical" and vertical_key and str(row.scope_id) == str(vertical_key):
            by_scope["vertical"] = row
        elif row.scope == "global":
            by_scope["global"] = row
    return by_scope["tenant"] or by_scope["vertical"] or by_scope["global"]


async def get_or_create_global_config(db: AsyncSession) -> TenantAssistantConfig:
    cfg = await resolve_config(db)
    if cfg:
        return cfg
    raise AssistantError("ASSISTANT_NOT_CONFIGURED",
                         "The assistant has not been configured yet.", 503)


def _role_allowed(cfg: TenantAssistantConfig, role: str | None) -> bool:
    allowed = cfg.allowed_roles
    if not allowed:
        return True
    return role in allowed


# ══════════════════════════════════════════════════════════════════════════════
# Sessions
# ══════════════════════════════════════════════════════════════════════════════
async def _active_session(db: AsyncSession, cfg: TenantAssistantConfig, *,
                          tenant_id: uuid.UUID, user_id: uuid.UUID,
                          user_role: str | None, path: str | None) -> TenantAssistantSession:
    cutoff = utcnow() - timedelta(minutes=cfg.session_idle_minutes)
    s = (await db.execute(
        select(TenantAssistantSession)
        .where(TenantAssistantSession.user_id == user_id,
               TenantAssistantSession.tenant_id == tenant_id,
               TenantAssistantSession.status == C.SESSION_ACTIVE,
               TenantAssistantSession.last_activity_at >= cutoff)
        .order_by(TenantAssistantSession.last_activity_at.desc())
    )).scalars().first()
    if s:
        return s
    s = TenantAssistantSession(tenant_id=tenant_id, user_id=user_id,
                               user_role=user_role, opened_from_path=path)
    db.add(s)
    await db.flush()
    return s


async def _record(db: AsyncSession, session: TenantAssistantSession, *, role: str,
                  content: str, resolution: str | None = None,
                  citations: list[dict] | None = None, tools_used: list[str] | None = None,
                  score: float | None = None, used_llm: bool = False,
                  latency_ms: int | None = None) -> TenantAssistantMessage:
    m = TenantAssistantMessage(
        session_id=session.id, tenant_id=session.tenant_id, role=role,
        content=content, resolution=resolution, citations=citations,
        tools_used=tools_used, used_llm=used_llm, latency_ms=latency_ms,
        retrieval_score=Decimal(str(round(score, 4))) if score is not None else None,
    )
    db.add(m)
    await db.flush()
    return m


async def _rate_limited(db: AsyncSession, cfg: TenantAssistantConfig,
                        session: TenantAssistantSession) -> bool:
    since = utcnow() - timedelta(hours=1)
    n = (await db.execute(
        select(func.count()).select_from(TenantAssistantMessage)
        .where(TenantAssistantMessage.tenant_id == session.tenant_id,
               TenantAssistantMessage.role == C.ROLE_USER,
               TenantAssistantMessage.created_at >= since)
    )).scalar() or 0
    return int(n) >= cfg.rate_limit_per_hour


# ══════════════════════════════════════════════════════════════════════════════
# Options panel — everything the tenant sees the moment the panel opens
# ══════════════════════════════════════════════════════════════════════════════
async def build_panel(db: AsyncSession, cfg: TenantAssistantConfig, *,
                      tenant_id: uuid.UUID, user_id: uuid.UUID,
                      role: str | None, path: str | None) -> dict:
    """One call returns the full opening surface. No LLM involved."""
    opts = (await db.execute(
        select(TenantAssistantOption)
        .where(TenantAssistantOption.is_enabled.is_(True))
        .order_by(TenantAssistantOption.group_key, TenantAssistantOption.display_order)
    )).scalars().all()

    # Role + page filtering happens here so the model never sees options the
    # caller may not use.
    def visible(o: TenantAssistantOption) -> bool:
        if o.role_keys and role not in o.role_keys:
            return False
        if o.page_prefixes and path:
            return any(path.startswith(p) for p in o.page_prefixes)
        return True

    groups: dict[str, list[dict]] = {}
    featured: list[dict] = []
    total = 0
    for o in opts:
        if not visible(o) or total >= cfg.max_options_total:
            continue
        bucket = groups.setdefault(o.group_key, [])
        if len(bucket) >= cfg.max_options_per_group:
            continue
        payload = o.to_dict()
        bucket.append(payload)
        total += 1
        if o.is_featured and len(featured) < 6:
            featured.append(payload)

    ordered_groups = [
        {"key": g, "label": C.GROUP_LABELS.get(g, g.replace("_", " ").title()),
         "options": groups[g]}
        for g in C.GROUP_ORDER if g in groups
    ] + [
        {"key": g, "label": g.replace("_", " ").title(), "options": v}
        for g, v in groups.items() if g not in C.GROUP_ORDER
    ]

    panel: dict = {
        "assistant": {
            "display_name": cfg.display_name, "tagline": cfg.tagline,
            "avatar_emoji": cfg.avatar_emoji, "greeting": cfg.greeting,
            "input_placeholder": cfg.input_placeholder,
            "can_escalate": cfg.escalation_enabled,
            "free_text_enabled": cfg.llm_enabled,
        },
        "groups": ordered_groups if cfg.show_categories else [],
        "featured": featured,
    }

    if cfg.show_most_asked:
        top = await retrieval.most_asked(db, limit=5,
                                         product_areas=cfg.allowed_product_areas)
        panel["most_asked"] = [
            {"slug": p.slug, "title": p.title, "product_area": p.product_area}
            for p in top
        ]

    tools = TenantAssistantTools(db, tenant_id, allowed=cfg.allowed_tools,
                                 product_areas=cfg.allowed_product_areas)

    if cfg.show_live_state and "get_readiness_snapshot" in (cfg.allowed_tools or []):
        snap = await tools._tool_get_readiness_snapshot()
        panel["live_state"] = {
            "looks_ready": snap.get("looks_ready"),
            "blockers": snap.get("blockers", []),
            "account_status": snap.get("account_status"),
        }

    if cfg.show_recent_requests:
        reqs = await tools._tool_get_open_requests()
        panel["open_requests"] = reqs.get("requests", [])

    if cfg.show_announcements:
        ann = await tools._tool_get_announcements()
        panel["announcements"] = ann.get("announcements", [])

    if cfg.show_page_context and path:
        panel["page_context"] = _page_hint(path)

    return panel


def _page_hint(path: str) -> dict | None:
    for key, (route, label) in C.PORTAL_ROUTES.items():
        base = route.split("?")[0]
        if base != "/" and path.startswith(base):
            return {"key": key, "route": route, "label": label}
    return None


# ══════════════════════════════════════════════════════════════════════════════
# Deterministic option actions (zero LLM calls)
# ══════════════════════════════════════════════════════════════════════════════
async def run_option(db: AsyncSession, cfg: TenantAssistantConfig, option_id: uuid.UUID, *,
                     tenant_id: uuid.UUID, user_id: uuid.UUID, role: str | None,
                     path: str | None) -> dict:
    o = (await db.execute(select(TenantAssistantOption)
                          .where(TenantAssistantOption.id == option_id))).scalars().first()
    if not o or not o.is_enabled:
        raise AssistantError("ASSISTANT_OPTION_NOT_FOUND", "That option is no longer available.", 404)

    o.click_count = (o.click_count or 0) + 1
    session = await _active_session(db, cfg, tenant_id=tenant_id, user_id=user_id,
                                    user_role=role, path=path)
    await _record(db, session, role=C.ROLE_USER, content=o.label)

    if o.action_type == C.ACTION_TICKET:
        return {"kind": "escalate", "session_id": str(session.id),
                "prefill": {"subject": o.label}}

    if o.action_type == C.ACTION_LINK:
        route = C.PORTAL_ROUTES.get(o.action_target or "", (o.action_target, o.label))
        return {"kind": "link", "route": route[0], "label": route[1]}

    if o.action_type == C.ACTION_TOPIC:
        passages = await retrieval.by_area(db, o.action_target or "", limit=10)
        return {"kind": "article_list", "product_area": o.action_target,
                "articles": [{"slug": p.slug, "title": p.title, "summary": p.summary}
                             for p in passages]}

    if o.action_type == C.ACTION_ARTICLE:
        p = await retrieval.by_slug(db, o.action_target or "")
        if not p:
            return {"kind": "answer", "answer": cfg.no_answer_message,
                    "resolution": C.RES_NO_ANSWER, "citations": [], "can_escalate": True}
        await retrieval.record_view(db, p.article_id)
        msg = await _record(db, session, role=C.ROLE_ASSISTANT,
                            content=p.body or p.summary or p.title,
                            resolution=C.RES_ANSWERED, citations=[p.as_citation()])
        return {"kind": "answer", "message_id": str(msg.id),
                "answer": p.body or p.summary or p.title,
                "resolution": C.RES_ANSWERED, "citations": [p.as_citation()],
                "can_escalate": cfg.escalation_enabled}

    if o.action_type == C.ACTION_TOOL:
        tools = TenantAssistantTools(db, tenant_id, allowed=cfg.allowed_tools,
                                     product_areas=cfg.allowed_product_areas)
        raw = await tools.execute(o.action_target or "")
        msg = await _record(db, session, role=C.ROLE_ASSISTANT, content=raw,
                            resolution=C.RES_ANSWERED, tools_used=tools.calls)
        return {"kind": "data", "message_id": str(msg.id),
                "tool": o.action_target, "data": raw,
                "can_escalate": cfg.escalation_enabled}

    if o.action_type == C.ACTION_PROMPT:
        return await ask(db, cfg, question=o.action_target or o.label,
                         tenant_id=tenant_id, user_id=user_id, role=role, path=path)

    raise AssistantError("ASSISTANT_UNKNOWN_ACTION", "Unsupported option type.", 400)


# ══════════════════════════════════════════════════════════════════════════════
# Free-text answering
# ══════════════════════════════════════════════════════════════════════════════
def _out_of_scope(question: str) -> bool:
    low = (question or "").lower()
    return any(p in low for p in C.OUT_OF_SCOPE_PATTERNS)


async def ask(db: AsyncSession, cfg: TenantAssistantConfig, *, question: str,
              tenant_id: uuid.UUID, user_id: uuid.UUID, role: str | None,
              path: str | None = None, request_id: str = "—") -> dict:
    started = time.monotonic()
    question = (question or "").strip()[:C.MAX_QUESTION_CHARS]
    if not question:
        raise AssistantError("ASSISTANT_EMPTY_QUESTION", "Type a question first.")

    session = await _active_session(db, cfg, tenant_id=tenant_id, user_id=user_id,
                                    user_role=role, path=path)
    session.turn_count = (session.turn_count or 0) + 1
    session.last_activity_at = utcnow()
    await _record(db, session, role=C.ROLE_USER, content=question)

    def _reply(answer: str, resolution: str, **extra) -> dict:
        return {"kind": "answer", "session_id": str(session.id), "answer": answer,
                "resolution": resolution,
                "can_escalate": cfg.escalation_enabled,
                "should_escalate": (
                    cfg.escalation_enabled
                    and resolution in C.UNRESOLVED
                    and session.unresolved_streak >= cfg.auto_escalate_after_unresolved
                ), **extra}

    # 1 ── rate limit
    if await _rate_limited(db, cfg, session):
        msg = await _record(db, session, role=C.ROLE_ASSISTANT,
                            content="Rate limit reached.", resolution=C.RES_RATE_LIMITED)
        return _reply("You have asked a lot of questions this hour. Please try again "
                      "shortly, or raise a support ticket and the team will reply.",
                      C.RES_RATE_LIMITED, message_id=str(msg.id))

    # 2 ── scope guard, before any spend
    if _out_of_scope(question):
        session.unresolved_streak = (session.unresolved_streak or 0) + 1
        msg = await _record(db, session, role=C.ROLE_ASSISTANT,
                            content=cfg.out_of_scope_message, resolution=C.RES_OUT_OF_SCOPE)
        return _reply(cfg.out_of_scope_message, C.RES_OUT_OF_SCOPE, message_id=str(msg.id))

    # 3 ── retrieve
    found = await retrieval.search(db, question, top_k=cfg.retrieval_top_k,
                                   product_areas=cfg.allowed_product_areas)
    threshold = float(cfg.retrieval_min_score)
    passages = [p for p in found.passages if p.score >= threshold]

    # 4 ── tenant data, when the question is about their own account
    tools = TenantAssistantTools(db, tenant_id, allowed=cfg.allowed_tools,
                                 product_areas=cfg.allowed_product_areas)
    tool_context = ""
    if _wants_own_data(question) and cfg.allowed_tools:
        for name in _pick_tools(question, cfg.allowed_tools):
            tool_context += f"\n[live:{name}] {await tools.execute(name)}"

    # 5 ── gate: nothing to ground an answer in
    if not passages and not tool_context:
        session.unresolved_streak = (session.unresolved_streak or 0) + 1
        msg = await _record(db, session, role=C.ROLE_ASSISTANT,
                            content=cfg.no_answer_message, resolution=C.RES_NO_ANSWER,
                            score=found.top_score)
        return _reply(cfg.no_answer_message, C.RES_NO_ANSWER, message_id=str(msg.id),
                      citations=[])

    citations = [p.as_citation() for p in passages]

    # 6 ── render
    if not cfg.llm_enabled:
        answer = _deterministic_answer(passages, tool_context)
        session.unresolved_streak = 0
        msg = await _record(db, session, role=C.ROLE_ASSISTANT, content=answer,
                            resolution=C.RES_ANSWERED, citations=citations,
                            tools_used=tools.calls, score=found.top_score,
                            latency_ms=int((time.monotonic() - started) * 1000))
        return _reply(answer, C.RES_ANSWERED, message_id=str(msg.id), citations=citations)

    context = C.CONTEXT_HEADER + "\n\n".join(p.as_context() for p in passages) + tool_context
    answer, ok_answer = await _render_with_llm(
        db, cfg, question=question, context=context, session_id=str(session.id),
        request_id=request_id,
    )

    if not ok_answer:
        session.unresolved_streak = (session.unresolved_streak or 0) + 1
        msg = await _record(db, session, role=C.ROLE_ASSISTANT,
                            content=cfg.no_answer_message, resolution=C.RES_NO_ANSWER,
                            score=found.top_score, used_llm=True)
        return _reply(cfg.no_answer_message, C.RES_NO_ANSWER, message_id=str(msg.id))

    session.unresolved_streak = 0
    msg = await _record(db, session, role=C.ROLE_ASSISTANT, content=answer,
                        resolution=C.RES_ANSWERED, citations=citations,
                        tools_used=tools.calls, score=found.top_score, used_llm=True,
                        latency_ms=int((time.monotonic() - started) * 1000))
    for p in passages[:2]:
        await retrieval.record_view(db, p.article_id)
    return _reply(answer, C.RES_ANSWERED, message_id=str(msg.id), citations=citations)


_OWN_DATA_HINTS = ("my ", "our ", "i have", "we have", "am i", "are we",
                   "how many", "status", "pending", "stand", "ready", "left")
_TOOL_HINTS = {
    "get_job_summary":        ("job", "booking", "work", "dispatch", "schedule"),
    "get_team_summary":       ("staff", "technician", "team", "member", "people"),
    "get_business_profile":   ("plan", "package", "profile", "account", "subscription", "health"),
    "get_readiness_snapshot": ("ready", "live", "pending", "stand", "blocked", "activate", "start"),
    "get_open_requests":      ("ticket", "request", "raised", "complaint", "support"),
    "get_platform_status":    ("down", "outage", "incident", "not working", "slow"),
}


def _wants_own_data(question: str) -> bool:
    low = question.lower()
    return any(h in low for h in _OWN_DATA_HINTS)


def _pick_tools(question: str, allowed: list[str]) -> list[str]:
    low = question.lower()
    picked = [name for name, hints in _TOOL_HINTS.items()
              if name in allowed and any(h in low for h in hints)]
    return picked[:2]


def _deterministic_answer(passages, tool_context: str) -> str:
    """Used when an admin turns the LLM off — the assistant still works, it
    just quotes the help centre verbatim instead of paraphrasing."""
    parts = []
    for p in passages[:2]:
        parts.append(f"{p.title}\n{(p.body or p.summary or '').strip()}")
    if tool_context:
        parts.append("From your account:" + tool_context)
    return "\n\n".join(parts) if parts else ""


async def _render_with_llm(db: AsyncSession, cfg: TenantAssistantConfig, *, question: str,
                           context: str, session_id: str, request_id: str) -> tuple[str, bool]:
    """Call DeepSeek purely to phrase retrieved context. Returns (answer, ok)."""
    from app.engines.ai_conversation.deepseek_client import DeepSeekClientService
    from app.engines.ai_conversation.safety import (
        detect_prompt_injection, validate_assistant_reply,
    )

    if detect_prompt_injection(question):
        return "", False

    system = cfg.system_prompt.replace("{display_name}", cfg.display_name)
    messages = [
        {"role": "system", "content": system},
        {"role": "system", "content": context},
        {"role": "user", "content": question},
    ]
    try:
        # session_id stays None: ai_llm_call_logs.session_id is FK-bound to
        # ai_conversation_sessions (the customer assistant). Passing our own
        # session id violates that FK and rolls the whole request back. Our
        # own latency/usage is recorded on tenant_assistant_messages instead.
        client = DeepSeekClientService(db, session_id=None, request_id=request_id)
        raw = await client.chat(messages)
        answer = (raw.get("choices") or [{}])[0].get("message", {}).get("content", "")
    except Exception as exc:                                       # noqa: BLE001
        logger.warning("tenant_assistant.llm_failed", error=str(exc))
        return "", False

    answer = (answer or "").strip()
    if not answer:
        return "", False
    cleaned, _violations = validate_assistant_reply(answer)
    if C.NO_CONTEXT_SENTINEL in cleaned:
        return "", False
    return cleaned, True


# ══════════════════════════════════════════════════════════════════════════════
# Escalation — the assistant hands over to a real human queue
# ══════════════════════════════════════════════════════════════════════════════
async def escalate(db: AsyncSession, cfg: TenantAssistantConfig, *,
                   session_id: uuid.UUID | None, tenant_id: uuid.UUID,
                   user_id: uuid.UUID, user_name: str | None, user_role: str | None,
                   subject: str, description: str,
                   category: str | None = None, impact: str | None = None) -> dict:
    """Creates a real SupportTicket. The tenant then sees admin replies on the
    existing Help & Support page, and the support engine's own notification
    events deliver in-app + email."""
    if not cfg.escalation_enabled:
        raise AssistantError("ASSISTANT_ESCALATION_DISABLED",
                             "Raising a ticket from the assistant is turned off.", 403)

    session = None
    if session_id:
        session = (await db.execute(select(TenantAssistantSession).where(
            TenantAssistantSession.id == session_id,
            TenantAssistantSession.tenant_id == tenant_id,
        ))).scalars().first()

    body = (description or "").strip()
    if session and cfg.escalation_include_transcript:
        body = f"{body}\n\n--- Assistant conversation ---\n{await _transcript(db, session)}"

    ticket = await support_svc.create_ticket(
        db,
        tenant_id=tenant_id, reporter_user_id=user_id,
        reporter_name=user_name, reporter_role=user_role,
        category=category or cfg.escalation_category,
        subject=subject.strip()[:300],
        description=body,
        impact=impact or cfg.escalation_impact,
        affected_feature="AI assistant escalation",
        related_entities={"assistant_session_id": str(session.id)} if session else None,
    )

    if session:
        session.status = C.SESSION_ESCALATED
        session.escalated_ticket_id = ticket.id
        session.unresolved_streak = 0
        await _record(db, session, role=C.ROLE_SYSTEM,
                      content=f"Escalated to support request {ticket.ticket_number}.",
                      resolution=C.RES_ESCALATED)

    logger.info("tenant_assistant.escalated", tenant_id=str(tenant_id),
                ticket=ticket.ticket_number)
    return {
        "ticket_id": str(ticket.id),
        "ticket_number": ticket.ticket_number,
        "status": ticket.status,
        "priority": ticket.priority,
        "deep_link": SC.DEEP_LINK.format(ticket_id=ticket.id),
    }


async def _transcript(db: AsyncSession, session: TenantAssistantSession) -> str:
    rows = (await db.execute(
        select(TenantAssistantMessage)
        .where(TenantAssistantMessage.session_id == session.id)
        .order_by(TenantAssistantMessage.created_at)
    )).scalars().all()
    lines = []
    for m in rows:
        who = {"user": "Tenant", "assistant": "Assistant"}.get(m.role, "System")
        lines.append(f"{who}: {m.content}")
    out = "\n".join(lines)
    return out[-C.MAX_TRANSCRIPT_CHARS:]


# ══════════════════════════════════════════════════════════════════════════════
# History + feedback
# ══════════════════════════════════════════════════════════════════════════════
async def history(db: AsyncSession, *, tenant_id: uuid.UUID, user_id: uuid.UUID,
                  limit: int = 30) -> dict:
    s = (await db.execute(
        select(TenantAssistantSession)
        .where(TenantAssistantSession.user_id == user_id,
               TenantAssistantSession.tenant_id == tenant_id)
        .order_by(TenantAssistantSession.last_activity_at.desc())
    )).scalars().first()
    if not s:
        return {"session": None, "messages": []}
    rows = (await db.execute(
        select(TenantAssistantMessage)
        .where(TenantAssistantMessage.session_id == s.id)
        .order_by(TenantAssistantMessage.created_at.desc()).limit(limit)
    )).scalars().all()
    return {"session": s.to_dict(),
            "messages": [m.to_dict() for m in reversed(rows)]}


async def rate(db: AsyncSession, *, message_id: uuid.UUID, tenant_id: uuid.UUID,
               user_id: uuid.UUID, is_helpful: bool, note: str | None = None) -> dict:
    m = (await db.execute(select(TenantAssistantMessage).where(
        TenantAssistantMessage.id == message_id,
        TenantAssistantMessage.tenant_id == tenant_id,
    ))).scalars().first()
    if not m:
        raise AssistantError("ASSISTANT_MESSAGE_NOT_FOUND", "That answer is no longer available.", 404)

    existing = (await db.execute(select(TenantAssistantFeedback).where(
        TenantAssistantFeedback.message_id == message_id,
        TenantAssistantFeedback.user_id == user_id,
    ))).scalars().first()
    if existing:
        existing.is_helpful = is_helpful
        existing.note = note
    else:
        db.add(TenantAssistantFeedback(message_id=message_id, tenant_id=tenant_id,
                                       user_id=user_id, is_helpful=is_helpful, note=note))

    # Feed the help centre's own counters so "most asked" stays honest.
    for cite in (m.citations or []):
        col = "helpful_count" if is_helpful else "not_helpful_count"
        await db.execute(text(
            f"UPDATE support_knowledge_articles SET {col} = {col} + 1 WHERE id = :id"
        ), {"id": cite.get("article_id")})
    return {"recorded": True, "is_helpful": is_helpful}


# ══════════════════════════════════════════════════════════════════════════════
# Admin analytics
# ══════════════════════════════════════════════════════════════════════════════
async def analytics(db: AsyncSession, days: int = 30) -> dict:
    since = utcnow() - timedelta(days=days)
    rows = (await db.execute(text("""
        SELECT resolution, count(*) AS n
        FROM tenant_assistant_messages
        WHERE role = 'assistant' AND created_at >= :since
        GROUP BY resolution
    """), {"since": since})).mappings().all()
    by_res = {r["resolution"] or "unknown": int(r["n"]) for r in rows}
    total = sum(by_res.values())
    answered = by_res.get(C.RES_ANSWERED, 0)

    # A question counts as a gap only when the answer that IMMEDIATELY follows
    # it failed. Matching any later failure in the session would mark every
    # answered question in a conversation that later went wrong.
    unanswered = (await db.execute(text("""
        WITH paired AS (
            SELECT m.content,
                   (SELECT a.resolution
                      FROM tenant_assistant_messages a
                     WHERE a.session_id = m.session_id
                       AND a.role = 'assistant'
                       AND a.created_at >= m.created_at
                     ORDER BY a.created_at
                     LIMIT 1) AS outcome
              FROM tenant_assistant_messages m
             WHERE m.role = 'user' AND m.created_at >= :since
        )
        SELECT content, count(*) AS n
          FROM paired
         WHERE outcome IN ('no_answer', 'out_of_scope')
         GROUP BY content ORDER BY n DESC LIMIT 15
    """), {"since": since})).mappings().all()

    escalations = (await db.execute(text("""
        SELECT count(*) FROM tenant_assistant_sessions
        WHERE status = 'escalated' AND last_activity_at >= :since
    """), {"since": since})).scalar() or 0

    top_options = (await db.execute(
        select(TenantAssistantOption)
        .order_by(TenantAssistantOption.click_count.desc()).limit(10)
    )).scalars().all()

    return {
        "window_days": days,
        "total_answers": total,
        "by_resolution": by_res,
        "answer_rate": round(answered / total, 3) if total else None,
        "escalations": int(escalations),
        "content_gaps": [{"question": r["content"], "times": int(r["n"])} for r in unanswered],
        "top_options": [{"label": o.label, "group": o.group_key,
                         "clicks": o.click_count} for o in top_options],
    }
