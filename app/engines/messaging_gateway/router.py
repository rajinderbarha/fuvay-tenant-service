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
from app.engines.messaging_gateway.constants import ENGINE_ID
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
):
    """Meta calls this once when the webhook URL is saved.

    It expects the raw `hub.challenge` echoed back as plain text — a JSON
    envelope or any other body fails verification, which is why this returns a
    bare `Response` rather than the usual `ok(...)` wrapper.
    """
    if not meta_client.verify_subscription(hub_mode, hub_verify_token):
        logger.warning("messaging_gateway.verify.rejected", mode=hub_mode)
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
    signature = r.headers.get("X-Hub-Signature-256")

    if not meta_client.verify_signature(raw, signature):
        logger.warning("messaging_gateway.signature.rejected",
                       has_signature=bool(signature), body_bytes=len(raw))
        return Response(content="invalid signature", status_code=403,
                        media_type="text/plain")

    try:
        payload = await r.json()
    except Exception:
        logger.warning("messaging_gateway.payload.unparseable")
        return ok({"received": 0, "results": []}, _rid(r), ENGINE_ID)

    messages = meta_client.parse_inbound(payload)
    if not messages:
        # Delivery/read receipts and echoes land here — expected, not an error.
        return ok({"received": 0, "results": []}, _rid(r), ENGINE_ID)

    svc = MessagingGatewayService(db, request_id=_rid(r))
    results = []
    for msg in messages:
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

    return ok({"received": len(messages), "results": results}, _rid(r), ENGINE_ID)


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
