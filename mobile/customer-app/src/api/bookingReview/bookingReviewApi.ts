import { authenticatedRequest } from "../client/authenticatedClient";
import { parseApiSuccess } from "../client/responseParser";
import {
  serviceabilityCheckResponseSchema, priceEstimateResponseSchema, matchAndPriceResponseSchema,
  confirmPriceChoiceResponseSchema, buildBookingSummaryResponseSchema,
  availableSlotsResponseSchema, selectSlotResponseSchema,
} from "../contracts/bookingReview";
import { bookingDraftResponseSchema } from "../contracts/bookingDraft";

const base = (draftId: string) => `/v1/customer/home-services/booking-drafts/${draftId}`;

export async function getDraft(draftId: string) {
  const res = await authenticatedRequest({ method: "GET", path: base(draftId) });
  return parseApiSuccess(res.json, bookingDraftResponseSchema);
}

/** Real bug risk documented here rather than fixed silently: the backend
 * (`update_draft_fields`) sets `draft.zipcode`/`draft.city` FROM the
 * address record whenever `address_id` is sent -- it does not itself
 * reject a zip-mismatched address. The zipcode this draft was matched
 * against must never change (the assigned provider was matched against
 * it), so the caller MUST only ever pass an address whose own zipcode
 * already equals the entry zipcode -- enforced in
 * AddressTurn/useBookingChatController, not here. */
export async function setDraftAddress(draftId: string, addressId: string) {
  const res = await authenticatedRequest({
    method: "PUT", path: base(draftId), body: { address_id: addressId },
  });
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

/** Every real, capacity-checked slot the assigned provider can offer --
 * lets Review show a picker instead of only the single slot
 * `build_booking_summary` already promised. Empty list (never an error)
 * when no provider is assigned yet or the provider has no capacity in
 * the search horizon. */
export async function getAvailableSlots(draftId: string) {
  const res = await authenticatedRequest({ method: "GET", path: `${base(draftId)}/available-slots` });
  return parseApiSuccess(res.json, availableSlotsResponseSchema);
}

/** Re-validated against live capacity server-side, not trusted from the
 * list response the customer may have been looking at for a while -- a
 * slot that lost capacity in the meantime comes back as a 422, not a
 * silent overbook. */
export async function selectSlot(draftId: string, dateIso: string, timeWindow: string) {
  const res = await authenticatedRequest({
    method: "POST", path: `${base(draftId)}/select-slot`, body: { date: dateIso, time_window: timeWindow },
  });
  return parseApiSuccess(res.json, selectSlotResponseSchema);
}
