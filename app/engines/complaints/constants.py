# Sprint 25 — Complaints constants
from decimal import Decimal

# ── Error codes ────────────────────────────────────────────────────────────────
ERR_COMPLAINT_NOT_FOUND              = "COMPLAINT_NOT_FOUND"
ERR_COMPLAINT_ACCESS_DENIED          = "COMPLAINT_ACCESS_DENIED"
ERR_COMPLAINT_NOT_ELIGIBLE           = "COMPLAINT_NOT_ELIGIBLE"
ERR_COMPLAINT_WINDOW_EXPIRED         = "COMPLAINT_WINDOW_EXPIRED"
ERR_COMPLAINT_DUPLICATE_OPEN         = "COMPLAINT_DUPLICATE_OPEN"
ERR_COMPLAINT_INVALID_RECORD_TYPE    = "COMPLAINT_INVALID_RECORD_TYPE"
ERR_COMPLAINT_RECORD_NOT_FOUND       = "COMPLAINT_RECORD_NOT_FOUND"
ERR_COMPLAINT_TYPE_REQUIRED          = "COMPLAINT_TYPE_REQUIRED"
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
STATUS_UNDER_ADMIN_REVIEW        = "under_admin_review"
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

# ── Valid status transitions ───────────────────────────────────────────────────
ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    # MODULE-L5-02 bug #29: the customer refund endpoint is reachable directly
    # from an open (or awaiting_provider) complaint, but refund_requested was not
    # a permitted target from either. refund_service guards every complaint
    # transition with `if status in allowed` and SILENTLY SKIPS otherwise, so the
    # complaint stayed 'open' while the refund advanced to approved/recorded —
    # i.e. a refund could be fully approved and paid out and the complaint would
    # still show as open forever, never resolving. Allow refund_requested here.
    STATUS_OPEN:               {STATUS_AWAITING_PROVIDER, STATUS_UNDER_ADMIN_REVIEW, STATUS_CANCELLED,
                                STATUS_REFUND_REQUESTED},
    STATUS_AWAITING_PROVIDER:  {STATUS_UNDER_ADMIN_REVIEW, STATUS_RESOLUTION_PROPOSED,
                                STATUS_REFUND_REQUESTED},
    STATUS_UNDER_ADMIN_REVIEW: {STATUS_RESOLUTION_PROPOSED, STATUS_REWORK_APPROVED,
                                STATUS_REFUND_REQUESTED, STATUS_REJECTED, STATUS_RESOLVED},
    # MODULE-L5-02 bug #27: once a provider/admin proposes a resolution the
    # complaint sits in resolution_proposed, and the customer responds directly
    # via customer_accept_resolution (-> resolved) or customer_reject_resolution
    # (-> under_admin_review). Neither target was reachable from here (only
    # awaiting_customer was, and nothing ever moved it there), so a proposed
    # resolution could never be accepted or rejected — every complaint stalled at
    # resolution_proposed. Allow the customer's accept/reject targets directly.
    STATUS_RESOLUTION_PROPOSED:{STATUS_AWAITING_CUSTOMER, STATUS_AWAITING_PROVIDER, STATUS_RESOLVED,
                                STATUS_REWORK_APPROVED},
    STATUS_AWAITING_CUSTOMER:  {STATUS_RESOLVED, STATUS_AWAITING_PROVIDER},
    STATUS_REWORK_APPROVED:    {STATUS_RESOLVED},
    STATUS_REFUND_REQUESTED:   {STATUS_REFUND_APPROVED},
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

# ── Requested resolutions ─────────────────────────────────────────────────────
REQUESTED_RESOLUTIONS = {
    "rework", "refund", "callback", "apology",
    "provider_reassignment", "admin_review", "no_action",
}

# ── Resolution types ───────────────────────────────────────────────────────────
RESOLUTION_TYPES = {
    "rework", "refund", "callback", "provider_reassignment",
    "apology", "warning", "no_action", "rejected",
}

# ── Resolution statuses ────────────────────────────────────────────────────────
RES_PROPOSED          = "proposed"
RES_CUSTOMER_ACCEPTED = "customer_accepted"
RES_CUSTOMER_REJECTED = "customer_rejected"
RES_ADMIN_APPROVED    = "admin_approved"
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
    RECORD_SERVICE_BOOKING:      {"completed","payment_collected","paid","cancelled","failed","quote_rejected"},
    # MODULE-L5-02 bug #23 (same class as the review-eligibility fix): a
    # completed job transitions to invoice_issued the moment it is billed, and to
    # paid once settled. Excluding those states meant a customer could not file a
    # complaint about a completed job that had gone through billing — the normal
    # flow — so poor-quality billed work became uncontestable.
    RECORD_SERVICE_JOB:          {"completed","work_done","cancelled","invoice_issued","paid"},
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
REFUND_ADMIN_REVIEW    = "admin_review"
REFUND_APPROVED        = "approved"
REFUND_REJECTED        = "rejected"
REFUND_RECORDED        = "recorded"
REFUND_VERIFIED        = "verified"
REFUND_CANCELLED       = "cancelled"

# ── Event types ───────────────────────────────────────────────────────────────
EVT_COMPLAINT_CREATED             = "complaint_created"
EVT_COMPLAINT_ASSIGNED            = "complaint_assigned"
EVT_PROVIDER_RESPONSE_REQUESTED   = "provider_response_requested"
EVT_PROVIDER_RESPONDED            = "provider_responded"
EVT_CUSTOMER_MESSAGE_ADDED        = "customer_message_added"
EVT_ADMIN_MESSAGE_ADDED           = "admin_message_added"
EVT_EVIDENCE_UPLOADED             = "evidence_uploaded"
EVT_PRIORITY_CHANGED              = "priority_changed"
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
EVT_COMPLAINT_REJECTED            = "complaint_rejected"
EVT_COMPLAINT_RESOLVED            = "complaint_resolved"
EVT_COMPLAINT_CLOSED              = "complaint_closed"

# ── Message visibility ────────────────────────────────────────────────────────
VIS_PUBLIC       = "public_to_case"
VIS_ADMIN_ONLY   = "admin_only"
VIS_PROVIDER_ONLY = "provider_only"
VIS_CUSTOMER_ONLY = "customer_only"

# ── Actor types ───────────────────────────────────────────────────────────────
ACTOR_CUSTOMER = "customer"
ACTOR_PROVIDER = "provider"
ACTOR_STAFF    = "staff"
ACTOR_ADMIN    = "admin"
ACTOR_SYSTEM   = "system"
ACTOR_AI       = "ai"

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
STATUS_TENANT_REVIEW_PENDING  = "tenant_review_pending"
STATUS_TENANT_NO_RESPONSE     = "tenant_no_response"
STATUS_AI_SETTLEMENT_STARTED  = "ai_settlement_started"
STATUS_AI_WAITING_CUSTOMER    = "ai_waiting_customer"
STATUS_AI_WAITING_TENANT      = "ai_waiting_tenant"
STATUS_AI_PROPOSAL_SENT       = "ai_proposal_sent"
STATUS_AI_SETTLEMENT_ACCEPTED = "ai_settlement_accepted"
STATUS_AI_SETTLEMENT_FAILED   = "ai_settlement_failed"
STATUS_ADMIN_REVIEW_PENDING   = "admin_review_pending"
STATUS_ADMIN_DECISION_MADE    = "admin_decision_made"
STATUS_SETTLEMENT_PROPOSED    = "settlement_proposed"
STATUS_SETTLED                = "settled"

# Add new statuses to final set
FINAL_STATUSES_EXT = FINAL_STATUSES | {STATUS_SETTLED, "closed", "cancelled", "rejected"}

# Extended transitions (merged with ALLOWED_TRANSITIONS)
ALLOWED_TRANSITIONS_EXT: dict[str, set[str]] = {
    **ALLOWED_TRANSITIONS,
    STATUS_OPEN:               {STATUS_AWAITING_PROVIDER, STATUS_TENANT_REVIEW_PENDING,
                                STATUS_UNDER_ADMIN_REVIEW, STATUS_CANCELLED},
    STATUS_TENANT_REVIEW_PENDING: {STATUS_AWAITING_PROVIDER, STATUS_SETTLEMENT_PROPOSED,
                                    STATUS_TENANT_NO_RESPONSE, STATUS_UNDER_ADMIN_REVIEW},
    STATUS_TENANT_NO_RESPONSE: {STATUS_AI_SETTLEMENT_STARTED, STATUS_ADMIN_REVIEW_PENDING},
    STATUS_AI_SETTLEMENT_STARTED: {STATUS_AI_WAITING_CUSTOMER, STATUS_AI_WAITING_TENANT},
    STATUS_AI_WAITING_CUSTOMER: {STATUS_AI_WAITING_TENANT, STATUS_AI_PROPOSAL_SENT,
                                  STATUS_AI_SETTLEMENT_FAILED},
    STATUS_AI_WAITING_TENANT:  {STATUS_AI_WAITING_CUSTOMER, STATUS_AI_PROPOSAL_SENT,
                                 STATUS_AI_SETTLEMENT_FAILED},
    STATUS_AI_PROPOSAL_SENT:   {STATUS_AI_SETTLEMENT_ACCEPTED, STATUS_AI_SETTLEMENT_FAILED,
                                 STATUS_ADMIN_REVIEW_PENDING},
    STATUS_AI_SETTLEMENT_ACCEPTED: {STATUS_SETTLED},
    STATUS_AI_SETTLEMENT_FAILED:   {STATUS_ADMIN_REVIEW_PENDING},
    STATUS_SETTLEMENT_PROPOSED:    {STATUS_AI_SETTLEMENT_STARTED, STATUS_ADMIN_REVIEW_PENDING,
                                     STATUS_AWAITING_CUSTOMER},
    STATUS_ADMIN_REVIEW_PENDING:   {STATUS_ADMIN_DECISION_MADE, STATUS_SETTLEMENT_PROPOSED},
    STATUS_ADMIN_DECISION_MADE:    {STATUS_SETTLED, STATUS_REJECTED, STATUS_RESOLVED},
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
PROPOSAL_EXPIRED    = "expired"
PROPOSAL_WITHDRAWN  = "withdrawn"
PROPOSAL_ADMIN_APPROVED = "admin_approved"

# ── AI session statuses ────────────────────────────────────────────────────────
AI_SESSION_STARTED          = "started"
AI_SESSION_COLLECTING       = "collecting"
AI_SESSION_ANALYZING        = "analyzing"
AI_SESSION_PROPOSAL_READY   = "proposal_ready"
AI_SESSION_COMPLETED        = "completed"
AI_SESSION_FAILED           = "failed"

# ── Extended event types ──────────────────────────────────────────────────────
EVT_SLA_BREACHED             = "sla_breached"
EVT_AI_SESSION_STARTED       = "ai_session_started"
EVT_AI_PROPOSAL_GENERATED    = "ai_proposal_generated"
EVT_SETTLEMENT_PROPOSED      = "settlement_proposed"
EVT_SETTLEMENT_ACCEPTED      = "settlement_accepted"
EVT_SETTLEMENT_REJECTED      = "settlement_rejected"
EVT_SETTLEMENT_COUNTERED     = "settlement_countered"
EVT_ADMIN_ESCALATED          = "admin_escalated"
EVT_COMPLAINT_SETTLED        = "complaint_settled"
EVT_SEVERITY_CHANGED         = "severity_changed"

# ── AI settlement rule (migration 138) ────────────────────────────────────────
# The admin sets the rule; everything else is automatic.
#
#  * The AI takes over only once the PROVIDER has failed to solve the complaint
#    (no response within SLA, or the customer rejected what they offered).
#  * It may offer at most AI_SETTLEMENT_DEFAULT_MAX_PCT of the job's value.
#  * A case strong enough to warrant MORE than the cap is NOT settled by the AI —
#    it is escalated to admin manual review.
#  * Compensation is paid in CREDIT POINTS, never real money. Those credits are
#    funded by deducting from the PROVIDER's credit wallet, falling back to their
#    security deposit.
AI_SETTLEMENT_DEFAULT_MAX_PCT = Decimal("25.00")

# Remedies the AI is allowed to propose. Deliberately excludes every monetary
# option — the platform never settles a dispute with real money.
AI_ALLOWED_REMEDIES = ["credit_points", "rework", "callback", "apology", "no_action"]

# Proposal types that move REAL MONEY. The AI must never reach for these, and the
# code rejects them even if the model returns one anyway.
MONETARY_REMEDIES = {
    "refund", "partial_refund", "full_refund", "cash", "cash_refund",
    "tenant_direct_refund", "manual_customer_refund_exception", "bank_transfer",
}

# Maps an allowed AI remedy onto the DisputeSettlement settlement_type that
# actually executes it (see app/engines/customer_credits/service.py).
REMEDY_TO_SETTLEMENT_TYPE = {
    "credit_points": "customer_service_credit",
    "rework":        "tenant_revisit",
    "callback":      "tenant_revisit",
    "apology":       "no_compensation",
    "no_action":     "no_compensation",
}

# Customer remedies are funded from canonical provider usage credit only.
SETTLEMENT_DEDUCTION_STRATEGY = "tenant_wallet"

# Running an AI settlement is a paid platform service: the PROVIDER is charged
# this many usage credits when the session starts (deducted from their credit
# balance — the same canonical account as the remedy itself).
AI_SETTLEMENT_FEE_CREDITS = Decimal("20.00")

ERR_AI_SETTLEMENT_DISABLED = "AI_SETTLEMENT_DISABLED"
EVT_AI_CAP_EXCEEDED        = "ai_settlement_cap_exceeded"
EVT_AI_AUTO_STARTED        = "ai_settlement_auto_started"
EVT_SETTLEMENT_EXECUTED    = "settlement_executed"
