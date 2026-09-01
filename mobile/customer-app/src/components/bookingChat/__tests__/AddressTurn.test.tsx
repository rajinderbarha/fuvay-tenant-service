import React from "react";
import { fireEvent, screen, waitFor } from "@testing-library/react-native";

import { renderWithProviders } from "../../../testing/renderWithProviders";
import type { CustomerSavedAddress } from "../../../domain/customerSavedAddress";
import type { ServerTimestamp } from "../../../domain/dates";
import { AddressTurn } from "../AddressTurn";

const baseProps = {
  zipcode: "141002",
  loading: false,
  submitting: false,
  error: null,
  onPickExisting: jest.fn(),
  onCreateNew: jest.fn(),
};

function saved(label: string, id: string): CustomerSavedAddress {
  return {
    id,
    label,
    recipientName: null,
    mobile: null,
    line1: `${id} Model Town`,
    line2: null,
    landmark: null,
    city: "Ludhiana",
    district: null,
    state: "Punjab",
    country: "India",
    postalCode: "141002",
    isDefault: label === "Home",
    createdAt: "2026-08-01T00:00:00Z" as ServerTimestamp,
    updatedAt: null,
  };
}

describe("AddressTurn", () => {
  beforeEach(() => jest.clearAllMocks());

  it("shows every address field and submits the locked booking pincode", async () => {
    renderWithProviders(<AddressTurn {...baseProps} addresses={[]} />);
    await waitFor(() => expect(screen.getByLabelText("Add a new address")).toBeTruthy());
    fireEvent.press(screen.getByLabelText("Add a new address"));

    fireEvent.changeText(screen.getByLabelText("Recipient name"), "Amit Kumar");
    fireEvent.changeText(screen.getByLabelText("Flat, building and street"), "14 Model Town");
    fireEvent.changeText(screen.getByLabelText("Apartment floor or area"), "Second floor");
    fireEvent.changeText(screen.getByLabelText("Landmark"), "Near City Park");
    fireEvent.changeText(screen.getByLabelText("City"), "Ludhiana");
    fireEvent.changeText(screen.getByLabelText("State"), "Punjab");

    const pincode = screen.getByLabelText("Pincode, automatically filled");
    expect(pincode.props.value).toBe("141002");
    expect(pincode.props.editable).toBe(false);
    fireEvent.press(screen.getByLabelText(/Save address/));

    expect(baseProps.onCreateNew).toHaveBeenCalledWith(expect.objectContaining({
      label: "Home",
      name: "Amit Kumar",
      address_line_1: "14 Model Town",
      address_line_2: "Second floor",
      landmark: "Near City Park",
      city: "Ludhiana",
      state: "Punjab",
      zipcode: "141002",
    }));
  });

  it("stops offering another address after Home, Office and Other exist", async () => {
    renderWithProviders(
      <AddressTurn {...baseProps} addresses={[saved("Home", "home"), saved("Work", "office"), saved("Other", "other")]} />,
    );
    await waitFor(() => expect(screen.getByText("Home, Office and Other already saved")).toBeTruthy());
    expect(screen.getByLabelText("Add a new address").props.accessibilityState.disabled).toBe(true);
  });
});
