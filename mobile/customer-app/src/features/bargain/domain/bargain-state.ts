import type { ValidatedPriceOptions } from "../../pricing/domain/pricing-schema";
import type { ValidatedMatchedProvider } from "../../provider-matching/domain/provider-match-schema";
import type { ValidatedBookingSummary, PriceTier } from "./bargain-schema";

/**
 * Centralized bargain state (CUSTOMER-L5-10 §12) — deliberately small.
 * No `RATE_LIMITED`/`ATTEMPTS_EXHAUSTED`/`COOLDOWN`/`COUNTEROFFER_RECEIVED`
 * states exist in this union: none of those backend capabilities exist in
 * the real system (see CUSTOMER-L5-10-contract-matrix.md) — modeling
 * states for capabilities that cannot occur would be indistinguishable
 * from fabricating them, the same principle CUSTOMER-L5-09's state model
 * already applied to `CONFLICT`/`EXPIRED`.
 */
export type BargainState =
  | { kind: "preflight_failed"; reasonKey: string }
  | { kind: "loading_estimate" }
  | { kind: "estimate_unavailable" }
  | { kind: "choosing"; options: ValidatedPriceOptions; provider: ValidatedMatchedProvider }
  | { kind: "confirming"; options: ValidatedPriceOptions; provider: ValidatedMatchedProvider; tier: PriceTier }
  | { kind: "confirmed"; summary: ValidatedBookingSummary }
  | { kind: "confirm_failed"; options: ValidatedPriceOptions; provider: ValidatedMatchedProvider };

export interface EstimateMutationSnapshot {
  isIdle: boolean;
  isPending: boolean;
  isError: boolean;
  data?: { selected_provider_price_options: ValidatedPriceOptions; selected_provider: ValidatedMatchedProvider };
}

export interface ConfirmMutationSnapshot {
  isPending: boolean;
  isError: boolean;
  isSuccess: boolean;
  data?: { booking_summary: ValidatedBookingSummary };
}

/** Pure state derivation — extracted so it is directly unit-testable without mounting hooks (mirrors CUSTOMER-L5-09's `derivePricingState`). */
export function deriveBargainState(params: {
  preflightReasonKey: string | null;
  estimate: EstimateMutationSnapshot;
  confirm: ConfirmMutationSnapshot;
  selectedTier: PriceTier | null;
}): BargainState {
  const { preflightReasonKey, estimate, confirm, selectedTier } = params;

  if (preflightReasonKey) return { kind: "preflight_failed", reasonKey: preflightReasonKey };
  if (estimate.isPending || estimate.isIdle) return { kind: "loading_estimate" };
  if (estimate.isError || !estimate.data) return { kind: "estimate_unavailable" };

  const { selected_provider_price_options: options, selected_provider: provider } = estimate.data;

  if (confirm.isSuccess && confirm.data) return { kind: "confirmed", summary: confirm.data.booking_summary };
  if (confirm.isPending && selectedTier) return { kind: "confirming", options, provider, tier: selectedTier };
  if (confirm.isError) return { kind: "confirm_failed", options, provider };
  return { kind: "choosing", options, provider };
}
