import React from "react";
import { fireEvent, waitFor } from "@testing-library/react-native";
import { renderWithProviders } from "../../../testing/renderWithProviders";
import { DataCorrectionRequestScreen } from "../DataCorrectionRequestScreen";
import * as queriesModule from "../../../api/privacyData/usePrivacyDataQueries";
import * as privacyDataApi from "../../../api/privacyData/privacyDataApi";
import * as networkStateModule from "../../../api/networkState";
import { PrivacyRequest } from "../../../domain/privacyData";
import { ServerTimestamp } from "../../../domain/dates";
import { DomainError } from "../../../domain/errors";

const mockNavigate = jest.fn();
const mockReplace = jest.fn();
const mockGoBack = jest.fn();
jest.mock("@react-navigation/native", () => ({
  ...jest.requireActual("@react-navigation/native"),
  useNavigation: () => ({ navigate: mockNavigate, goBack: mockGoBack, replace: mockReplace }),
}));

function request(overrides: Partial<PrivacyRequest> = {}): PrivacyRequest {
  return {
    id: "r-1", requestNumber: "COMP-1", requestType: "data_correction",
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
  return renderWithProviders(<DataCorrectionRequestScreen />);
}

async function fillValidForm(getByLabelText: (label: string) => { props: { onChangeText?: (t: string) => void } }) {
  fireEvent.changeText(getByLabelText("What is incorrect?"), "My address on file is outdated");
  fireEvent.changeText(getByLabelText("What should it say?"), "123 New Street, Ludhiana");
  fireEvent.press(getByLabelText("I confirm the information I've provided is accurate."));
}

describe("DataCorrectionRequestScreen", () => {
  afterEach(() => { jest.restoreAllMocks(); mockNavigate.mockClear(); mockReplace.mockClear(); mockGoBack.mockClear(); });

  it("shows the loading state while checking for an existing correction request", () => {
    mockRequests(undefined, true);
    const { getByText } = render();
    expect(getByText("Checking your correction requests…")).toBeTruthy();
  });

  it("defaults to the Account details category, a real direct-edit destination", () => {
    mockRequests([]);
    const { getByText } = render();
    expect(getByText("This can be updated right away")).toBeTruthy();
    expect(getByText("Edit personal details")).toBeTruthy();
  });

  it("hands off Account details to the real EditProfile screen, never a formal request", () => {
    mockRequests([]);
    const { getByText, queryByText } = render();
    fireEvent.press(getByText("Edit personal details"));
    expect(mockNavigate).toHaveBeenCalledWith("EditProfile");
    expect(queryByText("Submit correction request")).toBeNull();
  });

  it("hands off Address information to the real Saved Addresses screen", () => {
    mockRequests([]);
    const { getByLabelText, getByText } = render();
    fireEvent.press(getByLabelText("Information category: Account details"));
    fireEvent.press(getByText("Address information"));
    fireEvent.press(getByText("Manage addresses"));
    expect(mockNavigate).toHaveBeenCalledWith("SavedAddresses");
  });

  it("shows the real correction form for a category with no direct-edit path", () => {
    mockRequests([]);
    const { getByLabelText, getByText } = render();
    fireEvent.press(getByLabelText("Information category: Account details"));
    fireEvent.press(getByText("Contact information"));
    expect(getByText("What is incorrect?")).toBeTruthy();
    expect(getByText("What should it say?")).toBeTruthy();
  });

  it("disables Submit until both fields are filled and the acknowledgement is checked", () => {
    mockRequests([]);
    const { getByLabelText, getByText } = render();
    fireEvent.press(getByLabelText("Information category: Account details"));
    fireEvent.press(getByText("Contact information"));
    expect(getByLabelText("Submit correction request").props.accessibilityState.disabled).toBe(true);
  });

  it("submits only the real backend fields, folding the category into the one real reason field", async () => {
    mockRequests([]);
    const createSpy = jest.spyOn(privacyDataApi, "createMyPrivacyRequest").mockResolvedValue({
      data: { request_id: "r-9", request_number: "COMP-9", request_type: "data_correction", status: "submitted", status_label: "Submitted", sla_status: "on_track", submitted_at: null, due_at: null, message: "ok" },
    } as unknown as Awaited<ReturnType<typeof privacyDataApi.createMyPrivacyRequest>>);

    const { getByLabelText, getByText } = render();
    fireEvent.press(getByLabelText("Information category: Account details"));
    fireEvent.press(getByText("Contact information"));
    await fillValidForm(getByLabelText);
    fireEvent.press(getByLabelText("Submit correction request"));

    await waitFor(() => expect(createSpy).toHaveBeenCalled());
    const payload = createSpy.mock.calls[0][0];
    expect(payload.request_type).toBe("data_correction");
    expect(payload.confirm_understanding).toBe(true);
    expect(typeof payload.idempotency_key).toBe("string");
    expect(payload.reason).toContain("Category: Contact information");
    expect(payload.reason).toContain("My address on file is outdated");
    expect(payload.reason).toContain("123 New Street, Ludhiana");
    expect((payload as unknown as { customer_id?: string }).customer_id).toBeUndefined();

    await waitFor(() => expect(mockReplace).toHaveBeenCalledWith("PrivacyRequestSubmitted", { requestId: "r-9" }));
  });

  it("preserves Unicode (Punjabi/Hindi) input in the submitted reason", async () => {
    mockRequests([]);
    const createSpy = jest.spyOn(privacyDataApi, "createMyPrivacyRequest").mockResolvedValue({
      data: { request_id: "r-10", request_number: "COMP-10", request_type: "data_correction", status: "submitted", status_label: "Submitted", sla_status: "on_track", submitted_at: null, due_at: null, message: "ok" },
    } as unknown as Awaited<ReturnType<typeof privacyDataApi.createMyPrivacyRequest>>);

    const { getByLabelText, getByText } = render();
    fireEvent.press(getByLabelText("Information category: Account details"));
    fireEvent.press(getByText("Contact information"));
    fireEvent.changeText(getByLabelText("What is incorrect?"), "ਮੇਰਾ ਨਾਮ ਗਲਤ ਹੈ");
    fireEvent.changeText(getByLabelText("What should it say?"), "मेरा सही नाम राजिंदर सिंह है");
    fireEvent.press(getByLabelText("I confirm the information I've provided is accurate."));
    fireEvent.press(getByLabelText("Submit correction request"));

    await waitFor(() => expect(createSpy).toHaveBeenCalled());
    expect(createSpy.mock.calls[0][0].reason).toContain("ਮੇਰਾ ਨਾਮ ਗਲਤ ਹੈ");
    expect(createSpy.mock.calls[0][0].reason).toContain("मेरा सही नाम राजिंदर सिंह है");
  });

  it("reuses the same idempotency key across a retry of the same submission", async () => {
    mockRequests([]);
    const createSpy = jest.spyOn(privacyDataApi, "createMyPrivacyRequest")
      .mockRejectedValueOnce(new DomainError({ category: "TIMEOUT", diagnostic: "timed out" }))
      .mockResolvedValueOnce({
        data: { request_id: "r-11", request_number: "COMP-11", request_type: "data_correction", status: "submitted", status_label: "Submitted", sla_status: "on_track", submitted_at: null, due_at: null, message: "ok" },
      } as unknown as Awaited<ReturnType<typeof privacyDataApi.createMyPrivacyRequest>>);

    const { getByLabelText, getByText } = render();
    fireEvent.press(getByLabelText("Information category: Account details"));
    fireEvent.press(getByText("Contact information"));
    await fillValidForm(getByLabelText);

    fireEvent.press(getByLabelText("Submit correction request"));
    await waitFor(() => expect(createSpy).toHaveBeenCalledTimes(1));
    fireEvent.press(getByLabelText("Submit correction request"));
    await waitFor(() => expect(createSpy).toHaveBeenCalledTimes(2));

    expect(createSpy.mock.calls[0][0].idempotency_key).toBe(createSpy.mock.calls[1][0].idempotency_key);
  });

  it("routes to the existing request on a duplicate-open-request response", async () => {
    mockRequests([]);
    jest.spyOn(privacyDataApi, "createMyPrivacyRequest").mockRejectedValue(
      new DomainError({ category: "CONFLICT_STALE_WORKFLOW", diagnostic: "duplicate", telemetryMeta: { existingRequestId: "existing-r-3" } }),
    );

    const { getByLabelText, getByText } = render();
    fireEvent.press(getByLabelText("Information category: Account details"));
    fireEvent.press(getByText("Contact information"));
    await fillValidForm(getByLabelText);
    fireEvent.press(getByLabelText("Submit correction request"));

    await waitFor(() => expect(mockReplace).toHaveBeenCalledWith("PrivacyRequestDetails", { requestId: "existing-r-3" }));
  });

  it("shows the existing-active-request state and never a second form when one is already open", () => {
    mockRequests([request({ status: "under_review" })]);
    const { getByText, queryByText } = render();
    expect(getByText("You already have a correction request in progress")).toBeTruthy();
    expect(queryByText("Submit correction request")).toBeNull();
  });

  it("preserves entered text after a recoverable submission failure", async () => {
    mockRequests([]);
    jest.spyOn(privacyDataApi, "createMyPrivacyRequest").mockRejectedValue(new Error("network"));

    const { getByLabelText, getByText } = render();
    fireEvent.press(getByLabelText("Information category: Account details"));
    fireEvent.press(getByText("Contact information"));
    await fillValidForm(getByLabelText);
    fireEvent.press(getByLabelText("Submit correction request"));

    await waitFor(() => expect(getByText("Couldn't submit your correction request.")).toBeTruthy());
    expect(getByLabelText("What is incorrect?").props.value).toBe("My address on file is outdated");
  });

  it("disables submission and explains why while offline", () => {
    jest.spyOn(networkStateModule, "isOffline").mockReturnValue(true);
    mockRequests([]);
    const { getByLabelText, getByText } = render();
    fireEvent.press(getByLabelText("Information category: Account details"));
    fireEvent.press(getByText("Contact information"));
    expect(getByText("Connect to the internet to submit this request.")).toBeTruthy();
  });

  it("Cancel returns without submitting", () => {
    mockRequests([]);
    const createSpy = jest.spyOn(privacyDataApi, "createMyPrivacyRequest");
    const { getByLabelText, getByText } = render();
    fireEvent.press(getByLabelText("Information category: Account details"));
    fireEvent.press(getByText("Contact information"));
    fireEvent.press(getByLabelText("Cancel"));
    expect(mockGoBack).toHaveBeenCalled();
    expect(createSpy).not.toHaveBeenCalled();
  });

  it("Go back navigates via the back chevron", () => {
    mockRequests([]);
    const { getByLabelText } = render();
    fireEvent.press(getByLabelText("Go back"));
    expect(mockGoBack).toHaveBeenCalled();
  });
});
