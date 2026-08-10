import React from "react";
import { fireEvent, waitFor } from "@testing-library/react-native";
import { renderAuthScreen } from "../../../testing/authTestNavHarness";
import { VerifyLoginOtpScreen } from "../VerifyLoginOtpScreen";
import * as sessionManager from "../../../api/session/sessionManager";
import { DomainError } from "../../../domain/errors";

describe("VerifyLoginOtpScreen", () => {
  afterEach(() => jest.restoreAllMocks());

  it("masks the phone number in the heading, never showing it in full", () => {
    const { getByText, queryByText } = renderAuthScreen("VerifyLoginOtp", VerifyLoginOtpScreen, { phone: "+919876543210" });
    expect(getByText(/\+91 •••••43210/)).toBeTruthy();
    expect(queryByText(/9876543210/)).toBeNull();
  });

  it("submits the code once 6 digits are entered and shows an inline error on invalid code", async () => {
    jest.spyOn(sessionManager, "verifyLoginOtp").mockRejectedValue(
      new DomainError({ category: "AUTH_REQUIRED", diagnostic: "Incorrect OTP." }),
    );
    const { getByLabelText, findByText } = renderAuthScreen("VerifyLoginOtp", VerifyLoginOtpScreen, { phone: "+919876543210" });
    fireEvent.changeText(getByLabelText("Verification code"), "123456");
    await findByText(/couldn't sign you in/i);
  });

  it("navigates toward MFA when the outcome is a challenge, not an authenticated session", async () => {
    jest.spyOn(sessionManager, "verifyLoginOtp").mockResolvedValue({ status: "challenge_required", challengeToken: "chal-1" });
    const { getByLabelText } = renderAuthScreen("VerifyLoginOtp", VerifyLoginOtpScreen, { phone: "+919876543210" });
    fireEvent.changeText(getByLabelText("Verification code"), "123456");
    await waitFor(() => expect(sessionManager.verifyLoginOtp).toHaveBeenCalledWith("+919876543210", "123456"));
  });

  it("shows a rate-limited banner (not a per-field error) when the backend rate-limits verification", async () => {
    jest.spyOn(sessionManager, "verifyLoginOtp").mockRejectedValue(
      new DomainError({ category: "RATE_LIMITED", diagnostic: "slow down", telemetryMeta: { backendCode: "RATE_LIMITED" } }),
    );
    const { getByLabelText, findByText } = renderAuthScreen("VerifyLoginOtp", VerifyLoginOtpScreen, { phone: "+919876543210" });
    fireEvent.changeText(getByLabelText("Verification code"), "123456");
    await findByText(/too many attempts/i);
  });

  it("resend is available immediately (no fabricated countdown) since the backend returns no cooldown metadata", () => {
    const { queryByText, getByText } = renderAuthScreen("VerifyLoginOtp", VerifyLoginOtpScreen, { phone: "+919876543210" });
    expect(queryByText(/Resend code in/)).toBeNull();
    expect(getByText("Resend code")).toBeTruthy();
  });

  it("starts a real countdown only after the backend actually rate-limits the resend", async () => {
    jest.spyOn(sessionManager, "requestLoginOtp").mockRejectedValue(
      new DomainError({ category: "RATE_LIMITED", diagnostic: "slow down", telemetryMeta: { backendCode: "RATE_LIMITED", retryAfterSeconds: 30 } }),
    );
    const { getByText, findByText } = renderAuthScreen("VerifyLoginOtp", VerifyLoginOtpScreen, { phone: "+919876543210" });
    fireEvent.press(getByText("Resend code"));
    await findByText(/Resend code in/);
  });
});

describe("VerifyLoginOtpScreen: the emailed code", () => {
  afterEach(() => jest.restoreAllMocks());

  function renderEmail() {
    return renderAuthScreen(
      "VerifyLoginOtp", VerifyLoginOtpScreen, { email: "raj@example.com" },
      { MfaChallenge: "mfa-screen" },
    );
  }

  it("says where the code went, and does not call it a number", () => {
    // One screen for both channels: redeeming a 6-digit code is the same job, and two
    // copies would be two places for the attempt-limit and MFA branches to drift.
    const screen = renderEmail();
    expect(screen.getByText("Check your email")).toBeTruthy();
    expect(screen.getByText(/raj@example.com/)).toBeTruthy();
    expect(screen.queryByText("Verify your number")).toBeNull();
    // And the way back is not "Change number" either.
    expect(screen.getByText("Change email")).toBeTruthy();
  });

  it("redeems it through the email endpoint, not the phone one", async () => {
    const email = jest.spyOn(sessionManager, "verifyEmailLoginOtp")
      .mockResolvedValue({ status: "authenticated" } as never);
    const phone = jest.spyOn(sessionManager, "verifyLoginOtp");

    const screen = renderEmail();
    fireEvent.changeText(screen.getByLabelText("Verification code"), "123456");

    await waitFor(() => expect(email).toHaveBeenCalledWith("raj@example.com", "123456"));
    expect(phone).not.toHaveBeenCalled();
  });

  it("resends by email as well", async () => {
    jest.spyOn(sessionManager, "verifyEmailLoginOtp").mockResolvedValue({} as never);
    const resend = jest.spyOn(sessionManager, "requestEmailLoginOtp")
      .mockResolvedValue({ message: "sent" } as never);
    const screen = renderEmail();

    fireEvent.press(screen.getByText("Resend code"));
    await waitFor(() => expect(resend).toHaveBeenCalledWith("raj@example.com"));
  });
});
