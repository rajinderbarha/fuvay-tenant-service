import type { ValidatedPriceOptions } from "./pricing-schema";
import type { ValidatedMatchedProvider } from "../../provider-matching/domain/provider-match-schema";

/**
 * Centralized pricing state (CUSTOMER-L5-09 §38) — a pure, testable
 * derivation instead of scattered booleans. `CONFLICT`/`EXPIRED` are
 * deliberately absent from this union: no draft-version-conflict response
 * shape and no price-specific expiry exist anywhere in the real backend
 * (see CUSTOMER-L5-09-contract-matrix.md) — modeling states for
 * capabilities that cannot occur would be indistinguishable from
 * fabricating them. `preflight_failed` covers the one real "cannot even
 * try" case (including the real, generic draft-level expiry).
 */
export type PricingState =
  | { kind: "idle" }
  | { kind: "preflight_failed"; reasonKey: string }
  | { kind: "calculating"; isRevalidating: boolean }
  | { kind: "ready"; options: ValidatedPriceOptions; provider: ValidatedMatchedProvider; revised: boolean }
  | { kind: "unavailable" }
  | { kind: "failed" };

export interface PricingMutationSnapshot {
  isIdle: boolean;
  isPending: boolean;
  isSuccess: boolean;
  isError: boolean;
  data?: { selected_provider_price_options: ValidatedPriceOptions; selected_provider: ValidatedMatchedProvider };
}

export function derivePricingState(params: {
  preflightReasonKey: string | null;
  mutation: PricingMutationSnapshot;
  hasCalculatedBefore: boolean;
  previousOptions: ValidatedPriceOptions | null;
}): PricingState {
  const { preflightReasonKey, mutation, hasCalculatedBefore, previousOptions } = params;

  if (preflightReasonKey) return { kind: "preflight_failed", reasonKey: preflightReasonKey };
  if (mutation.isPending) return { kind: "calculating", isRevalidating: hasCalculatedBefore };
  if (mutation.isError) return hasCalculatedBefore ? { kind: "unavailable" } : { kind: "failed" };
  if (mutation.isSuccess && mutation.data) {
    const options = mutation.data.selected_provider_price_options;
    const revised = previousOptions != null && !priceOptionsEqual(previousOptions, options);
    return { kind: "ready", options, provider: mutation.data.selected_provider, revised };
  }
  return { kind: "idle" };
}

export function priceOptionsEqual(a: ValidatedPriceOptions, b: ValidatedPriceOptions): boolean {
  return a.currency === b.currency && a.low_price === b.low_price && a.mid_price === b.mid_price && a.high_price === b.high_price;
}
