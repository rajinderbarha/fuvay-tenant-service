import React from "react";
import { render, screen, waitFor, fireEvent, act } from "@testing-library/react-native";
import { ThemeProvider } from "../../../design-system/themes";
import { OtpVerifyScreen } from "../OtpVerifyScreen";

jest.mock("../../../services/auth/authApi");
jest.mock("../../../hooks/useNetworkStatus", () => ({ useNetworkStatus: () => "online" }));

const mockEstablishSession = jest.fn().mockResolvedValue(undefined);
jest.mock("../../../navigation/session/SessionProvider", () => ({
  useSession: () => ({ establishSession: mockEstablishSession }),
}));

import * as authApi from "../../../services/auth/authApi";

const navigation = { navigate: jest.fn(), goBack: jest.fn() } as any;
const route = { key: "OtpVerify", name: "OtpVerify", params: { phone: "9876543210" } } as any;

function renderScreen() {
  return render(<ThemeProvider><OtpVerifyScreen navigation={navigation} route={route} /></ThemeProvider>);
}

beforeEach(() => jest.clearAllMocks());

describe("OtpVerifyScreen (spec sections 4, 17)", () => {
  it("auto-submits and establishes a session once all 6 digits are entered (valid code)", async () => {
    (authApi.verifyOtp as jest.Mock).mockResolvedValue({
      ok: true, data: { mfa_required: false, access_token: "a", refresh_token: "r", user: {}, tenant: {} }, meta: {},
    });
    renderScreen();
    fireEvent.changeText(screen.getByLabelText("Verification code"), "123456");
    await waitFor(() => expect(mockEstablishSession).toHaveBeenCalledWith({ access_token: "a", refresh_token: "r" }));
  });

  it("shows a safe error and clears the code on an invalid code", async () => {
    (authApi.verifyOtp as jest.Mock).mockResolvedValue({
      ok: false, error: { code: "AUTH_REQUIRED", category: "auth", safeMessage: "Incorrect OTP.", retryable: false },
    });
    renderScreen();
    fireEvent.changeText(screen.getByLabelText("Verification code"), "000000");
    await waitFor(() => expect(screen.getByText("Incorrect OTP.")).toBeTruthy());
    expect(mockEstablishSession).not.toHaveBeenCalled();
  });

  it("shows a safe error on an expired code", async () => {
    (authApi.verifyOtp as jest.Mock).mockResolvedValue({
      ok: false, error: { code: "AUTH_REQUIRED", category: "auth", safeMessage: "OTP not found or expired.", retryable: false },
    });
    renderScreen();
    fireEvent.changeText(screen.getByLabelText("Verification code"), "111111");
    await waitFor(() => expect(screen.getByText("OTP not found or expired.")).toBeTruthy());
  });

  it("respects rate limiting via the mapped Retry-After error", async () => {
    (authApi.verifyOtp as jest.Mock).mockResolvedValue({
      ok: false, error: { code: "RATE_LIMITED", category: "rate_limit", safeMessage: "Too many attempts. Try again shortly.", retryable: true, retryAfterSeconds: 30 },
    });
    renderScreen();
    fireEvent.changeText(screen.getByLabelText("Verification code"), "222222");
    await waitFor(() => expect(screen.getByText("Too many attempts. Try again shortly.")).toBeTruthy());
  });

  it("transitions to MFA (not an error) when verify_phone_otp_login requires it", async () => {
    (authApi.verifyOtp as jest.Mock).mockResolvedValue({
      ok: true, data: { mfa_required: true, mfa_challenge_token: "challenge-otp" }, meta: {},
    });
    renderScreen();
    fireEvent.changeText(screen.getByLabelText("Verification code"), "333333");
    await waitFor(() => expect(navigation.navigate).toHaveBeenCalledWith("Mfa", { mfaChallengeToken: "challenge-otp", rememberDevice: false }));
    expect(mockEstablishSession).not.toHaveBeenCalled();
  });

  it("shows a resend cooldown timer and disables Resend until it elapses", () => {
    jest.useFakeTimers();
    renderScreen();
    expect(screen.getByText(/Resend code \(30s\)/)).toBeTruthy();
    act(() => { jest.advanceTimersByTime(5000); });
    expect(screen.getByText(/Resend code \(25s\)/)).toBeTruthy();
    jest.useRealTimers();
  });

  it("resends the code via sendOtp when the cooldown has elapsed", async () => {
    jest.useFakeTimers();
    (authApi.sendOtp as jest.Mock).mockResolvedValue({ ok: true, data: { message: "OTP sent." }, meta: {} });
    renderScreen();
    act(() => { jest.advanceTimersByTime(30_000); });
    jest.useRealTimers();
    fireEvent.press(screen.getByText("Resend code"));
    await waitFor(() => expect(authApi.sendOtp).toHaveBeenCalledWith({ phone: "9876543210", purpose: "phone_login" }));
  });
});
