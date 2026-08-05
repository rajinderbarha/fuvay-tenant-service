import React from "react";
import { Alert } from "react-native";
import { fireEvent, waitFor } from "@testing-library/react-native";
import { NavigationContainer, useNavigation } from "@react-navigation/native";
import { renderWithProviders } from "../../../testing/renderWithProviders";
import { EditProfileScreen } from "../EditProfileScreen";
import * as profileQueryModule from "../../../api/customer/useCustomerProfileQuery";
import * as customerProfileApi from "../../../api/customer/customerProfileApi";
import { parseCustomerProfileDto } from "../../../api/adapters/customer";
import { makeCustomerProfileDto } from "../../../testing/fixtures";
import { asCustomerId } from "../../../domain/ids";

function baseProfile(overrides: Partial<Record<string, unknown>> = {}) {
  return {
    id: asCustomerId("c-1"), fullName: "Rajinder Singh", displayName: "Rajinder",
    phone: "+919900024102", email: "rajinder@example.com", avatarUrl: null,
    language: "en", timezone: "Asia/Kolkata", verified: true, isActive: true,
    createdAt: "2026-01-01T00:00:00Z",
    capabilities: { canEditProfile: true, canUpdateAvatar: false, canManageAddresses: false, canChangePassword: true, canManageSessions: true, canDeleteAccount: false },
    ...overrides,
  };
}

function renderScreen() {
  return renderWithProviders(
    <NavigationContainer>
      <EditProfileScreen />
    </NavigationContainer>,
  );
}

describe("EditProfileScreen", () => {
  beforeEach(() => {
    jest.spyOn(profileQueryModule, "useCustomerProfileQuery").mockReturnValue({
      data: baseProfile(), isPending: false, isError: false, refetch: jest.fn(),
    } as unknown as ReturnType<typeof profileQueryModule.useCustomerProfileQuery>);
  });
  afterEach(() => jest.restoreAllMocks());

  it("initializes the form from the shared profile query", () => {
    const { getByDisplayValue } = renderScreen();
    expect(getByDisplayValue("Rajinder Singh")).toBeTruthy();
  });

  it("shows the Verified badge only when the backend's real is_verified flag is true, not because of the component's name", () => {
    jest.spyOn(profileQueryModule, "useCustomerProfileQuery").mockReturnValue({
      data: baseProfile({ verified: false }), isPending: false, isError: false, refetch: jest.fn(),
    } as unknown as ReturnType<typeof profileQueryModule.useCustomerProfileQuery>);
    const { queryByText } = renderScreen();
    expect(queryByText("Verified")).toBeNull();
  });

  it("renders mobile/email as read-only verified rows, never as editable inputs", () => {
    const { getByText, queryByDisplayValue } = renderScreen();
    expect(getByText(/24102/)).toBeTruthy();
    expect(getByText("rajinder@example.com")).toBeTruthy();
    expect(queryByDisplayValue("+919900024102")).toBeNull();
    expect(queryByDisplayValue("rajinder@example.com")).toBeNull();
  });

  it("masks the phone number for display, never showing it in full", () => {
    const { queryByText } = renderScreen();
    expect(queryByText("+919900024102")).toBeNull();
  });

  it("hides avatar-change controls -- no confirmed upload capability", () => {
    const { queryByText } = renderScreen();
    expect(queryByText("Change photo")).toBeNull();
  });

  it("hides Change actions on contact rows -- no confirmed OTP contact-change flow", () => {
    const { queryAllByText } = renderScreen();
    expect(queryAllByText("Change")).toHaveLength(0);
  });

  it("Save is disabled until the name actually changes", () => {
    const { getByText } = renderScreen();
    const saveButton = getByText("Save changes");
    expect(saveButton.props.accessibilityState?.disabled ?? true).toBe(true);
  });

  it("shows a validation error for a name shorter than 2 characters and keeps Save disabled", () => {
    const { getByLabelText, getByText } = renderScreen();
    fireEvent.changeText(getByLabelText("Full name"), "R");
    expect(getByText(/at least 2/)).toBeTruthy();
  });

  it("normalizes whitespace and saves via the canonical mutation, updating the shared cache", async () => {
    const updateSpy = jest.spyOn(customerProfileApi, "updateCustomerProfile").mockResolvedValue({
      data: parseCustomerProfileDto(makeCustomerProfileDto({ full_name: "Rajinder Kaur" })),
      requestId: "req-1",
    } as unknown as Awaited<ReturnType<typeof customerProfileApi.updateCustomerProfile>>);

    const { getByLabelText, getByText } = renderScreen();
    fireEvent.changeText(getByLabelText("Full name"), "  Rajinder   Kaur  ");
    fireEvent.press(getByText("Save changes"));

    await waitFor(() => expect(updateSpy).toHaveBeenCalledWith({ full_name: "Rajinder Kaur" }));
  });

  it("never submits verification flags, role, or account status in the update payload", async () => {
    const updateSpy = jest.spyOn(customerProfileApi, "updateCustomerProfile").mockResolvedValue({
      data: parseCustomerProfileDto(makeCustomerProfileDto()),
      requestId: "req-1",
    } as unknown as Awaited<ReturnType<typeof customerProfileApi.updateCustomerProfile>>);

    const { getByLabelText, getByText } = renderScreen();
    fireEvent.changeText(getByLabelText("Full name"), "New Name");
    fireEvent.press(getByText("Save changes"));

    await waitFor(() => expect(updateSpy).toHaveBeenCalled());
    const payload = updateSpy.mock.calls[0][0];
    expect(payload).not.toHaveProperty("is_verified");
    expect(payload).not.toHaveProperty("role");
    expect(payload).not.toHaveProperty("account_status");
    expect(payload).not.toHaveProperty("id");
  });

  it("preserves the entered name after a recoverable save failure", async () => {
    jest.spyOn(customerProfileApi, "updateCustomerProfile").mockRejectedValue(new Error("network"));
    const { getByLabelText, getByText } = renderScreen();
    fireEvent.changeText(getByLabelText("Full name"), "Preserved Name");
    fireEvent.press(getByText("Save changes"));
    await waitFor(() => expect(getByText(/Couldn't save/)).toBeTruthy());
    expect(getByLabelText("Full name").props.value).toBe("Preserved Name");
  });

  it("does not warn when Cancel is pressed with no changes made", () => {
    const alertSpy = jest.spyOn(Alert, "alert");
    const { getByText } = renderScreen();
    fireEvent.press(getByText("Cancel"));
    expect(alertSpy).not.toHaveBeenCalled();
  });

  it("warns before discarding when the form is dirty, and Discard resets the field", () => {
    const alertSpy = jest.spyOn(Alert, "alert").mockImplementation((_title, _msg, buttons) => {
      const discard = buttons?.find(b => b.text === "Discard");
      discard?.onPress?.();
    });
    const { getByLabelText, getByText } = renderScreen();
    fireEvent.changeText(getByLabelText("Full name"), "Changed Name");
    fireEvent.press(getByText("Cancel"));
    expect(alertSpy).toHaveBeenCalledWith(
      "Discard changes?", "Your unsaved profile changes will be lost.", expect.any(Array),
    );
  });

  it("never renders unsupported fields", () => {
    const { queryByText } = renderScreen();
    for (const forbidden of ["Gender", "Birthday", "Username", "Wallet", "Password", "Marketing"]) {
      expect(queryByText(new RegExp(forbidden, "i"))).toBeNull();
    }
  });
});
