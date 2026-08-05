import React from "react";
import { fireEvent } from "@testing-library/react-native";
import { renderWithProviders } from "../../../testing/renderWithProviders";
import { SupportRequestsScreen } from "../SupportRequestsScreen";
import * as queriesModule from "../../../api/supportRequests/useSupportRequestsQueries";
import * as networkStateModule from "../../../api/networkState";
import { SupportRequest } from "../../../domain/supportRequests";
import { ServerTimestamp } from "../../../domain/dates";

const mockNavigate = jest.fn();
const mockGoBack = jest.fn();
jest.mock("@react-navigation/native", () => ({
  ...jest.requireActual("@react-navigation/native"),
  useNavigation: () => ({ navigate: mockNavigate, goBack: mockGoBack }),
}));

function request(overrides: Partial<SupportRequest> = {}): SupportRequest {
  return {
    id: "c-1", complaintNumber: "CMP-1", recordType: "service_booking", recordId: "b-1",
    bookingId: "b-1", complaintType: "service_quality", status: "open",
    title: null, description: "Provider arrived late", requestedResolution: null, customerVisibleSummary: null,
    createdAt: "2026-01-01T00:00:00Z" as ServerTimestamp, updatedAt: null, resolvedAt: null, closedAt: null,
    ...overrides,
  };
}

function mockList(data: SupportRequest[] | undefined, isPending = false, isError = false, isRefetching = false) {
  const refetch = jest.fn();
  jest.spyOn(queriesModule, "useSupportRequestsListQuery").mockReturnValue({
    data, isPending, isError, isRefetching, refetch,
  } as unknown as ReturnType<typeof queriesModule.useSupportRequestsListQuery>);
  return refetch;
}

describe("SupportRequestsScreen", () => {
  afterEach(() => { jest.restoreAllMocks(); mockNavigate.mockClear(); });

  it("shows the loading state", () => {
    mockList(undefined, true);
    const { getByText } = renderWithProviders(<SupportRequestsScreen />);
    expect(getByText("Loading your requests…")).toBeTruthy();
  });

  it("defaults to the Active tab and shows its own empty copy", () => {
    mockList([]);
    const { getByText } = renderWithProviders(<SupportRequestsScreen />);
    expect(getByText("No active requests")).toBeTruthy();
  });

  it("switching to the Resolved tab shows its own empty copy", () => {
    mockList([]);
    const { getByText } = renderWithProviders(<SupportRequestsScreen />);
    fireEvent.press(getByText("Resolved"));
    expect(getByText("No resolved requests")).toBeTruthy();
  });

  it("switching to the All tab shows the general empty copy", () => {
    mockList([]);
    const { getByText } = renderWithProviders(<SupportRequestsScreen />);
    fireEvent.press(getByText("All"));
    expect(getByText("No support requests yet")).toBeTruthy();
  });

  it("classifies requests into Active vs Resolved from a single fetch, never a partial page", () => {
    mockList([
      request({ id: "c-1", status: "open" }),
      request({ id: "c-2", status: "under_admin_review" }),
      request({ id: "c-3", status: "resolved" }),
      request({ id: "c-4", status: "closed" }),
    ]);
    const { getByText, queryByText, getAllByText } = renderWithProviders(<SupportRequestsScreen />);
    // Active tab (default): both open + under_admin_review requests, no resolved/closed.
    expect(getAllByText("Service quality").length).toBe(2);

    fireEvent.press(getByText("Resolved"));
    expect(getAllByText("Service quality").length).toBe(2);

    fireEvent.press(getByText("All"));
    expect(getAllByText("Service quality").length).toBe(4);
    expect(queryByText("No support requests yet")).toBeNull();
  });

  it("renders real requests with their status and navigates to detail on tap", () => {
    mockList([request({ complaintType: "late_arrival", status: "under_admin_review" })]);
    const { getByText } = renderWithProviders(<SupportRequestsScreen />);
    expect(getByText("Late arrival")).toBeTruthy();
    expect(getByText("Under review")).toBeTruthy();
    fireEvent.press(getByText("Late arrival"));
    expect(mockNavigate).toHaveBeenCalledWith("SupportRequestDetails", { requestId: "c-1" });
  });

  it("shows a booking link that navigates to Booking Details independently of the card tap", () => {
    mockList([request({ bookingId: "b-42" })]);
    const { getByLabelText } = renderWithProviders(<SupportRequestsScreen />);
    fireEvent.press(getByLabelText("View linked booking"));
    expect(mockNavigate).toHaveBeenCalledWith("BookingDetails", { bookingId: "b-42" });
  });

  it("omits the booking link when the request has no linked booking", () => {
    mockList([request({ bookingId: null })]);
    const { queryByLabelText } = renderWithProviders(<SupportRequestsScreen />);
    expect(queryByLabelText("View linked booking")).toBeNull();
  });

  it("never renders a raw booking UUID", () => {
    mockList([request({ bookingId: "11111111-2222-3333-4444-555555555555" })]);
    const { queryByText } = renderWithProviders(<SupportRequestsScreen />);
    expect(queryByText("11111111-2222-3333-4444-555555555555")).toBeNull();
  });

  it("shows a recoverable error state on first-load failure", () => {
    mockList(undefined, false, true);
    const { getByText } = renderWithProviders(<SupportRequestsScreen />);
    expect(getByText("We couldn't load your requests.")).toBeTruthy();
  });

  it("preserves the last-known list and shows recoverable copy on a refresh error", () => {
    mockList([request()], false, true);
    const { getByText } = renderWithProviders(<SupportRequestsScreen />);
    expect(getByText("Service quality")).toBeTruthy();
    expect(getByText("We couldn't refresh your requests. Showing the last known list.")).toBeTruthy();
  });

  it("shows an offline message when there is no cached data at all", () => {
    jest.spyOn(networkStateModule, "isOffline").mockReturnValue(true);
    mockList(undefined);
    const { getByText } = renderWithProviders(<SupportRequestsScreen />);
    expect(getByText("Connect to the internet to view your support requests.")).toBeTruthy();
  });

  it("New request opens Step 1 of the create-support-request wizard", () => {
    mockList([]);
    const { getByText } = renderWithProviders(<SupportRequestsScreen />);
    fireEvent.press(getByText("New request"));
    expect(mockNavigate).toHaveBeenCalledWith("CreateSupportRequest", { source: "support_requests" });
  });

  it("shows Status unavailable for an unrecognized backend status, never the raw enum", () => {
    mockList([request({ status: "some_future_status_v9" })]);
    const { getByText, queryByText } = renderWithProviders(<SupportRequestsScreen />);
    fireEvent.press(getByText("All"));
    expect(getByText("Status unavailable")).toBeTruthy();
    expect(queryByText("some_future_status_v9")).toBeNull();
  });

  it("triggers a refetch from the header refresh action", () => {
    const refetch = mockList([request()]);
    const { getByLabelText } = renderWithProviders(<SupportRequestsScreen />);
    fireEvent.press(getByLabelText("Refresh"));
    expect(refetch).toHaveBeenCalled();
  });

  it("always shows the pull-to-refresh footer hint, never claiming real-time delivery", () => {
    mockList([request()]);
    const { getByText, queryByText } = renderWithProviders(<SupportRequestsScreen />);
    expect(getByText("Pull down to check for updates.")).toBeTruthy();
    expect(queryByText(/live|real-time/i)).toBeNull();
  });
});
