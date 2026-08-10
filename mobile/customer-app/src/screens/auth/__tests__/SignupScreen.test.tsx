import React from "react";
import { fireEvent, waitFor } from "@testing-library/react-native";
import { renderAuthScreen } from "../../../testing/authTestNavHarness";
import { SignupScreen } from "../SignupScreen";
import * as authApi from "../../../api/auth/authApi";
import * as sessionManager from "../../../api/session/sessionManager";
import { DomainError } from "../../../domain/errors";

type Screen = ReturnType<typeof renderAuthScreen>;

let register: jest.SpyInstance;
let requestOtp: jest.SpyInstance;

function render(): Screen {
  return renderAuthScreen("Signup", SignupScreen, undefined, {
    VerifyLoginOtp: "verify-otp-screen",
    LoginMethod: "login-method-screen",
  });
}

function fillValid(screen: Screen) {
  fireEvent.changeText(screen.getByLabelText("Full name"), "Rajinder Singh");
  fireEvent.changeText(screen.getByLabelText("Mobile number"), "9876543210");
}

describe("SignupScreen", () => {
  beforeEach(() => {
    register = jest.spyOn(authApi, "registerCustomer").mockResolvedValue(
      { data: { user_id: "u-1", message: "OTP sent." } } as never,
    );
    requestOtp = jest.spyOn(sessionManager, "requestLoginOtp").mockResolvedValue(
      { message: "OTP sent." } as never,
    );
  });

  afterEach(() => jest.restoreAllMocks());

  it("registers with only the fields the backend actually stores", async () => {
    // Name, phone, optional email. No address and no password: the account is usable
    // immediately, and the first address is collected during a booking where it is
    // genuinely needed.
    const screen = render();
    fillValid(screen);
    fireEvent.press(screen.getByText("Create account"));

    await waitFor(() => expect(register).toHaveBeenCalledWith({
      fullName: "Rajinder Singh", phone: "+919876543210", email: undefined,
    }));
  });

  it("sends the email only when one was entered", async () => {
    const screen = render();
    fillValid(screen);
    fireEvent.changeText(screen.getByLabelText("Email, optional"), " raj@example.com ");
    fireEvent.press(screen.getByText("Create account"));

    await waitFor(() => expect(register).toHaveBeenCalledWith(
      expect.objectContaining({ email: "raj@example.com" }),
    ));
  });

  it("verifies through the same OTP screen a returning customer uses", async () => {
    // The registration response carries its own OTP, but it is scoped to
    // `phone_verification` and /otp/verify rejects it (confirmed live). A normal login
    // OTP is sent instead, so there is ONE verification implementation.
    const screen = render();
    fillValid(screen);
    fireEvent.press(screen.getByText("Create account"));

    await waitFor(() => expect(requestOtp).toHaveBeenCalledWith("+919876543210"));
    await waitFor(() => expect(screen.getByText("verify-otp-screen")).toBeTruthy());
  });

  it("rejects a too-short name and an invalid number without calling the backend", async () => {
    const screen = render();
    fireEvent.changeText(screen.getByLabelText("Full name"), "R");
    fireEvent.changeText(screen.getByLabelText("Mobile number"), "98765");
    fireEvent.press(screen.getByText("Create account"));

    await waitFor(() => expect(screen.getByText(/Enter your name/)).toBeTruthy());
    expect(screen.getByText(/valid 10-digit mobile number/)).toBeTruthy();
    expect(register).not.toHaveBeenCalled();
  });

  it("shows the backend's reason when the number already has an account", async () => {
    // Telling someone their OWN number is already registered is legitimate -- unlike
    // on login, where the same disclosure would let anyone enumerate accounts.
    // Exactly what the live API returns: 409 with error_code ALREADY_EXISTS, which the
    // error mapper carries through as telemetryMeta.backendCode.
    register.mockRejectedValue(new DomainError({
      category: "VALIDATION_FAILURE",
      diagnostic: "An account with this phone number already exists.",
      httpStatus: 409,
      telemetryMeta: { backendCode: "ALREADY_EXISTS" },
    }));
    const screen = render();
    fillValid(screen);
    fireEvent.press(screen.getByText("Create account"));

    await waitFor(() => expect(screen.getByText(/already has an account/i)).toBeTruthy());
    expect(screen.queryByText("verify-otp-screen")).toBeNull();
  });

  it("does not navigate when the OTP could not be sent", async () => {
    // The account exists, but sending someone to a code screen with no code on the way
    // is a dead end.
    requestOtp.mockRejectedValue(new Error("network"));
    const screen = render();
    fillValid(screen);
    fireEvent.press(screen.getByText("Create account"));

    await waitFor(() => expect(requestOtp).toHaveBeenCalled());
    // Still on signup: sending someone to a code screen with no code on the way is a
    // dead end.
    expect(screen.getByText("Create account")).toBeTruthy();
    expect(screen.queryByText("verify-otp-screen")).toBeNull();
  });

  it("offers the way back to signing in", async () => {
    const screen = render();
    fireEvent.press(screen.getByLabelText("I already have an account"));
    await waitFor(() => expect(screen.getByText("login-method-screen")).toBeTruthy());
  });
});

describe("signup verification is a real step", () => {
  afterEach(() => jest.restoreAllMocks());

  it("stops at the code screen instead of signing the customer straight in", async () => {
    // Real bug: the verify screen pre-filled the dev code AND auto-submitted it, so
    // creating an account on a dev build went straight into the app with no code screen
    // at all. The one step that proves the customer owns the number was invisible, and
    // untestable.
    jest.spyOn(authApi, "registerCustomer").mockResolvedValue(
      { data: { user_id: "u-1", message: "OTP sent." } } as never,
    );
    jest.spyOn(sessionManager, "requestLoginOtp").mockResolvedValue(
      { message: "OTP sent.", otp_hint: "123456" } as never,
    );
    const verify = jest.spyOn(sessionManager, "verifyLoginOtp");

    const screen = render();
    fillValid(screen);
    fireEvent.press(screen.getByText("Create account"));

    await waitFor(() => expect(screen.getByText("verify-otp-screen")).toBeTruthy());
    // Nothing was redeemed on the customer's behalf.
    expect(verify).not.toHaveBeenCalled();
  });
});
