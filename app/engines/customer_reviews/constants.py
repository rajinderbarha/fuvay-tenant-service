# Sprint 24 — Customer Reviews constants

# ── Error codes ────────────────────────────────────────────────────────────────
ERR_REVIEW_NOT_FOUND          = "REVIEW_NOT_FOUND"
ERR_REVIEW_ALREADY_EXISTS     = "REVIEW_ALREADY_EXISTS"
ERR_REVIEW_NOT_ELIGIBLE       = "REVIEW_NOT_ELIGIBLE"
ERR_REVIEW_NOT_EDITABLE       = "REVIEW_NOT_EDITABLE"
ERR_REVIEW_EDIT_WINDOW_CLOSED = "REVIEW_EDIT_WINDOW_CLOSED"
ERR_REVIEW_ALREADY_APPROVED   = "REVIEW_ALREADY_APPROVED"
ERR_REVIEW_INVALID_RATING     = "REVIEW_INVALID_RATING"
ERR_REPLY_NOT_FOUND           = "REPLY_NOT_FOUND"
ERR_REPLY_ALREADY_EXISTS      = "REPLY_ALREADY_EXISTS"
ERR_FLAG_NOT_FOUND            = "FLAG_NOT_FOUND"
ERR_POLICY_NOT_FOUND          = "POLICY_NOT_FOUND"
ERR_RECORD_NOT_FOUND          = "RECORD_NOT_FOUND"
ERR_PERMISSION_DENIED         = "PERMISSION_DENIED"

# ── Review statuses ────────────────────────────────────────────────────────────
STATUS_PENDING   = "pending"
STATUS_APPROVED  = "approved"
STATUS_REJECTED  = "rejected"
STATUS_HIDDEN    = "hidden"
STATUS_FLAGGED   = "flagged"
STATUS_DELETED   = "deleted"

REVIEW_STATUSES = {STATUS_PENDING, STATUS_APPROVED, STATUS_REJECTED,
                   STATUS_HIDDEN, STATUS_FLAGGED, STATUS_DELETED}

# ── Visibility ─────────────────────────────────────────────────────────────────
VISIBILITY_PRIVATE   = "private_until_approved"
VISIBILITY_PUBLIC    = "public"
VISIBILITY_HIDDEN    = "hidden"

# ── Reply statuses ────────────────────────────────────────────────────────────
REPLY_PENDING  = "pending"
REPLY_APPROVED = "approved"
REPLY_REJECTED = "rejected"

# ── Flag statuses / reason codes ──────────────────────────────────────────────
FLAG_STATUS_OPEN     = "open"
FLAG_STATUS_REVIEWED = "reviewed"
FLAG_STATUS_RESOLVED = "resolved"

FLAG_REASON_SPAM        = "spam"
FLAG_REASON_FAKE        = "fake"
FLAG_REASON_OFFENSIVE   = "offensive"
FLAG_REASON_IRRELEVANT  = "irrelevant"
FLAG_REASON_OTHER       = "other"

FLAG_REASONS = {FLAG_REASON_SPAM, FLAG_REASON_FAKE, FLAG_REASON_OFFENSIVE,
                FLAG_REASON_IRRELEVANT, FLAG_REASON_OTHER}

# ── Record types ──────────────────────────────────────────────────────────────
RECORD_TYPE_SERVICE_BOOKING      = "service_booking"
RECORD_TYPE_SERVICE_JOB          = "service_job"
RECORD_TYPE_COACHING_APPOINTMENT = "coaching_appointment"
RECORD_TYPE_REAL_ESTATE_LEAD     = "real_estate_lead"

VALID_RECORD_TYPES = {
    RECORD_TYPE_SERVICE_BOOKING,
    RECORD_TYPE_SERVICE_JOB,
    RECORD_TYPE_COACHING_APPOINTMENT,
    RECORD_TYPE_REAL_ESTATE_LEAD,
}

# ── Eligible statuses per record type ─────────────────────────────────────────
ELIGIBLE_STATUSES: dict[str, set[str]] = {
    RECORD_TYPE_SERVICE_BOOKING:      {"completed", "payment_collected", "paid"},
    # MODULE-L5-02 bug #20: a completed job transitions to "invoice_issued" the
    # moment it is billed (invoice_service sets job.status = invoice_issued) and
    # to "paid" once settled — the normal downstream flow. Excluding those states
    # slammed the review window shut the instant a completed job was invoiced, so
    # a customer could realistically never review a job that went through billing.
    RECORD_TYPE_SERVICE_JOB:          {"completed", "work_done", "invoice_issued", "paid"},
    RECORD_TYPE_COACHING_APPOINTMENT: {"completed"},
    RECORD_TYPE_REAL_ESTATE_LEAD:     {
        "contacted", "follow_up", "site_visit_completed",
        "converted", "closed_lost",
    },
}

# ── Event types ───────────────────────────────────────────────────────────────
EVT_REVIEW_SUBMITTED = "review_submitted"
EVT_REVIEW_EDITED    = "review_edited"
EVT_REVIEW_APPROVED  = "review_approved"
EVT_REVIEW_REJECTED  = "review_rejected"
EVT_REVIEW_HIDDEN    = "review_hidden"
EVT_REVIEW_DELETED   = "review_deleted"
EVT_REPLY_SUBMITTED  = "reply_submitted"
EVT_REPLY_APPROVED   = "reply_approved"
EVT_REPLY_REJECTED   = "reply_rejected"
EVT_FLAG_CREATED     = "flag_created"
EVT_FLAG_RESOLVED    = "flag_resolved"
EVT_RATING_UPDATED   = "rating_summary_updated"

# ── Actor types ───────────────────────────────────────────────────────────────
ACTOR_CUSTOMER = "customer"
ACTOR_PROVIDER = "provider"
ACTOR_ADMIN    = "admin"
ACTOR_SYSTEM   = "system"
