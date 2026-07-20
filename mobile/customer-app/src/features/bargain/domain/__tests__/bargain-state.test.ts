import { deriveBargainState, type EstimateMutationSnapshot, type ConfirmMutationSnapshot } from "../bargain-state";

const provider = {
  tenant_id: "t-1",
  provider_name: "Acme Repairs",
  public_badges: ["Verified"],
  rating: 4.2,
  customer_visible_reason: "reason",
};

const options = {
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

const summary = {
  selected_tenant_id: "t-1",
  selected_provider_name: "Acme Repairs",
  selected_zipcode: "411001",
  selected_price_tier: "mid" as const,
  customer_offer: 690,
  allowed_offer_min: 550,
  allowed_offer_max: 770,
  platform_fee_amount: 70,
  payment_mode: "customer_pays_provider_directly",
};

const idleEstimate: EstimateMutationSnapshot = { isIdle: true, isPending: false, isError: false };
const pendingEstimate: EstimateMutationSnapshot = { isIdle: false, isPending: true, isError: false };
const errorEstimate: EstimateMutationSnapshot = { isIdle: false, isPending: false, isError: true };
const readyEstimate: EstimateMutationSnapshot = {
  isIdle: false,
  isPending: false,
  isError: false,
  data: { selected_provider_price_options: options, selected_provider: provider },
};

const idleConfirm: ConfirmMutationSnapshot = { isPending: false, isError: false, isSuccess: false };
const pendingConfirm: ConfirmMutationSnapshot = { isPending: true, isError: false, isSuccess: false };
const errorConfirm: ConfirmMutationSnapshot = { isPending: false, isError: true, isSuccess: false };
const successConfirm: ConfirmMutationSnapshot = { isPending: false, isError: false, isSuccess: true, data: { booking_summary: summary } };

describe("deriveBargainState", () => {
  it("returns preflight_failed before considering the estimate mutation at all", () => {
    const state = deriveBargainState({
      preflightReasonKey: "pricing.preflight.providerNotMatched",
      estimate: idleEstimate,
      confirm: idleConfirm,
      selectedTier: null,
    });
    expect(state).toEqual({ kind: "preflight_failed", reasonKey: "pricing.preflight.providerNotMatched" });
  });

  it("returns loading_estimate while idle or pending", () => {
    expect(deriveBargainState({ preflightReasonKey: null, estimate: idleEstimate, confirm: idleConfirm, selectedTier: null })).toEqual({
      kind: "loading_estimate",
    });
    expect(deriveBargainState({ preflightReasonKey: null, estimate: pendingEstimate, confirm: idleConfirm, selectedTier: null })).toEqual({
      kind: "loading_estimate",
    });
  });

  it("returns estimate_unavailable on estimate error", () => {
    expect(deriveBargainState({ preflightReasonKey: null, estimate: errorEstimate, confirm: idleConfirm, selectedTier: null })).toEqual({
      kind: "estimate_unavailable",
    });
  });

  it("returns choosing once the estimate is ready and no tier has been chosen yet", () => {
    const state = deriveBargainState({ preflightReasonKey: null, estimate: readyEstimate, confirm: idleConfirm, selectedTier: null });
    expect(state).toEqual({ kind: "choosing", options, provider });
  });

  it("returns confirming while a chosen tier's confirmation is in flight", () => {
    const state = deriveBargainState({ preflightReasonKey: null, estimate: readyEstimate, confirm: pendingConfirm, selectedTier: "high" });
    expect(state).toEqual({ kind: "confirming", options, provider, tier: "high" });
  });

  it("returns confirm_failed when confirmation errors", () => {
    const state = deriveBargainState({ preflightReasonKey: null, estimate: readyEstimate, confirm: errorConfirm, selectedTier: "high" });
    expect(state).toEqual({ kind: "confirm_failed", options, provider });
  });

  it("returns confirmed with the real backend-resolved summary on success", () => {
    const state = deriveBargainState({ preflightReasonKey: null, estimate: readyEstimate, confirm: successConfirm, selectedTier: "mid" });
    expect(state).toEqual({ kind: "confirmed", summary });
  });

  it("prioritizes a confirmed result over the estimate even if selectedTier is null (e.g. after changeSelection then re-render)", () => {
    const state = deriveBargainState({ preflightReasonKey: null, estimate: readyEstimate, confirm: successConfirm, selectedTier: null });
    expect(state.kind).toBe("confirmed");
  });
});
