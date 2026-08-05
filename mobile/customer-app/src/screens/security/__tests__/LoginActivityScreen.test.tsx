import React from "react";
import { fireEvent } from "@testing-library/react-native";
import { renderWithProviders } from "../../../testing/renderWithProviders";
import { LoginActivityScreen } from "../LoginActivityScreen";
import * as loginActivityQueryModule from "../../../api/customerSecurity/useLoginActivityQuery";
import { LoginActivityEvent } from "../../../domain/customerSecurity";
import { ServerTimestamp } from "../../../domain/dates";

const mockNavigate = jest.fn();
jest.mock("@react-navigation/native", () => ({
  ...jest.requireActual("@react-navigation/native"),
  useNavigation: () => ({ navigate: mockNavigate, goBack: jest.fn() }),
}));

function event(overrides: Partial<LoginActivityEvent> = {}): LoginActivityEvent {
  return {
    eventId: "e-1", label: "Successful sign-in", outcome: "successful", channel: "iOS",
    deviceName: "This device", isCurrentDevice: true,
    occurredAt: new Date().toISOString() as ServerTimestamp,
    ...overrides,
  };
}

function mockQuery(pages: { events: LoginActivityEvent[]; nextCursor: string | null }[] | undefined, opts: Partial<ReturnType<typeof loginActivityQueryModule.useLoginActivityQuery>> = {}) {
  jest.spyOn(loginActivityQueryModule, "useLoginActivityQuery").mockReturnValue({
    data: pages ? { pages, pageParams: [] } : undefined,
    isPending: false, isError: false, refetch: jest.fn(),
    hasNextPage: false, isFetchingNextPage: false, fetchNextPage: jest.fn(),
    ...opts,
  } as unknown as ReturnType<typeof loginActivityQueryModule.useLoginActivityQuery>);
}

function render() {
  return renderWithProviders(<LoginActivityScreen />);
}

describe("LoginActivityScreen", () => {
  afterEach(() => { jest.restoreAllMocks(); mockNavigate.mockClear(); });

  it("shows the loading state", () => {
    mockQuery(undefined, { isPending: true });
    const { getByText } = render();
    expect(getByText("Loading login activity…")).toBeTruthy();
  });

  it("shows a recoverable first-load error with retry", () => {
    mockQuery(undefined, { isPending: false, isError: true });
    const { getByText } = render();
    expect(getByText("We couldn't load your login activity.")).toBeTruthy();
    expect(getByText("Try again")).toBeTruthy();
  });

  it("shows the honest empty state, never a false safety claim", () => {
    mockQuery([{ events: [], nextCursor: null }]);
    const { getByText, queryByText } = render();
    expect(getByText("No login activity available")).toBeTruthy();
    expect(queryByText(/no suspicious activity|account is safe/i)).toBeNull();
  });

  it("renders a successful sign-in event with the current-device badge", () => {
    mockQuery([{ events: [event({ outcome: "successful", isCurrentDevice: true })], nextCursor: null }]);
    const { getByText } = render();
    expect(getByText("Successful sign-in")).toBeTruthy();
    expect(getByText("Current device")).toBeTruthy();
  });

  it("renders a verification-required event", () => {
    mockQuery([{ events: [event({ eventId: "e-2", label: "Additional verification required", outcome: "verification_required", isCurrentDevice: false })], nextCursor: null }]);
    const { getByText } = render();
    expect(getByText("Additional verification required")).toBeTruthy();
  });

  it("renders a blocked event with safe copy only, no raw failure reason", () => {
    mockQuery([{ events: [event({ eventId: "e-3", label: "Sign-in blocked", outcome: "blocked", deviceName: "Chrome", channel: "Web", isCurrentDevice: false })], nextCursor: null }]);
    const { getByText, queryByText } = render();
    expect(getByText("Sign-in blocked")).toBeTruthy();
    expect(queryByText(/wrong password|user not found|invalid credential/i)).toBeNull();
  });

  it("never renders raw IP, risk score, or backend event_type strings", () => {
    mockQuery([{ events: [event()], nextCursor: null }]);
    const { queryByText } = render();
    expect(queryByText(/192\.168|risk score|login_success|mfa_challenge_required/i)).toBeNull();
  });

  it("switches between All / Successful / Needs attention filters", () => {
    mockQuery([{ events: [event()], nextCursor: null }]);
    const { getByText } = render();
    fireEvent.press(getByText("Successful"));
    fireEvent.press(getByText("Needs attention"));
    fireEvent.press(getByText("All"));
    // No crash across filter switches -- the hook itself is mocked per test,
    // so this proves the tab control wires through without error.
    expect(getByText("All")).toBeTruthy();
  });

  it("groups events under Today", () => {
    mockQuery([{ events: [event({ occurredAt: new Date().toISOString() as ServerTimestamp })], nextCursor: null }]);
    const { getByText } = render();
    expect(getByText("Today")).toBeTruthy();
  });

  it("shows a Load more button only when a next page exists", () => {
    mockQuery([{ events: [event()], nextCursor: "cursor-1" }], { hasNextPage: true });
    const { getByText } = render();
    expect(getByText("Load more")).toBeTruthy();
  });

  it("navigates to Manage Sessions and Security (change password) via the remediation card", () => {
    mockQuery([{ events: [event()], nextCursor: null }]);
    const { getByText } = render();
    fireEvent.press(getByText("Review sessions"));
    expect(mockNavigate).toHaveBeenCalledWith("ManageSessions");
    fireEvent.press(getByText("Change password"));
    expect(mockNavigate).toHaveBeenCalledWith("Security");
  });

  it("shows the read-only disclosure and no delete/clear controls", () => {
    mockQuery([{ events: [event()], nextCursor: null }]);
    const { getByText, queryByText } = render();
    expect(getByText("Login history is read-only and cannot be deleted.")).toBeTruthy();
    expect(queryByText(/clear history|dismiss|mark as safe/i)).toBeNull();
    expect(queryByText("Delete")).toBeNull();
  });
});
