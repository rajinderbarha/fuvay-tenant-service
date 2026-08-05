import React from "react";
import { fireEvent } from "@testing-library/react-native";
import { renderWithProviders } from "../../../testing/renderWithProviders";
import { HelpSupportScreen } from "../HelpSupportScreen";

const mockTabNavigate = jest.fn();
const mockStackNavigate = jest.fn();

jest.mock("@react-navigation/native", () => ({
  ...jest.requireActual("@react-navigation/native"),
  useNavigation: () => ({ navigate: (...args: unknown[]) => { mockTabNavigate(...args); mockStackNavigate(...args); } }),
}));

function render() {
  return renderWithProviders(<HelpSupportScreen />);
}

describe("HelpSupportScreen", () => {
  afterEach(() => { mockTabNavigate.mockClear(); mockStackNavigate.mockClear(); });

  it("shows the real header copy", () => {
    const { getByText } = render();
    expect(getByText("Help & Support")).toBeTruthy();
    expect(getByText("Find answers or get the right help")).toBeTruthy();
  });

  it("never renders a search field -- no customer-facing knowledge search exists", () => {
    const { queryByPlaceholderText, queryByLabelText } = render();
    expect(queryByPlaceholderText("Search help topics")).toBeNull();
    expect(queryByLabelText("Search help topics")).toBeNull();
  });

  it("never renders a Popular help section -- no published-content source exists", () => {
    const { queryByText } = render();
    expect(queryByText("Popular help")).toBeNull();
    expect(queryByText("Featured help")).toBeNull();
  });

  it("never fabricates phone/email/emergency support entries", () => {
    const { queryByText } = render();
    expect(queryByText(/call support|email us|24\/7|emergency/i)).toBeNull();
  });

  it("Choose booking navigates to the booking picker in help mode", () => {
    const { getByText } = render();
    fireEvent.press(getByText("Choose booking"));
    expect(mockStackNavigate).toHaveBeenCalledWith("BookingSupportEntry", { mode: "help" });
  });

  it("Account & security navigates to the real Security screen", () => {
    const { getByText } = render();
    fireEvent.press(getByText("Account & security"));
    expect(mockStackNavigate).toHaveBeenCalledWith("Security");
  });

  it("Privacy & data navigates to the real Privacy & Data screen", () => {
    const { getByText } = render();
    fireEvent.press(getByText("Privacy & data"));
    expect(mockStackNavigate).toHaveBeenCalledWith("PrivacyData");
  });

  it("Safety & trust routes through the real booking-linked safety flow", () => {
    const { getByText } = render();
    fireEvent.press(getByText("Safety & trust"));
    expect(mockStackNavigate).toHaveBeenCalledWith("BookingSupportEntry", { mode: "safety" });
  });

  it("My support requests navigates to the real request list", () => {
    const { getByText } = render();
    fireEvent.press(getByText("My support requests"));
    expect(mockStackNavigate).toHaveBeenCalledWith("SupportRequests");
  });

  it("Create request opens Step 1 of the create-support-request wizard", () => {
    const { getByText } = render();
    fireEvent.press(getByText("Create request"));
    expect(mockStackNavigate).toHaveBeenCalledWith("CreateSupportRequest", { source: "help_hub" });
  });
});
