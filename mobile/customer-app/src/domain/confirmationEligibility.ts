import { ServicePriceState } from "./servicePricing";

export type ConfirmationBlockReason =
  | "draft_incomplete"
  | "address_required"
  | "unserviceable"
  | "no_provider"
  | "pricing_unavailable"
  | "stale_review"
  | "request_in_progress"
  | "unknown";

export type ConfirmationEligibility =
  | { allowed: true }
  | { allowed: false; reason: ConfirmationBlockReason };

export interface ConfirmationEligibilityInput {
  questionsComplete: boolean;
  hasAddress: boolean;
  serviceable: boolean;
  hasSelectedProvider: boolean;
  priceState: ServicePriceState;
  /** Low/Mid/High tier selection is out of scope this phase (mission
   * statement) -- a bargain-available draft can never reach `allowed:
   * true` here regardless of price state, until that phase exists. */
  bargainAvailable: boolean;
  /** Backend's own `booking_summary.ready_for_confirmation` -- the single
   * authoritative signal this resolver ultimately defers to once every
   * client-visible precondition above has already passed. */
  readyForConfirmation: boolean;
  requestInFlight: boolean;
}

/**
 * Single domain-level resolver (spec section 7: "Create one domain-level
 * eligibility resolver. Do not scatter button conditions across
 * components."). Every reason is checked in a fixed, most-actionable-first
 * order so the UI never shows a vaguer reason when a more specific one
 * also applies.
 */
export function resolveConfirmationEligibility(input: ConfirmationEligibilityInput): ConfirmationEligibility {
  if (input.requestInFlight) return { allowed: false, reason: "request_in_progress" };
  if (!input.questionsComplete) return { allowed: false, reason: "draft_incomplete" };
  if (!input.hasAddress) return { allowed: false, reason: "address_required" };
  if (!input.serviceable) return { allowed: false, reason: "unserviceable" };
  if (!input.hasSelectedProvider) return { allowed: false, reason: "no_provider" };
  if (input.bargainAvailable) return { allowed: false, reason: "pricing_unavailable" };
  if (input.priceState.kind === "unavailable") return { allowed: false, reason: "pricing_unavailable" };
  if (!input.readyForConfirmation) return { allowed: false, reason: "stale_review" };
  return { allowed: true };
}

export const CONFIRMATION_BLOCK_COPY: Record<ConfirmationBlockReason, string> = {
  draft_incomplete: "Finish answering the assistant's questions first.",
  address_required: "Add a service address to continue.",
  unserviceable: "This service isn't available at this address yet.",
  no_provider: "No eligible professional is available right now.",
  pricing_unavailable: "Pricing for this request isn't ready yet.",
  stale_review: "Your review needs to be refreshed before confirming.",
  request_in_progress: "Please wait for the current request to finish.",
  unknown: "This request can't be confirmed right now.",
};
