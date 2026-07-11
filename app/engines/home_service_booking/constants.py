"""Sprint 16 — Home Service Booking Draft: constants, statuses, error codes."""

# ── Draft lifecycle statuses ──────────────────────────────────────────────────
DRAFT_STATUS_DRAFT                  = "draft"
DRAFT_STATUS_COLLECTING_DETAILS     = "collecting_details"
DRAFT_STATUS_SERVICEABILITY_CHECKED = "serviceability_checked"
DRAFT_STATUS_PRICE_ESTIMATED        = "price_estimated"
DRAFT_STATUS_PROVIDER_MATCHED       = "provider_matched"
DRAFT_STATUS_READY_FOR_CONFIRMATION = "ready_for_confirmation"
DRAFT_STATUS_CONFIRMED              = "confirmed"
DRAFT_STATUS_EXPIRED                = "expired"
DRAFT_STATUS_CANCELLED              = "cancelled"
DRAFT_STATUS_FAILED                 = "failed"

VALID_DRAFT_STATUSES = {
    DRAFT_STATUS_DRAFT,
    DRAFT_STATUS_COLLECTING_DETAILS,
    DRAFT_STATUS_SERVICEABILITY_CHECKED,
    DRAFT_STATUS_PRICE_ESTIMATED,
    DRAFT_STATUS_PROVIDER_MATCHED,
    DRAFT_STATUS_READY_FOR_CONFIRMATION,
    DRAFT_STATUS_CONFIRMED,
    DRAFT_STATUS_EXPIRED,
    DRAFT_STATUS_CANCELLED,
    DRAFT_STATUS_FAILED,
}

TERMINAL_STATUSES = {
    DRAFT_STATUS_CONFIRMED,
    DRAFT_STATUS_EXPIRED,
    DRAFT_STATUS_CANCELLED,
    DRAFT_STATUS_FAILED,
}

# ── Serviceability statuses ───────────────────────────────────────────────────
SVCABILITY_PENDING          = "pending"
SVCABILITY_SERVICEABLE      = "serviceable"
SVCABILITY_NOT_SERVICEABLE  = "not_serviceable"

# ── Price statuses ────────────────────────────────────────────────────────────
PRICE_STATUS_PENDING    = "pending"
PRICE_STATUS_ESTIMATED  = "estimated"
PRICE_STATUS_FAILED     = "failed"

# ── Provider match statuses ───────────────────────────────────────────────────
PROVIDER_MATCH_PENDING     = "pending"
PROVIDER_MATCH_MATCHED     = "matched"
PROVIDER_MATCH_NO_PROVIDER = "no_provider"

# ── Actor types (for events) ──────────────────────────────────────────────────
ACTOR_CUSTOMER = "customer"
ACTOR_AI       = "ai"
ACTOR_BACKEND  = "backend"
ACTOR_SYSTEM   = "system"

# ── Event types (for events) ──────────────────────────────────────────────────
EVENT_DRAFT_CREATED          = "draft_created"
EVENT_FIELD_COLLECTED        = "field_collected"
EVENT_PHOTO_UPLOADED         = "photo_uploaded"
EVENT_SERVICEABILITY_CHECKED = "serviceability_checked"
EVENT_PRICE_ESTIMATED        = "price_estimated"
EVENT_PROVIDER_MATCHED       = "provider_matched"
EVENT_PROVIDER_SELECTED      = "provider_selected"
EVENT_SUMMARY_GENERATED      = "summary_generated"
EVENT_CONFIRMATION_REQUESTED = "confirmation_requested"
EVENT_DRAFT_CONFIRMED        = "draft_confirmed"
EVENT_DRAFT_CANCELLED        = "draft_cancelled"
EVENT_DRAFT_FAILED           = "draft_failed"

# ── Home Services category slug ───────────────────────────────────────────────
HOME_SERVICES_CATEGORY_SLUG    = "home-services"
HOME_SERVICES_CATEGORY_ALIASES = {
    "home-services", "home_services", "home services",
    "homeservices", "home service",
}

# ── Error codes ───────────────────────────────────────────────────────────────
ERR_DRAFT_NOT_FOUND                       = "HOME_BOOKING_DRAFT_NOT_FOUND"
ERR_DRAFT_ACCESS_DENIED                   = "HOME_BOOKING_DRAFT_ACCESS_DENIED"
ERR_DRAFT_EXPIRED                         = "HOME_BOOKING_DRAFT_EXPIRED"
ERR_DRAFT_TERMINAL                        = "HOME_BOOKING_DRAFT_TERMINAL_STATUS"
ERR_CATEGORY_INVALID                      = "HOME_BOOKING_CATEGORY_INVALID"
ERR_OFFERING_INVALID                      = "HOME_BOOKING_OFFERING_INVALID"
ERR_REQUIRED_FIELD_MISSING                = "HOME_BOOKING_REQUIRED_FIELD_MISSING"
ERR_TYPE_REQUIRED                         = "HOME_BOOKING_TYPE_REQUIRED"
ERR_BRAND_REQUIRED                        = "HOME_BOOKING_BRAND_REQUIRED"
ERR_ADDRESS_REQUIRED                      = "HOME_BOOKING_ADDRESS_REQUIRED"
ERR_SERVICE_NOT_AVAILABLE                 = "HOME_BOOKING_SERVICE_NOT_AVAILABLE"
ERR_NO_PROVIDER_AVAILABLE                 = "HOME_BOOKING_NO_PROVIDER_AVAILABLE"
ERR_PRICE_ESTIMATE_FAILED                 = "HOME_BOOKING_PRICE_ESTIMATE_FAILED"
ERR_PROVIDER_NOT_BOOKABLE                 = "HOME_BOOKING_PROVIDER_NOT_BOOKABLE"
ERR_PROVIDER_NOT_IN_AREA                  = "HOME_BOOKING_PROVIDER_NOT_IN_AREA"
ERR_PROVIDER_DOES_NOT_SUPPORT_TYPE        = "HOME_BOOKING_PROVIDER_DOES_NOT_SUPPORT_TYPE"
ERR_PROVIDER_DOES_NOT_SUPPORT_BRAND       = "HOME_BOOKING_PROVIDER_DOES_NOT_SUPPORT_BRAND"
ERR_CONFIRMATION_NOT_READY                = "HOME_BOOKING_CONFIRMATION_NOT_READY"
ERR_PROVIDER_ENTITLEMENT_CHANGED          = "PROVIDER_ENTITLEMENT_CHANGED"
ERR_PHOTO_UPLOAD_FAILED                   = "HOME_BOOKING_PHOTO_UPLOAD_FAILED"
ERR_SERVICEABILITY_NOT_CHECKED            = "HOME_BOOKING_SERVICEABILITY_NOT_CHECKED"
ERR_NO_PROVIDER_IN_ZIPCODE                = "NO_PROVIDER_IN_ZIPCODE"
ERR_NO_PROVIDER_IN_CITY                   = "NO_PROVIDER_IN_CITY"

# ── Pricing model labels ──────────────────────────────────────────────────────
PRICING_MODEL_VISIT_FEE = "visit_fee_plus_quote"
PRICING_MODEL_FIXED     = "fixed"
PRICING_MODEL_HOURLY    = "hourly"

# ── Draft expiry ──────────────────────────────────────────────────────────────
DRAFT_EXPIRY_HOURS    = 24
DRAFT_MAX_PHOTOS      = 5
ALLOWED_PHOTO_TYPES   = {"image/jpeg", "image/png", "image/webp"}
MAX_PHOTO_SIZE_BYTES  = 10 * 1024 * 1024  # 10 MB
