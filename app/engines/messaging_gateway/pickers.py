"""In-chat pickers — the customer app's choice screens, rendered as taps.

A booking step that is a pick-list is not a sentence, and WhatsApp can render
one: an interactive list shows ten labelled rows and returns the exact option
id the customer tapped.

So this module renders the SAME option sets the customer app renders, from the
same sources of truth, and applies the tap through the same services:

    offering type / brand / every catalog question
        `QuestionFlowService.get_current_question` -> `submit_answer`
    the slot grid
        `HomeServiceChatbotBookingService.list_available_slots`
        -> `select_promised_slot`

Nothing here decides what to ask or which answers are valid — the question flow
already resolves that deterministically, and `submit_answer` re-validates every
option id against the freshly resolved question. A tap is exactly as trusted as
a tap in the app: not at all.

Row ids are self-describing (`qf|<question_id>|<option_id>`), so no "what did I
last ask?" state is kept anywhere. A tap on a message from yesterday, a
redelivered webhook and a resumed conversation all resolve identically — and a
question that is no longer applicable fails closed in `submit_answer` with a
422 the customer sees as a plain "that has moved on, here's the current step".
"""
from __future__ import annotations

import uuid
import structlog

from app.engines.messaging_gateway.constants import (
    CHANNEL_INSTAGRAM, MAX_IG_STACKED_OPTIONS, MAX_WA_LIST_ROWS,
    PICK_MORE, PICK_QUESTION, PICK_RESTART, PICK_SLOT,
    PICKER_PREFIXES, PICKER_SEP, SLOT_EMERGENCY_FLAG,
)
from app.exceptions import ServiceOSException

logger = structlog.get_logger(__name__)

#: One row of every page is spent on "Show more", so a page holds one fewer.
_MORE_TITLE = "Show more ▸"

#: Weekday/day-month labels read better than an ISO date in a 24-character row.
_DAY_FORMAT = "%a %d %b"

_SECTION_STANDARD = "Standard slots"


def _section_emergency(surcharge: str | None) -> str:
    """Emergency slots are grouped under their own heading, priced."""
    return f"Emergency {surcharge}" if surcharge else "Emergency (sooner)"

#: On non-carousel lists, so a customer is never more than one tap from
#: beginning again. Instagram image carousels deliberately omit this row:
#: Meta renders it as another full-size card beside the real services.
_RESTART_ROW = {
    "id": PICK_RESTART + PICKER_SEP + "1", "title": "Start over",
    "button_title": "Start over",
    # Generic-template cards need their own explanatory copy.  Without it,
    # Instagram rendered the navigation card differently from the catalog
    # cards (and the customer could not tell what the card would do).
    "description": "Begin again from the first question.",
}


def channel_capacity(channel: str) -> int:
    """How many option rows this channel can render in one message."""
    return MAX_IG_STACKED_OPTIONS if channel == CHANNEL_INSTAGRAM else MAX_WA_LIST_ROWS


def is_picker_reply(reply_id: str | None) -> bool:
    """True when an inbound tap is one of ours rather than a template button."""
    if not reply_id:
        return False
    return reply_id.split(PICKER_SEP, 1)[0] in PICKER_PREFIXES


# ── Building ─────────────────────────────────────────────────────────────────


async def build_picker(
    db,
    draft: dict | None,
    *,
    customer_id: uuid.UUID | None,
    channel: str,
    page: int = 0,
    emergency: bool = False,
    capacity_override: int | None = None,
) -> dict | None:
    """The picker for whatever the draft is currently blocked on, or None.

    Returns `{"body", "rows", "list_button", "section_title"}`. None means
    there is nothing to pick right now — the conversation carries on in words.
    """
    if not draft or not draft.get("id"):
        return None
    draft_id = uuid.UUID(str(draft["id"]))

    if not emergency:
        picker = await _question_picker(db, draft_id, customer_id, channel, page)
        if picker:
            return picker
    return await _slot_picker(
        db, draft, draft_id, customer_id, channel, page,
        emergency=emergency, capacity_override=capacity_override,
    )


async def _question_picker(
    db, draft_id: uuid.UUID, customer_id: uuid.UUID | None, channel: str, page: int,
) -> dict | None:
    """The current catalog question, when it is a choice between known options.

    A free-text or photo question has nothing to tap, so `flow` asks for it in
    words instead.
    """
    from app.engines.home_service_booking.question_flow_service import QuestionFlowService

    try:
        envelope = await QuestionFlowService(db).get_current_question(draft_id, customer_id)
    except ServiceOSException as exc:
        # No job type resolved yet, offering withdrawn, draft not visible —
        # all real states where there is simply no question to render.
        logger.info("messaging_gateway.picker.no_question",
                    draft_id=str(draft_id), error_code=getattr(exc, "error_code", None))
        return None

    question = envelope.get("current_question")
    if not question:
        return None
    options = question.get("options") or []
    if not options or question.get("question_type") not in ("single_select", "multi_select"):
        return None

    rows = [
        {"id": _join(PICK_QUESTION, question["question_id"], str(o["id"])),
         "title": str(o.get("label") or "")}
        for o in options
        if o.get("id")
    ]
    body = str(question.get("text") or "Please choose:")
    if question.get("help_text"):
        body = f"{body}\n{question['help_text']}"
    return _paginate(rows, body, channel, page, kind=PICK_QUESTION,
                     list_button="Choose", section_title=body)


async def _slot_picker(
    db, draft: dict, draft_id: uuid.UUID, customer_id: uuid.UUID | None,
    channel: str, page: int, emergency: bool = False,
    capacity_override: int | None = None,
) -> dict | None:
    """Every bookable time in ONE list: standard first, then emergency.

    Emergency booking waives the provider's notice period down to "the slot
    has not started yet" — but only for a provider who opted in, and it never
    invents capacity, so the emergency walk returns the standard slots plus
    the near-term ones the notice period was hiding. Those extra slots are the
    only ones that carry the surcharge, and they say so on the row: an
    emergency must never be a surprise line on the final bill.
    """
    if draft.get("preferred_date") and not emergency:
        return None  # already chosen; nothing to pick
    if 'required_fields' in draft and 'preferred_date' not in draft['required_fields']:
        return None  # The saved workflow does not ask for a scheduled slot.
    if not draft.get("selected_tenant_id") and not draft.get("selected_provider_snapshot"):
        return None  # no provider yet — `list_available_slots` would be empty

    from app.engines.home_service_booking.service import HomeServiceChatbotBookingService

    service = HomeServiceChatbotBookingService(db)
    try:
        standard = await service.list_available_slots(
            draft_id=draft_id, customer_id=customer_id, emergency=False,
        )
    except Exception as exc:
        logger.warning("messaging_gateway.picker.slots_failed",
                       draft_id=str(draft_id), error=str(exc))
        return None

    rows = _slot_rows(standard.get("slots") or [], emergency=False,
                      section=_SECTION_STANDARD)
    known = {r["id"] for r in rows}

    urgent_rows: list[dict] = []
    if await _emergency_allowed(db, draft):
        surcharge = await _emergency_surcharge(service, draft_id, customer_id)
        try:
            urgent = await service.list_available_slots(
                draft_id=draft_id, customer_id=customer_id, emergency=True,
            )
        except Exception as exc:
            logger.warning("messaging_gateway.picker.emergency_slots_failed",
                           draft_id=str(draft_id), error=str(exc))
            urgent = {"slots": []}
        urgent_rows = [
            row for row in _slot_rows(urgent.get("slots") or [], emergency=True,
                                      section=_section_emergency(surcharge),
                                      note=surcharge)
            # Only what the shorter notice actually unlocks. A slot already in
            # the standard list is not an emergency and must not be surcharged.
            if _join(PICK_SLOT, *row["id"].split(PICKER_SEP)[1:3]) not in known
        ]

    if not rows and not urgent_rows:
        return None
    return _paginate(rows + urgent_rows, "Pick a time that suits you:", channel,
                     page, kind=PICK_SLOT, list_button="Pick a time",
                     section_title=_SECTION_STANDARD,
                     capacity_override=capacity_override)


async def _emergency_surcharge(service, draft_id: uuid.UUID,
                               customer_id: uuid.UUID | None) -> str | None:
    """What the provider charges for an emergency visit, if anything."""
    from app.engines.home_service_booking.models import HomeServiceBookingDraft

    try:
        draft = await service.db.get(HomeServiceBookingDraft, draft_id)
        value = await service._emergency_surcharge_for(draft) if draft else None
    except Exception as exc:
        logger.warning("messaging_gateway.picker.surcharge_failed",
                       draft_id=str(draft_id), error=str(exc))
        return None
    return f"+₹{value}" if value else None


def _slot_rows(slots: list[dict], emergency: bool, section: str,
               note: str | None = None) -> list[dict]:
    """Slot rows, grouped under a heading and priced when they carry a cost.

    An emergency row is flagged in its id so the tap itself records which list
    it came from — `select_promised_slot(emergency=...)` is what writes
    `is_emergency` and applies the surcharge, and it must never be guessed
    from what happened to be on screen.
    """
    rows = []
    for slot in slots:
        date_iso = str(slot.get("date") or "")
        window = str(slot.get("time_window") or "")
        if not date_iso or not window:
            continue
        parts = [PICK_SLOT, date_iso, window]
        if emergency:
            parts.append(SLOT_EMERGENCY_FLAG)
        rows.append({
            "id": _join(*parts),
            "title": f"{_day_label(date_iso)} {window}",
            "description": " · ".join(filter(None, [note if emergency else None,
                f"{slot['available_slots']} slots available" if slot.get("available_slots") is not None else None])) or None,
            "section": section,
        })
    return rows


async def _emergency_allowed(db, draft: dict) -> bool:
    """Whether this provider offers emergency booking at all.

    Only the provider's own opt-in is checked, exactly as the app's toggle
    does. Comparing the two slot lists first would be more precise but costs a
    second full availability walk on every slot turn, and the emergency list
    can only ever be a superset — so the toggle can never mislead about
    capacity, at worst it opens a list with nothing extra in it.
    """
    from app.engines.home_service_booking.provider_slot_service import booking_window_settings

    tenant_id = draft.get("selected_tenant_id")
    if not tenant_id:
        return False
    try:
        settings = await booking_window_settings(db, uuid.UUID(str(tenant_id)))
    except Exception as exc:
        logger.warning("messaging_gateway.picker.window_settings_failed",
                       draft_id=str(draft.get("id")), error=str(exc))
        return False
    return bool(settings.get("emergency_booking_allowed"))


def _paginate(
    rows: list[dict], body: str, channel: str, page: int, *,
    kind: str, list_button: str, section_title: str,
    more_context: str = "", reserve: int = 0,
    presentation: str = "quick_replies", capacity_override: int | None = None,
) -> dict | None:
    """Cut `rows` to one channel-sized page, appending a "Show more" row.

    Meta caps a list at ten rows and drops nothing gracefully — an eleventh row
    fails the whole send — so a long brand list has to page rather than
    silently lose its tail.
    """
    # Instagram renders every generic-template row as a full-size card. A
    # navigation-only "Start over" card looks like another service and wastes
    # scarce carousel space, so those customers use the /fuvay command instead.
    # WhatsApp and Instagram's non-carousel pickers keep the convenient row.
    include_restart = not (
        channel == CHANNEL_INSTAGRAM and presentation == "carousel"
    )
    capacity = (
        (capacity_override or channel_capacity(channel))
        - reserve
        - (1 if include_restart else 0)
    )
    if not rows:
        return None
    page = max(0, page)
    if len(rows) <= capacity:
        window, has_more = rows, False
    else:
        per_page = capacity - 1  # one row is spent on "Show more"
        start = page * per_page
        if start >= len(rows):
            start, page = 0, 0
        window = rows[start:start + per_page]
        has_more = (start + per_page) < len(rows)
        if not window:
            return None
    if has_more:
        # The next page must be renderable from the tap alone, so a list whose
        # contents depend on an earlier choice (the offerings of a category)
        # carries that choice in the row id rather than in remembered state.
        more_id = _join(PICK_MORE, kind, str(page + 1))
        if more_context:
            more_id = _join(more_id, more_context)
        window = window + [{"id": more_id, "title": _MORE_TITLE,
                            "button_title": "Show more"}]
    picker_rows = window + ([dict(_RESTART_ROW)] if include_restart else [])
    return {
        "body": body,
        "rows": picker_rows,
        "list_button": list_button,
        "section_title": section_title,
        "presentation": presentation,
    }


# ── Applying a tap ───────────────────────────────────────────────────────────


async def apply_reply(
    db,
    reply_id: str,
    draft: dict | None,
    *,
    customer_id: uuid.UUID | None,
) -> dict:
    """Apply one tapped option to the draft.

    Returns `{"applied": bool, "note": str | None, "page": int}`. `note` is a
    sentence for the customer when something needs saying — a rejected option,
    a slot that has just gone. `page` asks the caller to render that page of
    the current picker instead of the first.

    Never raises: a tap that no longer makes sense must still leave the
    customer with a usable next step.
    """
    kind, _, remainder = reply_id.partition(PICKER_SEP)

    if kind == PICK_MORE:
        _, _, page = remainder.partition(PICKER_SEP)
        return {"applied": False, "note": None, "page": _int(page)}

    if not draft or not draft.get("id"):
        return {"applied": False, "note": None, "page": 0}
    draft_id = uuid.UUID(str(draft["id"]))

    if kind == PICK_QUESTION:
        question_id, _, option_id = remainder.partition(PICKER_SEP)
        return await _apply_question(db, draft_id, customer_id, question_id, option_id)

    if kind == PICK_SLOT:
        date_iso, _, tail = remainder.partition(PICKER_SEP)
        window, _, flag = tail.partition(PICKER_SEP)
        return await _apply_slot(db, draft_id, customer_id, date_iso, window,
                                 emergency=flag == SLOT_EMERGENCY_FLAG)

    return {"applied": False, "note": None, "page": 0}


async def _apply_question(
    db, draft_id: uuid.UUID, customer_id: uuid.UUID | None,
    question_id: str, option_id: str,
) -> dict:
    from app.engines.home_service_booking.question_flow_service import QuestionFlowService

    if not question_id or not option_id:
        return {"applied": False, "note": None, "page": 0}
    try:
        await QuestionFlowService(db).submit_answer(
            draft_id=draft_id, customer_id=customer_id,
            question_id=question_id, option_id=option_id,
        )
        return {"applied": True, "note": None, "page": 0}
    except ServiceOSException as exc:
        # The question moved on (already answered, or a rule now hides it).
        # Saying so plainly beats re-asking something that no longer applies.
        logger.info("messaging_gateway.picker.answer_rejected",
                    draft_id=str(draft_id),
                    error_code=getattr(exc, "error_code", None))
        return {"applied": False,
                "note": "That step has already moved on — here is where we are now.",
                "page": 0}
    except Exception as exc:
        logger.warning("messaging_gateway.picker.answer_failed",
                       draft_id=str(draft_id), error=str(exc))
        return {"applied": False, "note": None, "page": 0}


async def _apply_slot(
    db, draft_id: uuid.UUID, customer_id: uuid.UUID | None,
    date_iso: str, window: str, emergency: bool = False,
) -> dict:
    from app.engines.home_service_booking.service import HomeServiceChatbotBookingService

    if not date_iso or not window:
        return {"applied": False, "note": None, "page": 0}
    try:
        await HomeServiceChatbotBookingService(db).select_promised_slot(
            draft_id=draft_id, customer_id=customer_id,
            date_iso=date_iso, time_window=window, emergency=emergency,
        )
        # Choosing a time on WhatsApp/Instagram updates the draft only.  It
        # neither reserves provider capacity nor creates a booking; only the
        # later confirmation/finalization step does that.  Do not tell the
        # customer the slot is held or booked before that point.
        held = "Emergency time selected" if emergency else "Time selected"
        return {"applied": True,
                "note": f"{held} for {_day_label(date_iso)}, {window}.",
                "page": 0}
    except Exception as exc:
        # `select_promised_slot` deliberately re-checks live capacity rather
        # than trusting the list the customer was looking at.
        logger.info("messaging_gateway.picker.slot_unavailable",
                    draft_id=str(draft_id), error=str(exc))
        return {"applied": False,
                "note": "That time has just been taken. Here are the times still open:",
                "page": 0}


# ── Helpers ──────────────────────────────────────────────────────────────────


def _join(*parts: str) -> str:
    return PICKER_SEP.join(str(p) for p in parts)


def _int(value: str) -> int:
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return 0


def _day_label(date_iso: str) -> str:
    import datetime as dt

    try:
        return dt.date.fromisoformat(date_iso).strftime(_DAY_FORMAT)
    except (TypeError, ValueError):
        return date_iso
