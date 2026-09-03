"""Super-admin control plane for WhatsApp and Instagram booking channels."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import UserContext, require_super_admin
from app.dependencies.db import get_db
from app.engines.messaging_gateway.config_service import messaging_channel_config_service
from app.engines.messaging_gateway.constants import VALID_CHANNELS
from app.engines.messaging_gateway.models import MessagingDeliveryEvent, MessagingInboundMessage, MessagingThread
from app.exceptions import ServiceOSException
from app.schemas.base import ok


router = APIRouter(prefix="/v1/admin/messaging-channels", tags=["Admin Messaging Channels"])


def _rid(request: Request) -> str:
    return getattr(request.state, "request_id", "—")


def _actor(user: UserContext) -> uuid.UUID | None:
    return uuid.UUID(user.user_id) if user.user_id else None


class ConfigurationIn(BaseModel):
    values: dict


class EnabledIn(BaseModel):
    enabled: bool


class HandoffIn(BaseModel):
    human_handoff: bool


@router.get("", summary="List Meta booking channel configuration")
async def list_channels(
    request: Request,
    user: UserContext = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    items = await messaging_channel_config_service.list_public(db)
    counts = dict((await db.execute(
        select(MessagingThread.channel, func.count(MessagingThread.id))
        .group_by(MessagingThread.channel)
    )).all())
    for item in items:
        item["thread_count"] = int(counts.get(item["channel"], 0))
    return ok({"items": items}, _rid(request), "admin.messaging_channels.list")


@router.put("/{channel}", summary="Save encrypted Meta channel credentials")
async def save_channel(
    channel: str,
    body: ConfigurationIn,
    request: Request,
    user: UserContext = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    item = await messaging_channel_config_service.save(db, channel, body.values, _actor(user))
    return ok(item, _rid(request), "admin.messaging_channels.configure")


@router.post("/{channel}/test", summary="Test Meta channel credentials")
async def test_channel(
    channel: str,
    request: Request,
    user: UserContext = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    item = await messaging_channel_config_service.test(db, channel, _actor(user))
    return ok(item, _rid(request), "admin.messaging_channels.test")


@router.put("/{channel}/enabled", summary="Enable or disable social booking")
async def set_channel_enabled(
    channel: str,
    body: EnabledIn,
    request: Request,
    user: UserContext = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    item = await messaging_channel_config_service.set_enabled(db, channel, body.enabled, _actor(user))
    return ok(item, _rid(request), "admin.messaging_channels.enabled")


@router.post("/{channel}/profile/sync", summary="Publish Instagram conversation entry points")
async def sync_channel_profile(
    channel: str,
    request: Request,
    user: UserContext = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    item = await messaging_channel_config_service.sync_profile(
        db, channel, _actor(user),
    )
    return ok(item, _rid(request), "admin.messaging_channels.profile_sync")


@router.get("/{channel}/audit", summary="List secret-free configuration audit history")
async def channel_audit(
    channel: str,
    request: Request,
    limit: int = Query(50, ge=1, le=200),
    user: UserContext = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    return ok(
        {"items": await messaging_channel_config_service.audit(db, channel, limit)},
        _rid(request), "admin.messaging_channels.audit",
    )


@router.get("/threads/list", summary="List WhatsApp and Instagram booking conversations")
async def list_threads(
    request: Request,
    channel: str | None = Query(None),
    handoff_only: bool = Query(False),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user: UserContext = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    if channel and channel not in VALID_CHANNELS:
        raise ServiceOSException("MESSAGING_CHANNEL_NOT_FOUND", "Unknown messaging channel.", status_code=404)
    query = select(MessagingThread)
    count_query = select(func.count()).select_from(MessagingThread)
    if channel:
        query = query.where(MessagingThread.channel == channel)
        count_query = count_query.where(MessagingThread.channel == channel)
    if handoff_only:
        query = query.where(MessagingThread.human_handoff.is_(True))
        count_query = count_query.where(MessagingThread.human_handoff.is_(True))
    rows = (await db.execute(
        query.order_by(MessagingThread.last_inbound_at.desc().nullslast()).offset(offset).limit(limit)
    )).scalars().all()
    total = int((await db.execute(count_query)).scalar() or 0)
    return ok({"items": [row.to_dict() for row in rows], "total": total}, _rid(request), "admin.messaging_threads.list")


@router.put("/threads/{thread_id}/handoff", summary="Give the bot or a human control of a thread")
async def set_thread_handoff(
    thread_id: uuid.UUID,
    body: HandoffIn,
    request: Request,
    user: UserContext = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    row = await db.get(MessagingThread, thread_id)
    if not row:
        raise ServiceOSException("MESSAGING_THREAD_NOT_FOUND", "Messaging thread not found.", status_code=404)
    row.human_handoff = body.human_handoff
    await db.commit()
    return ok(row.to_dict(), _rid(request), "admin.messaging_threads.handoff")


@router.get("/messages/recent", summary="List recent inbound webhook processing outcomes")
async def recent_messages(
    request: Request,
    limit: int = Query(50, ge=1, le=200),
    user: UserContext = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    rows = (await db.execute(
        select(MessagingInboundMessage)
        .order_by(MessagingInboundMessage.created_at.desc())
        .limit(limit)
    )).scalars().all()
    return ok({"items": [row.to_dict() for row in rows]}, _rid(request), "admin.messaging_messages.list")


@router.get("/delivery-events/recent", summary="List recent Meta delivery and read callbacks")
async def recent_delivery_events(
    request: Request,
    limit: int = Query(50, ge=1, le=200),
    user: UserContext = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    rows = (await db.execute(
        select(MessagingDeliveryEvent)
        .order_by(MessagingDeliveryEvent.occurred_at.desc())
        .limit(limit)
    )).scalars().all()
    return ok({"items": [row.to_dict() for row in rows]}, _rid(request), "admin.messaging_delivery.list")
