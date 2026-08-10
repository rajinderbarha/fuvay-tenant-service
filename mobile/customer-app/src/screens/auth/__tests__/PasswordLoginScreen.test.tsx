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

describe("PasswordLoginScreen: the other two ways in", () => {
  afterEach(() => jest.restoreAllMocks());

  function render() {
    return renderAuthScreen("PasswordLogin", PasswordLoginScreen, undefined, {
      VerifyLoginOtp: "verify-otp-screen",
      Signup: "signup-screen",
      LoginMethod: "login-method-screen",
    });
  }

  it("offers create-account, because this is where someone finds out they have none", async () => {
    const screen = render();
    fireEvent.press(screen.getByLabelText("New to Fuvay? Create an account"));
    await waitFor(() => expect(screen.getByText("signup-screen")).toBeTruthy());
  });

  it("offers an emailed code only once the identifier looks like an email", () => {
    // The code goes to an inbox, so offering it beside a phone number would be a
    // button that cannot work.
    const screen = render();
    expect(screen.queryByText("Email me a code instead")).toBeNull();
    fireEvent.changeText(screen.getByLabelText("Email or mobile"), "9876543210");
    expect(screen.queryByText("Email me a code instead")).toBeNull();
    fireEvent.changeText(screen.getByLabelText("Email or mobile"), "raj@example.com");
    expect(screen.getByText("Email me a code instead")).toBeTruthy();
  });

  it("emails a code and moves to the code screen", async () => {
    const send = jest.spyOn(sessionManager, "requestEmailLoginOtp")
      .mockResolvedValue({ message: "If an account exists, a sign-in code has been sent." } as never);
    const screen = render();
    fireEvent.changeText(screen.getByLabelText("Email or mobile"), " raj@example.com ");
    fireEvent.press(screen.getByText("Email me a code instead"));

    await waitFor(() => expect(send).toHaveBeenCalledWith("raj@example.com"));
    await waitFor(() => expect(screen.getByText("verify-otp-screen")).toBeTruthy());
  });

  it("cannot be used to find out whether an email is registered", async () => {
    // The endpoint answers identically either way, so the screen must move on either
    // way too -- branching here would rebuild the oracle the backend refuses to be.
    jest.spyOn(sessionManager, "requestEmailLoginOtp")
      .mockResolvedValue({ message: "If an account exists, a sign-in code has been sent." } as never);
    const screen = render();
    fireEvent.changeText(screen.getByLabelText("Email or mobile"), "nobody@example.com");
    fireEvent.press(screen.getByText("Email me a code instead"));

    await waitFor(() => expect(screen.getByText("verify-otp-screen")).toBeTruthy());
  });

  it("stays put and explains when the code could not be sent", async () => {
    jest.spyOn(sessionManager, "requestEmailLoginOtp").mockRejectedValue(
      new DomainError({ category: "BACKEND_UNAVAILABLE", diagnostic: "smtp down" }),
    );
    const screen = render();
    fireEvent.changeText(screen.getByLabelText("Email or mobile"), "raj@example.com");
    fireEvent.press(screen.getByText("Email me a code instead"));

    await waitFor(() => expect(screen.getByText(/can't reach Fuvay/i)).toBeTruthy());
    expect(screen.queryByText("verify-otp-screen")).toBeNull();
  });
});
