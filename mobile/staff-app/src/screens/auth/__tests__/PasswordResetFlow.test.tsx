import React from "react";
import { render, screen, waitFor, fireEvent } from "@testing-library/react-native";
import { ThemeProvider } from "../../../design-system/themes";
import { ForgotPasswordScreen } from "../ForgotPasswordScreen";
import { ResetPasswordScreen } from "../ResetPasswordScreen";

jest.mock("../../../services/auth/authApi");
jest.mock("../../../hooks/useNetworkStatus", () => ({ useNetworkStatus: () => ({ meta: { readiness: "production_ready" }, networkState: "online", cacheState: "fresh", pendingDrafts: 0, syncState: "idle" }) }));

import * as authApi from "../../../services/auth/authApi";

const navigation = { navigate: jest.fn(), reset: jest.fn() } as any;

beforeEach(() => jest.clearAllMocks());

describe("ForgotPasswordScreen (spec section 7, 17)", () => {
  function renderScreen() {
    return render(<ThemeProvider><ForgotPasswordScreen navigation={navigation} route={{ key: "ForgotPassword", name: "ForgotPassword", params: undefined }} /></ThemeProvider>);
  }

  it("shows the same enumeration-safe confirmation regardless of whether the account exists", async () => {
    (authApi.requestPasswordReset as jest.Mock).mockResolvedValue({ ok: true, data: { message: "If an account exists, a reset OTP has been sent." }, meta: {} });
    renderScreen();
    fireEvent.changeText(screen.getByPlaceholderText("Enter email or mobile"), "tech@biz.io");
    fireEvent.press(screen.getByText("Send reset code"));
    await waitFor(() => expect(screen.getByText(/If this account exists/)).toBeTruthy());
  });

  it("shows the identical message even when the backend enumeration-safe response reports failure shape", async () => {
    (authApi.requestPasswordReset as jest.Mock).mockResolvedValue({ ok: true, data: { message: "If an account exists, a reset OTP has been sent." }, meta: {} });
    renderScreen();
    fireEvent.changeText(screen.getByPlaceholderText("Enter email or mobile"), "unknown@biz.io");
    fireEvent.press(screen.getByText("Send reset code"));
    await waitFor(() => expect(screen.getByText(/If this account exists/)).toBeTruthy());
  });

  it("surfaces a real network failure distinctly instead of the enumeration-safe message", async () => {
    (authApi.requestPasswordReset as jest.Mock).mockResolvedValue({ ok: false, error: { code: "NETWORK_TIMEOUT", category: "network", safeMessage: "Couldn't reach ServiceOS. Check your connection and try again.", retryable: true } });
    renderScreen();
    fireEvent.changeText(screen.getByPlaceholderText("Enter email or mobile"), "tech@biz.io");
    fireEvent.press(screen.getByText("Send reset code"));
    await waitFor(() => expect(screen.getByText("Couldn't reach ServiceOS. Check your connection and try again.")).toBeTruthy());
  });
});

describe("ResetPasswordScreen (spec section 7, 17)", () => {
  const route = { key: "ResetPassword", name: "ResetPassword", params: { identifier: { email: "tech@biz.io" } } } as any;
  function renderScreen() {
    return render(<ThemeProvider><ResetPasswordScreen navigation={navigation} route={route} /></ThemeProvider>);
  }

  it("resets successfully and navigates to ResetSuccess without establishing a session", async () => {
    (authApi.confirmPasswordReset as jest.Mock).mockResolvedValue({ ok: true, data: { message: "Your password has been reset." }, meta: {} });
    renderScreen();
    fireEvent.changeText(screen.getByLabelText("Reset code"), "123456");
    fireEvent.changeText(screen.getByPlaceholderText("Enter new password"), "NewPassw0rd!");
    fireEvent.changeText(screen.getByPlaceholderText("Re-enter new password"), "NewPassw0rd!");
    fireEvent.press(screen.getByText("Reset password"));
    await waitFor(() => expect(navigation.reset).toHaveBeenCalledWith({ index: 0, routes: [{ name: "ResetSuccess" }] }));
  });

  it("shows a mismatch error locally without calling the backend when passwords don't match", async () => {
    renderScreen();
    fireEvent.changeText(screen.getByLabelText("Reset code"), "123456");
    fireEvent.changeText(screen.getByPlaceholderText("Enter new password"), "NewPassw0rd!");
    fireEvent.changeText(screen.getByPlaceholderText("Re-enter new password"), "Different1!");
    fireEvent.press(screen.getByText("Reset password"));
    await waitFor(() => expect(screen.getByText("Passwords don't match.")).toBeTruthy());
    expect(authApi.confirmPasswordReset).not.toHaveBeenCalled();
  });

  it("shows a safe error on an invalid/expired reset code", async () => {
    (authApi.confirmPasswordReset as jest.Mock).mockResolvedValue({
      ok: false, error: { code: "UNKNOWN_API_ERROR", category: "unknown", safeMessage: "This reset code is invalid or has expired.", retryable: false },
    });
    renderScreen();
    fireEvent.changeText(screen.getByLabelText("Reset code"), "000000");
    fireEvent.changeText(screen.getByPlaceholderText("Enter new password"), "NewPassw0rd!");
    fireEvent.changeText(screen.getByPlaceholderText("Re-enter new password"), "NewPassw0rd!");
    fireEvent.press(screen.getByText("Reset password"));
    await waitFor(() => expect(screen.getByText("This reset code is invalid or has expired.")).toBeTruthy());
    expect(navigation.reset).not.toHaveBeenCalled();
  });
});
