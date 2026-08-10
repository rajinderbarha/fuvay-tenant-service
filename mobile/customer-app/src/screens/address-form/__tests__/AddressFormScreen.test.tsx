import React from "react";
import { Alert } from "react-native";
import { fireEvent, waitFor } from "@testing-library/react-native";
import { renderWithProviders } from "../../../testing/renderWithProviders";
import { AddressFormScreen } from "../AddressFormScreen";
import * as addressesQueryModule from "../../../api/customerAddresses/useCustomerAddressesQuery";
import * as detailQueryModule from "../../../api/customerAddresses/useCustomerAddressDetailQuery";
import * as createMutationModule from "../../../api/customerAddresses/useCreateAddressMutation";
import * as updateMutationModule from "../../../api/customerAddresses/useUpdateAddressMutation";
import { CustomerSavedAddress } from "../../../domain/customerSavedAddress";

const mockNavigate = jest.fn();
const mockGoBack = jest.fn();
let mockRouteName = "AddAddress";
let mockRouteParams: Record<string, unknown> = {};

jest.mock("@react-navigation/native", () => ({
  ...jest.requireActual("@react-navigation/native"),
  useNavigation: () => ({ navigate: mockNavigate, goBack: mockGoBack }),
  useRoute: () => ({ name: mockRouteName, params: mockRouteParams }),
}));

function address(overrides: Partial<CustomerSavedAddress> = {}): CustomerSavedAddress {
  return {
    id: "a-1", label: "Home", recipientName: "Rajinder Singh", mobile: "+919900024102",
    line1: "House 24", line2: "Model Town", landmark: null,
    city: "Ludhiana", district: null, state: "Punjab", country: "India",
    postalCode: "141002", isDefault: false,
    createdAt: "2026-01-01T00:00:00Z" as CustomerSavedAddress["createdAt"], updatedAt: null,
    ...overrides,
  };
}

function mockAddressesList(data: CustomerSavedAddress[]) {
  jest.spyOn(addressesQueryModule, "useCustomerAddressesQuery").mockReturnValue({
    data, isPending: false, isError: false, refetch: jest.fn(),
  } as unknown as ReturnType<typeof addressesQueryModule.useCustomerAddressesQuery>);
}

function mockDetail(data: CustomerSavedAddress | undefined, isPending = false, isError = false) {
  jest.spyOn(detailQueryModule, "useCustomerAddressDetailQuery").mockReturnValue({
    data, isPending, isError, refetch: jest.fn(),
  } as unknown as ReturnType<typeof detailQueryModule.useCustomerAddressDetailQuery>);
}

function render() {
  return renderWithProviders(<AddressFormScreen />);
}

/**
 * Add mode now leads with address search and reveals the fields once there is a place
 * to attach them to (or once the customer says they would rather type it). Tests that
 * are about the FIELDS take the manual escape so they are not also testing the lookup.
 */
function renderWithFields() {
  const screen = render();
  const manual = screen.queryByLabelText("Enter address manually");
  if (manual) fireEvent.press(manual);
  return screen;
}

describe("AddressFormScreen", () => {
  afterEach(() => {
    jest.restoreAllMocks();
    mockNavigate.mockClear();
    mockGoBack.mockClear();
    mockRouteName = "AddAddress";
    mockRouteParams = {};
  });

  describe("Add mode", () => {
    beforeEach(() => {
      mockAddressesList([address()]);
      mockDetail(undefined);
    });

    it("shows the Add-mode header copy", () => {
      const { getByText } = render();
      expect(getByText("Add address")).toBeTruthy();
      expect(getByText("Save an address for future service requests")).toBeTruthy();
    });

    it("disables Save until required fields are valid", () => {
      const { getByLabelText } = render();
      const saveButton = getByLabelText("Save address");
      expect(saveButton.props.accessibilityState.disabled).toBe(true);
    });

    it("forces default-on and explains why when this is the customer's first address", () => {
      mockAddressesList([]);
      const { getByLabelText, getByText } = render();
      const toggle = getByLabelText("Make this my default address");
      expect(toggle.props.accessibilityState.checked).toBe(true);
      expect(toggle.props.accessibilityState.disabled).toBe(true);
      expect(getByText("Your first saved address is automatically your default.")).toBeTruthy();
    });

    it("leads with search and keeps the fields back until there is a place", () => {
      // People filled every field by hand and never touched the search, so the lookup
      // that supplies city, state, PIN and coordinates went unused and addresses were
      // saved with no point on the map.
      const { getByLabelText, queryByLabelText, getByText } = render();
      expect(getByLabelText("Search your address")).toBeTruthy();
      expect(queryByLabelText("House, flat, or floor")).toBeNull();
      expect(getByText(/Search for your area or building/)).toBeTruthy();
    });

    it("never traps someone who would rather type it", () => {
      const { getByLabelText, queryByLabelText } = render();
      fireEvent.press(getByLabelText("Enter address manually"));
      expect(queryByLabelText("House, flat, or floor")).toBeTruthy();
    });

    it("submits an allowlisted create payload and navigates back on success", async () => {
      const mutateAsync = jest.fn().mockResolvedValue({ data: address() });
      jest.spyOn(createMutationModule, "useCreateAddressMutation").mockReturnValue({
        mutateAsync, isPending: false,
      } as unknown as ReturnType<typeof createMutationModule.useCreateAddressMutation>);

      const { getByLabelText, getByText } = renderWithFields();
      fireEvent.changeText(getByLabelText("House, flat, or floor"), "House 24");
      fireEvent.changeText(getByLabelText("City"), "Ludhiana");
      fireEvent.changeText(getByLabelText("State"), "Punjab");
      fireEvent.changeText(getByLabelText("PIN code"), "141002");
      fireEvent.press(getByText("Save address"));

      await waitFor(() => expect(mutateAsync).toHaveBeenCalled());
      const payload = mutateAsync.mock.calls[0][0];
      expect(payload).toMatchObject({
        address_line_1: "House 24", city: "Ludhiana", state: "Punjab", zipcode: "141002",
      });
      expect(payload).not.toHaveProperty("serviceable");
      await waitFor(() => expect(mockGoBack).toHaveBeenCalled());
    });

    it("shows the 6-digit valid indicator only for a valid PIN", () => {
      const { getByLabelText, getByText, queryByText } = renderWithFields();
      expect(queryByText("6-digit valid")).toBeNull();
      fireEvent.changeText(getByLabelText("PIN code"), "141002");
      expect(getByText("6-digit valid")).toBeTruthy();
    });

    it("never renders maps, GPS, or coordinate text", () => {
      const { queryByText } = render();
      expect(queryByText(/latitude|longitude|GPS/i)).toBeNull();
    });

    it("shows the confirmed-booking-snapshot disclosure", () => {
      const { getByText } = render();
      expect(getByText("Confirmed bookings stay unchanged")).toBeTruthy();
    });
  });

  describe("Edit mode", () => {
    beforeEach(() => {
      mockRouteName = "EditAddress";
      mockRouteParams = { addressId: "a-1" };
      mockAddressesList([address()]);
    });

    it("loads the owned address by id, not a value passed through navigation params", () => {
      mockDetail(address({ landmark: "Near Bus Stand" }));
      const { getByText, getByDisplayValue } = render();
      expect(getByText("Edit address")).toBeTruthy();
      expect(getByDisplayValue("Near Bus Stand")).toBeTruthy();
    });

    it("shows a loading state while the owned address is being fetched", () => {
      mockDetail(undefined, true);
      const { getByText } = render();
      expect(getByText("Loading address")).toBeTruthy();
    });

    it("shows a recoverable error state when the address fails to load", () => {
      mockDetail(undefined, false, true);
      const { getByText } = render();
      expect(getByText("We couldn't load this address")).toBeTruthy();
    });

    it("disables Save Changes until the form is actually dirty", () => {
      mockDetail(address());
      const { getByLabelText } = render();
      const saveButton = getByLabelText("Save changes");
      expect(saveButton.props.accessibilityState.disabled).toBe(true);
    });

    it("forces the default toggle on and explains why when editing the current default address", () => {
      mockDetail(address({ isDefault: true }));
      const { getByLabelText, getByText } = render();
      const toggle = getByLabelText("Make this my default address");
      expect(toggle.props.accessibilityState.checked).toBe(true);
      expect(toggle.props.accessibilityState.disabled).toBe(true);
      expect(getByText("This is your default address. Set another address as default to change it.")).toBeTruthy();
    });

    it("submits only the changed fields on save", async () => {
      mockDetail(address());
      const mutateAsync = jest.fn().mockResolvedValue({ data: address() });
      jest.spyOn(updateMutationModule, "useUpdateAddressMutation").mockReturnValue({
        mutateAsync, isPending: false,
      } as unknown as ReturnType<typeof updateMutationModule.useUpdateAddressMutation>);

      const { getByLabelText, getByText } = render();
      fireEvent.changeText(getByLabelText("Landmark, optional"), "Near Bus Stand");
      fireEvent.press(getByText("Save changes"));

      await waitFor(() => expect(mutateAsync).toHaveBeenCalledWith({ landmark: "Near Bus Stand" }));
    });

    it("prompts to discard unsaved changes on back, but exits immediately when clean", () => {
      mockDetail(address());
      const alertSpy = jest.spyOn(Alert, "alert").mockImplementation(() => {});
      const { getByLabelText, getAllByLabelText } = render();

      fireEvent.press(getAllByLabelText("Go back")[0]);
      expect(alertSpy).not.toHaveBeenCalled();
      expect(mockGoBack).toHaveBeenCalledTimes(1);

      fireEvent.changeText(getByLabelText("Landmark, optional"), "Changed");
      fireEvent.press(getAllByLabelText("Go back")[0]);
      expect(alertSpy).toHaveBeenCalledWith(
        "Discard changes?", "Your unsaved address changes will be lost.", expect.any(Array),
      );
    });
  });
});
