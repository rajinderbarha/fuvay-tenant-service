import type { ValidatedBookingSummary } from "./review-schema";
import type { ValidatedConfirmBookingResult } from "./booking-schema";
import type { ApiErrorCategory } from "../../../api/api-errors";

/**
 * Review-load state (CUSTOMER-L5-11 §9/§24). `not_ready` covers every real
 * precondition failure via the backend's own `ready_for_confirmation`
 * flag (CUSTOMER-L5-10's `/summary` contract) — this client does not
 * reimplement the individual checks `mark_ready_for_confirmation`
 * performs server-side; it only reflects the one boolean result honestly.
 */
export type ReviewState =
  | { kind: "preflight_failed"; reasonKey: string }
  | { kind: "loading" }
  | { kind: "unavailable" }
  | { kind: "not_ready"; summary: ValidatedBookingSummary }
  | { kind: "ready"; summary: ValidatedBookingSummary };

export interface ReviewMutationSnapshot {
  isIdle: boolean;
  isPending: boolean;
  isError: boolean;
  data?: { booking_summary: ValidatedBookingSummary };
}

export function deriveReviewState(params: { preflightReasonKey: string | null; review: ReviewMutationSnapshot }): ReviewState {
  const { preflightReasonKey, review } = params;
  if (preflightReasonKey) return { kind: "preflight_failed", reasonKey: preflightReasonKey };
  if (review.isPending || review.isIdle) return { kind: "loading" };
  if (review.isError || !review.data) return { kind: "unavailable" };
  const { booking_summary: summary } = review.data;
  return summary.ready_for_confirmation ? { kind: "ready", summary } : { kind: "not_ready", summary };
}

/**
 * Confirmation-submission state, tracked separately from `ReviewState` so
 * a failed/uncertain confirmation attempt never discards the already-loaded
 * review data (the customer can retry without a full reload).
 *
 * `uncertain` (not `failed`) is used for any error category where the
 * request may have actually committed server-side before the response was
 * lost (`timeout`/`network_error`/`server_error`/`unknown_error`) — per
 * CUSTOMER-L5-11 §30, the honest response to genuine uncertainty is a
 * calm "checking" state, never a premature "booking failed." `failed` is
 * reserved for error categories that are certain the request never
 * committed (`validation_error`/`not_found`/`forbidden`/`conflict` —
 * rejected before or during the transaction, not after).
 */
export type ConfirmState =
  { kind: "idle" } | { kind: "confirming" } | { kind: "uncertain" } | { kind: "confirmed"; result: ValidatedConfirmBookingResult } | { kind: "failed" };

const UNCERTAIN_CATEGORIES: readonly ApiErrorCategory[] = ["timeout", "network_error", "server_error", "unknown_error", "maintenance", "rate_limited"];

export function categorizeConfirmFailure(category: ApiErrorCategory): "uncertain" | "failed" {
  return UNCERTAIN_CATEGORIES.includes(category) ? "uncertain" : "failed";
}
