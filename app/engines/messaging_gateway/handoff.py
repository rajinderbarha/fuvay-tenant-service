"""Chat -> web handoff — redemption only.

Every step that once needed a web screen — picking a type, a brand, a slot —
is now asked and answered inside the chat itself (see `flow.py`), so nothing
issues these links any more and there is no customer web surface to send
anyone to. `redeem_link` remains so that a token minted before that change
still burns correctly rather than 404ing.

The token is single-use, short-lived and hashed — deliberately the same shape
as `media_signed_links`, which this codebase already uses for signed media
access.
"""
from __future__ import annotations

import hashlib

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

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
