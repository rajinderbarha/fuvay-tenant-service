"""Messaging Gateway router — Meta Cloud API webhook.

Two endpoints, both unauthenticated by design: Meta calls them, not a user.
Authenticity is proved by the verify token (GET) and the HMAC signature over
the raw body (POST), never by a session.
"""
from __future__ import annotations

import structlog
from fastapi import APIRouter, Depends, Query, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.db import get_db
from app.exceptions import ServiceOSException
from app.engines.messaging_gateway import handoff, meta_client
from app.engines.messaging_gateway.config_service import messaging_channel_config_service
from app.engines.messaging_gateway.constants import (
    CHANNEL_INSTAGRAM, CHANNEL_WHATSAPP, ENGINE_ID, VALID_CHANNELS,
)
from app.engines.messaging_gateway.service import MessagingGatewayService
from app.schemas.base import ok

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/v1/messaging/meta", tags=["Messaging Gateway"])


def _rid(r: Request) -> str:
    return getattr(r.state, "request_id", None) or r.headers.get("X-Request-ID", "—")


@router.get("/webhook", summary="Meta webhook subscription handshake")
async def verify_webhook(
    hub_mode: str | None = Query(None, alias="hub.mode"),
    hub_verify_token: str | None = Query(None, alias="hub.verify_token"),
    hub_challenge: str | None = Query(None, alias="hub.challenge"),
    db: AsyncSession = Depends(get_db),
):
    """Meta calls this once when the webhook URL is saved.

    It expects the raw `hub.challenge` echoed back as plain text — a JSON
    envelope or any other body fails verification, which is why this returns a
    bare `Response` rather than the usual `ok(...)` wrapper.
    """
    matched = False
    for channel in (CHANNEL_WHATSAPP, CHANNEL_INSTAGRAM):
        config = await messaging_channel_config_service.get(db, channel)
        if config and meta_client.verify_subscription(
            hub_mode, hub_verify_token,
            verify_token=str(config.get("verify_token") or ""),
        ):
            matched = True
            break
    if not matched:
        logger.warning("messaging_gateway.verify.rejected", mode=hub_mode)
        return Response(content="forbidden", status_code=403, media_type="text/plain")
    return Response(content=hub_challenge or "", status_code=200, media_type="text/plain")


@router.get("/webhook/{channel}", summary="Channel-specific Meta webhook handshake")
async def verify_channel_webhook(
    channel: str,
    hub_mode: str | None = Query(None, alias="hub.mode"),
    hub_verify_token: str | None = Query(None, alias="hub.verify_token"),
    hub_challenge: str | None = Query(None, alias="hub.challenge"),
    db: AsyncSession = Depends(get_db),
):
    if channel not in VALID_CHANNELS:
        return Response(content="not found", status_code=404, media_type="text/plain")
    config = await messaging_channel_config_service.get(db, channel)
    if not config or not meta_client.verify_subscription(
        hub_mode, hub_verify_token, verify_token=str(config.get("verify_token") or ""),
    ):
        logger.warning("messaging_gateway.verify.rejected", mode=hub_mode, channel=channel)
        return Response(content="forbidden", status_code=403, media_type="text/plain")
    return Response(content=hub_challenge or "", status_code=200, media_type="text/plain")


@router.post("/webhook", summary="Meta inbound message webhook")
async def receive_webhook(
    r: Request,
    db: AsyncSession = Depends(get_db),
):
    """Receive inbound WhatsApp/Instagram messages.

    Answers 200 for anything it has safely recorded or safely ignored. Meta
    redelivers on any non-2xx, so returning an error for an unparseable or
    irrelevant payload (a delivery receipt, an unsupported message type) would
    put that payload into a permanent retry loop. Only a failed signature is
    rejected — that traffic is not Meta's and should not be acknowledged.
    """
    raw = await r.body()
    try:
        payload = await r.json()
    except Exception:
        logger.warning("messaging_gateway.payload.unparseable")
        return ok({"received": 0, "results": []}, _rid(r), ENGINE_ID)
    channel = CHANNEL_INSTAGRAM if payload.get("object") == "instagram" else CHANNEL_WHATSAPP
    config = await messaging_channel_config_service.get(db, channel)
    if not config:
        return Response(content="channel not configured", status_code=503, media_type="text/plain")
    signature = r.headers.get("X-Hub-Signature-256")
    if not meta_client.verify_signature(
        raw, signature, app_secret=str(config.get("app_secret") or ""),
    ):
        logger.warning("messaging_gateway.signature.rejected", channel=channel,
                       has_signature=bool(signature), body_bytes=len(raw))
        return Response(content="invalid signature", status_code=403,
                        media_type="text/plain")
    active = await messaging_channel_config_service.get(db, channel, require_enabled=True)
    if not active:
        return ok({"received": 0, "results": [], "disabled": True}, _rid(r), ENGINE_ID)

    messages = meta_client.parse_inbound(payload, expected_channel=channel)
    if not messages:
        # Delivery/read receipts and echoes land here — expected, not an error.
        return ok({"received": 0, "results": []}, _rid(r), ENGINE_ID)

    accepted = [
        message for message in messages
        if await messaging_channel_config_service.accepts_business_id(
            db, channel, message.business_id,
        )
    ]
    svc = MessagingGatewayService(db, request_id=_rid(r), channel_config=active)
    results = []
    for msg in accepted:
        if not msg.provider_message_id or not msg.from_id:
            continue
        try:
            results.append(await svc.handle_inbound(msg))
        except Exception as exc:
            # One bad message must not fail the batch and trigger redelivery of
            # the messages that already succeeded.
            logger.warning("messaging_gateway.inbound.failed",
                           provider_message_id=msg.provider_message_id, error=str(exc))
            results.append({"status": "failed", "reply_sent": False})

    return ok({"received": len(accepted), "results": results}, _rid(r), ENGINE_ID)


@router.post("/webhook/{channel}", summary="Channel-specific Meta inbound webhook")
async def receive_channel_webhook(
    channel: str,
    r: Request,
    db: AsyncSession = Depends(get_db),
):
    if channel not in VALID_CHANNELS:
        return Response(content="not found", status_code=404, media_type="text/plain")
    config = await messaging_channel_config_service.get(db, channel)
    if not config:
        return Response(content="channel not configured", status_code=503, media_type="text/plain")
    raw = await r.body()
    if not meta_client.verify_signature(
        raw, r.headers.get("X-Hub-Signature-256"),
        app_secret=str(config.get("app_secret") or ""),
    ):
        logger.warning("messaging_gateway.signature.rejected", channel=channel, body_bytes=len(raw))
        return Response(content="invalid signature", status_code=403, media_type="text/plain")
    active = await messaging_channel_config_service.get(db, channel, require_enabled=True)
    if not active:
        # A correctly signed event received while the admin switch is off is
        # acknowledged but never processed, preventing Meta retry storms.
        return ok({"received": 0, "results": [], "disabled": True}, _rid(r), ENGINE_ID)
    try:
        payload = await r.json()
    except Exception:
        return ok({"received": 0, "results": []}, _rid(r), ENGINE_ID)
    messages = meta_client.parse_inbound(payload, expected_channel=channel)
    accepted = [
        message for message in messages
        if await messaging_channel_config_service.accepts_business_id(db, channel, message.business_id)
    ]
    if len(accepted) != len(messages):
        logger.warning(
            "messaging_gateway.business_id.rejected",
            # The id actually seen, so a mismatch is diagnosable from the log
            # instead of only being visible as a silent count.
            seen_business_ids=sorted({
                str(m.business_id) for m in messages if m.business_id
            }),
            channel=channel, rejected=len(messages) - len(accepted),
        )
    svc = MessagingGatewayService(db, request_id=_rid(r), channel_config=active)
    results = []
    for msg in accepted:
        if not msg.provider_message_id or not msg.from_id:
            continue
        try:
            results.append(await svc.handle_inbound(msg))
        except Exception as exc:
            logger.warning("messaging_gateway.inbound.failed", provider_message_id=msg.provider_message_id, error=str(exc))
            results.append({"status": "failed", "reply_sent": False})
    return ok({"received": len(accepted), "results": results}, _rid(r), ENGINE_ID)


@router.post("/handoff/redeem", summary="Redeem a chat -> web handoff link")
async def redeem_handoff(
    r: Request,
    t: str = Query(..., description="The single-use token from the chat link"),
    db: AsyncSession = Depends(get_db),
):
    """Exchange a handoff token for the draft it points at.

    Unauthenticated on purpose — the token IS the credential, which is why it
    is single-use and short-lived. The web surface calls this on landing, then
    loads the returned draft.

    Invalid, expired and already-used tokens are answered identically (404
    HANDOFF_LINK_INVALID) so a forwarded link cannot be probed for which of
    those it is. Redemption is a POST, not a GET, because it BURNS the token —
    a link preview fetcher or browser prefetch must not be able to consume it.
    """
    result = await handoff.redeem_link(db, t)
    if not result:
        logger.info("messaging_gateway.handoff.redeem_rejected")
        raise ServiceOSException(
            error_code="HANDOFF_LINK_INVALID",
            detail="This link is no longer valid.",
            status_code=404,
            resolution="Send a message in the chat and ask for a new link.",
        )
    await db.commit()
    return ok(result, _rid(r), ENGINE_ID)
