import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react-native";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ThemeProvider } from "../../../design-system/themes";
import { ActiveSessionsScreen } from "../ActiveSessionsScreen";
import { SessionListResponseDTO } from "../../../services/auth/types";

jest.mock("../../../services/auth/authApi");
jest.mock("../../../services/auth/securityApi");
jest.mock("../../../hooks/useNetworkStatus", () => ({ useNetworkStatus: jest.fn(() => "online") }));

import * as authApi from "../../../services/auth/authApi";
import * as securityApi from "../../../services/auth/securityApi";
import { useNetworkStatus } from "../../../hooks/useNetworkStatus";

const navigation = { navigate: jest.fn(), goBack: jest.fn() } as any;
const route = { params: undefined } as any;

const DATA: SessionListResponseDTO = {
  total: 2, current_session_id: "s1", total_sessions: 2, trusted_device_count: 1,
  sessions: [
    { session_id: "s1", device_name: "Samsung Galaxy S24", device_display_name: "Samsung Galaxy S24", device_type: "ServiceOS Staff · Android 16", is_trusted: true, approximate_location: "Ludhiana", last_active_at: new Date().toISOString(), created_at: "2026-07-31T00:00:00Z", is_current: true, allowed_actions: ["view", "remove_trust"] },
    { session_id: "s2", device_name: "Chrome on Windows", device_display_name: "Chrome on Windows", device_type: "Windows 11 · Chrome 150", is_trusted: false, approximate_location: "Ludhiana", last_active_at: "2026-07-31T07:00:00Z", created_at: "2026-07-28T00:00:00Z", is_current: false, allowed_actions: ["view", "revoke"] },
  ],
};

function wrapper() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return ({ children }: { children: React.ReactNode }) => <QueryClientProvider client={client}><ThemeProvider>{children}</ThemeProvider></QueryClientProvider>;
}

function renderScreen() {
  const Wrapper = wrapper();
  return render(<Wrapper><ActiveSessionsScreen route={route} navigation={navigation} /></Wrapper>);
}

beforeEach(() => {
  jest.clearAllMocks();
  (useNetworkStatus as jest.Mock).mockReturnValue("online");
  (authApi.listSessions as jest.Mock).mockResolvedValue({ ok: true, data: DATA });
});

describe("ActiveSessionsScreen (Phase W)", () => {
  it("renders the current device with 'This device' and 'Trusted' pills", async () => {
    renderScreen();
    expect(await screen.findByText("Samsung Galaxy S24")).toBeTruthy();
    expect(screen.getByText("This device")).toBeTruthy();
    expect(screen.getAllByText("Trusted").length).toBeGreaterThanOrEqual(1);
  });

  it("renders other sessions with a Sign out action and Not trusted state", async () => {
    renderScreen();
    expect(await screen.findByText("Chrome on Windows")).toBeTruthy();
    expect(screen.getByText("Not trusted")).toBeTruthy();
    expect(screen.getByText("Sign out")).toBeTruthy();
  });

  it("never shows a revoke-current-session button next to the current device", async () => {
    renderScreen();
    await screen.findByText("Samsung Galaxy S24");
    // Only one "Sign out" button total -- it belongs to the other session, not the current one.
    expect(screen.getAllByText("Sign out").length).toBe(1);
  });

  it("confirms then revokes a single other session", async () => {
    (authApi.revokeSession as jest.Mock).mockResolvedValue({ ok: true, data: { session_id: "s2", revoked: true } });
    renderScreen();
    await screen.findByText("Chrome on Windows");
    fireEvent.press(screen.getByText("Sign out"));
    const buttons = await screen.findAllByText("Sign out");
    fireEvent.press(buttons[buttons.length - 1]);
    await waitFor(() => expect(authApi.revokeSession).toHaveBeenCalledWith("s2"));
  });

  it("shows the trusted-device count and footer notice", async () => {
    renderScreen();
    await screen.findByText("Samsung Galaxy S24");
    expect(screen.getByText("1")).toBeTruthy();
    expect(screen.getByText("Session changes are recorded in your security activity.")).toBeTruthy();
  });

  it("opens the current-device menu and removes trust", async () => {
    (securityApi.removeDeviceTrust as jest.Mock).mockResolvedValue({ ok: true, data: { session_id: "s1", is_trusted: false } });
    renderScreen();
    await screen.findByText("Samsung Galaxy S24");
    fireEvent.press(screen.getByLabelText("Device options"));
    fireEvent.press(screen.getByText("Remove trust"));
    await waitFor(() => expect(securityApi.removeDeviceTrust).toHaveBeenCalledWith("s1"));
  });

  it("disables bulk sign-out and shows a warning when current session can't be resolved", async () => {
    (authApi.listSessions as jest.Mock).mockResolvedValue({ ok: true, data: { ...DATA, current_session_id: null } });
    renderScreen();
    await screen.findByText("Chrome on Windows");
    expect(screen.getByText("Current device unknown")).toBeTruthy();
  });

  it("shows an offline banner", async () => {
    (useNetworkStatus as jest.Mock).mockReturnValue("offline");
    renderScreen();
    expect(await screen.findByText("Offline")).toBeTruthy();
  });

  it("shows a loading skeleton, then an error state on failure", async () => {
    (authApi.listSessions as jest.Mock).mockResolvedValue({ ok: false, error: { code: "VALIDATION_ERROR", category: "network", safeMessage: "Network error", retryable: true } });
    renderScreen();
    await waitFor(() => expect(screen.getByText("Couldn't load sessions")).toBeTruthy());
  });
});
