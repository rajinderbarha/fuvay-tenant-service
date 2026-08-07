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
    ...overrides,
  };
}

function render(overrides: Partial<CustomerBookingListItem> = {}) {
  return renderWithProviders(
    <ActiveBookingCard item={item(overrides)} onViewDetails={() => {}} onContactSupport={() => {}} />,
  );
}

describe("ActiveBookingCard additional detail", () => {
  it("shows the assistant's captured free-text answer as a paragraph", () => {
    // This is what the booking bot asked and the customer typed; it is
    // frozen into answer_snapshot and never changes afterwards.
    const { getByText } = render({
      summaryFields: [
        { key: "q-2", label: "Please share any additional details about the issue.", value: "Water drips from the outdoor unit each morning.", questionType: "text" },
      ],
    });
    expect(getByText("Additional Detail")).toBeTruthy();
    expect(getByText("Water drips from the outdoor unit each morning.")).toBeTruthy();
  });

  it("omits the section entirely when the flow never asked for free text", () => {
    // An empty bordered box on the card would imply something is missing
    // or fillable; nothing here is editable.
    const { queryByText } = render({
      summaryFields: [
        { key: "q-1", label: "Brand", value: "LG", questionType: "single_select" },
      ],
    });
    expect(queryByText("Additional Detail")).toBeNull();
  });

  it("keeps chosen-option answers out of the note box and in the grid", () => {
    const { getByText, queryByText } = render({
      summaryFields: [
        { key: "q-1", label: "Brand", value: "LG", questionType: "single_select" },
        { key: "q-2", label: "Notes", value: "Second floor flat", questionType: "text" },
      ],
    });
    expect(getByText("LG")).toBeTruthy();
    expect(getByText("Second floor flat")).toBeTruthy();
    // The grid never renders the free-text answer as a cell.
    expect(queryByText("Additional Detail")).toBeTruthy();
  });
});
