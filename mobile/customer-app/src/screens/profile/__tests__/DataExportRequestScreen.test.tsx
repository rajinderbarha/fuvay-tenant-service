import React from "react";
import { fireEvent, waitFor } from "@testing-library/react-native";
import { renderWithProviders } from "../../../testing/renderWithProviders";
import { DataExportRequestScreen } from "../DataExportRequestScreen";
import * as queriesModule from "../../../api/privacyData/usePrivacyDataQueries";
import * as privacyDataApi from "../../../api/privacyData/privacyDataApi";
import * as networkStateModule from "../../../api/networkState";
import { PrivacyRequest } from "../../../domain/privacyData";
import { ServerTimestamp } from "../../../domain/dates";
import { DomainError } from "../../../domain/errors";

const mockReplace = jest.fn();
const mockGoBack = jest.fn();
jest.mock("@react-navigation/native", () => ({
  ...jest.requireActual("@react-navigation/native"),
  useNavigation: () => ({ navigate: jest.fn(), goBack: mockGoBack, replace: mockReplace }),
}));

function request(overrides: Partial<PrivacyRequest> = {}): PrivacyRequest {
  return {
    id: "r-1", requestNumber: "COMP-1", requestType: "data_export",
    status: "submitted", statusLabel: "Submitted", slaStatus: "on_track", slaLabel: "On Track",
    verificationStatus: "not_required",
    submittedAt: "2026-01-01T00:00:00Z" as ServerTimestamp, dueAt: null, completedAt: null,
    reason: null, rejectionReason: null,
    createdAt: "2026-01-01T00:00:00Z" as ServerTimestamp, updatedAt: null,
    ...overrides,
  };
}

function mockRequests(requests: PrivacyRequest[] | undefined, isPending = false) {
  jest.spyOn(queriesModule, "usePrivacyRequestsQuery").mockReturnValue({
    data: requests ? { requests, meta: { total: requests.length, page: 1, limit: 20, total_pages: 1 } } : undefined,
    isPending, isError: false, refetch: jest.fn(),
  } as unknown as ReturnType<typeof queriesModule.usePrivacyRequestsQuery>);
}

function render() {
  return renderWithProviders(<DataExportRequestScreen />);
}

describe("DataExportRequestScreen", () => {
  afterEach(() => { jest.restoreAllMocks(); mockReplace.mockClear(); mockGoBack.mockClear(); });

  it("shows the loading state while checking export eligibility", () => {
    mockRequests(undefined, true);
    const { getByText } = render();
    expect(getByText("Checking your export eligibility…")).toBeTruthy();
  });

  it("shows the generic export-contents fallback -- never invented specific categories", () => {
    mockRequests([]);
    const { getByText, queryByText } = render();
    expect(getByText("Your export contains the customer information available under the platform's export policy.")).toBeTruthy();
    expect(queryByText("Profile and account")).toBeNull();
    expect(queryByText("Bookings and addresses")).toBeNull();
  });

  it("shows the three how-it-works steps without ETA, file size or guaranteed delivery language", () => {
    mockRequests([]);
    const { getByText, queryByText } = render();
    expect(getByText("Request your copy")).toBeTruthy();
    expect(getByText("We prepare the export")).toBeTruthy();
    expect(getByText("Download securely")).toBeTruthy();
    expect(queryByText(/\d+ (mb|kb|gb)|guaranteed|within \d+ (hours|minutes)/i)).toBeNull();
  });

  it("submits a real export request and replaces navigation to the request details screen", async () => {
    mockRequests([]);
    const createSpy = jest.spyOn(privacyDataApi, "createMyPrivacyRequest").mockResolvedValue({
      data: { request_id: "r-2", request_number: "COMP-2", request_type: "data_export", status: "submitted", status_label: "Submitted", sla_status: "on_track", submitted_at: null, due_at: null, message: "ok" },
      requestId: "req-1",
    } as unknown as Awaited<ReturnType<typeof privacyDataApi.createMyPrivacyRequest>>);

    const { getByText } = render();
    fireEvent.press(getByText("Request data export"));

    await waitFor(() => expect(createSpy).toHaveBeenCalledWith({
      request_type: "data_export", confirm_understanding: true, idempotency_key: expect.any(String),
    }));
    await waitFor(() => expect(mockReplace).toHaveBeenCalledWith("PrivacyRequestSubmitted", { requestId: "r-2" }));
  });

  it("reuses the same idempotency key across a retry of the same submission attempt", async () => {
    mockRequests([]);
    const createSpy = jest.spyOn(privacyDataApi, "createMyPrivacyRequest")
      .mockRejectedValueOnce(new DomainError({ category: "TIMEOUT", diagnostic: "timed out" }))
      .mockResolvedValueOnce({
        data: { request_id: "r-4", request_number: "COMP-4", request_type: "data_export", status: "submitted", status_label: "Submitted", sla_status: "on_track", submitted_at: null, due_at: null, message: "ok" },
      } as unknown as Awaited<ReturnType<typeof privacyDataApi.createMyPrivacyRequest>>);

    const { getByText } = render();
    fireEvent.press(getByText("Request data export"));
    await waitFor(() => expect(createSpy).toHaveBeenCalledTimes(1));
    fireEvent.press(getByText("Request data export"));
    await waitFor(() => expect(createSpy).toHaveBeenCalledTimes(2));

    const firstKey = createSpy.mock.calls[0][0].idempotency_key;
    const secondKey = createSpy.mock.calls[1][0].idempotency_key;
    expect(firstKey).toBe(secondKey);
  });

  it("disables the submit button while the mutation is in flight, preventing a double tap", async () => {
    mockRequests([]);
    type CreateResult = Awaited<ReturnType<typeof privacyDataApi.createMyPrivacyRequest>>;
    let resolveCreate: (v: CreateResult) => void = () => {};
    jest.spyOn(privacyDataApi, "createMyPrivacyRequest").mockReturnValue(
      new Promise<CreateResult>(resolve => { resolveCreate = resolve; }),
    );

    const { getByLabelText } = render();
    fireEvent.press(getByLabelText("Request data export"));
    expect(getByLabelText("Request data export").props.accessibilityState.disabled).toBe(true);

    resolveCreate({
      data: { request_id: "r-3", request_number: "COMP-3", request_type: "data_export", status: "submitted", status_label: "Submitted", sla_status: "on_track", submitted_at: null, due_at: null, message: "ok" },
      requestId: "req-1",
    });
    await waitFor(() => expect(mockReplace).toHaveBeenCalled());
  });

  it("shows the export-in-progress state and never a second creation form when one is already preparing", () => {
    mockRequests([request({ status: "under_review" })]);
    const { getByText, queryByText } = render();
    expect(getByText("Your export is being prepared")).toBeTruthy();
    expect(queryByText("Request data export")).toBeNull();
  });

  it("shows the ready state and links to the request details screen for a completed, unexpired export", () => {
    mockRequests([request({
      status: "completed",
      export: { exportId: "e-1", status: "ready", expiresAt: null, isExpired: false },
    })]);
    const { getByText, queryByText } = render();
    expect(getByText("Your export is ready")).toBeTruthy();
    expect(queryByText("Request data export")).toBeNull();
  });

  it("allows a new request when the existing export has expired", () => {
    mockRequests([request({
      status: "completed",
      export: { exportId: "e-1", status: "expired", expiresAt: null, isExpired: true },
    })]);
    const { getByText } = render();
    expect(getByText("Request data export")).toBeTruthy();
  });

  it("routes straight to the existing request on a duplicate-open-request response", async () => {
    mockRequests([]);
    jest.spyOn(privacyDataApi, "createMyPrivacyRequest").mockRejectedValue(
      new DomainError({
        category: "CONFLICT_STALE_WORKFLOW", diagnostic: "duplicate",
        telemetryMeta: { existingRequestId: "existing-r-9" },
      }),
    );

    const { getByText } = render();
    fireEvent.press(getByText("Request data export"));

    await waitFor(() => expect(mockReplace).toHaveBeenCalledWith("PrivacyRequestDetails", { requestId: "existing-r-9" }));
  });

  it("shows recoverable copy on a rate-limited response, without a fabricated retry countdown", async () => {
    mockRequests([]);
    jest.spyOn(privacyDataApi, "createMyPrivacyRequest").mockRejectedValue(
      new DomainError({ category: "RATE_LIMITED", diagnostic: "Limit of 5 actions per day reached. Try again tomorrow." }),
    );

    const { getByText } = render();
    fireEvent.press(getByText("Request data export"));

    await waitFor(() => expect(getByText("Limit of 5 actions per day reached. Try again tomorrow.")).toBeTruthy());
  });

  it("shows a recoverable failure message on an unexpected error", async () => {
    mockRequests([]);
    jest.spyOn(privacyDataApi, "createMyPrivacyRequest").mockRejectedValue(new Error("network"));

    const { getByText } = render();
    fireEvent.press(getByText("Request data export"));

    await waitFor(() => expect(getByText("Couldn't submit your export request.")).toBeTruthy());
  });

  it("disables submission and explains why while offline, keeping explanatory content visible", () => {
    jest.spyOn(networkStateModule, "isOffline").mockReturnValue(true);
    mockRequests([]);
    const { getByText, getByLabelText } = render();
    expect(getByText("Connect to the internet to request your data.")).toBeTruthy();
    expect(getByLabelText("Request data export").props.accessibilityState.disabled).toBe(true);
    expect(getByText("How it works")).toBeTruthy();
  });

  it("Not now returns to Privacy & data without submitting", () => {
    mockRequests([]);
    const createSpy = jest.spyOn(privacyDataApi, "createMyPrivacyRequest");
    const { getByText } = render();
    fireEvent.press(getByText("Not now"));
    expect(mockGoBack).toHaveBeenCalled();
    expect(createSpy).not.toHaveBeenCalled();
  });
});
