import { authenticatedRequest } from "../client/authenticatedClient";
import { parseApiSuccess } from "../client/responseParser";
import {
  serviceabilityCheckResponseSchema, priceEstimateResponseSchema, matchAndPriceResponseSchema,
  confirmPriceChoiceResponseSchema, buildBookingSummaryResponseSchema,
} from "../contracts/bookingReview";
import { bookingDraftResponseSchema } from "../contracts/bookingDraft";

const base = (draftId: string) => `/v1/customer/home-services/booking-drafts/${draftId}`;

export async function getDraft(draftId: string) {
  const res = await authenticatedRequest({ method: "GET", path: base(draftId) });
  return parseApiSuccess(res.json, bookingDraftResponseSchema);
}

export async function checkServiceability(draftId: string) {
  const res = await authenticatedRequest({ method: "POST", path: `${base(draftId)}/serviceability-check` });
  return parseApiSuccess(res.json, serviceabilityCheckResponseSchema);
}

/** Resolves `requires_inspection_estimate`/`visit_fee` -- must be called
 * BEFORE match-and-price so both merge onto the same draft.price_snapshot
 * (confirmed in source: match-and-price spreads the existing snapshot
 * rather than replacing it). */
/** Returns the `{ price_snapshot, draft_status }` ENVELOPE the backend
 * actually sends -- see priceEstimateResponseSchema for the bug this
 * fixed (the snapshot was previously parsed one level too high, so every
 * price field silently read as undefined). */
export async function resolvePriceEstimate(draftId: string) {
  const res = await authenticatedRequest({ method: "POST", path: `${base(draftId)}/price-estimate` });
  return parseApiSuccess(res.json, priceEstimateResponseSchema);
}

/** Backend selects the single eligible provider server-side -- the app
 * never sends a body and never receives a list to choose from. */
export async function matchAndPrice(draftId: string) {
  const res = await authenticatedRequest({ method: "POST", path: `${base(draftId)}/match-and-price` });
  return parseApiSuccess(res.json, matchAndPriceResponseSchema);
}

/** `tier` must be 'standard' when `bargain_available` is false (the only
 * path this phase drives automatically -- see useBookingReviewController).
 * Low/Mid/High tier selection UI is out of scope this phase. */
export async function confirmPriceChoice(draftId: string, tier: "standard" | "low" | "mid" | "high") {
  const res = await authenticatedRequest({
    method: "POST", path: `${base(draftId)}/confirm-price-choice`, body: { price_tier: tier },
  });
  return parseApiSuccess(res.json, confirmPriceChoiceResponseSchema);
}

/**
 * There is deliberately no separate "mark ready" call from the app --
 * `POST /{draft_id}/confirm` (see bookingConfirmationApi.ts) calls
 * `mark_ready_for_confirmation` and `finalize()` together server-side in
 * one request (confirmed in `customer_router.confirm_draft`). Calling it
 * here first would only create a race window between two round-trips.
 */
export async function buildBookingSummary(draftId: string) {
  const res = await authenticatedRequest({ method: "POST", path: `${base(draftId)}/summary` });
  return parseApiSuccess(res.json, buildBookingSummaryResponseSchema);
}
