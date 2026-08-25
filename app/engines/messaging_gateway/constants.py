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

#: Commands understood regardless of casing or surrounding whitespace.
KNOWN_COMMANDS = {CMD_START, CMD_RESET, CMD_STOP, CMD_HELP, CMD_HUMAN}

HELP_TEXT = (
    "I can help you book a home service, check an existing booking, or answer "
    "questions about what we cover.\n\n"
    "Just tell me what you need — for example \"AC not cooling in Ludhiana\".\n\n"
    "Commands:\n"
    "/fuvay — start over\n"
    "/human — talk to a person\n"
    "/stop — stop messages"
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
MAX_SESSIONS_PER_SENDER_PER_HOUR = 6
