import React from "react";
import { screen, fireEvent } from "@testing-library/react-native";
import { renderWithProviders } from "../../../testing/renderWithProviders";
import { ReviewSheet } from "../ReviewSheet";
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

const noop = {
  onConfirm: () => {}, onEditSlot: () => {}, onEditPhotos: () => {}, onClose: () => {},
};

describe("ReviewSheet", () => {
  it("presents the request, technician and money as one document", () => {
    renderWithProviders(
      <ReviewSheet
        summary={summary()} slotLabel="Today, 14:00-15:00"
        confirming={false} confirmDisabledReason={null} {...noop}
      />,
    );
    expect(screen.getByText("Review your booking")).toBeTruthy();
    expect(screen.getByText("THE PROBLEM")).toBeTruthy();
    expect(screen.getByText("PAYMENT AFTER SERVICE")).toBeTruthy();
  });

  it("makes it clear that no payment is collected while booking", () => {
    renderWithProviders(
      <ReviewSheet
        summary={summary()} slotLabel="Today, 14:00-15:00"
        confirming={false} confirmDisabledReason={null} {...noop}
      />,
    );
    expect(screen.getByText("Nothing due now")).toBeTruthy();
    expect(screen.getByText("Pay after inspection or completed work")).toBeTruthy();
    expect(screen.getByLabelText("Confirm and book")).toBeTruthy();
  });

  it("omits the amount row when nothing is payable up front", () => {
    renderWithProviders(
      <ReviewSheet
        summary={summary({ inspection: null })} slotLabel={null}
        confirming={false} confirmDisabledReason={null} {...noop}
      />,
    );
    expect(screen.queryByText("Inspection fee")).toBeNull();
    // The rest of the sheet still renders.
    expect(screen.getByText("THE PROBLEM")).toBeTruthy();
  });

  it("lets the customer leave without booking", () => {
    const onClose = jest.fn();
    renderWithProviders(
      <ReviewSheet
        summary={summary()} slotLabel={null}
        confirming={false} confirmDisabledReason={null}
        onConfirm={() => {}} onEditSlot={() => {}} onEditPhotos={() => {}} onClose={onClose}
      />,
    );
    fireEvent.press(screen.getByLabelText("Back to chat"));
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("offers a way back to the selected time", () => {
    const onEditSlot = jest.fn();
    const onEditPhotos = jest.fn();
    renderWithProviders(
      <ReviewSheet
        summary={summary()} slotLabel="Today, 14:00-15:00"
        confirming={false} confirmDisabledReason={null}
        onConfirm={() => {}} onClose={() => {}}
        onEditSlot={onEditSlot} onEditPhotos={onEditPhotos}
      />,
    );
    fireEvent.press(screen.getByLabelText("Change time"));
    expect(onEditSlot).toHaveBeenCalledTimes(1);
    expect(onEditPhotos).not.toHaveBeenCalled();
  });

  it("blocks confirmation with the real reason when not eligible", () => {
    const onConfirm = jest.fn();
    renderWithProviders(
      <ReviewSheet
        summary={summary()} slotLabel={null}
        confirming={false} confirmDisabledReason="Something is still missing."
        onConfirm={onConfirm} onEditSlot={() => {}} onEditPhotos={() => {}} onClose={() => {}}
      />,
    );
    expect(screen.getByText("Something is still missing.")).toBeTruthy();
    fireEvent.press(screen.getByLabelText("Confirm and book"));
    expect(onConfirm).not.toHaveBeenCalled();
  });

  it("cannot be double-submitted while confirming", () => {
    const onConfirm = jest.fn();
    renderWithProviders(
      <ReviewSheet
        summary={summary()} slotLabel={null}
        confirming confirmDisabledReason={null}
        onConfirm={onConfirm} onEditSlot={() => {}} onEditPhotos={() => {}} onClose={() => {}}
      />,
    );
    fireEvent.press(screen.getByLabelText("Confirming"));
    expect(onConfirm).not.toHaveBeenCalled();
  });

  it("shows the free-cancellation reassurance when nothing is blocking", () => {
    renderWithProviders(
      <ReviewSheet
        summary={summary()} slotLabel={null}
        confirming={false} confirmDisabledReason={null} {...noop}
      />,
    );
    expect(screen.getByText(/Free cancellation up to 2 hours before the visit/)).toBeTruthy();
  });
});
