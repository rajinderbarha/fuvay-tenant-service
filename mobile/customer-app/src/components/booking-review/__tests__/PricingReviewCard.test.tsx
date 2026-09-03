import React from "react";
import { renderWithProviders } from "../../../testing/renderWithProviders";
import { PricingReviewCard } from "../PricingReviewCard";
import { classifyReviewPricing } from "../../../domain/servicePricing";

/**
 * Regression tests for the physical/live defect: AC Gas Refilling's
 * Booking Review reached a real customer showing ₹0 instead of the real
 * ₹299 visit fee + inspection-required messaging. `classifyReviewPricing`
 * is the same real classification function `adaptBookingReviewSummary`
 * uses, so these tests exercise the exact input shapes the backend now
 * produces after the pricing-contract fix (visit_fee=299, standard_price
 * null for inspection mode; a real positive standard_price for fixed
 * mode) and assert on what actually renders.
 */
describe("PricingReviewCard", () => {
  it("shows the real ₹299 visit fee and inspection-required copy for AC Gas Refilling, never ₹0 or Free", () => {
    const { state, inspection } = classifyReviewPricing({
      requiresInspectionEstimate: true,
      visitFeeRaw: 299,
      feeAdjustmentNote: null,
      standardPriceRaw: null,
    });

    const { getByText, queryByText } = renderWithProviders(
      <PricingReviewCard priceState={state} inspection={inspection} />,
    );

    expect(getByText("Inspection required")).toBeTruthy();
    expect(getByText("₹299.00 visit fee")).toBeTruthy();
    expect(getByText(/inspect your service and provide an estimate/i)).toBeTruthy();
    expect(getByText(/approval will be required before repair begins/i)).toBeTruthy();

    expect(queryByText("₹0")).toBeNull();
    expect(queryByText("Free")).toBeNull();
    expect(queryByText(/^₹0/)).toBeNull();
  });

  it("shows AC Installation's real positive fixed price, never a zero or admin-catalog placeholder", () => {
    const { state, inspection } = classifyReviewPricing({
      requiresInspectionEstimate: false,
      visitFeeRaw: null,
      feeAdjustmentNote: null,
      standardPriceRaw: 1200,
    });

    const { getByText, queryByText } = renderWithProviders(
      <PricingReviewCard priceState={state} inspection={inspection} />,
    );

    expect(getByText("₹1,200.00")).toBeTruthy();
    expect(queryByText("₹0")).toBeNull();
    expect(queryByText("Free")).toBeNull();
    expect(queryByText("Inspection required")).toBeNull();
  });

  it("never renders ₹0 or Free when the resolved fixed price is exactly zero -- shows an unavailable state instead", () => {
    const { state, inspection } = classifyReviewPricing({
      requiresInspectionEstimate: false,
      visitFeeRaw: null,
      feeAdjustmentNote: null,
      standardPriceRaw: 0,
    });

    const { getByText, queryByText } = renderWithProviders(
      <PricingReviewCard priceState={state} inspection={inspection} />,
    );

    expect(getByText("Pricing is currently unavailable for this service")).toBeTruthy();
    expect(queryByText("₹0")).toBeNull();
    expect(queryByText("Free")).toBeNull();
  });

  it("never renders a numeric price or Free when pricing is missing entirely", () => {
    const { state, inspection } = classifyReviewPricing({
      requiresInspectionEstimate: false,
      visitFeeRaw: null,
      feeAdjustmentNote: null,
      standardPriceRaw: null,
    });

    const { getByText, queryByText } = renderWithProviders(
      <PricingReviewCard priceState={state} inspection={inspection} />,
    );

    expect(getByText("Pricing is currently unavailable for this service")).toBeTruthy();
    expect(queryByText("₹0")).toBeNull();
    expect(queryByText("Free")).toBeNull();
  });

  it("never renders ₹0 or Free for an inspection-mode offering with a missing/zero visit fee -- shows unavailable instead", () => {
    const { state, inspection } = classifyReviewPricing({
      requiresInspectionEstimate: true,
      visitFeeRaw: 0,
      feeAdjustmentNote: null,
      standardPriceRaw: null,
    });

    const { getByText, queryByText } = renderWithProviders(
      <PricingReviewCard priceState={state} inspection={inspection} />,
    );

    expect(getByText("Pricing is currently unavailable for this service")).toBeTruthy();
    expect(queryByText("Inspection required")).toBeNull();
    expect(queryByText("₹0")).toBeNull();
    expect(queryByText("Free")).toBeNull();
  });
});
