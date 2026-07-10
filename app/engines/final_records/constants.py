"""Sprint 19 — Final Records constants."""

# ── Draft types ────────────────────────────────────────────────────────────────
DRAFT_TYPE_HOME_SERVICE = "home_service"
DRAFT_TYPE_COACHING     = "coaching"
DRAFT_TYPE_REAL_ESTATE  = "real_estate"

VALID_DRAFT_TYPES = {DRAFT_TYPE_HOME_SERVICE, DRAFT_TYPE_COACHING, DRAFT_TYPE_REAL_ESTATE}

# ── Result types ───────────────────────────────────────────────────────────────
RESULT_TYPE_SERVICE_BOOKING         = "service_booking"
RESULT_TYPE_COACHING_APPOINTMENT    = "coaching_appointment"
RESULT_TYPE_REAL_ESTATE_LEAD        = "real_estate_lead"

# ── Confirmation statuses ──────────────────────────────────────────────────────
CONFIRM_STATUS_CREATED = "created"
CONFIRM_STATUS_FAILED  = "failed"

# ── Service booking statuses ───────────────────────────────────────────────────
BOOKING_STATUS_PENDING_ASSIGNMENT = "pending_assignment"
BOOKING_STATUS_ASSIGNED           = "assigned"
BOOKING_STATUS_IN_PROGRESS        = "in_progress"
BOOKING_STATUS_COMPLETED          = "completed"
BOOKING_STATUS_CANCELLED          = "cancelled"

# ── Service job statuses ───────────────────────────────────────────────────────
JOB_STATUS_PENDING_ASSIGNMENT = "pending_assignment"
JOB_STATUS_ASSIGNED           = "assigned"
JOB_STATUS_DISPATCHED         = "dispatched"
JOB_STATUS_IN_PROGRESS        = "in_progress"
JOB_STATUS_COMPLETED          = "completed"
JOB_STATUS_CANCELLED          = "cancelled"

# ── Coaching appointment statuses ──────────────────────────────────────────────
APPT_STATUS_CONFIRMED  = "confirmed"
APPT_STATUS_COMPLETED  = "completed"
APPT_STATUS_CANCELLED  = "cancelled"
APPT_STATUS_NO_SHOW    = "no_show"

# ── Real estate lead statuses ──────────────────────────────────────────────────
LEAD_STATUS_NEW        = "new"
LEAD_STATUS_CONTACTED  = "contacted"
LEAD_STATUS_QUALIFIED  = "qualified"
LEAD_STATUS_CONVERTED  = "converted"
LEAD_STATUS_REJECTED   = "rejected"

# ── Audit log actions ──────────────────────────────────────────────────────────
AUDIT_BOOKING_CREATED          = "booking_created"
AUDIT_APPOINTMENT_CREATED      = "appointment_created"
AUDIT_LEAD_CREATED             = "lead_created"
AUDIT_CONFIRMATION_DUPLICATE   = "confirmation_duplicate"
AUDIT_CONFIRMATION_FAILED      = "confirmation_failed"

# ── Number prefixes ────────────────────────────────────────────────────────────
NUMBER_PREFIX_BOOKING     = "BK"
NUMBER_PREFIX_JOB         = "JOB"
NUMBER_PREFIX_APPOINTMENT = "APPT"
NUMBER_PREFIX_LEAD        = "LEAD"

# ── Error codes ────────────────────────────────────────────────────────────────
ERR_DRAFT_NOT_FOUND            = "FINAL_DRAFT_NOT_FOUND"
ERR_DRAFT_NOT_READY            = "FINAL_DRAFT_NOT_READY"
ERR_DRAFT_ALREADY_CONFIRMED    = "FINAL_DRAFT_ALREADY_CONFIRMED"
ERR_DUPLICATE_CONFIRMATION     = "FINAL_DUPLICATE_CONFIRMATION"
ERR_INVALID_DRAFT_TYPE         = "FINAL_INVALID_DRAFT_TYPE"
ERR_BOOKING_NOT_FOUND          = "FINAL_BOOKING_NOT_FOUND"
ERR_APPOINTMENT_NOT_FOUND      = "FINAL_APPOINTMENT_NOT_FOUND"
ERR_LEAD_NOT_FOUND             = "FINAL_LEAD_NOT_FOUND"
ERR_JOB_NOT_FOUND              = "FINAL_JOB_NOT_FOUND"
ERR_ACCESS_DENIED              = "FINAL_ACCESS_DENIED"
ERR_NUMBER_GENERATION_FAILED   = "FINAL_NUMBER_GENERATION_FAILED"
ERR_PROVIDER_REQUIRED          = "FINAL_PROVIDER_REQUIRED"
ERR_PRICE_NOT_VALIDATED        = "FINAL_PRICE_NOT_VALIDATED"
ERR_SLOT_NOT_VALIDATED         = "FINAL_SLOT_NOT_VALIDATED"
ERR_LOCATION_NOT_VALIDATED     = "FINAL_LOCATION_NOT_VALIDATED"
ERR_CUSTOMER_INFO_MISSING      = "FINAL_CUSTOMER_INFO_MISSING"
ERR_CATEGORY_MISMATCH          = "FINAL_CATEGORY_MISMATCH"
ERR_CREATION_FAILED            = "FINAL_CREATION_FAILED"
ERR_AUDIT_LOG_FAILED           = "FINAL_AUDIT_LOG_FAILED"
ERR_CONFIRMATION_LOCK_FAILED   = "FINAL_CONFIRMATION_LOCK_FAILED"
ERR_DRAFT_TYPE_UNKNOWN         = "FINAL_DRAFT_TYPE_UNKNOWN"
ERR_ACTIVITY_FETCH_FAILED      = "FINAL_ACTIVITY_FETCH_FAILED"
ERR_SLOT_HOLD_MISSING          = "CONFIRMATION_SLOT_HOLD_MISSING"
ERR_SLOT_HOLD_EXPIRED          = "CONFIRMATION_SLOT_HOLD_EXPIRED"
ERR_SLOT_HOLD_ALREADY_CONVERTED = "CONFIRMATION_SLOT_HOLD_ALREADY_CONVERTED"
