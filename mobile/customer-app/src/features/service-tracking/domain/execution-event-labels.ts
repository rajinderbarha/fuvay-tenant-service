import { logger } from "../../../observability/logger";

/**
 * Unlike CUSTOMER-L5-12's `ServiceJobAssignmentEvent` timeline (which the
 * backend itself already maps to customer-safe labels via
 * `_safe_event_label`), the execution engine's own
 * `GET /v1/customer/service-jobs/{jobId}/tracking` endpoint returns raw
 * `event_type` strings with no server-side customer-safe label mapping
 * at all — this client takes on that responsibility itself, mapping only
 * the real, confirmed event types from `app/engines/execution/constants.py`.
 * See CUSTOMER-L5-13-contract-matrix.md and CUSTOMER-L5-13-timeline-contract.md.
 */
const EVENT_LABEL_KEYS: Record<string, string> = {
  job_accepted: "serviceTracking.event.jobAccepted",
  job_rejected: "serviceTracking.event.jobRejected",
  job_scheduled: "serviceTracking.event.jobScheduled",
  technician_on_the_way: "serviceTracking.event.onTheWay",
  technician_reached_site: "serviceTracking.event.reachedSite",
  inspection_started: "serviceTracking.event.inspectionStarted",
  inspection_completed: "serviceTracking.event.inspectionCompleted",
  service_started: "serviceTracking.event.serviceStarted",
  work_done: "serviceTracking.event.workDone",
  customer_not_available: "serviceTracking.event.customerNotAvailable",
  job_cancelled: "serviceTracking.event.jobCancelled",
  job_failed: "serviceTracking.event.jobFailed",
  quote_required: "serviceTracking.event.quoteRequired",
  parts_required: "serviceTracking.event.partsRequired",
};

/**
 * Fails safe: an unrecognized event type is dropped from the rendered
 * timeline entirely (never shown as a raw internal string, and never
 * silently rendered as if it were a known milestone) — the caller is
 * expected to filter out `null` results. Diagnosis/photo/work-note events
 * (`diagnosis_added`, `before_photo_uploaded`, `after_photo_uploaded`,
 * `work_note_added`) are real but deliberately unmapped: they are
 * execution detail (notes/media), not status milestones, and this
 * sprint's scope is the milestone timeline only (contract-matrix.md).
 */
export function resolveExecutionEventLabelKey(eventType: string): string | null {
  const key = EVENT_LABEL_KEYS[eventType];
  if (!key) {
    logger.warn("execution_event_unmapped", { eventType });
    return null;
  }
  return key;
}
