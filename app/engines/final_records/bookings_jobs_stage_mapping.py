"""TENANT-OPS-01 — canonical status -> display stage mapping for the
Bookings & Jobs workspace.

Single source of truth consumed by both the list projection
(tenant_bookings_jobs_router.py) and (eventually) the Board view. Maps the
REAL ServiceJob.status values defined in app.engines.execution.constants
(the actual execution-engine status machine — JOB_TRANSITIONS) to a display
stage, an active/terminal classification, and the action key the frontend
should render as the "next required action" CTA.

Nothing here invents a new database status. Nothing here decides whether an
action is actually ALLOWED right now (permission/eligibility/state checks
still happen at the real mutation endpoint) -- this only decides which
action key/label to *show* given the job's current real status, matching
the spec's "backend computes available actions, frontend never infers from
status alone" rule at the display layer.
"""
from __future__ import annotations

from app.engines.execution.constants import (
    JS_PENDING_ASSIGNMENT, JS_ASSIGNED, JS_ACCEPTED, JS_SCHEDULED,
    JS_ON_THE_WAY, JS_REACHED_SITE, JS_INSPECTION_STARTED, JS_INSPECTION_DONE,
    JS_QUOTE_REQUIRED, JS_SERVICE_STARTED, JS_WORK_DONE,
    JS_CUSTOMER_NOT_AVAIL, JS_CANCELLED, JS_FAILED, JS_CLOSED_ESTIMATE_DECLINED,
)

# Terminal statuses never trigger a next-required-action and never count as
# "active" in the KPI strip.
TERMINAL_STATUSES = {"completed", JS_CANCELLED, JS_FAILED, JS_CLOSED_ESTIMATE_DECLINED}

# status -> (display_stage, action_key, action_label)
_STAGE_MAP: dict[str, tuple[str, str | None, str | None]] = {
    JS_PENDING_ASSIGNMENT:       ("new",                "assign_technician",   "Assign technician"),
    JS_ASSIGNED:                 ("assignment",         "confirm_schedule",    "Confirm schedule"),
    # accepted/reached_site aligned to the admin projection's assignment
    # (operations_service.JOB_STAGE_MAP) so the same job never sits in a
    # different stage on the two screens: `accepted` is still the ASSIGNED
    # phase (the tech accepted, nothing is scheduled yet), and `reached_site`
    # is still ON_THE_WAY until inspection actually starts.
    JS_ACCEPTED:                 ("assignment",         "confirm_schedule",    "Confirm schedule"),
    JS_SCHEDULED:                ("scheduled",          "mark_on_the_way",     "Mark on the way"),
    JS_ON_THE_WAY:               ("on_the_way",         "mark_reached_site",  "Mark reached site"),
    JS_REACHED_SITE:             ("on_the_way",         "start_inspection",   "Start inspection"),
    JS_INSPECTION_STARTED:       ("inspection",         "complete_inspection","Complete inspection"),
    JS_INSPECTION_DONE:          ("estimate_approval",  "create_estimate",    "Create estimate"),
    JS_QUOTE_REQUIRED:           ("estimate_approval",  "send_estimate",      "Send / follow up on estimate"),
    JS_SERVICE_STARTED:          ("in_progress",        "mark_work_done",     "Mark work done"),
    JS_WORK_DONE:                ("payment",            "confirm_payment",    "Confirm direct payment"),
    "completed":                 ("completed",          None,                 None),
    JS_CANCELLED:                ("cancelled",          None,                 None),
    # `failed` is TERMINAL (see TERMINAL_STATUSES) but used to share the
    # "exception" stage with customer_not_available, which is recoverable and
    # carries a reschedule action -- so a dead job was labelled "At risk",
    # implying it was still actionable. Split so the terminal case reads as
    # closed and only the recoverable case reads as at-risk.
    JS_FAILED:                   ("failed",             None,                 None),
    JS_CUSTOMER_NOT_AVAIL:       ("exception",          "reschedule",         "Reschedule visit"),
    JS_CLOSED_ESTIMATE_DECLINED: ("estimate_declined",  None,                 None),
}

# Display-group label shown on the lifecycle tabs (spec section "LIFECYCLE
# PRESENTATION GROUPS") — purely cosmetic grouping over the same statuses.
#
# WORDING IS DELIBERATELY IDENTICAL to the super-admin projection's
# STAGE_LABEL (frontend/super-admin/app/admin/home-services/bookings-jobs/
# page.tsx), so one job never reads as a differently-named stage depending on
# which console you open. Previously these two vocabularies drifted ("New" vs
# "Unassigned", "Estimate approval" vs "Awaiting estimate", "In progress" vs
# "Work in progress", "Payment" vs "Work done"), which made admin and tenant
# unable to discuss a job by stage name.
#
# The stage KEYS are intentionally NOT renamed to admin's uppercase set --
# they drive this workspace's lifecycle stepper ordering, tab filtering and
# next-action CTAs (see the tenant bookings-jobs page's LIFECYCLE_STAGES).
# Only the human-facing labels are unified.
STAGE_LABELS: dict[str, str] = {
    "new":               "Unassigned",
    "assignment":        "Assigned",
    "scheduled":         "Scheduled",
    "on_the_way":        "On the way",
    "inspection":        "Inspection",
    "estimate_approval": "Awaiting estimate",
    "in_progress":       "Work in progress",
    "payment":           "Work done",
    "completed":         "Completed",
    # The three below stay FINER than the admin projection, which collapses
    # cancelled / failed / estimate-declined into a single "CLOSED" stage.
    # Keeping them separate here is deliberate: the tenant needs to tell
    # "customer wasn't available -> reschedule" apart from "cancelled" and
    # from "customer declined the estimate" to know what to do next, and
    # collapsing them to match admin would remove that. Labels are chosen not
    # to collide with admin's wording so the difference reads as more detail
    # rather than a contradiction.
    "cancelled":         "Closed — cancelled",
    "estimate_declined": "Closed — estimate declined",
    "failed":            "Closed — failed",
    "exception":         "At risk",
}


def map_job_status(job_status: str, assignment_status: str | None) -> dict:
    """Returns {stage, stage_label, is_active, is_terminal, next_action}."""
    stage, action_key, action_label = _STAGE_MAP.get(
        job_status, ("exception", None, None)
    )
    is_terminal = job_status in TERMINAL_STATUSES

    # Unassigned overrides the status-derived stage — an assigned status with
    # no assigned_staff_id would be a data-integrity anomaly, but the
    # assignment_status field (owned by home_service_assignment) is the more
    # authoritative source for "does this job actually have someone on it".
    if job_status == JS_PENDING_ASSIGNMENT and assignment_status not in ("assigned",):
        stage = "new"

    next_action = None
    if not is_terminal and action_key:
        next_action = {"action_key": action_key, "label": action_label}

    return {
        "stage":        stage,
        "stage_label":  STAGE_LABELS.get(stage, stage),
        "is_active":    not is_terminal,
        "is_terminal":  is_terminal,
        "next_action":  next_action,
    }


def compute_available_actions(job_status: str, assignment_status: str | None) -> list[dict]:
    """Backend-computed list of action keys valid to *offer* for this job's
    current real status. This mirrors the JOB_TRANSITIONS graph in
    app.engines.execution.constants at a coarse, UI-facing level; the actual
    mutation endpoints (home_service_assignment.provider_router /assign,
    execution.home_service_router status-transition endpoints, quote_checklist
    provider_router, invoice_payment) independently re-validate the real
    transition and are the only source of truth for whether an action
    actually SUCCEEDS -- this list only decides what to render as clickable."""
    actions: list[dict] = []

    if job_status == JS_PENDING_ASSIGNMENT and assignment_status != "assigned":
        actions.append({"action_key": "assign_technician", "label": "Assign technician",
                         "endpoint": "POST /v1/provider/service-jobs/{job_id}/assign"})
    if job_status in (JS_ASSIGNED, JS_ACCEPTED, JS_SCHEDULED):
        actions.append({"action_key": "reassign_technician", "label": "Reassign technician",
                         "endpoint": "POST /v1/provider/service-jobs/{job_id}/reassign"})
        actions.append({"action_key": "schedule", "label": "Schedule",
                         "endpoint": "POST /v1/provider/service-jobs/{job_id}/schedule"})
    if job_status == JS_INSPECTION_DONE:
        actions.append({"action_key": "create_estimate", "label": "Create estimate",
                         "endpoint": "POST /provider/quotes (quote_checklist engine)"})
    if job_status == JS_QUOTE_REQUIRED:
        actions.append({"action_key": "send_estimate", "label": "Send estimate",
                         "endpoint": "POST /provider/quotes (quote_checklist engine)"})
    if job_status == JS_WORK_DONE:
        # Two real, separate payment paths exist in this codebase (confirmed
        # live, not assumed): catalog-priced jobs (e.g. Installation) never
        # get a ServiceInvoice at all -- execution.home_service_service.
        # complete_job() records collected_amount directly on the job and
        # completes it in one action (this is what actually completed the
        # live JOB-20260729-000001 test row). Inspection/estimate-based
        # Repair jobs DO get a ServiceInvoice once the estimate is approved,
        # and that invoice is confirmed via this workspace's own
        # /bookings-jobs/{job_id}/confirm-payment (added this pass, a thin
        # adapter over ServicePaymentService.record_onsite_payment -- see
        # tenant_bookings_jobs_router.py). The frontend should try the invoice
        # path first (GET .../bookings-jobs/{job_id} returns `invoice: null`
        # when none exists) and fall back to the direct-completion endpoint
        # when there is no invoice to confirm against.
        actions.append({"action_key": "mark_work_done_and_confirm_payment",
                         "label": "Mark work done & confirm payment",
                         "endpoint": "POST /v1/staff/service-jobs/{job_id}/complete"})
        actions.append({"action_key": "confirm_payment", "label": "Confirm direct payment (invoiced jobs)",
                         "endpoint": "POST /v1/tenant/home-services/bookings-jobs/{job_id}/confirm-payment"})
    if job_status not in TERMINAL_STATUSES:
        actions.append({"action_key": "cancel_assignment", "label": "Cancel assignment",
                         "endpoint": "POST /v1/provider/service-jobs/{job_id}/cancel-assignment"})

    return actions
