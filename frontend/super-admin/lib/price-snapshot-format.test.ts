import { describe, expect, it } from "vitest";
import { formatPriceSnapshotLabel, formatPriceSnapshotValue } from "./price-snapshot-format";

describe("price snapshot formatting", () => {
  it("renders configured rates as percentages instead of rupees", () => {
    expect(formatPriceSnapshotLabel("platform_fee_pct")).toBe("Platform fee (%)");
    expect(formatPriceSnapshotValue("platform_fee_pct", 5)).toBe("5%");
    expect(formatPriceSnapshotValue("provider_percentage", "10.5")).toBe("10.5%");
  });

  it("renders only monetary fields as INR", () => {
    expect(formatPriceSnapshotValue("platform_fee", 15)).toBe("₹15");
    expect(formatPriceSnapshotValue("customer_total", 315)).toBe("₹315");
    expect(formatPriceSnapshotValue("monetization_policy_version", 2)).toBe("2");
  });

  it("renders flags and enum values in readable form", () => {
    expect(formatPriceSnapshotValue("requires_inspection_estimate", true)).toBe("Yes");
    expect(formatPriceSnapshotValue("requires_inspection_estimate", false)).toBe("No");
    expect(formatPriceSnapshotValue("platform_fee_model", "PERCENTAGE_WITH_MIN_MAX"))
      .toBe("Percentage with min max");
  });
});
