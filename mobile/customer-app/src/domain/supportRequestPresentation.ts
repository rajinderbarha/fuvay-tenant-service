import { SupportRequest, SupportRequestType } from "./supportRequests";

export type SupportRequestTone = "success" | "warning" | "danger" | "info" | "neutral";

export interface SupportRequestPresentation {
  typeLabel: string;
  statusLabel: string;
  tone: SupportRequestTone;
  isTerminal: boolean;
}

const TYPE_LABEL: Record<string, string> = {
  service_quality: "Service quality", technician_behavior: "Technician behavior",
  late_arrival: "Late arrival", no_show: "No-show",
  overcharging: "Overcharging", payment_issue: "Payment issue",
  refund_request: "Refund request", rework_request: "Rework request",
  wrong_information: "Wrong information", appointment_issue: "Appointment issue",
  agent_issue: "Agent issue", other: "Other",
  safety_concern: "Safety concern",
};

/** Unlike the compliance engine, `app/engines/complaints/customer_router.py`
 * returns the raw internal `status` string with no server-provided safe
 * label -- this mapping is the frontend's own, built from the real,
 * confirmed enum in `app/engines/complaints/constants.py`. An unrecognized
 * value falls back to a neutral "Status unavailable" rather than showing
 * the raw backend string (spec section 4/9's fail-safe requirement). */
const STATUS_PRESENTATION: Record<string, { label: string; tone: SupportRequestTone; isTerminal: boolean }> = {
  open: { label: "Open", tone: "info", isTerminal: false },
  awaiting_provider_response: { label: "Waiting on provider", tone: "warning", isTerminal: false },
  awaiting_customer_response: { label: "Waiting on you", tone: "warning", isTerminal: false },
  under_admin_review: { label: "Under review", tone: "warning", isTerminal: false },
  resolution_proposed: { label: "Resolution proposed", tone: "info", isTerminal: false },
  rework_approved: { label: "Rework approved", tone: "success", isTerminal: false },
  refund_requested: { label: "Refund requested", tone: "info", isTerminal: false },
  refund_approved: { label: "Refund approved", tone: "success", isTerminal: false },
  refund_recorded: { label: "Refund recorded", tone: "success", isTerminal: false },
  rejected: { label: "Rejected", tone: "danger", isTerminal: true },
  resolved: { label: "Resolved", tone: "success", isTerminal: false },
  closed: { label: "Closed", tone: "neutral", isTerminal: true },
  cancelled: { label: "Cancelled", tone: "neutral", isTerminal: true },
};

/** Only "open" transitions to "cancelled" in the backend's real state
 * machine (`app/engines/complaints/constants.py` `ALLOWED_TRANSITIONS`) --
 * every other status would hit `COMPLAINT_INVALID_STATUS_TRANSITION` on
 * cancel, so the action is hidden rather than shown-then-rejected. */
const CANCELLABLE_STATUSES = new Set(["open"]);

export function resolveSupportRequestPresentation(request: SupportRequest): SupportRequestPresentation {
  const typeLabel = TYPE_LABEL[request.complaintType] ?? "Support request";
  const known = STATUS_PRESENTATION[request.status];
  if (!known) {
    return { typeLabel, statusLabel: "Status unavailable", tone: "neutral", isTerminal: false };
  }
  return { typeLabel, statusLabel: known.label, tone: known.tone, isTerminal: known.isTerminal };
}

export function canCancelSupportRequest(status: string): boolean {
  return CANCELLABLE_STATUSES.has(status);
}

export type SupportRequestStage = "active" | "resolved" | "unknown";

/** `resolved`, `closed`, `rejected` and `cancelled` are the only statuses
 * that read as "done" to a customer -- everything else (including
 * mid-flow states like `resolution_proposed`/`refund_approved`) is still
 * something the customer is waiting on, so it stays in "Active" (spec
 * section 4's single centralized classifier). An unrecognized status maps
 * to "unknown" rather than silently joining either bucket. */
const RESOLVED_STAGE_STATUSES = new Set(["resolved", "closed", "rejected", "cancelled"]);

export function resolveSupportRequestStage(status: string): SupportRequestStage {
  if (!STATUS_PRESENTATION[status]) return "unknown";
  return RESOLVED_STAGE_STATUSES.has(status) ? "resolved" : "active";
}

/** Only these two statuses have a dedicated hero treatment on the details
 * screen (spec section 5) -- `rejected`/`cancelled` still render through
 * the normal status card, since the mockup's "Resolved" hero only applies
 * to a genuinely resolved or closed request, not a rejected/withdrawn one. */
export type ResolvedHeroKind = "resolved" | "closed" | null;

export function resolveHeroKind(status: string): ResolvedHeroKind {
  if (status === "resolved") return "resolved";
  if (status === "closed") return "closed";
  return null;
}

/** Truthful headline copy per real status -- never claims the underlying
 * issue was fixed (spec section 5: "resolved" only means the case was
 * closed out, not that anything was repaired). */
export function resolvedHeroHeadline(kind: ResolvedHeroKind): string {
  if (kind === "closed") return "This request has been closed";
  return "Your request has been resolved";
}

/** Composer stays for `resolved` (the backend's `add_customer_message`
 * only blocks on closed/cancelled/rejected -- confirmed via
 * `ComplaintService.add_customer_message`'s `FINAL_STATUSES` check) --
 * only a true `isTerminal` status is read-only. This mirrors
 * `isTerminal` above; kept as a named export so the screen's intent is
 * self-documenting rather than reusing a generically-named field. */
export function isConversationReadOnly(status: string): boolean {
  return STATUS_PRESENTATION[status]?.isTerminal ?? false;
}

export const SUPPORT_REQUEST_TYPES: SupportRequestType[] = [
  "service_quality", "technician_behavior", "late_arrival", "no_show",
  "overcharging", "payment_issue", "refund_request", "rework_request",
  "wrong_information", "appointment_issue", "agent_issue", "other",
];

export function supportRequestTypeLabel(type: string): string {
  return TYPE_LABEL[type] ?? type;
}
