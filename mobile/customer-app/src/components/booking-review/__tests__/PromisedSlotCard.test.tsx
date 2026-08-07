import React from "react";
import { fireEvent, waitFor } from "@testing-library/react-native";
import { renderWithProviders } from "../../../testing/renderWithProviders";
import { PromisedSlotCard } from "../PromisedSlotCard";

const SLOT = { date: "2026-08-10", timeWindow: "10:00-11:00", startsAt: "2026-08-10T10:00:00", endsAt: "2026-08-10T11:00:00", slotMinutes: 60, daysAhead: 3 };

function render(overrides: Partial<React.ComponentProps<typeof PromisedSlotCard>> = {}) {
  return renderWithProviders(
    <PromisedSlotCard
      slot={SLOT}
      slaMinutes={60}
      availableSlots={null}
      slotsLoading={false}
      slotSelectionError={null}
      onOpenPicker={jest.fn()}
      onSelectSlot={jest.fn().mockResolvedValue(undefined)}
      {...overrides}
    />,
  );
}

describe("PromisedSlotCard picker", () => {
  it("fetches the real slot list only once the customer opens the picker, not on mount", () => {
    const onOpenPicker = jest.fn();
    const { getByText } = render({ onOpenPicker });
    expect(onOpenPicker).not.toHaveBeenCalled();
    fireEvent.press(getByText("Change"));
    expect(onOpenPicker).toHaveBeenCalledTimes(1);
  });

  it("lets the customer pick a slot other than the system-chosen one", async () => {
    const onSelectSlot = jest.fn().mockResolvedValue(undefined);
    const other = { date: "2026-08-11", timeWindow: "14:00-15:00", daysAhead: 4 };
    const { getByText, getByLabelText } = render({
      onSelectSlot,
      availableSlots: [{ date: SLOT.date, timeWindow: SLOT.timeWindow, daysAhead: SLOT.daysAhead }, other],
    });
    fireEvent.press(getByText("Change"));
    fireEvent.press(getByLabelText(/Tuesday 11 Aug, 14:00-15:00/));
    await waitFor(() => expect(onSelectSlot).toHaveBeenCalledWith("2026-08-11", "14:00-15:00"));
  });

  it("shows the real reason a slot could not be selected, from the controller's own message", () => {
    // The card renders whatever slotSelectionError the controller set
    // after a failed pick -- it never invents its own wording.
    const { getByText } = render({
      availableSlots: [{ date: "2026-08-11", timeWindow: "14:00-15:00", daysAhead: 4 }],
      slotSelectionError: "That time is no longer available.",
    });
    fireEvent.press(getByText("Change"));
    expect(getByText("That time is no longer available.")).toBeTruthy();
  });

  it("does not close the sheet or clear the pick when selection fails", async () => {
    const onSelectSlot = jest.fn().mockRejectedValue(new Error("nope"));
    const other = { date: "2026-08-11", timeWindow: "14:00-15:00", daysAhead: 4 };
    const { getByText, getByLabelText } = render({ onSelectSlot, availableSlots: [other] });
    fireEvent.press(getByText("Change"));
    fireEvent.press(getByLabelText(/Tuesday 11 Aug, 14:00-15:00/));
    await waitFor(() => expect(onSelectSlot).toHaveBeenCalled());
    // The sheet's own heading is still on screen -- it never auto-closed.
    expect(getByText("Choose a time")).toBeTruthy();
  });

  it("shows the honest no-promise state when the provider has no capacity", () => {
    const { getByText } = render({ slot: null });
    expect(getByText(/can't confirm a service time right now/)).toBeTruthy();
  });
});
