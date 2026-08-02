import { Theme } from "./themes/buildTheme";

/**
 * Centralized backend-status -> display mapping (foundation spec section
 * 16). Values match the REAL canonical job status constants in
 * app/engines/execution/constants.py (JOB_TRANSITIONS) -- not invented.
 * Screens must import WORKFLOW_STATUS_MAP rather than hand-writing a label
 * or color for a status string anywhere else.
 */
export type WorkflowTone = "completed" | "current" | "upcoming" | "blocked" | "cancelled" | "neutral";

export interface WorkflowStatusEntry {
  label: string;
  tone: WorkflowTone;
  description: string;
}

export const WORKFLOW_STATUS_MAP: Record<string, WorkflowStatusEntry> = {
  pending_assignment: { label: "Pending Assignment", tone: "upcoming", description: "Waiting to be assigned to a technician." },
  assigned:            { label: "Assigned",            tone: "current",   description: "Assigned to you -- accept or decline." },
  accepted:            { label: "Accepted",            tone: "current",   description: "You've accepted this job." },
  scheduled:           { label: "Scheduled",            tone: "upcoming",  description: "Scheduled for a future date/time." },
  on_the_way:          { label: "On The Way",           tone: "current",   description: "You're en route to the customer." },
  reached_site:        { label: "Arrived",              tone: "current",   description: "You've arrived at the job site." },
  inspection_started:  { label: "Inspection",           tone: "current",   description: "Inspection in progress." },
  inspection_done:     { label: "Inspection Complete",  tone: "current",   description: "Inspection complete." },
  quote_required:      { label: "Estimate Pending",     tone: "blocked",   description: "An estimate must be created and approved before work can start." },
  service_started:     { label: "Work In Progress",     tone: "current",   description: "Work has started." },
  work_done:           { label: "Work Done",            tone: "current",   description: "Work is done -- awaiting completion submission." },
  completed:           { label: "Completed",            tone: "completed", description: "Job completed." },
  customer_not_available: { label: "Customer Unavailable", tone: "blocked", description: "Customer was not available." },
  cancelled:           { label: "Cancelled",            tone: "cancelled", description: "This job was cancelled." },
  failed:              { label: "Failed",               tone: "cancelled", description: "This job could not be completed." },
  closed_estimate_declined: { label: "Estimate Declined", tone: "cancelled", description: "The customer declined the estimate. This job is closed." },
};

const SAFE_FALLBACK: WorkflowStatusEntry = {
  label: "Unknown Status",
  tone: "neutral",
  description: "This status isn't recognized by the app yet. No action is available -- contact support if this persists.",
};

/**
 * Never guesses a transition for an unrecognized status: returns the safe
 * fallback and lets the caller log telemetry (services/telemetry) rather
 * than throwing or rendering broken UI.
 */
export function resolveWorkflowStatus(status: string | null | undefined): WorkflowStatusEntry {
  if (!status) return SAFE_FALLBACK;
  return WORKFLOW_STATUS_MAP[status] ?? SAFE_FALLBACK;
}

export function workflowToneColor(theme: Theme, tone: WorkflowTone): string {
  switch (tone) {
    case "completed": return theme.colors.workflowCompleted;
    case "current":    return theme.colors.workflowCurrent;
    case "upcoming":   return theme.colors.workflowUpcoming;
    case "blocked":    return theme.colors.workflowBlocked;
    case "cancelled":  return theme.colors.workflowCancelled;
    default:           return theme.colors.textTertiary;
  }
}
