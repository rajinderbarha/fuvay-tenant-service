import { parseConfirmPriceChoiceResult } from "../bargain-schema";

const validSummary = {
  selected_tenant_id: "t-1",
  selected_provider_name: "Acme Repairs",
  selected_zipcode: "411001",
  selected_price_tier: "mid",
  customer_offer: 690,
  allowed_offer_min: 550,
  allowed_offer_max: 770,
  platform_fee_amount: 70,
  payment_mode: "customer_pays_provider_directly",
};

describe("parseConfirmPriceChoiceResult", () => {
  it("accepts the real confirm-price-choice response shape", () => {
    const parsed = parseConfirmPriceChoiceResult({ booking_summary: validSummary, draft_status: "provider_matched" });
    expect(parsed?.booking_summary.selected_price_tier).toBe("mid");
    expect(parsed?.booking_summary.customer_offer).toBe(690);
  });

  it("accepts all three real tier values", () => {
    for (const tier of ["low", "mid", "high"] as const) {
      const parsed = parseConfirmPriceChoiceResult({
        booking_summary: { ...validSummary, selected_price_tier: tier },
        draft_status: "provider_matched",
      });
      expect(parsed?.booking_summary.selected_price_tier).toBe(tier);
    }
  });

  it("rejects an unrecognized tier value (fails closed rather than trusting an unexpected value)", () => {
    expect(
      parseConfirmPriceChoiceResult({
        booking_summary: { ...validSummary, selected_price_tier: "premium" },
        draft_status: "provider_matched",
      })
    ).toBeNull();
  });

  it("accepts a null selected_tenant_id/selected_provider_name/selected_zipcode (real, possible shape)", () => {
    const parsed = parseConfirmPriceChoiceResult({
      booking_summary: { ...validSummary, selected_tenant_id: null, selected_provider_name: null, selected_zipcode: null },
      draft_status: "provider_matched",
    });
    expect(parsed?.booking_summary.selected_provider_name).toBeNull();
  });

  it("rejects a malformed payload without throwing", () => {
    expect(parseConfirmPriceChoiceResult(null)).toBeNull();
    expect(parseConfirmPriceChoiceResult({})).toBeNull();
    expect(parseConfirmPriceChoiceResult({ booking_summary: validSummary })).toBeNull();
  });
});
