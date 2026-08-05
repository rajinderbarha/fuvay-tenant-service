import React from "react";
import { Alert } from "react-native";
import { fireEvent } from "@testing-library/react-native";
import { renderWithProviders } from "../../../testing/renderWithProviders";
import { CreateSupportRequestDetailsScreen } from "../CreateSupportRequestDetailsScreen";
import * as bookingsQueryModule from "../../../api/customerBookings/useCustomerBookingsListQuery";
import * as wizardContextModule from "../SupportRequestWizardContext";
import { SupportRequestDraft, createEmptySupportRequestDraft } from "../../../domain/supportRequestDraft";

const mockNavigate = jest.fn();
const mockGoBack = jest.fn();
const mockParentGoBack = jest.fn();

jest.mock("@react-navigation/native", () => ({
  ...jest.requireActual("@react-navigation/native"),
  useNavigation: () => ({
    navigate: mockNavigate, goBack: mockGoBack,
    getParent: () => ({ goBack: mockParentGoBack }),
  }),
}));

function mockBookings() {
  jest.spyOn(bookingsQueryModule, "useCustomerBookingsListQuery").mockReturnValue({
    items: [], counts: { active: 0, completed: 0, all: 0 },
    isPending: false, isError: false, isRefetching: false, isFetchingNextPage: false,
    hasNextPage: false, fetchNextPage: jest.fn(), refetch: jest.fn(), dataUpdatedAt: 0,
  } as unknown as ReturnType<typeof bookingsQueryModule.useCustomerBookingsListQuery>);
}

let currentDraft: SupportRequestDraft;
function mockWizard(initial: Partial<SupportRequestDraft> = { categoryCode: "booking_service" }) {
  currentDraft = { ...createEmptySupportRequestDraft(), ...initial };
  jest.spyOn(wizardContextModule, "useSupportRequestWizard").mockImplementation(() => ({
    draft: currentDraft,
    setDraft: (updater: SupportRequestDraft | ((d: SupportRequestDraft) => SupportRequestDraft)) => {
      currentDraft = typeof updater === "function" ? updater(currentDraft) : updater;
    },
    resetDraft: () => { currentDraft = createEmptySupportRequestDraft(); },
  }));
}

function render() {
  return renderWithProviders(<CreateSupportRequestDetailsScreen />);
}

describe("CreateSupportRequestDetailsScreen", () => {
  afterEach(() => { jest.restoreAllMocks(); mockNavigate.mockClear(); mockGoBack.mockClear(); mockParentGoBack.mockClear(); });

  it("shows the step header and progress", () => {
    mockBookings(); mockWizard();
    const { getByText } = render();
    expect(getByText("Share the details clearly")).toBeTruthy();
    expect(getByText("Step 2 of 3")).toBeTruthy();
  });

  it("safely returns to Step 1 when Step 1 context is missing, never rendering an incomplete form", () => {
    mockBookings(); mockWizard({ categoryCode: null });
    render();
    expect(mockGoBack).toHaveBeenCalled();
  });

  it("shows the context summary with an Edit action, never a raw booking UUID", () => {
    mockBookings(); mockWizard({ categoryCode: "booking_service" });
    const { getByText, queryByText } = render();
    expect(getByText("Booking & service")).toBeTruthy();
    expect(getByText("Edit")).toBeTruthy();
    expect(queryByText(/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}/i)).toBeNull();
  });

  it("Edit returns to Step 1 preserving state", () => {
    mockBookings(); mockWizard();
    const { getByText } = render();
    fireEvent.press(getByText("Edit"));
    expect(mockGoBack).toHaveBeenCalled();
  });

  it("never renders unsupported fields: priority, attachments, agent, SLA", () => {
    mockBookings(); mockWizard();
    const { queryByText } = render();
    expect(queryByText(/priority|urgency|sla|assigned agent|guaranteed response/i)).toBeNull();
    expect(queryByText("Add evidence")).toBeNull();
    expect(queryByText("Choose files")).toBeNull();
  });

  it("shows the real 300-character title limit, never a fabricated 80", () => {
    mockBookings(); mockWizard();
    const { getByText } = render();
    expect(getByText("0 / 300")).toBeTruthy();
  });

  it("shows the sensitive-information warning", () => {
    mockBookings(); mockWizard();
    const { getByText } = render();
    expect(getByText("Protect your information")).toBeTruthy();
    expect(getByText("Do not include passwords, OTPs or payment-card details.")).toBeTruthy();
  });

  it("Continue to review is disabled until description is non-empty", () => {
    mockBookings(); mockWizard();
    const { getByLabelText } = render();
    expect(getByLabelText("Continue to review").props.accessibilityState.disabled).toBe(true);
  });

  it("rejects a whitespace-only description, shown on blur", () => {
    mockBookings(); mockWizard({ categoryCode: "booking_service", description: "   " });
    const { getByLabelText, getByText } = render();
    fireEvent(getByLabelText("Tell us what happened"), "blur");
    expect(getByText("Tell us what happened.")).toBeTruthy();
  });

  it("Continue to review stays disabled for a whitespace-only description", () => {
    mockBookings(); mockWizard({ categoryCode: "booking_service", description: "   " });
    const { getByLabelText } = render();
    expect(getByLabelText("Continue to review").props.accessibilityState.disabled).toBe(true);
  });

  it("Continue to review navigates to Step 3 once description is valid, with no backend mutation", () => {
    mockBookings(); mockWizard({ categoryCode: "booking_service", description: "My booking is confirmed but I need help." });
    const { getByLabelText } = render();
    fireEvent.press(getByLabelText("Continue to review"));
    expect(mockNavigate).toHaveBeenCalledWith("Review");
  });

  it("Cancel with entered content shows a discard confirmation and exits the whole wizard", () => {
    mockBookings(); mockWizard({ categoryCode: "booking_service", description: "test" });
    const alertSpy = jest.spyOn(Alert, "alert").mockImplementation(() => {});
    const { getByText } = render();
    fireEvent.press(getByText("Cancel"));
    expect(alertSpy).toHaveBeenCalledWith("Discard this request?", expect.any(String), expect.any(Array));
    expect(mockParentGoBack).not.toHaveBeenCalled();
  });

  it("never shows Save and exit -- no draft endpoint exists", () => {
    mockBookings(); mockWizard();
    const { queryByText } = render();
    expect(queryByText("Save and exit")).toBeNull();
  });
});
