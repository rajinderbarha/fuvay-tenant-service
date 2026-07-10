"""Sprint 18 — Real Estate Lead Flow constants."""

# ── Draft statuses ─────────────────────────────────────────────────────────────
DRAFT_STATUS_DRAFT                 = "draft"
DRAFT_STATUS_COLLECTING            = "collecting_details"
DRAFT_STATUS_LOCATION_CHECKED      = "location_checked"
DRAFT_STATUS_PROVIDERS_FOUND       = "providers_found"
DRAFT_STATUS_NO_EXACT_MATCH        = "no_provider_exact_match"
DRAFT_STATUS_FALLBACK_AVAILABLE    = "fallback_available"
DRAFT_STATUS_READY                 = "ready_for_confirmation"
DRAFT_STATUS_CONFIRMED             = "confirmed"
DRAFT_STATUS_EXPIRED               = "expired"
DRAFT_STATUS_CANCELLED             = "cancelled"
DRAFT_STATUS_FAILED                = "failed"

TERMINAL_STATUSES = {
    DRAFT_STATUS_CONFIRMED,
    DRAFT_STATUS_EXPIRED,
    DRAFT_STATUS_CANCELLED,
    DRAFT_STATUS_FAILED,
}

# ── Lead intent ────────────────────────────────────────────────────────────────
INTENT_BUY          = "buy"
INTENT_RENT         = "rent"
INTENT_SELL         = "sell"
INTENT_SITE_VISIT   = "site_visit"
INTENT_CONSULTATION = "consultation"
INTENT_COMMERCIAL   = "commercial"
INTENT_PLOT         = "plot"
INTENT_UNKNOWN      = "unknown"

VALID_INTENTS = {
    INTENT_BUY, INTENT_RENT, INTENT_SELL, INTENT_SITE_VISIT,
    INTENT_CONSULTATION, INTENT_COMMERCIAL, INTENT_PLOT, INTENT_UNKNOWN,
}

# ── Property types ─────────────────────────────────────────────────────────────
PROPERTY_HOUSE      = "house"
PROPERTY_FLAT       = "flat"
PROPERTY_APARTMENT  = "apartment"
PROPERTY_VILLA      = "villa"
PROPERTY_PLOT       = "plot"
PROPERTY_SHOP       = "shop"
PROPERTY_OFFICE     = "office"
PROPERTY_COMMERCIAL = "commercial"
PROPERTY_LAND       = "land"
PROPERTY_OTHER      = "other"

VALID_PROPERTY_TYPES = {
    PROPERTY_HOUSE, PROPERTY_FLAT, PROPERTY_APARTMENT, PROPERTY_VILLA,
    PROPERTY_PLOT, PROPERTY_SHOP, PROPERTY_OFFICE, PROPERTY_COMMERCIAL,
    PROPERTY_LAND, PROPERTY_OTHER,
}

# ── Furnishing ─────────────────────────────────────────────────────────────────
FURNISHING_FURNISHED      = "furnished"
FURNISHING_SEMI           = "semi_furnished"
FURNISHING_UNFURNISHED    = "unfurnished"
FURNISHING_NOT_SURE       = "not_sure"

# ── Possession preference ──────────────────────────────────────────────────────
POSSESSION_READY          = "ready_to_move"
POSSESSION_UNDER          = "under_construction"
POSSESSION_ANY            = "any"

# ── Match scopes for routing rules ────────────────────────────────────────────
SCOPE_EXACT_ZIPCODE  = "exact_zipcode"
SCOPE_LOCALITY       = "locality"
SCOPE_CITY           = "city"
SCOPE_DISTRICT       = "district"
SCOPE_ZONE           = "zone"
SCOPE_FALLBACK_CITY  = "fallback_city"

# ── Actor types ────────────────────────────────────────────────────────────────
ACTOR_CUSTOMER = "customer"
ACTOR_AI       = "ai"
ACTOR_BACKEND  = "backend"
ACTOR_SYSTEM   = "system"

# ── Event types ────────────────────────────────────────────────────────────────
EVENT_DRAFT_CREATED        = "draft_created"
EVENT_FIELD_COLLECTED      = "field_collected"
EVENT_LOCATION_CHECKED     = "location_checked"
EVENT_PROVIDERS_FOUND      = "providers_found"
EVENT_NO_EXACT_MATCH       = "no_provider_exact_match"
EVENT_FALLBACK_PREPARED    = "fallback_prepared"
EVENT_AGENT_SUGGESTED      = "agent_suggested"
EVENT_LEAD_SCORED          = "lead_scored"
EVENT_SUMMARY_GENERATED    = "summary_generated"
EVENT_CONFIRMATION_REQUESTED = "confirmation_requested"
EVENT_DRAFT_CONFIRMED      = "draft_confirmed"
EVENT_DRAFT_CANCELLED      = "draft_cancelled"
EVENT_DRAFT_FAILED         = "draft_failed"
EVENT_DRAFT_EXPIRED        = "draft_expired"

# ── Lead score labels ──────────────────────────────────────────────────────────
SCORE_COLD = "cold"
SCORE_WARM = "warm"
SCORE_HOT  = "hot"

SCORE_THRESHOLD_WARM = 40
SCORE_THRESHOLD_HOT  = 70

# ── Real Estate category aliases ───────────────────────────────────────────────
REAL_ESTATE_CATEGORY_ALIASES = {
    "real-estate", "real_estate", "real estate", "realestate",
    "property", "properties", "housing", "land", "plot",
    "residential", "commercial-property",
}

# ── Error codes ────────────────────────────────────────────────────────────────
ERR_DRAFT_NOT_FOUND              = "REAL_ESTATE_LEAD_DRAFT_NOT_FOUND"
ERR_DRAFT_ACCESS_DENIED          = "REAL_ESTATE_LEAD_DRAFT_ACCESS_DENIED"
ERR_DRAFT_EXPIRED                = "REAL_ESTATE_LEAD_DRAFT_EXPIRED"
ERR_CATEGORY_INVALID             = "REAL_ESTATE_CATEGORY_INVALID"
ERR_OFFERING_INVALID             = "REAL_ESTATE_OFFERING_INVALID"
ERR_REQUIRED_FIELD_MISSING       = "REAL_ESTATE_REQUIRED_FIELD_MISSING"
ERR_INTENT_REQUIRED              = "REAL_ESTATE_INTENT_REQUIRED"
ERR_PROPERTY_TYPE_REQUIRED       = "REAL_ESTATE_PROPERTY_TYPE_REQUIRED"
ERR_LOCATION_REQUIRED            = "REAL_ESTATE_LOCATION_REQUIRED"
ERR_CONTACT_REQUIRED             = "REAL_ESTATE_CONTACT_REQUIRED"
ERR_NO_PROVIDER_AVAILABLE        = "REAL_ESTATE_NO_PROVIDER_AVAILABLE"
ERR_NO_EXACT_PROVIDER_MATCH      = "REAL_ESTATE_NO_EXACT_PROVIDER_MATCH"
ERR_FALLBACK_AVAILABLE           = "REAL_ESTATE_FALLBACK_AVAILABLE"
ERR_PROVIDER_NOT_BOOKABLE        = "REAL_ESTATE_PROVIDER_NOT_BOOKABLE"
ERR_PROVIDER_SUBSCRIPTION_INACTIVE = "REAL_ESTATE_PROVIDER_SUBSCRIPTION_INACTIVE"
ERR_PROVIDER_LOCATION_UNSUPPORTED  = "REAL_ESTATE_PROVIDER_LOCATION_UNSUPPORTED"
ERR_AGENT_NOT_AVAILABLE          = "REAL_ESTATE_AGENT_NOT_AVAILABLE"
ERR_LEAD_SCORE_FAILED            = "REAL_ESTATE_LEAD_SCORE_FAILED"
ERR_CONFIRMATION_NOT_READY       = "REAL_ESTATE_CONFIRMATION_NOT_READY"
ERR_FAKE_PROVIDER_BLOCKED        = "REAL_ESTATE_FAKE_PROVIDER_BLOCKED"
ERR_ROUTING_RULE_INVALID         = "REAL_ESTATE_ROUTING_RULE_INVALID"
# Site visit date/time is captured but NOT validated against agent availability
# in Sprint 18. Sprint 19+ must check agent calendar before confirming.
ERR_SITE_VISIT_AVAILABILITY_NOT_VALIDATED = "REAL_ESTATE_SITE_VISIT_AVAILABILITY_NOT_VALIDATED"

# ── Defaults ───────────────────────────────────────────────────────────────────
DEFAULT_MAX_PROVIDERS      = 5
DEFAULT_DRAFT_EXPIRY_HOURS = 48
