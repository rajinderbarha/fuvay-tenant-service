"""Meta Cloud API client — signature verification, payload parsing, outbound send.

Everything Meta-specific is confined to this module. The service layer works
only with the normalised `InboundMessage` below, so adding Twilio or Instagram
later is a second parser, not a second pipeline.
"""
from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import dataclass, field
from typing import Any

import httpx
import structlog

from app.config import get_settings
from app.engines.messaging_gateway.constants import (
    CHANNEL_INSTAGRAM, CHANNEL_WHATSAPP, MAX_OUTBOUND_CHARS,
)

logger = structlog.get_logger(__name__)

GRAPH_BASE = "https://graph.facebook.com/v21.0"


@dataclass
class InboundMessage:
    """One customer message, normalised away from Meta's envelope."""
    channel: str
    provider_message_id: str
    from_id: str
    business_id: str | None
    message_type: str
    text: str
    display_name: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


def _cfg(name: str, default: str = "") -> str:
    return str(getattr(get_settings(), name, default) or default)


def verify_signature(raw_body: bytes, header_signature: str | None) -> bool:
    """Validate Meta's `X-Hub-Signature-256` over the RAW request body.

    This must run against the exact bytes received: re-serialising the parsed
    JSON changes key order and whitespace and the HMAC will never match.

    Returns False when no app secret is configured, so an unconfigured
    deployment fails CLOSED rather than accepting unsigned traffic.
    """
    secret = _cfg("META_APP_SECRET")
    if not secret:
        logger.warning("messaging_gateway.signature.no_secret_configured")
        return False
    if not header_signature or not header_signature.startswith("sha256="):
        return False
    expected = hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
    # Constant-time compare — a plain `==` leaks the signature byte by byte.
    return hmac.compare_digest(expected, header_signature.split("=", 1)[1])


def verify_subscription(mode: str | None, token: str | None) -> bool:
    """The GET handshake Meta performs once when the webhook URL is saved."""
    configured = _cfg("META_VERIFY_TOKEN")
    if not configured:
        return False
    return mode == "subscribe" and hmac.compare_digest(configured, token or "")


def parse_inbound(payload: dict[str, Any]) -> list[InboundMessage]:
    """Extract customer messages from a Meta webhook payload.

    Meta batches: one payload carries `entry[] -> changes[] -> value.messages[]`.
    Status callbacks (delivered/read receipts) arrive on the same webhook with
    `value.statuses` and NO `messages` key — those are deliberately skipped
    here, otherwise every delivery receipt would be replayed into the agent as
    if the customer had said something.
    """
    out: list[InboundMessage] = []
    for entry in payload.get("entry") or []:
        for change in entry.get("changes") or []:
            value = change.get("value") or {}
            if not value.get("messages"):
                continue  # statuses / read receipts / echoes

            meta_field = change.get("field") or ""
            channel = CHANNEL_INSTAGRAM if "instagram" in meta_field else CHANNEL_WHATSAPP
            business_id = ((value.get("metadata") or {}).get("phone_number_id")
                           or entry.get("id"))

            names = {
                c.get("wa_id"): ((c.get("profile") or {}).get("name"))
                for c in (value.get("contacts") or [])
            }

            for m in value["messages"]:
                mtype = m.get("type") or "unknown"
                out.append(InboundMessage(
                    channel=channel,
                    provider_message_id=str(m.get("id") or ""),
                    from_id=str(m.get("from") or ""),
                    business_id=str(business_id) if business_id else None,
                    message_type=mtype,
                    text=_extract_text(m, mtype),
                    display_name=names.get(m.get("from")),
                    raw=m,
                ))
    return out


def _extract_text(m: dict[str, Any], mtype: str) -> str:
    """Pull usable text out of the message types worth answering.

    Interactive replies (button/list taps) carry their text under a different
    key than a plain message; treating them as empty would make every tap look
    like an unsupported message type.
    """
    if mtype == "text":
        return str((m.get("text") or {}).get("body") or "").strip()
    if mtype == "interactive":
        inter = m.get("interactive") or {}
        for key in ("button_reply", "list_reply"):
            if inter.get(key):
                return str(inter[key].get("title") or inter[key].get("id") or "").strip()
        return ""
    if mtype == "button":
        return str((m.get("button") or {}).get("text") or "").strip()
    # Images/audio/documents carry an optional caption worth reading; the media
    # itself is handled separately (the booking draft has its own photo upload).
    for key in ("image", "video", "document", "audio"):
        if m.get(key):
            return str((m[key] or {}).get("caption") or "").strip()
    return ""


async def send_text(to: str, text: str, *, channel: str = CHANNEL_WHATSAPP) -> dict[str, Any]:
    """Send a plain text reply.

    Only valid inside the 24-hour customer service window; a business-initiated
    message outside it must use an approved template and will be rejected here
    by Meta with a 131047-class error. Reminders and confirmation prompts are
    therefore template sends, not this call.
    """
    token = _cfg("META_ACCESS_TOKEN")
    phone_number_id = _cfg("META_PHONE_NUMBER_ID")
    if not token or not phone_number_id:
        logger.warning("messaging_gateway.send.not_configured", channel=channel)
        return {"sent": False, "reason": "channel_not_configured"}

    body = text.strip()
    if len(body) > MAX_OUTBOUND_CHARS:
        body = body[: MAX_OUTBOUND_CHARS - 1].rstrip() + "…"

    url = f"{GRAPH_BASE}/{phone_number_id}/messages"
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to,
        "type": "text",
        "text": {"preview_url": False, "body": body},
    }
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                url, headers={"Authorization": f"Bearer {token}"}, json=payload,
            )
        ok = resp.status_code < 400
        if not ok:
            logger.warning("messaging_gateway.send.failed",
                           status=resp.status_code, body=resp.text[:400])
        return {"sent": ok, "status": resp.status_code,
                "response": _safe_json(resp.text)}
    except Exception as exc:  # network/timeout — never break inbound handling
        logger.warning("messaging_gateway.send.exception", error=str(exc))
        return {"sent": False, "reason": "transport_error"}


def _safe_json(text: str) -> Any:
    try:
        return json.loads(text)
    except Exception:
        return text[:400]
