import { parseProviderMatchResult } from "../provider-match-schema";

describe("parseProviderMatchResult", () => {
  it("accepts the real minimal match-and-price response shape", () => {
    const parsed = parseProviderMatchResult({
      selected_provider: {
        tenant_id: "t-1",
        provider_name: "Acme Repairs",
        public_badges: ["Verified", "Highly Rated"],
        rating: 4.7,
        customer_visible_reason: "Best matched provider based on service coverage, availability, quality, and completion history.",
      },
      draft_status: "provider_matched",
    });
    expect(parsed?.selected_provider.provider_name).toBe("Acme Repairs");
    expect(parsed?.selected_provider.public_badges).toEqual(["Verified", "Highly Rated"]);
    expect(parsed?.draft_status).toBe("provider_matched");
  });

  it("accepts a null rating (real, unrated provider)", () => {
    const parsed = parseProviderMatchResult({
      selected_provider: {
        tenant_id: "t-2",
        provider_name: "New Provider",
        public_badges: ["Verified"],
        rating: null,
        customer_visible_reason: "Best matched provider based on service coverage, availability, quality, and completion history.",
      },
      draft_status: "provider_matched",
    });
    expect(parsed?.selected_provider.rating).toBeNull();
  });

  it("accepts an empty badges array (a real, if rare, possible response)", () => {
    const parsed = parseProviderMatchResult({
      selected_provider: {
        tenant_id: "t-3",
        provider_name: "Barely Eligible Co",
        public_badges: [],
        rating: 2.1,
        customer_visible_reason: "Best matched provider based on service coverage, availability, quality, and completion history.",
      },
      draft_status: "provider_matched",
    });
    expect(parsed?.selected_provider.public_badges).toEqual([]);
  });

  it("strips pricing fields present in the real response instead of exposing them (CUSTOMER-L5-09 scope)", () => {
    const parsed = parseProviderMatchResult({
      selected_provider: {
        tenant_id: "t-4",
        provider_name: "Acme Repairs",
        public_badges: ["Verified"],
        rating: 4.2,
        customer_visible_reason: "Best matched provider based on service coverage, availability, quality, and completion history.",
      },
      selected_provider_price_options: { currency: "INR", low_price: 100, mid_price: 150, high_price: 200 },
      area_market_comparison: { area: "Pune 411001", competitor_provider_count: 3 },
      draft_status: "provider_matched",
    });
    expect(parsed).not.toBeNull();
    expect(parsed).not.toHaveProperty("selected_provider_price_options");
    expect(parsed).not.toHaveProperty("area_market_comparison");
    expect(Object.keys(parsed as object).sort()).toEqual(["draft_status", "selected_provider"]);
  });

  it("rejects a malformed payload without throwing", () => {
    expect(parseProviderMatchResult(null)).toBeNull();
    expect(parseProviderMatchResult({})).toBeNull();
    expect(parseProviderMatchResult({ selected_provider: {}, draft_status: "x" })).toBeNull();
  });

  it("rejects a missing draft_status", () => {
    expect(
      parseProviderMatchResult({
        selected_provider: {
          tenant_id: "t-5",
          provider_name: "Acme Repairs",
          public_badges: ["Verified"],
          rating: 4.2,
          customer_visible_reason: "reason",
        },
      })
    ).toBeNull();
  });
});
