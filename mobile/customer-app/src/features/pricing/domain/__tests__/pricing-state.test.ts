import { derivePricingState, priceOptionsEqual, type PricingMutationSnapshot } from "../pricing-state";
import type { ValidatedPriceOptions } from "../pricing-schema";

const provider = {
  tenant_id: "t-1",
  provider_name: "Acme Repairs",
  public_badges: ["Verified"],
  rating: 4.2,
  customer_visible_reason: "reason",
};

const options: ValidatedPriceOptions = {
  currency: "INR",
  low_price: 550,
  mid_price: 690,
  high_price: 770,
  allowed_offer_min: 550,
  allowed_offer_max: 770,
  platform_fee_percent: 10,
  platform_fee_amount: 70,
  payment_mode: "customer_pays_provider_directly",
};

const idleMutation: PricingMutationSnapshot = { isIdle: true, isPending: false, isSuccess: false, isError: false };
const pendingMutation: PricingMutationSnapshot = { isIdle: false, isPending: true, isSuccess: false, isError: false };
const errorMutation: PricingMutationSnapshot = { isIdle: false, isPending: false, isSuccess: false, isError: true };
const successMutation: PricingMutationSnapshot = {
  isIdle: false,
  isPending: false,
  isSuccess: true,
  isError: false,
  data: { selected_provider_price_options: options, selected_provider: provider },
};

describe("derivePricingState", () => {
  it("returns preflight_failed when preconditions are unmet, before ever considering the mutation", () => {
    const state = derivePricingState({
      preflightReasonKey: "pricing.preflight.providerNotMatched",
      mutation: idleMutation,
      hasCalculatedBefore: false,
      previousOptions: null,
    });
    expect(state).toEqual({ kind: "preflight_failed", reasonKey: "pricing.preflight.providerNotMatched" });
  });

  it("returns idle when preflight passes but nothing has been triggered yet", () => {
    const state = derivePricingState({ preflightReasonKey: null, mutation: idleMutation, hasCalculatedBefore: false, previousOptions: null });
    expect(state).toEqual({ kind: "idle" });
  });

  it("returns calculating (not revalidating) for the first-ever calculation", () => {
    const state = derivePricingState({ preflightReasonKey: null, mutation: pendingMutation, hasCalculatedBefore: false, previousOptions: null });
    expect(state).toEqual({ kind: "calculating", isRevalidating: false });
  });

  it("returns calculating (revalidating) when a manual refresh re-runs after a prior success", () => {
    const state = derivePricingState({ preflightReasonKey: null, mutation: pendingMutation, hasCalculatedBefore: true, previousOptions: options });
    expect(state).toEqual({ kind: "calculating", isRevalidating: true });
  });

  it("returns failed on the first-ever error", () => {
    const state = derivePricingState({ preflightReasonKey: null, mutation: errorMutation, hasCalculatedBefore: false, previousOptions: null });
    expect(state).toEqual({ kind: "failed" });
  });

  it("returns unavailable (not failed) when a revalidation attempt errors after a prior success", () => {
    const state = derivePricingState({ preflightReasonKey: null, mutation: errorMutation, hasCalculatedBefore: true, previousOptions: options });
    expect(state).toEqual({ kind: "unavailable" });
  });

  it("returns ready with revised: false on the first successful calculation", () => {
    const state = derivePricingState({ preflightReasonKey: null, mutation: successMutation, hasCalculatedBefore: false, previousOptions: null });
    expect(state).toEqual({ kind: "ready", options, provider, revised: false });
  });

  it("returns ready with revised: true when a revalidation returns different numbers", () => {
    const changed: ValidatedPriceOptions = { ...options, low_price: 600, mid_price: 700, high_price: 800 };
    const mutation: PricingMutationSnapshot = { ...successMutation, data: { selected_provider_price_options: changed, selected_provider: provider } };
    const state = derivePricingState({ preflightReasonKey: null, mutation, hasCalculatedBefore: true, previousOptions: options });
    expect(state).toEqual({ kind: "ready", options: changed, provider, revised: true });
  });

  it("returns ready with revised: false when a revalidation returns the exact same numbers", () => {
    const state = derivePricingState({ preflightReasonKey: null, mutation: successMutation, hasCalculatedBefore: true, previousOptions: { ...options } });
    expect(state.kind).toBe("ready");
    expect((state as { revised: boolean }).revised).toBe(false);
  });
});

describe("priceOptionsEqual", () => {
  it("is true for identical values in separate objects", () => {
    expect(priceOptionsEqual(options, { ...options })).toBe(true);
  });

  it("is false when any of the three real amounts differ", () => {
    expect(priceOptionsEqual(options, { ...options, mid_price: 691 })).toBe(false);
  });

  it("is false when currency differs", () => {
    expect(priceOptionsEqual(options, { ...options, currency: "USD" })).toBe(false);
  });
});
