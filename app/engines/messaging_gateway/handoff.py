"""Chat -> web handoff.

Some booking steps are comparison UI, not conversation: choosing between
matched providers, choosing a price option, picking a slot from a grid, and
picking an offering type or brand from a list. Trying to run those in a
WhatsApp thread reads as an interrogation and abandons badly.

So the agent handles what is genuinely conversational and, the moment the draft
reaches one of those steps, the customer gets ONE link into the web surface
carrying their draft.

The link is a single-use, short-lived, hashed token — deliberately the same
shape as `media_signed_links`, which this codebase already uses for signed
media access.
"""
from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings

logger = structlog.get_logger(__name__)

#: Long enough to walk away and come back, short enough that a forwarded
#: WhatsApp message is not a standing key to someone's account.
LINK_TTL_MINUTES = 30

# ── Handoff reasons, in the order they occur in a booking ────────────────
REASON_SELECT_OPTIONS = "select_options"    # offering type / brand — pick lists
REASON_SELECT_SLOT = "select_slot"          # picking from a slot grid

# NOTE: there is deliberately NO "choose a provider" reason. This product does
# not have provider comparison: `match_provider_and_price` picks the provider
# server-side, and `match_providers` auto-selects `providers[0]` in the same
# call that fills `provider_options`. So "options present, none selected" is
# unreachable by either route, and a handoff branch on it would be dead code.

#: Fields the conversation deliberately never asks for. This mirrors
#: `BackendToolExecutor._CHAT_UNASKABLE_FIELDS` rather than re-deciding it —
#: the agent already refuses to ask these, so a draft still missing one is
#: definitionally stuck until a screen collects it.
UNASKABLE_FIELDS = ("offering_type_id", "brand_id")

#: Mirrors `home_service_booking.constants.TERMINAL_DRAFT_STATUSES`, copied
#: rather than imported so this module has no dependency on that engine.
_TERMINAL = {"confirmed", "cancelled", "expired", "failed"}

REASON_TEXT = {
    REASON_SELECT_OPTIONS: "Pick your exact type and brand here so I can price it correctly:",
    REASON_SELECT_SLOT: "Pick a time that suits you:",
}


def detect_handoff(draft: dict | None) -> str | None:
    """Return the handoff reason for a draft, or None to stay in chat.

    Expects the ENRICHED draft dict — `HomeServiceBookingDraft.to_dict()` plus
    a `required_fields` list, which the booking service computes from the
    offering's `is_type_required` / `is_brand_required` / `requires_schedule`
    flags and does NOT store on the row.

    Ordered so the EARLIEST blocking step wins: there is no point sending
    someone to a slot picker when the draft still has no brand.
    """
    if not draft:
        return None
    if str(draft.get("status") or "").lower() in _TERMINAL:
        return None

    required = set(draft.get("required_fields") or [])
    for field in UNASKABLE_FIELDS:
        if field in required and not draft.get(field):
            return REASON_SELECT_OPTIONS

    # Everything the chat can collect is collected; what remains is the slot
    # grid. Note there is deliberately no price handoff either: `price_snapshot`
    # is a single computed estimate, not a set of options to compare.
    if (
        "preferred_date" in required
        and not draft.get("preferred_date")
        and draft.get("selected_provider_snapshot")
    ):
        return REASON_SELECT_SLOT

    return None


def _base_url() -> str:
    """Where the customer web surface lives.

    NOTE: that surface does not exist yet. Until it does this points at the
    configured web origin and the link will 404 — which is why `issue_link`
    returns None when nothing is configured, so the bot never sends a customer
    a link to nowhere.
    """
    s = get_settings()
    return str(getattr(s, "CUSTOMER_WEB_BASE_URL", "") or "").rstrip("/")


async def issue_link(
    db: AsyncSession,
    *,
    thread_id: uuid.UUID | None,
    customer_id: uuid.UUID | None,
    draft_id: uuid.UUID | None,
    reason: str,
    target_path: str = "/booking/resume",
) -> str | None:
    """Mint a single-use handoff URL, or None if the web surface is unconfigured."""
    base = _base_url()
    if not base:
        logger.info("messaging_gateway.handoff.no_web_base_configured", reason=reason)
        return None

    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    expires = datetime.now(timezone.utc) + timedelta(minutes=LINK_TTL_MINUTES)

    await db.execute(text("""
        INSERT INTO messaging_handoff_links
            (token_hash, thread_id, customer_id, draft_id, reason, target_path, expires_at)
        VALUES (:h, :thread, :customer, :draft, :reason, :path, :expires)
    """), {
        "h": token_hash,
        "thread": str(thread_id) if thread_id else None,
        "customer": str(customer_id) if customer_id else None,
        "draft": str(draft_id) if draft_id else None,
        "reason": reason,
        "path": target_path,
        "expires": expires,
    })
    return f"{base}{target_path}?t={token}"


async def redeem_link(db: AsyncSession, token: str) -> dict | None:
    """Validate and burn a handoff token.

    Single-use is enforced by the atomic UPDATE below: two concurrent clicks
    cannot both match `status='active'`, so a forwarded link cannot be used
    twice. Returns None for anything invalid, expired or already used — the
    caller must not distinguish between those for the customer.
    """
    token_hash = hashlib.sha256((token or "").encode("utf-8")).hexdigest()
    row = (await db.execute(text("""
        UPDATE messaging_handoff_links
           SET status = 'used', used_at = now()
         WHERE token_hash = :h
           AND status = 'active'
           AND expires_at > now()
        RETURNING customer_id, draft_id, thread_id, reason, target_path
    """), {"h": token_hash})).fetchone()
    if not row:
        return None
    return {
        "customer_id": str(row.customer_id) if row.customer_id else None,
        "draft_id": str(row.draft_id) if row.draft_id else None,
        "thread_id": str(row.thread_id) if row.thread_id else None,
        "reason": row.reason,
        "target_path": row.target_path,
    }
