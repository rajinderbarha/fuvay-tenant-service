/**
 * Verified workflow status unions. Every value here is confirmed against
 * the backend source of truth as of Phase D:
 *   - job status literals: app/engines/execution/constants.py (JS_*)
 *   - assignment status literals: app/engines/home_service_assignment/customer_router.py
 *     (_ASSIGNMENT_DISPLAY map) and service.py
 *   - parts status literals: app/engines/execution/constants.py (PARTS_STATUS_*)
 *
 * `ServiceBooking.status` / `ServiceJob.status` are plain VARCHAR columns
 * (String(40)), not a database enum -- the backend enforces the allowed
 * set in application code, not the schema. That means a value this app has
 * never seen is a real possibility (a future backend status added without
 * a client update), not just a theoretical TypeScript concern. Every
 * parser in src/api/adapters must route an unrecognized value through
 * `UnknownStatusError` (see errors.ts) rather than guessing or silently
 * defaulting -- see section 12 of the Phase D spec.
 */

export const JOB_STATUSES = [
  "pending_assignment",
  "assigned",
  "accepted",
  "scheduled",
  "on_the_way",
  "reached_site",
  "inspection_started",
  "inspection_done",
  "quote_required",
  "service_started",
  "work_done",
  "customer_not_available",
  "cancelled",
  "failed",
  "closed_estimate_declined",
  "completed",
] as const;
export type JobStatus = (typeof JOB_STATUSES)[number];

export const ASSIGNMENT_STATUSES = [
  "unassigned",
  "assigned",
  "accepted",
  "rejected",
  "cancelled",
  "reassigned",
] as const;
export type AssignmentStatus = (typeof ASSIGNMENT_STATUSES)[number];

/** ServiceBooking.status shares the same lifecycle vocabulary as the job it
 * spawns, plus its own pre-assignment starting value. */
export const BOOKING_STATUSES = [
  "pending_assignment",
  "assigned",
  "accepted",
  "scheduled",
  "cancelled",
  "failed",
  "completed",
] as const;
export type BookingStatus = (typeof BOOKING_STATUSES)[number];

/** Confirmed in app/engines/execution/constants.py (PARTS_STATUS_*).
 * NOTE: no customer-facing route currently exposes this to the mobile app
 * (see capability registry, key `parts.customerView` = MISSING) even
 * though the backend already models a customer-approval step -- do not
 * build screens against this until a route exists. */
export const PARTS_REQUEST_STATUSES = [
  "requested",
  "business_approved",
  "business_rejected",
  "customer_approval_pending",
  "customer_approved",
  "customer_rejected",
  "installed",
  "cancelled",
] as const;
export type PartsRequestStatus = (typeof PARTS_REQUEST_STATUSES)[number];

/** Confirmed in app/engines/quote_checklist -- exact enum values were not
 * exhaustively grepped this phase; the set below covers every transition
 * reachable from the verified customer_router.py actions (approve/reject/
 * request-revision) plus the natural pending/expired bookends. Treat as
 * SOURCE_VERIFIED-partial: adapters must still reject unknown values. */
export const QUOTE_STATUSES = [
  "pending",
  "sent",
  "approved",
  "rejected",
  "revision_requested",
  "expired",
] as const;
export type QuoteStatus = (typeof QUOTE_STATUSES)[number];

export const NOTIFICATION_STATES = ["unread", "read"] as const;
export type NotificationState = (typeof NOTIFICATION_STATES)[number];

/** No backend route currently exists for customer review *eligibility*
 * beyond a boolean + reason (GET /v1/customer/reviews/eligibility) --
 * this models that response, not a broader lifecycle. */
export const REVIEW_ELIGIBILITY_REASONS = [
  "eligible",
  "already_reviewed",
  "job_not_completed",
  "not_found",
] as const;
export type ReviewEligibilityReason = (typeof REVIEW_ELIGIBILITY_REASONS)[number];

function isOneOf<T extends string>(values: readonly T[], value: string): value is T {
  return (values as readonly string[]).includes(value);
}

export const isJobStatus = (v: string): v is JobStatus => isOneOf(JOB_STATUSES, v);
export const isAssignmentStatus = (v: string): v is AssignmentStatus => isOneOf(ASSIGNMENT_STATUSES, v);
export const isBookingStatus = (v: string): v is BookingStatus => isOneOf(BOOKING_STATUSES, v);
export const isQuoteStatus = (v: string): v is QuoteStatus => isOneOf(QUOTE_STATUSES, v);
