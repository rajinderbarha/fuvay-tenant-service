"""Sprint 20 — Home Service Job Assignment constants."""

# ── Assignment statuses ────────────────────────────────────────────────────────
ASSIGN_STATUS_ASSIGNED   = "assigned"
ASSIGN_STATUS_ACCEPTED   = "accepted"
ASSIGN_STATUS_REJECTED   = "rejected"
ASSIGN_STATUS_CANCELLED  = "cancelled"
ASSIGN_STATUS_REASSIGNED = "reassigned"

# ── Job assignment_status values (on service_jobs / service_bookings) ──────────
JOB_ASSIGN_UNASSIGNED  = "unassigned"
JOB_ASSIGN_ASSIGNED    = "assigned"
JOB_ASSIGN_ACCEPTED    = "accepted"
JOB_ASSIGN_REJECTED    = "rejected"
JOB_ASSIGN_CANCELLED   = "cancelled"
JOB_ASSIGN_REASSIGNED  = "reassigned"

# ── Job status values (Sprint 20 subset) ──────────────────────────────────────
JOB_STATUS_PENDING_ASSIGNMENT = "pending_assignment"
JOB_STATUS_ASSIGNED           = "assigned"
JOB_STATUS_ACCEPTED           = "accepted"
JOB_STATUS_SCHEDULED          = "scheduled"
JOB_STATUS_CANCELLED          = "cancelled"
JOB_STATUS_FAILED             = "failed"

# ── Assignment types ───────────────────────────────────────────────────────────
ASSIGN_TYPE_MANUAL         = "manual"
ASSIGN_TYPE_AUTO           = "auto"
ASSIGN_TYPE_ADMIN_OVERRIDE = "admin_override"

# ── Event types ────────────────────────────────────────────────────────────────
EVENT_JOB_RECEIVED           = "job_received"
EVENT_ASSIGNMENT_CREATED     = "assignment_created"
EVENT_ASSIGNMENT_REASSIGNED  = "assignment_reassigned"
EVENT_ASSIGNMENT_CANCELLED   = "assignment_cancelled"
EVENT_TECHNICIAN_ACCEPTED    = "technician_accepted"
EVENT_TECHNICIAN_REJECTED    = "technician_rejected"
EVENT_JOB_SCHEDULED          = "job_scheduled"
EVENT_ASSIGNMENT_FAILED      = "assignment_failed"
EVENT_CUSTOMER_CANCELLED     = "customer_cancelled_booking"
EVENT_CUSTOMER_RESCHEDULED   = "customer_rescheduled_booking"

# ── Staff roles eligible for field execution ──────────────────────────────────
ELIGIBLE_DESIGNATIONS = {
    "technician",
    "field_staff",
    "service_worker",
    "engineer",
    "installer",
    "field_engineer",
    "senior_technician",
    "lead_technician",
}

# ── Error codes ────────────────────────────────────────────────────────────────
ERR_JOB_NOT_FOUND                = "JOB_ASSIGNMENT_JOB_NOT_FOUND"
ERR_JOB_CANCELLED                = "JOB_ASSIGNMENT_JOB_CANCELLED"
ERR_JOB_COMPLETED                = "JOB_ASSIGNMENT_JOB_COMPLETED"
ERR_ASSIGNMENT_NOT_FOUND         = "JOB_ASSIGNMENT_NOT_FOUND"
ERR_ACCESS_DENIED                = "JOB_ASSIGNMENT_ACCESS_DENIED"
ERR_INVALID_STATUS               = "JOB_ASSIGNMENT_INVALID_STATUS"
ERR_ALREADY_ASSIGNED             = "JOB_ASSIGNMENT_ALREADY_ASSIGNED"
ERR_STAFF_NOT_FOUND              = "JOB_ASSIGNMENT_STAFF_NOT_FOUND"
ERR_STAFF_NOT_ELIGIBLE           = "JOB_ASSIGNMENT_STAFF_NOT_ELIGIBLE"
ERR_STAFF_WRONG_TENANT           = "JOB_ASSIGNMENT_STAFF_WRONG_TENANT"
ERR_STAFF_INACTIVE               = "JOB_ASSIGNMENT_STAFF_INACTIVE"
ERR_ROLE_NOT_ALLOWED             = "JOB_ASSIGNMENT_ROLE_NOT_ALLOWED"
ERR_CONFLICT                     = "JOB_ASSIGNMENT_CONFLICT"
ERR_REASON_REQUIRED              = "JOB_ASSIGNMENT_REASON_REQUIRED"
ERR_REASSIGN_NOT_ALLOWED         = "JOB_ASSIGNMENT_REASSIGN_NOT_ALLOWED"
ERR_CANCEL_NOT_ALLOWED           = "JOB_ASSIGNMENT_CANCEL_NOT_ALLOWED"
ERR_BOOKING_NOT_FOUND            = "JOB_ASSIGNMENT_BOOKING_NOT_FOUND"
ERR_RESCHEDULE_NOT_ALLOWED       = "JOB_ASSIGNMENT_RESCHEDULE_NOT_ALLOWED"
ERR_STAFF_JOB_NOT_ASSIGNED       = "STAFF_JOB_NOT_ASSIGNED_TO_USER"
ERR_STAFF_JOB_ALREADY_ACCEPTED   = "STAFF_JOB_ALREADY_ACCEPTED"
ERR_STAFF_JOB_ALREADY_REJECTED   = "STAFF_JOB_ALREADY_REJECTED"

# MODULE-L5-29: a customer may cancel/reschedule its own booking only before
# real work has begun — once a quote is approved or an invoice is issued the
# provider may already have incurred cost, so those cases must go through a
# complaint/refund conversation instead of a bare self-service cancel.
CUSTOMER_CANCELLABLE_JOB_STATUSES = {
    "pending_assignment", "assigned", "accepted", "scheduled",
}
