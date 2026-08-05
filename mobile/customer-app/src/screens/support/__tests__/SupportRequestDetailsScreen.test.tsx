import React from "react";
import { fireEvent } from "@testing-library/react-native";
import { renderWithProviders } from "../../../testing/renderWithProviders";
import { SupportRequestDetailsScreen } from "../SupportRequestDetailsScreen";
import * as queriesModule from "../../../api/supportRequests/useSupportRequestsQueries";
import * as bookingsModule from "../../../api/customerBookings/useCustomerBookingsListQuery";
import { SupportRequest } from "../../../domain/supportRequests";
import { ServerTimestamp } from "../../../domain/dates";

const mockNavigate = jest.fn();
const mockGoBack = jest.fn();
jest.mock("@react-navigation/native", () => ({
  ...jest.requireActual("@react-navigation/native"),
  useNavigation: () => ({ navigate: mockNavigate, goBack: mockGoBack }),
  useRoute: () => ({ name: "SupportRequestDetails", params: { requestId: "c-1" } }),
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

function mockDetail(
  result: { kind: "found"; request: SupportRequest } | { kind: "unavailable" } | undefined,
  opts: { isPending?: boolean; isRefetching?: boolean } = {},
) {
  jest.spyOn(queriesModule, "useSupportRequestDetailQuery").mockReturnValue({
    data: result, isPending: !!opts.isPending, isError: false,
    isRefetching: !!opts.isRefetching, refetch: jest.fn(),
  } as unknown as ReturnType<typeof queriesModule.useSupportRequestDetailQuery>);
}

function mockMessages(data: unknown[] = []) {
  jest.spyOn(queriesModule, "useSupportRequestMessagesQuery").mockReturnValue({
    data, isPending: false, refetch: jest.fn(),
  } as unknown as ReturnType<typeof queriesModule.useSupportRequestMessagesQuery>);
}

function mockCancel() {
  jest.spyOn(queriesModule, "useCancelSupportRequestMutation").mockReturnValue({
    mutateAsync: jest.fn(), isPending: false,
  } as unknown as ReturnType<typeof queriesModule.useCancelSupportRequestMutation>);
}

function mockAddMessage() {
  jest.spyOn(queriesModule, "useAddSupportRequestMessageMutation").mockReturnValue({
    mutateAsync: jest.fn(), isPending: false,
  } as unknown as ReturnType<typeof queriesModule.useAddSupportRequestMessageMutation>);
}

function mockBookings(items: Array<{ bookingId: string; serviceName: string | null; bookingNumber: string | null }> = []) {
  jest.spyOn(bookingsModule, "useCustomerBookingsListQuery").mockReturnValue({
    items, isPending: false, isError: false, isRefetching: false,
  } as unknown as ReturnType<typeof bookingsModule.useCustomerBookingsListQuery>);
}

describe("SupportRequestDetailsScreen", () => {
  afterEach(() => { jest.restoreAllMocks(); mockGoBack.mockClear(); mockNavigate.mockClear(); });

  it("shows the enumeration-safe unavailable state for a missing or foreign request", () => {
    mockDetail({ kind: "unavailable" });
    mockMessages(); mockCancel(); mockAddMessage(); mockBookings();
    const { getByText } = renderWithProviders(<SupportRequestDetailsScreen />);
    expect(getByText("This request is unavailable.")).toBeTruthy();
  });

  it("shows real status and description, never a fabricated agent or resolution time", () => {
    mockDetail({ kind: "found", request: request({ status: "under_admin_review" }) });
    mockMessages(); mockCancel(); mockAddMessage(); mockBookings();
    const { getByText, queryByText } = renderWithProviders(<SupportRequestDetailsScreen />);
    expect(getByText("Under review")).toBeTruthy();
    expect(getByText("Provider arrived late")).toBeTruthy();
    expect(queryByText(/agent|resolution time|\bETA\b/i)).toBeNull();
  });

  it("shows Cancel request only when the real backend allows it (status open)", () => {
    mockDetail({ kind: "found", request: request({ status: "open" }) });
    mockMessages(); mockCancel(); mockAddMessage(); mockBookings();
    const { getByText } = renderWithProviders(<SupportRequestDetailsScreen />);
    expect(getByText("Cancel request")).toBeTruthy();
  });

  it("hides Cancel request once the status has moved past 'open'", () => {
    mockDetail({ kind: "found", request: request({ status: "under_admin_review" }) });
    mockMessages(); mockCancel(); mockAddMessage(); mockBookings();
    const { queryByText } = renderWithProviders(<SupportRequestDetailsScreen />);
    expect(queryByText("Cancel request")).toBeNull();
  });

  it("shows the resolved hero with the real resolution timestamp and a safe reference, never a raw UUID", () => {
    mockDetail({ kind: "found", request: request({
      status: "resolved", resolvedAt: "2026-08-01T10:18:00Z" as ServerTimestamp,
    }) });
    mockMessages(); mockCancel(); mockAddMessage(); mockBookings();
    const { getByText, getAllByText, queryByText } = renderWithProviders(<SupportRequestDetailsScreen />);
    expect(getByText("Your request has been resolved")).toBeTruthy();
    expect(getByText(/Resolved on/)).toBeTruthy();
    expect(getAllByText("Request CMP-1").length).toBeGreaterThan(0);
    expect(queryByText("c-1")).toBeNull();
  });

  it("uses closed-state language (not 'resolved') when the real status is closed", () => {
    mockDetail({ kind: "found", request: request({
      status: "closed", closedAt: "2026-08-01T10:18:00Z" as ServerTimestamp,
    }) });
    mockMessages(); mockCancel(); mockAddMessage(); mockBookings();
    const { getByText, queryByText } = renderWithProviders(<SupportRequestDetailsScreen />);
    expect(getByText("This request has been closed")).toBeTruthy();
    expect(queryByText("Your request has been resolved")).toBeNull();
  });

  it("renders the real customer-visible resolution summary when present", () => {
    mockDetail({ kind: "found", request: request({
      status: "resolved", customerVisibleSummary: "Your booking remains active. You can follow its progress from My Bookings.",
    }) });
    mockMessages(); mockCancel(); mockAddMessage(); mockBookings();
    const { getByText } = renderWithProviders(<SupportRequestDetailsScreen />);
    expect(getByText("Your booking remains active. You can follow its progress from My Bookings.")).toBeTruthy();
  });

  it("falls back to a generic resolution line when no customer-visible summary exists, never fabricating detail", () => {
    mockDetail({ kind: "found", request: request({ status: "resolved", customerVisibleSummary: null }) });
    mockMessages(); mockCancel(); mockAddMessage(); mockBookings();
    const { getByText } = renderWithProviders(<SupportRequestDetailsScreen />);
    expect(getByText("This request has been marked as resolved.")).toBeTruthy();
  });

  it("keeps the message composer for a resolved request, matching the real backend contract", () => {
    mockDetail({ kind: "found", request: request({ status: "resolved" }) });
    mockMessages(); mockCancel(); mockAddMessage(); mockBookings();
    const { getByLabelText, queryByText } = renderWithProviders(<SupportRequestDetailsScreen />);
    expect(getByLabelText("Add a message")).toBeTruthy();
    expect(queryByText("This conversation is now read-only.")).toBeNull();
  });

  it("removes the composer and shows read-only copy for a closed request", () => {
    mockDetail({ kind: "found", request: request({ status: "closed" }) });
    mockMessages(); mockCancel(); mockAddMessage(); mockBookings();
    const { queryByLabelText, getByText } = renderWithProviders(<SupportRequestDetailsScreen />);
    expect(queryByLabelText("Add a message")).toBeNull();
    expect(getByText("This conversation is now read-only.")).toBeTruthy();
  });

  it("renames the conversation section to 'Conversation history'", () => {
    mockDetail({ kind: "found", request: request({ status: "open" }) });
    mockMessages(); mockCancel(); mockAddMessage(); mockBookings();
    const { getByText, queryByText } = renderWithProviders(<SupportRequestDetailsScreen />);
    expect(getByText("Conversation history")).toBeTruthy();
    expect(queryByText("Messages")).toBeNull();
  });

  it("shows the linked booking card with safe fields only and navigates to BookingDetails", () => {
    mockDetail({ kind: "found", request: request({ status: "resolved", bookingId: "b-1" }) });
    mockMessages();
    mockCancel(); mockAddMessage();
    mockBookings([{ bookingId: "b-1", serviceName: "AC Repair", bookingNumber: "FUV-2841" }]);
    const { getByText, getAllByLabelText } = renderWithProviders(<SupportRequestDetailsScreen />);
    expect(getByText("AC Repair")).toBeTruthy();
    expect(getByText("Booking FUV-2841")).toBeTruthy();
    getAllByLabelText("View booking")[0].props.onPress();
    expect(mockNavigate).toHaveBeenCalledWith("BookingDetails", { bookingId: "b-1" });
  });

  it("omits the linked booking card when the booking can't be resolved to a safe record", () => {
    mockDetail({ kind: "found", request: request({ status: "resolved", bookingId: "b-missing" }) });
    mockMessages(); mockCancel(); mockAddMessage(); mockBookings([]);
    const { queryByText } = renderWithProviders(<SupportRequestDetailsScreen />);
    expect(queryByText("Linked booking")).toBeNull();
  });

  it("shows 'Back to support' for a resolved request and navigates to My Support Requests", () => {
    mockDetail({ kind: "found", request: request({ status: "resolved" }) });
    mockMessages(); mockCancel(); mockAddMessage(); mockBookings();
    const { getByText } = renderWithProviders(<SupportRequestDetailsScreen />);
    fireEvent.press(getByText("Back to support"));
    expect(mockNavigate).toHaveBeenCalledWith("SupportRequests");
  });

  it("never renders feedback controls -- no real backend write endpoint exists for this", () => {
    mockDetail({ kind: "found", request: request({ status: "resolved" }) });
    mockMessages(); mockCancel(); mockAddMessage(); mockBookings();
    const { queryByText } = renderWithProviders(<SupportRequestDetailsScreen />);
    expect(queryByText(/was this resolution helpful/i)).toBeNull();
    expect(queryByText(/^Helpful$/)).toBeNull();
    expect(queryByText(/^Not helpful$/)).toBeNull();
  });

  it("does not render the resolved hero, resolution section, or 'Back to support' for a still-active request", () => {
    mockDetail({ kind: "found", request: request({ status: "open" }) });
    mockMessages(); mockCancel(); mockAddMessage(); mockBookings();
    const { queryByText } = renderWithProviders(<SupportRequestDetailsScreen />);
    expect(queryByText("Your request has been resolved")).toBeNull();
    expect(queryByText("Resolution")).toBeNull();
    expect(queryByText("Back to support")).toBeNull();
  });
});
