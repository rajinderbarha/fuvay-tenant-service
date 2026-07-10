"""Sprint 29 — AI Hardening constants (extends Sprint 15 constants).

New error codes, flow types, action types, and the structured AI output contract.
"""

# ── Flow types ────────────────────────────────────────────────────────────────
FLOW_HOME_SERVICE   = "home_service_booking"
FLOW_COACHING       = "coaching_appointment"
FLOW_REAL_ESTATE    = "real_estate_lead"
FLOW_UNSUPPORTED    = "unsupported"

VALID_FLOW_TYPES = {
    FLOW_HOME_SERVICE,
    FLOW_COACHING,
    FLOW_REAL_ESTATE,
    FLOW_UNSUPPORTED,
}

# ── Required next action values ───────────────────────────────────────────────
NEXT_ACTION_ASK_QUESTION      = "ask_question"
NEXT_ACTION_SHOW_OPTIONS       = "show_backend_options"
NEXT_ACTION_UPDATE_DRAFT       = "update_draft"
NEXT_ACTION_CONFIRM_READY      = "confirm_ready"
NEXT_ACTION_HANDOFF_HUMAN      = "handoff_to_human"
NEXT_ACTION_UNSUPPORTED        = "unsupported"
NEXT_ACTION_ERROR_RECOVERY     = "error_recovery"

ALLOWED_NEXT_ACTIONS = {
    NEXT_ACTION_ASK_QUESTION,
    NEXT_ACTION_SHOW_OPTIONS,
    NEXT_ACTION_UPDATE_DRAFT,
    NEXT_ACTION_CONFIRM_READY,
    NEXT_ACTION_HANDOFF_HUMAN,
    NEXT_ACTION_UNSUPPORTED,
    NEXT_ACTION_ERROR_RECOVERY,
}

# ── Backend action request values ─────────────────────────────────────────────
BACKEND_ACTION_NONE            = "none"
BACKEND_ACTION_CREATE_DRAFT    = "create_draft"
BACKEND_ACTION_UPDATE_DRAFT    = "update_draft"
BACKEND_ACTION_GET_OPTIONS     = "get_options"
BACKEND_ACTION_VALIDATE_DRAFT  = "validate_draft"
BACKEND_ACTION_CONFIRM_DRAFT   = "confirm_draft"
BACKEND_ACTION_HANDOFF         = "handoff_to_human"

ALLOWED_BACKEND_ACTIONS = {
    BACKEND_ACTION_NONE,
    BACKEND_ACTION_CREATE_DRAFT,
    BACKEND_ACTION_UPDATE_DRAFT,
    BACKEND_ACTION_GET_OPTIONS,
    BACKEND_ACTION_VALIDATE_DRAFT,
    BACKEND_ACTION_CONFIRM_DRAFT,
    BACKEND_ACTION_HANDOFF,
}

# ── Blocked AI actions (must never appear in backend_action_request.action) ───
BLOCKED_AI_ACTIONS = {
    "create_final_booking_directly",
    "assign_provider_directly",
    "set_final_price_directly",
    "deduct_wallet_directly",
    "mark_payment_paid_directly",
    "approve_refund_directly",
    "approve_complaint_directly",
    "change_admin_config_directly",
}

# ── AI action log statuses ────────────────────────────────────────────────────
AI_ACTION_REQUESTED  = "requested"
AI_ACTION_VALIDATED  = "validated"
AI_ACTION_EXECUTED   = "executed"
AI_ACTION_BLOCKED    = "blocked"
AI_ACTION_FAILED     = "failed"

# ── New error codes (Sprint 29) ───────────────────────────────────────────────
ERR_AI_RATE_LIMIT_EXCEEDED    = "AI_RATE_LIMIT_EXCEEDED"
ERR_AI_PROMPT_TOO_LARGE       = "AI_PROMPT_TOO_LARGE"
ERR_AI_RESPONSE_INVALID       = "AI_RESPONSE_INVALID"
ERR_AI_ACTION_BLOCKED         = "AI_ACTION_BLOCKED"
ERR_AI_PROVIDER_TIMEOUT       = "AI_PROVIDER_TIMEOUT"
ERR_AI_PROVIDER_NOT_CONFIGURED= "AI_PROVIDER_NOT_CONFIGURED"
ERR_AI_UNSUPPORTED_INTENT     = "AI_UNSUPPORTED_INTENT"
ERR_AI_HANDOFF_FAILED         = "AI_HANDOFF_FAILED"
ERR_AI_SESSION_ACCESS_DENIED  = "AI_SESSION_ACCESS_DENIED"

# ── Price/provider claim patterns (hallucination detection) ───────────────────
PRICE_CLAIM_PATTERNS = [
    r"₹\s*\d+",
    r"rs\.?\s*\d+",
    r"inr\s*\d+",
    r"\d+\s*rupees?",
    r"price is \d+",
    r"costs? \d+",
    r"charges? \d+",
    r"fee is \d+",
    r"starting from ₹",       # allowed only if sourced from backend
]

PROVIDER_CLAIM_PATTERNS = [
    r"provider [a-z0-9\-]+ is available",
    r"[a-z]+ services? will come",
    r"i have assigned",
    r"your technician is [a-z]+",
    r"booked with [a-z]+",
]

# ── Rate limiting ─────────────────────────────────────────────────────────────
AI_RATE_LIMIT_MESSAGES_PER_SESSION  = 50   # already covered by MAX_TURNS_PER_SESSION
AI_RATE_LIMIT_MESSAGES_PER_MINUTE   = 10   # per customer per minute
AI_RATE_LIMIT_SESSIONS_PER_HOUR     = 5    # new sessions per customer per hour
AI_MAX_PROMPT_CHARS                 = 8000
AI_MAX_RESPONSE_CHARS               = 4000
AI_FAILURE_COOLDOWN_COUNT           = 5    # repeated failures before cooldown
AI_FAILURE_COOLDOWN_MINUTES         = 10   # cooldown window in minutes

# ── Safe fallback message ─────────────────────────────────────────────────────
AI_SAFE_FALLBACK_MESSAGE = (
    "I'm having trouble processing your request right now. "
    "Please try again in a moment or contact our support team for immediate assistance."
)

# ── Structured output contract keys ──────────────────────────────────────────
AI_CONTRACT_REQUIRED_KEYS = {
    "intent",
    "customer_message",
    "required_next_action",
}
