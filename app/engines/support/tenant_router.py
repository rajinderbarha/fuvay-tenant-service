"""TENANT-SUPPORT tenant API — /v1/tenant/support/*

Tenant-facing only. Every admin-only capability (assign, set priority,
internal note, arbitrary status, incident create/resolve) lives in
admin_router.py and is unreachable from here. The frontend never submits
tenant_id, priority, SLA, assignee, status or internal notes — all of those
are backend-derived (section 21).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import P, permission_checker
from app.dependencies.auth import UserContext, get_current_user
from app.dependencies.db import get_db
from app.engines.media.models import MediaAsset
from app.engines.support import constants as C
from app.engines.support import service as svc
from app.engines.support.models import SupportTicket
from app.schemas.base import ok

router = APIRouter(prefix="/v1/tenant/support", tags=["Tenant Help & Support"])

utcnow = lambda: datetime.now(timezone.utc)


def _tid(user: UserContext) -> uuid.UUID:
    if not user.tenant_id:
        raise HTTPException(403, "No tenant context")
    return uuid.UUID(user.tenant_id)


def _rid(request: Request) -> str:
    return getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID", "—")


def _perm(user: UserContext, permission: str) -> bool:
    return permission_checker.has(user.role, permission, user.permission_overrides)


def _read_only(user: UserContext) -> bool:
    return user.access_scope == "customer_support_limited"


def _can_submit(user: UserContext) -> bool:
    return _perm(user, P.SUPPORT_REQUESTS_CREATE) and not _read_only(user)


def _require_view(user: UserContext) -> None:
    if not _perm(user, P.SUPPORT_REQUESTS_VIEW):
        raise HTTPException(403, "You do not have access to support requests.")


def _permissions(user: UserContext) -> dict:
    return {
        "can_view": _perm(user, P.SUPPORT_REQUESTS_VIEW),
        "can_view_all": _perm(user, P.SUPPORT_REQUESTS_VIEW_ALL),
        "can_create": _can_submit(user),
        "can_reply": _perm(user, P.SUPPORT_REQUESTS_REPLY) and not _read_only(user),
        "can_reopen": _perm(user, P.SUPPORT_REQUESTS_REOPEN) and not _read_only(user),
        "can_report_critical_incident": _perm(user, P.SUPPORT_INCIDENT_REPORT) and not _read_only(user),
        "read_only": _read_only(user),
        "role": user.role,
    }


async def _load(db: AsyncSession, ticket_id: uuid.UUID, user: UserContext) -> SupportTicket:
    """Tenant isolation: a ticket outside the caller's tenant is a 404, never a
    hint that it exists. Users without view_all only reach their own cases."""
    t = (await db.execute(select(SupportTicket).where(
        SupportTicket.id == ticket_id,
        SupportTicket.tenant_id == _tid(user),
    ))).scalars().first()
    if not t:
        raise HTTPException(404, "Support request not found.")
    if not _perm(user, P.SUPPORT_REQUESTS_VIEW_ALL) and str(t.reporter_user_id) != user.user_id:
        raise HTTPException(404, "Support request not found.")
    return t


# ══════════════════════════════════════════════════════════════════════════════
# Workspace
# ══════════════════════════════════════════════════════════════════════════════
@router.get("/workspace")
async def get_workspace(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
):
    """One round trip for the initial page load: status banner, quick-help
    categories, summary, requests, featured knowledge and announcements."""
    _require_view(user)
    tid = _tid(user)
    mine_only = not _perm(user, P.SUPPORT_REQUESTS_VIEW_ALL)
    rows, total = await svc.list_tickets(
        db, tenant_id=tid,
        submitted_by=uuid.UUID(user.user_id) if mine_only else None, limit=200,
    )
    kb = await svc.knowledge(db, role=user.role, limit=60)
    return ok({
        "service_status": await svc.service_status(db),
        "summary": await svc.summary(db, tid),
        "requests": [svc.ticket_row(t) for t in rows],
        "requests_total": total,
        "quick_help": kb["categories"],
        "recommended_articles": kb["featured"],
        "knowledge_total": kb["total_published"],
        "announcements": (await svc.announcements(
            db, tenant_id=tid, user_id=uuid.UUID(user.user_id), role=user.role))["items"],
        "form_options": {
            "categories": [{"key": c["key"], "label": c["label"]} for c in C.CATEGORIES],
            "subcategories": C.SUBCATEGORY_SUGGESTIONS,
            "impacts": [{"key": k, "label": C.IMPACT_LABELS[k]} for k in C.IMPACTS],
            "critical_impacts": [{"key": k, "label": v} for k, v in C.CRITICAL_INCIDENT_IMPACTS],
            "related_entity_keys": sorted(svc.SAFE_RELATED_KEYS),
            "attachment_privacy_warning": C.ATTACHMENT_PRIVACY_WARNING,
        },
        "statuses": [{"key": s, "label": C.STATUS_LABELS[s]} for s in C.STATUSES],
        "priorities": C.PRIORITIES,
        "permissions": _permissions(user),
        "complaints_redirect": {
            "message": "For a customer complaint about a job, open Complaints.",
            "href": "/home-services/complaints",
        },
    }, request_id=_rid(request))


@router.get("/service-status")
async def get_service_status(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
):
    _tid(user)
    return ok(await svc.service_status(db), request_id=_rid(request))


# ══════════════════════════════════════════════════════════════════════════════
# Requests
# ══════════════════════════════════════════════════════════════════════════════
@router.get("/requests")
async def list_requests(
    request: Request,
    search: str | None = None,
    category: str | None = None,
    status: str | None = None,
    priority: str | None = None,
    submitted_by: uuid.UUID | None = None,
    created_from: datetime | None = None,
    updated_from: datetime | None = None,
    limit: int = Query(100, le=200),
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
):
    _require_view(user)
    if not _perm(user, P.SUPPORT_REQUESTS_VIEW_ALL):
        submitted_by = uuid.UUID(user.user_id)
    rows, total = await svc.list_tickets(
        db, tenant_id=_tid(user), search=search, category=category, status=status,
        priority=priority, submitted_by=submitted_by, created_from=created_from,
        updated_from=updated_from, limit=limit, offset=offset,
    )
    return ok({"items": [svc.ticket_row(t) for t in rows], "total": total,
               "summary": await svc.summary(db, _tid(user))}, request_id=_rid(request))


class CreateRequestIn(BaseModel):
    """Note what is ABSENT and can never be submitted: tenant_id, priority,
    status, assignee, SLA fields, internal notes."""
    category: str
    subject: str = Field(min_length=3, max_length=300)
    description: str = Field(min_length=10)
    impact: str
    subcategory: str | None = None
    affected_feature: str | None = None
    started_at: datetime | None = None
    related_entities: dict[str, str] | None = None
    attachment_media_ids: list[uuid.UUID] | None = None
    acknowledge_similar: bool = False


@router.post("/requests")
async def create_request(
    payload: CreateRequestIn,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
):
    if not _can_submit(user):
        raise HTTPException(403, "You do not have permission to create support requests.")
    tid = _tid(user)

    similar = await svc.find_similar_open(db, tid, payload.category, payload.subject)
    t = await svc.create_ticket(
        db, tenant_id=tid, reporter_user_id=uuid.UUID(user.user_id),
        reporter_name=user.full_name, reporter_role=user.role,
        category=payload.category, subject=payload.subject,
        description=payload.description, impact=payload.impact,
        subcategory=payload.subcategory, affected_feature=payload.affected_feature,
        started_at=payload.started_at, related_entities=payload.related_entities,
        vertical_key="home_services" if "home_services" in (user.enabled_engines or []) else None,
    )
    if payload.attachment_media_ids:
        await _attach(db, t, payload.attachment_media_ids, user)
    await db.commit()
    await db.refresh(t)
    detail = await svc.ticket_detail(db, t, for_admin=False, can_submit=_can_submit(user))
    detail["similar_open_requests"] = similar   # warn, never block
    return ok(detail, request_id=_rid(request))


class CriticalIncidentIn(BaseModel):
    critical_impact_key: str
    subject: str = Field(min_length=3, max_length=300)
    description: str = Field(min_length=10)
    affected_feature: str | None = None
    started_at: datetime | None = None


@router.post("/critical-incident")
async def report_critical_incident(
    payload: CriticalIncidentIn,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
):
    """Restrained channel (section 17). Permission-gated, rate-limited, routed
    to Fuvay Incident Response, audited. Not a shortcut for questions."""
    if not (_perm(user, P.SUPPORT_INCIDENT_REPORT) and not _read_only(user)):
        raise HTTPException(403, "Only an owner can report a critical platform incident.")
    if payload.critical_impact_key not in C.CRITICAL_INCIDENT_IMPACT_KEYS:
        raise HTTPException(400, "Choose one of the listed critical impact types.")
    tid = _tid(user)
    await svc.check_critical_rate_limit(db, tid)
    t = await svc.create_ticket(
        db, tenant_id=tid, reporter_user_id=uuid.UUID(user.user_id),
        reporter_name=user.full_name, reporter_role=user.role,
        category="technical" if payload.critical_impact_key != "security_incident" else "security",
        subject=payload.subject, description=payload.description,
        impact=C.IMPACT_BUSINESS_BLOCKED, affected_feature=payload.affected_feature,
        started_at=payload.started_at, is_critical_incident=True,
        critical_impact_key=payload.critical_impact_key,
    )
    await db.commit()
    await db.refresh(t)
    return ok(await svc.ticket_detail(db, t, for_admin=False, can_submit=_can_submit(user)),
              request_id=_rid(request))


@router.get("/requests/{ticket_id}")
async def get_request(
    ticket_id: uuid.UUID,
    request: Request,
    mark_read: bool = True,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
):
    _require_view(user)
    t = await _load(db, ticket_id, user)
    detail = await svc.ticket_detail(db, t, for_admin=False, can_submit=_can_submit(user))
    if mark_read and t.tenant_unread_count:
        t.tenant_unread_count = 0
        await db.commit()
    return ok(detail, request_id=_rid(request))


class MessageIn(BaseModel):
    body: str = Field(min_length=1)
    attachment_ids: list[uuid.UUID] | None = None


@router.post("/requests/{ticket_id}/messages")
async def add_reply(
    ticket_id: uuid.UUID,
    payload: MessageIn,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
):
    if not (_perm(user, P.SUPPORT_REQUESTS_REPLY) and not _read_only(user)):
        raise HTTPException(403, "You do not have permission to reply on support requests.")
    t = await _load(db, ticket_id, user)
    await svc.tenant_reply(db, t, body=payload.body, user_id=uuid.UUID(user.user_id),
                           user_name=user.full_name, user_role=user.role,
                           attachment_ids=payload.attachment_ids)
    await db.commit()
    await db.refresh(t)
    return ok(await svc.ticket_detail(db, t, for_admin=False, can_submit=_can_submit(user)),
              request_id=_rid(request))


class AttachmentsIn(BaseModel):
    media_asset_ids: list[uuid.UUID]


async def _attach(db: AsyncSession, t: SupportTicket, ids: list[uuid.UUID],
                  user: UserContext) -> list[dict]:
    """Attachments always resolve through the canonical media engine, scoped to
    the caller's tenant and to the support_attachment context — a media id
    belonging to another tenant or another context is rejected, never linked."""
    from app.engines.support.models import SupportTicketAttachment
    out = []
    for mid in ids:
        asset = (await db.execute(select(MediaAsset).where(
            MediaAsset.id == mid,
            MediaAsset.tenant_id == t.tenant_id,
            MediaAsset.media_context == C.SUPPORT_MEDIA_CONTEXT,
            MediaAsset.status == "active",
        ))).scalars().first()
        if not asset:
            raise HTTPException(400, "One or more attachments are not available for this request.")
        ext = (asset.file_extension or "").lstrip(".").lower()
        if ext in C.BLOCKED_ATTACHMENT_EXTENSIONS:
            raise HTTPException(400, f".{ext} files cannot be attached to a support request.")
        if asset.file_size_bytes and asset.file_size_bytes > C.MAX_ATTACHMENT_BYTES:
            raise HTTPException(400, "Attachment exceeds the maximum allowed size.")
        row = SupportTicketAttachment(
            ticket_id=t.id, media_asset_id=asset.id,
            file_name=asset.file_name_original, mime_type=asset.mime_type,
            size_bytes=asset.file_size_bytes,
            uploaded_by=uuid.UUID(user.user_id), uploaded_by_type="tenant",
        )
        db.add(row)
        out.append({"media_asset_id": str(asset.id), "file_name": asset.file_name_original})
    await svc.log_event(db, t.id, "attachment_added", to_value=str(len(out)),
                        actor_user_id=uuid.UUID(user.user_id), actor_type="tenant",
                        actor_name=user.full_name)
    await db.flush()
    return out


@router.post("/requests/{ticket_id}/attachments")
async def add_attachments(
    ticket_id: uuid.UUID,
    payload: AttachmentsIn,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
):
    if not (_perm(user, P.SUPPORT_REQUESTS_REPLY) and not _read_only(user)):
        raise HTTPException(403, "You do not have permission to attach files.")
    t = await _load(db, ticket_id, user)
    if t.status not in C.OPEN_STATUSES:
        raise HTTPException(409, "This request is no longer open for attachments.")
    await _attach(db, t, payload.media_asset_ids, user)
    await db.commit()
    await db.refresh(t)
    return ok(await svc.ticket_detail(db, t, for_admin=False, can_submit=_can_submit(user)),
              request_id=_rid(request))


class ReopenIn(BaseModel):
    reason: str = Field(min_length=3)


@router.post("/requests/{ticket_id}/reopen")
async def reopen_request(
    ticket_id: uuid.UUID,
    payload: ReopenIn,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
):
    if not (_perm(user, P.SUPPORT_REQUESTS_REOPEN) and not _read_only(user)):
        raise HTTPException(403, "You do not have permission to reopen support requests.")
    t = await _load(db, ticket_id, user)
    await svc.tenant_reopen(db, t, reason=payload.reason, user_id=uuid.UUID(user.user_id),
                            user_name=user.full_name)
    await db.commit()
    await db.refresh(t)
    return ok(await svc.ticket_detail(db, t, for_admin=False, can_submit=_can_submit(user)),
              request_id=_rid(request))


@router.post("/requests/{ticket_id}/confirm-resolution")
async def confirm_resolution(
    ticket_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
):
    """Tenant confirms a Fuvay resolution -> the case closes. The tenant
    can only reach 'closed' from 'resolved' — never an arbitrary status."""
    if not (_perm(user, P.SUPPORT_REQUESTS_REPLY) and not _read_only(user)):
        raise HTTPException(403, "You do not have permission to confirm a resolution.")
    t = await _load(db, ticket_id, user)
    if t.status != C.ST_RESOLVED:
        raise HTTPException(409, "Only a resolved request can be confirmed.")
    t.status = C.ST_CLOSED
    t.closed_at = utcnow()
    await svc.log_event(db, t.id, "status_changed", from_value=C.ST_RESOLVED,
                        to_value=C.ST_CLOSED, reason="Tenant confirmed the resolution",
                        actor_user_id=uuid.UUID(user.user_id), actor_type="tenant",
                        actor_name=user.full_name)
    await db.commit()
    await db.refresh(t)
    return ok(await svc.ticket_detail(db, t, for_admin=False, can_submit=_can_submit(user)),
              request_id=_rid(request))


@router.post("/requests/{ticket_id}/escalate")
async def escalate_request(
    ticket_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
):
    if not (_perm(user, P.SUPPORT_REQUESTS_REPLY) and not _read_only(user)):
        raise HTTPException(403, "You do not have permission to escalate this request.")
    t = await _load(db, ticket_id, user)
    await svc.tenant_escalate(db, t, user_id=uuid.UUID(user.user_id), user_name=user.full_name)
    await db.commit()
    await db.refresh(t)
    return ok(await svc.ticket_detail(db, t, for_admin=False, can_submit=_can_submit(user)),
              request_id=_rid(request))


# ══════════════════════════════════════════════════════════════════════════════
# Knowledge base + announcements
# ══════════════════════════════════════════════════════════════════════════════
@router.get("/knowledge")
async def get_knowledge(
    request: Request,
    search: str | None = None,
    area: str | None = None,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
):
    _tid(user)
    return ok(await svc.knowledge(db, search=search, area=area, role=user.role),
              request_id=_rid(request))


class ArticleFeedbackIn(BaseModel):
    is_helpful: bool
    comment: str | None = None


@router.post("/knowledge/{article_id}/feedback")
async def post_article_feedback(
    article_id: uuid.UUID,
    payload: ArticleFeedbackIn,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
):
    await svc.article_feedback(db, article_id, is_helpful=payload.is_helpful,
                               tenant_id=_tid(user), user_id=uuid.UUID(user.user_id),
                               comment=payload.comment)
    await db.commit()
    return ok({"recorded": True}, request_id=_rid(request))


@router.get("/announcements")
async def get_announcements(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
):
    return ok(await svc.announcements(db, tenant_id=_tid(user),
                                      user_id=uuid.UUID(user.user_id), role=user.role),
              request_id=_rid(request))


@router.post("/announcements/{announcement_id}/acknowledge")
async def acknowledge(
    announcement_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
):
    await svc.acknowledge_announcement(db, announcement_id, tenant_id=_tid(user),
                                        user_id=uuid.UUID(user.user_id))
    await db.commit()
    return ok({"acknowledged": True}, request_id=_rid(request))
