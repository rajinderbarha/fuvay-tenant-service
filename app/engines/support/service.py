"""TENANT-SUPPORT service — the single canonical owner of ticket lifecycle,
priority derivation, SLA computation, conversation visibility and the
service-status projection. Both the tenant router and the admin router call
into here, so tenant and admin can never drift apart.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import Text, and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.platform_notifications.notification_service import NotificationService
from app.engines.support import constants as C
from app.engines.support.models import (
    SupportAnnouncement, SupportAnnouncementAck, SupportArticleFeedback,
    SupportKnowledgeArticle, SupportPlatformIncident, SupportStatusHeartbeat,
    SupportTicket, SupportTicketAttachment, SupportTicketEvent,
    SupportTicketMessage,
)
from app.exceptions import ServiceOSException

utcnow = lambda: datetime.now(timezone.utc)
_notif = NotificationService()

# Heartbeat staleness beyond which we refuse to claim "operational".
HEARTBEAT_STALE_MINUTES = 15


class SupportError(ServiceOSException):
    def __init__(self, code: str, message: str, resolution: str | None = None, status_code: int = 400):
        # Always pass an explicit status_code -- unregistered domain codes
        # otherwise default to 500 (see app/exceptions.py:206).
        super().__init__(error_code=code, detail=message, resolution=resolution,
                         status_code=status_code)


def _iso(dt: datetime | None) -> str | None:
    return dt.isoformat() if dt else None


# ══════════════════════════════════════════════════════════════════════════════
# SLA
# ══════════════════════════════════════════════════════════════════════════════
def apply_sla_targets(t: SupportTicket) -> None:
    """(Re)compute SLA due dates from the CURRENT derived priority. Only ever
    called server-side; a tenant can never submit these values."""
    fr, nu, res = C.SLA_TARGETS.get(t.priority, C.SLA_TARGETS[C.PRIORITY_NORMAL])
    base = t.created_at or utcnow()
    t.sla_policy = C.SLA_POLICY_NAME
    if not t.first_response_met_at:
        t.first_response_due_at = base + timedelta(hours=fr)
    t.next_update_due_at = utcnow() + timedelta(hours=nu)
    t.resolution_target_at = (base + timedelta(hours=res)) if res else None


def sla_projection(t: SupportTicket) -> dict:
    """Backend-derived SLA state. Never invents a promise: when a target does
    not apply for the policy/priority it is reported not_applicable."""
    now = utcnow()
    paused = t.status == C.ST_WAITING_FOR_TENANT and t.sla_paused_at is not None

    def state(due: datetime | None, met: datetime | None) -> str:
        if met:
            return C.BREACH_MET
        if due is None:
            return C.BREACH_NA
        if paused:
            return C.BREACH_PAUSED
        if now > due:
            return C.BREACH_BREACHED
        if (due - now) <= timedelta(hours=1):
            return C.BREACH_AT_RISK
        return C.BREACH_OK

    fr_state = state(t.first_response_due_at, t.first_response_met_at)
    terminal = t.status in (C.ST_RESOLVED, C.ST_CLOSED, C.ST_WITHDRAWN, C.ST_DRAFT)
    nu_state = C.BREACH_NA if terminal else state(t.next_update_due_at, None)
    res_state = C.BREACH_MET if t.resolved_at else (C.BREACH_NA if terminal else state(t.resolution_target_at, None))

    overall = C.BREACH_OK
    for s in (fr_state, nu_state, res_state):
        if s == C.BREACH_BREACHED:
            overall = C.BREACH_BREACHED
            break
        if s == C.BREACH_AT_RISK:
            overall = C.BREACH_AT_RISK
    if paused:
        overall = C.BREACH_PAUSED
    if terminal and overall not in (C.BREACH_BREACHED,):
        overall = C.BREACH_MET if t.resolved_at else C.BREACH_NA

    if paused:
        msg = "Paused — waiting for your reply"
    elif overall == C.BREACH_BREACHED:
        msg = "SLA breached — escalation available"
    elif t.resolved_at:
        msg = "Resolved"
    elif fr_state in (C.BREACH_OK, C.BREACH_AT_RISK) and not t.first_response_met_at:
        msg = f"First response due {_human(t.first_response_due_at, now)}"
    elif t.next_update_due_at:
        msg = f"Next update due {_human(t.next_update_due_at, now)}"
    else:
        msg = "No active SLA target"

    return {
        "sla_policy": t.sla_policy or C.SLA_POLICY_NAME,
        "first_response_due_at": _iso(t.first_response_due_at),
        "first_response_met_at": _iso(t.first_response_met_at),
        "first_response_state": fr_state,
        "next_update_due_at": _iso(t.next_update_due_at),
        "next_update_state": nu_state,
        "resolution_target_at": _iso(t.resolution_target_at),
        "resolution_state": res_state,
        "paused_at": _iso(t.sla_paused_at),
        "paused": paused,
        "breach_state": overall,
        "breached_at": _iso(t.sla_breached_at),
        "escalation_available": overall == C.BREACH_BREACHED and not t.escalated_at
                                and t.status in C.OPEN_STATUSES,
        "display_message": msg,
    }


def _human(due: datetime | None, now: datetime) -> str:
    if not due:
        return "—"
    delta = due - now
    past = delta.total_seconds() < 0
    mins = abs(int(delta.total_seconds() // 60))
    if mins < 60:
        txt = f"{mins} min"
    elif mins < 60 * 48:
        txt = f"{mins // 60} h"
    else:
        txt = f"{mins // (60 * 24)} d"
    return f"{txt} ago" if past else f"in {txt}"


# ══════════════════════════════════════════════════════════════════════════════
# Audit + conversation
# ══════════════════════════════════════════════════════════════════════════════
async def log_event(
    db: AsyncSession, ticket_id: uuid.UUID, event_type: str, *,
    from_value: str | None = None, to_value: str | None = None,
    reason: str | None = None, actor_user_id: uuid.UUID | None = None,
    actor_type: str = "system", actor_name: str | None = None,
    visibility: str = "tenant_visible", meta: dict | None = None,
) -> SupportTicketEvent:
    ev = SupportTicketEvent(
        ticket_id=ticket_id, event_type=event_type, from_value=from_value,
        to_value=to_value, reason=reason, actor_user_id=actor_user_id,
        actor_type=actor_type, actor_name=actor_name, visibility=visibility,
        meta=meta,
    )
    db.add(ev)
    return ev


async def add_message(
    db: AsyncSession, ticket: SupportTicket, *, kind: str, body: str,
    author_type: str, author_user_id: uuid.UUID | None = None,
    author_name: str | None = None, author_role: str | None = None,
    visibility: str = "tenant_visible", attachments: list[dict] | None = None,
) -> SupportTicketMessage:
    msg = SupportTicketMessage(
        ticket_id=ticket.id, kind=kind, body=body, author_type=author_type,
        author_user_id=author_user_id, author_name=author_name,
        author_role=author_role, visibility=visibility, attachments=attachments,
    )
    db.add(msg)
    return msg


# ══════════════════════════════════════════════════════════════════════════════
# Creation
# ══════════════════════════════════════════════════════════════════════════════
SAFE_RELATED_KEYS = {
    "job_id", "booking_id", "invoice_id", "document_request_id",
    "payment_record_id", "team_member_id", "quote_id", "complaint_id",
}


def sanitize_related_entities(raw: dict | None) -> dict:
    """Store scoped references only — never raw customer data, never arbitrary
    URLs (section 20/21)."""
    if not raw:
        return {}
    out: dict = {}
    for k, v in raw.items():
        if k not in SAFE_RELATED_KEYS or v in (None, ""):
            continue
        try:
            out[k] = str(uuid.UUID(str(v)))
        except (ValueError, TypeError):
            continue
    return out


async def find_similar_open(
    db: AsyncSession, tenant_id: uuid.UUID, category: str, subject: str,
) -> list[dict]:
    rows = (await db.execute(
        select(SupportTicket).where(
            SupportTicket.tenant_id == tenant_id,
            SupportTicket.category == category,
            SupportTicket.status.in_(C.OPEN_STATUSES),
        ).order_by(SupportTicket.created_at.desc()).limit(5)
    )).scalars().all()
    return [{"id": str(r.id), "ticket_number": r.ticket_number, "subject": r.subject,
             "status": r.status, "created_at": _iso(r.created_at)} for r in rows]


async def _active_incident(db: AsyncSession) -> SupportPlatformIncident | None:
    return (await db.execute(
        select(SupportPlatformIncident)
        .where(SupportPlatformIncident.resolved_at.is_(None))
        .order_by(SupportPlatformIncident.started_at.desc()).limit(1)
    )).scalars().first()


async def create_ticket(
    db: AsyncSession, *, tenant_id: uuid.UUID, reporter_user_id: uuid.UUID,
    reporter_name: str | None, reporter_role: str | None,
    category: str, subject: str, description: str, impact: str,
    subcategory: str | None = None, affected_feature: str | None = None,
    vertical_key: str | None = None, started_at: datetime | None = None,
    related_entities: dict | None = None, is_critical_incident: bool = False,
    critical_impact_key: str | None = None, tenant_name: str | None = None,
) -> SupportTicket:
    if category not in C.CATEGORY_KEYS:
        raise SupportError("SUPPORT_INVALID_CATEGORY", f"Unknown support category '{category}'.",
                           "Choose one of the listed categories.")
    if impact not in C.IMPACTS:
        raise SupportError("SUPPORT_INVALID_IMPACT", f"Unknown impact '{impact}'.",
                           "Choose how the problem affects your business.")
    if not (subject or "").strip():
        raise SupportError("SUPPORT_SUBJECT_REQUIRED", "A subject is required.")
    if len((description or "").strip()) < 10:
        raise SupportError("SUPPORT_DESCRIPTION_TOO_SHORT",
                           "Please describe the problem in at least a sentence.",
                           "Include what you expected and what happened instead.")

    incident = await _active_incident(db)
    priority, reasons = C.derive_priority(
        impact, category,
        is_critical_incident=is_critical_incident,
        active_incident=incident is not None,
    )

    cat = C.CATEGORY_MAP[category]
    t = SupportTicket(
        tenant_id=tenant_id, reporter_user_id=reporter_user_id,
        reporter_name=reporter_name, reporter_role=reporter_role,
        category=category, subcategory=subcategory, product_area=cat.get("area"),
        affected_feature=affected_feature, subject=subject.strip()[:300],
        description=description.strip(), started_at=started_at,
        impact=impact, priority=priority, priority_reasons=reasons,
        is_critical_incident=is_critical_incident,
        critical_impact_key=critical_impact_key,
        status=C.ST_SUBMITTED, vertical_key=vertical_key,
        related_entities=sanitize_related_entities(related_entities),
        assigned_team=_route_team(category, is_critical_incident),
        incident_id=incident.id if incident else None,
        created_at=utcnow(),
    )
    apply_sla_targets(t)
    db.add(t)
    await db.flush()

    await add_message(
        db, t, kind=C.MSG_TENANT, body=t.description, author_type="tenant",
        author_user_id=reporter_user_id, author_name=reporter_name,
        author_role=reporter_role,
    )
    await log_event(db, t.id, "created", to_value=C.ST_SUBMITTED,
                    actor_user_id=reporter_user_id, actor_type="tenant",
                    actor_name=reporter_name,
                    meta={"impact": impact, "derived_priority": priority,
                          "priority_reasons": reasons})
    await db.flush()

    ev_key = C.EV_CRITICAL if is_critical_incident else C.EV_SUBMITTED
    await _fire(db, ev_key, t, extra={
        "tenant_name": tenant_name or "",
        "critical_impact": dict(C.CRITICAL_INCIDENT_IMPACTS).get(critical_impact_key or "", ""),
        "first_response_due": _iso(t.first_response_due_at) or "",
    })
    return t


def _route_team(category: str, critical: bool) -> str:
    if critical:
        return "ServiceOS Incident Response"
    return {
        "account_access": "ServiceOS Account Support",
        "security": "ServiceOS Security",
        "onboarding": "ServiceOS Onboarding",
        "profile_documents": "ServiceOS Verification",
        "finance_credits": "ServiceOS Finance Support",
        "direct_payments": "ServiceOS Finance Support",
        "integrations": "ServiceOS Platform Engineering",
        "technical": "ServiceOS Platform Engineering",
    }.get(category, "ServiceOS Provider Support")


TENANT_FACING_EVENTS = {
    C.EV_SUBMITTED, C.EV_REPLIED, C.EV_INFO_REQUESTED, C.EV_PRIORITY_CHANGED,
    C.EV_RESOLVED, C.EV_SLA_BREACHED, C.EV_CRITICAL, C.EV_ANNOUNCEMENT,
}
ADMIN_FACING_EVENTS = {
    C.EV_SUBMITTED, C.EV_REOPENED, C.EV_SLA_BREACHED, C.EV_CRITICAL,
}
_ADMIN_NOTIFY_ROLES = ("super_admin", "admin_operations")


async def _recipients(db: AsyncSession, event_key: str, t: SupportTicket) -> list[dict]:
    """fire_event() only creates outbox/in-app rows for EXPLICIT recipients
    (it has no recipient resolver of its own -- see notification_service.py:81),
    so every support event resolves its own audience here. Without this the
    event row is written and nothing is ever delivered."""
    from app.engines.auth.models import User

    out: list[dict] = []
    seen: set[str] = set()

    def add(uid, rtype: str) -> None:
        if uid and str(uid) not in seen:
            seen.add(str(uid))
            out.append({"user_id": str(uid), "recipient_type": rtype})

    if event_key in TENANT_FACING_EVENTS:
        add(t.reporter_user_id, "provider")
        owners = (await db.execute(
            select(User.id).where(User.tenant_id == t.tenant_id,
                                  User.role == "tenant_owner",
                                  User.is_active.is_(True))
        )).scalars().all()
        for uid in owners:
            add(uid, "provider")

    if event_key in ADMIN_FACING_EVENTS:
        admins = (await db.execute(
            select(User.id).where(User.role.in_(_ADMIN_NOTIFY_ROLES),
                                  User.is_active.is_(True)).limit(20)
        )).scalars().all()
        for uid in admins:
            add(uid, "admin")
    return out


async def _fire(db: AsyncSession, event_key: str, t: SupportTicket, extra: dict | None = None) -> None:
    payload = {
        "ticket_id": str(t.id), "ticket_number": t.ticket_number,
        "subject": t.subject, "status": t.status, "priority": t.priority,
        "category": t.category,
        "action_url": C.DEEP_LINK.format(ticket_id=t.id),
        **(extra or {}),
    }
    await _notif.fire_event(
        db, event_key, payload, tenant_id=t.tenant_id,
        source_record_type="support_ticket", source_record_id=t.id,
        recipients=await _recipients(db, event_key, t),
    )


# ══════════════════════════════════════════════════════════════════════════════
# Critical incident rate limit (section 17)
# ══════════════════════════════════════════════════════════════════════════════
async def check_critical_rate_limit(db: AsyncSession, tenant_id: uuid.UUID) -> None:
    since = utcnow() - timedelta(hours=C.CRITICAL_INCIDENT_WINDOW_HOURS)
    n = (await db.execute(
        select(func.count()).select_from(SupportTicket).where(
            SupportTicket.tenant_id == tenant_id,
            SupportTicket.is_critical_incident.is_(True),
            SupportTicket.created_at >= since,
        )
    )).scalar() or 0
    if n >= C.CRITICAL_INCIDENT_MAX_PER_WINDOW:
        raise SupportError(
            "SUPPORT_CRITICAL_RATE_LIMITED",
            f"You have already reported {n} critical incidents in the last "
            f"{C.CRITICAL_INCIDENT_WINDOW_HOURS} hours.",
            "Reply on the existing critical incident instead, or raise a normal "
            "support request if this is not an outage.",
            status_code=429,
        )


# ══════════════════════════════════════════════════════════════════════════════
# Tenant replies
# ══════════════════════════════════════════════════════════════════════════════
async def tenant_reply(
    db: AsyncSession, t: SupportTicket, *, body: str, user_id: uuid.UUID,
    user_name: str | None, user_role: str | None,
    attachment_ids: list[uuid.UUID] | None = None,
) -> SupportTicketMessage:
    if t.status not in C.OPEN_STATUSES:
        raise SupportError("SUPPORT_TICKET_NOT_OPEN",
                           "This request is no longer open for replies.",
                           "Reopen the request if you still need help.", status_code=409)
    if not (body or "").strip():
        raise SupportError("SUPPORT_REPLY_EMPTY", "Write a reply before sending.")

    attachments = []
    if attachment_ids:
        rows = (await db.execute(
            select(SupportTicketAttachment).where(
                SupportTicketAttachment.ticket_id == t.id,
                SupportTicketAttachment.id.in_(attachment_ids),
            )
        )).scalars().all()
        attachments = [{"id": str(a.id), "file_name": a.file_name,
                        "mime_type": a.mime_type, "size_bytes": a.size_bytes} for a in rows]

    msg = await add_message(
        db, t, kind=C.MSG_TENANT, body=body.strip(), author_type="tenant",
        author_user_id=user_id, author_name=user_name, author_role=user_role,
        attachments=attachments or None,
    )
    t.last_tenant_reply_at = utcnow()

    # A tenant reply to waiting_for_tenant returns the case to ServiceOS
    # handling and un-pauses the SLA clock (section 11/12).
    if t.status == C.ST_WAITING_FOR_TENANT:
        prev = t.status
        if t.sla_paused_at:
            t.sla_paused_seconds = (t.sla_paused_seconds or 0) + int((utcnow() - t.sla_paused_at).total_seconds())
            t.sla_paused_at = None
        t.status = C.ST_WAITING_FOR_SERVICEOS
        apply_sla_targets(t)
        await log_event(db, t.id, "status_changed", from_value=prev, to_value=t.status,
                        reason="Tenant provided the requested information",
                        actor_user_id=user_id, actor_type="tenant", actor_name=user_name)
    await db.flush()
    return msg


async def tenant_reopen(
    db: AsyncSession, t: SupportTicket, *, reason: str, user_id: uuid.UUID,
    user_name: str | None,
) -> SupportTicket:
    if t.status not in (C.ST_RESOLVED, C.ST_CLOSED):
        raise SupportError("SUPPORT_REOPEN_NOT_ALLOWED",
                           "Only a resolved or closed request can be reopened.",
                           status_code=409)
    if t.reopen_deadline_at and utcnow() > t.reopen_deadline_at:
        raise SupportError("SUPPORT_REOPEN_WINDOW_EXPIRED",
                           f"The {C.REOPEN_WINDOW_DAYS}-day reopen window for this "
                           "request has closed.",
                           "Create a new support request referencing this ticket number.",
                           status_code=409)
    prev = t.status
    t.status = C.ST_REOPENED
    t.reopen_count = (t.reopen_count or 0) + 1
    t.resolved_at = None
    t.first_response_met_at = None
    t.created_at = t.created_at or utcnow()
    apply_sla_targets(t)
    await add_message(db, t, kind=C.MSG_TENANT, body=reason.strip() or "Reopened.",
                      author_type="tenant", author_user_id=user_id, author_name=user_name)
    await log_event(db, t.id, "reopened", from_value=prev, to_value=t.status,
                    reason=reason, actor_user_id=user_id, actor_type="tenant",
                    actor_name=user_name)
    await db.flush()
    await _fire(db, C.EV_REOPENED, t)
    return t


async def tenant_escalate(db: AsyncSession, t: SupportTicket, *, user_id: uuid.UUID,
                          user_name: str | None) -> SupportTicket:
    sla = sla_projection(t)
    if not sla["escalation_available"]:
        raise SupportError("SUPPORT_ESCALATION_NOT_AVAILABLE",
                           "Escalation becomes available only after an SLA breach.",
                           status_code=409)
    t.escalated_at = utcnow()
    t.sla_breached_at = t.sla_breached_at or utcnow()
    await log_event(db, t.id, "escalated", to_value="escalated",
                    reason="Tenant escalated after SLA breach",
                    actor_user_id=user_id, actor_type="tenant", actor_name=user_name)
    await db.flush()
    await _fire(db, C.EV_SLA_BREACHED, t, extra={"sla_kind": "first response / next update"})
    return t


# ══════════════════════════════════════════════════════════════════════════════
# Admin operations
# ══════════════════════════════════════════════════════════════════════════════
async def admin_transition(
    db: AsyncSession, t: SupportTicket, *, to_status: str, actor_user_id: uuid.UUID,
    actor_name: str | None, reason: str | None = None,
    resolution_summary: str | None = None,
) -> SupportTicket:
    allowed = C.ADMIN_TRANSITIONS.get(t.status, [])
    if to_status not in allowed:
        raise SupportError("SUPPORT_INVALID_TRANSITION",
                           f"Cannot move a {t.status} request to {to_status}.",
                           f"Allowed: {', '.join(allowed) or 'none'}", status_code=409)
    prev = t.status
    t.status = to_status

    if to_status == C.ST_WAITING_FOR_TENANT:
        t.sla_paused_at = utcnow()
    elif t.sla_paused_at:
        t.sla_paused_seconds = (t.sla_paused_seconds or 0) + int((utcnow() - t.sla_paused_at).total_seconds())
        t.sla_paused_at = None

    if to_status == C.ST_RESOLVED:
        t.resolved_at = utcnow()
        t.reopen_deadline_at = t.resolved_at + timedelta(days=C.REOPEN_WINDOW_DAYS)
        t.resolution_summary = resolution_summary or t.resolution_summary
        t.next_update_due_at = None
        if t.resolution_summary:
            await add_message(db, t, kind=C.MSG_RESOLUTION, body=t.resolution_summary,
                              author_type="serviceos", author_user_id=actor_user_id,
                              author_name=actor_name)
    elif to_status == C.ST_CLOSED:
        t.closed_at = utcnow()
    else:
        apply_sla_targets(t)

    await log_event(db, t.id, "status_changed", from_value=prev, to_value=to_status,
                    reason=reason, actor_user_id=actor_user_id, actor_type="serviceos",
                    actor_name=actor_name)
    t.tenant_unread_count = (t.tenant_unread_count or 0) + 1
    await db.flush()

    if to_status == C.ST_RESOLVED:
        await _fire(db, C.EV_RESOLVED, t, extra={"resolution_summary": t.resolution_summary or ""})
    elif to_status == C.ST_WAITING_FOR_TENANT:
        await _fire(db, C.EV_INFO_REQUESTED, t)
    return t


async def admin_assign(db: AsyncSession, t: SupportTicket, *, team: str | None,
                       assignee_id: uuid.UUID | None, assignee_name: str | None,
                       actor_user_id: uuid.UUID, actor_name: str | None) -> SupportTicket:
    t.assigned_team = team or t.assigned_team
    t.assigned_admin_user_id = assignee_id
    t.assigned_admin_name = assignee_name
    if t.status in (C.ST_SUBMITTED, C.ST_TRIAGED, C.ST_REOPENED):
        prev = t.status
        t.status = C.ST_ASSIGNED
        await log_event(db, t.id, "status_changed", from_value=prev, to_value=t.status,
                        actor_user_id=actor_user_id, actor_type="serviceos", actor_name=actor_name)
    await log_event(db, t.id, "assigned", to_value=t.assigned_team,
                    reason=assignee_name, actor_user_id=actor_user_id,
                    actor_type="serviceos", actor_name=actor_name)
    await db.flush()
    return t


async def admin_set_priority(db: AsyncSession, t: SupportTicket, *, priority: str,
                             reason: str, actor_user_id: uuid.UUID,
                             actor_name: str | None) -> SupportTicket:
    if priority not in C.PRIORITIES:
        raise SupportError("SUPPORT_INVALID_PRIORITY", f"Unknown priority '{priority}'.")
    if not (reason or "").strip():
        raise SupportError("SUPPORT_PRIORITY_REASON_REQUIRED",
                           "A reason is required to override the derived priority.")
    prev = t.priority
    t.priority = priority
    t.priority_reasons = (t.priority_reasons or []) + [f"admin override: {reason}"]
    apply_sla_targets(t)
    await log_event(db, t.id, "priority_changed", from_value=prev, to_value=priority,
                    reason=reason, actor_user_id=actor_user_id, actor_type="serviceos",
                    actor_name=actor_name)
    await db.flush()
    await _fire(db, C.EV_PRIORITY_CHANGED, t, extra={"reason": reason})
    return t


async def admin_reply(db: AsyncSession, t: SupportTicket, *, body: str, internal: bool,
                      request_info: bool, actor_user_id: uuid.UUID,
                      actor_name: str | None) -> SupportTicketMessage:
    if not (body or "").strip():
        raise SupportError("SUPPORT_REPLY_EMPTY", "Write a message before sending.")
    kind = (C.MSG_INTERNAL_NOTE if internal
            else C.MSG_INFO_REQUEST if request_info else C.MSG_SUPPORT)
    msg = await add_message(
        db, t, kind=kind, body=body.strip(), author_type="serviceos",
        author_user_id=actor_user_id, author_name=actor_name,
        visibility="internal" if internal else "tenant_visible",
    )
    if not internal:
        t.last_support_reply_at = utcnow()
        t.tenant_unread_count = (t.tenant_unread_count or 0) + 1
        if not t.first_response_met_at:
            t.first_response_met_at = utcnow()
        fr, nu, _ = C.SLA_TARGETS.get(t.priority, C.SLA_TARGETS[C.PRIORITY_NORMAL])
        t.next_update_due_at = utcnow() + timedelta(hours=nu)
        if request_info and t.status in C.OPEN_STATUSES and t.status != C.ST_WAITING_FOR_TENANT:
            prev = t.status
            t.status = C.ST_WAITING_FOR_TENANT
            t.sla_paused_at = utcnow()
            await log_event(db, t.id, "status_changed", from_value=prev, to_value=t.status,
                            reason="ServiceOS requested more information",
                            actor_user_id=actor_user_id, actor_type="serviceos",
                            actor_name=actor_name)
        await db.flush()
        await _fire(db, C.EV_INFO_REQUESTED if request_info else C.EV_REPLIED, t)
    else:
        await log_event(db, t.id, "internal_note_added", visibility="internal",
                        actor_user_id=actor_user_id, actor_type="serviceos",
                        actor_name=actor_name)
        await db.flush()
    return msg


# ══════════════════════════════════════════════════════════════════════════════
# Projections
# ══════════════════════════════════════════════════════════════════════════════
def ticket_row(t: SupportTicket) -> dict:
    sla = sla_projection(t)
    return {
        "id": str(t.id),
        "ticket_number": t.ticket_number,
        "subject": t.subject,
        "category": t.category,
        "category_label": C.CATEGORY_MAP.get(t.category, {}).get("label", t.category),
        "subcategory": t.subcategory,
        "priority": t.priority,
        "status": t.status,
        "status_label": C.STATUS_LABELS.get(t.status, t.status),
        "impact": t.impact,
        "impact_label": C.IMPACT_LABELS.get(t.impact, t.impact),
        "reporter_name": t.reporter_name,
        "reporter_role": t.reporter_role,
        "assigned_team": t.assigned_team,
        "assigned_admin_name": t.assigned_admin_name,
        "is_critical_incident": t.is_critical_incident,
        "sla_display": sla["display_message"],
        "sla_breach_state": sla["breach_state"],
        "unread_updates": t.tenant_unread_count or 0,
        "created_at": _iso(t.created_at),
        "updated_at": _iso(t.updated_at),
    }


def tenant_allowed_actions(t: SupportTicket, *, can_submit: bool) -> dict:
    open_ = t.status in C.OPEN_STATUSES
    sla = sla_projection(t)
    in_reopen_window = bool(t.reopen_deadline_at and utcnow() <= t.reopen_deadline_at)
    return {
        "can_reply": can_submit and open_,
        "can_attach": can_submit and open_,
        "can_provide_information": can_submit and t.status == C.ST_WAITING_FOR_TENANT,
        "can_confirm_resolution": can_submit and t.status == C.ST_RESOLVED,
        "can_reopen": can_submit and t.status in (C.ST_RESOLVED, C.ST_CLOSED) and in_reopen_window,
        "can_withdraw_draft": can_submit and t.status == C.ST_DRAFT,
        "can_escalate": can_submit and sla["escalation_available"],
        "reopen_deadline_at": _iso(t.reopen_deadline_at),
    }


async def ticket_detail(
    db: AsyncSession, t: SupportTicket, *, for_admin: bool, can_submit: bool = True,
) -> dict:
    q = select(SupportTicketMessage).where(SupportTicketMessage.ticket_id == t.id)
    if not for_admin:
        # Internal admin notes must NEVER reach a tenant API (section 13/20).
        q = q.where(SupportTicketMessage.visibility == "tenant_visible",
                    SupportTicketMessage.kind.in_(C.TENANT_VISIBLE_MESSAGE_KINDS))
    msgs = (await db.execute(q.order_by(SupportTicketMessage.created_at.asc()))).scalars().all()

    eq = select(SupportTicketEvent).where(SupportTicketEvent.ticket_id == t.id)
    if not for_admin:
        eq = eq.where(SupportTicketEvent.visibility == "tenant_visible")
    events = (await db.execute(eq.order_by(SupportTicketEvent.created_at.asc()))).scalars().all()

    aq = select(SupportTicketAttachment).where(SupportTicketAttachment.ticket_id == t.id)
    if not for_admin:
        aq = aq.where(SupportTicketAttachment.visibility == "tenant_visible")
    atts = (await db.execute(aq.order_by(SupportTicketAttachment.created_at.asc()))).scalars().all()

    detail = ticket_row(t) | {
        "description": t.description,
        "product_area": t.product_area,
        "affected_feature": t.affected_feature,
        "started_at": _iso(t.started_at),
        "workspace": str(t.tenant_id),
        "vertical_key": t.vertical_key,
        "related_entities": t.related_entities or {},
        "resolution_summary": t.resolution_summary,
        "resolved_at": _iso(t.resolved_at),
        "closed_at": _iso(t.closed_at),
        "reopen_count": t.reopen_count or 0,
        "sla": sla_projection(t),
        "conversation": [{
            "id": str(m.id), "kind": m.kind, "author_name": m.author_name or (
                "ServiceOS Support" if m.author_type == "serviceos" else "System"),
            "author_type": m.author_type, "author_role": m.author_role,
            "body": m.body, "visibility": m.visibility,
            "attachments": m.attachments or [],
            "created_at": _iso(m.created_at),
        } for m in msgs],
        "status_history": [{
            "id": str(e.id), "event_type": e.event_type, "from": e.from_value,
            "to": e.to_value, "reason": e.reason, "actor_type": e.actor_type,
            "actor_name": e.actor_name, "created_at": _iso(e.created_at),
            **({"meta": e.meta} if for_admin else {}),
        } for e in events],
        "attachments": [{
            "id": str(a.id), "media_asset_id": str(a.media_asset_id),
            "file_name": a.file_name, "mime_type": a.mime_type,
            "size_bytes": a.size_bytes, "uploaded_by_type": a.uploaded_by_type,
            "created_at": _iso(a.created_at),
        } for a in atts],
        "attachment_privacy_warning": C.ATTACHMENT_PRIVACY_WARNING,
    }
    if for_admin:
        detail["priority_reasons"] = t.priority_reasons or []
        detail["allowed_transitions"] = C.ADMIN_TRANSITIONS.get(t.status, [])
        detail["reporter_user_id"] = str(t.reporter_user_id)
        detail["tenant_id"] = str(t.tenant_id)
    else:
        detail["allowed_actions"] = tenant_allowed_actions(t, can_submit=can_submit)
    return detail


async def list_tickets(
    db: AsyncSession, *, tenant_id: uuid.UUID | None = None, search: str | None = None,
    category: str | None = None, status: str | None = None, priority: str | None = None,
    submitted_by: uuid.UUID | None = None, created_from: datetime | None = None,
    updated_from: datetime | None = None, limit: int = 100, offset: int = 0,
) -> tuple[list[SupportTicket], int]:
    conds = []
    if tenant_id:
        conds.append(SupportTicket.tenant_id == tenant_id)
    if category:
        conds.append(SupportTicket.category == category)
    if status == "open":
        conds.append(SupportTicket.status.in_(C.OPEN_STATUSES))
    elif status:
        conds.append(SupportTicket.status == status)
    if priority:
        conds.append(SupportTicket.priority == priority)
    if submitted_by:
        conds.append(SupportTicket.reporter_user_id == submitted_by)
    if created_from:
        conds.append(SupportTicket.created_at >= created_from)
    if updated_from:
        conds.append(SupportTicket.updated_at >= updated_from)
    if search:
        like = f"%{search.lower()}%"
        conds.append(or_(func.lower(SupportTicket.subject).like(like),
                         func.lower(SupportTicket.ticket_number).like(like),
                         func.lower(SupportTicket.description).like(like)))
    where = and_(*conds) if conds else None
    q = select(SupportTicket)
    cq = select(func.count()).select_from(SupportTicket)
    if where is not None:
        q, cq = q.where(where), cq.where(where)
    total = (await db.execute(cq)).scalar() or 0
    rows = (await db.execute(
        q.order_by(SupportTicket.created_at.desc()).limit(limit).offset(offset)
    )).scalars().all()
    return rows, total


async def summary(db: AsyncSession, tenant_id: uuid.UUID) -> dict:
    rows = (await db.execute(
        select(SupportTicket.status, func.count()).where(SupportTicket.tenant_id == tenant_id)
        .group_by(SupportTicket.status)
    )).all()
    by = {s: n for s, n in rows}
    return {
        "open": sum(n for s, n in by.items() if s in C.OPEN_STATUSES),
        "awaiting_your_reply": by.get(C.ST_WAITING_FOR_TENANT, 0),
        "resolved": by.get(C.ST_RESOLVED, 0) + by.get(C.ST_CLOSED, 0),
        "total": sum(by.values()),
        "by_status": by,
    }


# ══════════════════════════════════════════════════════════════════════════════
# Service status (section 4) — never green without evidence
# ══════════════════════════════════════════════════════════════════════════════
async def service_status(db: AsyncSession) -> dict:
    incidents = (await db.execute(
        select(SupportPlatformIncident)
        .where(SupportPlatformIncident.resolved_at.is_(None))
        .order_by(SupportPlatformIncident.started_at.desc())
    )).scalars().all()

    hb = (await db.execute(
        select(SupportStatusHeartbeat).order_by(SupportStatusHeartbeat.checked_at.desc()).limit(20)
    )).scalars().all()
    last_checked = hb[0].checked_at if hb else None
    fresh = bool(last_checked and (utcnow() - last_checked) <= timedelta(minutes=HEARTBEAT_STALE_MINUTES))

    affected: list[str] = []
    for i in incidents:
        affected.extend(i.components or [])
    unhealthy = [h.component for h in hb if not h.is_healthy]
    affected.extend(unhealthy)
    affected = sorted(set(affected))

    if incidents:
        worst = "minor"
        for i in incidents:
            if i.severity == "major":
                worst = "major"
                break
            if i.severity == "minor":
                worst = "minor"
            elif worst != "minor":
                worst = i.severity
        state = C.INCIDENT_SEVERITY_TO_STATUS.get(worst, C.STATUS_DEGRADED)
        message = incidents[0].title
    elif not fresh:
        # No live evidence -> refuse to claim operational (section 4/26.16).
        state = C.STATUS_UNAVAILABLE
        message = ("We cannot confirm platform status right now — the status "
                   "monitor has not reported recently.")
    elif unhealthy:
        state = C.STATUS_DEGRADED
        message = "Some platform components are reporting degraded health."
    else:
        state = C.STATUS_OPERATIONAL
        message = "All ServiceOS platform components are operational."

    return {
        "state": state,
        "message": message,
        "last_checked_at": _iso(last_checked),
        "evidence_fresh": fresh,
        "affected_components": affected,
        "active_incident_count": len(incidents),
        "incidents": [{
            "id": str(i.id), "reference": i.reference, "title": i.title,
            "severity": i.severity, "status": i.status,
            "components": i.components or [],
            "started_at": _iso(i.started_at),
        } for i in incidents],
        "status_page_href": "/help-support?tab=announcements",
    }


async def record_heartbeat(db: AsyncSession, component: str, is_healthy: bool,
                           detail: str | None = None) -> None:
    db.add(SupportStatusHeartbeat(component=component, is_healthy=is_healthy,
                                  detail=detail, checked_at=utcnow()))
    await db.flush()


# ══════════════════════════════════════════════════════════════════════════════
# Knowledge base (section 15)
# ══════════════════════════════════════════════════════════════════════════════
def _article(a: SupportKnowledgeArticle, *, with_body: bool = False) -> dict:
    d = {
        "id": str(a.id), "slug": a.slug, "title": a.title, "summary": a.summary,
        "product_area": a.product_area, "keywords": a.keywords or [],
        "is_featured": a.is_featured, "policy_version": a.policy_version,
        "helpful_count": a.helpful_count, "not_helpful_count": a.not_helpful_count,
        "updated_at": _iso(a.updated_at),
    }
    if with_body:
        d["body"] = a.body
    return d


async def knowledge(
    db: AsyncSession, *, search: str | None = None, area: str | None = None,
    vertical_key: str | None = None, role: str | None = None, limit: int = 60,
) -> dict:
    q = select(SupportKnowledgeArticle).where(SupportKnowledgeArticle.is_published.is_(True))
    if area:
        q = q.where(SupportKnowledgeArticle.product_area == area)
    if search:
        like = f"%{search.lower()}%"
        q = q.where(or_(
            func.lower(SupportKnowledgeArticle.title).like(like),
            func.lower(SupportKnowledgeArticle.summary).like(like),
            func.lower(SupportKnowledgeArticle.body).like(like),
            SupportKnowledgeArticle.keywords.cast(Text).ilike(like),
        ))
    rows = (await db.execute(
        q.order_by(SupportKnowledgeArticle.is_featured.desc(),
                   SupportKnowledgeArticle.updated_at.desc()).limit(limit)
    )).scalars().all()

    def relevant(a: SupportKnowledgeArticle) -> bool:
        if vertical_key and a.vertical_keys and vertical_key not in a.vertical_keys:
            return False
        if role and a.role_keys and role not in a.role_keys:
            return False
        return True

    rows = [a for a in rows if relevant(a)]

    counts = dict((await db.execute(
        select(SupportKnowledgeArticle.product_area, func.count())
        .where(SupportKnowledgeArticle.is_published.is_(True))
        .group_by(SupportKnowledgeArticle.product_area)
    )).all())

    categories = [{
        **pa,
        "article_count": counts.get(pa["key"], 0),
        "has_content": counts.get(pa["key"], 0) > 0,
    } for pa in C.PRODUCT_AREAS]

    return {
        "articles": [_article(a, with_body=True) for a in rows],
        "featured": [_article(a) for a in rows if a.is_featured][:4],
        "recently_updated": [_article(a) for a in sorted(
            rows, key=lambda x: x.updated_at or utcnow(), reverse=True)][:5],
        "categories": categories,
        "total_published": sum(counts.values()),
        "search": search,
        "area": area,
    }


async def article_feedback(db: AsyncSession, article_id: uuid.UUID, *, is_helpful: bool,
                           tenant_id: uuid.UUID | None, user_id: uuid.UUID | None,
                           comment: str | None = None) -> None:
    a = (await db.execute(
        select(SupportKnowledgeArticle).where(SupportKnowledgeArticle.id == article_id,
                                              SupportKnowledgeArticle.is_published.is_(True))
    )).scalars().first()
    if not a:
        raise SupportError("SUPPORT_ARTICLE_NOT_FOUND", "That help article is not available.",
                           status_code=404)
    db.add(SupportArticleFeedback(article_id=article_id, tenant_id=tenant_id,
                                  user_id=user_id, is_helpful=is_helpful, comment=comment))
    if is_helpful:
        a.helpful_count = (a.helpful_count or 0) + 1
    else:
        a.not_helpful_count = (a.not_helpful_count or 0) + 1
    await db.flush()


# ══════════════════════════════════════════════════════════════════════════════
# Announcements (section 16)
# ══════════════════════════════════════════════════════════════════════════════
async def announcements(
    db: AsyncSession, *, tenant_id: uuid.UUID, user_id: uuid.UUID,
    vertical_key: str | None = None, role: str | None = None,
    include_expired: bool = True,
) -> dict:
    now = utcnow()
    q = select(SupportAnnouncement).where(SupportAnnouncement.is_published.is_(True))
    q = q.where(or_(SupportAnnouncement.effective_from.is_(None),
                    SupportAnnouncement.effective_from <= now))
    rows = (await db.execute(q.order_by(SupportAnnouncement.effective_from.desc().nullslast()))).scalars().all()

    acks = {r.announcement_id for r in (await db.execute(
        select(SupportAnnouncementAck).where(SupportAnnouncementAck.user_id == user_id)
    )).scalars().all()}

    out = []
    for a in rows:
        if a.tenant_ids and str(tenant_id) not in [str(x) for x in a.tenant_ids]:
            continue
        # Historical announcements stay readable even if the vertical was later
        # disabled (section 16) -- vertical scoping filters, never deletes.
        if a.vertical_keys and vertical_key and vertical_key not in a.vertical_keys:
            continue
        if a.role_keys and role and role not in a.role_keys:
            continue
        expired = bool(a.expires_at and a.expires_at < now)
        if expired and not include_expired:
            continue
        out.append({
            "id": str(a.id), "announcement_type": a.announcement_type,
            "title": a.title, "body": a.body,
            "requires_acknowledgement": a.requires_acknowledgement,
            "acknowledged": a.id in acks,
            "effective_from": _iso(a.effective_from),
            "expires_at": _iso(a.expires_at),
            "is_expired": expired,
            "vertical_keys": a.vertical_keys or [],
        })
    return {
        "items": out,
        "unacknowledged_required": sum(
            1 for x in out if x["requires_acknowledgement"] and not x["acknowledged"]),
    }


async def acknowledge_announcement(db: AsyncSession, announcement_id: uuid.UUID, *,
                                   tenant_id: uuid.UUID, user_id: uuid.UUID) -> None:
    a = (await db.execute(select(SupportAnnouncement).where(
        SupportAnnouncement.id == announcement_id,
        SupportAnnouncement.is_published.is_(True)))).scalars().first()
    if not a:
        raise SupportError("SUPPORT_ANNOUNCEMENT_NOT_FOUND",
                           "That announcement is not available.", status_code=404)
    existing = (await db.execute(select(SupportAnnouncementAck).where(
        SupportAnnouncementAck.announcement_id == announcement_id,
        SupportAnnouncementAck.user_id == user_id))).scalars().first()
    if existing:
        return
    db.add(SupportAnnouncementAck(announcement_id=announcement_id, tenant_id=tenant_id,
                                  user_id=user_id))
    await db.flush()
