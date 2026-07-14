"""Sprint 27 — Admin Notification Outbox + Chat + Audit APIs."""
from __future__ import annotations
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Request, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import get_current_user, require_super_admin, require_platform_staff, UserContext
from app.dependencies.db import get_db
from app.schemas.base import ok
from app.engines.platform_notifications.notification_service import NotificationService
from app.engines.platform_notifications.chat_service import ChatThreadService, ChatMessageService
from app.engines.platform_notifications.audit_service import PlatformAuditLogService
from app.engines.platform_notifications.constants import RECIP_ADMIN
from app.engines.platform_notifications.models import NotificationEvent
from sqlalchemy import select

admin_notif_router = APIRouter(
    prefix="/v1/admin/notifications",
    tags=["Admin Notifications"],
)
admin_outbox_router = APIRouter(
    prefix="/v1/admin/notification-outbox",
    tags=["Admin Notification Outbox"],
)
admin_notif_events_router = APIRouter(
    prefix="/v1/admin/notification-events",
    tags=["Admin Notification Events"],
)
admin_notif_templates_router = APIRouter(
    prefix="/v1/admin/notification-templates",
    tags=["Notification Templates"],
)
admin_chat_router = APIRouter(
    prefix="/v1/admin/chat",
    tags=["Admin Chat"],
)
admin_audit_router = APIRouter(
    prefix="/v1/admin/audit-logs",
    tags=["Admin Audit Logs"],
)

_notif_svc  = NotificationService()
_thread_svc = ChatThreadService()
_msg_svc    = ChatMessageService(_thread_svc)
_audit_svc  = PlatformAuditLogService()


def _rid(r: Request) -> str:
    return getattr(r.state, "request_id", "—")


# ═══════════════════════════════════════════════════════════════════════════════
# ADMIN IN-APP NOTIFICATIONS
# ═══════════════════════════════════════════════════════════════════════════════

@admin_notif_router.get("", summary="List admin in-app notifications")
async def admin_list_notifications(
    r: Request,
    read_status: Optional[str] = Query(None),
    limit: int = Query(30, ge=1, le=100),
    offset: int = Query(0, ge=0),
    u: UserContext = Depends(require_platform_staff),
    db: AsyncSession = Depends(get_db),
):
    result = await _notif_svc.get_user_notifications(
        db, uuid.UUID(u.user_id), read_status=read_status, limit=limit, offset=offset,
    )
    return ok(result, _rid(r), "admin.notifications.list")


@admin_notif_router.get("/unread-count", summary="Admin unread notification count")
async def admin_unread_count(
    r: Request,
    u: UserContext = Depends(require_platform_staff),
    db: AsyncSession = Depends(get_db),
):
    count = await _notif_svc.get_unread_count(db, uuid.UUID(u.user_id))
    return ok({"unread_count": count}, _rid(r), "admin.notifications.unread_count")


@admin_notif_router.post("/{notification_id}/read", summary="Mark admin notification read")
async def admin_mark_read(
    notification_id: uuid.UUID,
    r: Request,
    u: UserContext = Depends(require_platform_staff),
    db: AsyncSession = Depends(get_db),
):
    notif = await _notif_svc.mark_notification_read(db, uuid.UUID(u.user_id), notification_id)
    return ok(notif.to_dict(), _rid(r), "admin.notifications.read")


@admin_notif_router.post("/mark-all-read", summary="Mark all admin notifications read")
async def admin_mark_all_read(
    r: Request,
    u: UserContext = Depends(require_platform_staff),
    db: AsyncSession = Depends(get_db),
):
    count = await _notif_svc.mark_all_read(db, uuid.UUID(u.user_id))
    return ok({"marked_read": count}, _rid(r), "admin.notifications.mark_all_read")


# ── MODULE-L5-11: admin notification settings (preferences) ────────────────────
# The admin side had no notification settings page at all — only providers could
# manage which events/channels they receive. These mirror the provider
# preference endpoints, scoped to the logged-in admin's own user.
@admin_notif_router.get("/preferences", summary="Get my (admin) notification preferences")
async def admin_get_prefs(
    r: Request,
    u: UserContext = Depends(require_platform_staff),
    db: AsyncSession = Depends(get_db),
):
    prefs = await _notif_svc.get_preferences(db, uuid.UUID(u.user_id))
    return ok([p.to_dict() for p in prefs], _rid(r), "admin.notifications.preferences")


class AdminPrefIn(BaseModel):
    event_key: str
    channel: str
    is_enabled: bool


@admin_notif_router.put("/preferences", summary="Update my (admin) notification preference")
async def admin_update_pref(
    body: AdminPrefIn,
    r: Request,
    u: UserContext = Depends(require_platform_staff),
    db: AsyncSession = Depends(get_db),
):
    pref = await _notif_svc.update_preference(
        db, uuid.UUID(u.user_id),
        uuid.UUID(str(u.tenant_id)) if getattr(u, "tenant_id", None) else None,
        body.event_key, body.channel, body.is_enabled,
    )
    return ok(pref.to_dict(), _rid(r), "admin.notifications.preferences.update")


# ═══════════════════════════════════════════════════════════════════════════════
# ADMIN NOTIFICATION EVENTS
# ═══════════════════════════════════════════════════════════════════════════════

@admin_notif_events_router.get("", summary="List all notification events")
async def admin_list_events(
    r: Request,
    event_key: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    tenant_id: Optional[uuid.UUID] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    u: UserContext = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import func as sqlfunc
    q = select(NotificationEvent)
    if event_key:
        q = q.where(NotificationEvent.event_key == event_key)
    if status:
        q = q.where(NotificationEvent.status == status)
    if tenant_id:
        q = q.where(NotificationEvent.tenant_id == tenant_id)
    total_r = await db.execute(select(sqlfunc.count()).select_from(q.subquery()))
    total = total_r.scalar_one()
    res = await db.execute(q.order_by(NotificationEvent.created_at.desc()).limit(limit).offset(offset))
    items = res.scalars().all()
    return ok({"items": [e.to_dict() for e in items], "total": total}, _rid(r), "admin.notification_events.list")


# ═══════════════════════════════════════════════════════════════════════════════
# ADMIN NOTIFICATION OUTBOX
# ═══════════════════════════════════════════════════════════════════════════════

@admin_outbox_router.get("", summary="List notification outbox records")
async def admin_list_outbox(
    r: Request,
    delivery_status: Optional[str] = Query(None),
    channel: Optional[str] = Query(None),
    recipient_type: Optional[str] = Query(None),
    tenant_id: Optional[uuid.UUID] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    u: UserContext = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await _notif_svc.list_outbox(
        db, delivery_status=delivery_status, channel=channel,
        recipient_type=recipient_type, tenant_id=tenant_id,
        limit=limit, offset=offset,
    )
    return ok(result, _rid(r), "admin.notification_outbox.list")


@admin_outbox_router.get("/{outbox_id}", summary="Get outbox record details")
async def admin_get_outbox(
    outbox_id: uuid.UUID,
    r: Request,
    u: UserContext = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    outbox = await _notif_svc.get_outbox_record(db, outbox_id)
    return ok(outbox.to_dict(), _rid(r), "admin.notification_outbox.get")


@admin_outbox_router.post("/{outbox_id}/retry", summary="Retry a failed outbox record")
async def admin_retry_outbox(
    outbox_id: uuid.UUID,
    r: Request,
    u: UserContext = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    outbox = await _notif_svc.retry_outbox(db, outbox_id)
    return ok(outbox.to_dict(), _rid(r), "admin.notification_outbox.retry")


# ═══════════════════════════════════════════════════════════════════════════════
# NOTIFICATION TEMPLATES
# ═══════════════════════════════════════════════════════════════════════════════

@admin_notif_templates_router.get("", summary="List notification event templates")
async def admin_list_templates(
    r: Request,
    channel: Optional[str] = Query(None),
    u: UserContext = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    items = await _notif_svc.list_templates(db, channel=channel)
    return ok({"items": items, "total": len(items)}, _rid(r), "admin.notification_templates.list")


class CreateTemplateIn(BaseModel):
    template_key: str
    template_name: str
    channel: str
    subject_template: Optional[str] = None
    body_template: str
    action_label_template: Optional[str] = None
    action_url_template: Optional[str] = None
    is_active: bool = True


@admin_notif_templates_router.post("", summary="Create notification template", status_code=201)
async def admin_create_template(
    body: CreateTemplateIn,
    r: Request,
    u: UserContext = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    tmpl = await _notif_svc.create_template(db, body.model_dump())
    return ok(tmpl.to_dict(), _rid(r), "admin.notification_templates.create")


class UpdateTemplateIn(BaseModel):
    template_name: Optional[str] = None
    subject_template: Optional[str] = None
    body_template: Optional[str] = None
    action_label_template: Optional[str] = None
    action_url_template: Optional[str] = None


@admin_notif_templates_router.put("/{template_id}", summary="Update notification template")
async def admin_update_template(
    template_id: uuid.UUID,
    body: UpdateTemplateIn,
    r: Request,
    u: UserContext = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    tmpl = await _notif_svc.update_template(db, template_id, body.model_dump(exclude_none=True))
    return ok(tmpl.to_dict(), _rid(r), "admin.notification_templates.update")


@admin_notif_templates_router.post("/{template_id}/activate", summary="Activate template")
async def admin_activate_template(
    template_id: uuid.UUID,
    r: Request,
    u: UserContext = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    tmpl = await _notif_svc.set_template_active(db, template_id, True)
    return ok(tmpl.to_dict(), _rid(r), "admin.notification_templates.activate")


@admin_notif_templates_router.post("/{template_id}/deactivate", summary="Deactivate template")
async def admin_deactivate_template(
    template_id: uuid.UUID,
    r: Request,
    u: UserContext = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    tmpl = await _notif_svc.set_template_active(db, template_id, False)
    return ok(tmpl.to_dict(), _rid(r), "admin.notification_templates.deactivate")


# ═══════════════════════════════════════════════════════════════════════════════
# ADMIN CHAT
# ═══════════════════════════════════════════════════════════════════════════════

@admin_chat_router.get("/threads", summary="List all chat threads (admin)")
async def admin_list_threads(
    r: Request,
    status: Optional[str] = Query(None),
    tenant_id: Optional[uuid.UUID] = Query(None),
    limit: int = Query(30, ge=1, le=200),
    offset: int = Query(0, ge=0),
    u: UserContext = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    from app.engines.platform_notifications.models import ChatThread
    from sqlalchemy import func as sqlfunc
    q = select(ChatThread)
    if status:
        q = q.where(ChatThread.status == status)
    if tenant_id:
        q = q.where(ChatThread.tenant_id == tenant_id)
    total_r = await db.execute(select(sqlfunc.count()).select_from(q.subquery()))
    total = total_r.scalar_one()
    res = await db.execute(q.order_by(ChatThread.last_message_at.desc().nullslast()).limit(limit).offset(offset))
    items = res.scalars().all()
    return ok({"items": [t.to_dict() for t in items], "total": total}, _rid(r), "admin.chat.threads.list")


@admin_chat_router.get("/threads/{thread_id}", summary="Get thread (admin)")
async def admin_get_thread(
    thread_id: uuid.UUID,
    r: Request,
    u: UserContext = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    from app.engines.platform_notifications.models import ChatThread
    res = await db.execute(select(ChatThread).where(ChatThread.id == thread_id))
    thread = res.scalars().first()
    if not thread:
        raise ValueError("CHAT_THREAD_NOT_FOUND")
    return ok(thread.to_dict(), _rid(r), "admin.chat.thread.get")


@admin_chat_router.get("/threads/{thread_id}/messages", summary="List messages (admin)")
async def admin_list_messages(
    thread_id: uuid.UUID,
    r: Request,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    u: UserContext = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await _msg_svc.list_messages(
        db, thread_id, uuid.UUID(u.user_id), RECIP_ADMIN, None,
        limit=limit, offset=offset,
    )
    return ok(result, _rid(r), "admin.chat.messages.list")


class AdminSendMsgIn(BaseModel):
    message_text: Optional[str] = None
    message_type: str = "text"
    visibility: str = "thread"


@admin_chat_router.post("/threads/{thread_id}/messages", summary="Admin send message", status_code=201)
async def admin_send_message(
    thread_id: uuid.UUID,
    body: AdminSendMsgIn,
    r: Request,
    u: UserContext = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    msg = await _msg_svc.send_message(
        db=db, thread_id=thread_id,
        actor_user_id=uuid.UUID(u.user_id), actor_type=RECIP_ADMIN,
        tenant_id=None, message_text=body.message_text,
        message_type=body.message_type, visibility=body.visibility,
    )
    return ok(msg.to_dict(RECIP_ADMIN), _rid(r), "admin.chat.message.send")


@admin_chat_router.post("/threads/{thread_id}/close", summary="Close a chat thread (admin)")
async def admin_close_thread(
    thread_id: uuid.UUID,
    r: Request,
    u: UserContext = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    thread = await _thread_svc.close_thread(
        db, thread_id, uuid.UUID(u.user_id), RECIP_ADMIN,
    )
    return ok(thread.to_dict(), _rid(r), "admin.chat.thread.close")


class HideMsgIn(BaseModel):
    reason: str


@admin_chat_router.post("/messages/{message_id}/hide", summary="Hide/moderate a chat message (admin)")
async def admin_hide_message(
    message_id: uuid.UUID,
    body: HideMsgIn,
    r: Request,
    u: UserContext = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    msg = await _msg_svc.moderate_message(db, message_id, uuid.UUID(u.user_id), body.reason)
    return ok({"hidden": True, "message_id": str(msg.id)}, _rid(r), "admin.chat.message.hide")


# ═══════════════════════════════════════════════════════════════════════════════
# ADMIN AUDIT LOGS
# ═══════════════════════════════════════════════════════════════════════════════

@admin_audit_router.get("", summary="List all platform audit logs")
async def admin_list_audit(
    r: Request,
    resource_type: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    engine_key: Optional[str] = Query(None),
    tenant_id: Optional[uuid.UUID] = Query(None),
    actor_user_id: Optional[uuid.UUID] = Query(None),
    search: Optional[str] = Query(None, max_length=256),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    u: UserContext = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await _audit_svc.get_audit_logs(
        db, actor_type="admin",
        resource_type=resource_type, action=action, engine_key=engine_key,
        tenant_id=tenant_id, actor_user_id_filter=actor_user_id,
        search=search, limit=limit, offset=offset,
    )
    return ok(result, _rid(r), "admin.audit_logs.list")


@admin_audit_router.get("/login-events", summary="Admin login/logout audit trail (login_events table)")
async def admin_list_login_events(
    r: Request,
    email: Optional[str] = Query(None),
    event_type: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    u: UserContext = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    """Phase 1 Admin Setup certification fix: login/logout events were being
    recorded to login_events but never exposed to any admin UI — this closes
    that gap so login/logout is visible under /admin/audit-logs."""
    from sqlalchemy import text as _text
    where = []
    params: dict = {"limit": limit, "offset": offset}
    if email:
        where.append("email_attempted ILIKE :email")
        params["email"] = f"%{email}%"
    if event_type:
        where.append("event_type = :event_type")
        params["event_type"] = event_type
    where_sql = f"WHERE {' AND '.join(where)}" if where else ""
    total = (await db.execute(_text(
        f"SELECT count(*) FROM login_events {where_sql}"), params)).scalar_one_or_none() or 0
    rows = (await db.execute(_text(f"""
        SELECT id, user_id, email_attempted, event_type, failure_reason,
               ip_address, request_id, created_at
        FROM login_events {where_sql}
        ORDER BY created_at DESC OFFSET :offset LIMIT :limit
    """), params)).mappings().all()
    items = [{
        "id": str(row["id"]), "user_id": str(row["user_id"]) if row["user_id"] else None,
        "email_attempted": row["email_attempted"], "event_type": row["event_type"],
        "failure_reason": row["failure_reason"], "ip_address": row["ip_address"],
        "request_id": row["request_id"],
        "created_at": row["created_at"].isoformat() if row["created_at"] else None,
    } for row in rows]
    return ok({"items": items, "total": total, "limit": limit, "offset": offset},
              _rid(r), "admin.audit_logs.login_events")


@admin_audit_router.get("/record-timeline", summary="Audit timeline for a specific record")
async def admin_record_timeline(
    resource_type: str,
    resource_id: uuid.UUID,
    r: Request,
    u: UserContext = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    items = await _audit_svc.get_record_timeline(db, resource_type, resource_id, actor_type="admin")
    return ok({"timeline": items}, _rid(r), "admin.audit_logs.timeline")
