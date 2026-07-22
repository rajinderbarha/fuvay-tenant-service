"""Sprint 27 — Customer Notification + Chat APIs."""
from __future__ import annotations
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Request, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import UserContext, require_customer
from app.dependencies.db import get_db
from app.schemas.base import ok
from app.engines.platform_notifications.notification_service import NotificationService
from app.engines.platform_notifications.chat_service import ChatThreadService, ChatMessageService
from app.engines.platform_notifications.constants import RECIP_CUSTOMER

customer_notif_router = APIRouter(
    prefix="/v1/customer/notifications",
    tags=["Customer Notifications"],
)
customer_chat_router = APIRouter(
    prefix="/v1/customer/chat",
    tags=["Customer Chat"],
)

_notif_svc = NotificationService()
_thread_svc = ChatThreadService()
_msg_svc = ChatMessageService(_thread_svc)


def _rid(r: Request) -> str:
    return getattr(r.state, "request_id", "—")


# ── Notification endpoints ─────────────────────────────────────────────────────

@customer_notif_router.get(
    "",
    summary="List customer in-app notifications",
    description="Returns in-app notifications for the current customer, newest first.",
)
async def list_notifications(
    r: Request,
    read_status: Optional[str] = Query(None, description="unread | read | archived"),
    limit: int = Query(30, ge=1, le=100),
    offset: int = Query(0, ge=0),
    u: UserContext = Depends(require_customer),
    db: AsyncSession = Depends(get_db),
):
    result = await _notif_svc.get_user_notifications(
        db, uuid.UUID(u.user_id), read_status=read_status, limit=limit, offset=offset,
    )
    return ok(result, _rid(r), "customer.notifications.list")


@customer_notif_router.get(
    "/unread-count",
    summary="Get unread notification count",
)
async def unread_count(
    r: Request,
    u: UserContext = Depends(require_customer),
    db: AsyncSession = Depends(get_db),
):
    count = await _notif_svc.get_unread_count(db, uuid.UUID(u.user_id))
    return ok({"unread_count": count}, _rid(r), "customer.notifications.unread_count")


@customer_notif_router.post(
    "/{notification_id}/read",
    summary="Mark a notification as read",
)
async def mark_read(
    notification_id: uuid.UUID,
    r: Request,
    u: UserContext = Depends(require_customer),
    db: AsyncSession = Depends(get_db),
):
    notif = await _notif_svc.mark_notification_read(db, uuid.UUID(u.user_id), notification_id)
    return ok(notif.to_dict(), _rid(r), "customer.notifications.read")


@customer_notif_router.post(
    "/mark-all-read",
    summary="Mark all notifications as read",
)
async def mark_all_read(
    r: Request,
    u: UserContext = Depends(require_customer),
    db: AsyncSession = Depends(get_db),
):
    count = await _notif_svc.mark_all_read(db, uuid.UUID(u.user_id))
    return ok({"marked_read": count}, _rid(r), "customer.notifications.mark_all_read")


@customer_notif_router.get(
    "/preferences",
    summary="Get notification preferences",
)
async def get_preferences(
    r: Request,
    u: UserContext = Depends(require_customer),
    db: AsyncSession = Depends(get_db),
):
    prefs = await _notif_svc.get_preferences(db, uuid.UUID(u.user_id))
    return ok([p.to_dict() for p in prefs], _rid(r), "customer.notifications.preferences")


class UpdatePrefIn(BaseModel):
    event_key: str
    channel: str
    is_enabled: bool


@customer_notif_router.put(
    "/preferences",
    summary="Update notification preference",
)
async def update_preference(
    body: UpdatePrefIn,
    r: Request,
    u: UserContext = Depends(require_customer),
    db: AsyncSession = Depends(get_db),
):
    pref = await _notif_svc.update_preference(
        db, uuid.UUID(u.user_id),
        uuid.UUID(u.tenant_id) if u.tenant_id else None,
        body.event_key, body.channel, body.is_enabled,
    )
    return ok(pref.to_dict(), _rid(r), "customer.notifications.preferences.update")


# ── Chat endpoints ─────────────────────────────────────────────────────────────

@customer_chat_router.get(
    "/threads",
    summary="List customer chat threads",
)
async def list_threads(
    r: Request,
    status: Optional[str] = Query(None),
    limit: int = Query(30, ge=1, le=100),
    offset: int = Query(0, ge=0),
    u: UserContext = Depends(require_customer),
    db: AsyncSession = Depends(get_db),
):
    result = await _thread_svc.list_threads(
        db, uuid.UUID(u.user_id), RECIP_CUSTOMER,
        tenant_id=None, status=status, limit=limit, offset=offset,
    )
    return ok(result, _rid(r), "customer.chat.threads.list")


class CreateThreadIn(BaseModel):
    record_type: str = Field(..., description="service_booking | service_job | complaint | etc.")
    record_id: uuid.UUID


@customer_chat_router.post(
    "/threads",
    summary="Create or get chat thread for a linked record",
    status_code=201,
)
async def create_thread(
    body: CreateThreadIn,
    r: Request,
    u: UserContext = Depends(require_customer),
    db: AsyncSession = Depends(get_db),
):
    thread = await _thread_svc.get_or_create_thread(
        db=db, record_type=body.record_type, record_id=body.record_id,
        actor_user_id=uuid.UUID(u.user_id), actor_type=RECIP_CUSTOMER,
        customer_id=uuid.UUID(u.user_id),
    )
    return ok(thread.to_dict(), _rid(r), "customer.chat.thread.create")


@customer_chat_router.get(
    "/threads/{thread_id}",
    summary="Get thread details",
)
async def get_thread(
    thread_id: uuid.UUID,
    r: Request,
    u: UserContext = Depends(require_customer),
    db: AsyncSession = Depends(get_db),
):
    thread = await _thread_svc.get_thread(
        db, thread_id, uuid.UUID(u.user_id), RECIP_CUSTOMER,
    )
    return ok(thread.to_dict(), _rid(r), "customer.chat.thread.get")


@customer_chat_router.get(
    "/threads/{thread_id}/messages",
    summary="List messages in a thread",
)
async def list_messages(
    thread_id: uuid.UUID,
    r: Request,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    u: UserContext = Depends(require_customer),
    db: AsyncSession = Depends(get_db),
):
    result = await _msg_svc.list_messages(
        db, thread_id, uuid.UUID(u.user_id), RECIP_CUSTOMER, None,
        limit=limit, offset=offset,
    )
    return ok(result, _rid(r), "customer.chat.messages.list")


class SendMessageIn(BaseModel):
    message_text: Optional[str] = None
    message_type: str = "text"
    visibility: str = "thread"


@customer_chat_router.post(
    "/threads/{thread_id}/messages",
    summary="Send a chat message",
    status_code=201,
)
async def send_message(
    thread_id: uuid.UUID,
    body: SendMessageIn,
    r: Request,
    u: UserContext = Depends(require_customer),
    db: AsyncSession = Depends(get_db),
):
    msg = await _msg_svc.send_message(
        db=db, thread_id=thread_id,
        actor_user_id=uuid.UUID(u.user_id), actor_type=RECIP_CUSTOMER,
        tenant_id=None, message_text=body.message_text,
        message_type=body.message_type, visibility=body.visibility,
        actor=u,
    )
    return ok(msg.to_dict(RECIP_CUSTOMER), _rid(r), "customer.chat.message.send")


@customer_chat_router.post(
    "/threads/{thread_id}/read",
    summary="Mark thread messages as read",
)
async def mark_thread_read(
    thread_id: uuid.UUID,
    r: Request,
    u: UserContext = Depends(require_customer),
    db: AsyncSession = Depends(get_db),
):
    count = await _msg_svc.mark_thread_read(
        db, thread_id, uuid.UUID(u.user_id), RECIP_CUSTOMER, None,
    )
    return ok({"messages_marked_read": count}, _rid(r), "customer.chat.thread.read")
