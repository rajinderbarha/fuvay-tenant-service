/**
 * Centralized status registry (CUSTOMER-L5-12 §26, extended by
 * CUSTOMER-L5-13 and CUSTOMER-L5-14). Covers the full real
 * `ServiceJob.status` vocabulary.
 *
 * CUSTOMER-L5-12 found that `final_records/constants.py`'s own
 * `JOB_STATUS_DISPATCHED`/`_IN_PROGRESS`/`_COMPLETED`/`_CANCELLED`
 * constants are never assigned by any real code path — that remains true
 * for those specific constants. CUSTOMER-L5-13's own research found a
 * *separate*, real, live execution engine (`app/engines/execution/`,
 * deliberately deferred by L5-12) with its own, differently-named real
 * status constants that genuinely ARE written to this same
 * `ServiceJob.status` column via real, permission-checked staff
 * endpoints: `on_the_way`, `reached_site`, `inspection_started`,
 * `inspection_done`, `quote_required`, `service_started`, `work_done`,
 * `customer_not_available`, plus real `completed`/`cancelled`/`failed`
 * (see CUSTOMER-L5-13-baseline-verification.md's Central Findings #1).
 * `dispatched`/`in_progress` (the L5-12-era, unused `final_records`
 * names) remain mapped for forward-compatibility only — still never
 * observed assigned by any real code path.
 *
 * CUSTOMER-L5-14 found a *third*, again separate real engine
 * (`app/engines/quote_checklist/`) that writes yet another, differently
 * named set of real statuses to this same `ServiceJob.status` column as
 * a side effect of its own customer quote-decision actions:
 * `awaiting_customer_quote_approval`, `quote_approved`, `quote_rejected`,
 * `quote_revision_requested` — see
 * CUSTOMER-L5-14-contract-matrix.md's job/booking status side-effects
 * table. These are genuinely reachable (this sprint's own
 * `customer_approve`/`customer_reject`/`customer_request_revision`
 * mutations trigger them), unlike `execution`'s already-known dead
 * `dispatched`/`in_progress`.
 */
export type BookingStatusGroup = "active" | "past";

export interface BookingStatusDefinition {
  code: string;
  titleKey: string;
  group: BookingStatusGroup;
  terminal: boolean;
  success: boolean;
  warning: boolean;
}

const REGISTRY: Record<string, BookingStatusDefinition> = {
  pending_assignment: {
    code: "pending_assignment",
    titleKey: "bookings.status.pendingAssignment",
    group: "active",
    terminal: false,
    success: false,
    warning: false,
  },
  assigned: { code: "assigned", titleKey: "bookings.status.assigned", group: "active", terminal: false, success: false, warning: false },
  accepted: { code: "accepted", titleKey: "bookings.status.accepted", group: "active", terminal: false, success: false, warning: false },
  scheduled: { code: "scheduled", titleKey: "bookings.status.scheduled", group: "active", terminal: false, success: false, warning: false },
  dispatched: { code: "dispatched", titleKey: "bookings.status.dispatched", group: "active", terminal: false, success: false, warning: false },
  in_progress: { code: "in_progress", titleKey: "bookings.status.inProgress", group: "active", terminal: false, success: false, warning: false },
  on_the_way: { code: "on_the_way", titleKey: "bookings.status.onTheWay", group: "active", terminal: false, success: false, warning: false },
  reached_site: { code: "reached_site", titleKey: "bookings.status.reachedSite", group: "active", terminal: false, success: false, warning: false },
  inspection_started: {
    code: "inspection_started",
    titleKey: "bookings.status.inspectionStarted",
    group: "active",
    terminal: false,
    success: false,
    warning: false,
  },
  inspection_done: { code: "inspection_done", titleKey: "bookings.status.inspectionDone", group: "active", terminal: false, success: false, warning: false },
  quote_required: { code: "quote_required", titleKey: "bookings.status.quoteRequired", group: "active", terminal: false, success: false, warning: false },
  service_started: { code: "service_started", titleKey: "bookings.status.serviceStarted", group: "active", terminal: false, success: false, warning: false },
  work_done: { code: "work_done", titleKey: "bookings.status.workDone", group: "active", terminal: false, success: false, warning: false },
  customer_not_available: {
    code: "customer_not_available",
    titleKey: "bookings.status.customerNotAvailable",
    group: "active",
    terminal: false,
    success: false,
    warning: true,
  },
  awaiting_customer_quote_approval: {
    code: "awaiting_customer_quote_approval",
    titleKey: "bookings.status.awaitingQuoteApproval",
    group: "active",
    terminal: false,
    success: false,
    warning: true,
  },
  quote_approved: { code: "quote_approved", titleKey: "bookings.status.quoteApproved", group: "active", terminal: false, success: true, warning: false },
  quote_rejected: { code: "quote_rejected", titleKey: "bookings.status.quoteRejected", group: "active", terminal: false, success: false, warning: true },
  quote_revision_requested: {
    code: "quote_revision_requested",
    titleKey: "bookings.status.quoteRevisionRequested",
    group: "active",
    terminal: false,
    success: false,
    warning: true,
  },
  completed: { code: "completed", titleKey: "bookings.status.completed", group: "past", terminal: true, success: true, warning: false },
  cancelled: { code: "cancelled", titleKey: "bookings.status.cancelled", group: "past", terminal: true, success: false, warning: true },
  failed: { code: "failed", titleKey: "bookings.status.failed", group: "past", terminal: true, success: false, warning: true },
};

const UNKNOWN_STATUS: BookingStatusDefinition = {
  code: "unknown",
  titleKey: "bookings.status.processing",
  group: "active",
  terminal: false,
  success: false,
  warning: false,
};

/** Fails safe: an unrecognized status never defaults to "completed" or any terminal/success state (CUSTOMER-L5-12 §26's hard requirement). */
export function resolveBookingStatus(code: string): BookingStatusDefinition {
  return REGISTRY[code] ?? UNKNOWN_STATUS;
}

export function isKnownBookingStatus(code: string): boolean {
  return code in REGISTRY;
}
