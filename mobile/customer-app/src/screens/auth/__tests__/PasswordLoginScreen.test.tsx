import React from "react";
import { fireEvent, waitFor } from "@testing-library/react-native";
import { renderAuthScreen } from "../../../testing/authTestNavHarness";
import { PasswordLoginScreen } from "../PasswordLoginScreen";
import * as sessionManager from "../../../api/session/sessionManager";
import { DomainError } from "../../../domain/errors";

describe("PasswordLoginScreen", () => {
  afterEach(() => jest.restoreAllMocks());

  it("accepts a single combined email-or-mobile identifier field (no separate phone field)", () => {
    const { getByLabelText, queryByLabelText } = renderAuthScreen("PasswordLogin", PasswordLoginScreen);
    expect(getByLabelText("Email or mobile")).toBeTruthy();
    expect(queryByLabelText("Mobile number")).toBeNull();
  });

  it("shows an enumeration-safe error, never a field-specific 'not found' message", async () => {
    jest.spyOn(sessionManager, "loginWithPassword").mockRejectedValue(
      new DomainError({ category: "AUTH_REQUIRED", diagnostic: "Invalid email or password." }),
    );
    const { getByLabelText, getByText, findByText } = renderAuthScreen("PasswordLogin", PasswordLoginScreen);
    fireEvent.changeText(getByLabelText("Email or mobile"), "customer@example.com");
    fireEvent.changeText(getByLabelText("Password"), "wrongpassword");
    fireEvent.press(getByText("Sign in"));
    const error = await findByText(/couldn't sign you in/i);
    expect(error).toBeTruthy();
  });

  it("clears the password field after a failed sign-in attempt", async () => {
    jest.spyOn(sessionManager, "loginWithPassword").mockRejectedValue(
      new DomainError({ category: "AUTH_REQUIRED", diagnostic: "Invalid email or password." }),
    );
    const { getByLabelText, getByText, findByText } = renderAuthScreen("PasswordLogin", PasswordLoginScreen);
    const passwordField = getByLabelText("Password");
    fireEvent.changeText(getByLabelText("Email or mobile"), "customer@example.com");
    fireEvent.changeText(passwordField, "wrongpassword");
    fireEvent.press(getByText("Sign in"));
    await findByText(/couldn't sign you in/i);
    expect(passwordField.props.value).toBe("");
  });

  it("toggles password visibility via the accessible show/hide action", () => {
    const { getByLabelText } = renderAuthScreen("PasswordLogin", PasswordLoginScreen);
    const passwordField = getByLabelText("Password");
    expect(passwordField.props.secureTextEntry).toBe(true);
    fireEvent.press(getByLabelText("Show password"));
    expect(passwordField.props.secureTextEntry).toBe(false);
  });

  it("navigates toward MFA when password login returns a challenge", async () => {
    jest.spyOn(sessionManager, "loginWithPassword").mockResolvedValue({ status: "challenge_required", challengeToken: "chal-1" });
    const { getByLabelText, getByText } = renderAuthScreen("PasswordLogin", PasswordLoginScreen);
    fireEvent.changeText(getByLabelText("Email or mobile"), "customer@example.com");
    fireEvent.changeText(getByLabelText("Password"), "correcthorse");
    fireEvent.press(getByText("Sign in"));
    await waitFor(() => expect(sessionManager.loginWithPassword).toHaveBeenCalled());
  });
});
