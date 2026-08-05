/**
 * Shared presentation resolver for the Privacy Request receipt/detail surface.
 *
 * One receipt maps any customer-facing request type (export, erasure/deletion,
 * correction, consent withdrawal, ...) to its display copy, instead of
 * scattering per-type string checks through JSX. Adding a new request type
 * means adding a case here, not a new screen.
 */
import { ComplianceRequest } from "./api/customer-privacy";

export interface PrivacyReceiptPresentation {
  headline: string;
  message: string;
  nextSteps: string[];
  /** Only true for request types where account access is proven to remain
   *  unchanged by submission (currently: right_to_erasure). Never inferred
   *  from a hardcoded blanket assumption. */
  showAccountActiveNote: boolean;
}

export function resolvePrivacyReceiptPresentation(
  requestType: string,
): PrivacyReceiptPresentation {
  const isErasure = requestType === "right_to_erasure";

  const nextSteps = ["We'll review your request", "Track updates in Privacy & data"];
  if (isErasure) nextSteps.push("Your account remains active during review");

  return {
    headline: "Your request is in",
    message: isErasure
      ? "We've received your account deletion request."
      : "We've received your request.",
    nextSteps,
    showAccountActiveNote: isErasure,
  };
}

/** Public reference shown to the customer. Never falls back to the raw
 *  UUID `id` — if the backend hasn't supplied a human reference, the row
 *  is hidden entirely by the caller instead of leaking the internal id. */
export function publicReference(req: Pick<ComplianceRequest, "request_number">): string | null {
  return req.request_number || null;
}

export function requestTypeLabel(requestType: string, requestTypes: { value: string; label: string }[]): string {
  return requestTypes.find((t) => t.value === requestType)?.label ?? requestType;
}
