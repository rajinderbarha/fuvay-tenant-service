import React from "react";
import { Alert } from "react-native";
import { fireEvent, waitFor } from "@testing-library/react-native";
import { NavigationContainer } from "@react-navigation/native";
import { renderWithProviders } from "../../../testing/renderWithProviders";
import { ProfileScreen } from "../ProfileScreen";
import * as profileQueryModule from "../../../api/customer/useCustomerProfileQuery";
import * as addressesQueryModule from "../../../api/customerAddresses/useCustomerAddressesQuery";
import * as sessionManager from "../../../api/session/sessionManager";
import { asCustomerId } from "../../../domain/ids";

jest.mock("../../../api/session/sessionManager", () => ({
  ...jest.requireActual("../../../api/session/sessionManager"),
  logout: jest.fn(),
}));

function baseProfile(overrides: Partial<Record<string, unknown>> = {}) {
  return {
    id: asCustomerId("c-1"), fullName: "Priya Sharma", displayName: "Priya", phone: "+919900000000",
    email: "priya@example.com", avatarUrl: null, language: "en", timezone: "Asia/Kolkata",
    verified: true, isActive: true, createdAt: "2026-01-01T00:00:00Z",
    capabilities: { canEditProfile: true, canUpdateAvatar: false, canManageAddresses: false, canChangePassword: true, canManageSessions: true, canDeleteAccount: false },
    ...overrides,
  };
}

function baseAddress(overrides: Partial<Record<string, unknown>> = {}) {
  return {
    id: "addr-1", label: "Home", recipientName: null, mobile: "+919900024102",
    line1: "House 24, Model Town", line2: null, landmark: null, city: "Ludhiana", district: null,
    state: "Punjab", country: "India", postalCode: "141002", isDefault: true,
    createdAt: "2026-01-01T00:00:00Z", updatedAt: null,
    ...overrides,
  };
}

function renderProfile() {
  return renderWithProviders(
    <NavigationContainer>
      <ProfileScreen />
    </NavigationContainer>,
  );
}

describe("ProfileScreen", () => {
  beforeEach(() => {
    jest.spyOn(profileQueryModule, "useCustomerProfileQuery").mockReturnValue({
      isPending: false, isError: false, data: baseProfile(), refetch: jest.fn(),
    } as unknown as ReturnType<typeof profileQueryModule.useCustomerProfileQuery>);
    jest.spyOn(addressesQueryModule, "useCustomerAddressesQuery").mockReturnValue({
      data: [baseAddress()], isPending: false, isError: false, refetch: jest.fn(),
    } as unknown as ReturnType<typeof addressesQueryModule.useCustomerAddressesQuery>);
    (sessionManager.logout as jest.Mock).mockResolvedValue(undefined);
  });
  afterEach(() => jest.restoreAllMocks());

  it("renders the real customer's own name and contact info, never sample data", () => {
    const { getByText } = renderProfile();
    expect(getByText("Priya")).toBeTruthy();
    expect(getByText("+919900000000")).toBeTruthy();
    expect(getByText("priya@example.com")).toBeTruthy();
  });

  it("shows a single combined Verified badge, never separate mobile/email verified badges", () => {
    const { getByText, queryByText } = renderProfile();
    expect(getByText("Verified")).toBeTruthy();
    expect(queryByText("Mobile verified")).toBeNull();
    expect(queryByText("Email verified")).toBeNull();
  });

  it("shows the real default address preview from the shared addresses query, not a temporary Home ZIP override", () => {
    const { getByText } = renderProfile();
    expect(getByText(/House 24, Model Town/)).toBeTruthy();
  });

  it("shows an honest 'no saved addresses' subtitle when the customer has none", () => {
    jest.spyOn(addressesQueryModule, "useCustomerAddressesQuery").mockReturnValue({
      data: [], isPending: false, isError: false, refetch: jest.fn(),
    } as unknown as ReturnType<typeof addressesQueryModule.useCustomerAddressesQuery>);
    const { getByText } = renderProfile();
    expect(getByText("No saved addresses yet")).toBeTruthy();
  });

  it("never renders unsupported features", () => {
    const { queryByText } = renderProfile();
    for (const forbidden of ["Wallet", "Rewards", "Membership", "Payment methods", "Referral", "Points"]) {
      expect(queryByText(new RegExp(forbidden, "i"))).toBeNull();
    }
  });

  it("calls the canonical session logout only after the customer confirms sign-out", async () => {
    const alertSpy = jest.spyOn(Alert, "alert").mockImplementation((_title, _msg, buttons) => {
      const confirm = buttons?.find(b => b.text === "Sign out");
      confirm?.onPress?.();
    });
    const { getByText } = renderProfile();
    fireEvent.press(getByText("Sign out"));
    await waitFor(() => expect(sessionManager.logout).toHaveBeenCalledTimes(1));
    alertSpy.mockRestore();
  });

  it("Fuvay Assistant language row is informational only, never a global app-language setting", () => {
    const { getByText } = renderProfile();
    expect(getByText("Fuvay Assistant language")).toBeTruthy();
    expect(getByText(/App interface remains in English/)).toBeTruthy();
  });
});
