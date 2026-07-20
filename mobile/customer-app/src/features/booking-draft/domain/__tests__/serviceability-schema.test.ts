import { parseServiceabilityResult } from "../serviceability-schema";

describe("parseServiceabilityResult", () => {
  it("accepts a real serviceable result (zipcode match)", () => {
    const parsed = parseServiceabilityResult({
      serviceable: true,
      available_provider_count: 3,
      matched_by: "zipcode",
      message: "Service is available in Bengaluru 560001.",
      reason_code: null,
      draft_status: "serviceability_checked",
    });
    expect(parsed?.serviceable).toBe(true);
    expect(parsed?.matched_by).toBe("zipcode");
  });

  it("accepts a real serviceable result (city fallback match)", () => {
    const parsed = parseServiceabilityResult({
      serviceable: true,
      available_provider_count: 1,
      matched_by: "city",
      message: "Service is available in Bengaluru.",
      reason_code: null,
      draft_status: "serviceability_checked",
    });
    expect(parsed?.matched_by).toBe("city");
  });

  it("accepts a real not-serviceable result", () => {
    const parsed = parseServiceabilityResult({
      serviceable: false,
      available_provider_count: 0,
      matched_by: null,
      message: "This service is not available in Pune yet. We're expanding soon!",
      reason_code: "NO_PROVIDER_IN_CITY",
      draft_status: "collecting_details",
    });
    expect(parsed?.serviceable).toBe(false);
    expect(parsed?.reason_code).toBe("NO_PROVIDER_IN_CITY");
  });

  it("rejects an unknown matched_by value (fails closed rather than trusting an unexpected value)", () => {
    expect(
      parseServiceabilityResult({
        serviceable: true,
        available_provider_count: 1,
        matched_by: "radius",
        message: "x",
        reason_code: null,
        draft_status: "draft",
      })
    ).toBeNull();
  });

  it("rejects a malformed payload without throwing", () => {
    expect(parseServiceabilityResult(null)).toBeNull();
    expect(parseServiceabilityResult({})).toBeNull();
  });
});
