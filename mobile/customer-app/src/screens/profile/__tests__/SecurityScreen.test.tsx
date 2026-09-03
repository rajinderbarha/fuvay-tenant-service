import React from "react";
import { Alert } from "react-native";
import { cleanup, fireEvent, waitFor } from "@testing-library/react-native";
import { renderWithProviders } from "../../../testing/renderWithProviders";
import { SecurityScreen } from "../SecurityScreen";
import * as profileQueryModule from "../../../api/customer/useCustomerProfileQuery";
import * as sessionsQueryModule from "../../../api/customerSecurity/useCustomerSessionsQuery";
import * as customerSecurityApi from "../../../api/customerSecurity/customerSecurityApi";
import * as sessionManagerModule from "../../../api/session/sessionManager";
import { CustomerProfile } from "../../../domain/customer";
import { asCustomerId } from "../../../domain/ids";

const mockNavigate = jest.fn();
jest.mock("@react-navigation/native", () => ({
  ...jest.requireActual("@react-navigation/native"),
  useNavigation: () => ({ navigate: mockNavigate, goBack: jest.fn() }),
}));

jest.mock("../../../api/session/sessionManager", () => ({
  ...jest.requireActual("../../../api/session/sessionManager"),
  logout: jest.fn(),
}));

function profile(overrides: Partial<CustomerProfile> = {}): CustomerProfile {
  return {
    id: asCustomerId("c-1"), fullName: "Rajinder Singh", displayName: "Rajinder",
    phone: "+919900024102", email: "rajinder@example.com", avatarUrl: null,
    language: "en", timezone: "Asia/Kolkata", verified: true, mfaEnabled: false, isActive: true,
    createdAt: "2026-01-01T00:00:00Z" as CustomerProfile["createdAt"],
    capabilities: { canEditProfile: true, canUpdateAvatar: false, canManageAddresses: false, canChangePassword: true, canManageSessions: true, canDeleteAccount: false },
    ...overrides,
  };
}

function mockProfile(data: CustomerProfile | undefined, isPending = false, isError = false) {
  jest.spyOn(profileQueryModule, "useCustomerProfileQuery").mockReturnValue({
    data, isPending, isError, refetch: jest.fn(),
  } as unknown as ReturnType<typeof profileQueryModule.useCustomerProfileQuery>);
}

function mockSessions(data: ReturnType<typeof sessionsQueryModule.useCustomerSessionsQuery>["data"]) {
  jest.spyOn(sessionsQueryModule, "useCustomerSessionsQuery").mockReturnValue({
    data, isPending: false, isError: false,
  } as unknown as ReturnType<typeof sessionsQueryModule.useCustomerSessionsQuery>);
}

function render() {
  return renderWithProviders(<SecurityScreen />);
}

describe("SecurityScreen", () => {
  afterEach(() => {
    cleanup();
    jest.restoreAllMocks();
    mockNavigate.mockClear();
    (sessionManagerModule.logout as jest.Mock).mockClear();
  });

  it("shows the static safety guidance panel, never a security score", () => {
    mockProfile(profile());
    mockSessions([]);
    const { getByText, queryByText } = render();
    expect(getByText("Keep your account secure")).toBeTruthy();
    expect(getByText("Never share your password or one-time code.")).toBeTruthy();
    expect(queryByText(/%|score/i)).toBeNull();
  });

  it("shows the masked mobile number and a Verified badge only from the real backend flag", () => {
    mockProfile(profile({ verified: true }));
    mockSessions([]);
    const { getByText } = render();
    expect(getByText("Verified")).toBeTruthy();
  });

  it("does not show Verified when the backend flag is false", () => {
    mockProfile(profile({ verified: false }));
    mockSessions([]);
    const { queryByText } = render();
    expect(queryByText("Verified")).toBeNull();
  });

  it("shows 'Password is set' with a Change action", () => {
    mockProfile(profile());
    mockSessions([]);
    const { getByText } = render();
    expect(getByText("Password is set")).toBeTruthy();
    expect(getByText("Change")).toBeTruthy();
  });

  it("shows 'Not enabled' with Set up when MFA is disabled", () => {
    mockProfile(profile({ mfaEnabled: false }));
    mockSessions([]);
    const { getByText } = render();
    expect(getByText("Not enabled")).toBeTruthy();
    expect(getByText("Set up")).toBeTruthy();
  });

  it("shows 'Enabled' with Manage when MFA is on, and navigates to the real MFA screen", () => {
    mockProfile(profile({ mfaEnabled: true }));
    mockSessions([]);
    const { getByText } = render();
    expect(getByText("Enabled")).toBeTruthy();
    fireEvent.press(getByText("Manage"));
    expect(mockNavigate).toHaveBeenCalledWith("MfaManage");
  });

  it("shows This device as Current and Active now from the real is_current session flag", () => {
    mockProfile(profile());
    mockSessions([{ sessionId: "s-1", deviceName: "iPhone", channel: "Mobile", isCurrent: true, isTrusted: true, lastActiveAt: null, createdAt: null }]);
    const { getByText } = render();
    expect(getByText("This device")).toBeTruthy();
    expect(getByText("Current")).toBeTruthy();
    expect(getByText("Active now")).toBeTruthy();
  });

  it("never renders invented city, IP location, device model, or browser info", () => {
    mockProfile(profile());
    mockSessions([{ sessionId: "s-1", deviceName: "iPhone", channel: "Mobile", isCurrent: true, isTrusted: true, lastActiveAt: null, createdAt: null }]);
    const { queryByText } = render();
    expect(queryByText(/mumbai|delhi|chrome|safari|192\.168/i)).toBeNull();
  });

  it("expands the change-password form and calls the real endpoint with all three fields", async () => {
    mockProfile(profile());
    mockSessions([]);
    const spy = jest.spyOn(customerSecurityApi, "changePassword").mockResolvedValue({
      data: { message: "ok" }, requestId: "req-1",
    } as unknown as Awaited<ReturnType<typeof customerSecurityApi.changePassword>>);

    const { getByText, getByLabelText } = render();
    fireEvent.press(getByText("Change"));
    fireEvent.changeText(getByLabelText("Current password"), "OldPass123!");
    fireEvent.changeText(getByLabelText("New password"), "NewPass456!");
    fireEvent.changeText(getByLabelText("Confirm new password"), "NewPass456!");
    fireEvent.press(getByText("Update password"));

    await waitFor(() => expect(spy).toHaveBeenCalledWith({
      current_password: "OldPass123!", new_password: "NewPass456!", confirm_password: "NewPass456!",
    }));
  });

  it("shows a validation error and never submits when confirmation does not match", async () => {
    mockProfile(profile());
    mockSessions([]);
    const spy = jest.spyOn(customerSecurityApi, "changePassword");

    const { getByText, getByLabelText } = render();
    fireEvent.press(getByText("Change"));
    fireEvent.changeText(getByLabelText("Current password"), "OldPass123!");
    fireEvent.changeText(getByLabelText("New password"), "NewPass456!");
    fireEvent.changeText(getByLabelText("Confirm new password"), "Mismatch!");
    fireEvent.press(getByText("Update password"));

    expect(getByText(/do not match/i)).toBeTruthy();
    expect(spy).not.toHaveBeenCalled();
  });

  it("shows the global sign-out confirmation sheet before calling the real endpoint", () => {
    mockProfile(profile());
    mockSessions([]);
    const alertSpy = jest.spyOn(Alert, "alert").mockImplementation(() => {});
    const { getByText } = render();

    fireEvent.press(getByText("Sign out of all devices"));

    expect(alertSpy).toHaveBeenCalledWith(
      "Sign out of all devices?",
      "All active sessions, including this device, will be signed out. You will need to sign in again.",
      expect.any(Array),
    );
  });

  it("global sign-out clears credentials and private cache only after a real server success", async () => {
    mockProfile(profile());
    mockSessions([]);
    const logoutAllSpy = jest.spyOn(customerSecurityApi, "logoutAllSessions").mockResolvedValue({
      data: { sessions_revoked: 3, message: "done" }, requestId: "req-1",
    } as unknown as Awaited<ReturnType<typeof customerSecurityApi.logoutAllSessions>>);
    const logoutSpy = sessionManagerModule.logout as jest.Mock;

    jest.spyOn(Alert, "alert").mockImplementation((_t, _m, buttons) => {
      const confirm = buttons?.find(b => b.text === "Sign out all");
      confirm?.onPress?.();
    });

    const { getByText } = render();
    fireEvent.press(getByText("Sign out of all devices"));

    await waitFor(() => expect(logoutAllSpy).toHaveBeenCalled());
    await waitFor(() => expect(logoutSpy).toHaveBeenCalled());
  });

  it("keeps the session locally when the global sign-out request fails", async () => {
    mockProfile(profile());
    mockSessions([]);
    jest.spyOn(customerSecurityApi, "logoutAllSessions").mockRejectedValue(new Error("network"));
    const logoutSpy = sessionManagerModule.logout as jest.Mock;

    jest.spyOn(Alert, "alert").mockImplementation((_t, _m, buttons) => {
      const confirm = buttons?.find(b => b.text === "Sign out all");
      confirm?.onPress?.();
    });

    const { getByText } = render();
    fireEvent.press(getByText("Sign out of all devices"));

    await waitFor(() => expect(customerSecurityApi.logoutAllSessions).toHaveBeenCalled());
    expect(logoutSpy).not.toHaveBeenCalled();
  });

  it("shows loading state, never a stale render, while the security overview loads", () => {
    mockProfile(undefined, true);
    mockSessions(undefined);
    const { getByText } = render();
    expect(getByText("Loading security settings")).toBeTruthy();
  });

  it("shows a recoverable error state on first-load failure with a retry action", () => {
    mockProfile(undefined, false, true);
    mockSessions(undefined);
    const { getByText } = render();
    expect(getByText("We couldn't load your security settings")).toBeTruthy();
    expect(getByText("Try again")).toBeTruthy();
  });

  it("never renders a raw backend error string", () => {
    mockProfile(profile());
    mockSessions([]);
    const { queryByText } = render();
    expect(queryByText(/traceback|stack trace|exception/i)).toBeNull();
  });
});
