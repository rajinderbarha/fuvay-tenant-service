# Sprint 25 — Complaints constants
# ── Error codes ────────────────────────────────────────────────────────────────
ERR_COMPLAINT_NOT_FOUND              = "COMPLAINT_NOT_FOUND"
ERR_COMPLAINT_ACCESS_DENIED          = "COMPLAINT_ACCESS_DENIED"
ERR_COMPLAINT_NOT_ELIGIBLE           = "COMPLAINT_NOT_ELIGIBLE"
ERR_COMPLAINT_WINDOW_EXPIRED         = "COMPLAINT_WINDOW_EXPIRED"
ERR_COMPLAINT_DUPLICATE_OPEN         = "COMPLAINT_DUPLICATE_OPEN"
ERR_COMPLAINT_INVALID_RECORD_TYPE    = "COMPLAINT_INVALID_RECORD_TYPE"
ERR_COMPLAINT_RECORD_NOT_FOUND       = "COMPLAINT_RECORD_NOT_FOUND"
ERR_COMPLAINT_TYPE_REQUIRED          = "COMPLAINT_TYPE_REQUIRED"
ERR_COMPLAINT_TYPE_NOT_SUPPORTED     = "COMPLAINT_TYPE_NOT_SUPPORTED"
ERR_COMPLAINT_DESCRIPTION_REQUIRED   = "COMPLAINT_DESCRIPTION_REQUIRED"
ERR_COMPLAINT_INVALID_TRANSITION     = "COMPLAINT_INVALID_STATUS_TRANSITION"
ERR_COMPLAINT_REASON_REQUIRED        = "COMPLAINT_REASON_REQUIRED"
ERR_COMPLAINT_ALREADY_CLOSED         = "COMPLAINT_ALREADY_CLOSED"
ERR_COMPLAINT_MEDIA_UPLOAD_FAILED    = "COMPLAINT_MEDIA_UPLOAD_FAILED"
ERR_COMPLAINT_MESSAGE_REQUIRED       = "COMPLAINT_MESSAGE_REQUIRED"
ERR_COMPLAINT_POLICY_NOT_FOUND       = "COMPLAINT_POLICY_NOT_FOUND"
ERR_RESOLUTION_NOT_FOUND             = "RESOLUTION_NOT_FOUND"
ERR_RESOLUTION_ACCESS_DENIED         = "RESOLUTION_ACCESS_DENIED"
ERR_RESOLUTION_INVALID_STATUS        = "RESOLUTION_INVALID_STATUS"
ERR_REWORK_NOT_FOUND                 = "REWORK_NOT_FOUND"
ERR_REWORK_ACCESS_DENIED             = "REWORK_ACCESS_DENIED"
ERR_REWORK_NOT_ALLOWED               = "REWORK_NOT_ALLOWED"
ERR_REWORK_ASSIGNMENT_FAILED         = "REWORK_ASSIGNMENT_FAILED"
ERR_REFUND_NOT_FOUND                 = "REFUND_NOT_FOUND"
ERR_REFUND_ACCESS_DENIED             = "REFUND_ACCESS_DENIED"
ERR_REFUND_NOT_ALLOWED               = "REFUND_NOT_ALLOWED"
ERR_REFUND_AMOUNT_INVALID            = "REFUND_AMOUNT_INVALID"
ERR_REFUND_APPROVAL_FAILED           = "REFUND_APPROVAL_FAILED"
ERR_REFUND_RECORD_FAILED             = "REFUND_RECORD_FAILED"
ERR_REFUND_VERIFY_FAILED             = "REFUND_VERIFY_FAILED"

# ── Complaint statuses ─────────────────────────────────────────────────────────
STATUS_OPEN                      = "open"
STATUS_AWAITING_PROVIDER         = "awaiting_provider_response"
STATUS_AWAITING_CUSTOMER         = "awaiting_customer_response"
STATUS_RESOLUTION_PROPOSED       = "resolution_proposed"
STATUS_REWORK_APPROVED           = "rework_approved"
STATUS_REFUND_REQUESTED          = "refund_requested"
STATUS_REFUND_APPROVED           = "refund_approved"
STATUS_REFUND_RECORDED           = "refund_recorded"
STATUS_REJECTED                  = "rejected"
STATUS_RESOLVED                  = "resolved"
STATUS_CLOSED                    = "closed"
STATUS_CANCELLED                 = "cancelled"

FINAL_STATUSES = {STATUS_CLOSED, STATUS_CANCELLED, STATUS_REJECTED}

# ── Whose move is it ──────────────────────────────────────────────────────────
# A complaint only stays healthy if every non-final status has an owner who is
# on a clock. Before these sets existed, the only deadline was the provider's
# FIRST reply: one "we are looking into it" and the case could sit open forever
# with nothing measuring it.
#
# The provider owns these. `refund_requested` is the provider's move too, but
# the refund request carries its own response deadline and penalty
# (RefundRequest.provider_response_due_at), so the complaint does not run a
# second, overlapping clock for it.
PROVIDER_TURN_STATUSES = {
    STATUS_OPEN, STATUS_AWAITING_PROVIDER, STATUS_REWORK_APPROVED,
    STATUS_REFUND_REQUESTED, STATUS_REFUND_APPROVED,
}
PROVIDER_ACTION_TIMED_STATUSES = PROVIDER_TURN_STATUSES - {STATUS_REFUND_REQUESTED}
# The customer owns these: a resolution is waiting for their accept/reject.
CUSTOMER_TURN_STATUSES = {STATUS_RESOLUTION_PROPOSED, STATUS_AWAITING_CUSTOMER}

# How long a proposed resolution may wait on the customer. A reminder goes out
# at the first mark; at the second the case resolves as unanswered, so a
# customer who never replies cannot hold the provider's queue open forever.
CUSTOMER_REMINDER_HOURS = 48
CUSTOMER_RESPONSE_EXPIRY_HOURS = 168

# A resolved case stays open for follow-up messages for this long, then closes.
# Nothing ever wrote `closed` before, so every resolved case stayed in the
# provider's Open queue permanently.
RESOLVED_AUTO_CLOSE_HOURS = 72

# ── Valid status transitions ───────────────────────────────────────────────────
ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    # MODULE-L5-02 bug #29: the customer refund endpoint is reachable directly
    # from an open (or awaiting_provider) complaint, but refund_requested was not
    # a permitted target from either. refund_service guards every complaint
    # transition with `if status in allowed` and SILENTLY SKIPS otherwise, so the
    # complaint stayed 'open' while the refund advanced to approved/recorded —
    # i.e. a refund could be fully approved and paid out and the complaint would
    # still show as open forever, never resolving. Allow refund_requested here.
    STATUS_OPEN:               {STATUS_AWAITING_PROVIDER, STATUS_RESOLUTION_PROPOSED,
                                STATUS_CANCELLED, STATUS_REFUND_REQUESTED},
    STATUS_AWAITING_PROVIDER:  {STATUS_RESOLUTION_PROPOSED, STATUS_REFUND_REQUESTED},
    # MODULE-L5-02 bug #27: once a provider/admin proposes a resolution the
    # complaint sits in resolution_proposed, and the customer responds directly
    # via customer_accept_resolution (-> resolved) or customer_reject_resolution
    # (-> awaiting_provider). Neither target was reachable from here (only
    # awaiting_customer was, and nothing ever moved it there), so a proposed
    # resolution could never be accepted or rejected — every complaint stalled at
    # resolution_proposed. Allow the customer's accept/reject targets directly.
    # STATUS_REFUND_APPROVED: the customer accepted a refund the provider
    # offered. The provider made the offer, so the refund starts approved and
    # the provider's remaining step is recording the repayment. Without this
    # edge, accepting a refund offer resolved the case and no refund existed.
    STATUS_RESOLUTION_PROPOSED:{STATUS_AWAITING_CUSTOMER, STATUS_AWAITING_PROVIDER, STATUS_RESOLVED,
                                STATUS_REWORK_APPROVED, STATUS_REFUND_APPROVED},
    STATUS_AWAITING_CUSTOMER:  {STATUS_RESOLVED, STATUS_AWAITING_PROVIDER},
    STATUS_REWORK_APPROVED:    {STATUS_RESOLVED},
    # A declined refund used to leave the case in refund_requested with no
    # legal move at all: the provider could not offer anything else and no
    # clock watched it. A refund-only case (the dedicated refund flow) ends
    # as rejected; any other complaint returns to the provider, who still owes
    # a resolution for the underlying issue.
    STATUS_REFUND_REQUESTED:   {STATUS_REFUND_APPROVED, STATUS_REJECTED, STATUS_AWAITING_PROVIDER},
    STATUS_REFUND_APPROVED:    {STATUS_REFUND_RECORDED},
    STATUS_REFUND_RECORDED:    {STATUS_RESOLVED},
    STATUS_RESOLVED:           {STATUS_CLOSED},
}

# ── Priorities ─────────────────────────────────────────────────────────────────
PRIORITY_LOW    = "low"
PRIORITY_NORMAL = "normal"
PRIORITY_HIGH   = "high"
PRIORITY_URGENT = "urgent"
VALID_PRIORITIES = {PRIORITY_LOW, PRIORITY_NORMAL, PRIORITY_HIGH, PRIORITY_URGENT}

# ── Complaint types ────────────────────────────────────────────────────────────
COMPLAINT_TYPES = {
    "service_quality", "technician_behavior", "late_arrival", "no_show",
    "overcharging", "payment_issue", "refund_request", "rework_request",
    "wrong_information", "appointment_issue", "agent_issue", "other",
}

# Home Services complaints are resolved directly by the provider. Keep this
# customer-facing intake deliberately narrow: operational timing/no-show
# problems are already detected by the assignment and SLA engines, while
# warranty and payment each have their own dedicated workflows.
HOME_SERVICE_PROVIDER_COMPLAINT_OPTIONS = (
    ("service_quality", "Service quality issue"),
    ("technician_behavior", "Technician behaviour"),
    ("property_damage", "Property damage"),
)
HOME_SERVICE_PROVIDER_COMPLAINT_TYPES = {
    key for key, _label in HOME_SERVICE_PROVIDER_COMPLAINT_OPTIONS
}

# A Home Services complaint becomes available only once actual service work
# has started. These states prove that directly without needing event history;
# the eligibility service additionally checks for a prior inspection/service
# start event so a job that later moved to quote_required/cancelled remains
# reportable.
HOME_SERVICE_WORK_STARTED_STATUSES = {
    "inspection_started", "inspection_done", "quote_required",
    "in_progress", "service_started", "work_done", "completed",
    "invoice_issued", "payment_collected", "paid",
}

# Once the job is complete, service-performance recurrence belongs to the
# warranty workflow. Conduct and property-damage incidents remain reportable
# because they are not warranty defects and may only be noticed after handover.
HOME_SERVICE_COMPLETED_STATUSES = {
    "work_done", "completed", "invoice_issued", "payment_collected", "paid",
    "issued", "overdue",
}
HOME_SERVICE_POST_COMPLETION_COMPLAINT_TYPES = {
    "technician_behavior", "property_damage",
}

# ── Requested resolutions ─────────────────────────────────────────────────────
REQUESTED_RESOLUTIONS = {
    "rework", "refund", "callback", "apology",
    "provider_reassignment", "no_action",
}

# ── Resolution types ───────────────────────────────────────────────────────────
RESOLUTION_TYPES = {
    "rework", "refund", "callback", "provider_reassignment",
    "apology", "warning", "no_action", "rejected",
}

# What a provider can offer from the case workspace. Every value has a defined
# outcome when the customer accepts: rework spawns a rework visit, refund spawns
# an approved refund the provider must record, and the rest resolve the case.
# The workspace previously offered "partial_refund" and "credit", which the
# engine never modelled -- accepting them resolved the case and nothing
# happened. A partial refund is a refund with a smaller amount; credits belong
# to the settlement flow.
PROVIDER_RESOLUTION_OPTIONS = (
    ("rework", "Free rework visit"),
    ("refund", "Refund"),
    ("callback", "Callback"),
    ("apology", "Apology / goodwill"),
    ("no_action", "No action required"),
)
PROVIDER_RESOLUTION_TYPES = {key for key, _label in PROVIDER_RESOLUTION_OPTIONS}
ERR_RESOLUTION_TYPE_NOT_ALLOWED = "RESOLUTION_TYPE_NOT_ALLOWED"
ERR_RESOLUTION_AMOUNT_REQUIRED  = "RESOLUTION_AMOUNT_REQUIRED"

# ── Resolution statuses ────────────────────────────────────────────────────────
RES_PROPOSED          = "proposed"
RES_CUSTOMER_ACCEPTED = "customer_accepted"
RES_CUSTOMER_REJECTED = "customer_rejected"
RES_COMPLETED         = "completed"
RES_CANCELLED         = "cancelled"

# ── Record types ──────────────────────────────────────────────────────────────
RECORD_SERVICE_BOOKING      = "service_booking"
RECORD_SERVICE_JOB          = "service_job"
RECORD_SERVICE_INVOICE      = "service_invoice"
RECORD_COACHING_APPOINTMENT = "coaching_appointment"
RECORD_REAL_ESTATE_LEAD     = "real_estate_lead"
RECORD_CUSTOMER_REVIEW      = "customer_review"

VALID_RECORD_TYPES = {
    RECORD_SERVICE_BOOKING, RECORD_SERVICE_JOB, RECORD_SERVICE_INVOICE,
    RECORD_COACHING_APPOINTMENT, RECORD_REAL_ESTATE_LEAD, RECORD_CUSTOMER_REVIEW,
}

# ── Eligible statuses per record type ─────────────────────────────────────────
ELIGIBLE_STATUSES: dict[str, set[str]] = {
    # This is the broad status vocabulary a record may occupy after work has
    # started. ComplaintEligibilityService applies the stricter work-start
    # proof before allowing a Home Services complaint.
    RECORD_SERVICE_BOOKING:      {
        "pending_assignment", "assigned", "accepted", "scheduled",
        "on_the_way", "reached_site", "in_progress", "inspection_started",
        "inspection_done", "quote_required", "service_started", "work_done",
        "customer_not_available", "completed", "payment_collected", "paid",
        "cancelled", "failed", "quote_rejected",
    },
    # MODULE-L5-02 bug #23 (same class as the review-eligibility fix): a
    # completed job transitions to invoice_issued the moment it is billed, and to
    # paid once settled. Excluding those states meant a customer could not file a
    # complaint about a completed job that had gone through billing — the normal
    # flow — so poor-quality billed work became uncontestable.
    RECORD_SERVICE_JOB:          {
        "pending_assignment", "assigned", "dispatched", "accepted", "scheduled",
        "on_the_way", "reached_site", "in_progress", "inspection_started",
        "inspection_done", "quote_required", "service_started", "work_done",
        "customer_not_available", "completed", "cancelled", "invoice_issued", "paid",
    },
    RECORD_SERVICE_INVOICE:      {"issued","paid","overdue","cancelled"},
    RECORD_COACHING_APPOINTMENT: {"completed","no_show","cancelled"},
    RECORD_REAL_ESTATE_LEAD:     {"accepted","contacted","follow_up","site_visit_planned",
                                  "site_visit_completed","closed_lost","converted"},
    RECORD_CUSTOMER_REVIEW:      {"approved","rejected","hidden"},
}

# ── Rework statuses ────────────────────────────────────────────────────────────
REWORK_REQUESTED   = "requested"
REWORK_APPROVED    = "approved"
REWORK_ASSIGNED    = "assigned"
REWORK_SCHEDULED   = "scheduled"
REWORK_IN_PROGRESS = "in_progress"
REWORK_COMPLETED   = "completed"
REWORK_REJECTED    = "rejected"
REWORK_CANCELLED   = "cancelled"

# ── Refund statuses ────────────────────────────────────────────────────────────
REFUND_REQUESTED      = "requested"
REFUND_PROVIDER_REVIEW = "provider_review"
REFUND_APPROVED        = "approved"
REFUND_REJECTED        = "rejected"
REFUND_RECORDED        = "recorded"
REFUND_VERIFIED        = "verified"
REFUND_CANCELLED       = "cancelled"

# ── Event types ───────────────────────────────────────────────────────────────
EVT_COMPLAINT_CREATED             = "complaint_created"
EVT_PROVIDER_RESPONDED            = "provider_responded"
EVT_CUSTOMER_MESSAGE_ADDED        = "customer_message_added"
EVT_EVIDENCE_UPLOADED             = "evidence_uploaded"
EVT_STATUS_CHANGED                = "status_changed"
EVT_RESOLUTION_PROPOSED           = "resolution_proposed"
EVT_RESOLUTION_ACCEPTED           = "resolution_accepted"
EVT_RESOLUTION_REJECTED           = "resolution_rejected"
EVT_REWORK_REQUESTED              = "rework_requested"
EVT_REWORK_APPROVED               = "rework_approved"
EVT_REWORK_CREATED                = "rework_created"
EVT_REFUND_REQUESTED              = "refund_requested"
EVT_REFUND_APPROVED               = "refund_approved"
EVT_REFUND_RECORDED               = "refund_recorded"

# ── Message visibility ────────────────────────────────────────────────────────
VIS_PUBLIC       = "public_to_case"
VIS_ADMIN_ONLY   = "admin_only"
VIS_PROVIDER_ONLY = "provider_only"
VIS_CUSTOMER_ONLY = "customer_only"

# ── Actor types ───────────────────────────────────────────────────────────────
ACTOR_CUSTOMER = "customer"
ACTOR_PROVIDER = "provider"
ACTOR_STAFF    = "staff"
ACTOR_SYSTEM   = "system"

# ── Severity levels (Sprint 75) ───────────────────────────────────────────────
SEVERITY_LOW      = "low"
SEVERITY_MEDIUM   = "medium"
SEVERITY_HIGH     = "high"
SEVERITY_CRITICAL = "critical"
VALID_SEVERITIES  = {SEVERITY_LOW, SEVERITY_MEDIUM, SEVERITY_HIGH, SEVERITY_CRITICAL}

# ── SLA statuses ──────────────────────────────────────────────────────────────
SLA_ON_TIME   = "on_time"
SLA_AT_RISK   = "at_risk"
SLA_BREACHED  = "breached"
SLA_ESCALATED = "escalated"

# ── Extended complaint statuses (settlement workflow) ─────────────────────────
STATUS_SETTLED                = "settled"

FINAL_STATUSES_EXT = FINAL_STATUSES | {STATUS_SETTLED}

#: Nothing left for anyone to do. `resolved`, `refund_recorded` and `settled`
#: are outcomes waiting only to close. FINAL_STATUSES alone was used as "open"
#: everywhere, so resolved cases counted as open in the provider's queue and
#: KPIs, stayed eligible for the first-response penalty, and blocked nothing.
RESOLVED_OR_FINAL_STATUSES = FINAL_STATUSES_EXT | {STATUS_RESOLVED, STATUS_REFUND_RECORDED}

ALLOWED_TRANSITIONS_EXT: dict[str, set[str]] = {
    **ALLOWED_TRANSITIONS,
    STATUS_SETTLED:                {STATUS_CLOSED},
}

# ── Extended complaint types ───────────────────────────────────────────────────
COMPLAINT_TYPES_EXT = COMPLAINT_TYPES | {
    "property_damage", "service_not_completed", "poor_work_quality",
    "wrong_charge", "technician_misbehavior", "wrong_part_or_material",
    "warranty_claim", "repeat_issue", "safety_concern",
}

# ── Settlement proposal statuses ──────────────────────────────────────────────
PROPOSAL_PROPOSED   = "proposed"
PROPOSAL_ACCEPTED   = "accepted"
PROPOSAL_REJECTED   = "rejected"
PROPOSAL_COUNTERED  = "countered"


# ── Extended event types ──────────────────────────────────────────────────────
EVT_SLA_BREACHED             = "sla_breached"
EVT_SETTLEMENT_PROPOSED      = "settlement_proposed"
EVT_SETTLEMENT_ACCEPTED      = "settlement_accepted"
EVT_SETTLEMENT_REJECTED      = "settlement_rejected"
EVT_SETTLEMENT_COUNTERED     = "settlement_countered"


# Monetary remedies stay in the provider-owned refund flow. Mutual settlement
# proposals can grant service credits or non-monetary remedies only.
MONETARY_REMEDIES = {
    "refund", "partial_refund", "full_refund", "cash", "cash_refund",
    "tenant_direct_refund", "manual_customer_refund_exception", "bank_transfer",
}

ERR_SETTLEMENT_MONETARY_NOT_ALLOWED = "SETTLEMENT_MONETARY_REMEDY_NOT_ALLOWED"

# Maps a mutually agreed remedy onto the credit-ledger settlement type.
REMEDY_TO_SETTLEMENT_TYPE = {
    "credit_points": "customer_service_credit",
    "rework":        "tenant_revisit",
    "callback":      "tenant_revisit",
    "apology":       "no_compensation",
    "no_action":     "no_compensation",
}

# Customer remedies are funded from canonical provider usage credit only.
SETTLEMENT_DEDUCTION_STRATEGY = "tenant_wallet"
