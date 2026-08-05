import React from "react";
import { Alert } from "react-native";
import { fireEvent } from "@testing-library/react-native";
import { renderWithProviders } from "../../../testing/renderWithProviders";
import { AppProviders } from "../../../providers/AppProviders";
import { CreateSupportRequestTopicScreen } from "../CreateSupportRequestTopicScreen";
import * as bookingsQueryModule from "../../../api/customerBookings/useCustomerBookingsListQuery";
import * as wizardContextModule from "../SupportRequestWizardContext";
import { CustomerBookingListItem } from "../../../domain/bookingList";
import { SupportRequestDraft, createEmptySupportRequestDraft } from "../../../domain/supportRequestDraft";

const mockNavigate = jest.fn();
const mockGoBack = jest.fn();
const mockParentNavigate = jest.fn();
let mockRouteParams: Record<string, unknown> | undefined = undefined;

jest.mock("@react-navigation/native", () => ({
  ...jest.requireActual("@react-navigation/native"),
  useNavigation: () => ({
    navigate: mockNavigate, goBack: mockGoBack,
    getParent: () => ({ navigate: mockParentNavigate, goBack: mockGoBack }),
  }),
  useRoute: () => ({ name: "Topic", params: mockRouteParams }),
}));

function booking(overrides: Partial<CustomerBookingListItem> = {}): CustomerBookingListItem {
  return {
    bookingId: "b-1", bookingNumber: "FUV-2841", rawStatus: "confirmed",
    stage: "active" as never, statusLabel: "Request confirmed",
    activityText: null, supportingText: null, createdAt: null,
    serviceName: "AC Repair", jobType: null, summaryFields: [],
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
function mockWizard() {
  currentDraft = createEmptySupportRequestDraft();
  jest.spyOn(wizardContextModule, "useSupportRequestWizard").mockImplementation(() => ({
    draft: currentDraft,
    setDraft: (updater: SupportRequestDraft | ((d: SupportRequestDraft) => SupportRequestDraft)) => {
      currentDraft = typeof updater === "function" ? updater(currentDraft) : updater;
    },
    resetDraft: () => { currentDraft = createEmptySupportRequestDraft(); },
  }));
}

function render() {
  return renderWithProviders(<CreateSupportRequestTopicScreen />);
}

describe("CreateSupportRequestTopicScreen", () => {
  afterEach(() => { jest.restoreAllMocks(); mockNavigate.mockClear(); mockGoBack.mockClear(); mockParentNavigate.mockClear(); mockRouteParams = undefined; });

  it("shows the step header and progress labels", () => {
    mockBookings([]); mockWizard();
    const { getByText } = render();
    expect(getByText("Create request")).toBeTruthy();
    expect(getByText("Step 1 of 3")).toBeTruthy();
    expect(getByText("Topic & context")).toBeTruthy();
  });

  it("shows only the real confirmed topics -- no fabricated categories", () => {
    mockBookings([]); mockWizard();
    const { getByText, queryByText } = render();
    expect(getByText("Booking & service")).toBeTruthy();
    expect(getByText("Account & security")).toBeTruthy();
    expect(getByText("Pricing question")).toBeTruthy();
    expect(getByText("Something else")).toBeTruthy();
    expect(queryByText("Safety concern")).toBeNull();
  });

  it("never shows unsupported Step-1 fields (priority, attachments, description, agent, SLA)", () => {
    mockBookings([]); mockWizard();
    const { queryByText, queryByLabelText } = render();
    expect(queryByText(/priority|urgency|sla|assigned agent|expected response/i)).toBeNull();
    expect(queryByLabelText("Description")).toBeNull();
    expect(queryByText("Attachments")).toBeNull();
  });

  it("Continue is disabled until a non-rerouting topic is selected", () => {
    mockBookings([]); mockWizard();
    const { getByLabelText, rerender } = render();
    let continueBtn = getByLabelText("Continue");
    expect(continueBtn.props.accessibilityState.disabled).toBe(true);

    fireEvent.press(getByLabelText("Booking & service: A current or past service"));
    rerender(<AppProviders><CreateSupportRequestTopicScreen /></AppProviders>);
    continueBtn = getByLabelText("Continue");
    expect(continueBtn.props.accessibilityState.disabled).toBe(false);
  });

  it("selecting Account & security reroutes to the real Security screen instead of continuing the wizard", () => {
    mockBookings([]); mockWizard();
    const { getByLabelText } = render();
    fireEvent.press(getByLabelText("Account & security: Sign-in or account access"));
    expect(mockParentNavigate).toHaveBeenCalledWith("Security", undefined);
  });

  it("shows Link a booking only for booking-applicable topics", () => {
    mockBookings([]); mockWizard();
    const { getByLabelText, getByText, queryByText, rerender } = render();
    expect(queryByText("Link a booking")).toBeNull();

    fireEvent.press(getByLabelText("Pricing question: Service price or visit fee"));
    rerender(<AppProviders><CreateSupportRequestTopicScreen /></AppProviders>);
    expect(getByText("Link a booking")).toBeTruthy();
    expect(getByText("Optional")).toBeTruthy();
  });

  it("only lets the customer choose from their own real bookings", () => {
    mockBookings([booking()]); mockWizard();
    const { getByLabelText, getByText, rerender } = render();
    fireEvent.press(getByLabelText("Booking & service: A current or past service"));
    rerender(<AppProviders><CreateSupportRequestTopicScreen /></AppProviders>);
    fireEvent.press(getByText("Choose a booking"));
    expect(getByText("AC Repair")).toBeTruthy();
    fireEvent.press(getByText("AC Repair"));
    rerender(<AppProviders><CreateSupportRequestTopicScreen /></AppProviders>);
    expect(getByText("Booking FUV-2841")).toBeTruthy();
  });

  it("a foreign/unavailable booking id passed via route params is never displayed or trusted", () => {
    mockRouteParams = { bookingId: "not-mine-or-deleted" };
    mockBookings([booking()]); mockWizard();
    const { getByLabelText, queryByText, rerender } = render();
    fireEvent.press(getByLabelText("Booking & service: A current or past service"));
    rerender(<AppProviders><CreateSupportRequestTopicScreen /></AppProviders>);
    expect(queryByText("Booking FUV-2841")).toBeNull();
  });

  it("Continue carries the draft forward without any backend mutation", () => {
    mockBookings([]); mockWizard();
    const { getByLabelText, rerender } = render();
    fireEvent.press(getByLabelText("Booking & service: A current or past service"));
    rerender(<AppProviders><CreateSupportRequestTopicScreen /></AppProviders>);
    fireEvent.press(getByLabelText("Continue"));
    expect(mockNavigate).toHaveBeenCalledWith("Details");
  });

  it("Cancel with no selection leaves immediately, no discard prompt", () => {
    mockBookings([]); mockWizard();
    const alertSpy = jest.spyOn(Alert, "alert");
    const { getByText } = render();
    fireEvent.press(getByText("Cancel"));
    expect(alertSpy).not.toHaveBeenCalled();
    expect(mockGoBack).toHaveBeenCalled();
  });

  it("Cancel with a dirty draft shows a discard confirmation", () => {
    mockBookings([]); mockWizard();
    const alertSpy = jest.spyOn(Alert, "alert").mockImplementation(() => {});
    const { getByLabelText, getByText, rerender } = render();
    fireEvent.press(getByLabelText("Booking & service: A current or past service"));
    rerender(<AppProviders><CreateSupportRequestTopicScreen /></AppProviders>);
    fireEvent.press(getByText("Cancel"));
    expect(alertSpy).toHaveBeenCalledWith("Discard this request?", expect.any(String), expect.any(Array));
    expect(mockGoBack).not.toHaveBeenCalled();
  });

  it("shows the honest privacy copy, never claiming end-to-end encryption", () => {
    mockBookings([]); mockWizard();
    const { getByText, queryByText } = render();
    expect(getByText("Your request is linked to your Fuvay account")).toBeTruthy();
    expect(queryByText(/end-to-end encrypt/i)).toBeNull();
  });
});
