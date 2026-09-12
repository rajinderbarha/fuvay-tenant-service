"""Messaging Gateway — WhatsApp/Instagram inbound channel constants.

This engine is a CHANNEL ADAPTER, not a second bot. The conversational agent
already exists: `app.engines.ai_conversation` is a DeepSeek tool-calling agent
that can drive an entire home-service booking draft end to end
(_tool_start_home_service_draft, _tool_get_service_problems,
_tool_check_home_service_availability, _tool_get_home_service_price_estimate,
...). Everything here does is:

    inbound Meta webhook  ->  resolve the sender to a customer account
                          ->  map the thread to an AIConversationSession
                          ->  hand the text to the existing agent
                          ->  send the agent's reply back out

No prompt, no tool and no booking logic lives in this engine.
"""
from __future__ import annotations

ENGINE_ID = "messaging_gateway"

# ── Channels ─────────────────────────────────────────────────────────────────
CHANNEL_WHATSAPP = "whatsapp"
CHANNEL_INSTAGRAM = "instagram"
VALID_CHANNELS = {CHANNEL_WHATSAPP, CHANNEL_INSTAGRAM}

# Encrypted configuration-store keys. These are intentionally distinct from
# the notification engine's Twilio ``whatsapp`` delivery provider.
CONFIG_CHANNEL_WHATSAPP = "wa_booking"
CONFIG_CHANNEL_INSTAGRAM = "ig_booking"
CONFIG_CHANNEL_BY_PUBLIC = {
    CHANNEL_WHATSAPP: CONFIG_CHANNEL_WHATSAPP,
    CHANNEL_INSTAGRAM: CONFIG_CHANNEL_INSTAGRAM,
}
DEFAULT_GRAPH_API_VERSION = "v26.0"

# ── Commands ─────────────────────────────────────────────────────────────────
# `/fuvay` is an OPTIONAL entry point: any message starts or continues a
# conversation, and `/fuvay` explicitly starts over. Requiring it would lose
# every customer who simply writes "AC not cooling" and gets no reply.
COMMAND_PREFIX = "/"
CMD_START = "fuvay"
CMD_RESET = "reset"
CMD_STOP = "stop"
CMD_HELP = "help"
CMD_HUMAN = "human"
CMD_TRACK = "track"
CMD_LINK = "link"
CMD_VERIFY = "verify"

#: Commands understood regardless of casing or surrounding whitespace.
KNOWN_COMMANDS = {
    CMD_START, CMD_RESET, CMD_STOP, CMD_HELP, CMD_HUMAN, CMD_TRACK,
    CMD_LINK, CMD_VERIFY,
}

#: How long a chat may go quiet before the next message opens a NEW
#: conversation rather than continuing the old one.
#:
#: The thread remembers `zipcode`/`city` indefinitely, so without this a
#: customer whose pincode was uncovered yesterday was answered "we do not
#: cover that yet" to every later message forever. Confirmed live on
#: Instagram.
#:
#: A greeting word is deliberately NOT the trigger. Matching on "hi" both
#: missed the customer who opens with an emoji or "AC not cooling", and
#: restarted mid-booking for anyone who typed "hi" as a filler line. The
#: honest signal is the gap itself: after this long the previous conversation
#: is over, so whatever arrives next is an opener. Inside the window nothing
#: restarts except an explicit /fuvay or /reset.
SESSION_IDLE_TIMEOUT_HOURS = 1

HELP_TEXT = (
    "I can book a home service for you, or show you where an existing "
    "booking has got to.\n\n"
    "Everything is a tap — just choose from the options I show you. "
    "Send /fuvay at any time to start over."
)

STOP_TEXT = (
    "You will not receive further automated messages on this number. "
    "Send /fuvay any time to start again."
)

HANDOFF_TEXT = (
    "I have asked a member of the team to pick this up. "
    "They will reply on this chat."
)

# ── Delivery outcomes (persisted on the inbound record) ──────────────────────
STATUS_RECEIVED = "received"
STATUS_PROCESSED = "processed"
STATUS_IGNORED = "ignored"
STATUS_FAILED = "failed"
STATUS_DUPLICATE = "duplicate"

# ── Errors ───────────────────────────────────────────────────────────────────
ERR_SIGNATURE_INVALID = "MESSAGING_SIGNATURE_INVALID"
ERR_VERIFY_TOKEN_INVALID = "MESSAGING_VERIFY_TOKEN_INVALID"
ERR_CHANNEL_NOT_CONFIGURED = "MESSAGING_CHANNEL_NOT_CONFIGURED"

# ── Limits ───────────────────────────────────────────────────────────────────
#: WhatsApp hard-caps a text body at 4096 characters.
MAX_OUTBOUND_CHARS = 4096

#: A single sender may not open more than this many sessions in an hour. The
#: agent has its own per-session turn cap (MAX_TURNS_PER_SESSION); this guards
#: the cheaper abuse of repeatedly starting fresh sessions.
#:
#: The cap itself is enforced by the `booking:social_session` rate limit, which
#: is where the (3600, 6) window actually lives -- it has to be Redis-backed to
#: survive the restart it is counting. Keep the two in step. What is left here
#: is the derived per-thread message ceiling below.
MAX_SESSIONS_PER_SENDER_PER_HOUR = 6

# ── In-chat pickers ──────────────────────────────────────────────────────────
# Choosing an AC type, a brand or a slot is a pick-list, not a sentence. Rather
# than send the customer out to a web screen, the gateway renders the SAME
# option set the customer app renders (`question_flow_service`'s
# `current_question.options`, `list_available_slots`) as a native WhatsApp
# interactive list or Instagram quick replies, and maps the tap straight back
# onto the draft. Meta's own caps drive these numbers:
#:   list rows: 10 total, title 24 chars, description 72
#:   reply buttons: 3, title 20 chars
#:   Instagram quick replies: 13, title 20 chars
MAX_WA_LIST_ROWS = 10
MAX_WA_BUTTONS = 3
MAX_IG_QUICK_REPLIES = 13
MAX_IG_GENERIC_ELEMENTS = 10
IG_GENERIC_TITLE_CHARS = 80
IG_GENERIC_SUBTITLE_CHARS = 80
#: Instagram has no list message: quick replies render as a single horizontal
#: strip of chips that scrolls off-screen, so a long option set is unreadable.
#: Options are therefore sent as a NUMBERED, stacked text list that the
#: customer answers with a number — which also survives clients that render
#: quick replies inconsistently.
MAX_IG_STACKED_OPTIONS = 12
WA_ROW_TITLE_CHARS = 24
WA_ROW_DESCRIPTION_CHARS = 72
WA_BUTTON_TITLE_CHARS = 20
#: An interactive body is capped well below a plain text body.
MAX_INTERACTIVE_BODY_CHARS = 1024

#: The bundled WhatsApp Flow has one terminal scheduling screen. Fuvay
#: injects live slots at send time and processes the resulting ``nfm_reply``
#: through the same slot-selection service as an ordinary list tap.
WHATSAPP_BOOKING_FLOW_SCREEN = "BOOKING_SLOT"
WHATSAPP_BOOKING_FLOW_CTA = "Complete booking"
WHATSAPP_FLOW_TOKEN_TTL_HOURS = 48

#: Row-id grammar. Every id is self-describing so a tap needs no server-side
#: "what did I last ask?" state — a resumed conversation, a redelivered
#: webhook and a tap on an older message all resolve identically.
PICKER_SEP = "|"
PICK_QUESTION = "qf"      # qf|<question_id>|<option_id>
PICK_SLOT = "sl"          # sl|<date>|<time_window>
PICK_MORE = "more"        # more|<kind>|<page>
PICKER_PREFIXES = (PICK_QUESTION, PICK_SLOT, PICK_MORE)

# Steps that are a choice between admin-defined rows, and so are asked as a
# picker rather than a sentence. Every id is `<prefix>|<value>[|<value>]`.
PICK_CATEGORY = "cat"     # cat|<category_slug>
PICK_OFFERING = "of"      # of|<category_slug>|<offering_slug>
PICK_PROBLEM = "pb"       # pb|<issue_type_id>
PICK_CONFIRM = "cf"       # cf|yes / cf|no
PICK_DUPLICATE = "dup"    # dup|<draft_id>|yes/no — explicit same-problem rebooking
PICK_EMERGENCY = "em"     # em|on / em|off — switch between the two slot lists
PICK_RESTART = "rs"       # rs|1 — abandon this booking and start a new one
PICK_TRACK = "tr"         # tr|<booking_number> — where has my booking got to
PICK_AREA = "ar"          # ar|<zipcode> — the exact pincode we cover
PICK_AREA_CITY = "ac"     # ac|<city> — narrow to that city's pincodes
PICK_CANCEL = "cx"        # cx|<booking_number> — ask, then cx|<number>|<reason>
PICK_SKIP = "sk"          # sk|location — carry on without a location pin
PICK_PARTS = "pt"         # pt|<parts_request_id>|approve / decline
PICK_QUOTE = "qt"         # qt|<quote_id>|approve / decline / revise
PICK_HANDOVER = "ho"      # ho|<job_id>|acknowledge
PICK_PAYMENT = "pay"      # pay|<payment_id>|confirm / not_paid
PICK_PHONE = "phone"      # phone|change — discard pending OTP and enter another number
PICK_ADDON = "ao"         # ao|draft_id|price_token|action|mapping_id|quantity
PICK_DIMENSION = "dim"    # dim|<dimension_key>|<value_id> — e.g. dim|type|<uuid>
PICK_RATING = "rt"        # rt|<booking_id>|<1-5> — see rating_request.py
PICKER_PREFIXES = (
    PICK_QUESTION, PICK_SLOT, PICK_MORE,
    PICK_CATEGORY, PICK_OFFERING, PICK_PROBLEM, PICK_CONFIRM, PICK_DUPLICATE,
    PICK_EMERGENCY,
    PICK_RESTART, PICK_TRACK, PICK_AREA, PICK_AREA_CITY, PICK_CANCEL,
    PICK_SKIP, PICK_PARTS, PICK_QUOTE, PICK_HANDOVER, PICK_PAYMENT, PICK_PHONE, PICK_ADDON,
    PICK_DIMENSION, PICK_RATING,
)

#: The Job-Type Blueprint dimensions the chat can ask for, mapped to the draft
#: column each answer lands in. Order comes from `catalog_dimensions`, not from
#: here — this only says which keys are answerable in a conversation.
DIMENSION_DRAFT_FIELD = {
    "type": "offering_type_id",
    "brand": "brand_id",
}

#: Taps that answer something the BUSINESS asked, on a message it sent at a
#: time of its choosing. A parts approval raised at 2pm and tapped at 5pm is
#: the normal case, not a stale one, so the idle-session rule must not swallow
#: these in a welcome message -- the customer would have approved nothing and
#: the technician would still be waiting. Ordinary booking taps are not here:
#: after an hour those genuinely are a new conversation.
DURABLE_ACTION_PICKS = {
    PICK_TRACK, PICK_CANCEL, PICK_PARTS, PICK_QUOTE, PICK_HANDOVER, PICK_PAYMENT,
    PICK_RATING,
}

#: Where a finished job's "how would you rate it?" is asked. Instagram only for
#: now; the prompt and the tap handling are channel-neutral (WhatsApp renders
#: the same five options as a list), so adding WhatsApp is this line alone.
RATING_REQUEST_CHANNELS = (CHANNEL_INSTAGRAM,)

#: WhatsApp only allows a business-initiated message outside this window via a
#: pre-approved template; inside it, an ordinary message is fine. Instagram
#: applies the same 24 hours and has no template mechanism at all. So a parts
#: request raised while the customer is quiet waits for them to write in.
CUSTOMER_SERVICE_WINDOW_HOURS = 24

#: A booking a customer can still be waiting on. Anything else — completed,
#: cancelled — is history, and offering to track it would be noise.
LIVE_BOOKING_STATUSES = (
    # Canonical statuses from execution.constants. Keep every non-terminal
    # state here so chat does not lose a booking as field work progresses.
    "pending_assignment", "assigned", "accepted", "scheduled",
    "on_the_way", "reached_site", "inspection_started", "inspection_done",
    "quote_required", "service_started", "work_done",
    "customer_not_available",
)

#: Marks a slot row taken from the EMERGENCY list (`sl|<date>|<window>|e`), so
#: the tap alone tells `select_promised_slot` which list it came from — that
#: call is what records `is_emergency` and prices the surcharge.
SLOT_EMERGENCY_FLAG = "e"

#: The exact phrase the booking service demands before creating final records.
CONFIRM_PHRASE = "CONFIRM BOOKING"
