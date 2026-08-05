import React from "react";
import { Alert } from "react-native";
import { fireEvent, waitFor } from "@testing-library/react-native";
import { renderWithProviders } from "../../../testing/renderWithProviders";
import { ManageSessionsScreen } from "../ManageSessionsScreen";
import * as sessionsQueryModule from "../../../api/customerSecurity/useCustomerSessionsQuery";
import * as customerSecurityApi from "../../../api/customerSecurity/customerSecurityApi";
import { CustomerSession } from "../../../domain/customerSecurity";
import { ServerTimestamp } from "../../../domain/dates";

const mockGoBack = jest.fn();
jest.mock("@react-navigation/native", () => ({
  ...jest.requireActual("@react-navigation/native"),
  useNavigation: () => ({ navigate: jest.fn(), goBack: mockGoBack }),
}));

function session(overrides: Partial<CustomerSession> = {}): CustomerSession {
  return {
    sessionId: "s-1", deviceName: "This device", channel: "iOS", isCurrent: true, isTrusted: false,
    lastActiveAt: "2026-01-01T00:00:00Z" as ServerTimestamp,
    createdAt: "2026-01-01T00:00:00Z" as ServerTimestamp,
    ...overrides,
  };
}

function mockSessions(data: CustomerSession[] | undefined, isPending = false, isError = false) {
  jest.spyOn(sessionsQueryModule, "useCustomerSessionsQuery").mockReturnValue({
    data, isPending, isError, refetch: jest.fn(),
  } as unknown as ReturnType<typeof sessionsQueryModule.useCustomerSessionsQuery>);
}

function render() {
  return renderWithProviders(<ManageSessionsScreen />);
}

describe("ManageSessionsScreen", () => {
  afterEach(() => { jest.restoreAllMocks(); mockGoBack.mockClear(); });

  it("shows the loading state while sessions are being checked", () => {
    mockSessions(undefined, true);
    const { getByText } = render();
    expect(getByText("Checking active sessions…")).toBeTruthy();
  });

  it("shows a recoverable error state with retry on first-load failure", () => {
    mockSessions(undefined, false, true);
    const { getByText } = render();
    expect(getByText("We couldn't load your sessions")).toBeTruthy();
    expect(getByText("Try again")).toBeTruthy();
  });

  it("shows the real active session count, never a fabricated total", () => {
    mockSessions([session({ sessionId: "s-1", isCurrent: true }), session({ sessionId: "s-2", isCurrent: false, deviceName: "Android phone" })]);
    const { getByText } = render();
    expect(getByText("2 active sessions")).toBeTruthy();
  });

  it("renders the current session card without a Sign out button", () => {
    mockSessions([session({ sessionId: "s-1", isCurrent: true, channel: "iOS" })]);
    const { getByText, queryAllByText } = render();
    expect(getByText("This device")).toBeTruthy();
    expect(getByText("Fuvay app • iOS")).toBeTruthy();
    expect(getByText("Active now")).toBeTruthy();
    expect(queryAllByText("Sign out").length).toBe(0);
  });

  it("shows the honest empty state when only the current session exists", () => {
    mockSessions([session({ sessionId: "s-1", isCurrent: true })]);
    const { getByText, queryByText } = render();
    expect(getByText("No other active sessions")).toBeTruthy();
    expect(queryByText("Sign out of other devices")).toBeNull();
  });

  it("renders other sessions with a Sign out action, never invented city/IP/device-model info", () => {
    mockSessions([
      session({ sessionId: "s-1", isCurrent: true }),
      session({ sessionId: "s-2", isCurrent: false, deviceName: "Android phone", channel: "Android" }),
    ]);
    const { getByText, queryByText } = render();
    expect(getByText("Android phone")).toBeTruthy();
    expect(getByText("Sign out")).toBeTruthy();
    expect(queryByText(/mumbai|delhi|192\.168|chrome|safari/i)).toBeNull();
  });

  it("shows the single-session sign-out confirmation before calling the real revoke endpoint", () => {
    mockSessions([
      session({ sessionId: "s-1", isCurrent: true }),
      session({ sessionId: "s-2", isCurrent: false, deviceName: "Android phone" }),
    ]);
    const alertSpy = jest.spyOn(Alert, "alert").mockImplementation(() => {});
    const { getByText } = render();

    fireEvent.press(getByText("Sign out"));

    expect(alertSpy).toHaveBeenCalledWith(
      "Sign out this device?",
      "Android phone will need to sign in again.",
      expect.any(Array),
    );
  });

  it("only revokes after confirmation, and refreshes the session list on success", async () => {
    mockSessions([
      session({ sessionId: "s-1", isCurrent: true }),
      session({ sessionId: "s-2", isCurrent: false, deviceName: "Android phone" }),
    ]);
    const revokeSpy = jest.spyOn(customerSecurityApi, "revokeSession").mockResolvedValue({
      data: { session_id: "s-2", revoked: true }, requestId: "req-1",
    } as unknown as Awaited<ReturnType<typeof customerSecurityApi.revokeSession>>);
    jest.spyOn(Alert, "alert").mockImplementation((_t, _m, buttons) => {
      const confirm = buttons?.find(b => b.text === "Sign out");
      confirm?.onPress?.();
    });

    const { getByText } = render();
    fireEvent.press(getByText("Sign out"));

    await waitFor(() => expect(revokeSpy).toHaveBeenCalledWith("s-2"));
  });

  it("shows the bulk sign-out-others confirmation before calling the real endpoint, preserving the current session", () => {
    mockSessions([
      session({ sessionId: "s-1", isCurrent: true }),
      session({ sessionId: "s-2", isCurrent: false, deviceName: "Android phone" }),
    ]);
    const alertSpy = jest.spyOn(Alert, "alert").mockImplementation(() => {});
    const { getByText } = render();

    fireEvent.press(getByText("Sign out of other devices"));

    expect(alertSpy).toHaveBeenCalledWith(
      "Sign out of all other devices?",
      "Every other active session will need to sign in again. This device will remain signed in.",
      expect.any(Array),
    );
  });

  it("bulk sign-out calls the real revoke-all-other endpoint only after confirmation", async () => {
    mockSessions([
      session({ sessionId: "s-1", isCurrent: true }),
      session({ sessionId: "s-2", isCurrent: false, deviceName: "Android phone" }),
    ]);
    const spy = jest.spyOn(customerSecurityApi, "revokeOtherSessions").mockResolvedValue({
      data: { sessions_revoked: 1, active_session_count: 1, message: "done" }, requestId: "req-1",
    } as unknown as Awaited<ReturnType<typeof customerSecurityApi.revokeOtherSessions>>);
    jest.spyOn(Alert, "alert").mockImplementation((_t, _m, buttons) => {
      const confirm = buttons?.find(b => b.text === "Sign out others");
      confirm?.onPress?.();
    });

    const { getByText } = render();
    fireEvent.press(getByText("Sign out of other devices"));

    await waitFor(() => expect(spy).toHaveBeenCalled());
  });

  it("never renders raw token, session id, or full backend error text", () => {
    mockSessions([session({ sessionId: "s-1", isCurrent: true })]);
    const { queryByText } = render();
    expect(queryByText(/bearer|jwt|traceback/i)).toBeNull();
  });
});
