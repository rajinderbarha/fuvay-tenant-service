"""TENANT-SUPPORT admin API — /v1/admin/support/*

The canonical Super Admin support queue. There was NO admin support/ticket
queue anywhere in the codebase before this engine (audited), so this is the
one it is built as — the tenant surface is NOT a disconnected tenant-only
ticket system: both sides call app/engines/support/service.py.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import P, permission_checker
from app.dependencies.auth import UserContext, get_current_user
from app.dependencies.db import get_db
from app.engines.support import constants as C
from app.engines.support import service as svc
from app.engines.support.models import SupportPlatformIncident, SupportTicket
from app.schemas.base import ok

router = APIRouter(prefix="/v1/admin/support", tags=["Admin — Tenant Support Queue"])

utcnow = lambda: datetime.now(timezone.utc)


def _rid(request: Request) -> str:
    return getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID", "—")


def _require(user: UserContext, permission: str) -> None:
    if not permission_checker.has(user.role, permission, user.permission_overrides):
        raise HTTPException(403, "You do not have access to the Fuvay support queue.")


async def _load(db: AsyncSession, ticket_id: uuid.UUID) -> SupportTicket:
    t = (await db.execute(select(SupportTicket).where(SupportTicket.id == ticket_id))).scalars().first()
    if not t:
        raise HTTPException(404, "Support request not found.")
    return t


@router.get("/queue")
async def queue(
    request: Request,
    search: str | None = None,
    tenant_id: uuid.UUID | None = None,
    category: str | None = None,
    status: str | None = None,
    priority: str | None = None,
    limit: int = Query(100, le=200),
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
):
    _require(user, P.SUPPORT_ADMIN_QUEUE_VIEW)
    rows, total = await svc.list_tickets(
        db, tenant_id=tenant_id, search=search, category=category, status=status,
        priority=priority, limit=limit, offset=offset,
    )
    by_status = dict((await db.execute(
        select(SupportTicket.status, func.count()).group_by(SupportTicket.status)
    )).all())
    breached = 0
    for t in rows:
        if svc.sla_projection(t)["breach_state"] == C.BREACH_BREACHED:
            breached += 1
    return ok({
        "items": [svc.ticket_row(t) | {"tenant_id": str(t.tenant_id)} for t in rows],
        "total": total,
        "counts": {
            "open": sum(n for s, n in by_status.items() if s in C.OPEN_STATUSES),
            "unassigned": by_status.get(C.ST_SUBMITTED, 0),
            "waiting_for_tenant": by_status.get(C.ST_WAITING_FOR_TENANT, 0),
            "resolved": by_status.get(C.ST_RESOLVED, 0) + by_status.get(C.ST_CLOSED, 0),
            "sla_breached_on_page": breached,
            "by_status": by_status,
        },
        "categories": [{"key": c["key"], "label": c["label"]} for c in C.CATEGORIES],
        "priorities": C.PRIORITIES,
        "statuses": [{"key": s, "label": C.STATUS_LABELS[s]} for s in C.STATUSES],
    }, request_id=_rid(request))


@router.get("/requests/{ticket_id}")
async def detail(
    ticket_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
):
    _require(user, P.SUPPORT_ADMIN_QUEUE_VIEW)
    t = await _load(db, ticket_id)
    return ok(await svc.ticket_detail(db, t, for_admin=True), request_id=_rid(request))


class TriageIn(BaseModel):
    to_status: str
    reason: str | None = None
    resolution_summary: str | None = None


@router.post("/requests/{ticket_id}/transition")
async def transition(
    ticket_id: uuid.UUID,
    payload: TriageIn,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
):
    _require(user, P.SUPPORT_ADMIN_TRIAGE if payload.to_status != C.ST_RESOLVED
             else P.SUPPORT_ADMIN_RESOLVE)
    t = await _load(db, ticket_id)
    await svc.admin_transition(db, t, to_status=payload.to_status,
                               actor_user_id=uuid.UUID(user.user_id),
                               actor_name=user.full_name or "Fuvay Support",
                               reason=payload.reason,
                               resolution_summary=payload.resolution_summary)
    await db.commit()
    await db.refresh(t)
    return ok(await svc.ticket_detail(db, t, for_admin=True), request_id=_rid(request))


class AssignIn(BaseModel):
    team: str | None = None
    assignee_id: uuid.UUID | None = None
    assignee_name: str | None = None


@router.post("/requests/{ticket_id}/assign")
async def assign(
    ticket_id: uuid.UUID,
    payload: AssignIn,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
):
    _require(user, P.SUPPORT_ADMIN_TRIAGE)
    t = await _load(db, ticket_id)
    await svc.admin_assign(db, t, team=payload.team, assignee_id=payload.assignee_id,
                           assignee_name=payload.assignee_name,
                           actor_user_id=uuid.UUID(user.user_id),
                           actor_name=user.full_name or "Fuvay Support")
    await db.commit()
    await db.refresh(t)
    return ok(await svc.ticket_detail(db, t, for_admin=True), request_id=_rid(request))


class PriorityIn(BaseModel):
    priority: str
    reason: str = Field(min_length=3)


@router.post("/requests/{ticket_id}/priority")
async def set_priority(
    ticket_id: uuid.UUID,
    payload: PriorityIn,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
):
    _require(user, P.SUPPORT_ADMIN_TRIAGE)
    t = await _load(db, ticket_id)
    await svc.admin_set_priority(db, t, priority=payload.priority, reason=payload.reason,
                                 actor_user_id=uuid.UUID(user.user_id),
                                 actor_name=user.full_name or "Fuvay Support")
    await db.commit()
    await db.refresh(t)
    return ok(await svc.ticket_detail(db, t, for_admin=True), request_id=_rid(request))


class AdminReplyIn(BaseModel):
    body: str = Field(min_length=1)
    internal: bool = False
    request_info: bool = False


@router.post("/requests/{ticket_id}/messages")
async def reply(
    ticket_id: uuid.UUID,
    payload: AdminReplyIn,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
):
    _require(user, P.SUPPORT_ADMIN_INTERNAL_NOTE if payload.internal else P.SUPPORT_ADMIN_REPLY)
    t = await _load(db, ticket_id)
    await svc.admin_reply(db, t, body=payload.body, internal=payload.internal,
                          request_info=payload.request_info,
                          actor_user_id=uuid.UUID(user.user_id),
                          actor_name=user.full_name or "Fuvay Support")
    await db.commit()
    await db.refresh(t)
    return ok(await svc.ticket_detail(db, t, for_admin=True), request_id=_rid(request))


class MergeIn(BaseModel):
    merge_into_id: uuid.UUID
    reason: str = Field(min_length=3)


@router.post("/requests/{ticket_id}/merge")
async def merge(
    ticket_id: uuid.UUID,
    payload: MergeIn,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
):
    """Merge a duplicate WITHOUT losing history: the source case keeps its
    conversation and audit trail and is closed with a pointer, never deleted."""
    _require(user, P.SUPPORT_ADMIN_TRIAGE)
    t = await _load(db, ticket_id)
    target = await _load(db, payload.merge_into_id)
    if target.tenant_id != t.tenant_id:
        raise HTTPException(400, "Cannot merge support cases across tenants.")
    t.merged_into_id = target.id
    prev = t.status
    t.status = C.ST_CLOSED
    t.closed_at = utcnow()
    await svc.add_message(db, t, kind=C.MSG_SYSTEM,
                          body=f"Merged into {target.ticket_number}. {payload.reason}",
                          author_type="system", author_name="Fuvay")
    await svc.log_event(db, t.id, "merged", from_value=prev, to_value=target.ticket_number,
                        reason=payload.reason, actor_user_id=uuid.UUID(user.user_id),
                        actor_type="serviceos", actor_name=user.full_name)
    await db.commit()
    await db.refresh(t)
    return ok(await svc.ticket_detail(db, t, for_admin=True), request_id=_rid(request))


# ── Platform incidents / service status (admin-only, section 4/17) ───────────
class IncidentIn(BaseModel):
    title: str = Field(min_length=3, max_length=300)
    description: str | None = None
    severity: str = "minor"
    components: list[str] | None = None


@router.get("/incidents")
async def list_incidents(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
):
    _require(user, P.SUPPORT_ADMIN_QUEUE_VIEW)
    rows = (await db.execute(select(SupportPlatformIncident)
                             .order_by(SupportPlatformIncident.started_at.desc())
                             .limit(100))).scalars().all()
    return ok({"items": [{
        "id": str(i.id), "reference": i.reference, "title": i.title,
        "severity": i.severity, "status": i.status, "components": i.components or [],
        "started_at": i.started_at.isoformat() if i.started_at else None,
        "resolved_at": i.resolved_at.isoformat() if i.resolved_at else None,
    } for i in rows]}, request_id=_rid(request))


@router.post("/incidents")
async def create_incident(
    payload: IncidentIn,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
):
    _require(user, P.SUPPORT_ADMIN_INCIDENT_MANAGE)
    if payload.severity not in ("maintenance", "minor", "major"):
        raise HTTPException(400, "severity must be maintenance, minor or major.")
    inc = SupportPlatformIncident(
        reference="INC-" + uuid.uuid4().hex[:6].upper(), title=payload.title,
        description=payload.description, severity=payload.severity,
        components=payload.components or [], started_at=utcnow(),
        last_checked_at=utcnow(),
    )
    db.add(inc)
    await db.commit()
    return ok({"id": str(inc.id), "reference": inc.reference}, request_id=_rid(request))


@router.post("/incidents/{incident_id}/resolve")
async def resolve_incident(
    incident_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
):
    _require(user, P.SUPPORT_ADMIN_INCIDENT_MANAGE)
    inc = (await db.execute(select(SupportPlatformIncident)
                            .where(SupportPlatformIncident.id == incident_id))).scalars().first()
    if not inc:
        raise HTTPException(404, "Incident not found.")
    inc.status = "resolved"
    inc.resolved_at = utcnow()
    await db.commit()
    return ok({"id": str(inc.id), "status": inc.status}, request_id=_rid(request))


@router.post("/status/heartbeat")
async def heartbeat(
    request: Request,
    component: str = Query(...),
    is_healthy: bool = Query(True),
    detail: str | None = None,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
):
    """Real status evidence. Without a recent heartbeat the tenant banner shows
    'Status unavailable' instead of a fabricated green state."""
    _require(user, P.SUPPORT_ADMIN_INCIDENT_MANAGE)
    await svc.record_heartbeat(db, component, is_healthy, detail)
    await db.commit()
    return ok(await svc.service_status(db), request_id=_rid(request))
