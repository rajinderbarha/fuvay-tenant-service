import React from "react";
import { renderWithProviders } from "../../../testing/renderWithProviders";
import { ActiveBookingCard } from "../ActiveBookingCard";
import { CustomerBookingListItem } from "../../../domain/bookingList";
import { parseServerTimestamp } from "../../../domain/dates";

function item(overrides: Partial<CustomerBookingListItem> = {}): CustomerBookingListItem {
  return {
    bookingId: "b-1",
    bookingNumber: "BK-20260803-000010",
    rawStatus: "pending_assignment",
    stage: "provider_assignment",
    statusLabel: "Request confirmed",
    activityText: "Assigning an eligible professional",
    supportingText: "We'll notify you when a provider accepts the request.",
    createdAt: parseServerTimestamp("2026-08-03T09:41:00Z", "created_at"),
    serviceName: "Air Conditioning",
    jobType: "Repair",
    summaryFields: [],
    address: { label: null, formatted: "Model Town, Ludhiana - 141002", zipcode: "141002" },
    pricing: { state: { kind: "unavailable" }, inspection: null },
    urgency: null, scheduledDate: null, scheduledTimeWindow: null, latenessLabel: null,
    ...overrides,
  };
}

function render(overrides: Partial<CustomerBookingListItem> = {}) {
  return renderWithProviders(
    <ActiveBookingCard item={item(overrides)} onViewDetails={() => {}} onContactSupport={() => {}} />,
  );
}

describe("ActiveBookingCard scan-first summary", () => {
  it("keeps detailed assistant answers on Booking Details instead of duplicating them in the list", () => {
    const { queryByText, getByText } = render({
      summaryFields: [
        { key: "q-2", label: "Please share any additional details about the issue.", value: "Water drips from the outdoor unit each morning.", questionType: "text" },
      ],
    });
    expect(queryByText("Additional Detail")).toBeNull();
    expect(queryByText("Water drips from the outdoor unit each morning.")).toBeNull();
    expect(getByText("Assigning an eligible professional")).toBeTruthy();
    expect(getByText("View booking")).toBeTruthy();
  });

  it("shows only operational facts needed to choose the right request", () => {
    const { getByText } = render({
      scheduledDate: "2026-08-24",
      scheduledTimeWindow: "10:00 AM–12:00 PM",
      pricing: {
        state: { kind: "valid", amount: { minorUnits: 59900, currency: "INR" } },
        inspection: null,
      },
    });
    expect(getByText(/24 Aug 2026.*10:00 AM.*12:00 PM/)).toBeTruthy();
    expect(getByText("Model Town, Ludhiana - 141002")).toBeTruthy();
    expect(getByText(/Service price/)).toBeTruthy();
  });
});
