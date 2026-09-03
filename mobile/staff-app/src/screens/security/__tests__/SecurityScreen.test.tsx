import React from "react";
import { render, screen, fireEvent } from "@testing-library/react-native";
import { ThemeProvider } from "../../../design-system/themes";
import { SecurityScreen } from "../SecurityScreen";
import { SecuritySummaryDTO } from "../../../services/auth/securityApi";

jest.mock("../useSecurity");
jest.mock("../../../hooks/useNetworkStatus", () => ({ useNetworkStatus: jest.fn(() => ({ meta: { readiness: "production_ready" }, networkState: "online", cacheState: "fresh", pendingDrafts: 0, syncState: "idle" })) }));

import { useSecurity } from "../useSecurity";
import { useNetworkStatus } from "../../../hooks/useNetworkStatus";

const mockNavigate = jest.fn();
const navigation = { navigate: mockNavigate, goBack: jest.fn() } as any;
const route = { params: undefined } as any;

const PROTECTED: SecuritySummaryDTO = {
  security_status: { level: "protected", label: "Your account is protected", reasons: [] },
  password: { configured: true, changed_at: "2026-06-19T10:30:00Z", change_allowed: true },
  mfa: { enabled: true, method: "totp", enabled_at: "2026-05-01T00:00:00Z", recovery_codes_remaining: 8, required_by_policy: false },
  current_device: { session_id: "s1", trusted: true, device_name: "This Android device", last_active_at: "2026-07-31T09:12:00Z" },
  verified_contacts: { masked_mobile: "••••• 12345", mobile_verified: true, masked_email: "a•••@example.com", email_verified: true },
  active_session_count: 2,
  recent_activity: [
    { event_id: "e1", label: "Successful sign-in", outcome: "successful", channel: "Mobile", device_name: "This Android device", is_current_device: true, occurred_at: "2026-07-31T09:12:00Z" },
  ],
};

function baseHookReturn(overrides: Partial<ReturnType<typeof useSecurity>> = {}) {
  return { data: PROTECTED, isLoading: false, isError: false, error: null, isRefetching: false, refetch: jest.fn(), invalidate: jest.fn(), ...overrides };
}

function renderScreen() {
  return render(<ThemeProvider><SecurityScreen route={route} navigation={navigation} /></ThemeProvider>);
}

beforeEach(() => {
  jest.clearAllMocks();
  (useNetworkStatus as jest.Mock).mockReturnValue({ meta: { readiness: "production_ready" }, networkState: "online", cacheState: "fresh", pendingDrafts: 0, syncState: "idle" });
});

describe("SecurityScreen (Phase V)", () => {
  it("renders the backend-derived security status, never a decorative default", () => {
    (useSecurity as jest.Mock).mockReturnValue(baseHookReturn());
    renderScreen();
    expect(screen.getByText("Your account is protected")).toBeTruthy();
    expect(screen.getByText("Protected")).toBeTruthy();
  });

  it("renders sign-in security, verified contact and sessions from real data", () => {
    (useSecurity as jest.Mock).mockReturnValue(baseHookReturn());
    renderScreen();
    expect(screen.getByText("Enabled")).toBeTruthy();
    expect(screen.getByText("••••• 12345")).toBeTruthy();
    expect(screen.getByText("a•••@example.com")).toBeTruthy();
    expect(screen.getByText("2 signed-in devices")).toBeTruthy();
  });

  it("navigates to MFA management when two-step verification is already enabled", () => {
    (useSecurity as jest.Mock).mockReturnValue(baseHookReturn());
    renderScreen();
    fireEvent.press(screen.getByText("Two-step verification"));
    expect(mockNavigate).toHaveBeenCalledWith("MFAManagement");
  });

  it("navigates to MFA setup when two-step verification is not enabled", () => {
    (useSecurity as jest.Mock).mockReturnValue(baseHookReturn({ data: { ...PROTECTED, mfa: { ...PROTECTED.mfa, enabled: false } } }));
    renderScreen();
    fireEvent.press(screen.getByText("Two-step verification"));
    expect(mockNavigate).toHaveBeenCalledWith("MFASetup");
  });

  it("shows the footer notice about never asking for password or OTP", () => {
    (useSecurity as jest.Mock).mockReturnValue(baseHookReturn());
    renderScreen();
    expect(screen.getByText("Fuvay will never ask for your password or OTP.")).toBeTruthy();
  });

  it("shows an offline banner", () => {
    (useNetworkStatus as jest.Mock).mockReturnValue({ meta: { readiness: "production_ready" }, networkState: "offline", cacheState: "fresh", pendingDrafts: 0, syncState: "idle" });
    (useSecurity as jest.Mock).mockReturnValue(baseHookReturn());
    renderScreen();
    expect(screen.getByText("Offline")).toBeTruthy();
  });

  it("shows a loading skeleton, then an error state on failure", () => {
    (useSecurity as jest.Mock).mockReturnValue(baseHookReturn({ data: undefined, isLoading: true }));
    const { rerender } = renderScreen();
    expect(screen.queryByText("Your account is protected")).toBeNull();

    (useSecurity as jest.Mock).mockReturnValue(baseHookReturn({ data: undefined, isLoading: false, isError: true, error: { code: "VALIDATION_ERROR", category: "network", safeMessage: "Network error", retryable: true } }));
    rerender(<ThemeProvider><SecurityScreen route={route} navigation={navigation} /></ThemeProvider>);
    expect(screen.getByText("Couldn't load security status")).toBeTruthy();
  });
});
