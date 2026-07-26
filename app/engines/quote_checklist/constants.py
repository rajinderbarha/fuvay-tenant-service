"""Sprint 22 — Quote Approval + Checklist Engine constants."""

# ── Quote statuses ────────────────────────────────────────────────────────────
QS_DRAFT                   = "draft"
QS_SUBMITTED_TO_PROVIDER   = "submitted_to_provider"
QS_PROVIDER_APPROVED       = "provider_approved"
QS_PROVIDER_REJECTED       = "provider_rejected"
QS_SENT_TO_CUSTOMER        = "sent_to_customer"
QS_CUSTOMER_APPROVED       = "customer_approved"
QS_CUSTOMER_REJECTED       = "customer_rejected"
QS_REVISION_REQUESTED      = "revision_requested"
QS_REVISED                 = "revised"
QS_EXPIRED                 = "expired"
QS_CANCELLED               = "cancelled"

QUOTE_FINAL_STATUSES = {QS_CUSTOMER_APPROVED, QS_CUSTOMER_REJECTED, QS_EXPIRED, QS_CANCELLED}

# ── Quote transitions: from_status → set of valid to_statuses ────────────────
QUOTE_TRANSITIONS: dict[str, set[str]] = {
    QS_DRAFT:                 {QS_SUBMITTED_TO_PROVIDER, QS_SENT_TO_CUSTOMER, QS_CANCELLED},
    QS_SUBMITTED_TO_PROVIDER: {QS_PROVIDER_APPROVED, QS_PROVIDER_REJECTED, QS_CANCELLED},
    QS_PROVIDER_APPROVED:     {QS_SENT_TO_CUSTOMER, QS_CANCELLED},
    QS_PROVIDER_REJECTED:     {QS_REVISED, QS_CANCELLED},
    QS_SENT_TO_CUSTOMER:      {QS_CUSTOMER_APPROVED, QS_CUSTOMER_REJECTED,
                                QS_REVISION_REQUESTED, QS_EXPIRED, QS_CANCELLED},
    QS_CUSTOMER_APPROVED:     set(),
    QS_CUSTOMER_REJECTED:     set(),
    QS_REVISION_REQUESTED:    {QS_REVISED, QS_CANCELLED},
    QS_REVISED:               {QS_SUBMITTED_TO_PROVIDER, QS_SENT_TO_CUSTOMER, QS_CANCELLED},
    QS_EXPIRED:               set(),
    QS_CANCELLED:             set(),
}

# ── Quote types ───────────────────────────────────────────────────────────────
QUOTE_TYPE_REPAIR          = "repair_quote"
QUOTE_TYPE_PARTS           = "parts_quote"
QUOTE_TYPE_ADDITIONAL_WORK = "additional_work_quote"
QUOTE_TYPE_INSPECTION      = "inspection_quote"

VALID_QUOTE_TYPES = {QUOTE_TYPE_REPAIR, QUOTE_TYPE_PARTS,
                     QUOTE_TYPE_ADDITIONAL_WORK, QUOTE_TYPE_INSPECTION}

# ── Quote item types ──────────────────────────────────────────────────────────
ITEM_TYPE_LABOUR       = "labour"
ITEM_TYPE_PART         = "part"
ITEM_TYPE_MATERIAL     = "material"
ITEM_TYPE_SERVICE      = "service"
ITEM_TYPE_VISIT_CHARGE = "visit_charge"
ITEM_TYPE_DISCOUNT     = "discount"
ITEM_TYPE_TAX          = "tax"
ITEM_TYPE_OTHER        = "other"

VALID_ITEM_TYPES = {
    ITEM_TYPE_LABOUR, ITEM_TYPE_PART, ITEM_TYPE_MATERIAL, ITEM_TYPE_SERVICE,
    ITEM_TYPE_VISIT_CHARGE, ITEM_TYPE_DISCOUNT, ITEM_TYPE_TAX, ITEM_TYPE_OTHER,
}

# ── Quote event types ─────────────────────────────────────────────────────────
QEV_CREATED                = "quote_created"
QEV_ITEM_ADDED             = "quote_item_added"
QEV_ITEM_UPDATED           = "quote_item_updated"
QEV_ITEM_REMOVED           = "quote_item_removed"
QEV_SUBMITTED_TO_PROVIDER  = "quote_submitted_to_provider"
QEV_PROVIDER_APPROVED      = "quote_provider_approved"
QEV_PROVIDER_REJECTED      = "quote_provider_rejected"
QEV_SENT_TO_CUSTOMER       = "quote_sent_to_customer"
QEV_CUSTOMER_APPROVED      = "quote_customer_approved"
QEV_CUSTOMER_REJECTED      = "quote_customer_rejected"
QEV_REVISION_REQUESTED     = "quote_revision_requested"
QEV_REVISED                = "quote_revised"
QEV_EXPIRED                = "quote_expired"
QEV_CANCELLED              = "quote_cancelled"

# ── Job status syncs triggered by quote events ────────────────────────────────
JOB_STATUS_AWAITING_QUOTE_APPROVAL = "awaiting_customer_quote_approval"
JOB_STATUS_QUOTE_APPROVED          = "quote_approved"
JOB_STATUS_QUOTE_REJECTED          = "quote_rejected"
JOB_STATUS_QUOTE_REVISION          = "quote_revision_requested"

# ── Checklist statuses ────────────────────────────────────────────────────────
CL_PENDING     = "pending"
CL_IN_PROGRESS = "in_progress"
CL_COMPLETED   = "completed"
CL_SKIPPED     = "skipped"

# ── Checklist item statuses ───────────────────────────────────────────────────
CLI_PENDING   = "pending"
CLI_COMPLETED = "completed"
CLI_SKIPPED   = "skipped"
CLI_FAILED    = "failed"

# ── Checklist types ───────────────────────────────────────────────────────────
CL_TYPE_INSPECTION   = "inspection"
CL_TYPE_REPAIR       = "repair"
CL_TYPE_INSTALLATION = "installation"
CL_TYPE_COMPLETION   = "completion"
CL_TYPE_SAFETY       = "safety"
CL_TYPE_QUALITY      = "quality"

VALID_CHECKLIST_TYPES = {
    CL_TYPE_INSPECTION, CL_TYPE_REPAIR, CL_TYPE_INSTALLATION,
    CL_TYPE_COMPLETION, CL_TYPE_SAFETY, CL_TYPE_QUALITY,
}

# ── Checklist item input types ────────────────────────────────────────────────
INPUT_CHECKBOX = "checkbox"
INPUT_TEXT     = "text"
INPUT_NUMBER   = "number"
INPUT_PHOTO    = "photo"
INPUT_SELECT   = "select"

VALID_INPUT_TYPES = {INPUT_CHECKBOX, INPUT_TEXT, INPUT_NUMBER, INPUT_PHOTO, INPUT_SELECT}

# ── Template applies_to ───────────────────────────────────────────────────────
APPLIES_GLOBAL   = "global"
APPLIES_CATEGORY = "category"
APPLIES_OFFERING = "offering"
APPLIES_TENANT   = "tenant"

# ── Error codes ───────────────────────────────────────────────────────────────
ERR_QUOTE_NOT_FOUND                    = "QUOTE_NOT_FOUND"
ERR_QUOTE_ACCESS_DENIED                = "QUOTE_ACCESS_DENIED"
ERR_QUOTE_INVALID_TRANSITION           = "QUOTE_INVALID_STATUS_TRANSITION"
ERR_QUOTE_ALREADY_LOCKED               = "QUOTE_ALREADY_LOCKED"
ERR_QUOTE_EXPIRED                      = "QUOTE_EXPIRED"
ERR_QUOTE_ITEM_REQUIRED                = "QUOTE_ITEM_REQUIRED"
ERR_QUOTE_ITEM_INVALID                 = "QUOTE_ITEM_INVALID"
ERR_QUOTE_CUSTOMER_APPROVAL_NOT_ALLOWED = "QUOTE_CUSTOMER_APPROVAL_NOT_ALLOWED"
ERR_QUOTE_PROVIDER_APPROVAL_NOT_ALLOWED = "QUOTE_PROVIDER_APPROVAL_NOT_ALLOWED"
ERR_QUOTE_REJECTION_REASON_REQUIRED    = "QUOTE_REJECTION_REASON_REQUIRED"
ERR_QUOTE_REVISION_REASON_REQUIRED     = "QUOTE_REVISION_REASON_REQUIRED"
ERR_QUOTE_IDEMPOTENCY_CONFLICT         = "QUOTE_IDEMPOTENCY_CONFLICT"
ERR_QUOTE_JOB_NOT_FOUND                = "QUOTE_JOB_NOT_FOUND"
ERR_QUOTE_CREATE_FAILED                = "QUOTE_CREATE_FAILED"
# HOME-SERVICES-RUNTIME-SAFETY Phase 2A — a quote that has been superseded by
# a newer version (is_current=false) can no longer be approved/rejected/
# revised; the customer must act on the current effective quote instead.
ERR_QUOTE_NOT_CURRENT                  = "QUOTE_NOT_CURRENT"
# HOME-SERVICES-RUNTIME-SAFETY Phase 2A.1 (spec section 10) -- an ordinary
# create_quote call must not silently supersede a quote the customer already
# approved, or one currently awaiting the customer's decision. Only "no
# prior quote", "rejected", or "revision requested" (and terminal
# expired/cancelled) are legitimate replacement sources.
ERR_APPROVED_ESTIMATE_IMMUTABLE        = "APPROVED_ESTIMATE_IMMUTABLE"
ERR_INVALID_ESTIMATE_REVISION_STATE    = "INVALID_ESTIMATE_REVISION_STATE"
# HOME-SERVICES-RUNTIME-SAFETY Phase 2A.2 (spec section 14) -- a job the
# customer finally rejected the estimate for is terminal
# (closed_estimate_declined); no new quote may be created against it unless
# a separate, explicit reopen workflow exists (none does today).
ERR_JOB_CLOSED_ESTIMATE_DECLINED       = "JOB_CLOSED_ESTIMATE_DECLINED"
ERR_CHECKLIST_NOT_FOUND                = "CHECKLIST_NOT_FOUND"
ERR_CHECKLIST_ACCESS_DENIED            = "CHECKLIST_ACCESS_DENIED"
ERR_CHECKLIST_REQUIRED_ITEM_MISSING    = "CHECKLIST_REQUIRED_ITEM_MISSING"
ERR_CHECKLIST_ITEM_VALUE_REQUIRED      = "CHECKLIST_ITEM_VALUE_REQUIRED"
ERR_CHECKLIST_PHOTO_REQUIRED           = "CHECKLIST_PHOTO_REQUIRED"
ERR_CHECKLIST_ALREADY_COMPLETED        = "CHECKLIST_ALREADY_COMPLETED"
ERR_CHECKLIST_TEMPLATE_NOT_FOUND       = "CHECKLIST_TEMPLATE_NOT_FOUND"
ERR_CHECKLIST_ITEM_NOT_FOUND           = "CHECKLIST_ITEM_NOT_FOUND"
