import React from "react";
import { screen, fireEvent } from "@testing-library/react-native";
import { renderWithProviders } from "../../../testing/renderWithProviders";
import { BookingConfirmFlow } from "../BookingConfirmFlow";

const base = {
  bookingNumber: "BK-20260808-000002",
  providerName: "Guramrit",
  slotLabel: "Today, 14:00-15:00",
  amountLabel: "₹299.00",
  feeCreditedAgainstWork: true,
  onTrackBooking: () => {},
  onDone: () => {},
};

describe("BookingConfirmFlow", () => {
  it("shows progress while confirming and no success wording yet", () => {
    renderWithProviders(
      <BookingConfirmFlow {...base} phase="confirming" bookingNumber={null} />,
    );
    expect(screen.getByText("Confirming your booking")).toBeTruthy();
    expect(screen.getByText(/Please keep this screen open/)).toBeTruthy();
    // Critically: nothing that claims success before the backend said so.
    expect(screen.queryByText("You're booked")).toBeNull();
    expect(screen.queryByLabelText("Track this booking")).toBeNull();
  });

  it("never shows a booking number it does not have", () => {
    renderWithProviders(
      <BookingConfirmFlow {...base} phase="confirming" bookingNumber={null} />,
    );
    expect(screen.queryByText(/BK-/)).toBeNull();
  });

  it("shows the real booking details once confirmed", () => {
    renderWithProviders(<BookingConfirmFlow {...base} phase="confirmed" />);
    expect(screen.getByText("You're booked")).toBeTruthy();
    expect(screen.getByText("BK-20260808-000002")).toBeTruthy();
    expect(screen.getByText("Today, 14:00-15:00")).toBeTruthy();
    expect(screen.getByText("₹299.00")).toBeTruthy();
    expect(screen.getByText(/Guramrit has been notified/)).toBeTruthy();
  });

  it("highlights the fee credit only when the backend asserted it", () => {
    renderWithProviders(<BookingConfirmFlow {...base} phase="confirmed" />);
    expect(screen.getByText(/credited against the repair/)).toBeTruthy();
  });

  it("omits the fee-credit line when the backend did not assert the policy", () => {
    renderWithProviders(
      <BookingConfirmFlow {...base} phase="confirmed" feeCreditedAgainstWork={false} />,
    );
    expect(screen.queryByText(/credited against the repair/)).toBeNull();
  });

  it("says the provider will confirm a time rather than inventing one", () => {
    renderWithProviders(
      <BookingConfirmFlow {...base} phase="confirmed" slotLabel={null} />,
    );
    expect(screen.getByText("Your provider will confirm a time")).toBeTruthy();
  });

  it("falls back to an honest message when no provider was assigned", () => {
    renderWithProviders(
      <BookingConfirmFlow {...base} phase="confirmed" providerName={null} />,
    );
    expect(screen.getByText(/notify you as soon as a professional is assigned/)).toBeTruthy();
  });

  it("offers a way to start a new request, so success is not a dead end", () => {
    // A confirmed booking is terminal -- its draft cannot be continued. Without
    // this the only exits led away from the tab, and returning showed the same
    // stale "You're booked".
    const onBookAnother = jest.fn();
    renderWithProviders(
      <BookingConfirmFlow {...base} phase="confirmed" onBookAnother={onBookAnother} />,
    );
    fireEvent.press(screen.getByLabelText("Book another service"));
    expect(onBookAnother).toHaveBeenCalledTimes(1);
  });

  it("hides that option when the screen has nowhere to restart to", () => {
    renderWithProviders(<BookingConfirmFlow {...base} phase="confirmed" />);
    expect(screen.queryByLabelText("Book another service")).toBeNull();
  });

  it("lets the customer act on the booking straight away", () => {
    const onTrackBooking = jest.fn();
    renderWithProviders(
      <BookingConfirmFlow {...base} phase="confirmed" onTrackBooking={onTrackBooking} />,
    );
    fireEvent.press(screen.getByLabelText("Track this booking"));
    expect(onTrackBooking).toHaveBeenCalledTimes(1);
  });
});
