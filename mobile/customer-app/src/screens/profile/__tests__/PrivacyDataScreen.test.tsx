import React from "react";
import { fireEvent } from "@testing-library/react-native";
import { renderWithProviders } from "../../../testing/renderWithProviders";
import { PrivacyDataScreen } from "../PrivacyDataScreen";
import * as queriesModule from "../../../api/privacyData/usePrivacyDataQueries";
import { PrivacyRequest } from "../../../domain/privacyData";
import { ServerTimestamp } from "../../../domain/dates";

const mockNavigate = jest.fn();
jest.mock("@react-navigation/native", () => ({
  ...jest.requireActual("@react-navigation/native"),
  useNavigation: () => ({ navigate: mockNavigate, goBack: jest.fn() }),
}));

function request(overrides: Partial<PrivacyRequest> = {}): PrivacyRequest {
  return {
    id: "r-1", requestNumber: "REQ-001", requestType: "data_export",
    status: "submitted", statusLabel: "Submitted", slaStatus: "on_track", slaLabel: "On Track",
    verificationStatus: "not_required",
    submittedAt: "2026-01-01T00:00:00Z" as ServerTimestamp, dueAt: null, completedAt: null,
    reason: null, rejectionReason: null,
    createdAt: "2026-01-01T00:00:00Z" as ServerTimestamp, updatedAt: null,
    ...overrides,
  };
}

function mockRequests(requests: PrivacyRequest[] | undefined, isPending = false, isError = false) {
  jest.spyOn(queriesModule, "usePrivacyRequestsQuery").mockReturnValue({
    data: requests ? { requests, meta: { total: requests.length, page: 1, limit: 20, total_pages: 1 } } : undefined,
    isPending, isError, refetch: jest.fn(),
  } as unknown as ReturnType<typeof queriesModule.usePrivacyRequestsQuery>);
}

function render() {
  return renderWithProviders(<PrivacyDataScreen />);
}

describe("PrivacyDataScreen", () => {
  afterEach(() => { jest.restoreAllMocks(); mockNavigate.mockClear(); });

  it("shows the loading state", () => {
    mockRequests(undefined, true);
    const { getByText } = render();
    expect(getByText("Checking privacy controls…")).toBeTruthy();
  });

  it("shows a recoverable first-load error with retry", () => {
    mockRequests(undefined, false, true);
    const { getByText } = render();
    expect(getByText("We couldn't load your privacy controls.")).toBeTruthy();
    expect(getByText("Try again")).toBeTruthy();
  });

  it("shows the honest empty state when no requests exist", () => {
    mockRequests([]);
    const { getByText } = render();
    expect(getByText("No active requests")).toBeTruthy();
  });

  it("shows the static guidance panel, never a compliance guarantee", () => {
    mockRequests([]);
    const { getByText, queryByText } = render();
    expect(getByText("Your data, your choices")).toBeTruthy();
    expect(queryByText(/guaranteed|instant/i)).toBeNull();
  });

  it("navigates to the dedicated Data Export Request screen for Download your data", () => {
    mockRequests([]);
    const { getByLabelText } = render();
    fireEvent.press(getByLabelText("Download your data: Request"));
    expect(mockNavigate).toHaveBeenCalledWith("DataExportRequest");
  });

  it("disables the Download your data action while an export request is already active", () => {
    mockRequests([request({ requestType: "data_export", status: "submitted", statusLabel: "Submitted" })]);
    const { getByLabelText } = render();
    const requestAction = getByLabelText("Download your data: Request");
    expect(requestAction.props.accessibilityState.disabled).toBe(true);
  });

  it("navigates to the Data Correction Request screen for Correct my data", () => {
    mockRequests([]);
    const { getByLabelText } = render();
    fireEvent.press(getByLabelText("Correct my data: Request"));
    expect(mockNavigate).toHaveBeenCalledWith("DataCorrectionRequest");
  });

  it("navigates to the dedicated Account Deletion Request screen for Delete your account", () => {
    mockRequests([]);
    const { getByText } = render();
    fireEvent.press(getByText("Start"));
    expect(mockNavigate).toHaveBeenCalledWith("AccountDeletionRequest");
  });

  it("disables the Delete your account action while an erasure request is already active", () => {
    mockRequests([request({ requestType: "right_to_erasure", status: "submitted", statusLabel: "Submitted" })]);
    const { getByLabelText } = render();
    const startAction = getByLabelText("Delete your account: Start");
    expect(startAction.props.accessibilityState.disabled).toBe(true);
  });

  it("renders an active request card with its safe status label", () => {
    mockRequests([request({ requestType: "data_export", statusLabel: "Submitted" })]);
    const { getByText } = render();
    expect(getByText("Data export")).toBeTruthy();
    expect(getByText("Submitted")).toBeTruthy();
  });

  it("falls back to a neutral label for an unrecognized status", () => {
    mockRequests([request({ statusLabel: "" })]);
    const { getByText } = render();
    expect(getByText("Request status unavailable")).toBeTruthy();
  });

  it("shows Withdraw only for a cancellable request in an open state", () => {
    mockRequests([request({ status: "submitted" })]);
    const { getByText } = render();
    expect(getByText("Withdraw request")).toBeTruthy();
  });

  it("hides Withdraw for a completed request", () => {
    mockRequests([request({ status: "completed", statusLabel: "Completed" })]);
    const { queryByText } = render();
    expect(queryByText("Withdraw request")).toBeNull();
  });

  it("navigates to Privacy consent and Assistant conversations", () => {
    mockRequests([]);
    const { getAllByText } = render();
    fireEvent.press(getAllByText("View")[0]);
    expect(mockNavigate).toHaveBeenCalledWith("PrivacyConsent");
    fireEvent.press(getAllByText("View")[1]);
    expect(mockNavigate).toHaveBeenCalledWith("AssistantDataInfo");
  });

  it("shows the retention footer, never claiming all data is deleted", () => {
    mockRequests([]);
    const { getByText, queryByText } = render();
    expect(getByText("Fuvay keeps required records only according to its retention policy.")).toBeTruthy();
    expect(queryByText(/all data.*deleted|all information.*erased/i)).toBeNull();
  });

  it("never renders raw internal reviewer/admin fields", () => {
    mockRequests([request()]);
    const { queryByText } = render();
    expect(queryByText(/admin_notes|reviewer|internal_risk/i)).toBeNull();
  });
});
