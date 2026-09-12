"""The scripted booking flow — admin-defined questions, asked one at a time.

There is no language model anywhere in this module. Every question the
customer sees is a row an admin configured, and every answer is one of the
options that row offers:

    category        ServiceCategory (customer-visible, active)
    offering        offering_catalog_service.list_serviceable_offerings
    problem         ServiceIssueMapping -> MasterIssueType
    details         catalog_questions, resolved by question_flow_service
    address         typed — a pincode and a street are not a pick-list
    slot            provider_slot_service.list_available_slots
    confirmation    HomeServiceFinalCreationService.finalize

Answers are applied through `BackendToolExecutor`, which is the same code path
the app's own booking uses — it is a plain executor of backend calls, not the
agent, so reusing it here keeps one implementation of "start a draft for a
WhatsApp sender", "create the customer at confirmation", and every validation
in between, rather than a second one that can drift.

The step the customer is on is DERIVED from the draft each turn, never stored:
a draft with no problem is on the problem step, one with no pincode is on the
address step. So a tap on an older message, a redelivered webhook and a
conversation resumed tomorrow all resolve to the same place, and there is no
per-thread state to migrate, expire or repair.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from urllib.parse import quote_plus

import structlog
from sqlalchemy import func, select, text

from app.engines.messaging_gateway import pickers
from app.engines.messaging_gateway.constants import (
    CHANNEL_INSTAGRAM, CHANNEL_WHATSAPP, CONFIRM_PHRASE, DIMENSION_DRAFT_FIELD,
    MAX_IG_GENERIC_ELEMENTS,
    PICK_AREA, PICK_AREA_CITY, PICK_CANCEL, PICK_CATEGORY, PICK_DIMENSION,
    PICK_CONFIRM, PICK_DUPLICATE, PICK_EMERGENCY, PICK_MORE, PICK_OFFERING,
    PICK_PROBLEM,
    PICK_HANDOVER, PICK_PARTS, PICK_PAYMENT, PICK_QUESTION, PICK_QUOTE,
    PICK_RATING, PICK_RESTART, PICK_SKIP, PICK_SLOT, PICK_PHONE,
    PICK_TRACK, PICK_ADDON,
    PICKER_SEP, SLOT_EMERGENCY_FLAG,
)
from app.engines.messaging_gateway.pickers import _join
from app.engines.messaging_gateway.dev_identity import instagram_phone_bypass_enabled
from app.engines.messaging_gateway.problem_cards import problem_card_symbol

logger = structlog.get_logger(__name__)

#: Mirrors `home_service_booking.constants.TERMINAL_DRAFT_STATUSES`, copied
#: rather than imported so this module keeps no dependency on that engine.
_TERMINAL = {"confirmed", "cancelled", "expired", "failed"}

# ── What each step says ──────────────────────────────────────────────────────

ASK_CATEGORY = "What do you need help with?"
ASK_OFFERING = "Which service?"
ASK_PROBLEM = "What is the problem?"
#: `label` is the dimension's own name, lowercased — "type", "brand" — so one
#: sentence covers every dimension the blueprint may add later.
ASK_DIMENSION = "Which {label}?"
ASK_AREA = "Where do you need the service?"
ASK_AREA_PINCODE = "Which pincode in {city}?"
#: Only ever shown when the covered-area list cannot be built. Typing a
#: pincode still works, but nobody should have to.
ASK_PINCODE = (
    "First, send the 6-digit pincode where you need the service. "
    "We use it to check service availability."
)
ASK_CITY = "Which city are you in?"
#: An uncovered area is a dead end unless the reply says how to leave it. The
#: flow already re-reads a bare 6-digit reply as a new pincode
#: (`_apply_text`), so the only thing that was missing is saying so — without
#: it every later message was answered with this same sentence.
NOT_IN_CITY = (
    "We do not cover {area} yet.\n\n"
    "Send a different 6-digit pincode to check another area, "
    "or send /fuvay to start again."
)
SERVICE_NOT_IN_CITY = "That service is not available in {city} yet."
ASK_ADDRESS = (
    "Please type the complete service address — flat/house number, building, "
    "street or area, and a nearby landmark."
)
ASK_ADDRESS_WHATSAPP = (
    "Please send the complete service address — flat/house number, building, "
    "street or area, and a nearby landmark. You may share a WhatsApp location "
    "pin instead if it includes the full readable address."
)
BAD_ADDRESS = (
    "Please send a complete service address with at least the house/building "
    "and street or area."
)
LOCATION_SAVED = "Location saved — the technician will see it."
BAD_PINCODE = "That does not look like a pincode. Please send the 6 digits, for example 141001."
NOTHING_HERE = "There is nothing bookable here at the moment."
START_FAILED = (
    "I could not start that booking just now. Please wait a moment and tap "
    "the service again."
)
TOO_MANY_DRAFTS = (
    "You already have several unfinished bookings. Finish or cancel one, "
    "then tap the service again."
)
START_RATE_LIMITED = (
    "There have been too many booking attempts recently. Please wait a little "
    "and tap the service again."
)
#: Distinct from NOTHING_HERE on purpose: "no provider covers YOUR pincode" is
#: a different problem with a different fix, and telling a customer to start
#: over when all they need is a neighbouring pincode wastes the conversation.
NO_COVERAGE = (
    "We do not have a provider covering {zipcode} for this service yet. "
    "Send /fuvay to start again with a different area."
)
NO_SLOTS = (
    "There are no open slots for this service right now. "
    "Please try again later."
)
CONFIRMED = "Booking confirmed. Your booking number is {number}. We will message you when a technician is assigned."
#: A confirmed booking is a commitment on both sides — a provider has been
#: allocated and a technician is being assigned — so it is deliberately NOT
#: editable from chat. Taps on the messages above it must say so plainly
#: rather than silently doing nothing, or appearing to work.
ALREADY_BOOKED = "This booking is already confirmed, so it cannot be changed here."
CONFIRM_FAILED = "That booking could not be completed: {reason}"
DUPLICATE_PROMPT = "Do you still want to book this same problem again?"
DUPLICATE_DECLINED = "No new booking was created."
BOOKED_OPTIONS = "Your booking is with us. What would you like to do?"
#: Header for the same menu when nothing is open — "your booking is with us"
#: over a menu that can only book a new one reads as a booking that exists.
NO_BOOKING_OPTIONS = "What would you like to do?"
NOTHING_OPEN = "You have no booking open right now."
TRACK_ROW = "Track my booking"
NEW_BOOKING_ROW = "Book another service"
NO_BOOKINGS = "There is no booking on this number yet."
CANCEL_ROW = "Cancel booking"
CANCEL_NOT_ALLOWED = (
    "This booking can no longer be cancelled from chat. "
    "Tap Track my booking to see where it has got to."
)
CANCEL_FAILED = "That booking could not be cancelled just now. Please try again."
CANCELLED = "Booking {number} is cancelled."
ASK_CANCEL_REASON = "Why are you cancelling {number}?"
ASK_WHICH_CANCEL = "Which booking do you want to cancel?"
#: The reason codes the booking service accepts, in the words a customer would
#: use. The codes themselves come from the server's eligibility response — this
#: only decides how each is worded on the row.
CANCEL_REASON_LABELS = {
    "changed_mind": "Changed my mind",
    "found_another_provider": "Found another provider",
    "price_concern": "Too expensive",
    "schedule_conflict": "Schedule clash",
    "no_longer_needed": "No longer needed",
    "other": "Another reason",
}
#: A technician has opened up the unit and needs a part. Nothing else in the
#: chat matters until the customer answers: the job is halted waiting for it,
#: and the answer changes what they pay.
PARTS_HEADER = "Your technician needs a part to finish the job."
PARTS_LINE = "{part} × {quantity} — {total}"
PARTS_REASON = "Why: {reason}"
PARTS_TOTALS = "Estimate now {current} → {new} with this part."
#: A part can be requested before any quote exists, in which case there is no
#: "before" to show — quoting ₹0 as the current estimate would be a price we
#: never gave.
PARTS_ADDS = "This adds {total} to your estimate."
PARTS_APPROVE_ROW = "Approve"
PARTS_DECLINE_ROW = "Decline"
PARTS_APPROVED = "Approved. The technician will fit the part and carry on."
PARTS_DECLINED = (
    "Declined. The technician will finish what they can without the part."
)
PARTS_DECIDED_ALREADY = "That parts request has already been answered."
QUOTE_HEADER = "Your provider sent an estimate for this job."
QUOTE_LINE = "Estimate {number}: {total}"
QUOTE_APPROVE_ROW = "Approve estimate"
QUOTE_DECLINE_ROW = "Decline estimate"
QUOTE_REVISE_ROW = "Ask for changes"
QUOTE_APPROVED = "Estimate approved. The technician can continue the job."
QUOTE_DECLINED = "Estimate declined. The provider has been notified."
QUOTE_REVISION_REQUESTED = (
    "Changes requested. The provider will contact you before sending a new estimate."
)
QUOTE_DECIDED_ALREADY = "That estimate is no longer waiting for your decision."
HANDOVER_HEADER = "The technician has submitted the completion proof for your service."
HANDOVER_ACK_ROW = "Confirm handover"
HANDOVER_ACKNOWLEDGED = "Service handover confirmed. The provider can continue closure."
HANDOVER_DECIDED_ALREADY = "That handover is no longer waiting for your confirmation."
PAYMENT_HEADER = "The provider recorded a direct payment for this service."
PAYMENT_NOTICE = "You paid the provider directly. Fuvay did not collect this money."
PAYMENT_CONFIRM_ROW = "Yes, I paid"
PAYMENT_NOT_PAID_ROW = "I did not pay"
PAYMENT_CONFIRMED = "Payment confirmed. The technician can now close the job. Once the work is completed, we will send your rating options and warranty PDF here."
PAYMENT_MISMATCH_REPORTED = "Payment issue reported. The provider must resolve it before closing the job."
PAYMENT_DECIDED_ALREADY = "That payment is no longer waiting for your confirmation."
PAYMENT_NOT_PAID_WARNING = (
    "Report this only if you did not make the payment shown. The provider will "
    "have to resolve the mismatch before the job can close."
)
RESTARTED = "Starting again."
#: A booking has to reach a real person. WhatsApp hands us a number Meta has
#: already verified; every other channel collects one and confirms it by
#: one-time code, as a step of the booking — the booking services refuse to
#: create final records without a verified account, so skipping this would put
#: a Confirm button in front of the customer that fails when tapped.
ASK_PHONE = (
    "Almost done. Send your 10-digit mobile number so we can confirm the "
    "booking and the provider can reach you — for example 9876543210."
)
ASK_TEST_PHONE = (
    "Almost done. Send your 10-digit mobile number so the provider can reach "
    "you. No SMS code is needed during this test. For example: 9876543210."
)
ASK_PHONE_CONFIRM = "Send the OTP to {number}? No OTP is sent until you confirm."
ASK_OTP = (
    "Send the 6-digit OTP we just sent to {number}. "
    "To use a different mobile number, tap Use another number or type the "
    "new 10-digit number."
)
BAD_PHONE = (
    "That does not look like a mobile number. Send the 10 digits, "
    "for example 9876543210."
)

_YES, _NO = "yes", "no"

#: Page sentinels returned by `_apply_tap`. A page of DONE means "this turn is
#: finished, say only this"; BOOKED additionally means a real booking now
#: exists, so the customer is offered what to do with it.
DONE = -1
BOOKED = -2
DUPLICATE_CONFIRM = -3


class Turn:
    """What to send back: a sentence, a picker, or both."""

    __slots__ = ("text", "picker")

    def __init__(self, text: str | None = None, picker: dict | None = None):
        self.text = text
        self.picker = picker


# Meta does not provide an API for a business to hide Instagram's or
# WhatsApp's message composer.  Make picker turns selection-only on the
# server instead: text cannot leak into a later field, and the current choices
# are shown again.  The few pickers that intentionally sit beside a typed
# answer (currently OTP) opt out with ``allow_text``.
TAP_AN_OPTION = "Please tap one of the options shown below to continue."


def _requires_option_tap(turn: Turn) -> bool:
    return bool(turn.picker) and not bool(turn.picker.get("allow_text"))


async def advance(
    db,
    thread,
    *,
    text: str,
    reply_id: str | None,
    channel: str,
    identity=None,
    location: dict | None = None,
    location_unavailable: bool = False,
) -> Turn:
    """Apply whatever the customer just sent, then ask the next question."""
    executor = _executor(db, thread)
    draft = await _draft(db, thread)
    note: str | None = None
    page = 0

    if location and draft and channel == CHANNEL_WHATSAPP:
        note, draft = await _apply_location(db, draft, location)
        draft = await _draft(db, thread)
        step = await _next_step(db, thread, executor, draft, channel, 0, identity)
        step.text = f"{note}\n\n{step.text}" if step.text else note
        return step

    if location_unavailable:
        # Instagram location attachments are intentionally not part of the
        # booking contract. Keep the customer on the normal typed-address flow
        # without suggesting another location mechanism.
        return await _next_step(db, thread, executor, draft, channel, 0, identity)

    if not reply_id:
        # On Instagram the options are a numbered list, so "3" IS a tap. It is
        # resolved against the ids actually sent, so a number means the same
        # thing a tap would have.
        reply_id = await _resolve_numbered_choice(thread, text)

    # A customer can still see and use Meta's composer underneath buttons and
    # cards.  Reconstruct the current step before applying free text; if that
    # step is a picker, do not let the text become an address or another later
    # field.  Numbered WhatsApp replies have already become ``reply_id`` above.
    # TIMES remains the documented escape hatch when a WhatsApp Flow cannot
    # open, and OTP explicitly allows typing alongside its change-number
    # button.
    typed = (text or "").strip()
    whatsapp_times = channel == CHANNEL_WHATSAPP and typed.lower() in {
        "times", "time", "show times", "show time slots",
    }
    if typed and not reply_id and not whatsapp_times:
        current = await _next_step(
            db, thread, executor, draft, channel, 0, identity,
        )
        if _requires_option_tap(current):
            current.text = (
                f"{TAP_AN_OPTION}\n\n{current.text}"
                if current.text else TAP_AN_OPTION
            )
            return current

    if reply_id:
        kind = reply_id.partition(PICKER_SEP)[0]
        if not thread.zipcode and kind not in {
            PICK_RESTART, PICK_AREA, PICK_AREA_CITY, PICK_TRACK, PICK_CANCEL,
            PICK_PARTS, PICK_QUOTE, PICK_HANDOVER, PICK_PAYMENT, PICK_RATING,
        }:
            # Instagram quick replies and buttons on old messages remain
            # tappable. Once a new booking has cleared its area, an old
            # category/service tap must not bypass the zipcode-first gate.
            return Turn(ASK_PINCODE)
        if _is_finished(draft) and kind not in {
            PICK_RESTART, PICK_TRACK, PICK_CANCEL, PICK_PARTS, PICK_QUOTE,
            PICK_HANDOVER, PICK_PAYMENT, PICK_RATING,
        }:
            # Old service cards remain tappable after confirmation. Treat a
            # category/service choice as the start of another booking, which
            # asks for the pincode again before accepting any service input.
            # All other old controls still belong to the confirmed booking.
            if kind in {PICK_CATEGORY, PICK_OFFERING}:
                return await _restart(db, thread, executor, channel, identity)
            return await _booked_menu_for(identity, thread, "", ALREADY_BOOKED)
        # Two taps never touch the draft — they only choose which list to show
        # next — so they are answered directly rather than through the draft.
        direct = await _navigate(db, executor, reply_id, draft, thread, channel,
                                 identity)
        if direct is not None:
            return direct
        note, page, draft = await _apply_tap(db, thread, executor, reply_id, draft)
        if page == DUPLICATE_CONFIRM:
            return Turn(note, {
                "body": DUPLICATE_PROMPT,
                "rows": [
                    {"id": PICKER_SEP.join((PICK_DUPLICATE, str(draft["id"]), _YES)),
                     "title": "Yes, book again"},
                    {"id": PICKER_SEP.join((PICK_DUPLICATE, str(draft["id"]), _NO)),
                     "title": "No, keep existing"},
                ],
                "list_button": "Choose",
                "section_title": "Duplicate booking",
                "presentation": "buttons",
            })
        if note and page == BOOKED:
            # The booking exists now: offer the things a customer with one
            # actually wants, rather than ending the conversation.
            # Do not append the service-location CTA here: confirmation is the
            # end of booking, and showing an address action now looks like a
            # new location question. Location/address is collected beforehand.
            return await _booked_menu_for(identity, thread, "", note)
        if note and page == DONE:
            return Turn(note)
    elif (text or "").strip():
        note, draft = await _apply_text(db, thread, executor, text.strip(), draft,
                                        identity=identity)

    step = await _next_step(db, thread, executor, draft, channel, page, identity)
    if note and step.text:
        step.text = f"{note}\n\n{step.text}"
    elif note:
        step.text = note
    return step


async def _resolve_numbered_choice(thread, text: str) -> str | None:
    """Turn a bare "3" into the id of the third option last offered.

    Resolved against the ids actually SENT, not against a rebuilt step: the
    offerings of a category and every "Show more" page are reachable only
    through an earlier choice, so a rebuild silently resolves the number
    against the wrong list.
    """
    stripped = (text or "").strip()
    # A pincode is six digits and is answered at a step that offers no
    # options, so a number is only a choice when a list is actually open.
    if not stripped.isdigit() or len(stripped) > 2:
        return None
    rows = list(thread.last_options or [])
    index = int(stripped) - 1
    return rows[index] if 0 <= index < len(rows) else None


# ── Applying an answer ───────────────────────────────────────────────────────


async def _navigate(db, executor, reply_id: str, draft, thread, channel: str,
                    identity=None) -> Turn | None:
    """Answer the taps that only move between lists, or None if it is an answer.

    A category records nothing — it narrows the next list — and "Show more" is
    not an answer either. Both re-render a list, and each carries everything
    needed to do so in its own id.
    """
    kind, _, rest = reply_id.partition(PICKER_SEP)

    if kind == PICK_ADDON:
        from app.engines.messaging_gateway import addons
        result = await addons.handle(db, thread, draft, channel, rest)
        if result is not None:
            return result
        return await _next_step(db, thread, executor, await _draft(db, thread), channel, 0, identity)

    if kind == PICK_RESTART:
        return await _restart(db, thread, executor, channel, identity)

    if kind == PICK_PHONE and rest == "change":
        # Keep the completed booking draft and only restart its identity step.
        # The pending number is server-side conversation state, not a number
        # read from the Instagram device.
        thread.pending_customer_id = None
        thread.pending_phone_ciphertext = None
        return Turn(ASK_PHONE)

    if kind == PICK_PHONE and rest == "send":
        if identity is None or not _phone_confirmation_pending(identity, thread):
            return Turn(ASK_PHONE)
        await identity.confirm_phone_verification(thread)
        return _otp_step(identity, thread)

    if kind == PICK_TRACK:
        if identity is None:
            return None
        return await _track_step(thread, identity, rest, channel)

    if kind == PICK_CANCEL:
        if identity is None:
            return None
        return await _cancel_step(thread, identity, rest, channel)

    if kind == PICK_PARTS:
        if identity is None:
            return None
        parts_request_id, _, decision = rest.partition(PICKER_SEP)
        note = await identity.decide_parts(thread, parts_request_id, decision)
        # Straight on to the next one when there is another waiting, so a
        # customer with two requests is not left wondering.
        following = await _parts_step(identity, thread, channel)
        if following:
            following.text = f"{note}\n\n{following.text}"
            return following
        return await _booked_menu_for(identity, thread, "", note)

    if kind == PICK_QUOTE:
        if identity is None:
            return None
        quote_id, _, decision = rest.partition(PICKER_SEP)
        note = await identity.decide_quote(thread, quote_id, decision)
        following = await _quote_step(identity, thread, channel)
        if following:
            following.text = f"{note}\n\n{following.text}"
            return following
        return await _booked_menu_for(identity, thread, "", note)

    if kind == PICK_HANDOVER:
        if identity is None:
            return None
        job_id, _, decision = rest.partition(PICKER_SEP)
        if decision != "acknowledge":
            return None
        note = await identity.acknowledge_handover(thread, job_id)
        following = await _closure_step(identity, thread, channel)
        if following:
            following.text = f"{note}\n\n{following.text}"
            return following
        return await _booked_menu_for(identity, thread, "", note)

    if kind == PICK_PAYMENT:
        if identity is None:
            return None
        payment_id, _, decision = rest.partition(PICKER_SEP)
        if decision == "review_not_paid":
            return Turn(PAYMENT_NOT_PAID_WARNING, {
                "body": "Confirm the payment issue",
                "rows": [
                    {"id": PICKER_SEP.join((PICK_PAYMENT, payment_id, "not_paid")),
                     "title": "Confirm not paid"},
                    {"id": f"{PICK_TRACK}{PICKER_SEP}", "title": "Go back"},
                ],
                "list_button": "Choose", "section_title": "Payment issue",
                "presentation": "buttons",
            })
        if decision not in {"confirm", "not_paid"}:
            return None
        note = await identity.decide_payment(thread, payment_id, decision)
        following = await _closure_step(identity, thread, channel)
        if following:
            following.text = f"{note}\n\n{following.text}"
            return following
        return await _booked_menu_for(identity, thread, "", note)

    if kind == PICK_RATING:
        from app.engines.messaging_gateway import rating_request
        booking_id, _, stars = rest.partition(PICKER_SEP)
        note = await rating_request.record_rating(db, thread, booking_id, stars)
        return await _booked_menu_for(identity, thread, "", note)

    if kind == PICK_SKIP and draft:
        await _merge_address(db, draft, {"location_skipped": True})
        return None

    if kind == PICK_AREA_CITY:
        return await _area_step(db, channel, 0, city=rest)

    if kind == PICK_AREA:
        thread.zipcode = rest
        thread.city = await _area_city(db, rest)
        return await _next_step(db, thread, executor, None, channel, 0, identity)

    if kind == PICK_CATEGORY:
        return await _offering_step(db, executor, rest, channel, 0, thread)

    if kind == PICK_EMERGENCY:
        # Switching lists changes nothing on the draft — only which slots are
        # shown — so it is answered straight from the tap.
        return await _slot_turn(db, thread, draft, channel, 0,
                                emergency=rest == "on")

    if kind == PICK_MORE:
        of_kind, _, tail = rest.partition(PICKER_SEP)
        page_text, _, context = tail.partition(PICKER_SEP)
        page = pickers._int(page_text)
        if of_kind == PICK_AREA_CITY:
            return await _area_step(db, channel, page)
        if of_kind == PICK_AREA:
            return await _area_step(db, channel, page, city=context or None)
        if of_kind == PICK_CATEGORY:
            return _category_step(
                await _serviceable_categories(db, thread.zipcode or ""), channel, page)
        if of_kind == PICK_OFFERING:
            return await _offering_step(db, executor, context, channel, page, thread)
        if of_kind == PICK_PROBLEM and draft:
            return await _problem_step(executor, draft, channel, page)
        if of_kind == PICK_DIMENSION and draft:
            # `context` carries the dimension key, but the draft already knows
            # which one is outstanding — re-resolving it keeps a stale "More"
            # tap from reopening a dimension that has since been answered.
            return await _dimension_step(db, draft, channel, page)
        if of_kind == PICK_SLOT and context == SLOT_EMERGENCY_FLAG and draft:
            return await _slot_turn(db, thread, draft, channel, page, emergency=True)
        return None  # a question or slot page — the draft decides what to show

    return None


async def _slot_turn(db, thread, draft, channel: str, page: int,
                     *, emergency: bool) -> Turn:
    picker = await pickers.build_picker(
        db, draft, customer_id=thread.customer_id, channel=channel,
        page=page, emergency=emergency,
    )
    return Turn(None, picker) if picker else Turn(NO_SLOTS)


def reset_booking_state(thread) -> None:
    """Drop every booking-scoped value so the next message starts clean.

    THE definition of what "a new booking" forgets, so the callers that need
    it — the Start over tap here, and `/fuvay` (or a bare greeting) in the
    gateway service — cannot drift apart. Each used to inline its own list.

    `opted_out` and `human_handoff` are deliberately NOT touched: a /stop is a
    durable choice and an agent-owned thread must not be handed back to the
    bot. Only an explicit start-over clears those.
    """
    thread.ai_session_id = None
    thread.zipcode = None
    thread.city = None
    thread.pending_customer_id = None
    thread.pending_phone_ciphertext = None
    thread.last_options = None


async def abandon_social_booking_drafts(db, thread) -> int:
    """Cancel this sender's unfinished social drafts from older sessions.

    ``/fuvay`` rotates the AI session id.  Before this cleanup, every restart
    therefore hid the old draft from the chat while leaving it active for the
    booking service's three-draft safety cap.  A customer could lock themselves
    out simply by starting over a few times.

    Scope by the channel identity stored on the owning AI session, not by
    customer id: this retires only drafts created by this exact Instagram or
    WhatsApp sender and cannot cancel drafts begun in the customer app.
    """
    channel = str(getattr(thread, "channel", "") or "")
    channel_user_id = str(getattr(thread, "channel_user_id", "") or "")
    if channel not in {CHANNEL_INSTAGRAM, CHANNEL_WHATSAPP} or not channel_user_id:
        return 0

    from app.engines.ai_conversation.models import AIConversationSession
    from app.engines.home_service_booking.constants import (
        ACTOR_CUSTOMER,
        DRAFT_STATUS_CANCELLED,
        EVENT_DRAFT_CANCELLED,
        TERMINAL_STATUSES,
    )
    from app.engines.home_service_booking.models import HomeServiceBookingDraft
    from app.engines.home_service_booking.service import HomeServiceChatbotBookingService
    from app.models.base import utcnow

    now = utcnow()
    drafts = list((await db.execute(
        select(HomeServiceBookingDraft)
        .join(
            AIConversationSession,
            AIConversationSession.id == HomeServiceBookingDraft.ai_session_id,
        )
        .where(
            AIConversationSession.context_data.contains({
                "channel": channel,
                "channel_user_id": channel_user_id,
            }),
            HomeServiceBookingDraft.status.notin_(TERMINAL_STATUSES),
            (
                HomeServiceBookingDraft.expires_at.is_(None)
                | (HomeServiceBookingDraft.expires_at > now)
            ),
        )
        .with_for_update(of=HomeServiceBookingDraft)
    )).scalars().all())
    if not drafts:
        return 0

    events = HomeServiceChatbotBookingService(db)
    for draft in drafts:
        old_status = draft.status
        draft.status = DRAFT_STATUS_CANCELLED
        draft.updated_at = now
        await events._emit_event(
            draft.id,
            ACTOR_CUSTOMER,
            EVENT_DRAFT_CANCELLED,
            old_value={"status": old_status},
            new_value={"status": DRAFT_STATUS_CANCELLED},
            message="Superseded by a new social booking attempt.",
        )
    await db.flush()
    logger.info(
        "messaging_gateway.flow.abandoned_social_drafts",
        channel=channel,
        count=len(drafts),
    )
    return len(drafts)


async def _restart(db, thread, executor, channel: str, identity=None) -> Turn:
    """Abandon whatever is in progress and begin a new booking.

    Answered ahead of every other tap, and ahead of the confirmed-booking
    guard: starting again must work from any message, including after a
    booking has been made. Booking-scoped area state is cleared too: every new
    booking explicitly asks for its zipcode before any service question.
    """
    await abandon_social_booking_drafts(db, thread)
    reset_booking_state(thread)
    step = await _next_step(db, thread, executor, None, channel, 0, identity)
    step.text = f"{RESTARTED}\n\n{step.text}" if step.text else RESTARTED
    return step


async def _apply_tap(db, thread, executor, reply_id: str, draft: dict | None):
    """Returns (note, page, draft). See DONE / BOOKED for the page sentinels."""
    kind, _, rest = reply_id.partition(PICKER_SEP)

    if kind == PICK_MORE:
        _, _, tail = rest.partition(PICKER_SEP)
        page_text, _, _context = tail.partition(PICKER_SEP)
        return None, pickers._int(page_text), draft

    if kind == PICK_OFFERING:
        category_slug, _, offering_slug = rest.partition(PICKER_SEP)
        # A service tap starts one clean attempt. This also repairs accounts
        # already stuck behind drafts abandoned by pre-fix /fuvay sessions.
        await abandon_social_booking_drafts(db, thread)
        started = await executor._tool_start_home_service_draft(
            category_slug=category_slug, offering_slug=offering_slug,
        )
        if started.get("error") or not started.get("draft_id"):
            error_code = started.get("error_code")
            logger.warning(
                "messaging_gateway.flow.start_failed",
                error=started.get("error"), error_code=error_code,
            )
            if error_code == "ACTIVE_BOOKING_DRAFT_LIMIT":
                return TOO_MANY_DRAFTS, DONE, None
            if error_code in {"RATE_LIMITED", "SECURITY_CONTROL_UNAVAILABLE"}:
                return START_RATE_LIMITED, DONE, None
            if error_code == "DUPLICATE_ACTIVE_BOOKING":
                message = started.get("error") or "This service is already booked."
                return message, BOOKED, None
            return START_FAILED, DONE, None
        # The area was settled before any of this; carry it onto the draft so
        # serviceability and pricing have it and the customer is not re-asked.
        contact = await _verified_contact(db, thread)
        await executor._tool_update_home_service_draft(
            draft_id=str(started["draft_id"]),
            zipcode=thread.zipcode, city=thread.city, **contact,
        )
        # Serviceability is settled HERE, before a single question is asked.
        # It only needs the area, which is already known, so asking a customer
        # about their problem, brand and model first — and only then telling
        # them nobody covers them — wastes their time for no information.
        serviceable = await executor._tool_check_home_service_availability(
            draft_id=str(started["draft_id"]),
        )
        if not serviceable.get("serviceable"):
            return SERVICE_NOT_IN_CITY.format(city=thread.city or "your area"), DONE, None
        return None, 0, await _draft(db, thread)

    if not draft:
        return None, 0, draft

    if _is_finished(draft):
        # Every branch below writes to the draft. A tap on an older message —
        # a slot, a brand, even Confirm again — must not reopen a booking that
        # has already been made.
        return ALREADY_BOOKED, BOOKED, draft

    if kind == PICK_DIMENSION:
        return await _apply_dimension(db, thread, executor, rest, draft)

    if kind == PICK_PROBLEM:
        return await _apply_problem(db, thread, executor, rest, draft)

    if kind in (PICK_QUESTION, PICK_SLOT):
        outcome = await pickers.apply_reply(
            db, reply_id, draft, customer_id=thread.customer_id,
        )
        return outcome.get("note"), int(outcome.get("page") or 0), await _draft(db, thread)

    if kind == PICK_CONFIRM:
        if rest == _NO:
            thread.ai_session_id = None  # next turn opens a clean draft
            thread.zipcode = None
            thread.city = None
            thread.pending_customer_id = None
            thread.pending_phone_ciphertext = None
            return RESTARTED, 0, None
        return await _confirm(db, thread, executor, draft)

    if kind == PICK_DUPLICATE:
        expected_draft_id, _, decision = rest.partition(PICKER_SEP)
        if expected_draft_id != str(draft["id"]):
            return "That duplicate-booking confirmation is no longer current.", 0, draft
        if decision == _YES:
            return await _confirm(
                db, thread, executor, draft, allow_duplicate=True,
            )
        await abandon_social_booking_drafts(db, thread)
        reset_booking_state(thread)
        return DUPLICATE_DECLINED, BOOKED, draft

    return None, 0, draft


async def _apply_problem(db, thread, executor, issue_type_id: str, draft: dict):
    """Record the chosen problem — this is what resolves the job type."""
    name = await _problem_name(db, executor, draft, issue_type_id)
    result = await executor._tool_update_home_service_draft(
        draft_id=str(draft["id"]),
        selected_problem_id=issue_type_id,
        # `issue_summary` is a required field, and the problem the customer
        # picked is a truer summary than anything they would have typed.
        issue_summary=name or "Service request",
    )
    if not result.get("updated"):
        logger.warning("messaging_gateway.flow.problem_failed", error=result.get("error"))
    return None, 0, await _draft(db, thread)


async def _apply_location(db, draft: dict | None, location: dict) -> tuple[str | None, dict | None]:
    """Record a shared pin on the draft's address, where the technician reads it."""
    if not draft:
        return None, draft
    values = {
        "latitude": location["latitude"],
        "longitude": location["longitude"],
        # A link is what a technician can actually act on from a job screen.
        "maps_url": f"https://maps.google.com/?q={location['latitude']},{location['longitude']}",
        "location_label": location.get("name") or location.get("address"),
        "location_source": location.get("source") or "shared_pin",
    }
    # A WhatsApp pin can include Meta's readable address. When it does, one
    # customer action satisfies both the technician's map coordinates and the
    # booking's deliverable address. If Meta omits it, the normal typed-address
    # question remains open; coordinates alone are not a postal address.
    readable = " ".join(str(location.get("address") or "").split())
    if readable:
        values["address_line_1"] = readable[:255]
    await _merge_address(db, draft, values)
    return LOCATION_SAVED, None


async def _merge_address(db, draft: dict, values: dict) -> None:
    """Merge keys into the draft's address snapshot, in place."""
    import uuid as _uuid
    from app.engines.home_service_booking.models import HomeServiceBookingDraft

    row = await db.get(HomeServiceBookingDraft, _uuid.UUID(str(draft["id"])))
    if row is None:
        return
    row.address_snapshot = {**(row.address_snapshot or {}), **values}
    await db.flush()


async def _coordinates_from_text(text: str) -> dict | None:
    """Coordinates from a pasted map link, following a short link if needed.

    Phones share `maps.app.goo.gl/…` links, which carry no coordinates at all
    until they are resolved — so the short link is followed once, server-side,
    and the destination is parsed. A link that resolves to nothing usable is
    simply not a location.
    """
    direct = _maps_coordinates(text)
    if direct:
        return direct
    import re

    short = re.search(r"https?://(?:maps\.app\.goo\.gl|goo\.gl/maps)/\S+", text or "")
    if not short:
        return None
    try:
        import httpx

        async with httpx.AsyncClient(timeout=6.0, follow_redirects=True) as client:
            response = await client.get(short.group(0))
        return _maps_coordinates(str(response.url))
    except Exception as exc:  # noqa: BLE001 — an unreachable link is not an error
        logger.info("messaging_gateway.maps_link_unresolved", error=str(exc))
        return None


def _maps_coordinates(text: str) -> dict | None:
    """Pull coordinates out of a Google Maps link or a plain "lat, lng"."""
    import re

    patterns = (
        r"@(-?\d{1,3}\.\d+),(-?\d{1,3}\.\d+)",                    # /maps/@30.70,76.71,17z
        r"[?&]q=(-?\d{1,3}\.\d+),\s*(-?\d{1,3}\.\d+)",            # ?q=30.70,76.71
        r"!3d(-?\d{1,3}\.\d+)!4d(-?\d{1,3}\.\d+)",                # place links
        r"^\s*(-?\d{1,3}\.\d+)\s*,\s*(-?\d{1,3}\.\d+)\s*$",       # pasted pair
    )
    for pattern in patterns:
        found = re.search(pattern, text or "")
        if found:
            latitude, longitude = float(found.group(1)), float(found.group(2))
            if -90 <= latitude <= 90 and -180 <= longitude <= 180:
                return {"latitude": latitude, "longitude": longitude,
                        "name": None, "address": None, "source": "maps_link"}
    return None


async def _apply_text(db, thread, executor, text: str, draft: dict | None,
                      identity=None):
    """Apply a typed answer to whichever typed step is currently open.

    Only three things are ever typed: a pincode, a street address, and — off
    WhatsApp — a mobile number and its OTP. Everything else is a tap.
    """
    digits = "".join(ch for ch in text if ch.isdigit())

    # The area lives on the THREAD because it is explicitly asked before a
    # draft exists. A reply containing only six digits can also change the
    # pincode until a provider is matched. Requiring a pincode-only reply for
    # that later change prevents a complete street address ending in its
    # six-digit pincode from being mistaken for a pincode change.
    pincode_only = text.strip().isdigit() and len(digits) == 6
    if not thread.zipcode or (pincode_only and not (draft or {}).get("selected_tenant_id")):
        if len(digits) != 6:
            return BAD_PINCODE, draft
        changed = thread.zipcode != digits
        thread.zipcode = digits
        if changed:
            thread.city = None  # a new pincode is a new place
        # Fill the city from the coverage row rather than asking for it.
        thread.city = thread.city or await _area_city(db, digits)
        if draft:
            await executor._tool_update_home_service_draft(
                draft_id=str(draft["id"]), zipcode=digits,
            )
            return None, await _draft(db, thread)
        if db is not None and changed and not await _serviceable_categories(db, digits):
            from app.engines.home_service_booking.demand_signal_service import (
                record_unserved_area_demand,
            )
            await record_unserved_area_demand(
                db, zipcode=digits, city=thread.city, channel=thread.channel,
                dedupe_token=str(
                    getattr(thread, "id", None) or getattr(thread, "channel_user_id", "")
                ),
            )
        return None, draft

    if not thread.city:
        thread.city = text[:120]
        if draft:
            await executor._tool_update_home_service_draft(
                draft_id=str(draft["id"]), city=thread.city,
            )
            return None, await _draft(db, thread)
        return None, draft

    if draft and not _valid_address_line(
        (draft.get("address_snapshot") or {}).get("address_line_1")
    ):
        address = " ".join(text.split())
        # Use the booking API's canonical validation here too. The previous
        # social-only word check counted punctuation as a word, advanced to
        # slot selection, and then failed the final booking gate.
        try:
            from app.engines.serviceability.schemas import _validate_address_line

            address = _validate_address_line(address) or ""
        except ValueError:
            return BAD_ADDRESS, draft
        await executor._tool_update_home_service_draft(
            draft_id=str(draft["id"]), address_line_1=address[:255],
        )
        return None, await _draft(db, thread)

    if (
        identity is not None
        and thread.channel != "whatsapp"
        and draft
        and (not thread.customer_id or instagram_phone_bypass_enabled(thread.channel))
        and (draft.get("preferred_date") or (
            draft.get('selected_tenant_id') and 'required_fields' in draft
            and 'preferred_date' not in draft['required_fields']))
    ):
        # Ordered to mirror `_next_step`: the number is asked for only once
        # the booking is otherwise complete, so nothing typed here can still
        # be an address or a pincode, and this branch cannot swallow them.
        if instagram_phone_bypass_enabled(thread.channel):
            if draft.get("customer_phone"):
                return None, draft
            number = _indian_mobile(digits)
            if not number:
                return (BAD_PHONE if digits else None), draft
            result = await executor._tool_update_home_service_draft(
                draft_id=str(draft["id"]), customer_phone=number,
            )
            if not result.get("updated"):
                return "We could not save that number. Please try again.", draft
            return None, await _draft(db, thread)
        if thread.pending_phone_ciphertext:
            awaiting_confirmation = _phone_confirmation_pending(identity, thread)
            if len(digits) == 6 and not awaiting_confirmation:
                note = await identity.finish_phone_verification(thread, digits)
                # Re-read: a confirmed number is written onto the draft, and
                # the summary rendered later in THIS turn should show it.
                return note, await _draft(db, thread)
            # A whole number typed while an OTP is outstanding means "send it
            # to THIS one instead" — a wrong number, or an OTP that never
            # arrived, was otherwise a dead end: the step only ever accepted
            # six digits, so there was no way back to entering a number.
            resend = _indian_mobile(digits)
            if resend:
                await identity.stage_phone_verification(thread, resend)
                return None, draft
            return None, draft
        number = _indian_mobile(digits)
        if not number:
            # "hi" is not a failed phone number, it is a greeting.
            return (BAD_PHONE if digits else None), draft
        await identity.stage_phone_verification(thread, number)
        return None, draft

    return None, draft


async def _confirm(
    db, thread, executor, draft: dict, *, allow_duplicate: bool = False,
):
    from app.engines.messaging_gateway.addons import needs_review
    if needs_review(draft):
        return 'Review your add-ons and the updated total before confirming.', 0, draft
    result = await executor._tool_confirm_home_service_booking(
        draft_id=str(draft["id"]), confirmation_phrase=CONFIRM_PHRASE,
        allow_duplicate=allow_duplicate,
    )
    if not result.get("confirmed"):
        if result.get("error_code") == "DUPLICATE_ACTIVE_BOOKING":
            warning = result.get("error") or "This problem is already booked."
            return warning, DUPLICATE_CONFIRM, draft
        return CONFIRM_FAILED.format(
            reason=result.get("error") or "please check the details and try again."
        ), DONE, draft
    number = result.get("booking_number") or result.get("booking", {}).get("booking_number") or "—"
    # Confirming is what creates (or finds) the account the booking belongs to.
    # Without carrying it back to the thread, the very next turn cannot look
    # the booking up — tracking a booking made seconds earlier would say there
    # is none.
    if getattr(executor, "customer_id", None):
        thread.customer_id = executor.customer_id
    return CONFIRMED.format(number=number), BOOKED, draft


# ── Asking the next question ─────────────────────────────────────────────────


def _is_finished(draft: dict | None) -> bool:
    """True once the draft has become a real booking (or has been closed)."""
    return str((draft or {}).get("status") or "").lower() in _TERMINAL


def _booked_menu(text: str, rows: list[dict] | None = None,
                 has_booking: bool = True) -> Turn:
    """What a customer with a booking can do from here.

    A confirmed booking is not editable in chat, but "you cannot change this"
    is a dead end — tracking it, cancelling it, or starting another are the
    things they might actually want, so they are offered as taps rather than
    as commands to remember.
    """
    return Turn(text, {
        "body": BOOKED_OPTIONS if has_booking else NO_BOOKING_OPTIONS,
        "rows": rows if rows is not None else [
            {"id": f"{PICK_TRACK}{PICKER_SEP}", "title": TRACK_ROW},
            {"id": f"{PICK_RESTART}{PICKER_SEP}1", "title": NEW_BOOKING_ROW},
        ],
        "list_button": "Choose",
        "section_title": "Your booking",
        "presentation": "buttons",
    })


async def _booked_menu_for(identity, thread, booking_number: str, text: str) -> Turn:
    """The menu, built from what this customer actually still has open.

    Offering "Track my booking" to someone whose only booking was just
    cancelled is a row that answers "there is no booking" — so Track and
    Cancel appear only while something is genuinely live. Booking another
    service is always available.
    """
    rows: list[dict] = []
    bookings = []
    if identity is not None:
        try:
            bookings = await identity.live_bookings(thread)
        except Exception as exc:  # noqa: BLE001 — a menu must not break a reply
            logger.warning("messaging_gateway.flow.live_bookings_failed",
                           thread_id=str(getattr(thread, "id", "—")), error=str(exc))

    if bookings:
        rows.append({"id": f"{PICK_TRACK}{PICKER_SEP}", "title": TRACK_ROW})
        # A named booking is offered for cancellation only if the server still
        # allows it; with several open and none named, the Cancel row asks
        # which one rather than guessing at the newest.
        if booking_number:
            options = await identity.cancel_options(thread, booking_number)
            if options.get("can_cancel"):
                rows.append({"id": f"{PICK_CANCEL}{PICKER_SEP}{booking_number}",
                             "title": CANCEL_ROW})
        else:
            rows.append({"id": f"{PICK_CANCEL}{PICKER_SEP}", "title": CANCEL_ROW})

    rows.append({"id": f"{PICK_RESTART}{PICKER_SEP}1", "title": NEW_BOOKING_ROW})
    if identity is not None and not bookings and text == ALREADY_BOOKED:
        # Only said when we actually looked and found nothing — "this booking
        # cannot be changed" is still the honest answer when there is nobody
        # to ask about live bookings.
        text = NOTHING_OPEN
    return _booked_menu(text, rows, has_booking=bool(bookings))


async def _parts_step(
    identity, thread, channel: str, booking_number: str = "",
) -> Turn | None:
    """The oldest parts request awaiting this customer, as two taps.

    One at a time on purpose: each is a separate decision with its own price,
    and a list of them with a shared Approve button would approve things the
    customer did not read.
    """
    if identity is None:
        return None
    try:
        pending = await identity.pending_parts(thread)
    except Exception as exc:  # noqa: BLE001 — never break a reply over this
        logger.warning("messaging_gateway.flow.pending_parts_failed",
                       thread_id=str(getattr(thread, "id", "—")), error=str(exc))
        return None
    if booking_number:
        pending = [
            part for part in pending
            if str(part.get("booking_number") or "") == booking_number
        ]
    if not pending:
        return None

    part = pending[0]
    totals = await identity.parts_totals(thread, part["job_id"])
    currency = totals.get("currency") or "INR"
    lines = [PARTS_HEADER, ""]
    if part.get("booking_number"):
        lines.append(f"Booking {part['booking_number']}")
    lines.append(PARTS_LINE.format(
        part=part["part_name"], quantity=part["quantity"],
        total=_money(currency, part["line_total"])))
    if part.get("reason"):
        lines.append(PARTS_REASON.format(reason=part["reason"]))
    if totals.get("new_estimated_total"):
        lines.append("")
        previous = Decimal(str(totals.get("previous_estimated_total") or "0"))
        if previous > 0:
            lines.append(PARTS_TOTALS.format(
                current=_money(currency, previous),
                new=_money(currency, totals["new_estimated_total"])))
        else:
            lines.append(PARTS_ADDS.format(
                total=_money(currency, totals["new_estimated_total"])))
    if len(pending) > 1:
        lines.append("")
        lines.append(f"({len(pending) - 1} more to review after this one.)")

    return Turn("\n".join(lines), {
        "body": "Approve this part?",
        "rows": [
            {"id": PICKER_SEP.join((PICK_PARTS, part["id"], "approve")),
             "title": PARTS_APPROVE_ROW},
            {"id": PICKER_SEP.join((PICK_PARTS, part["id"], "decline")),
             "title": PARTS_DECLINE_ROW},
        ],
        "list_button": "Choose",
        "section_title": "Parts",
        "presentation": "buttons",
    })


async def _quote_step(
    identity, thread, channel: str, booking_number: str = "",
) -> Turn | None:
    """Show the oldest current estimate awaiting this customer's decision."""
    if identity is None:
        return None
    try:
        pending = await identity.pending_quotes(thread)
    except Exception as exc:  # noqa: BLE001 - a read must not break the chat
        logger.warning("messaging_gateway.flow.pending_quotes_failed",
                       thread_id=str(getattr(thread, "id", "-")), error=str(exc))
        return None
    if booking_number:
        pending = [
            quote for quote in pending
            if str(quote.get("booking_number") or "") == booking_number
        ]
    if not pending:
        return None

    quote = pending[0]
    currency = quote.get("currency") or "INR"
    lines = [QUOTE_HEADER, "", QUOTE_LINE.format(
        number=quote.get("quote_number") or "-",
        total=_money(currency, quote.get("amount") or "0"),
    )]
    if quote.get("booking_number"):
        lines.append(f"Booking {quote['booking_number']}")
    for item in quote.get("items") or []:
        name = item.get("item_name")
        total = item.get("line_total")
        if name and total is not None:
            lines.append(f"- {name}: {_money(currency, total)}")
    if quote.get("notes"):
        lines.extend(("", str(quote["notes"])))
    if len(pending) > 1:
        lines.extend(("", f"({len(pending) - 1} more estimate(s) to review after this one.)"))

    quote_id = quote["id"]
    return Turn("\n".join(lines), {
        "body": "What would you like to do with this estimate?",
        "rows": [
            {"id": PICKER_SEP.join((PICK_QUOTE, quote_id, "approve")),
             "title": QUOTE_APPROVE_ROW},
            {"id": PICKER_SEP.join((PICK_QUOTE, quote_id, "decline")),
             "title": QUOTE_DECLINE_ROW},
            {"id": PICKER_SEP.join((PICK_QUOTE, quote_id, "revise")),
             "title": QUOTE_REVISE_ROW},
        ],
        "list_button": "Choose",
        "section_title": "Estimate",
        "presentation": (
            "quick_replies" if channel == CHANNEL_INSTAGRAM else "buttons"
        ),
    })


async def _closure_step(
    identity, thread, channel: str, booking_number: str = "",
) -> Turn | None:
    """Render the customer actions that unblock staff/tenant final closure."""
    if identity is None:
        return None
    try:
        pending = await identity.pending_closure_actions(thread)
    except Exception as exc:  # noqa: BLE001 - a read must not break the chat
        logger.warning("messaging_gateway.flow.pending_closure_failed",
                       thread_id=str(getattr(thread, "id", "-")), error=str(exc))
        return None
    if booking_number:
        pending = [
            action for action in pending
            if str(action.get("booking_number") or "") == booking_number
        ]
    if not pending:
        return None

    action = pending[0]
    if action["kind"] == "handover":
        lines = [HANDOVER_HEADER]
        if action.get("booking_number"):
            lines.extend(("", f"Booking {action['booking_number']}"))
        if action.get("service"):
            lines.append(str(action["service"]))
        return Turn("\n".join(lines), {
            "body": "Was the completed work handed over to you?",
            "rows": [{
                "id": PICKER_SEP.join((PICK_HANDOVER, action["job_id"], "acknowledge")),
                "title": HANDOVER_ACK_ROW,
            }],
            "list_button": "Choose", "section_title": "Service handover",
            "presentation": "buttons",
        })

    if action["kind"] == "payment":
        amount = _money(action.get("currency") or "INR", action.get("amount") or "0")
        lines = [PAYMENT_HEADER, ""]
        if action.get("job_ref"):
            lines.append(f"Job {action['job_ref']}")
        if action.get("provider"):
            lines.append(f"Provider: {action['provider']}")
        lines.extend((f"Amount: {amount}", f"Method: {action.get('method') or '-'}", "",
                      PAYMENT_NOTICE))
        return Turn("\n".join(lines), {
            "body": f"Did you pay {amount} directly to the provider?",
            "rows": [
                {"id": PICKER_SEP.join((PICK_PAYMENT, action["payment_id"], "confirm")),
                 "title": PAYMENT_CONFIRM_ROW},
                {"id": PICKER_SEP.join((PICK_PAYMENT, action["payment_id"], "review_not_paid")),
                 "title": PAYMENT_NOT_PAID_ROW},
            ],
            "list_button": "Choose", "section_title": "Direct payment",
            "presentation": "buttons",
        })
    return None


def _money(currency: str, amount) -> str:
    """₹1,299 rather than 1299.00 — a price read aloud in a chat."""
    try:
        value = Decimal(str(amount))
    except (InvalidOperation, TypeError, ValueError):
        return f"{currency} {amount}"
    symbol = "₹" if str(currency).upper() == "INR" else f"{currency} "
    quantized = value.quantize(Decimal("1")) if value == value.to_integral_value() else value
    return f"{symbol}{quantized:,}"


async def _cancel_step(thread, identity, rest: str, channel: str) -> Turn:
    """Ask which, then why, then cancel — never on a single stray tap.

    The reasons offered are the ones the booking service accepts, read from
    its own eligibility response rather than restated here.
    """
    booking_number, _, reason = rest.partition(PICKER_SEP)

    if not booking_number:
        # Tapped from the menu with several bookings open: name them, so the
        # customer cancels the one they mean rather than the newest.
        bookings = await identity.live_bookings(thread)
        if not bookings:
            return await _booked_menu_for(identity, thread, "", NO_BOOKINGS)
        if len(bookings) == 1:
            return await _cancel_step(thread, identity, bookings[0]["number"], channel)
        rows = [
            {"id": f"{PICK_CANCEL}{PICKER_SEP}{b['number']}",
             "title": b["service"] or b["number"], "description": _booking_line(b)}
            for b in bookings
        ]
        picker = pickers._paginate(rows, ASK_WHICH_CANCEL, channel, 0,
                                   kind=PICK_CANCEL, list_button="Choose",
                                   section_title="Your bookings")
        return Turn(None, picker) if picker else Turn(CANCEL_FAILED)

    if reason:
        text = await identity.cancel_booking(thread, booking_number, reason)
        return await _booked_menu_for(identity, thread, "", text)

    options = await identity.cancel_options(thread, booking_number)
    if not options.get("can_cancel"):
        return await _booked_menu_for(identity, thread, booking_number,
                                      CANCEL_NOT_ALLOWED)
    rows = [
        {"id": PICKER_SEP.join((PICK_CANCEL, booking_number, code)),
         "title": CANCEL_REASON_LABELS.get(code, code.replace("_", " ").title())}
        for code in options["reasons"]
    ]
    picker = pickers._paginate(rows, ASK_CANCEL_REASON.format(number=booking_number),
                               channel, 0, kind=PICK_CANCEL, list_button="Choose",
                               section_title="Cancel booking")
    return Turn(None, picker) if picker else Turn(CANCEL_FAILED)


async def _track_step(thread, identity, booking_number: str, channel: str) -> Turn:
    """Show a booking's status — or, with several open, which one.

    Tapping "Track" with one live booking should answer, not ask. With several
    live bookings, always ask which one before surfacing approval actions: an
    estimate for booking A must not replace the status requested for booking B.
    """
    bookings = await identity.live_bookings(thread)
    if not booking_number and len(bookings) > 1:
        rows = [
            {"id": f"{PICK_TRACK}{PICKER_SEP}{b['number']}",
             "title": b["service"] or b["number"], "description": _booking_line(b),
             "image_url": b.get("image_url"),
             "button_title": b["service"] or "Track booking"}
            for b in bookings
        ]
        # Tracking needs the status/date/booking number visible for every row.
        # Instagram quick-reply chips show only the (often duplicated) service
        # name; generic cards retain the distinguishing subtitle even when an
        # older service has no uploaded artwork.
        cards = channel == CHANNEL_INSTAGRAM
        picker = pickers._paginate(
            rows, "Which booking?", channel, 0, kind=PICK_TRACK,
            list_button="Choose", section_title="Your bookings",
            presentation="carousel" if cards else "quick_replies",
            capacity_override=MAX_IG_GENERIC_ELEMENTS if cards else None,
        )
        return Turn(None, picker) if picker else await _booked_menu_for(
            identity, thread, "", NO_BOOKINGS,
        )

    if not booking_number and len(bookings) == 1:
        booking_number = bookings[0]["number"]

    action = await _parts_step(identity, thread, channel, booking_number)
    if action is None:
        action = await _quote_step(identity, thread, channel, booking_number)
    if action is None:
        action = await _closure_step(identity, thread, channel, booking_number)
    if action is not None:
        return action
    if booking_number:
        turn = await _tracked_booking_turn(identity, thread, booking_number, channel)
        return await _attach_booking_location(turn, identity, thread,
                                              booking_number, channel)
    if not bookings:
        return await _booked_menu_for(identity, thread, "", NO_BOOKINGS)
    return await _booked_menu_for(identity, thread, "", NO_BOOKINGS)


async def _tracked_booking_turn(identity, thread, booking_number: str,
                                channel: str) -> Turn:
    """Build detailed status plus an Instagram-native visual status card."""
    view = None
    status_view = getattr(identity, "booking_status_view", None)
    if status_view is not None:
        view = await status_view(thread, booking_number)
        status_text = view.get("text") or NO_BOOKINGS
    else:
        status_text = await identity.booking_status(thread, booking_number)
    turn = await _booked_menu_for(identity, thread, booking_number, status_text)
    if channel == CHANNEL_INSTAGRAM and view and turn.picker:
        rows = [dict(row) for row in turn.picker.get("rows") or []]
        for row in rows:
            if str(row.get("id") or "").startswith(f"{PICK_TRACK}{PICKER_SEP}"):
                row["title"] = "Refresh status"
        turn.picker["rows"] = rows
        turn.picker["presentation"] = "status_card"
        turn.picker["card"] = {
            "title": view.get("title"),
            "subtitle": view.get("subtitle"),
            "image_url": view.get("image_url"),
        }
    return turn


async def _attach_booking_location(
    turn: Turn, identity, thread, booking_number: str, channel: str,
) -> Turn:
    if channel != CHANNEL_WHATSAPP or not turn.picker:
        return turn
    try:
        cta = await identity.booking_location_cta(thread, booking_number)
    except Exception as exc:  # a map shortcut must never break tracking
        logger.warning("messaging_gateway.flow.booking_location_failed",
                       booking_number=booking_number, error=str(exc))
        return turn
    if cta:
        turn.picker["cta_url"] = cta
    return turn


async def _next_step(db, thread, executor, draft: dict | None, channel: str,
                     page: int, identity=None) -> Turn:
    if executor is not None and thread.customer_id and not executor.customer_id:
        # The customer may have been identified DURING this turn (the phone
        # step), and the executor was built before that. Without this the
        # summary is fetched as an anonymous caller and comes back empty.
        executor.customer_id = thread.customer_id

    # A halted job outranks everything: the technician is standing there, and
    # a booking flow started underneath an unanswered parts request would bury
    # the one message the customer needs to act on.
    if not draft or _is_finished(draft):
        parts = await _parts_step(identity, thread, channel)
        if parts:
            return parts
        quote = await _quote_step(identity, thread, channel)
        if quote:
            return quote
        closure = await _closure_step(identity, thread, channel)
        if closure:
            return closure

    if _is_finished(draft):
        return await _booked_menu_for(identity, thread, "", ALREADY_BOOKED)

    # The service area is settled FIRST. Asking it last meant a customer could
    # pick a service, a problem and answer half a dozen catalog questions
    # before being told nobody covers them.
    if not thread.zipcode:
        # Zipcode is the serviceability key and must be collected explicitly
        # before service, problem, catalog or address questions on both chat
        # channels. Area pickers remain accepted for already-sent messages,
        # but a new booking always starts with this unambiguous question.
        return Turn(ASK_PINCODE)

    # Coverage is decided on the PINCODE alone, so it is decided before any
    # other question — including the city, which is only ever asked as a
    # fallback for a covered area whose row does not name one.
    categories = await _serviceable_categories(db, thread.zipcode)
    if not categories:
        # An uncovered pincode has no coverage row, so there is no city name
        # to use — naming the pincode is the only honest thing to say.
        return Turn(NOT_IN_CITY.format(
            area=f"{thread.city} ({thread.zipcode})" if thread.city else thread.zipcode))

    if not thread.city:
        return Turn(ASK_CITY)

    if not draft:
        # Resolved BEFORE the page is cut, not after: a row prepended to an
        # already-full list is one row over Meta's cap, and Meta fails the
        # whole send rather than dropping it.
        live_bookings = await identity.live_bookings(thread) if identity is not None else []
        tracking = bool(live_bookings)
        step = _category_step(categories, channel, page, reserve=1 if tracking else 0)
        if step.picker and tracking:
            # Someone with a booking in progress is at least as likely to want
            # to check on it as to book something new, so the option leads.
            booking = live_bookings[0]
            track_row = {
                "id": f"{PICK_TRACK}{PICKER_SEP}",
                "title": TRACK_ROW,
                "button_title": "Track booking",
                "description": _booking_line(booking),
            }
            if channel == CHANNEL_INSTAGRAM and step.picker.get("presentation") == "carousel":
                # Never insert a blank full-size card beside illustrated
                # categories. Prefer the booked service artwork, then reuse a
                # public category image already present in this carousel.
                fallback_image = next((
                    artwork for artwork in (
                        _category_artwork(category) for category in categories
                    ) if artwork
                ), None)
                track_row["image_url"] = booking.get("image_url") or fallback_image
            step.picker["rows"] = (
                [track_row] + step.picker["rows"]
            )
        return step

    # Type and brand come BEFORE the problem: "my Split AC is not cooling" is
    # how a customer actually describes the job, and pricing needs both anyway.
    # Asking after the problem meant a Window-AC customer answered a problem
    # list written for every AC there is.
    dimension = await _dimension_step(db, draft, channel, page)
    if dimension:
        return dimension

    if not draft.get("job_type_id"):
        return await _problem_step(executor, draft, channel, page)

    picker = await pickers.build_picker(
        db, draft, customer_id=thread.customer_id, channel=channel, page=page,
    )
    if picker:  # a catalog question, or the slot grid once a provider is matched
        return Turn(None, picker)

    if not _valid_address_line(
        (draft.get("address_snapshot") or {}).get("address_line_1")
    ):
        return Turn(ASK_ADDRESS_WHATSAPP if channel == CHANNEL_WHATSAPP else ASK_ADDRESS)

    if not draft.get("selected_tenant_id"):
        return await _match_step(db, thread, executor, draft, channel, page)

    if not draft.get("preferred_date") and ('required_fields' not in draft or 'preferred_date' in draft['required_fields']):
        # A provider is matched but has no bookable capacity in the horizon.
        return Turn(NO_SLOTS)

    # The number is asked for HERE — after the booking is otherwise complete,
    # immediately before confirmation. WhatsApp needs none of this (Meta has
    # already verified the sender), but Instagram gives no number at all, and
    # asking a stranger for one as the opening question loses them before they
    # have seen a price or a slot.
    if instagram_phone_bypass_enabled(thread.channel) and not draft.get("customer_phone"):
        return Turn(ASK_TEST_PHONE)

    if (
        not thread.customer_id
        and thread.channel != "whatsapp"
        and not instagram_phone_bypass_enabled(thread.channel)
    ):
        if thread.pending_phone_ciphertext:
            if _phone_confirmation_pending(identity, thread):
                return _phone_confirmation_step(identity, thread)
            return _otp_step(identity, thread)
        return Turn(ASK_PHONE)

    from app.engines.messaging_gateway import addons
    addon_step = await addons.step(db, thread, draft, channel)
    if addon_step is not None:
        return addon_step
    return await _confirm_step(executor, draft, thread)


async def _area_step(db, channel: str, page: int, city: str | None = None) -> Turn:
    """The areas a published provider genuinely covers, as taps.

    Two steps, because a pincode is what coverage is actually keyed on and a
    city can hold dozens of them: cities first, then the pincodes inside the
    chosen one. A city with a single pincode is selected outright — there is
    no choice to offer, and an extra tap to confirm what we already know is
    an extra tap.
    """
    areas = await _covered_areas(db, city)
    if city:
        options = [
            {"id": f"{PICK_AREA}{PICKER_SEP}{zipcode}",
             "title": zone or str(zipcode),
             "description": str(zipcode) if zone else None}
            for _, zipcode, zone in areas
        ]
        body = ASK_AREA_PINCODE.format(city=city)
        section = city
    else:
        options, seen = [], {}
        for area_city, zipcode, _zone in areas:
            seen.setdefault(area_city, []).append(zipcode)
        for area_city, zipcodes in seen.items():
            single = len(zipcodes) == 1
            options.append({
                # One pincode: no choice to make, so the tap IS the answer.
                "id": (f"{PICK_AREA}{PICKER_SEP}{zipcodes[0]}" if single
                       else f"{PICK_AREA_CITY}{PICKER_SEP}{area_city}"),
                "title": (area_city or "").title() or str(zipcodes[0]),
                "description": (str(zipcodes[0]) if single
                                else f"{len(zipcodes)} areas"),
            })
        body, section = ASK_AREA, "Areas we cover"

    picker = pickers._paginate(options, body, channel, page,
                               kind=PICK_AREA_CITY if not city else PICK_AREA,
                               list_button="Choose area", section_title=section,
                               more_context=city or "")
    # No coverage configured at all: fall back to asking, rather than showing
    # an empty list.
    return Turn(None, picker) if picker else Turn(ASK_PINCODE)


async def _covered_areas(db, city: str | None) -> list:
    """(city, zipcode, zone) for every active covered area, one row each."""
    from app.engines.serviceability.models import TenantServiceArea

    query = (
        select(TenantServiceArea.city, TenantServiceArea.zipcode,
               func.max(TenantServiceArea.zone_name))
        .where(TenantServiceArea.is_active.is_(True),
               TenantServiceArea.zipcode.isnot(None))
        .group_by(TenantServiceArea.city, TenantServiceArea.zipcode)
        .order_by(TenantServiceArea.city, TenantServiceArea.zipcode)
    )
    if city:
        query = query.where(func.lower(TenantServiceArea.city) == city.lower())
    return list((await db.execute(query)).all())


async def _area_city(db, zipcode: str) -> str | None:
    """The city a published provider actually covers this pincode under.

    Providers are matched on the PINCODE, never on a typed city name, so
    asking the customer to type one is a question whose answer is already in
    `tenant_service_areas` — and a typo in it would only make the draft's
    address read wrong. Asked for only when no covering area names a city.
    """
    from app.engines.serviceability.models import TenantServiceArea

    city = (await db.execute(
        select(TenantServiceArea.city)
        .where(TenantServiceArea.zipcode == str(zipcode),
               TenantServiceArea.is_active.is_(True),
               TenantServiceArea.city.isnot(None))
        .limit(1)
    )).scalars().first()
    # Providers enter their areas in whatever case they like ("bassi pathana");
    # this name is read back to the customer on their address, so present it.
    return city.title() if city else None


async def _serviceable_categories(db, zipcode: str) -> list:
    """Categories with at least one offering a published tenant covers HERE.

    Reuses `offering_catalog_service._publisher_filter`, the same predicate the
    app's catalog uses, so the chat can never offer a category the app would
    have hidden — or hide one it would have shown.
    """
    from app.engines.admin_catalog.models import (
        MasterService, ServiceCategory, ServiceIssueMapping,
    )
    from app.engines.home_service_booking.offering_catalog_service import _publisher_filter

    covered = (
        select(MasterService.category_id)
        .where(
            MasterService.is_active.is_(True),
            _publisher_filter(zipcode),
            MasterService.id.in_(
                select(ServiceIssueMapping.master_service_id)
                .where(ServiceIssueMapping.status == "active")
            ),
        )
    )
    return list((await db.execute(
        select(ServiceCategory)
        .where(ServiceCategory.is_active.is_(True),
               ServiceCategory.is_customer_visible.is_(True),
               ServiceCategory.id.in_(covered))
        .order_by(ServiceCategory.name)
    )).scalars().all())


def _category_artwork(category) -> str | None:
    """The admin's picture for a category — the image if one is set, else the
    icon.

    Meta fetches the URL from its own servers, so only a public https address
    can ever render; a relative `/uploads/...` path or a plain-http host is
    dropped silently at send time. Treating those as no artwork at all keeps
    the numbered list — which at least reads — instead of a carousel of blank
    cards, and says so in the log so a mis-stored upload is findable.
    """
    for url in (getattr(category, "image_url", None), getattr(category, "icon_url", None)):
        value = str(url or "").strip()
        if value.startswith("https://"):
            return value
        if value:
            logger.info("messaging_gateway.category.artwork_not_public",
                        category=getattr(category, "slug", None), url=value)
    return None


def _category_step(categories: list, channel: str, page: int,
                   reserve: int = 0) -> Turn:
    """The serviceable categories, as taps — carrying the admin's artwork.

    A category the admin has given an icon or an image is worth showing as a
    picture, and Instagram's only option shape that can carry one is the
    generic carousel. So a list with artwork in it renders as cards, one
    without stays the cheaper numbered list, and WhatsApp — which has no
    per-row imagery at all — keeps its list either way.

    `reserve` is how many rows the caller will prepend after this returns (the
    "Track my booking" row), because the page has to be cut short enough to
    hold them: Meta rejects a whole message that runs one row over its cap
    rather than trimming it.
    """
    visible = [c for c in categories if c.slug]
    artwork = {c.slug: _category_artwork(c) for c in visible}
    cards = channel == CHANNEL_INSTAGRAM and any(artwork.values())

    options = []
    for c in visible:
        row = {"id": f"{PICK_CATEGORY}{PICKER_SEP}{c.slug}", "title": c.name}
        if cards:
            # Generic-template fields; every other renderer ignores them, so
            # the WhatsApp list is unchanged by a category gaining artwork.
            row["image_url"] = artwork[c.slug]
            row["description"] = getattr(c, "description", None) or None
            # Instagram echoes a postback button's title as the customer's
            # message. Use the actual choice instead of the unhelpful word
            # "Select", so the conversation visibly records what they picked.
            row["button_title"] = c.name
        options.append(row)

    picker = pickers._paginate(options, ASK_CATEGORY, channel, page,
                               kind=PICK_CATEGORY, list_button="Choose",
                               section_title="Services", reserve=reserve,
                               presentation="carousel" if cards else "quick_replies",
                               capacity_override=MAX_IG_GENERIC_ELEMENTS if cards else None)
    if not picker:
        return Turn(NOTHING_HERE)
    # A generic template carries no prompt of its own, so on Instagram the
    # question has to arrive as the message before the cards.
    return Turn(ASK_CATEGORY if cards else None, picker)


async def _offering_step(db, executor, category_slug: str, channel: str, page: int,
                         thread=None) -> Turn:
    result = await executor._tool_get_category_offerings(category_slug=category_slug)
    options = [
        {"id": PICKER_SEP.join((PICK_OFFERING, category_slug, o["slug"])),
         "title": o["name"], "description": o.get("description"),
         "image_url": o.get("image_url") or o.get("icon_url"),
         # Meta shows this button title as the customer's reply after a tap.
         # Repeating the option label makes the selected service unambiguous.
         "button_title": o["name"]}
        for o in (result.get("offerings") or []) if o.get("slug")
    ]
    picker = pickers._paginate(options, ASK_OFFERING, channel, page,
                               kind=PICK_OFFERING, list_button="Choose",
                               section_title="Services", more_context=category_slug,
                               presentation="carousel",
                               capacity_override=(MAX_IG_GENERIC_ELEMENTS
                                                  if channel == CHANNEL_INSTAGRAM else None))
    if picker:
        # Generic templates have no outer prompt text. Send the prompt as the
        # preceding message on Instagram; WhatsApp still carries it in its list.
        return Turn(ASK_OFFERING if channel == CHANNEL_INSTAGRAM else None, picker)
    # The category itself is covered somewhere, just not at this pincode — so
    # send them back to the list that IS covered rather than to a dead end.
    categories = await _serviceable_categories(db, thread.zipcode or "")
    step = _category_step(categories, channel, 0)
    return Turn(SERVICE_NOT_IN_CITY.format(city=thread.city or "your area"), step.picker)


#: Where a dimension's values live. Both shipped dimensions are
#: `legacy_source`-backed, so the options are the ACTIVE mappings for this
#: master service, not the whole global library — offering every brand on the
#: platform would let a customer pick one nobody services.
_DIMENSION_VALUE_SQL = {
    "type": """
        SELECT st.id, st.name, COALESCE(st.image_url, st.icon_url) AS image_url
          FROM master_service_types mst
          JOIN service_types st ON st.id = mst.service_type_id
         WHERE mst.master_service_id = :service
           AND mst.is_active IS TRUE
           AND st.is_active IS TRUE
           AND st.deleted_at IS NULL
           AND st.customer_visible IS TRUE
         ORDER BY st.display_order, st.name
    """,
    "brand": """
        SELECT b.id, b.name, COALESCE(b.image_url, b.logo_url) AS image_url
          FROM master_service_brands msb
          JOIN brands b ON b.id = msb.brand_id
         WHERE msb.master_service_id = :service
           AND msb.is_active IS TRUE
           AND msb.status = 'active'
           AND b.is_active IS TRUE
         ORDER BY msb.display_order, b.name
    """,
}


async def _pending_dimension(db, draft: dict) -> tuple[str, str, list] | None:
    """The next blueprint dimension this draft still needs, with its options.

    Returns `(key, label, rows)` or None when nothing is outstanding. Dimensions
    are configured per `(master_service, job_type)`, and `job_type_id` is only
    filled in once the problem is chosen — but every master service maps to
    exactly ONE active job type, so the blueprint is resolvable from the
    service alone and these can be asked BEFORE the problem.
    """
    service_id = draft.get("offering_id")
    if not service_id:
        return None

    job_type_id = draft.get("job_type_id")
    if not job_type_id:
        rows = (await db.execute(text(
            "SELECT job_type_id FROM master_service_job_types "
            "WHERE master_service_id = :s AND is_active IS TRUE"
        ), {"s": service_id})).all()
        if len(rows) != 1:
            # Ambiguous (or unconfigured) blueprint. The problem step resolves
            # the job type, so let it run first rather than guessing.
            return None
        job_type_id = rows[0][0]

    configured = (await db.execute(text(
        "SELECT cd.key, cd.name "
        "  FROM service_job_dimensions sjd "
        "  JOIN catalog_dimensions cd ON cd.id = sjd.dimension_id "
        " WHERE sjd.master_service_id = :s "
        "   AND sjd.job_type_id IS NOT DISTINCT FROM :j "
        "   AND sjd.enabled IS TRUE AND sjd.required IS TRUE "
        "   AND sjd.ask_customer IS TRUE AND cd.is_active IS TRUE "
        " ORDER BY sjd.display_order, cd.display_order"
    ), {"s": service_id, "j": job_type_id})).all()

    for key, label in configured:
        field = DIMENSION_DRAFT_FIELD.get(key)
        if not field or draft.get(field):
            continue  # not answerable in chat, or already answered
        sql = _DIMENSION_VALUE_SQL.get(key)
        if not sql:
            continue
        values = (await db.execute(text(sql), {"service": service_id})).all()
        if not values:
            # Required but nothing configured to offer. Skipping keeps the
            # booking moving instead of dead-ending the customer on a question
            # with no answers; the gap belongs in the catalog console.
            logger.warning("messaging_gateway.dimension.no_values",
                           dimension=key, service_id=str(service_id))
            continue
        return key, label, values
    return None


async def _dimension_step(db, draft: dict, channel: str, page: int) -> Turn | None:
    """Ask for the next outstanding type/brand, as taps."""
    pending = await _pending_dimension(db, draft)
    if not pending:
        return None
    key, label, values = pending
    normalized = []
    for value in values:
        value_id, name = value[0], value[1]
        image_url = value[2] if len(value) > 2 else None
        image_url = str(image_url or "").strip()
        normalized.append((value_id, name, image_url if image_url.startswith("https://") else None))
    cards = channel == CHANNEL_INSTAGRAM and any(image_url for _, _, image_url in normalized)
    options = []
    for value_id, name, image_url in normalized:
        row = {"id": _join(PICK_DIMENSION, key, str(value_id)), "title": str(name)}
        if cards:
            row.update({"image_url": image_url, "button_title": str(name)})
        options.append(row)
    picker = pickers._paginate(
        options, ASK_DIMENSION.format(label=str(label).lower()), channel, page,
        kind=_join(PICK_DIMENSION, key), list_button="Choose",
        section_title=str(label),
        presentation="carousel" if cards else "quick_replies",
        capacity_override=(MAX_IG_GENERIC_ELEMENTS if cards else None),
    )
    return Turn(ASK_DIMENSION.format(label=str(label).lower()) if cards else None, picker) if picker else None


async def _apply_dimension(db, thread, executor, rest: str, draft: dict):
    """Record a type/brand tap on the draft."""
    key, _, value_id = rest.partition(PICKER_SEP)
    field = DIMENSION_DRAFT_FIELD.get(key)
    if not field or not value_id:
        return None, 0, draft
    result = await executor._tool_update_home_service_draft(
        draft_id=str(draft["id"]), **{field: value_id},
    )
    if not result.get("updated"):
        logger.warning("messaging_gateway.flow.dimension_failed",
                       dimension=key, error=result.get("error"))
    return None, 0, await _draft(db, thread)


async def _problem_step(executor, draft: dict, channel: str, page: int) -> Turn:
    result = await executor._tool_get_service_problems(draft_id=str(draft["id"]))
    problems = result.get("problems") or []
    cards = channel == CHANNEL_INSTAGRAM and any(
        str(problem.get("image_url") or "").startswith("https://")
        for problem in problems
    )
    options = []
    for problem in problems:
        name = str(problem["name"])
        row = {
            "id": f"{PICK_PROBLEM}{PICKER_SEP}{problem['id']}",
            "title": (
                f"{problem_card_symbol(name)} {name}" if cards else name
            ),
            "description": (
                problem.get("description")
                or "Select this if it matches what you are experiencing."
            ),
        }
        if cards:
            row["image_url"] = problem.get("image_url")
            # Meta echoes the button title into the conversation after a tap;
            # keep that reply natural rather than repeating the decorative icon.
            row["button_title"] = name
        options.append(row)
    picker = pickers._paginate(options, ASK_PROBLEM, channel, page,
                               kind=PICK_PROBLEM, list_button="Choose",
                               section_title="Problems",
                               presentation="carousel" if cards else "quick_replies",
                               capacity_override=(MAX_IG_GENERIC_ELEMENTS
                                                  if cards else None))
    # A generic carousel cannot contain the question text, so send it as the
    # preceding message just like the category and service card pickers.
    return Turn(ASK_PROBLEM if cards else None, picker) if picker else Turn(NOTHING_HERE)


async def _match_step(db, thread, executor, draft: dict, channel: str, page: int) -> Turn:
    """Find a provider and a price, then offer that provider's real slots."""
    if str(draft.get("serviceability_status") or "") != "serviceable":
        serviceable = await executor._tool_check_home_service_availability(
            draft_id=str(draft["id"]),
        )
        if not serviceable.get("serviceable"):
            return Turn(NO_COVERAGE.format(zipcode=draft.get("zipcode") or "that pincode"))

    price = await executor._tool_get_home_service_price_estimate(draft_id=str(draft["id"]))
    draft = await _draft(db, thread)
    if not draft:
        return Turn(NOTHING_HERE)
    if draft.get('selected_tenant_id') and 'required_fields' in draft and 'preferred_date' not in draft['required_fields']:
        return await _next_step(db, thread, executor, draft, channel, 0)

    price_block = _price_block(price)

    picker = await pickers.build_picker(
        db, draft, customer_id=thread.customer_id, channel=channel, page=page,
    )
    if not picker:
        return Turn("\n\n".join(filter(None, [price_block, NO_SLOTS])))
    # Keep the amount and the action it belongs to in one visual unit. On
    # Instagram this is one message with the slot choices directly below; on
    # WhatsApp it becomes the interactive list body.
    picker = dict(picker)
    picker["body"] = "\n\n".join(filter(None, [price_block, picker.get("body")]))
    return Turn(None, picker)


async def _confirm_step(executor, draft: dict, thread) -> Turn:
    """The summary, then one tap to create the booking."""
    result = await executor._tool_get_home_service_booking_summary(draft_id=str(draft["id"]))
    # `build_booking_summary` returns {"booking_summary": {...}, "draft_status":
    # ...}; the fields worth showing are one level in.
    envelope = result.get("summary") or {}
    summary = envelope.get("booking_summary") or envelope
    if result.get('error') or summary.get('ready_for_confirmation') is False:
        missing = ', '.join(summary.get('missing') or [])
        return Turn(result.get('error') or f"Please complete your booking details before confirming{': ' + missing if missing else '.'}")
    price = summary.get("price_estimate") or {}
    lines = ["✅ Review your booking"]
    for label, value in (
        ("Service", summary.get("offering_name")),
        ("Problem", summary.get("issue_summary") or draft.get("issue_summary")),
        ("When", _when(summary, draft)),
        ("Address", _address(summary, draft)),
        ("Phone", summary.get("customer_phone") or draft.get("customer_phone")),
        # An emergency must never be a surprise line on the final bill, so the
        # surcharge the provider configured is shown before confirmation.
        ("Emergency", _emergency_line(summary, draft)),
    ):
        if value:
            lines.append(f"{label}: {value}")
    for addon in price.get('addon_lines', []):
        lines.append(f"Add-on: {addon['name']} × {addon['quantity']} — INR {addon['total']}")
    if price.get("display_price"):
        price_label = (
            "VISIT & INSPECTION FEE"
            if price.get("requires_inspection_estimate")
            else "TOTAL PRICE"
        )
        lines.extend(["", f"💳 {price_label}", str(price["display_price"])])
        adjustment = _visit_fee_adjustment(price)
        if adjustment:
            lines.append(adjustment)
    rows = [{"id": f"{PICK_CONFIRM}{PICKER_SEP}{_YES}", "title": "Confirm booking"}]
    if price.get('social_addons_reviewed'):
        from app.engines.messaging_gateway.addons import _id
        rows.append({'id': _id(draft, 'page', 0), 'title': 'Edit add-ons'})
    rows.append({"id": f"{PICK_RESTART}{PICKER_SEP}1", "title": "Start over"})
    return Turn("\n".join(lines), {
        "body": "Shall I confirm this booking?",
        "rows": rows,
        "list_button": "Choose",
        "section_title": "Confirm",
        "presentation": "buttons",
    })


# ── Helpers ──────────────────────────────────────────────────────────────────


def _executor(db, thread):
    """The app's own booking executor, driven directly rather than by a model."""
    from app.engines.ai_conversation.backend_tools import BackendToolExecutor

    return BackendToolExecutor(
        db=db,
        customer_id=thread.customer_id,
        # Without this, `list_serviceable_offerings` drops its coverage filter
        # and offers services no tenant covers at this pincode.
        zipcode=thread.zipcode,
        session_id=str(thread.ai_session_id) if thread.ai_session_id else None,
        channel=thread.channel,
        channel_user_id=thread.channel_user_id,
        display_name=thread.display_name,
        instagram_username=getattr(thread, "channel_username", None),
    )


async def _draft(db, thread) -> dict | None:
    """The draft for this thread's session, with `required_fields` filled in."""
    if not thread.ai_session_id:
        return None
    from app.engines.admin_catalog.models import MasterService
    from app.engines.home_service_booking.models import HomeServiceBookingDraft

    row = (await db.execute(
        select(HomeServiceBookingDraft)
        .where(HomeServiceBookingDraft.ai_session_id == thread.ai_session_id)
        .order_by(HomeServiceBookingDraft.created_at.desc())
        .limit(1)
    )).scalars().first()
    if not row:
        return None
    data = row.to_dict()
    required = ["issue_summary", "city"]
    offering = await db.get(MasterService, row.offering_id) if row.offering_id else None
    if offering is not None:
        from app.engines.home_service_booking.service import HomeServiceChatbotBookingService
        required = await HomeServiceChatbotBookingService(db)._get_required_field_list(offering, row)
    data["required_fields"] = required
    return data


def _pending_number(identity, thread) -> str:
    """The number an outstanding OTP went to, so the prompt can name it.

    Reading it back proves which number is being confirmed — a customer who
    mistyped a digit can see that before wondering why no message arrived.
    """
    try:
        return identity.pending_number(thread) or "your number"
    except Exception:  # noqa: BLE001 — a label must never break the step
        return "your number"


def _phone_confirmation_pending(identity, thread) -> bool:
    try:
        return bool(identity.phone_verification_requires_confirmation(thread))
    except Exception:  # noqa: BLE001 — old/custom identity adapters mean OTP sent
        return False


def _phone_confirmation_step(identity, thread) -> Turn:
    prompt = ASK_PHONE_CONFIRM.format(number=_masked_number(identity, thread))
    # Instagram renders a picker as its own message. Putting the prompt in
    # both Turn.text and picker.body produced two consecutive confirmation
    # messages. One interactive message is the complete step.
    return Turn(None, {
        "body": prompt,
        "rows": [
            {"id": f"{PICK_PHONE}{PICKER_SEP}send", "title": "Send OTP"},
            {"id": f"{PICK_PHONE}{PICKER_SEP}change", "title": "Change number"},
        ],
        "list_button": "Choose",
        "section_title": "Phone verification",
        "presentation": "buttons",
    })


def _otp_step(identity, thread) -> Turn:
    prompt = ASK_OTP.format(number=_masked_number(identity, thread))
    return Turn(None, {
        "body": prompt,
        "rows": [{
            "id": f"{PICK_PHONE}{PICKER_SEP}change",
            "title": "Use another number",
        }],
        "list_button": "Choose",
        "section_title": "Phone verification",
        "presentation": "buttons",
        # The button is only an alternate action; the normal answer to this
        # step is the six-digit code typed into the composer.
        "allow_text": True,
    })


def _price_block(price: dict) -> str | None:
    """Prominent, customer-only price presentation for the slot step.

    Instagram does not support HTML, Markdown or selectable font sizes in a
    message body. Bold Unicode digits provide supported visual emphasis.
    """
    amount = str(price.get("display_price") or "").strip()
    if not amount:
        return None
    strong_amount = amount.translate(str.maketrans(
        "0123456789", "𝟬𝟭𝟮𝟯𝟰𝟱𝟲𝟳𝟴𝟵",
    ))
    inspection = bool(
        price.get("requires_inspection_estimate")
        or price.get("pricing_mode") == "inspection"
    )
    if not inspection:
        return (
            "━━━━━━━━━━━━━━\n"
            f"💳 𝗧𝗢𝗧𝗔𝗟 𝗣𝗥𝗜𝗖𝗘\n{strong_amount}\n"
            "━━━━━━━━━━━━━━"
        )

    lines = [
        "━━━━━━━━━━━━━━",
        "🔎 𝗩𝗜𝗦𝗜𝗧 & 𝗜𝗡𝗦𝗣𝗘𝗖𝗧𝗜𝗢𝗡 𝗙𝗘𝗘",
        strong_amount,
        "━━━━━━━━━━━━━━",
    ]
    adjustment = _visit_fee_adjustment(price)
    if adjustment:
        lines.extend(["", adjustment])
    note = str(price.get("note") or "").strip()
    if note:
        # The structured, policy-backed disclosure above is the prominent
        # one; avoid repeating the same promise from the legacy prose note.
        note = note.replace(
            "This visit fee is adjusted against your final bill if you continue with the service.",
            "",
        ).strip()
    if note:
        lines.extend(["", note])
    return "\n".join(lines)


def _visit_fee_adjustment(price: dict) -> str | None:
    policy = price.get("visit_fee_policy") or {}
    if policy.get("credited_against_work"):
        return (
            "If you approve and continue with the repair, this visit/inspection "
            "fee is adjusted against the final bill when the repair amount "
            "exceeds the fee."
        )
    return None


def _masked_number(identity, thread) -> str:
    """Recognisable without making Instagram auto-link a full phone number."""
    number = _pending_number(identity, thread)
    digits = "".join(ch for ch in number if ch.isdigit())
    return f"******{digits[-4:]}" if len(digits) >= 4 else "your number"


def _indian_mobile(digits: str) -> str | None:
    """Normalise a typed Indian mobile to E.164, or None if it is not one.

    This is an India-only product, so the country code is not asked for — a
    customer types the ten digits they know. A `91`/`091`/`+91` prefix is still
    accepted because people type what they are used to, and the leading digit
    must be 6-9, which is what separates a real mobile from a pincode or a
    house number typed into the wrong step.
    """
    if len(digits) == 12 and digits.startswith("91"):
        digits = digits[2:]
    elif len(digits) == 13 and digits.startswith("091"):
        digits = digits[3:]
    elif len(digits) == 11 and digits.startswith("0"):
        digits = digits[1:]
    if len(digits) != 10 or digits[0] not in "6789":
        return None
    return f"+91{digits}"


async def _verified_contact(db, thread) -> dict:
    """Name and number for a draft started by an already-verified customer.

    `start_home_service_draft` fills these from the WhatsApp sender itself.
    Everywhere else the number was confirmed by code before the booking began,
    so it is copied from the account it was confirmed against — otherwise the
    booking carries no phone at all and the summary cannot show one back.
    """
    if thread.channel == "whatsapp" or not thread.customer_id:
        return {}
    from app.engines.auth.models import User

    user = await db.get(User, thread.customer_id)
    if user is None or not user.phone:
        return {}
    return {"customer_phone": user.phone,
            "customer_name": user.full_name or thread.display_name or "Customer"}


async def _problem_name(db, executor, draft: dict, issue_type_id: str) -> str | None:
    result = await executor._tool_get_service_problems(draft_id=str(draft["id"]))
    for problem in result.get("problems") or []:
        if str(problem.get("id")) == issue_type_id:
            return problem.get("name")
    return None


def _booking_line(booking: dict) -> str:
    """Status and visit, so two bookings for the SAME service are distinct.

    "AC Repair — Accepted" twice over is not a choice a customer can make;
    the visit date is what tells them apart.
    """
    parts = [booking.get("status"), booking.get("when"), booking.get("number")]
    return " · ".join(str(p) for p in parts if p)


def _emergency_line(summary: dict, draft: dict) -> str | None:
    if not (summary.get("is_emergency") or draft.get("is_emergency")):
        return None
    surcharge = summary.get("emergency_surcharge")
    return f"Yes (+{surcharge})" if surcharge else "Yes"


def _when(summary: dict, draft: dict) -> str | None:
    slot = summary.get("promised_slot") or {}
    date_iso = slot.get("date") or draft.get("preferred_date")
    window = slot.get("time_window") or draft.get("preferred_time_window")
    if not date_iso:
        return None
    return f"{pickers._day_label(str(date_iso))} {window}".strip()


def _address(summary: dict, draft: dict) -> str | None:
    snapshot = draft.get("address_snapshot") or {}
    parts = [snapshot.get("address_line_1"), draft.get("city"), draft.get("zipcode")]
    joined = ", ".join(str(p) for p in parts if p)
    return joined or None


def _valid_address_line(value: str | None) -> bool:
    """Use the final booking gate's deliverable-address rule for chat steps."""
    from app.engines.serviceability.schemas import _validate_address_line

    try:
        return bool(_validate_address_line(value))
    except (TypeError, ValueError):
        return False


def _location_cta(draft: dict | None) -> dict | None:
    """A customer-controlled HTTPS map link for the confirmed service address."""
    if not draft:
        return None
    snapshot = draft.get("address_snapshot") or {}
    maps_url = str(snapshot.get("maps_url") or "").strip()
    if not maps_url.startswith("https://"):
        address = _address({}, draft)
        if not address:
            return None
        maps_url = (
            "https://www.google.com/maps/search/?api=1&query="
            + quote_plus(address)
        )
    return {
        "body": "Check the service address saved with this booking.",
        "display_text": "Open location",
        "url": maps_url,
    }
