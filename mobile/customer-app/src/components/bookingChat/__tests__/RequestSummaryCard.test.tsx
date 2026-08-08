import React from "react";
import { screen } from "@testing-library/react-native";
import { renderWithProviders } from "../../../testing/renderWithProviders";
import { RequestSummaryCard } from "../RequestSummaryCard";
import { BookingReviewSummary } from "../../../domain/bookingReview";
import { asBookingDraftId } from "../../../domain/ids";

function summary(overrides: Partial<BookingReviewSummary> = {}): BookingReviewSummary {
  return {
    draftId: asBookingDraftId("d1"),
    categoryName: "Home Services",
    offeringName: "AC Service",
    jobTypeLabel: "Repair",
    issueSummary: "AC not cooling properly",
    answers: [
      { key: "ac_type", label: "Split AC or Window AC?", value: "Split AC" },
      { key: "brand", label: "Which AC brand do you have?", value: "LG" },
      { key: "issue_detail", label: "Additional details", value: "" },
    ],
    address: {
      city: "Ludhiana",
      zipcode: "141002",
      lines: ["House 214", "Model Town"],
      serviceable: true,
      serviceabilityStatus: "serviceable",
    },
    priceState: { kind: "inspection_based" },
    inspection: null,
    bargainAvailable: false,
    provider: null,
    photoCount: 2,
    photoUrls: ["https://cdn.test/a.jpg", "https://cdn.test/b.jpg"],
    preferredDate: null,
    promisedSlot: null,
    serviceSlaMinutes: null,
    serviceDueAt: null,
    isEmergency: false,
    emergencySurcharge: null,
    readyForConfirmation: true,
    missing: [],
    ...overrides,
  } as BookingReviewSummary;
}

describe("RequestSummaryCard", () => {
  it("plays back the service, job type and issue", () => {
    renderWithProviders(<RequestSummaryCard summary={summary()} slotLabel={null} />);
    expect(screen.getByText("AC Service")).toBeTruthy();
    expect(screen.getByText("Repair")).toBeTruthy();
    expect(screen.getByText("AC not cooling properly")).toBeTruthy();
  });

  it("plays back the customer's own answers so a wrong one can still be caught", () => {
    renderWithProviders(<RequestSummaryCard summary={summary()} slotLabel={null} />);
    expect(screen.getByText("Split AC or Window AC?")).toBeTruthy();
    expect(screen.getByText("Split AC")).toBeTruthy();
    expect(screen.getByText("LG")).toBeTruthy();
  });

  it("omits an answer the customer left blank rather than showing an empty row", () => {
    renderWithProviders(<RequestSummaryCard summary={summary()} slotLabel={null} />);
    expect(screen.queryByText("Additional details")).toBeNull();
  });

  it("shows the real address lines and locality", () => {
    renderWithProviders(<RequestSummaryCard summary={summary()} slotLabel={null} />);
    expect(screen.getByText(/House 214/)).toBeTruthy();
    expect(screen.getByText(/141002/)).toBeTruthy();
  });

  it("shows the chosen slot when one was promised", () => {
    renderWithProviders(
      <RequestSummaryCard summary={summary()} slotLabel="Today, 14:00-15:00" />,
    );
    expect(screen.getByText("When")).toBeTruthy();
    expect(screen.getByText("Today, 14:00-15:00")).toBeTruthy();
  });

  it("omits the When row entirely when no slot could be promised", () => {
    // Better silence than a fabricated arrival time.
    renderWithProviders(<RequestSummaryCard summary={summary()} slotLabel={null} />);
    expect(screen.queryByText("When")).toBeNull();
  });

  it("counts the attached photos in the heading", () => {
    renderWithProviders(<RequestSummaryCard summary={summary()} slotLabel={null} />);
    expect(screen.getByText("2 PHOTOS YOU SENT")).toBeTruthy();
    expect(screen.getAllByLabelText("Photo you attached")).toHaveLength(2);
  });

  it("uses the singular heading for one photo", () => {
    renderWithProviders(
      <RequestSummaryCard
        summary={summary({ photoUrls: ["https://cdn.test/a.jpg"], photoCount: 1 })}
        slotLabel={null}
      />,
    );
    expect(screen.getByText("PHOTO YOU SENT")).toBeTruthy();
  });

  it("omits the photo section when nothing was attached", () => {
    renderWithProviders(
      <RequestSummaryCard summary={summary({ photoUrls: [], photoCount: 0 })} slotLabel={null} />,
    );
    expect(screen.queryByText(/PHOTO/)).toBeNull();
  });

  it("renders without an address or answers rather than showing empty headings", () => {
    renderWithProviders(
      <RequestSummaryCard
        summary={summary({
          answers: [],
          address: { city: null, zipcode: null, lines: [], serviceable: true, serviceabilityStatus: null },
        })}
        slotLabel={null}
      />,
    );
    expect(screen.getByText("AC Service")).toBeTruthy();
    expect(screen.queryByText("WHAT YOU TOLD US")).toBeNull();
    expect(screen.queryByText("Where")).toBeNull();
  });
});
