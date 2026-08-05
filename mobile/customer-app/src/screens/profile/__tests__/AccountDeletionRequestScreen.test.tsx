import React from "react";
import { fireEvent } from "@testing-library/react-native";
import { renderWithProviders } from "../../../testing/renderWithProviders";
import { AccountDeletionRequestScreen } from "../AccountDeletionRequestScreen";
import * as queriesModule from "../../../api/privacyData/usePrivacyDataQueries";
import * as profileQueryModule from "../../../api/customer/useCustomerProfileQuery";
import { PrivacyRequest } from "../../../domain/privacyData";
import { ServerTimestamp } from "../../../domain/dates";

const mockGoBack = jest.fn();
const mockNavigate = jest.fn();
jest.mock("@react-navigation/native", () => ({
  ...jest.requireActual("@react-navigation/native"),
  useNavigation: () => ({ navigate: mockNavigate, goBack: mockGoBack }),
}));

function request(overrides: Partial<PrivacyRequest> = {}): PrivacyRequest {
  return {
    id: "r-1", requestNumber: "REQ-001", requestType: "right_to_erasure",
    status: "submitted", statusLabel: "Submitted", slaStatus: "on_track", slaLabel: "On Track",
    verificationStatus: "not_required",
    submittedAt: "2026-01-01T00:00:00Z" as ServerTimestamp, dueAt: null, completedAt: null,
    reason: "test", rejectionReason: null,
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

function mockProfile() {
  jest.spyOn(profileQueryModule, "useCustomerProfileQuery").mockReturnValue({
    data: { displayName: "Rajinder", fullName: "Rajinder Singh" },
    isPending: false, isError: false, refetch: jest.fn(),
  } as unknown as ReturnType<typeof profileQueryModule.useCustomerProfileQuery>);
}

function render() {
  return renderWithProviders(<AccountDeletionRequestScreen />);
}

describe("AccountDeletionRequestScreen", () => {
  afterEach(() => { jest.restoreAllMocks(); mockGoBack.mockClear(); mockNavigate.mockClear(); });

  it("shows the loading state while checking for an existing request", () => {
    mockRequests(undefined, true); mockProfile();
    const { getByText } = render();
    expect(getByText("Checking for an existing request…")).toBeTruthy();
  });

  it("shows the non-interactive active-request state instead of the form when one already exists", () => {
    mockRequests([request({ status: "under_review", statusLabel: "Under Review" })]); mockProfile();
    const { getByText, queryByText } = render();
    expect(getByText("You already have a deletion request in progress")).toBeTruthy();
    expect(queryByText("Continue")).toBeNull();
  });

  it("never mutates or submits merely by opening the screen", () => {
    mockRequests([]); mockProfile();
    render();
    expect(mockNavigate).not.toHaveBeenCalled();
  });

  it("shows the real account summary from the authenticated profile", () => {
    mockRequests([]); mockProfile();
    const { getByText } = render();
    expect(getByText("Rajinder")).toBeTruthy();
    expect(getByText("Fuvay customer account")).toBeTruthy();
  });

  it("shows the non-instant warning panel, never immediate-delete language", () => {
    mockRequests([]); mockProfile();
    const { getByText, queryByText } = render();
    expect(getByText("Your account is not deleted now")).toBeTruthy();
    expect(queryByText(/delete now|erase immediately|permanently delete instantly|guaranteed/i)).toBeNull();
  });

  it("disables Continue until a reason is entered", () => {
    mockRequests([]); mockProfile();
    const { getByLabelText } = render();
    const cont = getByLabelText("Continue");
    expect(cont.props.accessibilityState.disabled).toBe(true);
    fireEvent.changeText(getByLabelText("Reason for deletion"), "No longer needed");
    expect(cont.props.accessibilityState.disabled).toBe(false);
  });

  it("Continue navigates to Final Confirmation carrying the entered reason, without submitting anything", () => {
    mockRequests([]); mockProfile();
    const { getByLabelText } = render();
    fireEvent.changeText(getByLabelText("Reason for deletion"), "No longer needed");
    fireEvent.press(getByLabelText("Continue"));
    expect(mockNavigate).toHaveBeenCalledWith("DeleteAccountFinalConfirmation", { reason: "No longer needed" });
  });

  it("Keep my account returns without navigating forward", () => {
    mockRequests([]); mockProfile();
    const { getByLabelText } = render();
    fireEvent.press(getByLabelText("Keep my account"));
    expect(mockGoBack).toHaveBeenCalled();
    expect(mockNavigate).not.toHaveBeenCalled();
  });

  it("never claims records are fully erased -- only that eligible ones are retained per policy", () => {
    mockRequests([]); mockProfile();
    const { getByText, queryByText } = render();
    expect(getByText("Some records may be retained")).toBeTruthy();
    expect(queryByText(/all (your |)(data|records|information).{0,15}(erased|deleted)/i)).toBeNull();
  });

  it("Go back navigates via the back chevron", () => {
    mockRequests([]); mockProfile();
    const { getByLabelText } = render();
    fireEvent.press(getByLabelText("Go back"));
    expect(mockGoBack).toHaveBeenCalled();
  });
});
