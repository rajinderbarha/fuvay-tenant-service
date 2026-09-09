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
from datetime import datetime, timezone
from typing import Any

import httpx
import structlog

from app.config import get_settings
from app.engines.messaging_gateway.constants import (
    CHANNEL_INSTAGRAM, CHANNEL_WHATSAPP, DEFAULT_GRAPH_API_VERSION,
    IG_GENERIC_SUBTITLE_CHARS, IG_GENERIC_TITLE_CHARS,
    MAX_IG_GENERIC_ELEMENTS, MAX_IG_QUICK_REPLIES,
    MAX_INTERACTIVE_BODY_CHARS, MAX_OUTBOUND_CHARS,
    MAX_WA_BUTTONS, MAX_WA_LIST_ROWS, WA_BUTTON_TITLE_CHARS,
    WA_ROW_DESCRIPTION_CHARS, WA_ROW_TITLE_CHARS,
)

logger = structlog.get_logger(__name__)

FACEBOOK_GRAPH_HOST = "https://graph.facebook.com"
INSTAGRAM_GRAPH_HOST = "https://graph.instagram.com"

INSTAGRAM_ICEBREAKERS = (
    {"question": "Book a home service", "payload": "/fuvay"},
    {"question": "Track my booking", "payload": "/track"},
    {"question": "Check an estimate", "payload": "/track"},
    {"question": "Talk to support", "payload": "/human"},
)


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
    #: The id of the option the customer TAPPED, when they tapped one. The
    #: title alone is not enough to answer with: two brands can share a
    #: truncated 24-character label, and the booking services validate against
    #: option ids, never labels. None for anything typed.
    reply_id: str | None = None
    #: A shared location pin: {"latitude", "longitude", "name", "address"}.
    #: WhatsApp sends these as their own message type. Instagram can send a
    #: location attachment, but some clients omit its coordinates entirely.
    location: dict[str, Any] | None = None
    #: True when Instagram delivered a location-shaped attachment without any
    #: usable coordinates. This is distinct from an arbitrary unsupported
    #: attachment so the booking flow can give the customer a useful recovery.
    location_unavailable: bool = False
    #: Parsed ``interactive.nfm_reply.response_json`` from a completed
    #: WhatsApp Flow. It is kept separate from reply_id until the service has
    #: verified the signed, draft-bound flow token.
    flow_response: dict[str, Any] | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class DeliveryStatusEvent:
    channel: str
    provider_message_id: str
    status: str
    recipient_id: str | None
    business_id: str | None
    occurred_at: datetime
    raw: dict[str, Any] = field(default_factory=dict)


def parse_delivery_statuses(
    payload: dict[str, Any], *, expected_channel: str | None = None,
) -> list[DeliveryStatusEvent]:
    """Normalize WhatsApp and Instagram delivery/read callbacks.

    These callbacks are never passed into the booking conversation, but they
    are persisted so operations can distinguish sent, delivered, read and
    failed messages instead of treating a successful API request as delivery.
    """
    channel = expected_channel or (
        CHANNEL_INSTAGRAM if payload.get("object") == "instagram" else CHANNEL_WHATSAPP
    )
    events: list[DeliveryStatusEvent] = []
    if channel == CHANNEL_INSTAGRAM:
        for entry in payload.get("entry") or []:
            business_id = str(entry.get("id") or "") or None
            for envelope in entry.get("messaging") or []:
                recipient = str((envelope.get("recipient") or {}).get("id") or "") or None
                for status_key in ("delivery", "read"):
                    detail = envelope.get(status_key)
                    if not isinstance(detail, dict):
                        continue
                    timestamp = int(detail.get("watermark") or envelope.get("timestamp") or 0)
                    occurred = datetime.fromtimestamp(timestamp / 1000, timezone.utc) if timestamp else datetime.now(timezone.utc)
                    mids = detail.get("mids") or [f"watermark:{timestamp}"]
                    for mid in mids:
                        events.append(DeliveryStatusEvent(
                            channel=channel, provider_message_id=str(mid), status=status_key,
                            recipient_id=recipient, business_id=business_id,
                            occurred_at=occurred, raw=envelope,
                        ))
        return events

    for entry in payload.get("entry") or []:
        for change in entry.get("changes") or []:
            value = change.get("value") or {}
            business_id = str(((value.get("metadata") or {}).get("phone_number_id") or entry.get("id") or "")) or None
            for status in value.get("statuses") or []:
                raw_timestamp = int(status.get("timestamp") or 0)
                events.append(DeliveryStatusEvent(
                    channel=channel,
                    provider_message_id=str(status.get("id") or ""),
                    status=str(status.get("status") or "unknown"),
                    recipient_id=str(status.get("recipient_id") or "") or None,
                    business_id=business_id,
                    occurred_at=(datetime.fromtimestamp(raw_timestamp, timezone.utc)
                                 if raw_timestamp else datetime.now(timezone.utc)),
                    raw=status,
                ))
    return [event for event in events if event.provider_message_id]


def _cfg(name: str, default: str = "") -> str:
    return str(getattr(get_settings(), name, default) or default)


def verify_signature(
    raw_body: bytes,
    header_signature: str | None,
    *,
    app_secret: str | None = None,
) -> bool:
    """Validate Meta's `X-Hub-Signature-256` over the RAW request body.

    This must run against the exact bytes received: re-serialising the parsed
    JSON changes key order and whitespace and the HMAC will never match.

    Returns False when no app secret is configured, so an unconfigured
    deployment fails CLOSED rather than accepting unsigned traffic.
    """
    secret = (app_secret or _cfg("META_APP_SECRET")).strip()
    if not secret:
        logger.warning("messaging_gateway.signature.no_secret_configured")
        return False
    if not header_signature or not header_signature.startswith("sha256="):
        return False
    expected = hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
    # Constant-time compare — a plain `==` leaks the signature byte by byte.
    return hmac.compare_digest(expected, header_signature.split("=", 1)[1])


def verify_subscription(
    mode: str | None,
    token: str | None,
    *,
    verify_token: str | None = None,
) -> bool:
    """The GET handshake Meta performs once when the webhook URL is saved."""
    configured = (verify_token or _cfg("META_VERIFY_TOKEN")).strip()
    if not configured:
        return False
    return mode == "subscribe" and hmac.compare_digest(configured, token or "")


def parse_inbound(
    payload: dict[str, Any],
    *,
    expected_channel: str | None = None,
) -> list[InboundMessage]:
    """Extract customer messages from a Meta webhook payload.

    Meta batches: one payload carries `entry[] -> changes[] -> value.messages[]`.
    Status callbacks (delivered/read receipts) arrive on the same webhook with
    `value.statuses` and NO `messages` key — those are deliberately skipped
    here, otherwise every delivery receipt would be replayed into the agent as
    if the customer had said something.
    """
    if expected_channel == CHANNEL_INSTAGRAM or (
        expected_channel is None and payload.get("object") == "instagram"
    ):
        return _parse_instagram_inbound(payload)

    out: list[InboundMessage] = []
    for entry in payload.get("entry") or []:
        for change in entry.get("changes") or []:
            value = change.get("value") or {}
            if not value.get("messages"):
                continue  # statuses / read receipts / echoes

            channel = expected_channel or CHANNEL_WHATSAPP
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
                    reply_id=_extract_reply_id(m, mtype),
                    location=_extract_location(m),
                    flow_response=_extract_flow_response(m, mtype),
                    raw=m,
                ))
    return out


def _parse_instagram_inbound(payload: dict[str, Any]) -> list[InboundMessage]:
    """Parse the Messenger-shaped Instagram ``entry[].messaging[]`` envelope."""
    out: list[InboundMessage] = []
    for entry in payload.get("entry") or []:
        business_id = str(entry.get("id") or "") or None
        for event in entry.get("messaging") or []:
            sender_id = str((event.get("sender") or {}).get("id") or "")
            recipient_id = str((event.get("recipient") or {}).get("id") or "")
            message = event.get("message") or {}
            postback = event.get("postback") or {}
            if message.get("is_echo") or not sender_id:
                continue
            if not message and not postback:
                # Read receipts, delivery receipts, reactions and seen events
                # arrive on this SAME webhook shaped as `{"read": {...}}` with
                # no `message` at all — the Instagram twin of WhatsApp's
                # `value.statuses`. Answering one makes the reply generate
                # another receipt, which is answered in turn: a real loop,
                # confirmed live at roughly one message every 2.5 seconds.
                continue
            if (
                message
                and not postback
                and message.get("text") is None
                and not message.get("quick_reply")
                and message.get("attachments")
            ):
                # Instagram turns a phone number typed by the customer into a
                # contact card ("WhatsApp message" / "Call") and delivers that
                # generated card as a SECOND inbound attachment with its own
                # `mid`. It is not a second customer answer, so provider-id
                # idempotency cannot collapse it. Processing it re-rendered the
                # current step and sent two identical OTP confirmation cards.
                #
                # Instagram attachment/location collection is not part of the
                # booking flow; the validated typed address is authoritative.
                # Ignore every attachment-only event before it reaches flow.
                continue
            provider_id = str(message.get("mid") or postback.get("mid") or "")
            if not provider_id:
                # A timestamp used to stand in here. It is not a stable id, so
                # it defeated the `(channel, provider_message_id)` uniqueness
                # that stops a redelivered event being replayed — every receipt
                # looked like a brand-new message.
                continue
            postback_payload = str(postback.get("payload") or "").strip()
            if postback:
                message_type = "postback"
                # Icebreakers use the same command vocabulary as typed chat.
                # A slash payload must reach command parsing instead of being
                # mistaken for a flow picker merely because it is a postback.
                text = (postback_payload if postback_payload.startswith("/") else
                        str(postback.get("title") or postback_payload).strip())
            else:
                message_type = "text" if message.get("text") is not None else "attachment"
                quick_reply = message.get("quick_reply") or {}
                text = str(quick_reply.get("payload") or message.get("text") or "").strip()
            location, location_unavailable = _extract_instagram_location(message)
            out.append(InboundMessage(
                channel=CHANNEL_INSTAGRAM,
                provider_message_id=provider_id,
                from_id=sender_id,
                business_id=business_id or recipient_id or None,
                message_type=message_type,
                text=text,
                reply_id=(None if postback and postback_payload.startswith("/") else (
                    str((message.get("quick_reply") or {}).get("payload") or "")
                    or postback_payload
                ) or None),
                location=location,
                location_unavailable=location_unavailable,
                raw=event,
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
        if inter.get("type") == "nfm_reply":
            return "Booking form completed"
        return ""
    if mtype == "button":
        return str((m.get("button") or {}).get("text") or "").strip()
    # Images/audio/documents carry an optional caption worth reading; the media
    # itself is handled separately (the booking draft has its own photo upload).
    for key in ("image", "video", "document", "audio"):
        if m.get(key):
            return str((m[key] or {}).get("caption") or "").strip()
    return ""


def _extract_location(m: dict[str, Any]) -> dict[str, Any] | None:
    """A shared WhatsApp location pin, or None.

    WhatsApp sends `type: "location"` with real coordinates — the customer taps
    Attach -> Location. Instagram's different attachment envelope is handled
    separately by `_extract_instagram_location`.
    """
    pin = m.get("location") or {}
    latitude, longitude = pin.get("latitude"), pin.get("longitude")
    if latitude is None or longitude is None:
        return None
    try:
        return {
            "latitude": float(latitude),
            "longitude": float(longitude),
            "name": str(pin.get("name") or "").strip() or None,
            "address": str(pin.get("address") or "").strip() or None,
        }
    except (TypeError, ValueError):
        return None


def _extract_instagram_location(
    message: dict[str, Any],
) -> tuple[dict[str, Any] | None, bool]:
    """Return an Instagram location and whether a pin arrived without data.

    Instagram webhook payloads vary by client. Some expose a normal location
    attachment with coordinates; the current mobile client has also been seen
    live sending an empty generic-template attachment for a shared pin. The
    latter must not be mistaken for a normal image or silently accepted as a
    saved location.
    """
    attachments = message.get("attachments") or []
    for attachment in attachments:
        payload = attachment.get("payload") or {}
        candidates = (
            payload.get("coordinates"), payload.get("location"), payload,
            attachment.get("coordinates"), attachment.get("location"),
        )
        for candidate in candidates:
            if not isinstance(candidate, dict):
                continue
            latitude = candidate.get("latitude", candidate.get("lat"))
            longitude = candidate.get(
                "longitude", candidate.get("lng", candidate.get("long")),
            )
            if latitude is None or longitude is None:
                continue
            try:
                lat, lng = float(latitude), float(longitude)
            except (TypeError, ValueError):
                continue
            if -90 <= lat <= 90 and -180 <= lng <= 180:
                return ({
                    "latitude": lat,
                    "longitude": lng,
                    "name": str(candidate.get("name") or "").strip() or None,
                    "address": str(candidate.get("address") or "").strip() or None,
                    "source": "instagram_pin",
                }, False)

        # Observed from a real Instagram location share: Meta labels the
        # attachment as a generic template but supplies no element at all.
        generic = payload.get("generic")
        if (
            attachment.get("type") in {"location", "template"}
            and isinstance(generic, dict)
            and generic.get("elements") == []
        ):
            return None, True
        if attachment.get("type") == "location":
            return None, True
    return None, False


def _extract_reply_id(m: dict[str, Any], mtype: str) -> str | None:
    """The option id behind a tap, or None when the customer typed.

    WhatsApp puts it under `interactive.list_reply.id` / `button_reply.id`;
    the older `button` type (template quick replies) carries it as `payload`.
    """
    if mtype == "interactive":
        inter = m.get("interactive") or {}
        for key in ("button_reply", "list_reply"):
            if inter.get(key):
                return str(inter[key].get("id") or "").strip() or None
    if mtype == "button":
        return str((m.get("button") or {}).get("payload") or "").strip() or None
    return None


def _extract_flow_response(
    m: dict[str, Any], mtype: str,
) -> dict[str, Any] | None:
    """Parse a completed WhatsApp Flow response without trusting its fields."""
    if mtype != "interactive":
        return None
    interactive = m.get("interactive") or {}
    if interactive.get("type") != "nfm_reply":
        return None
    encoded = (interactive.get("nfm_reply") or {}).get("response_json")
    if not isinstance(encoded, str) or not encoded.strip():
        return None
    try:
        parsed = json.loads(encoded)
    except (TypeError, ValueError, json.JSONDecodeError):
        return None
    return parsed if isinstance(parsed, dict) else None


async def send_text(
    to: str,
    text: str,
    *,
    channel: str = CHANNEL_WHATSAPP,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Send a plain text reply.

    Only valid inside the 24-hour customer service window; a business-initiated
    message outside it must use an approved template and will be rejected here
    by Meta with a 131047-class error. Reminders and confirmation prompts are
    therefore template sends, not this call.
    """
    endpoint = _endpoint(channel, config)
    if not endpoint:
        logger.warning("messaging_gateway.send.not_configured", channel=channel)
        return {"sent": False, "reason": "channel_not_configured"}
    url, token = endpoint

    body = text.strip()
    chunk_size = min(MAX_OUTBOUND_CHARS, 900) if channel == CHANNEL_INSTAGRAM else MAX_OUTBOUND_CHARS
    if len(body) > chunk_size:
        # Financial summaries must not silently lose selected line items.
        result = {'sent': True}
        for offset in range(0, len(body), chunk_size):
            result = await send_text(to, body[offset:offset + chunk_size], channel=channel, config=config)
            if not result.get('sent'):
                return result
        return result

    if channel == CHANNEL_INSTAGRAM:
        payload = {"recipient": {"id": to}, "message": {"text": body}}
    else:
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "text",
            "text": {"preview_url": False, "body": body},
        }
    return await _post(url, token, payload)


def _endpoint(channel: str, config: dict[str, Any] | None) -> tuple[str, str] | None:
    """The Graph `/messages` URL and bearer token for a channel, or None."""
    cfg = dict(config or {})
    token = str(cfg.get("access_token") or _cfg("META_ACCESS_TOKEN")).strip()
    api_version = str(cfg.get("api_version") or DEFAULT_GRAPH_API_VERSION).strip()
    if not api_version.startswith("v"):
        api_version = f"v{api_version}"
    if channel == CHANNEL_INSTAGRAM:
        business_id = str(cfg.get("instagram_account_id") or "").strip()
        host = INSTAGRAM_GRAPH_HOST
    else:
        business_id = str(
            cfg.get("phone_number_id") or _cfg("META_PHONE_NUMBER_ID") or ""
        ).strip()
        host = FACEBOOK_GRAPH_HOST
    if not token or not business_id:
        return None
    return f"{host}/{api_version}/{business_id}/messages", token


async def _post(url: str, token: str, payload: dict[str, Any]) -> dict[str, Any]:
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                url, headers={"Authorization": f"Bearer {token}"}, json=payload,
            )
        ok = resp.status_code < 400
        if not ok:
            body = _safe_json(resp.text)
            code = (body or {}).get("error", {}).get("code") if isinstance(body, dict) else None
            if code == 190 or resp.status_code == 401:
                # An expired or revoked token looks exactly like a dead bot
                # from the outside: inbound is processed normally and every
                # reply is silently rejected. Say so plainly in the log — this
                # is a credential to rotate, not a code path to debug.
                logger.error("messaging_gateway.token_rejected",
                             status=resp.status_code, body=resp.text[:200],
                             action="rotate the channel access token")
            else:
                logger.warning("messaging_gateway.send.failed",
                               status=resp.status_code, body=resp.text[:400])
        return {"sent": ok, "status": resp.status_code,
                "response": _safe_json(resp.text)}
    except Exception as exc:  # network/timeout — never break inbound handling
        logger.warning("messaging_gateway.send.exception", error=str(exc))
        return {"sent": False, "reason": "transport_error"}


async def send_options(
    to: str,
    body: str,
    rows: list[dict[str, str]],
    *,
    channel: str = CHANNEL_WHATSAPP,
    config: dict[str, Any] | None = None,
    list_button: str = "Choose",
    section_title: str | None = None,
    presentation: str | None = None,
    flow: dict[str, Any] | None = None,
    card: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Send a tappable option set - the in-chat equivalent of a picker screen.

    `rows` are `{"id", "title", "description"?}` in display order, already
    trimmed to the channel's cap by the caller (see `pickers.py`); everything
    here does is pick the widest-supported Meta shape for that many options and
    truncate to Meta's field limits, because Meta rejects the whole message —
    it does not trim — when a title runs long.

    WhatsApp gets reply buttons for up to three options and a list beyond that.
    Instagram uses a generic carousel for catalog browsing, a button template
    for durable actions of up to three choices, and quick replies for transient
    questions. Longer quick-reply sets also include a visible numbered fallback.
    """
    endpoint = _endpoint(channel, config)
    if not endpoint:
        logger.warning("messaging_gateway.send.not_configured", channel=channel)
        return {"sent": False, "reason": "channel_not_configured"}
    url, token = endpoint

    rows = [r for r in rows if str(r.get("id") or "").strip()]
    if not rows:
        return {"sent": False, "reason": "no_options"}
    text = (body or "").strip()[:MAX_INTERACTIVE_BODY_CHARS] or "Please choose:"

    if channel == CHANNEL_WHATSAPP and presentation == "flow" and flow:
        parameters: dict[str, Any] = {
            "flow_message_version": "3",
            "flow_action": "navigate",
            "flow_token": str(flow.get("token") or ""),
            "flow_id": str(flow.get("id") or ""),
            "flow_cta": _clip(str(flow.get("cta") or "Complete booking"), 20),
            "flow_action_payload": {
                "screen": str(flow.get("screen") or "BOOKING_SLOT"),
                "data": dict(flow.get("data") or {}),
            },
        }
        if parameters["flow_id"] and parameters["flow_token"]:
            sent_flow = await _post(url, token, {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": to,
                "type": "interactive",
                "interactive": {
                    "type": "flow",
                    "body": {"text": text},
                    "footer": {"text": "If this form does not open, reply TIMES."},
                    "action": {"name": "flow", "parameters": parameters},
                },
            })
            if sent_flow.get("sent"):
                sent_flow["flow_sent"] = True
                return sent_flow
            logger.warning("messaging_gateway.flow.send_failed_using_list",
                           reason=sent_flow.get("reason"), status=sent_flow.get("status"))
        # A bad/unpublished Flow must not strand a customer. Fall through to
        # the same list picker that would have been sent with Flows disabled.

    if channel == CHANNEL_INSTAGRAM and presentation == "status_card" and card:
        # A single generic-template element gives tracking a visual identity
        # and keeps the actions attached to the booking they operate on.
        element: dict[str, Any] = {
            "title": _clip(str(card.get("title") or "Booking status"),
                           IG_GENERIC_TITLE_CHARS),
            "subtitle": _clip(str(card.get("subtitle") or text),
                              IG_GENERIC_SUBTITLE_CHARS),
            "buttons": [
                {"type": "postback",
                 "title": _clip(str(row.get("title") or "Choose"),
                                WA_BUTTON_TITLE_CHARS),
                 "payload": row["id"]}
                for row in rows[:MAX_WA_BUTTONS]
            ],
        }
        image_url = str(card.get("image_url") or "").strip()
        if image_url.startswith("https://"):
            element["image_url"] = image_url
        return await _post(url, token, {
            "recipient": {"id": to},
            "message": {"attachment": {"type": "template", "payload": {
                "template_type": "generic",
                "image_aspect_ratio": "square",
                "elements": [element],
            }}},
        })

    if channel == CHANNEL_INSTAGRAM and presentation == "carousel":
        elements = []
        for row in rows[:MAX_IG_GENERIC_ELEMENTS]:
            title = _clip(str(row.get("title") or "Choose"), IG_GENERIC_TITLE_CHARS)
            subtitle = _clip(
                str(row.get("description") or "Tap below to choose this service."),
                IG_GENERIC_SUBTITLE_CHARS,
            )
            element: dict[str, Any] = {
                "title": title,
                "subtitle": subtitle,
                "buttons": [{
                    "type": "postback",
                    "title": _clip(str(row.get("button_title") or "Select"),
                                   WA_BUTTON_TITLE_CHARS),
                    "payload": row["id"],
                }],
            }
            image_url = str(row.get("image_url") or "").strip()
            if image_url.startswith("https://"):
                element["image_url"] = image_url
            elements.append(element)
        return await _post(url, token, {
            "recipient": {"id": to},
            "message": {"attachment": {"type": "template", "payload": {
                "template_type": "generic",
                "image_aspect_ratio": "square",
                "elements": elements,
            }}},
        })

    if (channel == CHANNEL_INSTAGRAM and presentation == "buttons"
            and len(rows) <= MAX_WA_BUTTONS):
        # Instagram's only STACKED control is the button template, and it caps
        # at three. Short durable sets - confirmation and closure cards - get it,
        # because three buttons in a column read far better than three chips
        # in a scrolling strip. Longer sets fall through to the list below.
        return await _post(url, token, {
            "recipient": {"id": to},
            "message": {"attachment": {"type": "template", "payload": {
                "template_type": "button",
                "text": text,
                "buttons": [
                    {"type": "postback",
                     "title": _clip(r["title"], WA_BUTTON_TITLE_CHARS),
                     "payload": r["id"]}
                    for r in rows
                ],
            }}},
        })

    if channel == CHANNEL_INSTAGRAM:
        # Both, because neither alone is enough: Instagram has no list message,
        # its quick replies render as one horizontal strip that scrolls out of
        # view, and a text-only list cannot be tapped. So the numbered lines
        # make every option readable, and the same options ride along as
        # tappable chips - whichever the customer uses, `flow` resolves it.
        lines = []
        heading = None
        for i, r in enumerate(rows, start=1):
            # Instagram has no section headings, so a change of group is
            # announced inline - otherwise a standard and an emergency slot
            # look identical in a numbered list.
            if r.get("section") and r["section"] != heading:
                heading = r["section"]
                lines.append("" if len(lines) == 0 else " ")
                lines.append(heading + ":")
            suffix = f" ({r['description']})" if r.get("description") else ""
            lines.append(f"{i}. {r['title']}{suffix}")
        lines = [l for l in lines if l != ""]
        # Short, transient choices are clean quick-reply chips. Longer sets
        # retain the numbered fallback because chips scroll off-screen and are
        # currently unavailable in Instagram's desktop client.
        numbered = len(rows) > 5 or any(r.get("section") for r in rows)
        joined = (text if not numbered else
                  (chr(10) + chr(10)).join([text, chr(10).join(lines)]))
        result = await _post(url, token, {
            "recipient": {"id": to},
            "message": {
                "text": joined,
                "quick_replies": [
                    {
                        "content_type": "text",
                        "title": _clip(r["title"], WA_BUTTON_TITLE_CHARS),
                        "payload": r["id"],
                    }
                    for r in rows[:MAX_IG_QUICK_REPLIES]
                ],
            },
        })
        result["numbered_options"] = numbered
        return result
    if len(rows) <= MAX_WA_BUTTONS:
        interactive: dict[str, Any] = {
            "type": "button",
            "body": {"text": text},
            "action": {
                "buttons": [
                    {"type": "reply", "reply": {
                        "id": r["id"],
                        "title": _clip(r["title"], WA_BUTTON_TITLE_CHARS),
                    }}
                    for r in rows
                ]
            },
        }
    else:
        interactive = {
            "type": "list",
            "body": {"text": text},
            "action": {
                "button": _clip(list_button, WA_BUTTON_TITLE_CHARS),
                "sections": _sections(rows[:MAX_WA_LIST_ROWS], section_title),
            },
        }
    return await _post(url, token, {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to,
        "type": "interactive",
        "interactive": interactive,
    })


async def send_cta_url(
    to: str,
    body: str,
    display_text: str,
    target_url: str,
    *,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Send one in-session WhatsApp URL action, restricted to HTTPS targets."""
    endpoint = _endpoint(CHANNEL_WHATSAPP, config)
    url_value = str(target_url or "").strip()
    if not endpoint:
        return {"sent": False, "reason": "channel_not_configured"}
    if not url_value.startswith("https://"):
        return {"sent": False, "reason": "invalid_cta_url"}
    url, token = endpoint
    return await _post(url, token, {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to,
        "type": "interactive",
        "interactive": {
            "type": "cta_url",
            "body": {"text": (body or "Open the link below.")[:MAX_INTERACTIVE_BODY_CHARS]},
            "action": {
                "name": "cta_url",
                "parameters": {
                    "display_text": _clip(display_text, WA_BUTTON_TITLE_CHARS),
                    "url": url_value,
                },
            },
        },
    })


async def sync_instagram_profile(config: dict[str, Any]) -> dict[str, Any]:
    """Publish the entry-point icebreakers for the configured IG account.

    This is deliberately an explicit admin action. Saving credentials or
    deploying code must never silently rewrite a live Instagram profile.
    """
    endpoint = _endpoint(CHANNEL_INSTAGRAM, config)
    if not endpoint:
        return {"sent": False, "reason": "channel_not_configured"}
    message_url, token = endpoint
    profile_url = message_url.rsplit("/messages", 1)[0] + "/messenger_profile"
    return await _post(profile_url, token, {
        "platform": "instagram",
        "ice_breakers": list(INSTAGRAM_ICEBREAKERS),
    })


def _sections(rows: list[dict[str, str]], default_title: str | None) -> list[dict]:
    """Group rows under their own headings, preserving order.

    A row may name a `section` ("Standard slots", "Emergency +₹200"); rows
    that do not all fall under one heading. WhatsApp renders each heading in
    the list, which is what lets one message show two kinds of slot without
    the customer having to toggle between them.
    """
    grouped: list[dict] = []
    for row in rows:
        title = _clip(row.get("section") or default_title or "Options",
                      WA_ROW_TITLE_CHARS)
        if not grouped or grouped[-1]["title"] != title:
            grouped.append({"title": title, "rows": []})
        grouped[-1]["rows"].append({
            "id": row["id"],
            "title": _clip(row["title"], WA_ROW_TITLE_CHARS),
            **({"description": _clip(row["description"], WA_ROW_DESCRIPTION_CHARS)}
               if row.get("description") else {}),
        })
    return grouped


def _clip(value: str, limit: int) -> str:
    """Meta rejects an over-long title outright, so clip rather than risk it."""
    text = " ".join(str(value or "").split())
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


async def test_connection(
    channel: str, config: dict[str, Any],
) -> tuple[bool, str, list[str]]:
    """Validate the token against the configured Meta business identity.

    Returns (passed, message, alternate_ids) — the alternates being the OTHER
    identifiers Meta may use for the very same account in an inbound webhook.
    """
    token = str(config.get("access_token") or "").strip()
    api_version = str(config.get("api_version") or DEFAULT_GRAPH_API_VERSION).strip()
    if not api_version.startswith("v"):
        api_version = f"v{api_version}"
    if channel == CHANNEL_INSTAGRAM:
        business_id = str(config.get("instagram_account_id") or "").strip()
        # `user_id` is the SAME account under its other identifier. Instagram
        # uses both: the app-scoped id addresses the send API, while a webhook
        # may name the account by its professional-account id. Fetching it here
        # is what lets inbound events be matched to this channel.
        host, fields = INSTAGRAM_GRAPH_HOST, "id,username,user_id"
    else:
        business_id = str(config.get("phone_number_id") or "").strip()
        host, fields = FACEBOOK_GRAPH_HOST, "id,display_phone_number,verified_name"
    if not token or not business_id:
        return False, "Access token and business account identifier are required.", []
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(
                f"{host}/{api_version}/{business_id}",
                headers={"Authorization": f"Bearer {token}"},
                params={"fields": fields},
            )
        if response.status_code >= 400:
            return False, f"Meta rejected the configuration (HTTP {response.status_code}).", []
        result = _safe_json(response.text)
        if not isinstance(result, dict) or str(result.get("id") or "") != business_id:
            return False, "Meta returned a different business account. Check the account ID.", []
        label = result.get("username") or result.get("verified_name") or result.get("display_phone_number") or business_id
        if channel == CHANNEL_WHATSAPP:
            flow_id = str(config.get("booking_flow_id") or "").strip()
            if flow_id:
                async with httpx.AsyncClient(timeout=15.0) as client:
                    flow_response = await client.get(
                        f"{FACEBOOK_GRAPH_HOST}/{api_version}/{flow_id}",
                        headers={"Authorization": f"Bearer {token}"},
                        params={"fields": "id,name,status,validation_errors,whatsapp_business_account"},
                    )
                if flow_response.status_code >= 400:
                    return False, (
                        f"WhatsApp is connected, but Meta rejected booking Flow "
                        f"{flow_id} (HTTP {flow_response.status_code})."
                    ), []
                flow_result = _safe_json(flow_response.text)
                flow_status = str((flow_result or {}).get("status") or "").upper()
                if flow_status != "PUBLISHED":
                    return False, (
                        f"WhatsApp is connected, but booking Flow {flow_id} is "
                        f"{flow_status or 'not published'}. Publish it before enabling."
                    ), []
                flow_waba = (flow_result or {}).get("whatsapp_business_account") or {}
                flow_waba_id = str(
                    flow_waba.get("id") if isinstance(flow_waba, dict) else flow_waba
                    or ""
                )
                expected_waba = str(config.get("business_account_id") or "").strip()
                if expected_waba and flow_waba_id and flow_waba_id != expected_waba:
                    return False, "The booking Flow belongs to a different WhatsApp Business Account.", []
                label = f"{label}; booking Flow {(flow_result or {}).get('name') or flow_id} is published"
        alternate = str(result.get("user_id") or "").strip()
        return True, f"Connected to {label}.", ([alternate] if alternate else [])
    except Exception as exc:
        return False, f"Connection failed: {str(exc)[:300]}", []


def _safe_json(text: str) -> Any:
    try:
        return json.loads(text)
    except Exception:
        return text[:400]
