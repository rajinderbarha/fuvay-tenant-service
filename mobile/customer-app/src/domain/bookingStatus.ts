/**
 * Central customer-safe status adapter (spec section 4). Confirmed real
 * enum values via direct read of `app/engines/final_records/models.py`
 * AND `app/engines/home_service_assignment/{constants,service.py}` --
 * the latter audit (2026-08-01 correction) found `ServiceBooking.status`/
 * `assignment_status` are written by `_sync_booking` with a RICHER set of
 * values than `final_records/constants.py`'s own `BOOKING_STATUS_*` list
 * documents: `accepted` (JOB_STATUS_ACCEPTED) and `scheduled`
 * (JOB_STATUS_SCHEDULED) are real, live-written statuses that constants.py
 * never names. `KNOWN_BOOKING_STATUSES` below is the complete real set
 * confirmed across BOTH engines -- not just `final_records`' own constants.
 *
 * CORRECTION (2026-08-01): `in_progress`/`completed` previously mapped to
 * a fabricated `scheduled` receipt stage -- neither status actually
 * proves a visit was scheduled. Only `request_confirmed`
 * (`pending_assignment`+`unassigned`) and `provider_assignment` are fully
 * proven this phase (mission statement); `assigned` -> `provider_assigned`
 * remains a direct, evidence-backed mapping (the status IS the evidence).
 * Every OTHER real status -- `accepted`, `scheduled`, `in_progress`,
 * `completed`, `cancelled` -- and any unrecognized future value all
 * render the same safe neutral `unknown` stage until a later, cross-app-
 * proven phase owns them. This is a deliberate allowlist, not an
 * omission: a status not explicitly handled below NEVER falls through to
 * a more-advanced-looking stage by accident.
 */
export type BookingReceiptStage =
  | "request_confirmed"
  | "provider_assignment"
  | "provider_assigned"
  | "scheduled"
  | "unknown";

/** Every real value confirmed written onto `ServiceBooking.status` across
 * `final_records` and `home_service_assignment`. Recognizing a status
 * here does NOT mean this phase renders an advanced stage for it -- see
 * the allowlist in `interpretBookingStatus` below. */
const KNOWN_BOOKING_STATUSES = new Set([
  "pending_assignment", "assigned", "accepted", "scheduled", "in_progress", "completed", "cancelled",
]);

export interface StatusInterpretation {
  stage: BookingReceiptStage;
  statusLabel: string;
  activityText: string | null;
  supportingText: string | null;
}

const NEUTRAL_PENDING: StatusInterpretation = {
  stage: "unknown",
  statusLabel: "Status pending",
  activityText: null,
  supportingText: "Check My Bookings for the latest updates.",
};

/** Never infers a later stage from elapsed time or a timer -- driven
 * entirely by the two real backend fields passed in. A status this phase
 * doesn't fully own always resolves to the same neutral, honest state
 * rather than guessing forward. */
export function interpretBookingStatus(rawStatus: string, assignmentStatus: string): StatusInterpretation {
  if (!KNOWN_BOOKING_STATUSES.has(rawStatus)) {
    return NEUTRAL_PENDING;
  }

  if (rawStatus === "cancelled") {
    return { stage: "unknown", statusLabel: "Cancelled", activityText: null, supportingText: null };
  }

  if (rawStatus === "pending_assignment" && assignmentStatus === "unassigned") {
    return {
      stage: "provider_assignment",
      statusLabel: "Request confirmed",
      activityText: "Assigning an eligible professional",
      supportingText: "We'll notify you when a provider accepts the request.",
    };
  }

  if (rawStatus === "assigned") {
    return {
      stage: "provider_assigned",
      statusLabel: "Provider assigned",
      activityText: "Preparing your visit",
      supportingText: "We'll confirm your visit schedule shortly.",
    };
  }

  // accepted / scheduled / in_progress / completed -- and
  // pending_assignment with any assignment_status other than unassigned
  // -- are real, recognized statuses this phase does not yet own a
  // truthful advanced presentation for. Neutral, never fabricated.
  return NEUTRAL_PENDING;
}

export const RECEIPT_TIMELINE_STEPS: ReadonlyArray<{ key: BookingReceiptStage; label: string }> = [
  { key: "request_confirmed", label: "Request confirmed" },
  { key: "provider_assignment", label: "Provider assignment" },
  { key: "scheduled", label: "Visit scheduling" },
];

export type TimelineStepState = "complete" | "active" | "pending";

/** Pure function -- no timers, no elapsed-time inference (spec: "Never
 * mark provider assignment complete without backend evidence"). */
export function resolveTimelineStepState(stepKey: BookingReceiptStage, currentStage: BookingReceiptStage): TimelineStepState {
  const order: BookingReceiptStage[] = ["request_confirmed", "provider_assignment", "provider_assigned", "scheduled"];
  const currentIndex = order.indexOf(currentStage === "unknown" ? "request_confirmed" : currentStage);
  const stepIndex = order.indexOf(stepKey === "provider_assigned" ? "provider_assignment" : stepKey);
  if (stepIndex < currentIndex) return "complete";
  if (stepIndex === currentIndex) return "active";
  return "pending";
}
