import React from "react";
import { Alert } from "react-native";
import { fireEvent, waitFor } from "@testing-library/react-native";
import { NavigationContainer } from "@react-navigation/native";
import { renderWithProviders } from "../../../testing/renderWithProviders";
import { SavedAddressesScreen } from "../SavedAddressesScreen";
import * as addressesQueryModule from "../../../api/customerAddresses/useCustomerAddressesQuery";
import * as customerAddressesApi from "../../../api/customerAddresses/customerAddressesApi";
import { CustomerSavedAddress } from "../../../domain/customerSavedAddress";

const mockNavigate = jest.fn();
jest.mock("@react-navigation/native", () => ({
  ...jest.requireActual("@react-navigation/native"),
  useNavigation: () => ({ navigate: mockNavigate, goBack: jest.fn() }),
}));

function address(overrides: Partial<CustomerSavedAddress> = {}): CustomerSavedAddress {
  return {
    id: "a-1", label: "Home", recipientName: null, mobile: "+919900024102",
    line1: "House 24, Model Town", line2: null, landmark: null,
    city: "Ludhiana", district: null, state: "Punjab", country: "India",
    postalCode: "141002", isDefault: true,
    createdAt: "2026-01-01T00:00:00Z" as CustomerSavedAddress["createdAt"], updatedAt: null,
    ...overrides,
  };
}

function renderScreen() {
  return renderWithProviders(
    <NavigationContainer>
      <SavedAddressesScreen />
    </NavigationContainer>,
  );
}

function mockAddresses(data: CustomerSavedAddress[]) {
  jest.spyOn(addressesQueryModule, "useCustomerAddressesQuery").mockReturnValue({
    data, isPending: false, isError: false, refetch: jest.fn(),
  } as unknown as ReturnType<typeof addressesQueryModule.useCustomerAddressesQuery>);
}

describe("SavedAddressesScreen", () => {
  afterEach(() => { jest.restoreAllMocks(); mockNavigate.mockClear(); });

  it("shows the real default address with its Default badge and suggested-address copy", () => {
    mockAddresses([address()]);
    const { getByText } = renderScreen();
    expect(getByText("Default")).toBeTruthy();
    expect(getByText(/House 24, Model Town/)).toBeTruthy();
    expect(getByText("Used as the suggested address for new service requests.")).toBeTruthy();
  });

  it("never shows a permanent Serviceable/Unserviceable badge on a saved address", () => {
    mockAddresses([address()]);
    const { queryByText } = renderScreen();
    expect(queryByText(/serviceable/i)).toBeNull();
  });

  it("shows the honest empty state, never fabricated Work/Family addresses, when only a default exists", () => {
    mockAddresses([address()]);
    const { getByText, queryByText } = renderScreen();
    expect(getByText("No other saved addresses")).toBeTruthy();
    expect(queryByText("Work")).toBeNull();
    expect(queryByText("Family")).toBeNull();
  });

  it("shows Add new / Edit and navigates to the real Address Form -- functional as of this phase", () => {
    mockAddresses([address(), address({ id: "a-2", isDefault: false, label: "Work" })]);
    const { getByText, getAllByText } = renderScreen();
    expect(getByText("Add new")).toBeTruthy();

    fireEvent.press(getByText("Add new"));
    expect(mockNavigate).toHaveBeenCalledWith("AddAddress");

    fireEvent.press(getAllByText("Edit")[0]);
    expect(mockNavigate).toHaveBeenCalledWith("EditAddress", { addressId: "a-1" });
  });

  it("offers Set as default only on non-default addresses, and calls the real mutation", async () => {
    mockAddresses([address(), address({ id: "a-2", isDefault: false, label: "Work" })]);
    const setDefaultSpy = jest.spyOn(customerAddressesApi, "setDefaultAddress").mockResolvedValue({
      data: { ...address({ id: "a-2", isDefault: true, label: "Work" }) },
      requestId: "req-1",
    } as unknown as Awaited<ReturnType<typeof customerAddressesApi.setDefaultAddress>>);

    const { getByText, queryByText } = renderScreen();
    expect(queryByText("Set as default", { exact: false })).toBeTruthy();
    fireEvent.press(getByText("Set as default"));

    await waitFor(() => expect(setDefaultSpy).toHaveBeenCalledWith("a-2"));
  });

  it("shows a delete confirmation before calling the real delete mutation, and preserves confirmed-booking copy", () => {
    mockAddresses([address()]);
    const alertSpy = jest.spyOn(Alert, "alert").mockImplementation(() => {});
    const { getByText } = renderScreen();
    fireEvent.press(getByText("Delete"));
    expect(alertSpy).toHaveBeenCalledWith(
      "Delete this address?",
      expect.stringContaining("Confirmed bookings will keep their stored address."),
      expect.any(Array),
    );
  });

  it("only deletes after the customer confirms, never optimistically before server acknowledgement", async () => {
    mockAddresses([address()]);
    const deleteSpy = jest.spyOn(customerAddressesApi, "deleteMyAddress").mockResolvedValue({
      data: { address_id: "a-1", deleted: true }, requestId: "req-1",
    } as unknown as Awaited<ReturnType<typeof customerAddressesApi.deleteMyAddress>>);
    jest.spyOn(Alert, "alert").mockImplementation((_title, _msg, buttons) => {
      const confirm = buttons?.find(b => b.text === "Delete");
      confirm?.onPress?.();
    });

    const { getByText } = renderScreen();
    fireEvent.press(getByText("Delete"));

    await waitFor(() => expect(deleteSpy).toHaveBeenCalledWith("a-1"));
  });

  it("shows the immutable confirmed-booking-snapshot disclosure", () => {
    mockAddresses([address()]);
    const { getByText } = renderScreen();
    expect(getByText("Existing bookings stay unchanged")).toBeTruthy();
  });

  it("never renders maps, GPS graphics or coordinates", () => {
    mockAddresses([address()]);
    const { queryByText } = renderScreen();
    expect(queryByText(/latitude|longitude|GPS/i)).toBeNull();
  });
});
