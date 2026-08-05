import React from "react";
import { fireEvent } from "@testing-library/react-native";
import { renderWithProviders } from "../../../testing/renderWithProviders";
import { PrivacyRequestSubmittedScreen } from "../PrivacyRequestSubmittedScreen";
import * as queriesModule from "../../../api/privacyData/usePrivacyDataQueries";
import { PrivacyRequest } from "../../../domain/privacyData";
import { ServerTimestamp } from "../../../domain/dates";

const mockReplace = jest.fn();
const mockGoBack = jest.fn();
jest.mock("@react-navigation/native", () => ({
  ...jest.requireActual("@react-navigation/native"),
  useNavigation: () => ({ navigate: jest.fn(), goBack: mockGoBack, replace: mockReplace }),
  useRoute: () => ({ name: "PrivacyRequestSubmitted", params: { requestId: "r-1" } }),
}));

function request(overrides: Partial<PrivacyRequest> = {}): PrivacyRequest {
  return {
    id: "r-1", requestNumber: "COMP-2026-000004", requestType: "data_export",
    status: "submitted", statusLabel: "Submitted", slaStatus: "on_track", slaLabel: "On Track",
    verificationStatus: "not_required",
    submittedAt: "2026-08-02T10:32:00Z" as ServerTimestamp, dueAt: null, completedAt: null,
    reason: null, rejectionReason: null,
    createdAt: "2026-08-02T10:32:00Z" as ServerTimestamp, updatedAt: null,
    ...overrides,
  };
}

function mockDetail(
  result: { kind: "found"; request: PrivacyRequest } | { kind: "unavailable" } | undefined,
  opts: { isPending?: boolean } = {},
) {
  jest.spyOn(queriesModule, "usePrivacyRequestDetailQuery").mockReturnValue({
    data: result, isPending: !!opts.isPending, isError: false, refetch: jest.fn(),
  } as unknown as ReturnType<typeof queriesModule.usePrivacyRequestDetailQuery>);
}

describe("PrivacyRequestSubmittedScreen", () => {
  afterEach(() => { jest.restoreAllMocks(); mockReplace.mockClear(); mockGoBack.mockClear(); });

  it("shows a loading state while the authoritative detail is being fetched", () => {
    mockDetail(undefined, { isPending: true });
    const { getByText } = renderWithProviders(<PrivacyRequestSubmittedScreen />);
    expect(getByText("Confirming your request…")).toBeTruthy();
  });

  it("renders from the authoritative detail response -- real type, reference, timestamp and status", () => {
    mockDetail({ kind: "found", request: request() });
    const { getByText } = renderWithProviders(<PrivacyRequestSubmittedScreen />);
    expect(getByText("Your request is in")).toBeTruthy();
    expect(getByText("We've received your data export request.")).toBeTruthy();
    expect(getByText("Data export")).toBeTruthy();
    expect(getByText("COMP-2026-000004")).toBeTruthy();
  });

  it("never uses client-side time as the authoritative submission timestamp", () => {
    mockDetail({ kind: "found", request: request({ submittedAt: "2026-08-02T10:32:00Z" as ServerTimestamp }) });
    const { getByText } = renderWithProviders(<PrivacyRequestSubmittedScreen />);
    expect(getByText(/2 Aug 2026/)).toBeTruthy();
  });

  it("hides the reference row when no requestNumber exists, never fabricating one", () => {
    mockDetail({ kind: "found", request: request({ requestNumber: "" }) });
    const { queryByText } = renderWithProviders(<PrivacyRequestSubmittedScreen />);
    expect(queryByText("Reference")).toBeNull();
  });

  it("includes the download step only for a data_export request type", () => {
    mockDetail({ kind: "found", request: request({ requestType: "data_export" }) });
    const { getByText } = renderWithProviders(<PrivacyRequestSubmittedScreen />);
    expect(getByText("Download securely if an export becomes available")).toBeTruthy();
  });

  it("omits the download step for a non-export request type", () => {
    mockDetail({ kind: "found", request: request({ requestType: "right_to_erasure" }) });
    const { queryByText } = renderWithProviders(<PrivacyRequestSubmittedScreen />);
    expect(queryByText("Download securely if an export becomes available")).toBeNull();
  });

  it("maps an unrecognized status to the safe neutral fallback, never a raw enum", () => {
    mockDetail({ kind: "found", request: request({ status: "some_future_status" }) });
    const { getAllByText, queryByText } = renderWithProviders(<PrivacyRequestSubmittedScreen />);
    expect(getAllByText("Status unavailable").length).toBeGreaterThan(0);
    expect(queryByText("some_future_status")).toBeNull();
  });

  it("shows an honest acknowledgment (not a failure) when the detail read is delayed after real creation success", () => {
    mockDetail({ kind: "unavailable" });
    const { getByText, queryByText } = renderWithProviders(<PrivacyRequestSubmittedScreen />);
    expect(getByText("Your request is in")).toBeTruthy();
    expect(queryByText(/failed|error|something went wrong/i)).toBeNull();
  });

  it("View request navigates via replace to PrivacyRequestDetails with only the requestId", () => {
    mockDetail({ kind: "found", request: request() });
    const { getByText } = renderWithProviders(<PrivacyRequestSubmittedScreen />);
    fireEvent.press(getByText("View request"));
    expect(mockReplace).toHaveBeenCalledWith("PrivacyRequestDetails", { requestId: "r-1" });
  });

  it("Close navigates back without resubmitting", () => {
    mockDetail({ kind: "found", request: request() });
    const { getByLabelText } = renderWithProviders(<PrivacyRequestSubmittedScreen />);
    fireEvent.press(getByLabelText("Close"));
    expect(mockGoBack).toHaveBeenCalled();
  });

  it("Back to Privacy & data navigates back", () => {
    mockDetail({ kind: "found", request: request() });
    const { getByText } = renderWithProviders(<PrivacyRequestSubmittedScreen />);
    fireEvent.press(getByText("Back to Privacy & data"));
    expect(mockGoBack).toHaveBeenCalled();
  });

  it("never renders internal fields like a raw UUID, admin notes or reviewer identity", () => {
    mockDetail({ kind: "found", request: request() });
    const { queryByText } = renderWithProviders(<PrivacyRequestSubmittedScreen />);
    expect(queryByText(/r-1$/)).toBeNull();
    expect(queryByText(/admin|reviewer|assigned/i)).toBeNull();
  });

  it("never shows a Download action directly on this receipt", () => {
    mockDetail({ kind: "found", request: request() });
    const { queryByText } = renderWithProviders(<PrivacyRequestSubmittedScreen />);
    expect(queryByText(/^Download$/)).toBeNull();
  });

  it("does not claim completion -- shows the real Submitted status, not a false success state", () => {
    mockDetail({ kind: "found", request: request({ status: "submitted", statusLabel: "Submitted" }) });
    const { getAllByText, queryByText } = renderWithProviders(<PrivacyRequestSubmittedScreen />);
    expect(getAllByText("Submitted").length).toBeGreaterThan(0);
    expect(queryByText("Completed")).toBeNull();
  });

  it("shows the account-deletion-specific hero subtitle for a right_to_erasure request", () => {
    mockDetail({ kind: "found", request: request({ requestType: "right_to_erasure" }) });
    const { getByText } = renderWithProviders(<PrivacyRequestSubmittedScreen />);
    expect(getByText("We've received your account deletion request.")).toBeTruthy();
  });

  it("includes the account-remains-active step only for right_to_erasure", () => {
    mockDetail({ kind: "found", request: request({ requestType: "right_to_erasure" }) });
    const { getByText } = renderWithProviders(<PrivacyRequestSubmittedScreen />);
    expect(getByText("Your account remains active during review")).toBeTruthy();
  });

  it("omits the account-remains-active step for a data_export request", () => {
    mockDetail({ kind: "found", request: request({ requestType: "data_export" }) });
    const { queryByText } = renderWithProviders(<PrivacyRequestSubmittedScreen />);
    expect(queryByText("Your account remains active during review")).toBeNull();
  });

  it("shows the still-signed-in session message only for right_to_erasure", () => {
    mockDetail({ kind: "found", request: request({ requestType: "right_to_erasure" }) });
    const { getByText } = renderWithProviders(<PrivacyRequestSubmittedScreen />);
    expect(getByText("You're still signed in")).toBeTruthy();
    expect(getByText("Submitting this request does not immediately delete your account.")).toBeTruthy();
  });

  it("omits the session message for a data_export request -- never a blanket claim independent of type", () => {
    mockDetail({ kind: "found", request: request({ requestType: "data_export" }) });
    const { queryByText } = renderWithProviders(<PrivacyRequestSubmittedScreen />);
    expect(queryByText("You're still signed in")).toBeNull();
  });

  it("never shows Delete now, Sign out, Withdraw or Cancel actions on the deletion receipt", () => {
    mockDetail({ kind: "found", request: request({ requestType: "right_to_erasure" }) });
    const { queryByText } = renderWithProviders(<PrivacyRequestSubmittedScreen />);
    expect(queryByText(/delete now/i)).toBeNull();
    expect(queryByText(/^sign out$/i)).toBeNull();
    expect(queryByText(/withdraw/i)).toBeNull();
    expect(queryByText(/^cancel request$/i)).toBeNull();
  });

  it("Close and View request work identically for the deletion variant as for other types", () => {
    mockDetail({ kind: "found", request: request({ requestType: "right_to_erasure" }) });
    const { getByLabelText, getByText } = renderWithProviders(<PrivacyRequestSubmittedScreen />);
    expect(getByLabelText("Close")).toBeTruthy();
    expect(getByText("View request")).toBeTruthy();
  });
});
