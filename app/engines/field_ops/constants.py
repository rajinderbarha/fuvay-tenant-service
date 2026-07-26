"""Field Ops Engine — 23-status lifecycle and allowed-transitions graph.

Universal Service Phase Logic (Phase 7): three job types ride the same
status vocabulary but branch at a handful of points:
  - repair:       full lifecycle, assessment mandatory, quote optional.
  - service:      skips assessment entirely (price known upfront), checklist
                   required before work_complete.
  - consultation: assessment + quote only — no physical work statuses.
                   Approving the quote spawns a NEW repair job (see
                   FieldOpsService.respond_to_quote); the consultation job
                   itself still rides sign-off → invoice → close to bill the
                   consult fee, regardless of approve/reject.
"""

# ── Job Types ─────────────────────────────────────────────────────────────────
class JobType:
    REPAIR         = "repair"
    SERVICE        = "service"
    CONSULTATION   = "consultation"
    # Migration 151: admin_catalog.VALID_JOB_TYPES (service.py) already allows
    # these 6 additional values -- they previously had no entry here, so
    # get_allowed_transitions() silently fell back to the full repair graph
    # (mandatory assessment) for all of them with no way to configure
    # otherwise. Behavior below now mirrors app.engines.admin_catalog's
    # job_types table (requires_assessment/allows_quote/requires_checklist
    # seeded in migration 151) so both stay in sync.
    INSTALLATION   = "installation"
    UNINSTALLATION = "uninstallation"
    INSPECTION     = "inspection"
    MAINTENANCE    = "maintenance"
    CLEANING       = "cleaning"
    CUSTOM         = "custom"

JOB_TYPES = [
    JobType.REPAIR, JobType.SERVICE, JobType.CONSULTATION,
    JobType.INSTALLATION, JobType.UNINSTALLATION, JobType.INSPECTION,
    JobType.MAINTENANCE, JobType.CLEANING, JobType.CUSTOM,
]

# ── Job Statuses ───────────────────────────────────────────────────────────────
class JS:
    DRAFT               = "draft"
    PENDING_ASSIGNMENT  = "pending_assignment"   # Step 5: jobs created from booking start here
    ASSIGNED            = "assigned"             # Step 6: tenant assigned staff, awaiting accept
    REJECTED_BY_STAFF   = "rejected_by_staff"    # Step 6: staff declined the assignment
    CONFIRMED           = "confirmed"
    DISPATCHED          = "dispatched"
    ACCEPTED            = "accepted"
    EN_ROUTE            = "en_route"
    ARRIVED             = "arrived"
    ASSESSMENT_STARTED  = "assessment_started"
    ASSESSMENT_COMPLETE = "assessment_complete"
    QUOTE_PENDING       = "quote_sent"           # Step 7: renamed value (was "quote_pending")
    QUOTE_SENT          = QUOTE_PENDING          # Step 7: spec-named alias, same status
    QUOTE_APPROVED      = "quote_approved"
    QUOTE_REJECTED      = "quote_rejected"
    WORK_STARTED        = "work_started"
    PARTS_REQUIRED      = "parts_required"
    PARTS_ORDERED       = "parts_ordered"
    PARTS_RECEIVED      = "parts_received"
    WORK_RESUMED        = "work_resumed"
    WORK_COMPLETE       = "work_complete"
    CHECKLIST_STARTED   = "checklist_started"    # Step 7: service-only
    CHECKLIST_COMPLETE  = "checklist_complete"   # Step 7: service-only
    QUALITY_CHECK       = "quality_check"
    QUALITY_PASSED      = "quality_passed"
    QUALITY_FAILED      = "quality_failed"
    REWORK_REQUIRED     = "rework_required"
    REWORK_COMPLETE     = "rework_complete"
    PENDING_SIGN_OFF    = "pending_sign_off"
    SIGNED_OFF          = "signed_off"
    INVOICE_GENERATED   = "invoice_generated"
    PAYMENT_PENDING     = "payment_pending"    # Step 9: online-gateway payment awaited
    PAID                = "paid"               # Step 9: payment confirmed, pre-closure
    COMPLETED           = "completed"          # Step 6: simple lifecycle end (no billing yet)
    CONVERTED_TO_REPAIR = "converted_to_repair"  # Step 7: consultation -> repair conversion
    CLOSED              = "closed"
    VOIDED              = "voided"
    CANCELLED           = "cancelled"

# ── Base allowed-transitions graph — the repair flow (most complete) ─────────
ALLOWED_TRANSITIONS: dict[str, list[str]] = {
    JS.DRAFT:               [JS.CONFIRMED, JS.PENDING_ASSIGNMENT, JS.CANCELLED],
    JS.PENDING_ASSIGNMENT:  [JS.ASSIGNED, JS.CONFIRMED, JS.CANCELLED],
    JS.ASSIGNED:            [JS.ACCEPTED, JS.REJECTED_BY_STAFF, JS.CANCELLED],
    JS.REJECTED_BY_STAFF:   [JS.ASSIGNED, JS.CANCELLED],
    JS.CONFIRMED:           [JS.DISPATCHED, JS.CANCELLED],
    JS.DISPATCHED:          [JS.ACCEPTED, JS.CANCELLED],
    JS.ACCEPTED:            [JS.EN_ROUTE, JS.CANCELLED],
    JS.EN_ROUTE:            [JS.ARRIVED, JS.CANCELLED],
    JS.ARRIVED:             [JS.ASSESSMENT_STARTED],
    JS.ASSESSMENT_STARTED:  [JS.ASSESSMENT_COMPLETE],
    JS.ASSESSMENT_COMPLETE: [JS.WORK_STARTED, JS.PARTS_REQUIRED, JS.QUOTE_PENDING, JS.CANCELLED],
    JS.QUOTE_PENDING:       [JS.QUOTE_APPROVED, JS.QUOTE_REJECTED],
    JS.QUOTE_APPROVED:      [JS.WORK_STARTED, JS.PARTS_REQUIRED],
    JS.QUOTE_REJECTED:      [JS.ASSESSMENT_COMPLETE, JS.CANCELLED],
    JS.WORK_STARTED:        [JS.WORK_COMPLETE, JS.PARTS_REQUIRED],
    JS.PARTS_REQUIRED:      [JS.PARTS_ORDERED],
    JS.PARTS_ORDERED:       [JS.PARTS_RECEIVED],
    JS.PARTS_RECEIVED:      [JS.WORK_RESUMED],
    JS.WORK_RESUMED:        [JS.WORK_COMPLETE],
    JS.WORK_COMPLETE:       [JS.QUALITY_CHECK],
    JS.CHECKLIST_STARTED:   [JS.CHECKLIST_COMPLETE],
    JS.CHECKLIST_COMPLETE:  [JS.WORK_COMPLETE],
    JS.CONVERTED_TO_REPAIR: [JS.CLOSED],
    JS.QUALITY_CHECK:       [JS.QUALITY_PASSED, JS.QUALITY_FAILED],
    JS.QUALITY_PASSED:      [JS.PENDING_SIGN_OFF],
    JS.QUALITY_FAILED:      [JS.REWORK_REQUIRED],
    JS.REWORK_REQUIRED:     [JS.REWORK_COMPLETE],
    JS.REWORK_COMPLETE:     [JS.QUALITY_CHECK],
    JS.PENDING_SIGN_OFF:    [JS.SIGNED_OFF],
    JS.SIGNED_OFF:          [JS.INVOICE_GENERATED, JS.COMPLETED],
    # Step 9: invoice_generated -> {payment_pending (gateway) | paid (cash/upi on-site)} -> closed.
    # CLOSED kept directly reachable too, for the pre-existing atomic close_job() pipeline.
    JS.INVOICE_GENERATED:   [JS.PAYMENT_PENDING, JS.PAID, JS.CLOSED],
    JS.PAYMENT_PENDING:     [JS.PAID],
    JS.PAID:                [JS.CLOSED],
    JS.COMPLETED:           [],
    JS.CLOSED:              [],
    JS.VOIDED:              [],
    JS.CANCELLED:           [],
}

# ── Per-job-type overrides — only the statuses that actually diverge ─────────
TYPE_TRANSITION_OVERRIDES: dict[str, dict[str, list[str]]] = {
    JobType.SERVICE: {
        # Price known upfront, no assessment needed normally — straight to work.
        JS.ARRIVED: [JS.WORK_STARTED, JS.CANCELLED],
        # Step 7: checklist loop is optional (service catalog: requires_checklist) —
        # work_complete is allowed directly when no checklist is required.
        JS.WORK_STARTED: [JS.CHECKLIST_STARTED, JS.WORK_COMPLETE, JS.PARTS_REQUIRED, JS.CANCELLED],
        JS.CHECKLIST_COMPLETE: [JS.WORK_COMPLETE, JS.CANCELLED],
    },
    JobType.CONSULTATION: {
        # Consultation's "work" IS the assessment — never touches WORK_STARTED.
        JS.ASSESSMENT_COMPLETE: [JS.QUOTE_PENDING, JS.CANCELLED],
        # Step 7: dedicated tenant-triggered conversion path (no billing yet);
        # the legacy auto-spawn-on-approval path (sign-off → invoice → close,
        # billing the consult fee) remains available alongside it.
        JS.QUOTE_APPROVED: [JS.CONVERTED_TO_REPAIR, JS.PENDING_SIGN_OFF],
        JS.QUOTE_REJECTED: [JS.PENDING_SIGN_OFF, JS.CLOSED],
    },
    # Migration 151: no assessment, no quote, checklist required before
    # completion (job_types: requires_assessment=False, allows_quote=False,
    # requires_checklist=True) — price known upfront, same shape as SERVICE.
    JobType.INSTALLATION: {
        JS.ARRIVED: [JS.WORK_STARTED, JS.CANCELLED],
        JS.WORK_STARTED: [JS.CHECKLIST_STARTED, JS.WORK_COMPLETE, JS.PARTS_REQUIRED, JS.CANCELLED],
        JS.CHECKLIST_COMPLETE: [JS.WORK_COMPLETE, JS.CANCELLED],
    },
    JobType.MAINTENANCE: {
        JS.ARRIVED: [JS.WORK_STARTED, JS.CANCELLED],
        JS.WORK_STARTED: [JS.CHECKLIST_STARTED, JS.WORK_COMPLETE, JS.PARTS_REQUIRED, JS.CANCELLED],
        JS.CHECKLIST_COMPLETE: [JS.WORK_COMPLETE, JS.CANCELLED],
    },
    JobType.CLEANING: {
        JS.ARRIVED: [JS.WORK_STARTED, JS.CANCELLED],
        JS.WORK_STARTED: [JS.CHECKLIST_STARTED, JS.WORK_COMPLETE, JS.PARTS_REQUIRED, JS.CANCELLED],
        JS.CHECKLIST_COMPLETE: [JS.WORK_COMPLETE, JS.CANCELLED],
    },
    # No assessment, no quote, no checklist (job_types: all three False) —
    # skip straight from ARRIVED to work, complete directly.
    JobType.UNINSTALLATION: {
        JS.ARRIVED: [JS.WORK_STARTED, JS.CANCELLED],
    },
    # INSPECTION deliberately has NO override here: its flags (requires_
    # assessment=True, allows_quote=True, requires_checklist=False) are
    # already exactly what the base repair-flow graph provides, so the
    # get_allowed_transitions() fallback to ALLOWED_TRANSITIONS is correct.
    #
    # CUSTOM: same assessment/quote shape as repair, but ALSO requires a
    # checklist before work_complete (job_types: all three True).
    JobType.CUSTOM: {
        JS.WORK_STARTED: [JS.CHECKLIST_STARTED, JS.PARTS_REQUIRED, JS.CANCELLED],
        JS.CHECKLIST_COMPLETE: [JS.WORK_COMPLETE, JS.CANCELLED],
    },
}


def get_allowed_transitions(job_type: str, status: str) -> list[str]:
    """Resolve the allowed next-statuses for a given job_type, falling back
    to the shared (repair) graph for anything that doesn't diverge."""
    overrides = TYPE_TRANSITION_OVERRIDES.get(job_type, {})
    if status in overrides:
        return overrides[status]
    return ALLOWED_TRANSITIONS.get(status, [])

# Step 7: full per-job_type transition graph, materialized from the shared
# graph + overrides above — spec-required name for direct introspection.
TRANSITIONS_BY_JOB_TYPE: dict[str, dict[str, list[str]]] = {
    jt: {status: get_allowed_transitions(jt, status) for status in ALLOWED_TRANSITIONS}
    for jt in JOB_TYPES
}

# Statuses where staff cannot be changed
LOCKED_STATUSES = [
    JS.WORK_STARTED, JS.WORK_RESUMED, JS.WORK_COMPLETE,
    JS.QUALITY_CHECK, JS.QUALITY_PASSED, JS.PENDING_SIGN_OFF,
    JS.SIGNED_OFF, JS.INVOICE_GENERATED, JS.CLOSED,
]

# Terminal statuses
TERMINAL_STATUSES = [JS.CLOSED, JS.VOIDED, JS.CANCELLED, JS.COMPLETED]

# SLA thresholds per status (hours) — overridden by Settings engine
DEFAULT_STATUS_SLA_HOURS: dict[str, float] = {
    JS.DISPATCHED: 2.0,
    JS.ACCEPTED:   1.0,
    JS.EN_ROUTE:   2.0,
    JS.ARRIVED:    0.5,
    JS.WORK_STARTED: 8.0,
}

REDIS_JOB_TOKEN  = "serviceos:fo:job_token:{token}"
REDIS_JOB_COUNTS = "serviceos:fo:counts:{tenant_id}"
