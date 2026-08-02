import React from "react";
import { render, screen, waitFor, fireEvent } from "@testing-library/react-native";
import { ThemeProvider } from "../../../design-system/themes";
import { LoginScreen } from "../LoginScreen";

jest.mock("../../../services/auth/authApi");
jest.mock("../../../hooks/useNetworkStatus", () => ({ useNetworkStatus: () => "online" }));
jest.mock("../../../services/api/healthApi", () => ({ checkPublicHealth: jest.fn().mockResolvedValue("online") }));

const mockEstablishSession = jest.fn().mockResolvedValue(undefined);
jest.mock("../../../navigation/session/SessionProvider", () => ({
  useSession: () => ({ establishSession: mockEstablishSession }),
}));

import * as authApi from "../../../services/auth/authApi";

const navigation = { navigate: jest.fn(), goBack: jest.fn(), reset: jest.fn() } as any;

function renderScreen() {
  return render(
    <ThemeProvider>
      <LoginScreen navigation={navigation} route={{ key: "Login", name: "Login", params: undefined }} />
    </ThemeProvider>,
  );
}

beforeEach(() => jest.clearAllMocks());

describe("LoginScreen — password login (spec section 3, 17)", () => {
  it("succeeds with an email identifier and establishes the session without navigating directly to Home", async () => {
    (authApi.login as jest.Mock).mockResolvedValue({
      ok: true, data: { mfa_required: false, access_token: "a1", refresh_token: "r1", user: {}, tenant: {} }, meta: {},
    });
    renderScreen();
    fireEvent.changeText(screen.getByPlaceholderText("Enter email or mobile"), "tech@biz.io");
    fireEvent.changeText(screen.getByPlaceholderText("Enter password"), "Password123!");
    fireEvent.press(screen.getByText("Sign in"));

    await waitFor(() => expect(mockEstablishSession).toHaveBeenCalledWith({ access_token: "a1", refresh_token: "r1" }));
    expect(navigation.navigate).not.toHaveBeenCalled();
  });

  it("succeeds with a mobile-number identifier the same way", async () => {
    (authApi.login as jest.Mock).mockResolvedValue({
      ok: true, data: { mfa_required: false, access_token: "a2", refresh_token: "r2", user: {}, tenant: {} }, meta: {},
    });
    renderScreen();
    fireEvent.changeText(screen.getByPlaceholderText("Enter email or mobile"), "9876543210");
    fireEvent.changeText(screen.getByPlaceholderText("Enter password"), "Password123!");
    fireEvent.press(screen.getByText("Sign in"));

    await waitFor(() => expect(mockEstablishSession).toHaveBeenCalledWith({ access_token: "a2", refresh_token: "r2" }));
  });

  it("shows a safe error message on wrong credentials without establishing a session", async () => {
    (authApi.login as jest.Mock).mockResolvedValue({
      ok: false, error: { code: "AUTH_REQUIRED", category: "auth", safeMessage: "Invalid email or password.", retryable: false },
    });
    renderScreen();
    fireEvent.changeText(screen.getByPlaceholderText("Enter email or mobile"), "tech@biz.io");
    fireEvent.changeText(screen.getByPlaceholderText("Enter password"), "wrong");
    fireEvent.press(screen.getByText("Sign in"));

    await waitFor(() => expect(screen.getByText("Invalid email or password.")).toBeTruthy());
    expect(mockEstablishSession).not.toHaveBeenCalled();
  });

  it("prevents a duplicate submission while one login call is already in flight", async () => {
    let resolveLogin: (v: any) => void;
    (authApi.login as jest.Mock).mockReturnValue(new Promise(res => { resolveLogin = res; }));
    renderScreen();
    fireEvent.changeText(screen.getByPlaceholderText("Enter email or mobile"), "tech@biz.io");
    fireEvent.changeText(screen.getByPlaceholderText("Enter password"), "Password123!");
    const signInButton = screen.getByLabelText("Sign in");
    fireEvent.press(signInButton);
    fireEvent.press(signInButton);
    fireEvent.press(signInButton);

    resolveLogin!({ ok: true, data: { mfa_required: false, access_token: "a", refresh_token: "r", user: {}, tenant: {} }, meta: {} });
    await waitFor(() => expect(mockEstablishSession).toHaveBeenCalledTimes(1));
    expect(authApi.login).toHaveBeenCalledTimes(1);
  });

  it("transitions to the MFA screen (not an error) when the backend returns mfa_required", async () => {
    (authApi.login as jest.Mock).mockResolvedValue({
      ok: true, data: { mfa_required: true, mfa_challenge_token: "challenge-123" }, meta: {},
    });
    renderScreen();
    fireEvent.changeText(screen.getByPlaceholderText("Enter email or mobile"), "tech@biz.io");
    fireEvent.changeText(screen.getByPlaceholderText("Enter password"), "Password123!");
    fireEvent.press(screen.getByText("Sign in"));

    await waitFor(() => expect(navigation.navigate).toHaveBeenCalledWith("Mfa", { mfaChallengeToken: "challenge-123", rememberDevice: false }));
    expect(mockEstablishSession).not.toHaveBeenCalled();
  });

  it("passes the checked Remember-this-device state through to the MFA screen", async () => {
    (authApi.login as jest.Mock).mockResolvedValue({
      ok: true, data: { mfa_required: true, mfa_challenge_token: "challenge-456" }, meta: {},
    });
    renderScreen();
    fireEvent.changeText(screen.getByPlaceholderText("Enter email or mobile"), "tech@biz.io");
    fireEvent.changeText(screen.getByPlaceholderText("Enter password"), "Password123!");
    fireEvent.press(screen.getByLabelText("Remember this device"));
    fireEvent.press(screen.getByText("Sign in"));

    await waitFor(() => expect(navigation.navigate).toHaveBeenCalledWith("Mfa", { mfaChallengeToken: "challenge-456", rememberDevice: true }));
  });

  it("shows a safe generic message for an unrecognized backend error", async () => {
    (authApi.login as jest.Mock).mockResolvedValue({
      ok: false, error: { code: "UNKNOWN_API_ERROR", category: "unknown", safeMessage: "Something went wrong on our end. Please try again.", retryable: false },
    });
    renderScreen();
    fireEvent.changeText(screen.getByPlaceholderText("Enter email or mobile"), "tech@biz.io");
    fireEvent.changeText(screen.getByPlaceholderText("Enter password"), "Password123!");
    fireEvent.press(screen.getByText("Sign in"));

    await waitFor(() => expect(screen.getByText("Something went wrong on our end. Please try again.")).toBeTruthy());
  });

  it("never constructs an Authorization header itself -- login is delegated entirely to authApi", async () => {
    (authApi.login as jest.Mock).mockResolvedValue({ ok: true, data: { mfa_required: false, access_token: "a", refresh_token: "r", user: {}, tenant: {} }, meta: {} });
    renderScreen();
    fireEvent.changeText(screen.getByPlaceholderText("Enter email or mobile"), "tech@biz.io");
    fireEvent.changeText(screen.getByPlaceholderText("Enter password"), "Password123!");
    fireEvent.press(screen.getByText("Sign in"));
    await waitFor(() => expect(authApi.login).toHaveBeenCalled());
    const callArg = (authApi.login as jest.Mock).mock.calls[0][0];
    expect(callArg).not.toHaveProperty("Authorization");
    expect(callArg).not.toHaveProperty("headers");
  });
});

describe("LoginScreen — Mobile OTP request", () => {
  it("switches to OTP mode and navigates to code entry on Send code (enumeration-safe regardless of backend response)", async () => {
    (authApi.sendOtp as jest.Mock).mockResolvedValue({ ok: true, data: { message: "OTP sent." }, meta: {} });
    renderScreen();
    fireEvent.press(screen.getByText("Mobile OTP"));
    fireEvent.changeText(screen.getByPlaceholderText("Enter mobile number"), "9876543210");
    fireEvent.press(screen.getByText("Send code"));

    await waitFor(() => expect(navigation.navigate).toHaveBeenCalledWith("OtpVerify", { phone: "9876543210" }));
  });
});
