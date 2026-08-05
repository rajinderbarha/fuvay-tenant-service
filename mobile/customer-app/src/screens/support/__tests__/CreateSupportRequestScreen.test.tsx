import React from "react";
import { fireEvent, waitFor } from "@testing-library/react-native";
import { renderWithProviders } from "../../../testing/renderWithProviders";
import { SafetyReportScreen } from "../SafetyReportScreen";
import * as supportRequestsApi from "../../../api/supportRequests/supportRequestsApi";
import * as networkStateModule from "../../../api/networkState";
import { DomainError } from "../../../domain/errors";

const mockReplace = jest.fn();
const mockGoBack = jest.fn();
let mockRouteParams: Record<string, unknown> = { bookingId: "b-1" };

jest.mock("@react-navigation/native", () => ({
  ...jest.requireActual("@react-navigation/native"),
  useNavigation: () => ({ navigate: jest.fn(), goBack: mockGoBack, replace: mockReplace }),
  useRoute: () => ({ name: "SafetyReport", params: mockRouteParams }),
}));

describe("SafetyReportScreen", () => {
  afterEach(() => { jest.restoreAllMocks(); mockReplace.mockClear(); mockRouteParams = { bookingId: "b-1" }; });

  it("presets the category to the real safety_concern value and hides category choice", () => {
    const { getByText, queryByText, getByLabelText } = renderWithProviders(<SafetyReportScreen />);
    expect(getByText("Report a safety concern")).toBeTruthy();
    expect(queryByText("What's this about?")).toBeNull();
    expect(getByLabelText("Submit report")).toBeTruthy();
  });

  it("never claims to be an emergency service", () => {
    const { queryByText } = renderWithProviders(<SafetyReportScreen />);
    expect(queryByText(/emergency|police|ambulance|instant response|24\/7/i)).toBeNull();
  });

  it("shows recoverable copy on a backend rejection", async () => {
    jest.spyOn(supportRequestsApi, "createMySupportRequest").mockRejectedValue(
      new DomainError({ category: "VALIDATION_FAILURE", diagnostic: "This booking is not eligible for a new request." }),
    );
    const { getByLabelText, getByText } = renderWithProviders(<SafetyReportScreen />);
    fireEvent.changeText(getByLabelText("Description"), "unsafe");
    fireEvent.press(getByLabelText("Submit report"));

    await waitFor(() => expect(getByText("This booking is not eligible for a new request.")).toBeTruthy());
  });

  it("disables submission while offline", () => {
    jest.spyOn(networkStateModule, "isOffline").mockReturnValue(true);
    const { getByLabelText } = renderWithProviders(<SafetyReportScreen />);
    fireEvent.changeText(getByLabelText("Description"), "unsafe");
    expect(getByLabelText("Submit report").props.accessibilityState.disabled).toBe(true);
  });

  it("submits with complaint_type locked to safety_concern", async () => {
    const createSpy = jest.spyOn(supportRequestsApi, "createMySupportRequest").mockResolvedValue({
      data: { id: "c-10", complaint_number: "CMP-10", record_type: "service_booking", record_id: "b-1", booking_id: "b-1", complaint_type: "safety_concern", status: "open", title: null, description: "unsafe", requested_resolution: null, customer_visible_summary: null, created_at: null, updated_at: null, resolved_at: null, closed_at: null },
      requestId: "req-1",
    } as unknown as Awaited<ReturnType<typeof supportRequestsApi.createMySupportRequest>>);

    const { getByLabelText } = renderWithProviders(<SafetyReportScreen />);
    fireEvent.changeText(getByLabelText("Description"), "unsafe");
    fireEvent.press(getByLabelText("Submit report"));

    await waitFor(() => expect(createSpy).toHaveBeenCalledWith({
      record_type: "service_booking", record_id: "b-1", complaint_type: "safety_concern", description: "unsafe",
    }));
  });
});
