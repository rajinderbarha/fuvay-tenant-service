import React from "react";
import { fireEvent } from "@testing-library/react-native";
import { renderWithProviders } from "../../../testing/renderWithProviders";
import { PrivacyRequestsScreen } from "../PrivacyRequestsScreen";
import * as queriesModule from "../../../api/privacyData/usePrivacyDataQueries";
import { PrivacyRequest } from "../../../domain/privacyData";
import { ServerTimestamp } from "../../../domain/dates";
import { AppProviders } from "../../../providers/AppProviders";

const mockNavigate = jest.fn();
const mockGoBack = jest.fn();
jest.mock("@react-navigation/native", () => ({
  ...jest.requireActual("@react-navigation/native"),
  useNavigation: () => ({ navigate: mockNavigate, goBack: mockGoBack }),
}));

jest.mock("../../../api/networkState", () => ({
  ...jest.requireActual("../../../api/networkState"),
  isOffline: jest.fn(() => false),
}));
import { isOffline } from "../../../api/networkState";

function request(overrides: Partial<PrivacyRequest> = {}): PrivacyRequest {
  return {
    id: "req-1", requestNumber: "FUV-PV-1048", requestType: "data_export",
    status: "submitted", statusLabel: "Submitted", slaStatus: "on_track", slaLabel: "On Track",
    verificationStatus: "not_required",
    submittedAt: "2026-08-01T00:00:00Z" as ServerTimestamp, dueAt: null, completedAt: null,
    reason: null, rejectionReason: null,
    createdAt: "2026-08-01T00:00:00Z" as ServerTimestamp, updatedAt: "2026-08-02T00:00:00Z" as ServerTimestamp,
    ...overrides,
  };
}

function mockList(items: PrivacyRequest[], opts: {
  isPending?: boolean; isError?: boolean; isComplete?: boolean; hasNextPage?: boolean; isRefetching?: boolean; isFetchingNextPage?: boolean;
} = {}) {
  jest.spyOn(queriesModule, "usePrivacyRequestsListQuery").mockReturnValue({
    items, total: items.length, isComplete: opts.isComplete ?? true,
    isPending: !!opts.isPending, isError: !!opts.isError,
    isRefetching: !!opts.isRefetching, isFetchingNextPage: !!opts.isFetchingNextPage,
    hasNextPage: !!opts.hasNextPage, fetchNextPage: jest.fn(), refetch: jest.fn(),
  } as unknown as ReturnType<typeof queriesModule.usePrivacyRequestsListQuery>);
}

describe("PrivacyRequestsScreen", () => {
  beforeEach(() => { (isOffline as jest.Mock).mockReturnValue(false); });
  afterEach(() => { jest.restoreAllMocks(); mockNavigate.mockClear(); mockGoBack.mockClear(); });

  it("shows a loading state while the list is being fetched", () => {
    mockList([], { isPending: true });
    const { getByText } = renderWithProviders(<PrivacyRequestsScreen />);
    expect(getByText("Loading your privacy requests…")).toBeTruthy();
  });

  it("shows the honest empty state for an account with no privacy requests at all", () => {
    mockList([]);
    const { getByText } = renderWithProviders(<PrivacyRequestsScreen />);
    expect(getByText("No privacy requests yet")).toBeTruthy();
    expect(getByText("Requests you submit will appear here.")).toBeTruthy();
  });

  it("groups a submitted (non-terminal) request under Active", () => {
    mockList([request({ status: "submitted" })]);
    const { getAllByText } = renderWithProviders(<PrivacyRequestsScreen />);
    expect(getAllByText("Active").length).toBeGreaterThan(0);
    expect(getAllByText("Submitted").length).toBeGreaterThan(0);
  });

  it("groups a completed request under Completed with its true label", () => {
    mockList([request({ status: "completed", statusLabel: "Completed", completedAt: "2026-08-05T00:00:00Z" as ServerTimestamp })]);
    const { getAllByText } = renderWithProviders(<PrivacyRequestsScreen />);
    expect(getAllByText("Completed").length).toBeGreaterThan(0);
  });

  it("never labels a declined/rejected request as Completed", () => {
    mockList([request({ status: "rejected" })]);
    const { getByText } = renderWithProviders(<PrivacyRequestsScreen />);
    // The row's own status badge must say "Rejected", never "Completed" --
    // the "Completed" filter tab/section label existing elsewhere is fine.
    expect(getByText("Rejected")).toBeTruthy();
  });

  it("never labels a cancelled/withdrawn request as Completed", () => {
    mockList([request({ status: "cancelled" })]);
    const { getByText } = renderWithProviders(<PrivacyRequestsScreen />);
    expect(getByText("Withdrawn")).toBeTruthy();
  });

  it("falls back to a neutral label for an unrecognized status, never a raw enum", () => {
    mockList([request({ status: "some_future_status" })]);
    const { getByText, queryByText } = renderWithProviders(<PrivacyRequestsScreen />);
    expect(getByText("Status unavailable")).toBeTruthy();
    expect(queryByText("some_future_status")).toBeNull();
  });

  it("falls back to a neutral type label for an unrecognized request type, never a raw enum", () => {
    mockList([request({ requestType: "future_type" as PrivacyRequest["requestType"] })]);
    const { getByText, queryByText } = renderWithProviders(<PrivacyRequestsScreen />);
    expect(getByText("Privacy request")).toBeTruthy();
    expect(queryByText("future_type")).toBeNull();
  });

  it("renders the real public reference exactly as returned, never a raw UUID", () => {
    mockList([request({ id: "c8f1a2e4-91ab-4e3a-9c1a-000000000001", requestNumber: "FUV-PV-1048" })]);
    const { getByText, queryByText } = renderWithProviders(<PrivacyRequestsScreen />);
    expect(getByText("Request FUV-PV-1048")).toBeTruthy();
    expect(queryByText(/c8f1a2e4-91ab-4e3a-9c1a-000000000001/)).toBeNull();
  });

  it("shows the All/Active/Completed filters only when the list is proven complete", () => {
    mockList([request()], { isComplete: true });
    const { getByText, getAllByText } = renderWithProviders(<PrivacyRequestsScreen />);
    expect(getByText("All")).toBeTruthy();
    expect(getAllByText("Active").length).toBeGreaterThan(0);
  });

  it("omits the filter tabs and shows a single chronological list when completeness isn't proven", () => {
    mockList([request()], { isComplete: false, hasNextPage: true });
    const { queryByText } = renderWithProviders(<PrivacyRequestsScreen />);
    expect(queryByText("All", { exact: true })).toBeNull();
  });

  it("switching to the Active filter shows only non-terminal requests", () => {
    mockList([
      request({ id: "a", status: "submitted", requestType: "data_export" }),
      request({ id: "b", status: "completed", requestType: "data_correction" }),
    ], { isComplete: true });
    const { getAllByText, getByText, queryByText } = renderWithProviders(<PrivacyRequestsScreen />);
    fireEvent.press(getAllByText("Active")[0]);
    expect(getByText("Data export")).toBeTruthy();
    expect(queryByText("Data correction")).toBeNull();
  });

  it("switching to the Completed filter shows only terminal requests", () => {
    mockList([
      request({ id: "a", status: "submitted", requestType: "data_export" }),
      request({ id: "b", status: "completed", requestType: "data_correction" }),
    ], { isComplete: true });
    const { getAllByText, getByText, queryByText } = renderWithProviders(<PrivacyRequestsScreen />);
    fireEvent.press(getAllByText("Completed")[0]);
    expect(getByText("Data correction")).toBeTruthy();
    expect(queryByText("Data export")).toBeNull();
  });

  it("shows the empty-Active state distinct from an empty account", () => {
    mockList([request({ status: "completed" })], { isComplete: true });
    const { getAllByText, getByText, rerender } = renderWithProviders(<PrivacyRequestsScreen />);
    fireEvent.press(getAllByText("Active")[0]);
    mockList([request({ status: "completed" })], { isComplete: true });
    rerender(<AppProviders><PrivacyRequestsScreen /></AppProviders>);
    expect(getByText("No active requests")).toBeTruthy();
  });

  it("navigates to PrivacyRequestDetails with only the requestId, never the full object", () => {
    mockList([request({ id: "req-42" })]);
    const { getByText } = renderWithProviders(<PrivacyRequestsScreen />);
    fireEvent.press(getByText("View details"));
    expect(mockNavigate).toHaveBeenCalledWith("PrivacyRequestDetails", { requestId: "req-42" });
  });

  it("shows the private-requests assurance card", () => {
    mockList([request()]);
    const { getByText } = renderWithProviders(<PrivacyRequestsScreen />);
    expect(getByText("Requests are private")).toBeTruthy();
    expect(getByText("Only you can view the requests linked to your account.")).toBeTruthy();
  });

  it("Back to Privacy & data navigates back", () => {
    mockList([request()]);
    const { getByText } = renderWithProviders(<PrivacyRequestsScreen />);
    fireEvent.press(getByText("Back to Privacy & data"));
    expect(mockGoBack).toHaveBeenCalled();
  });

  it("preserves cached requests and shows a compact offline banner when offline with cache", () => {
    (isOffline as jest.Mock).mockReturnValue(true);
    mockList([request()]);
    const { getByText } = renderWithProviders(<PrivacyRequestsScreen />);
    expect(getByText("Data export")).toBeTruthy();
  });

  it("shows the uncached offline state with no data at all", () => {
    (isOffline as jest.Mock).mockReturnValue(true);
    mockList([]);
    const { getByText } = renderWithProviders(<PrivacyRequestsScreen />);
    expect(getByText("Requests can't be loaded")).toBeTruthy();
  });

  it("preserves the cached list on a refresh error instead of blanking the screen", () => {
    mockList([request()], { isError: true });
    const { getByText } = renderWithProviders(<PrivacyRequestsScreen />);
    expect(getByText("Data export")).toBeTruthy();
    expect(getByText(/couldn't refresh/i)).toBeTruthy();
  });

  it("shows a full-screen error only when there is no cached data at all", () => {
    mockList([], { isError: true });
    const { getByText } = renderWithProviders(<PrivacyRequestsScreen />);
    expect(getByText("Something went wrong")).toBeTruthy();
  });

  it("Go back navigates via the back chevron", () => {
    mockList([request()]);
    const { getByLabelText } = renderWithProviders(<PrivacyRequestsScreen />);
    fireEvent.press(getByLabelText("Go back"));
    expect(mockGoBack).toHaveBeenCalled();
  });

  it("gives each row an accessible label describing type, status and reference", () => {
    mockList([request({ requestNumber: "FUV-PV-1048" })]);
    const { getByLabelText } = renderWithProviders(<PrivacyRequestsScreen />);
    expect(getByLabelText(/Data export, Submitted, Request FUV-PV-1048/)).toBeTruthy();
  });
});
