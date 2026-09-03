import { resolveServicePriceDisplay, classifyRawAmount, classifyReviewPricing } from "../servicePricing";

describe("resolveServicePriceDisplay", () => {
  it("renders a valid positive price as 'From ₹X'", () => {
    const result = resolveServicePriceDisplay({ kind: "valid", amount: { minorUnits: 39900, currency: "INR" } });
    expect(result.label).toContain("399");
    expect(result.label.startsWith("From")).toBe(true);
    expect(result.isNumericPrice).toBe(true);
  });

  it("renders inspection-based pricing without a number", () => {
    const result = resolveServicePriceDisplay({ kind: "inspection_based" });
    expect(result.label).toBe("Inspection-based");
    expect(result.isNumericPrice).toBe(false);
  });

  it("renders detail-dependent pricing without a number", () => {
    expect(resolveServicePriceDisplay({ kind: "detail_dependent" }).label).toBe("Price after details");
  });

  it("renders quote-required pricing without a number", () => {
    expect(resolveServicePriceDisplay({ kind: "quote_required" }).label).toBe("Quote after inspection");
  });

  it("renders unavailable pricing without a number, never as ₹0", () => {
    const result = resolveServicePriceDisplay({ kind: "unavailable" });
    expect(result.label).not.toContain("₹0");
    expect(result.label).not.toMatch(/^\$?0/);
    expect(result.isNumericPrice).toBe(false);
  });

  it("only renders 'Free' when explicitly classified as free, never inferred", () => {
    expect(resolveServicePriceDisplay({ kind: "free" }).label).toBe("Free");
  });
});

describe("classifyRawAmount", () => {
  it("classifies a positive amount as valid", () => {
    expect(classifyRawAmount(39900)).toEqual({ kind: "valid", amount: { minorUnits: 39900, currency: "INR" } });
  });

  it("classifies exactly zero as unavailable, never valid or free (the confirmed live standard_price: 0.0 case)", () => {
    expect(classifyRawAmount(0)).toEqual({ kind: "unavailable" });
  });

  it("classifies null as unavailable", () => {
    expect(classifyRawAmount(null)).toEqual({ kind: "unavailable" });
  });

  it("classifies undefined as unavailable", () => {
    expect(classifyRawAmount(undefined)).toEqual({ kind: "unavailable" });
  });

  it("classifies a negative amount as unavailable", () => {
    expect(classifyRawAmount(-100)).toEqual({ kind: "unavailable" });
  });

  it("never produces a display label containing ₹0 for the classified zero case", () => {
    const state = classifyRawAmount(0);
    const display = resolveServicePriceDisplay(state);
    expect(display.label).not.toContain("₹0");
  });
});

describe("classifyReviewPricing", () => {
  it("classifies a valid inspection visit fee as inspection_based with the real amount", () => {
    const result = classifyReviewPricing({
      requiresInspectionEstimate: true, visitFeeRaw: 299, feeAdjustmentNote: null,
      standardPriceRaw: null,
    });
    expect(result.state).toEqual({ kind: "inspection_based" });
    expect(result.inspection?.visitFee).toEqual({ minorUnits: 29900, currency: "INR" });
  });

  it("classifies a zero/missing inspection visit fee as unavailable, never a fabricated fee", () => {
    const result = classifyReviewPricing({
      requiresInspectionEstimate: true, visitFeeRaw: 0, feeAdjustmentNote: null,
      standardPriceRaw: null,
    });
    expect(result.state).toEqual({ kind: "unavailable" });
    expect(result.inspection).toBeNull();
  });

  it("classifies a real standard price as valid", () => {
    const result = classifyReviewPricing({
      requiresInspectionEstimate: false, visitFeeRaw: null, feeAdjustmentNote: null,
      standardPriceRaw: 499,
    });
    expect(result.state).toEqual({ kind: "valid", amount: { minorUnits: 49900, currency: "INR" } });
  });

  it("classifies a zero standard price as unavailable, never ₹0 or Free", () => {
    const result = classifyReviewPricing({
      requiresInspectionEstimate: false, visitFeeRaw: null, feeAdjustmentNote: null,
      standardPriceRaw: 0,
    });
    expect(result.state).toEqual({ kind: "unavailable" });
  });
});
