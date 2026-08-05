/**
 * ARRIVAL-INSPECTION-QUOTE-APPROVAL phase -- customer-facing presentation
 * for the job/quote states this phase owns. Two independent real backend
 * vocabularies feed this: `ServiceJob.status` (real values confirmed via
 * `app/engines/execution/constants.py`: "reached_site", "inspection_started",
 * "inspection_done", "quote_required", ...) and `ServiceJobQuote.status`
 * (confirmed via `quote_checklist/constants.py`: "sent_to_customer",
 * "customer_approved", "customer_rejected", "revision_requested", "expired",
 * "cancelled", ...). Both are closed, string-keyed mappers with a neutral
 * fallback -- no raw backend enum ever reaches JSX directly.
 */

export type ArrivalInspectionStage = "arrived" | "inspecting" | "inspection_done" | "in_progress" | "work_done";

const ARRIVAL_STAGE_MAP: Record<string, ArrivalInspectionStage> = {
  reached_site: "arrived",
  inspection_started: "inspecting",
  inspection_done: "inspection_done",
  quote_required: "inspection_done",
  service_started: "in_progress",
  work_done: "work_done",
};

/** Fails safe to null for every job status this phase does not own
 * (pending_assignment, assigned, accepted, scheduled, on_the_way,
 * service_started, work_done, completed, cancelled, and any future/
 * unrecognized value). */
export function resolveArrivalInspectionStage(jobRawStatus: string | null | undefined): ArrivalInspectionStage | null {
  if (jobRawStatus && jobRawStatus in ARRIVAL_STAGE_MAP) {
    return ARRIVAL_STAGE_MAP[jobRawStatus];
  }
  return null;
}

export interface ArrivalInspectionPresentation {
  title: string;
  explanation: string;
}

const ARRIVAL_PRESENTATION: Record<ArrivalInspectionStage, ArrivalInspectionPresentation> = {
  arrived: { title: "Arrived", explanation: "Your service professional has arrived at your location." },
  inspecting: { title: "Inspection in progress", explanation: "The professional is inspecting your service." },
  inspection_done: { title: "Inspection complete", explanation: "The inspection is complete." },
  in_progress: { title: "Repair in progress", explanation: "Your service professional is carrying out the repair." },
  work_done: { title: "Work done", explanation: "The repair work is finished. Your provider will mark this job complete shortly." },
};

export function resolveArrivalInspectionPresentation(stage: ArrivalInspectionStage): ArrivalInspectionPresentation {
  return ARRIVAL_PRESENTATION[stage];
}

export type QuoteDecisionStage = "pending" | "ready" | "approved" | "declined" | "unavailable";

const QUOTE_STAGE_MAP: Record<string, QuoteDecisionStage> = {
  sent_to_customer: "ready",
  customer_approved: "approved",
  customer_rejected: "declined",
  revision_requested: "unavailable",
  expired: "unavailable",
  cancelled: "unavailable",
  draft: "pending",
  submitted_to_provider: "pending",
  provider_approved: "pending",
  provider_rejected: "pending",
  revised: "pending",
};

/** Never claims "ready" for a status this phase hasn't proven actionable --
 * an unrecognized future quote status resolves to "unavailable" (safe,
 * non-actionable), not "ready" (which would render live Approve/Decline
 * buttons against an unproven contract). */
export function resolveQuoteDecisionStage(quoteRawStatus: string | null | undefined): QuoteDecisionStage {
  if (quoteRawStatus && quoteRawStatus in QUOTE_STAGE_MAP) {
    return QUOTE_STAGE_MAP[quoteRawStatus];
  }
  return "unavailable";
}

export interface QuoteDecisionPresentation {
  title: string;
  explanation: string | null;
}

const QUOTE_DECISION_PRESENTATION: Record<QuoteDecisionStage, QuoteDecisionPresentation> = {
  pending: { title: "Estimate not ready", explanation: "Your provider is preparing an estimate." },
  ready: { title: "Quote ready", explanation: "The inspection is complete. Review the estimate before work begins." },
  approved: { title: "Quote approved", explanation: "You approved this estimate. Repair work can begin." },
  declined: { title: "Quote declined", explanation: "You declined this estimate." },
  unavailable: { title: "Status updating", explanation: null },
};

export function resolveQuoteDecisionPresentation(stage: QuoteDecisionStage): QuoteDecisionPresentation {
  return QUOTE_DECISION_PRESENTATION[stage];
}
