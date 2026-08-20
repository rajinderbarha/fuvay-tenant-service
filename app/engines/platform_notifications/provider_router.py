"""Sprint 27 — Provider + Staff Notification + Chat APIs."""
from __future__ import annotations
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Request, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import get_current_user, UserContext, require_staff_or_technician_only
from app.dependencies.db import get_db
from app.schemas.base import ok
from app.core.permissions import require_owner_or_office_staff_mutation
from app.engines.platform_notifications.notification_service import NotificationService
from app.engines.platform_notifications.chat_service import ChatThreadService, ChatMessageService
from app.engines.platform_notifications.audit_service import PlatformAuditLogService
from app.engines.platform_notifications.constants import RECIP_PROVIDER, RECIP_STAFF, RECIP_TECHNICIAN
from app.engines.platform_notifications.workspace_projection import get_workspace_summary, get_workspace_items, project_item

# Slice 2F-18: `provider_*` routers are the tenant_owner/office-staff surface
# (the same persona convention as every other `provider_router.py` in this
# codebase, e.g. field_ops.router) — narrower than "any authenticated role",
# which is what `get_current_user` alone allowed. `staff_*` routers are the
# staff/technician self-service surface (same convention as
# field_ops.staff_router), narrower still (excludes tenant_owner/super_admin,
# per require_staff_or_technician_only's own docstring).
_provider_guard = require_owner_or_office_staff_mutation
_staff_guard = require_staff_or_technician_only

provider_notif_router = APIRouter(
    prefix="/v1/provider/notifications",
    tags=["Provider Notifications"],
)
provider_chat_router = APIRouter(
    prefix="/v1/provider/chat",
    tags=["Provider Chat"],
)
provider_audit_router = APIRouter(
    prefix="/v1/provider/audit-logs",
    tags=["Provider Audit Logs"],
)
staff_notif_router = APIRouter(
    prefix="/v1/staff/notifications",
    tags=["Staff Notifications"],
)
staff_chat_router = APIRouter(
    prefix="/v1/staff/chat",
    tags=["Staff Chat"],
)

_notif_svc  = NotificationService()
_thread_svc = ChatThreadService()
_msg_svc    = ChatMessageService(_thread_svc)
_audit_svc  = PlatformAuditLogService()


def _rid(r: Request) -> str:
    return getattr(r.state, "request_id", "—")


def _tid(u: UserContext) -> uuid.UUID | None:
    return uuid.UUID(u.tenant_id) if u.tenant_id else None


def _staff_actor_type(u: UserContext) -> str:
    """Slice 2F-18A: staff_chat_router serves both `staff` and `technician`
    roles (require_staff_or_technician_only admits both), but they are NOT
    the same persona for chat/thread ownership purposes — a technician gets
    no tenant-wide access (see chat_service.validate_thread_access's
    RECIP_TECHNICIAN branch). Distinguish by the caller's real role so the
    service layer can apply the correct policy instead of treating every
    staff_chat_router caller as tenant-wide staff."""
    return RECIP_TECHNICIAN if u.role == "technician" else RECIP_STAFF


# ═══════════════════════════════════════════════════════════════════════════════
# PROVIDER NOTIFICATIONS
# ═══════════════════════════════════════════════════════════════════════════════

@provider_notif_router.get("", summary="List provider in-app notifications")
async def provider_list_notifications(
    r: Request,
    read_status: Optional[str] = Query(None),
    limit: int = Query(30, ge=1, le=100),
    offset: int = Query(0, ge=0),
    u: UserContext = Depends(_provider_guard),
    db: AsyncSession = Depends(get_db),
):
    result = await _notif_svc.get_user_notifications(
        db, uuid.UUID(u.user_id), read_status=read_status, limit=limit, offset=offset,
    )
    return ok(result, _rid(r), "provider.notifications.list")


@provider_notif_router.get("/workspace", summary="Provider notification workspace")
async def provider_notification_workspace(
    r: Request, limit: int = Query(30, ge=1, le=100), offset: int = Query(0, ge=0),
    u: UserContext = Depends(_provider_guard), db: AsyncSession = Depends(get_db),
):
    user_id = uuid.UUID(u.user_id)
    result = await get_workspace_items(db, user_id, limit=limit, offset=offset)
    workspace = await get_workspace_summary(db, user_id)
    workspace.update(result)
    return ok(workspace, _rid(r), "provider.notifications.workspace")


@provider_notif_router.get("/unread-count", summary="Provider unread notification count")
async def provider_unread_count(
    r: Request,
    u: UserContext = Depends(_provider_guard),
    db: AsyncSession = Depends(get_db),
):
    count = await _notif_svc.get_unread_count(db, uuid.UUID(u.user_id))
    return ok({"unread_count": count}, _rid(r), "provider.notifications.unread_count")


@provider_notif_router.post("/{notification_id}/read", summary="Mark provider notification read")
async def provider_mark_read(
    notification_id: uuid.UUID,
    r: Request,
    u: UserContext = Depends(_provider_guard),
    db: AsyncSession = Depends(get_db),
):
    notif = await _notif_svc.mark_notification_read(db, uuid.UUID(u.user_id), notification_id)
    return ok(notif.to_dict(), _rid(r), "provider.notifications.read")


@provider_notif_router.post("/mark-all-read", summary="Mark all provider notifications read")
async def provider_mark_all_read(
    r: Request,
    u: UserContext = Depends(_provider_guard),
    db: AsyncSession = Depends(get_db),
):
    count = await _notif_svc.mark_all_read(db, uuid.UUID(u.user_id))
    return ok({"marked_read": count}, _rid(r), "provider.notifications.mark_all_read")


@provider_notif_router.get("/preferences", summary="Get provider notification preferences")
async def provider_get_prefs(
    r: Request,
    u: UserContext = Depends(_provider_guard),
    db: AsyncSession = Depends(get_db),
):
    prefs = await _notif_svc.get_preferences(db, uuid.UUID(u.user_id))
    return ok([p.to_dict() for p in prefs], _rid(r), "provider.notifications.preferences")


class UpdatePrefIn(BaseModel):
    event_key: str
    channel: str
    is_enabled: bool


@provider_notif_router.put("/preferences", summary="Update provider notification preference")
async def provider_update_pref(
    body: UpdatePrefIn,
    r: Request,
    u: UserContext = Depends(_provider_guard),
    db: AsyncSession = Depends(get_db),
):
    pref = await _notif_svc.update_preference(
        db, uuid.UUID(u.user_id), _tid(u), body.event_key, body.channel, body.is_enabled,
    )
    return ok(pref.to_dict(), _rid(r), "provider.notifications.preferences.update")


class BulkReadIn(BaseModel):
    notification_ids: list[uuid.UUID] = Field(min_length=1, max_length=100)


@provider_notif_router.post("/mark-read-bulk", summary="Mark selected provider notifications read")
async def provider_mark_read_bulk(
    body: BulkReadIn, r: Request, u: UserContext = Depends(_provider_guard),
    db: AsyncSession = Depends(get_db),
):
    count = await _notif_svc.mark_read_bulk(db, uuid.UUID(u.user_id), body.notification_ids)
    return ok({"marked_read": count}, _rid(r), "provider.notifications.mark_read_bulk")


@provider_notif_router.get("/{notification_id}", summary="Get provider notification")
async def provider_get_notification(
    notification_id: uuid.UUID, r: Request, u: UserContext = Depends(_provider_guard),
    db: AsyncSession = Depends(get_db),
):
    notif = await _notif_svc._owned_notification(db, uuid.UUID(u.user_id), notification_id)
    return ok(project_item(notif), _rid(r), "provider.notifications.get")


@provider_notif_router.post("/{notification_id}/archive", summary="Archive provider notification")
async def provider_archive_notification(
    notification_id: uuid.UUID, r: Request, u: UserContext = Depends(_provider_guard),
    db: AsyncSession = Depends(get_db),
):
    notif = await _notif_svc.archive_notification(db, uuid.UUID(u.user_id), notification_id)
    return ok(project_item(notif), _rid(r), "provider.notifications.archive")


@provider_notif_router.post("/{notification_id}/unarchive", summary="Restore provider notification")
async def provider_unarchive_notification(
    notification_id: uuid.UUID, r: Request, u: UserContext = Depends(_provider_guard),
    db: AsyncSession = Depends(get_db),
):
    notif = await _notif_svc.unarchive_notification(db, uuid.UUID(u.user_id), notification_id)
    return ok(project_item(notif), _rid(r), "provider.notifications.unarchive")


# ═══════════════════════════════════════════════════════════════════════════════
# PROVIDER CHAT
# ═══════════════════════════════════════════════════════════════════════════════

@provider_chat_router.get("/threads", summary="List provider chat threads")
async def provider_list_threads(
    r: Request,
    status: Optional[str] = Query(None),
    limit: int = Query(30, ge=1, le=100),
    offset: int = Query(0, ge=0),
    u: UserContext = Depends(_provider_guard),
    db: AsyncSession = Depends(get_db),
):
    result = await _thread_svc.list_threads(
        db, uuid.UUID(u.user_id), RECIP_PROVIDER,
        tenant_id=_tid(u), status=status, limit=limit, offset=offset,
    )
    return ok(result, _rid(r), "provider.chat.threads.list")


class CreateThreadIn(BaseModel):
    record_type: str
    record_id: uuid.UUID


@provider_chat_router.post("/threads", summary="Create or get thread for linked record", status_code=201)
async def provider_create_thread(
    body: CreateThreadIn,
    r: Request,
    u: UserContext = Depends(_provider_guard),
    db: AsyncSession = Depends(get_db),
):
    thread = await _thread_svc.get_or_create_thread(
        db=db, record_type=body.record_type, record_id=body.record_id,
        actor_user_id=uuid.UUID(u.user_id), actor_type=RECIP_PROVIDER,
        tenant_id=_tid(u),
    )
    return ok(thread.to_dict(), _rid(r), "provider.chat.thread.create")


@provider_chat_router.get("/threads/{thread_id}", summary="Get thread details")
async def provider_get_thread(
    thread_id: uuid.UUID,
    r: Request,
    u: UserContext = Depends(_provider_guard),
    db: AsyncSession = Depends(get_db),
):
    thread = await _thread_svc.get_thread(
        db, thread_id, uuid.UUID(u.user_id), RECIP_PROVIDER, _tid(u),
    )
    return ok(thread.to_dict(), _rid(r), "provider.chat.thread.get")


@provider_chat_router.get("/threads/{thread_id}/messages", summary="List thread messages")
async def provider_list_messages(
    thread_id: uuid.UUID,
    r: Request,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    u: UserContext = Depends(_provider_guard),
    db: AsyncSession = Depends(get_db),
):
    result = await _msg_svc.list_messages(
        db, thread_id, uuid.UUID(u.user_id), RECIP_PROVIDER, _tid(u),
        limit=limit, offset=offset,
    )
    return ok(result, _rid(r), "provider.chat.messages.list")


class SendMsgIn(BaseModel):
    message_text: Optional[str] = None
    message_type: str = "text"
    visibility: str = "thread"
    media_ids: list[str] | None = None  # Phase 0A: media engine asset IDs for attachments


@provider_chat_router.post("/threads/{thread_id}/messages", summary="Send message", status_code=201)
async def provider_send_message(
    thread_id: uuid.UUID,
    body: SendMsgIn,
    r: Request,
    u: UserContext = Depends(_provider_guard),
    db: AsyncSession = Depends(get_db),
):
    media_urls = {"media_ids": body.media_ids} if body.media_ids else None
    msg = await _msg_svc.send_message(
        db=db, thread_id=thread_id,
        actor_user_id=uuid.UUID(u.user_id), actor_type=RECIP_PROVIDER,
        tenant_id=_tid(u), message_text=body.message_text,
        message_type=body.message_type, visibility=body.visibility,
        media_urls=media_urls, actor=u,
    )
    return ok(msg.to_dict(RECIP_PROVIDER), _rid(r), "provider.chat.message.send")


@provider_chat_router.post("/threads/{thread_id}/read", summary="Mark thread read")
async def provider_mark_thread_read(
    thread_id: uuid.UUID,
    r: Request,
    u: UserContext = Depends(_provider_guard),
    db: AsyncSession = Depends(get_db),
):
    count = await _msg_svc.mark_thread_read(
        db, thread_id, uuid.UUID(u.user_id), RECIP_PROVIDER, _tid(u),
    )
    return ok({"messages_marked_read": count}, _rid(r), "provider.chat.thread.read")


# ═══════════════════════════════════════════════════════════════════════════════
# PROVIDER AUDIT LOGS (scoped)
# ═══════════════════════════════════════════════════════════════════════════════

@provider_audit_router.get("", summary="List tenant-scoped audit logs")
async def provider_list_audit(
    r: Request,
    resource_type: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    u: UserContext = Depends(_provider_guard),
    db: AsyncSession = Depends(get_db),
):
    result = await _audit_svc.get_audit_logs(
        db, actor_type="provider", tenant_id=_tid(u),
        resource_type=resource_type, action=action,
        limit=limit, offset=offset,
    )
    return ok(result, _rid(r), "provider.audit_logs.list")


@provider_audit_router.get("/record-timeline", summary="Audit timeline for a specific record")
async def provider_record_timeline(
    resource_type: str,
    resource_id: uuid.UUID,
    r: Request,
    u: UserContext = Depends(_provider_guard),
    db: AsyncSession = Depends(get_db),
):
    items = await _audit_svc.get_record_timeline(
        db, resource_type, resource_id, actor_type="provider", tenant_id=_tid(u),
    )
    return ok({"timeline": items}, _rid(r), "provider.audit_logs.timeline")


# ═══════════════════════════════════════════════════════════════════════════════
# STAFF NOTIFICATIONS
# ═══════════════════════════════════════════════════════════════════════════════

@staff_notif_router.get("", summary="List staff in-app notifications")
async def staff_list_notifications(
    r: Request,
    read_status: Optional[str] = Query(None),
    limit: int = Query(30, ge=1, le=100),
    offset: int = Query(0, ge=0),
    u: UserContext = Depends(_staff_guard),
    db: AsyncSession = Depends(get_db),
):
    result = await _notif_svc.get_user_notifications(
        db, uuid.UUID(u.user_id), read_status=read_status, limit=limit, offset=offset,
    )
    return ok(result, _rid(r), "staff.notifications.list")


@staff_notif_router.get("/unread-count", summary="Staff unread notification count")
async def staff_unread_count(
    r: Request,
    u: UserContext = Depends(_staff_guard),
    db: AsyncSession = Depends(get_db),
):
    count = await _notif_svc.get_unread_count(db, uuid.UUID(u.user_id))
    return ok({"unread_count": count}, _rid(r), "staff.notifications.unread_count")


@staff_notif_router.post("/{notification_id}/read", summary="Mark staff notification read")
async def staff_mark_read(
    notification_id: uuid.UUID,
    r: Request,
    u: UserContext = Depends(_staff_guard),
    db: AsyncSession = Depends(get_db),
):
    notif = await _notif_svc.mark_notification_read(db, uuid.UUID(u.user_id), notification_id)
    return ok(notif.to_dict(), _rid(r), "staff.notifications.read")


@staff_notif_router.post("/mark-all-read", summary="Mark all staff notifications read")
async def staff_mark_all_read(
    r: Request,
    u: UserContext = Depends(_staff_guard),
    db: AsyncSession = Depends(get_db),
):
    count = await _notif_svc.mark_all_read(db, uuid.UUID(u.user_id))
    return ok({"marked_read": count}, _rid(r), "staff.notifications.mark_all_read")


# ═══════════════════════════════════════════════════════════════════════════════
# STAFF CHAT
# ═══════════════════════════════════════════════════════════════════════════════

@staff_chat_router.get("/threads", summary="List staff chat threads")
async def staff_list_threads(
    r: Request,
    status: Optional[str] = Query(None),
    limit: int = Query(30, ge=1, le=100),
    offset: int = Query(0, ge=0),
    u: UserContext = Depends(_staff_guard),
    db: AsyncSession = Depends(get_db),
):
    result = await _thread_svc.list_threads(
        db, uuid.UUID(u.user_id), _staff_actor_type(u),
        tenant_id=_tid(u), status=status, limit=limit, offset=offset,
    )
    return ok(result, _rid(r), "staff.chat.threads.list")


@staff_chat_router.get("/threads/{thread_id}", summary="Get staff thread")
async def staff_get_thread(
    thread_id: uuid.UUID,
    r: Request,
    u: UserContext = Depends(_staff_guard),
    db: AsyncSession = Depends(get_db),
):
    thread = await _thread_svc.get_thread(
        db, thread_id, uuid.UUID(u.user_id), _staff_actor_type(u), _tid(u),
    )
    return ok(thread.to_dict(), _rid(r), "staff.chat.thread.get")


@staff_chat_router.get("/threads/{thread_id}/messages", summary="List staff thread messages")
async def staff_list_messages(
    thread_id: uuid.UUID,
    r: Request,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    u: UserContext = Depends(_staff_guard),
    db: AsyncSession = Depends(get_db),
):
    result = await _msg_svc.list_messages(
        db, thread_id, uuid.UUID(u.user_id), _staff_actor_type(u), _tid(u),
        limit=limit, offset=offset,
    )
    return ok(result, _rid(r), "staff.chat.messages.list")


@staff_chat_router.post("/threads/{thread_id}/messages", summary="Staff send message", status_code=201)
async def staff_send_message(
    thread_id: uuid.UUID,
    body: SendMsgIn,
    r: Request,
    u: UserContext = Depends(_staff_guard),
    db: AsyncSession = Depends(get_db),
):
    # Slice 2F-18C: media_ids was previously accepted by this schema but
    # silently dropped (never forwarded) -- SAFE_SUPPORT disposition: now
    # forwarded through the same validated path provider_send_message uses
    # (existence/context/lifecycle/tenant/customer/MediaAccessService/
    # thread-lineage checks), not silently ignored.
    staff_actor_type = _staff_actor_type(u)
    media_urls = {"media_ids": body.media_ids} if body.media_ids else None
    msg = await _msg_svc.send_message(
        db=db, thread_id=thread_id,
        actor_user_id=uuid.UUID(u.user_id), actor_type=staff_actor_type,
        tenant_id=_tid(u), message_text=body.message_text,
        message_type=body.message_type, visibility=body.visibility,
        media_urls=media_urls, actor=u,
    )
    return ok(msg.to_dict(staff_actor_type), _rid(r), "staff.chat.message.send")


@staff_chat_router.post("/threads/{thread_id}/read", summary="Staff mark thread read")
async def staff_mark_thread_read(
    thread_id: uuid.UUID,
    r: Request,
    u: UserContext = Depends(_staff_guard),
    db: AsyncSession = Depends(get_db),
):
    count = await _msg_svc.mark_thread_read(
        db, thread_id, uuid.UUID(u.user_id), _staff_actor_type(u), _tid(u),
    )
    return ok({"messages_marked_read": count}, _rid(r), "staff.chat.thread.read")
