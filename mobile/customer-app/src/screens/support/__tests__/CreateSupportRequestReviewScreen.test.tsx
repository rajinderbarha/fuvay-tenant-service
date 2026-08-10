import React from "react";
import { Alert } from "react-native";
import { fireEvent, waitFor } from "@testing-library/react-native";
import { renderWithProviders } from "../../../testing/renderWithProviders";
import { CreateSupportRequestReviewScreen } from "../CreateSupportRequestReviewScreen";
import * as bookingsQueryModule from "../../../api/customerBookings/useCustomerBookingsListQuery";
import * as supportRequestsApi from "../../../api/supportRequests/supportRequestsApi";
import * as wizardContextModule from "../SupportRequestWizardContext";
import * as networkStateModule from "../../../api/networkState";
import { CustomerBookingListItem } from "../../../domain/bookingList";
import { SupportRequestDraft, createEmptySupportRequestDraft } from "../../../domain/supportRequestDraft";
import { DomainError } from "../../../domain/errors";

const mockNavigate = jest.fn();
const mockGoBack = jest.fn();
const mockParentReplace = jest.fn();
const mockParentGoBack = jest.fn();
const mockParentNavigate = jest.fn();

jest.mock("@react-navigation/native", () => ({
  ...jest.requireActual("@react-navigation/native"),
  useNavigation: () => ({
    navigate: mockNavigate, goBack: mockGoBack,
    getParent: () => ({ replace: mockParentReplace, goBack: mockParentGoBack, navigate: mockParentNavigate }),
  }),
}));

function booking(overrides: Partial<CustomerBookingListItem> = {}): CustomerBookingListItem {
  return {
    bookingId: "b-1", bookingNumber: "FUV-2841", rawStatus: "confirmed",
    stage: "active" as never, statusLabel: "Request confirmed",
    activityText: null, supportingText: null, createdAt: null,
    serviceName: "AC Repair", jobType: null, summaryFields: [],
    urgency: null, scheduledDate: null, scheduledTimeWindow: null, latenessLabel: null,
    address: { label: null, formatted: "Model Town, Ludhiana", zipcode: null },
    pricing: { state: "unavailable" as never, inspection: null },
    ...overrides,
  };
}

function mockBookings(items: CustomerBookingListItem[], isPending = false) {
  jest.spyOn(bookingsQueryModule, "useCustomerBookingsListQuery").mockReturnValue({
    items, counts: { active: items.length, completed: 0, all: items.length },
    isPending, isError: false, isRefetching: false, isFetchingNextPage: false,
    hasNextPage: false, fetchNextPage: jest.fn(), refetch: jest.fn(), dataUpdatedAt: 0,
  } as unknown as ReturnType<typeof bookingsQueryModule.useCustomerBookingsListQuery>);
}

let currentDraft: SupportRequestDraft;
let resetDraftSpy: jest.Mock;
function mockWizard(initial: Partial<SupportRequestDraft>) {
  currentDraft = { ...createEmptySupportRequestDraft(), ...initial };
  resetDraftSpy = jest.fn();
  jest.spyOn(wizardContextModule, "useSupportRequestWizard").mockImplementation(() => ({
    draft: currentDraft,
    setDraft: (updater: SupportRequestDraft | ((d: SupportRequestDraft) => SupportRequestDraft)) => {
      currentDraft = typeof updater === "function" ? updater(currentDraft) : updater;
    },
    resetDraft: resetDraftSpy,
  }));
}

function render() {
  return renderWithProviders(<CreateSupportRequestReviewScreen />);
}

describe("CreateSupportRequestReviewScreen", () => {
  afterEach(() => {
    jest.restoreAllMocks();
    mockNavigate.mockClear(); mockGoBack.mockClear();
    mockParentReplace.mockClear(); mockParentGoBack.mockClear(); mockParentNavigate.mockClear();
  });

  it("shows the review of the real Step 1/2 draft data", () => {
    mockBookings([booking()]);
    mockWizard({ categoryCode: "booking_service", bookingId: "b-1", subject: "Need help with my AC booking", description: "My booking is confirmed but I need help." });
    const { getByText } = render();
    expect(getByText("Review before submitting")).toBeTruthy();
    expect(getByText("Booking & service")).toBeTruthy();
    expect(getByText("AC Repair · Booking FUV-2841")).toBeTruthy();
    expect(getByText("Need help with my AC booking")).toBeTruthy();
    expect(getByText("My booking is confirmed but I need help.")).toBeTruthy();
  });

  it("never renders an attachments section -- no customer attachment route exists", () => {
    mockBookings([booking()]);
    mockWizard({ categoryCode: "booking_service", bookingId: "b-1", description: "test" });
    const { queryByText } = render();
    expect(queryByText("Attachments")).toBeNull();
    expect(queryByText("Add evidence")).toBeNull();
  });

  it("never shows Save & exit, priority, SLA, agent, or refund promises", () => {
    mockBookings([booking()]);
    mockWizard({ categoryCode: "booking_service", bookingId: "b-1", description: "test" });
    const { queryByText } = render();
    expect(queryByText("Save & exit")).toBeNull();
    expect(queryByText(/priority|sla|assigned agent|refund|24\/7|live support|reply within/i)).toBeNull();
  });

  it("returns to Step 1 when required context is missing, never rendering an incomplete review", () => {
    mockBookings([]);
    mockWizard({ categoryCode: null, description: "test" });
    render();
    expect(mockGoBack).toHaveBeenCalled();
  });

  it("Edit topic navigates back to Topic, Edit details navigates back to Details", () => {
    mockBookings([booking()]);
    mockWizard({ categoryCode: "booking_service", bookingId: "b-1", description: "test" });
    const { getByLabelText } = render();
    fireEvent.press(getByLabelText("Edit topic and booking"));
    expect(mockNavigate).toHaveBeenCalledWith("Topic");
    fireEvent.press(getByLabelText("Edit request details"));
    expect(mockNavigate).toHaveBeenCalledWith("Details");
  });

  it("blocks submission and explains when a booking-applicable topic has no linked booking", () => {
    mockBookings([]);
    mockWizard({ categoryCode: "booking_service", bookingId: null, description: "test" });
    const { getByLabelText, getByText } = render();
    expect(getByText("A booking is required to submit this request.")).toBeTruthy();
    expect(getByLabelText("Submit request").props.accessibilityState.disabled).toBe(true);
  });

  it("submits only the allowlisted real backend fields -- never customer_id, tenant_id, status, priority or assignee", async () => {
    mockBookings([booking()]);
    mockWizard({ categoryCode: "booking_service", bookingId: "b-1", subject: "Need help", description: "test description" });
    const createSpy = jest.spyOn(supportRequestsApi, "createMySupportRequest").mockResolvedValue({
      data: { id: "c-1", complaint_number: "CMP-1", record_type: "service_booking", record_id: "b-1", booking_id: "b-1", complaint_type: "other", status: "open", title: "Need help", description: "test description", requested_resolution: null, customer_visible_summary: null, created_at: null, updated_at: null, resolved_at: null, closed_at: null },
      requestId: "req-1",
    } as unknown as Awaited<ReturnType<typeof supportRequestsApi.createMySupportRequest>>);

    const { getByLabelText } = render();
    fireEvent.press(getByLabelText("Submit request"));

    await waitFor(() => expect(createSpy).toHaveBeenCalledWith({
      record_type: "service_booking", record_id: "b-1", complaint_type: "other",
      description: "test description", title: "Need help",
    }));
    const sentPayload = createSpy.mock.calls[0][0] as Record<string, unknown>;
    for (const forbidden of ["customer_id", "tenant_id", "assigned_to", "assigned_staff_id", "status", "priority", "sla", "refund_status", "resolution"]) {
      expect(sentPayload).not.toHaveProperty(forbidden);
    }
  });

  it("replaces navigation to the real created request, preventing back-resubmission", async () => {
    mockBookings([booking()]);
    mockWizard({ categoryCode: "booking_service", bookingId: "b-1", description: "test" });
    jest.spyOn(supportRequestsApi, "createMySupportRequest").mockResolvedValue({
      data: { id: "c-9", complaint_number: "CMP-9", record_type: "service_booking", record_id: "b-1", booking_id: "b-1", complaint_type: "other", status: "open", title: null, description: "test", requested_resolution: null, customer_visible_summary: null, created_at: null, updated_at: null, resolved_at: null, closed_at: null },
      requestId: "req-1",
    } as unknown as Awaited<ReturnType<typeof supportRequestsApi.createMySupportRequest>>);

    const { getByLabelText } = render();
    fireEvent.press(getByLabelText("Submit request"));

    await waitFor(() => expect(mockParentReplace).toHaveBeenCalledWith("SupportRequestDetails", { requestId: "c-9" }));
    await waitFor(() => expect(resetDraftSpy).toHaveBeenCalled());
  });

  it("double-tapping Submit fires only one mutation", async () => {
    mockBookings([booking()]);
    mockWizard({ categoryCode: "booking_service", bookingId: "b-1", description: "test" });
    const createSpy = jest.spyOn(supportRequestsApi, "createMySupportRequest").mockResolvedValue({
      data: { id: "c-1", complaint_number: "CMP-1", record_type: "service_booking", record_id: "b-1", booking_id: "b-1", complaint_type: "other", status: "open", title: null, description: "test", requested_resolution: null, customer_visible_summary: null, created_at: null, updated_at: null, resolved_at: null, closed_at: null },
      requestId: "req-1",
    } as unknown as Awaited<ReturnType<typeof supportRequestsApi.createMySupportRequest>>);

    const { getByLabelText } = render();
    fireEvent.press(getByLabelText("Submit request"));
    fireEvent.press(getByLabelText("Submit request"));

    await waitFor(() => expect(createSpy).toHaveBeenCalledTimes(1));
  });

  it("shows the honest unknown-result copy on a network/timeout failure, never claiming the request was not submitted", async () => {
    mockBookings([booking()]);
    mockWizard({ categoryCode: "booking_service", bookingId: "b-1", description: "test" });
    jest.spyOn(supportRequestsApi, "createMySupportRequest").mockRejectedValue(
      new DomainError({ category: "NETWORK_UNAVAILABLE", diagnostic: "network down" }),
    );

    const { getByLabelText, getByText, queryByText } = render();
    fireEvent.press(getByLabelText("Submit request"));

    await waitFor(() => expect(getByText(/couldn't confirm whether your request was submitted/i)).toBeTruthy());
    expect(queryByText(/request not submitted/i)).toBeNull();
    expect(getByText("Check My support requests")).toBeTruthy();
  });

  it("shows a definitive recoverable error for a validation failure, preserving entered data", async () => {
    mockBookings([booking()]);
    mockWizard({ categoryCode: "booking_service", bookingId: "b-1", subject: "kept title", description: "test" });
    jest.spyOn(supportRequestsApi, "createMySupportRequest").mockRejectedValue(
      new DomainError({ category: "VALIDATION_FAILURE", diagnostic: "This booking is not eligible for a new request." }),
    );

    const { getByLabelText, getByText } = render();
    fireEvent.press(getByLabelText("Submit request"));

    await waitFor(() => expect(getByText("This booking is not eligible for a new request.")).toBeTruthy());
    expect(getByText("kept title")).toBeTruthy();
  });

  it("disables submission while offline, keeping the review visible", () => {
    jest.spyOn(networkStateModule, "isOffline").mockReturnValue(true);
    mockBookings([booking()]);
    mockWizard({ categoryCode: "booking_service", bookingId: "b-1", description: "test" });
    const { getByLabelText, getByText } = render();
    expect(getByLabelText("Submit request").props.accessibilityState.disabled).toBe(true);
    expect(getByText("Review before submitting")).toBeTruthy();
  });

  it("Cancel with entered content shows a discard confirmation before exiting the wizard", () => {
    mockBookings([booking()]);
    mockWizard({ categoryCode: "booking_service", bookingId: "b-1", description: "test" });
    const alertSpy = jest.spyOn(Alert, "alert").mockImplementation(() => {});
    const { getByLabelText } = render();
    fireEvent.press(getByLabelText("Cancel and discard this request"));
    expect(alertSpy).toHaveBeenCalledWith("Discard this request?", expect.any(String), expect.any(Array));
    expect(mockParentGoBack).not.toHaveBeenCalled();
  });
});
