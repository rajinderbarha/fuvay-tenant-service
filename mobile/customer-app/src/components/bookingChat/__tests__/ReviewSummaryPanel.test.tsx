import React from "react";
import { screen, fireEvent } from "@testing-library/react-native";
import { renderWithProviders } from "../../../testing/renderWithProviders";
import { ReviewSummaryPanel } from "../ReviewSummaryPanel";
import { BookingReviewSummary } from "../../../domain/bookingReview";
import { asBookingDraftId } from "../../../domain/ids";

function summary(overrides: Partial<BookingReviewSummary> = {}): BookingReviewSummary {
  return {
    draftId: asBookingDraftId("d1"),
    categoryName: "Home Services",
    offeringName: "AC Service",
    jobTypeLabel: "Repair",
    issueSummary: "AC not cooling properly",
    answers: [{ key: "brand", label: "Which AC brand?", value: "LG" }],
    address: {
      city: "Ludhiana", zipcode: "141002", lines: ["House 214"],
      serviceable: true, serviceabilityStatus: "serviceable",
    },
    priceState: { kind: "inspection_based" },
    inspection: {
      visitFee: { minorUnits: 29900, currency: "INR" },
      feeAdjustmentNote: null,
      visitFeePolicy: {
        creditedAgainstWork: true,
        creditedWhen: "customer_approves_estimate",
        condition: "work_amount_exceeds_visit_fee",
        ifDeclined: "visit_fee_only",
      },
    },
    bargainAvailable: false,
    provider: {
      tenantId: "t1", providerName: "Guramrit", publicBadges: [], rating: null,
      facts: {
        verified: false, rating: null, reviewCount: 0, jobsCompleted: 0,
        completionRate: null, onPlatformSince: null, city: "Ludhiana", isNew: true,
      },
    },
    photoCount: 0,
    photoUrls: [],
    preferredDate: null,
    promisedSlot: null,
    serviceSlaMinutes: null,
    serviceDueAt: null,
    isEmergency: false,
    emergencySurcharge: null,
    emergencySurchargePreview: null,
    readyForConfirmation: true,
    missing: [],
    ...overrides,
  } as BookingReviewSummary;
}

const handlers = {
  onConfirm: () => {},
  onEditSlot: () => {},
  onEditPhotos: () => {},
};

describe("ReviewSummaryPanel", () => {
  it("presents request, technician and money together in one panel", () => {
    renderWithProviders(
      <ReviewSummaryPanel
        summary={summary()} slotLabel="Today, 14:00-15:00"
        confirming={false} confirmDisabledReason={null} {...handlers}
      />,
    );
    expect(screen.getByText("YOUR REQUEST")).toBeTruthy();
    expect(screen.getByText("YOUR TECHNICIAN")).toBeTruthy();
    expect(screen.getByText("What you'll pay")).toBeTruthy();
    expect(screen.getByLabelText("Confirm and book")).toBeTruthy();
  });

  it("offers a way back to the earlier turns", () => {
    const onEditSlot = jest.fn();
    const onEditPhotos = jest.fn();
    renderWithProviders(
      <ReviewSummaryPanel
        summary={summary()} slotLabel="Today, 14:00-15:00"
        confirming={false} confirmDisabledReason={null}
        onConfirm={() => {}} onEditSlot={onEditSlot} onEditPhotos={onEditPhotos}
      />,
    );
    fireEvent.press(screen.getByLabelText("Change time"));
    expect(onEditSlot).toHaveBeenCalledTimes(1);
    fireEvent.press(screen.getByLabelText("Add a photo"));
    expect(onEditPhotos).toHaveBeenCalledTimes(1);
  });

  it("invites choosing a time when none has been promised", () => {
    renderWithProviders(
      <ReviewSummaryPanel
        summary={summary()} slotLabel={null}
        confirming={false} confirmDisabledReason={null} {...handlers}
      />,
    );
    expect(screen.getByLabelText("Choose a time")).toBeTruthy();
    expect(screen.queryByLabelText("Change time")).toBeNull();
  });

  it("blocks confirmation with the real reason when not eligible", () => {
    const onConfirm = jest.fn();
    renderWithProviders(
      <ReviewSummaryPanel
        summary={summary()} slotLabel={null}
        confirming={false} confirmDisabledReason="Something is still missing."
        onConfirm={onConfirm} onEditSlot={() => {}} onEditPhotos={() => {}}
      />,
    );
    expect(screen.getByText("Something is still missing.")).toBeTruthy();
    fireEvent.press(screen.getByLabelText("Confirm and book"));
    expect(onConfirm).not.toHaveBeenCalled();
  });

  it("cannot be double-submitted while confirming", () => {
    const onConfirm = jest.fn();
    renderWithProviders(
      <ReviewSummaryPanel
        summary={summary()} slotLabel={null}
        confirming confirmDisabledReason={null}
        onConfirm={onConfirm} onEditSlot={() => {}} onEditPhotos={() => {}}
      />,
    );
    fireEvent.press(screen.getByLabelText("Confirming"));
    expect(onConfirm).not.toHaveBeenCalled();
  });

  it("omits the money section entirely when there is nothing payable up front", () => {
    renderWithProviders(
      <ReviewSummaryPanel
        summary={summary({ inspection: null })} slotLabel={null}
        confirming={false} confirmDisabledReason={null} {...handlers}
      />,
    );
    expect(screen.queryByText("What you'll pay")).toBeNull();
    // The rest of the panel still renders.
    expect(screen.getByText("YOUR REQUEST")).toBeTruthy();
  });
});
