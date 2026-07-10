"""Sprint 17 — Coaching Appointment Draft: constants, statuses, error codes."""

# ── Draft lifecycle statuses ──────────────────────────────────────────────────
DRAFT_STATUS_DRAFT                  = "draft"
DRAFT_STATUS_COLLECTING_DETAILS     = "collecting_details"
DRAFT_STATUS_LOCATION_CHECKED       = "location_checked"
DRAFT_STATUS_SLOTS_LOADED           = "slots_loaded"
DRAFT_STATUS_SLOT_SELECTED          = "slot_selected"
DRAFT_STATUS_READY_FOR_CONFIRMATION = "ready_for_confirmation"
DRAFT_STATUS_CONFIRMED              = "confirmed"
DRAFT_STATUS_EXPIRED                = "expired"
DRAFT_STATUS_CANCELLED              = "cancelled"
DRAFT_STATUS_FAILED                 = "failed"

TERMINAL_STATUSES = {
    DRAFT_STATUS_CONFIRMED,
    DRAFT_STATUS_EXPIRED,
    DRAFT_STATUS_CANCELLED,
    DRAFT_STATUS_FAILED,
}

# ── Location / center discovery statuses ──────────────────────────────────────
LOC_STATUS_PENDING       = "pending"
LOC_STATUS_AVAILABLE     = "available"
LOC_STATUS_NOT_AVAILABLE = "not_available"

# ── Slot statuses ─────────────────────────────────────────────────────────────
SLOT_STATUS_PENDING          = "pending"
SLOT_STATUS_LOADED           = "loaded"
SLOT_STATUS_NO_SLOT          = "no_slot_on_requested_date"
SLOT_STATUS_NEXT_FOUND       = "next_available_found"
SLOT_STATUS_SELECTED         = "selected"
SLOT_STATUS_HELD             = "held"
SLOT_STATUS_FALLBACK         = "fallback_prepared"

# ── Fee statuses ─────────────────────────────────────────────────────────────
FEE_STATUS_PENDING   = "pending"
FEE_STATUS_ESTIMATED = "estimated"
FEE_STATUS_FREE      = "free"
FEE_STATUS_FAILED    = "failed"

# ── Slot hold statuses ────────────────────────────────────────────────────────
HOLD_STATUS_HELD      = "held"
HOLD_STATUS_RELEASED  = "released"
HOLD_STATUS_CONVERTED = "converted"
HOLD_STATUS_EXPIRED   = "expired"

SLOT_HOLD_EXPIRY_MINUTES = 15

# ── Preferred modes ───────────────────────────────────────────────────────────
MODE_ONLINE  = "online"
MODE_OFFLINE = "offline"
MODE_HYBRID  = "hybrid"

VALID_MODES = {MODE_ONLINE, MODE_OFFLINE, MODE_HYBRID}

# ── Actor types (for events) ──────────────────────────────────────────────────
ACTOR_CUSTOMER = "customer"
ACTOR_AI       = "ai"
ACTOR_BACKEND  = "backend"
ACTOR_SYSTEM   = "system"

# ── Event types ───────────────────────────────────────────────────────────────
EVENT_DRAFT_CREATED               = "draft_created"
EVENT_FIELD_COLLECTED             = "field_collected"
EVENT_PROVIDER_OPTIONS_LOADED     = "provider_options_loaded"
EVENT_SLOTS_LOADED                = "slots_loaded"
EVENT_NO_SLOT_ON_REQUESTED_DATE   = "no_slot_on_requested_date"
EVENT_NEXT_AVAILABLE_SLOTS_LOADED = "next_available_slots_loaded"
EVENT_RECOMMENDED_SLOT_SUGGESTED  = "recommended_slot_suggested"
EVENT_SLOT_SELECTED               = "slot_selected"
EVENT_SLOT_HELD                   = "slot_held"
EVENT_FEE_ESTIMATED               = "fee_estimated"
EVENT_FALLBACK_INQUIRY_PREPARED   = "fallback_inquiry_prepared"
EVENT_SUMMARY_GENERATED           = "summary_generated"
EVENT_CONFIRMATION_REQUESTED      = "confirmation_requested"
EVENT_DRAFT_CONFIRMED             = "draft_confirmed"
EVENT_DRAFT_CANCELLED             = "draft_cancelled"
EVENT_DRAFT_FAILED                = "draft_failed"

# ── Coaching category slug identifiers ────────────────────────────────────────
COACHING_CATEGORY_ALIASES = {
    "coaching-center", "coaching_center", "coaching center",
    "coachingcenter", "ielts", "coaching", "education",
}

# ── Next-slot search defaults ─────────────────────────────────────────────────
DEFAULT_SEARCH_DAYS  = 14
DEFAULT_SLOT_LIMIT   = 5
DRAFT_EXPIRY_HOURS   = 24

# ── Error codes ───────────────────────────────────────────────────────────────
ERR_DRAFT_NOT_FOUND                 = "COACHING_APPOINTMENT_DRAFT_NOT_FOUND"
ERR_DRAFT_ACCESS_DENIED             = "COACHING_APPOINTMENT_DRAFT_ACCESS_DENIED"
ERR_DRAFT_EXPIRED                   = "COACHING_APPOINTMENT_DRAFT_EXPIRED"
ERR_DRAFT_TERMINAL                  = "COACHING_APPOINTMENT_DRAFT_TERMINAL_STATUS"
ERR_CATEGORY_INVALID                = "COACHING_CATEGORY_INVALID"
ERR_OFFERING_INVALID                = "COACHING_OFFERING_INVALID"
ERR_REQUIRED_FIELD_MISSING          = "COACHING_REQUIRED_FIELD_MISSING"
ERR_MODE_REQUIRED                   = "COACHING_MODE_REQUIRED"
ERR_LOCATION_REQUIRED               = "COACHING_LOCATION_REQUIRED"
ERR_DATE_REQUIRED                   = "COACHING_DATE_REQUIRED"
ERR_SLOT_REQUIRED                   = "COACHING_SLOT_REQUIRED"
ERR_NO_CENTER_AVAILABLE             = "COACHING_NO_CENTER_AVAILABLE"
ERR_NO_SLOT_AVAILABLE               = "COACHING_NO_SLOT_AVAILABLE"
ERR_NO_SLOT_ON_REQUESTED_DATE       = "COACHING_NO_SLOT_ON_REQUESTED_DATE"
ERR_NEXT_AVAILABLE_SLOT_NOT_FOUND   = "COACHING_NEXT_AVAILABLE_SLOT_NOT_FOUND"
ERR_SLOT_ALREADY_HELD               = "COACHING_SLOT_ALREADY_HELD"
ERR_SLOT_ALREADY_BOOKED             = "COACHING_SLOT_ALREADY_BOOKED"
ERR_SLOT_HOLD_EXPIRED               = "COACHING_SLOT_HOLD_EXPIRED"
ERR_FEE_ESTIMATE_FAILED             = "COACHING_FEE_ESTIMATE_FAILED"
ERR_PROVIDER_NOT_BOOKABLE           = "COACHING_PROVIDER_NOT_BOOKABLE"
ERR_PROVIDER_SUBSCRIPTION_INACTIVE  = "COACHING_PROVIDER_SUBSCRIPTION_INACTIVE"
ERR_CONFIRMATION_NOT_READY          = "COACHING_CONFIRMATION_NOT_READY"
ERR_FALLBACK_INQUIRY_PREPARED       = "COACHING_FALLBACK_INQUIRY_PREPARED"
ERR_FAKE_SLOT_BLOCKED               = "COACHING_FAKE_SLOT_BLOCKED"
