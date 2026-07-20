import { parsePriceEstimateResult, isSinglePointEstimate } from "../pricing-schema";

const validProvider = {
  tenant_id: "t-1",
  provider_name: "Acme Repairs",
  public_badges: ["Verified"],
  rating: 4.2,
  customer_visible_reason: "Best matched provider based on service coverage, availability, quality, and completion history.",
};

const validPriceOptions = {
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

describe("parsePriceEstimateResult", () => {
  it("accepts the real match-and-price response shape (range case)", () => {
    const parsed = parsePriceEstimateResult({
      selected_provider: validProvider,
      selected_provider_price_options: validPriceOptions,
      draft_status: "provider_matched",
    });
    expect(parsed?.selected_provider_price_options.low_price).toBe(550);
    expect(parsed?.selected_provider_price_options.mid_price).toBe(690);
    expect(parsed?.selected_provider_price_options.high_price).toBe(770);
  });

  it("strips area_market_comparison and admin fields present in a real response", () => {
    const parsed = parsePriceEstimateResult({
      selected_provider: validProvider,
      selected_provider_price_options: validPriceOptions,
      area_market_comparison: { area: "Pune 411001", competitor_provider_count: 3 },
      selected_provider_admin: { internal_score: 87.5 },
      draft_status: "provider_matched",
    });
    expect(parsed).not.toBeNull();
    expect(Object.keys(parsed as object).sort()).toEqual(["draft_status", "selected_provider", "selected_provider_price_options"]);
  });

  it("rejects a malformed payload without throwing", () => {
    expect(parsePriceEstimateResult(null)).toBeNull();
    expect(parsePriceEstimateResult({})).toBeNull();
    expect(parsePriceEstimateResult({ selected_provider: validProvider, draft_status: "x" })).toBeNull();
  });

  it("rejects price options missing a required field", () => {
    const { currency, ...withoutCurrency } = validPriceOptions;
    expect(
      parsePriceEstimateResult({
        selected_provider: validProvider,
        selected_provider_price_options: withoutCurrency,
        draft_status: "provider_matched",
      })
    ).toBeNull();
  });
});

describe("isSinglePointEstimate", () => {
  it("returns false for a real distinct low/high range", () => {
    expect(isSinglePointEstimate(validPriceOptions)).toBe(false);
  });

  it("returns true for the real degenerate case where low equals high", () => {
    expect(isSinglePointEstimate({ ...validPriceOptions, low_price: 600, mid_price: 600, high_price: 600 })).toBe(true);
  });
});
