import { parseReviewResult } from "../review-schema";

const provider = {
  tenant_id: "t-1",
  provider_name: "Acme Repairs",
  public_badges: ["Verified"],
  rating: 4.2,
  customer_visible_reason: "reason",
};

describe("parseReviewResult", () => {
  it("accepts a real, fully-ready booking_summary", () => {
    const parsed = parseReviewResult({
      booking_summary: {
        offering_name: "AC Repair",
        offering_slug: "ac-repair",
        issue_summary: "Not cooling",
        address: {
          address_line_1: "12 MG Road",
          address_line_2: null,
          landmark: "Near Metro",
          city: "Pune",
          state: "MH",
          zipcode: "411001",
          country: "IN",
          name: "Asha",
          phone: "9999999999",
        },
        city: "Pune",
        zipcode: "411001",
        preferred_date: null,
        preferred_time_window: "Morning",
        selected_provider: provider,
        serviceability: { serviceable: true, status: "serviceable" },
        ready_for_confirmation: true,
        selected_price_tier: "mid",
        customer_offer: 690,
        payment_mode: "customer_pays_provider_directly",
      },
      draft_status: "provider_matched",
    });
    expect(parsed?.booking_summary.ready_for_confirmation).toBe(true);
    expect(parsed?.booking_summary.selected_provider?.provider_name).toBe("Acme Repairs");
  });

  it("accepts a real not-ready booking_summary with missing optional fields", () => {
    const parsed = parseReviewResult({
      booking_summary: { ready_for_confirmation: false },
      draft_status: "serviceability_checked",
    });
    expect(parsed?.booking_summary.ready_for_confirmation).toBe(false);
    expect(parsed?.booking_summary.selected_provider).toBeUndefined();
  });

  it("rejects a missing ready_for_confirmation flag (the one always-real field)", () => {
    expect(parseReviewResult({ booking_summary: {}, draft_status: "draft" })).toBeNull();
  });

  it("rejects a malformed payload without throwing", () => {
    expect(parseReviewResult(null)).toBeNull();
    expect(parseReviewResult({})).toBeNull();
  });
});
