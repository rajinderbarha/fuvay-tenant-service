import { PrivacyRequest } from "./privacyData";

export type PrivacyRequestTone = "success" | "warning" | "danger" | "info" | "neutral";

export interface PrivacyRequestPresentation {
  typeLabel: string;
  title: string;
  explanation: string;
  tone: PrivacyRequestTone;
  isTerminal: boolean;
  isRefreshMeaningful: boolean;
  canWithdraw: boolean;
  canDownloadExport: boolean;
}

const TYPE_LABEL: Record<string, string> = {
  right_to_erasure: "Account deletion",
  data_export: "Data export",
  consent_withdrawal: "Consent withdrawal",
  consent_update: "Consent update",
  data_correction: "Data correction",
  processing_objection: "Processing objection",
  grievance: "Grievance",
};

/** One entry per status confirmed real in
 * `app/engines/compliance/customer_router.py`'s `STATUS_LABELS` /
 * `enterprise_service.VALID_STATUSES`. Keyed by the raw backend `status`
 * (not `statusLabel`) so an unrecognized value always falls through to the
 * safe "Status unavailable" branch below rather than silently matching
 * nothing (spec section 4). */
const STATUS_PRESENTATION: Record<string, {
  title: string; explanation: string; tone: PrivacyRequestTone;
  isTerminal: boolean; isRefreshMeaningful: boolean;
}> = {
  submitted: {
    title: "Submitted",
    explanation: "Your request has been received and is waiting to be reviewed.",
    tone: "info", isTerminal: false, isRefreshMeaningful: true,
  },
  identity_verification_pending: {
    title: "Additional verification required",
    explanation: "Your account remains active while we confirm a few details.",
    tone: "warning", isTerminal: false, isRefreshMeaningful: true,
  },
  under_review: {
    title: "Under review",
    explanation: "Your account remains active while your request is reviewed.",
    tone: "warning", isTerminal: false, isRefreshMeaningful: true,
  },
  approved: {
    title: "Approved",
    explanation: "Your request has been approved and will be processed shortly.",
    tone: "success", isTerminal: false, isRefreshMeaningful: true,
  },
  partially_approved: {
    title: "Partially approved",
    explanation: "Part of your request has been approved. Some items may follow platform retention policy.",
    tone: "success", isTerminal: false, isRefreshMeaningful: true,
  },
  processing: {
    title: "Processing",
    explanation: "Your request is being carried out.",
    tone: "info", isTerminal: false, isRefreshMeaningful: true,
  },
  completed: {
    title: "Completed",
    explanation: "This request has been completed.",
    tone: "success", isTerminal: true, isRefreshMeaningful: false,
  },
  rejected: {
    title: "Rejected",
    explanation: "This request was not approved.",
    tone: "danger", isTerminal: true, isRefreshMeaningful: false,
  },
  failed: {
    title: "Needs attention",
    explanation: "Something went wrong while processing this request. Our team has been notified.",
    tone: "danger", isTerminal: false, isRefreshMeaningful: true,
  },
  cancelled: {
    title: "Withdrawn",
    explanation: "You withdrew this request.",
    tone: "neutral", isTerminal: true, isRefreshMeaningful: false,
  },
  sla_breached: {
    title: "Delayed",
    explanation: "This request is taking longer than expected. Your account remains active.",
    tone: "warning", isTerminal: false, isRefreshMeaningful: true,
  },
};

const WITHDRAWABLE_STATUSES = new Set(["submitted", "identity_verification_pending"]);

/** Named per spec section 9 -- delegates to the same `STATUS_PRESENTATION`
 * table `resolvePrivacyRequestPresentation` uses, so Active/Completed
 * grouping on the Privacy Requests screen can never drift from the single
 * source of truth for per-status tone/explanation. An unrecognized status
 * is never terminal (stays visible under Active rather than silently
 * disappearing into a history bucket). */
export function isTerminalPrivacyStatus(status: string): boolean {
  return STATUS_PRESENTATION[status]?.isTerminal ?? false;
}

/** Named per spec section 7 -- the same closed type mapper
 * `resolvePrivacyRequestPresentation` uses internally, exposed standalone
 * for call sites (like the Privacy Requests list) that only have the raw
 * type string, not a full `PrivacyRequest`. */
export function resolvePrivacyRequestType(rawType: string): string {
  return TYPE_LABEL[rawType] ?? "Privacy request";
}

/** Named per spec section 8 -- same standalone-from-raw-status shape as
 * `resolvePrivacyRequestType` above. */
/** Deterministic, capability-aware "what happens next" copy for the
 * Privacy Request Submitted receipt (spec section 6). The download step
 * is included ONLY for `data_export` -- every other request type has no
 * export/download capability at all, so showing it would promise
 * something that can never happen. Never varies by elapsed time, never
 * shows an SLA/countdown/reviewer identity. `status` is accepted for
 * future extensibility (e.g. a terminal status suppressing "review"
 * language) but every currently-submittable status uses the same steps. */
export function resolvePrivacyReceiptNextSteps(params: {
  requestType: string; status: string;
}): string[] {
  const steps = ["We'll review your request", "Track updates in Privacy requests"];
  if (params.requestType === "data_export") {
    steps.push("Download securely if an export becomes available");
  }
  if (params.requestType === "right_to_erasure") {
    // Account Deletion Request Receipt phase: proven true across two
    // audited phases -- request creation never touches session/account
    // state (`create_my_request` only inserts a ComplianceRequest row;
    // actual anonymization is a separate, admin-triggered step). Never
    // shown for other request types, which have no comparable "your
    // account" concern.
    steps.push("Your account remains active during review");
  }
  return steps;
}

/** Receipt hero subtitle, keyed by real request type (spec section 4) --
 * moved out of JSX so every receipt variant's copy lives in one place.
 * Unknown/other types get the honest generic fallback, never a guess. */
export function resolvePrivacyReceiptSupportingMessage(requestType: string): string {
  if (requestType === "data_export") return "We've received your data export request.";
  if (requestType === "right_to_erasure") return "We've received your account deletion request.";
  return "We've received your privacy request.";
}

/** Account Deletion Request Receipt phase, spec section 7 -- rendered
 * ONLY for `right_to_erasure`, since that's the only request type whose
 * design calls for this specific reassurance. Only ever returned when
 * every one of the section's stated preconditions is proven true (all
 * confirmed by source audit): deletion is request-based, account stays
 * active, the session is never touched by request creation. Never
 * hardcoded as a blanket claim independent of request type. */
export function resolvePrivacyReceiptSessionMessage(requestType: string): { title: string; description: string } | null {
  if (requestType !== "right_to_erasure") return null;
  return {
    title: "You're still signed in",
    description: "Submitting this request does not immediately delete your account.",
  };
}

export function resolvePrivacyRequestStatus(rawStatus: string): {
  title: string; tone: PrivacyRequestTone; isTerminal: boolean;
} {
  const known = STATUS_PRESENTATION[rawStatus];
  if (!known) return { title: "Status unavailable", tone: "neutral", isTerminal: false };
  return { title: known.title, tone: known.tone, isTerminal: known.isTerminal };
}

/** Central, exhaustively tested status/type adapter (spec section 5). The
 * mobile app never independently decides whether a request is approved or
 * complete -- every field here is derived from the backend's own `status`,
 * never guessed or inferred from timing. */
export function resolvePrivacyRequestPresentation(request: PrivacyRequest): PrivacyRequestPresentation {
  const typeLabel = TYPE_LABEL[request.requestType] ?? "Privacy request";
  const known = STATUS_PRESENTATION[request.status];

  if (!known) {
    return {
      typeLabel,
      title: "Status unavailable",
      explanation: "We couldn't determine the current status of this request.",
      tone: "neutral",
      isTerminal: false,
      isRefreshMeaningful: true,
      canWithdraw: false,
      canDownloadExport: false,
    };
  }

  const canWithdraw = WITHDRAWABLE_STATUSES.has(request.status);
  const canDownloadExport =
    request.requestType === "data_export" &&
    !!request.export &&
    request.export.status === "ready" &&
    !request.export.isExpired;

  return {
    typeLabel,
    title: known.title,
    explanation: known.explanation,
    tone: known.tone,
    isTerminal: known.isTerminal,
    isRefreshMeaningful: known.isRefreshMeaningful,
    canWithdraw,
    canDownloadExport,
  };
}
