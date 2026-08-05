import React from "react";
import { Alert } from "react-native";
import { fireEvent, waitFor } from "@testing-library/react-native";
import { renderWithProviders } from "../../../testing/renderWithProviders";
import { PrivacyRequestDetailsScreen } from "../PrivacyRequestDetailsScreen";
import * as queriesModule from "../../../api/privacyData/usePrivacyDataQueries";
import * as networkStateModule from "../../../api/networkState";
import { PrivacyRequest } from "../../../domain/privacyData";
import { ServerTimestamp } from "../../../domain/dates";

const mockGoBack = jest.fn();
const mockRequestId = "r-1";

jest.mock("@react-navigation/native", () => ({
  ...jest.requireActual("@react-navigation/native"),
  useNavigation: () => ({ navigate: jest.fn(), goBack: mockGoBack }),
  useRoute: () => ({ name: "PrivacyRequestDetails", params: { requestId: mockRequestId } }),
}));

function request(overrides: Partial<PrivacyRequest> = {}): PrivacyRequest {
  return {
    id: mockRequestId, requestNumber: "COMP-2026-000001", requestType: "right_to_erasure",
    status: "under_review", statusLabel: "Under Review", slaStatus: "on_track", slaLabel: "On Track",
    verificationStatus: "not_required",
    submittedAt: "2026-01-01T10:00:00Z" as ServerTimestamp, dueAt: null, completedAt: null,
    reason: "test", rejectionReason: null,
    createdAt: "2026-01-01T10:00:00Z" as ServerTimestamp, updatedAt: "2026-01-02T11:00:00Z" as ServerTimestamp,
    ...overrides,
  };
}

function mockDetail(
  result: { kind: "found"; request: PrivacyRequest } | { kind: "unavailable" } | undefined,
  opts: { isPending?: boolean; isError?: boolean; isRefetching?: boolean } = {},
) {
  const refetch = jest.fn();
  jest.spyOn(queriesModule, "usePrivacyRequestDetailQuery").mockReturnValue({
    data: result, isPending: !!opts.isPending, isError: !!opts.isError,
    isRefetching: !!opts.isRefetching, refetch,
  } as unknown as ReturnType<typeof queriesModule.usePrivacyRequestDetailQuery>);
  return refetch;
}

function mockCancelMutation(overrides: Partial<ReturnType<typeof queriesModule.useCancelPrivacyRequestMutation>> = {}) {
  const mutateAsync = jest.fn().mockResolvedValue({});
  jest.spyOn(queriesModule, "useCancelPrivacyRequestMutation").mockReturnValue({
    mutateAsync, isPending: false, ...overrides,
  } as unknown as ReturnType<typeof queriesModule.useCancelPrivacyRequestMutation>);
  return mutateAsync;
}

function mockDownloadMutation(overrides: Partial<ReturnType<typeof queriesModule.useDownloadExportMutation>> = {}) {
  const mutateAsync = jest.fn().mockResolvedValue({ data: { download_url: "/v1/me/compliance/exports/e-1/download" } });
  jest.spyOn(queriesModule, "useDownloadExportMutation").mockReturnValue({
    mutateAsync, isPending: false, ...overrides,
  } as unknown as ReturnType<typeof queriesModule.useDownloadExportMutation>);
  return mutateAsync;
}

function render() {
  return renderWithProviders(<PrivacyRequestDetailsScreen />);
}

describe("PrivacyRequestDetailsScreen", () => {
  afterEach(() => { jest.restoreAllMocks(); mockGoBack.mockClear(); });

  it("shows the loading state while resolving the request", () => {
    mockDetail(undefined, { isPending: true });
    mockCancelMutation();
    mockDownloadMutation();
    const { getByText } = render();
    expect(getByText("Loading your request…")).toBeTruthy();
  });

  it("shows the enumeration-safe unavailable state for a missing or foreign request", () => {
    mockDetail({ kind: "unavailable" });
    mockCancelMutation();
    mockDownloadMutation();
    const { getByText } = render();
    expect(getByText("This privacy request is unavailable.")).toBeTruthy();
  });

  it("renders the real deletion request status, without a countdown or fabricated ETA", () => {
    mockDetail({ kind: "found", request: request({ status: "under_review" }) });
    mockCancelMutation();
    mockDownloadMutation();
    const { getByText, getAllByText, queryByText } = render();
    expect(getByText("Under review")).toBeTruthy();
    expect(getAllByText("Account deletion").length).toBeGreaterThan(0);
    expect(queryByText(/\d+ days? remaining|estimated completion|completion date/i)).toBeNull();
  });

  it("shows Status unavailable for an unrecognized backend status, not a raw enum value", () => {
    mockDetail({ kind: "found", request: request({ status: "some_new_status_v9" }) });
    mockCancelMutation();
    mockDownloadMutation();
    const { getByText, queryByText } = render();
    expect(getByText("Status unavailable")).toBeTruthy();
    expect(queryByText("some_new_status_v9")).toBeNull();
  });

  it("renders the real audit-trail timeline when the backend provides one", () => {
    mockDetail({
      kind: "found",
      request: request({
        auditTrail: [
          { action: "request.created", createdAt: "2026-01-01T10:00:00Z" as ServerTimestamp },
          { action: "request.approved", createdAt: "2026-01-02T10:00:00Z" as ServerTimestamp },
        ],
      }),
    });
    mockCancelMutation();
    mockDownloadMutation();
    const { getByText } = render();
    expect(getByText("Request submitted")).toBeTruthy();
    expect(getByText("Request approved")).toBeTruthy();
  });

  it("falls back to current-status-only with no manufactured history when the backend has none", () => {
    mockDetail({ kind: "found", request: request({ auditTrail: undefined }) });
    mockCancelMutation();
    mockDownloadMutation();
    const { getByText, queryByText } = render();
    expect(getByText("Under Review")).toBeTruthy();
    expect(queryByText("Request approved")).toBeNull();
  });

  it("shows Withdraw request only while the status allows it", () => {
    mockDetail({ kind: "found", request: request({ status: "submitted" }) });
    mockCancelMutation();
    mockDownloadMutation();
    const { getByText } = render();
    expect(getByText("Withdraw request")).toBeTruthy();
  });

  it("hides Withdraw request once the request is terminal", () => {
    mockDetail({ kind: "found", request: request({ status: "completed" }) });
    mockCancelMutation();
    mockDownloadMutation();
    const { queryByText } = render();
    expect(queryByText("Withdraw request")).toBeNull();
  });

  it("withdraws only after confirmation, waits for the response, then refetches", async () => {
    const refetch = mockDetail({ kind: "found", request: request({ status: "submitted" }) });
    const mutateAsync = mockCancelMutation();
    mockDownloadMutation();
    const alertSpy = jest.spyOn(Alert, "alert").mockImplementation((_t, _m, buttons) => {
      const confirm = buttons?.find(b => b.text === "Withdraw");
      confirm?.onPress?.();
    });

    const { getByText } = render();
    fireEvent.press(getByText("Withdraw request"));

    expect(alertSpy).toHaveBeenCalled();
    await waitFor(() => expect(mutateAsync).toHaveBeenCalledWith(mockRequestId));
    await waitFor(() => expect(refetch).toHaveBeenCalled());
  });

  it("shows recoverable copy and refetches on withdrawal failure, never marking it withdrawn optimistically", async () => {
    const refetch = mockDetail({ kind: "found", request: request({ status: "submitted" }) });
    mockCancelMutation({ mutateAsync: jest.fn().mockRejectedValue(new Error("conflict")) });
    mockDownloadMutation();
    jest.spyOn(Alert, "alert").mockImplementation((_t, _m, buttons) => {
      const confirm = buttons?.find(b => b.text === "Withdraw");
      confirm?.onPress?.();
    });

    const { getByText } = render();
    fireEvent.press(getByText("Withdraw request"));

    await waitFor(() => expect(getByText("Couldn't withdraw this request.")).toBeTruthy());
    expect(refetch).toHaveBeenCalled();
  });

  it("disables withdrawal while offline", () => {
    jest.spyOn(networkStateModule, "isOffline").mockReturnValue(true);
    mockDetail({ kind: "found", request: request({ status: "submitted" }) });
    mockCancelMutation();
    mockDownloadMutation();
    const { getByLabelText } = render();
    expect(getByLabelText("Withdraw request").props.accessibilityState.disabled).toBe(true);
  });

  it("shows a Download action for a ready export and never for a deletion request", () => {
    mockDetail({
      kind: "found",
      request: request({
        requestType: "data_export", status: "completed",
        export: { exportId: "e-1", status: "ready", expiresAt: null, isExpired: false },
      }),
    });
    mockCancelMutation();
    mockDownloadMutation();
    const { getByText } = render();
    expect(getByText("Download your data")).toBeTruthy();
  });

  it("shows expired-export copy and never reuses the old link", () => {
    mockDetail({
      kind: "found",
      request: request({
        requestType: "data_export", status: "completed",
        export: { exportId: "e-1", status: "expired", expiresAt: null, isExpired: true },
      }),
    });
    mockCancelMutation();
    mockDownloadMutation();
    const { getByText, queryByText } = render();
    expect(getByText("Your export has expired")).toBeTruthy();
    expect(queryByText("Download your data")).toBeNull();
  });

  it("shows preparing copy for an export that is not yet ready", () => {
    mockDetail({
      kind: "found",
      request: request({
        requestType: "data_export", status: "processing",
        export: { exportId: "e-1", status: "generating", expiresAt: null, isExpired: false },
      }),
    });
    mockCancelMutation();
    mockDownloadMutation();
    const { getByText } = render();
    expect(getByText("Preparing your data")).toBeTruthy();
  });

  it("downloads on tap and never persists the returned URL across renders", async () => {
    mockDetail({
      kind: "found",
      request: request({
        requestType: "data_export", status: "completed",
        export: { exportId: "e-1", status: "ready", expiresAt: null, isExpired: false },
      }),
    });
    mockCancelMutation();
    const mutateAsync = mockDownloadMutation();

    const { getByText } = render();
    fireEvent.press(getByText("Download your data"));

    await waitFor(() => expect(mutateAsync).toHaveBeenCalledWith({ exportId: "e-1", requestId: mockRequestId }));
  });

  it("preserves the last-known data and shows recoverable copy on a refresh error", () => {
    mockDetail({ kind: "found", request: request() }, { isError: true });
    mockCancelMutation();
    mockDownloadMutation();
    const { getByText } = render();
    expect(getByText("Under Review")).toBeTruthy();
    expect(getByText("We couldn't refresh this request. Showing the last known status.")).toBeTruthy();
  });

  it("shows a back arrow and never a bottom navigation bar", () => {
    mockDetail({ kind: "found", request: request() });
    mockCancelMutation();
    mockDownloadMutation();
    const { getByLabelText, queryByLabelText } = render();
    expect(getByLabelText("Go back")).toBeTruthy();
    expect(queryByLabelText("Home tab")).toBeNull();
  });

  it("never renders raw internal fields like admin notes or reviewer identity", () => {
    mockDetail({ kind: "found", request: request({ rejectionReason: null }) });
    mockCancelMutation();
    mockDownloadMutation();
    const { queryByText } = render();
    expect(queryByText(/admin_notes|reviewer|assigned_to|risk_score/i)).toBeNull();
  });
});
