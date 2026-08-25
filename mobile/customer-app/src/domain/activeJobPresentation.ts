import { parseServerDate, toDisplayDate } from "./dates";

/**
 * ACTIVE-BOOKING-DETAILS phase -- customer-facing presentation for the
 * three stages this phase owns (Assigned, Scheduled, On the way). Driven
 * entirely by the backend's own `map_job_status` `stage` key (never a
 * raw ServiceJob.status string in JSX). Any stage this phase does not own
 * (inspection, estimate_approval, in_progress, payment, completed,
 * cancelled, exception, and the unassigned "new" stage) is deliberately
 * NOT handled here -- the screen falls back to the existing booking-level
 * presentation for those, rather than fabricating a detailed card for a
 * later journey phase this task must not build.
 */
export type ActiveJobStage = "assignment" | "scheduled" | "on_the_way";

export interface ActiveJobPresentation {
  title: string;
  explanation: string;
  tone: "info" | "warning";
  nextExpected: string;
  showTechnicianCard: boolean;
  showSchedule: boolean;
}

const PRESENTATION: Record<ActiveJobStage, ActiveJobPresentation> = {
  assignment: {
    title: "Assigned",
    explanation: "A service professional has been assigned to your booking.",
    tone: "info",
    nextExpected: "We'll confirm your visit schedule shortly.",
    showTechnicianCard: true,
    showSchedule: false,
  },
  scheduled: {
    title: "Scheduled",
    explanation: "Your visit has been scheduled.",
    tone: "info",
    nextExpected: "Your professional will be on the way at the scheduled time.",
    showTechnicianCard: true,
    showSchedule: true,
  },
  on_the_way: {
    title: "On the way",
    explanation: "Your service professional is heading to your address.",
    tone: "warning",
    nextExpected: "We'll update this page when they arrive.",
    showTechnicianCard: true,
    showSchedule: true,
  },
};

const PROVIDER_ACCEPTED_PRESENTATION: ActiveJobPresentation = {
  title: "Provider accepted",
  explanation: "A verified provider has accepted your booking.",
  tone: "info",
  nextExpected: "A technician will be assigned for your visit next.",
  showTechnicianCard: false,
  showSchedule: false,
};

const KNOWN_ACTIVE_STAGES: ReadonlySet<string> = new Set(["assignment", "scheduled", "on_the_way"]);

/** Fails safe to `null` for every stage this phase does not own -- the
 * screen must then use its existing, already-safe booking-level fallback. */
export function resolveActiveJobStage(jobStage: string | null | undefined): ActiveJobStage | null {
  if (jobStage && KNOWN_ACTIVE_STAGES.has(jobStage)) {
    return jobStage as ActiveJobStage;
  }
  return null;
}

export function resolveActiveJobPresentation(stage: ActiveJobStage, rawStatus?: string | null): ActiveJobPresentation {
  if (stage === "assignment" && rawStatus === "accepted") {
    return PROVIDER_ACCEPTED_PRESENTATION;
  }
  return PRESENTATION[stage];
}

/** 5-step timeline (spec's approved visual: Booked, Assigned, Scheduled,
 * On the way, Arrived). "Arrived" is never marked complete or active by
 * this phase -- reaching it is a later phase's proof to make. */
export const JOB_PROGRESS_STEPS: ReadonlyArray<{ key: string; label: string; description: string }> = [
  { key: "booked", label: "Booked", description: "Your request has been received." },
  { key: "assignment", label: "Assigned", description: "A professional has been assigned." },
  { key: "scheduled", label: "Scheduled", description: "Your visit has been scheduled." },
  { key: "on_the_way", label: "On the way", description: "Your professional is on the way." },
  { key: "arrived", label: "Arrived", description: "We'll update when they arrive." },
];

export type JobProgressStepState = "complete" | "active" | "pending";

/** Pure function -- never infers a later step from elapsed time. Steps
 * strictly before the current active stage are complete; the current
 * stage is active; everything after (including "arrived", which this
 * phase never reaches) is pending. */
export function resolveJobProgressStepState(stepKey: string, activeStage: ActiveJobStage | "arrived"): JobProgressStepState {
  const order = ["booked", "assignment", "scheduled", "on_the_way", "arrived"];
  const currentIndex = order.indexOf(activeStage);
  const stepIndex = order.indexOf(stepKey);
  if (stepIndex < currentIndex) return "complete";
  if (stepIndex === currentIndex) return "active";
  return "pending";
}

/** Real, verified schedule text only -- never converts a date/window into
 * an ETA or a relative "today"/"in X" claim. Returns `null` (never a
 * placeholder string) when the backend hasn't set a confirmed schedule
 * yet, so the caller can omit the row entirely. */
export function formatScheduleWindow(scheduledDate: string | null, scheduledTimeWindow: string | null): string | null {
  if (!scheduledDate) return null;
  const display = toDisplayDate(parseServerDate(scheduledDate, "scheduled_date"))
    .toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" });
  return scheduledTimeWindow ? `${display} · ${formatTimeWindow(scheduledTimeWindow)}` : display;
}

function formatTimeWindow(value: string): string {
  const match = /^(\d{2}):(\d{2})-(\d{2}):(\d{2})$/.exec(value.trim());
  if (!match) return value;
  const [, startHour, startMinute, endHour, endMinute] = match;
  const label = (hour: string, minute: string) => {
    const numericHour = Number(hour);
    const period = numericHour >= 12 ? "PM" : "AM";
    const clockHour = numericHour % 12 || 12;
    return `${clockHour}:${minute} ${period}`;
  };
  return `${label(startHour, startMinute)}–${label(endHour, endMinute)}`;
}
