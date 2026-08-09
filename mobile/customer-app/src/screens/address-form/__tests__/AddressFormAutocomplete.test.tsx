import React from "react";
import { fireEvent, waitFor } from "@testing-library/react-native";
import { renderWithProviders } from "../../../testing/renderWithProviders";
import { AddressFormScreen } from "../AddressFormScreen";
import * as addressesQueryModule from "../../../api/customerAddresses/useCustomerAddressesQuery";
import * as detailQueryModule from "../../../api/customerAddresses/useCustomerAddressDetailQuery";
import * as createMutationModule from "../../../api/customerAddresses/useCreateAddressMutation";
import * as placesApi from "../../../api/places/placesApi";

jest.mock("../../../api/places/placesApi");

jest.mock("@react-navigation/native", () => ({
  ...jest.requireActual("@react-navigation/native"),
  useNavigation: () => ({ navigate: jest.fn(), goBack: jest.fn() }),
  useRoute: () => ({ name: "AddAddress", params: {} }),
}));

const suggest = placesApi.suggestAddresses as jest.Mock;
const resolve = placesApi.resolveAddress as jest.Mock;

const mutateAsync = jest.fn();

function mockScreenQueries() {
  jest.spyOn(addressesQueryModule, "useCustomerAddressesQuery").mockReturnValue({
    data: [], isPending: false, isError: false, refetch: jest.fn(),
  } as unknown as ReturnType<typeof addressesQueryModule.useCustomerAddressesQuery>);
  jest.spyOn(detailQueryModule, "useCustomerAddressDetailQuery").mockReturnValue({
    data: undefined, isPending: false, isError: false, refetch: jest.fn(),
  } as unknown as ReturnType<typeof detailQueryModule.useCustomerAddressDetailQuery>);
  jest.spyOn(createMutationModule, "useCreateAddressMutation").mockReturnValue({
    mutateAsync, isPending: false,
  } as unknown as ReturnType<typeof createMutationModule.useCreateAddressMutation>);
}

describe("AddressFormScreen address lookup", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockScreenQueries();
    suggest.mockResolvedValue({
      data: {
        configured: true,
        suggestions: [{ place_id: "p-1", description: "Bassi Pathana, Punjab, India" }],
      },
    });
  });

  afterEach(() => jest.restoreAllMocks());

  it("hides the search field entirely when the deployment has no Places key", async () => {
    // A search box that can never return anything reads as a broken app.
    suggest.mockResolvedValue({ data: { configured: false, suggestions: [] } });
    const { getByLabelText, queryByLabelText } = renderWithProviders(<AddressFormScreen />);

    fireEvent.changeText(getByLabelText("Search your address"), "Bassi");
    await waitFor(() => expect(suggest).toHaveBeenCalled(), { timeout: 4000 });
    await waitFor(() => expect(queryByLabelText("Search your address")).toBeNull(), { timeout: 4000 });
  });

  it("fills the form from a chosen suggestion and carries the coordinates into the payload", async () => {
    resolve.mockResolvedValue({
      data: {
        resolved: true,
        address: {
          formatted_address: "House 24, Bassi Pathana, Punjab 140412, India",
          line1: "House 24", city: "Bassi Pathana", state: "Punjab",
          zipcode: "140412", latitude: 30.6861187, longitude: 76.4042404,
        },
      },
    });
    const { getByLabelText, getByText, getByDisplayValue } = renderWithProviders(<AddressFormScreen />);

    fireEvent.changeText(getByLabelText("Search your address"), "Bassi");
    await waitFor(() => expect(getByText("Bassi Pathana, Punjab, India")).toBeTruthy(), { timeout: 4000 });
    fireEvent.press(getByText("Bassi Pathana, Punjab, India"));

    await waitFor(() => expect(resolve).toHaveBeenCalledWith("p-1", expect.any(String)));
    await waitFor(() => expect(getByDisplayValue("House 24")).toBeTruthy());

    fireEvent.press(getByText("Save address"));
    await waitFor(() => expect(mutateAsync).toHaveBeenCalled());
    expect(mutateAsync).toHaveBeenCalledWith(expect.objectContaining({
      address_line_1: "House 24", city: "Bassi Pathana", state: "Punjab",
      zipcode: "140412", latitude: 30.6861187, longitude: 76.4042404,
    }));
  });

  it("never invents a PIN code the lookup did not return", async () => {
    // Rural Indian localities frequently have no postal_code, and the PIN decides
    // serviceability -- so it stays empty and blocks save until entered by hand.
    resolve.mockResolvedValue({
      data: {
        resolved: true,
        address: {
          formatted_address: "Bassi Pathana, Punjab, India", line1: "Bassi Pathana",
          city: "Bassi Pathana", state: "Punjab",
          zipcode: null, latitude: 30.6861187, longitude: 76.4042404,
        },
      },
    });
    const { getByLabelText, getByText } = renderWithProviders(<AddressFormScreen />);

    fireEvent.changeText(getByLabelText("Search your address"), "Bassi");
    await waitFor(() => expect(getByText("Bassi Pathana, Punjab, India")).toBeTruthy());
    fireEvent.press(getByText("Bassi Pathana, Punjab, India"));

    await waitFor(() => expect(getByText("PIN code is required.")).toBeTruthy(), { timeout: 4000 });
    fireEvent.press(getByText("Save address"));
    expect(mutateAsync).not.toHaveBeenCalled();
  });
});
