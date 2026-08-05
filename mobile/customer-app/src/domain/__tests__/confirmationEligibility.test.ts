import { resolveConfirmationEligibility, ConfirmationEligibilityInput } from "../confirmationEligibility";
import { ServicePriceState } from "../servicePricing";

const VALID_PRICE: ServicePriceState = { kind: "valid", amount: { minorUnits: 49900, currency: "INR" } };

function baseInput(overrides: Partial<ConfirmationEligibilityInput> = {}): ConfirmationEligibilityInput {
  return {
    questionsComplete: true,
    hasAddress: true,
    serviceable: true,
    hasSelectedProvider: true,
    priceState: VALID_PRICE,
    bargainAvailable: false,
    readyForConfirmation: true,
    requestInFlight: false,
    ...overrides,
  };
}

describe("resolveConfirmationEligibility", () => {
  it("allows confirmation when every real precondition passes", () => {
    expect(resolveConfirmationEligibility(baseInput())).toEqual({ allowed: true });
  });

  it("blocks with request_in_progress ahead of every other reason", () => {
    expect(resolveConfirmationEligibility(baseInput({ requestInFlight: true, questionsComplete: false })))
      .toEqual({ allowed: false, reason: "request_in_progress" });
  });

  it("blocks with draft_incomplete when questions are not complete", () => {
    expect(resolveConfirmationEligibility(baseInput({ questionsComplete: false })))
      .toEqual({ allowed: false, reason: "draft_incomplete" });
  });

  it("blocks with unserviceable when the address is not serviceable", () => {
    expect(resolveConfirmationEligibility(baseInput({ serviceable: false })))
      .toEqual({ allowed: false, reason: "unserviceable" });
  });

  it("blocks with no_provider when no provider was matched", () => {
    expect(resolveConfirmationEligibility(baseInput({ hasSelectedProvider: false })))
      .toEqual({ allowed: false, reason: "no_provider" });
  });

  it("blocks with pricing_unavailable when bargaining is available (out of scope this phase)", () => {
    expect(resolveConfirmationEligibility(baseInput({ bargainAvailable: true })))
      .toEqual({ allowed: false, reason: "pricing_unavailable" });
  });

  it("blocks with pricing_unavailable when the price state is unavailable", () => {
    expect(resolveConfirmationEligibility(baseInput({ priceState: { kind: "unavailable" } })))
      .toEqual({ allowed: false, reason: "pricing_unavailable" });
  });

  it("blocks with stale_review when the backend's own ready_for_confirmation flag is false", () => {
    expect(resolveConfirmationEligibility(baseInput({ readyForConfirmation: false })))
      .toEqual({ allowed: false, reason: "stale_review" });
  });

  it("allows an inspection-based price state through (never requires a numeric price)", () => {
    expect(resolveConfirmationEligibility(baseInput({ priceState: { kind: "inspection_based" } })))
      .toEqual({ allowed: true });
  });
});
