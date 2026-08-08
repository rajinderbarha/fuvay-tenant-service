"""Sprint 21 — Execution lifecycle constants."""

# ── Home Service job statuses ──────────────────────────────────────────────────
JS_PENDING_ASSIGNMENT = "pending_assignment"
JS_ASSIGNED           = "assigned"
JS_ACCEPTED           = "accepted"
JS_SCHEDULED          = "scheduled"
JS_ON_THE_WAY         = "on_the_way"
JS_REACHED_SITE       = "reached_site"
JS_INSPECTION_STARTED = "inspection_started"
JS_INSPECTION_DONE    = "inspection_done"
JS_QUOTE_REQUIRED     = "quote_required"
JS_SERVICE_STARTED    = "service_started"
JS_WORK_DONE          = "work_done"
JS_CUSTOMER_NOT_AVAIL = "customer_not_available"
JS_CANCELLED          = "cancelled"
JS_FAILED             = "failed"
# HOME-SERVICES-RUNTIME-SAFETY Phase 2A — deterministic terminal status for a
# job whose customer rejected the estimate (spec section 9: do not leave the
# job in an ambiguous inspection state, and do not conflate this with
# revision-requested, which must remain non-terminal).
JS_CLOSED_ESTIMATE_DECLINED = "closed_estimate_declined"

# ── Allowed job transitions: from_status → set of valid to_statuses ───────────
JOB_TRANSITIONS: dict[str, set[str]] = {
    JS_ASSIGNED:           {JS_ACCEPTED, JS_CANCELLED},
    JS_ACCEPTED:           {JS_SCHEDULED, JS_ON_THE_WAY, JS_CANCELLED},
    JS_SCHEDULED:          {JS_ON_THE_WAY, JS_CANCELLED, JS_CUSTOMER_NOT_AVAIL},
    JS_ON_THE_WAY:         {JS_REACHED_SITE, JS_CUSTOMER_NOT_AVAIL, JS_CANCELLED},
    JS_REACHED_SITE:       {JS_INSPECTION_STARTED, JS_CUSTOMER_NOT_AVAIL, JS_CANCELLED},
    # JS_QUOTE_REQUIRED is reachable from here because both
    # `create_parts_request` and `mark_parts_required`/`mark_quote_required` are
    # explicitly available while an inspection is in progress
    # (PARTS_REQUEST_ALLOWED_JOB_STATUSES below lists JS_INSPECTION_STARTED, and
    # the refusal message reads "after inspection has started"). Without the edge
    # those endpoints raised EXECUTION_INVALID_STATUS_TRANSITION every time --
    # "cannot move from inspection_started to quote_required" -- so a technician
    # who found a part mid-inspection could not record it at all, and the error
    # blamed the transition rather than saying the action was unavailable.
    JS_INSPECTION_STARTED: {
        JS_INSPECTION_DONE, JS_QUOTE_REQUIRED, JS_CUSTOMER_NOT_AVAIL, JS_CANCELLED,
    },
    # Phase 2A: JS_SERVICE_STARTED remains a graph-valid target here (an
    # estimate-not-required job must keep working exactly as before) -- the
    # NEW guard (assert_job_can_start_work, called from _set_status) blocks
    # the transition at the service layer when the blueprint requires
    # approval and it hasn't been granted. The graph alone cannot express
    # that condition; see home_service_service.py.
    JS_INSPECTION_DONE:    {JS_QUOTE_REQUIRED, JS_SERVICE_STARTED, JS_CANCELLED},
    JS_SERVICE_STARTED:    {JS_WORK_DONE, JS_QUOTE_REQUIRED, JS_CANCELLED, "completed"},
    JS_WORK_DONE:          {"completed"},    # HS8B — completion via POST .../complete only
    JS_QUOTE_REQUIRED:     {"completed", JS_SERVICE_STARTED, JS_CLOSED_ESTIMATE_DECLINED},
    "completed":           set(),           # terminal
    JS_CUSTOMER_NOT_AVAIL: {JS_ACCEPTED, JS_SCHEDULED},
    JS_CANCELLED:          set(),
    JS_FAILED:             set(),
    JS_CLOSED_ESTIMATE_DECLINED: set(),     # terminal
}

# ── Home Service execution event types ────────────────────────────────────────
EV_JOB_ACCEPTED         = "job_accepted"
# The provider's FIRST task on an auto-accepted job: understand the request by
# speaking to the customer before travelling. Recorded as an event rather than
# a new job status so the existing JOB_TRANSITIONS graph stays untouched -- the
# job is legitimately `accepted` throughout, it just has one action to do first.
EV_CUSTOMER_CONTACTED   = "customer_contacted"
EV_JOB_REJECTED         = "job_rejected"
EV_JOB_SCHEDULED        = "job_scheduled"
EV_ON_THE_WAY           = "technician_on_the_way"
EV_REACHED_SITE         = "technician_reached_site"
EV_INSPECTION_STARTED   = "inspection_started"
EV_INSPECTION_COMPLETED = "inspection_completed"
EV_SERVICE_STARTED      = "service_started"
EV_DIAGNOSIS_ADDED      = "diagnosis_added"
EV_BEFORE_PHOTO         = "before_photo_uploaded"
EV_AFTER_PHOTO          = "after_photo_uploaded"
EV_WORK_NOTE_ADDED      = "work_note_added"
EV_QUOTE_REQUIRED       = "quote_required"
EV_PARTS_REQUIRED       = "parts_required"
EV_WORK_DONE            = "work_done"
EV_CUSTOMER_NOT_AVAIL   = "customer_not_available"
EV_JOB_CANCELLED        = "job_cancelled"
EV_JOB_FAILED           = "job_failed"

# ── Coaching appointment statuses ──────────────────────────────────────────────
AS_CONFIRMED            = "confirmed"
AS_ACCEPTED             = "accepted"
AS_REJECTED             = "rejected"
AS_SCHEDULED            = "scheduled"
AS_STARTED              = "started"
AS_COMPLETED            = "completed"
AS_NO_SHOW              = "no_show"
AS_RESCHEDULE_REQUESTED = "reschedule_requested"
AS_CANCELLED            = "cancelled"

APPT_TRANSITIONS: dict[str, set[str]] = {
    AS_CONFIRMED:  {AS_ACCEPTED, AS_REJECTED, AS_NO_SHOW, AS_CANCELLED},
    AS_ACCEPTED:   {AS_SCHEDULED, AS_STARTED, AS_NO_SHOW, AS_RESCHEDULE_REQUESTED, AS_CANCELLED},
    AS_SCHEDULED:  {AS_STARTED, AS_NO_SHOW, AS_RESCHEDULE_REQUESTED, AS_CANCELLED},
    AS_STARTED:    {AS_COMPLETED, AS_NO_SHOW},
    AS_COMPLETED:  set(),
    AS_NO_SHOW:    set(),
    AS_RESCHEDULE_REQUESTED: {AS_ACCEPTED, AS_CANCELLED},
    AS_REJECTED:   set(),
    AS_CANCELLED:  set(),
}

# ── Coaching execution event types ────────────────────────────────────────────
CA_EV_ACCEPTED        = "appointment_accepted"
CA_EV_REJECTED        = "appointment_rejected"
CA_EV_STARTED         = "appointment_started"
CA_EV_NOTE_ADDED      = "consultation_note_added"
CA_EV_COMPLETED       = "appointment_completed"
CA_EV_NO_SHOW         = "customer_no_show"
CA_EV_RESCHEDULE      = "reschedule_requested"
CA_EV_CANCELLED       = "appointment_cancelled"

# ── Real Estate lead statuses ──────────────────────────────────────────────────
LS_NEW             = "new"
LS_ACCEPTED        = "accepted"
LS_REJECTED        = "rejected"
LS_CONTACTED       = "contacted"
LS_FOLLOW_UP       = "follow_up"
LS_SITE_VISIT      = "site_visit_planned"
LS_SITE_VISITED    = "site_visit_completed"
LS_QUALIFIED       = "qualified"
LS_UNQUALIFIED     = "unqualified"
LS_CONVERTED       = "converted"
LS_CLOSED_LOST     = "closed_lost"

LEAD_TRANSITIONS: dict[str, set[str]] = {
    LS_NEW:          {LS_ACCEPTED, LS_REJECTED},
    LS_ACCEPTED:     {LS_CONTACTED, LS_UNQUALIFIED, LS_CLOSED_LOST},
    LS_CONTACTED:    {LS_FOLLOW_UP, LS_SITE_VISIT, LS_QUALIFIED, LS_UNQUALIFIED, LS_CLOSED_LOST},
    LS_FOLLOW_UP:    {LS_CONTACTED, LS_SITE_VISIT, LS_CONVERTED, LS_CLOSED_LOST, LS_UNQUALIFIED},
    LS_SITE_VISIT:   {LS_SITE_VISITED, LS_CLOSED_LOST},
    LS_SITE_VISITED: {LS_QUALIFIED, LS_FOLLOW_UP, LS_CONVERTED, LS_CLOSED_LOST},
    LS_QUALIFIED:    {LS_CONVERTED, LS_CLOSED_LOST},
    LS_UNQUALIFIED:  set(),
    LS_CONVERTED:    set(),
    LS_CLOSED_LOST:  set(),
    LS_REJECTED:     set(),
}

# ── Real estate execution event types ─────────────────────────────────────────
RE_EV_ACCEPTED       = "lead_accepted"
RE_EV_REJECTED       = "lead_rejected"
RE_EV_CONTACTED      = "customer_contacted"
RE_EV_NOTE_ADDED     = "consultation_note_added"
RE_EV_FOLLOW_UP      = "follow_up_scheduled"
RE_EV_SITE_PLANNED   = "site_visit_planned"
RE_EV_SITE_COMPLETED = "site_visit_completed"
RE_EV_QUALIFIED      = "lead_qualified"
RE_EV_UNQUALIFIED    = "lead_unqualified"
RE_EV_CONVERTED      = "lead_converted"
RE_EV_CLOSED_LOST    = "lead_closed_lost"

# ── Error codes ────────────────────────────────────────────────────────────────
ERR_RECORD_NOT_FOUND          = "EXECUTION_RECORD_NOT_FOUND"
ERR_ACCESS_DENIED             = "EXECUTION_ACCESS_DENIED"
ERR_INVALID_TRANSITION        = "EXECUTION_INVALID_STATUS_TRANSITION"
ERR_STATUS_ALREADY_SET        = "EXECUTION_STATUS_ALREADY_SET"
ERR_REASON_REQUIRED           = "EXECUTION_REASON_REQUIRED"
ERR_NOTE_REQUIRED             = "EXECUTION_NOTE_REQUIRED"
ERR_JOB_NOT_ASSIGNED          = "EXECUTION_JOB_NOT_ASSIGNED"
ERR_STAFF_NOT_ASSIGNED        = "EXECUTION_STAFF_NOT_ASSIGNED"
ERR_PROVIDER_SCOPE_INVALID    = "EXECUTION_PROVIDER_SCOPE_INVALID"
ERR_CUSTOMER_SCOPE_INVALID    = "EXECUTION_CUSTOMER_SCOPE_INVALID"
ERR_QUOTE_REQUIRED_HANDOFF    = "EXECUTION_QUOTE_REQUIRED_HANDOFF"

# ── HOME-SERVICES-RUNTIME-SAFETY Phase 2A — work-start approval gate ─────────
# Exact codes/messages per spec section 6 (not EXECUTION_-prefixed -- these
# are surfaced directly to staff/technician UI as the reason work cannot start).
ERR_ESTIMATE_REQUIRED          = "ESTIMATE_REQUIRED"
ERR_ESTIMATE_APPROVAL_REQUIRED = "ESTIMATE_APPROVAL_REQUIRED"
ERR_ESTIMATE_REVISION_REQUIRED = "ESTIMATE_REVISION_REQUIRED"
ERR_ESTIMATE_REJECTED          = "ESTIMATE_REJECTED"

MSG_ESTIMATE_REQUIRED          = "Create and send an estimate before starting work."
MSG_ESTIMATE_APPROVAL_REQUIRED = "The customer must approve the current estimate before work can start."
MSG_ESTIMATE_REVISION_REQUIRED = "The customer requested changes. Send a revised estimate for approval."
MSG_ESTIMATE_REJECTED          = "The estimate was rejected. Work cannot start."

# ── HOME-SERVICES-RUNTIME-SAFETY Phase 2A.1 -- exact Job-Type resolution ─────
ERR_JOB_TYPE_CONTEXT_UNRESOLVED = "JOB_TYPE_CONTEXT_UNRESOLVED"
MSG_JOB_TYPE_CONTEXT_UNRESOLVED = "The job type could not be resolved safely. Work cannot start until the job is reconciled."

# ── HS8B — Parts Request ─────────────────────────────────────────────────────
PARTS_STATUS_REQUESTED                 = "requested"
PARTS_STATUS_BUSINESS_APPROVED         = "business_approved"
PARTS_STATUS_BUSINESS_REJECTED         = "business_rejected"
PARTS_STATUS_CUSTOMER_APPROVAL_PENDING = "customer_approval_pending"
PARTS_STATUS_CUSTOMER_APPROVED         = "customer_approved"
PARTS_STATUS_CUSTOMER_REJECTED         = "customer_rejected"
PARTS_STATUS_INSTALLED                 = "installed"
PARTS_STATUS_CANCELLED                 = "cancelled"

# Job statuses during which a parts request may be created — real statuses
# from JOB_TRANSITIONS above, mapped from the ticket's generic
# inspection/service/in_progress/parts_requested vocabulary.
PARTS_REQUEST_ALLOWED_JOB_STATUSES = {
    JS_INSPECTION_STARTED, JS_INSPECTION_DONE,
    JS_SERVICE_STARTED, JS_QUOTE_REQUIRED,
}

ERR_PART_NAME_REQUIRED        = "PART_NAME_REQUIRED"
ERR_QUANTITY_INVALID          = "PART_QUANTITY_INVALID"
ERR_ESTIMATED_COST_INVALID    = "PART_ESTIMATED_COST_INVALID"
ERR_PARTS_REASON_REQUIRED     = "PART_REASON_REQUIRED"
ERR_PARTS_NOT_ALLOWED_STATUS  = "PARTS_REQUEST_NOT_ALLOWED_IN_CURRENT_STATUS"
ERR_PARTS_REQUEST_NOT_FOUND   = "PARTS_REQUEST_NOT_FOUND"
ERR_PARTS_ALREADY_DECIDED     = "PARTS_REQUEST_ALREADY_DECIDED"
ERR_PARTS_NOT_APPROVED        = "PARTS_REQUEST_NOT_APPROVED"
ERR_PARTS_REJECTED_CANNOT_INSTALL = "PARTS_REQUEST_REJECTED_CANNOT_INSTALL"
# PARTS-APPROVAL phase -- a customer tried to decide on a request whose
# `customer_approval_required` flag is false (business-only decision).
ERR_PARTS_CUSTOMER_DECISION_NOT_ALLOWED = "PARTS_REQUEST_CUSTOMER_DECISION_NOT_ALLOWED"

# ── HS8B — Single Validated Completion Action ────────────────────────────────
JS_COMPLETED = "completed"

COMPLETABLE_JOB_STATUSES = {
    JS_SERVICE_STARTED, JS_WORK_DONE, JS_QUOTE_REQUIRED,
}

PAYMENT_MODE_HOME_SERVICES = "customer_pays_provider_directly"

ERR_WORK_SUMMARY_REQUIRED     = "WORK_SUMMARY_REQUIRED"
ERR_COLLECTED_AMOUNT_REQUIRED = "COLLECTED_AMOUNT_REQUIRED"
ERR_COLLECTED_AMOUNT_INVALID  = "COLLECTED_AMOUNT_INVALID"
ERR_PAYMENT_MODE_INVALID      = "PAYMENT_MODE_INVALID"
ERR_JOB_NOT_COMPLETABLE       = "JOB_NOT_COMPLETABLE"
ERR_UNRESOLVED_PARTS_REQUESTS = "UNRESOLVED_PARTS_REQUESTS_BLOCK_COMPLETION"
