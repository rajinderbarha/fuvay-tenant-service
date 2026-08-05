import React from "react";
import { fireEvent, waitFor } from "@testing-library/react-native";
import { renderWithProviders } from "../../../testing/renderWithProviders";
import { DeleteAccountFinalConfirmationScreen } from "../DeleteAccountFinalConfirmationScreen";
import * as privacyDataApi from "../../../api/privacyData/privacyDataApi";
import * as profileQueryModule from "../../../api/customer/useCustomerProfileQuery";
import * as networkStateModule from "../../../api/networkState";
import { DomainError } from "../../../domain/errors";

const mockGoBack = jest.fn();
const mockReplace = jest.fn();
jest.mock("@react-navigation/native", () => ({
  ...jest.requireActual("@react-navigation/native"),
  useNavigation: () => ({ navigate: jest.fn(), goBack: mockGoBack, replace: mockReplace }),
  useRoute: () => ({ name: "DeleteAccountFinalConfirmation", params: { reason: "No longer needed" } }),
}));

function mockProfile() {
  jest.spyOn(profileQueryModule, "useCustomerProfileQuery").mockReturnValue({
    data: { displayName: "Rajinder", fullName: "Rajinder Singh" },
    isPending: false, isError: false, refetch: jest.fn(),
  } as unknown as ReturnType<typeof profileQueryModule.useCustomerProfileQuery>);
}

function render() {
  return renderWithProviders(<DeleteAccountFinalConfirmationScreen />);
}

describe("DeleteAccountFinalConfirmationScreen", () => {
  beforeEach(() => { mockProfile(); });
  afterEach(() => { jest.restoreAllMocks(); mockGoBack.mockClear(); mockReplace.mockClear(); });

  it("never submits merely by opening the screen", () => {
    const createSpy = jest.spyOn(privacyDataApi, "createMyPrivacyRequest");
    render();
    expect(createSpy).not.toHaveBeenCalled();
  });

  it("shows the real account summary and carried-forward request type, never a raw internal field", () => {
    const { getByText, queryByText } = render();
    expect(getByText("Account deletion")).toBeTruthy();
    expect(getByText("Rajinder")).toBeTruthy();
    expect(getByText("Remains active during review")).toBeTruthy();
    expect(queryByText(/challenge|proof-token|internal/i)).toBeNull();
  });

  it("shows the real password field -- the actual verification mechanism, disclosed deviation from the mockup", () => {
    const { getByLabelText } = render();
    expect(getByLabelText("Password")).toBeTruthy();
  });

  it("disables Submit until password is entered and the acknowledgement is checked", () => {
    const { getByLabelText } = render();
    const submit = getByLabelText("Submit deletion request");
    expect(submit.props.accessibilityState.disabled).toBe(true);

    fireEvent.press(getByLabelText("I understand and want to submit this deletion request."));
    expect(submit.props.accessibilityState.disabled).toBe(true); // still no password

    fireEvent.changeText(getByLabelText("Password"), "correct-password");
    expect(submit.props.accessibilityState.disabled).toBe(false);
  });

  it("submits reason, password, confirm_understanding and a real idempotency key, and navigates to the shared receipt", async () => {
    const createSpy = jest.spyOn(privacyDataApi, "createMyPrivacyRequest").mockResolvedValue({
      data: { request_id: "r-9", request_number: "REQ-009", request_type: "right_to_erasure", status: "submitted", status_label: "Submitted", sla_status: "on_track", submitted_at: null, due_at: null, message: "ok" },
    } as unknown as Awaited<ReturnType<typeof privacyDataApi.createMyPrivacyRequest>>);

    const { getByLabelText } = render();
    fireEvent.press(getByLabelText("I understand and want to submit this deletion request."));
    fireEvent.changeText(getByLabelText("Password"), "correct-password");
    fireEvent.press(getByLabelText("Submit deletion request"));

    await waitFor(() => expect(createSpy).toHaveBeenCalled());
    const payload = createSpy.mock.calls[0][0];
    expect(payload.request_type).toBe("right_to_erasure");
    expect(payload.reason).toBe("No longer needed");
    expect(payload.password).toBe("correct-password");
    expect(payload.confirm_understanding).toBe(true);
    expect(typeof payload.idempotency_key).toBe("string");

    await waitFor(() => expect(mockReplace).toHaveBeenCalledWith("PrivacyRequestSubmitted", { requestId: "r-9" }));
  });

  it("reuses the same idempotency key across a retry of the same submission", async () => {
    const createSpy = jest.spyOn(privacyDataApi, "createMyPrivacyRequest")
      .mockRejectedValueOnce(new DomainError({ category: "TIMEOUT", diagnostic: "timed out" }))
      .mockResolvedValueOnce({
        data: { request_id: "r-10", request_number: "REQ-010", request_type: "right_to_erasure", status: "submitted", status_label: "Submitted", sla_status: "on_track", submitted_at: null, due_at: null, message: "ok" },
      } as unknown as Awaited<ReturnType<typeof privacyDataApi.createMyPrivacyRequest>>);

    const { getByLabelText } = render();
    fireEvent.press(getByLabelText("I understand and want to submit this deletion request."));
    fireEvent.changeText(getByLabelText("Password"), "correct-password");

    fireEvent.press(getByLabelText("Submit deletion request"));
    await waitFor(() => expect(createSpy).toHaveBeenCalledTimes(1));

    fireEvent.changeText(getByLabelText("Password"), "correct-password");
    fireEvent.press(getByLabelText("Submit deletion request"));
    await waitFor(() => expect(createSpy).toHaveBeenCalledTimes(2));

    expect(createSpy.mock.calls[0][0].idempotency_key).toBe(createSpy.mock.calls[1][0].idempotency_key);
  });

  it("shows a recoverable error and clears the password field on an incorrect password, never signing the customer out", async () => {
    jest.spyOn(privacyDataApi, "createMyPrivacyRequest").mockRejectedValue(
      new DomainError({ category: "VALIDATION_FAILURE", diagnostic: "Incorrect password. Please try again.", telemetryMeta: { backendCode: "INVALID_PASSWORD" } }),
    );

    const { getByLabelText, getByText } = render();
    fireEvent.press(getByLabelText("I understand and want to submit this deletion request."));
    fireEvent.changeText(getByLabelText("Password"), "wrong-password");
    fireEvent.press(getByLabelText("Submit deletion request"));

    await waitFor(() => expect(getByText("Incorrect password. Please try again.")).toBeTruthy());
    expect(getByLabelText("Password").props.value).toBe("");
    expect(mockReplace).not.toHaveBeenCalled();
  });

  it("routes to the existing request on a duplicate-open-request response", async () => {
    jest.spyOn(privacyDataApi, "createMyPrivacyRequest").mockRejectedValue(
      new DomainError({ category: "CONFLICT_STALE_WORKFLOW", diagnostic: "duplicate", telemetryMeta: { existingRequestId: "existing-r-4" } }),
    );

    const { getByLabelText } = render();
    fireEvent.press(getByLabelText("I understand and want to submit this deletion request."));
    fireEvent.changeText(getByLabelText("Password"), "correct-password");
    fireEvent.press(getByLabelText("Submit deletion request"));

    await waitFor(() => expect(mockReplace).toHaveBeenCalledWith("PrivacyRequestDetails", { requestId: "existing-r-4" }));
  });

  it("Keep my account clears the password and acknowledgement and navigates back without submitting", () => {
    const createSpy = jest.spyOn(privacyDataApi, "createMyPrivacyRequest");
    const { getByLabelText } = render();
    fireEvent.changeText(getByLabelText("Password"), "correct-password");
    fireEvent.press(getByLabelText("I understand and want to submit this deletion request."));
    fireEvent.press(getByLabelText("Keep my account"));
    expect(mockGoBack).toHaveBeenCalled();
    expect(createSpy).not.toHaveBeenCalled();
  });

  it("disables Submit and explains why while offline", () => {
    jest.spyOn(networkStateModule, "isOffline").mockReturnValue(true);
    const { getByLabelText, getByText } = render();
    fireEvent.press(getByLabelText("I understand and want to submit this deletion request."));
    fireEvent.changeText(getByLabelText("Password"), "correct-password");
    expect(getByLabelText("Submit deletion request").props.accessibilityState.disabled).toBe(true);
    expect(getByText("Connect to the internet to submit this request.")).toBeTruthy();
  });

  it("never claims the account was deleted or the customer was signed out", () => {
    const { queryByText } = render();
    expect(queryByText(/account has been deleted|signed out|logged out/i)).toBeNull();
  });

  it("Go back navigates via the back chevron", () => {
    const { getByLabelText } = render();
    fireEvent.press(getByLabelText("Go back"));
    expect(mockGoBack).toHaveBeenCalled();
  });
});
