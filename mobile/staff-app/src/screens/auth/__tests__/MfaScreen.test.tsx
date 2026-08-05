import React from "react";
import { render, screen, waitFor, fireEvent } from "@testing-library/react-native";
import { ThemeProvider } from "../../../design-system/themes";
import { MfaScreen } from "../MfaScreen";

jest.mock("../../../services/auth/authApi");
jest.mock("../../../hooks/useNetworkStatus", () => ({ useNetworkStatus: () => ({ meta: { readiness: "production_ready" }, networkState: "online", cacheState: "fresh", pendingDrafts: 0, syncState: "idle" }) }));

const mockEstablishSession = jest.fn().mockResolvedValue(undefined);
jest.mock("../../../navigation/session/SessionProvider", () => ({
  useSession: () => ({ establishSession: mockEstablishSession }),
}));

import * as authApi from "../../../services/auth/authApi";

const navigation = { navigate: jest.fn() } as any;

function renderScreen(rememberDevice = false) {
  const route = { key: "Mfa", name: "Mfa", params: { mfaChallengeToken: "challenge-abc", rememberDevice } } as any;
  return render(<ThemeProvider><MfaScreen navigation={navigation} route={route} /></ThemeProvider>);
}

beforeEach(() => jest.clearAllMocks());

describe("MfaScreen (spec sections 5, 6, 17)", () => {
  it("includes the challenge token in the verify request", async () => {
    (authApi.verifyMfa as jest.Mock).mockResolvedValue({
      ok: true, data: { mfa_required: false, access_token: "a", refresh_token: "r", user: {}, tenant: {} }, meta: {},
    });
    renderScreen();
    fireEvent.changeText(screen.getByLabelText("Authenticator code"), "123456");
    await waitFor(() => expect(authApi.verifyMfa).toHaveBeenCalledWith(expect.objectContaining({ mfaChallengeToken: "challenge-abc", code: "123456" })));
  });

  it("establishes the session only after a successful verification", async () => {
    (authApi.verifyMfa as jest.Mock).mockResolvedValue({
      ok: true, data: { mfa_required: false, access_token: "a1", refresh_token: "r1", user: {}, tenant: {} }, meta: {},
    });
    renderScreen();
    fireEvent.changeText(screen.getByLabelText("Authenticator code"), "654321");
    await waitFor(() => expect(mockEstablishSession).toHaveBeenCalledWith({ access_token: "a1", refresh_token: "r1" }));
  });

  it("does not establish a session on an invalid/expired challenge", async () => {
    (authApi.verifyMfa as jest.Mock).mockResolvedValue({
      ok: false, error: { code: "INVALID_TOKEN", category: "auth", safeMessage: "Invalid or expired MFA challenge token.", retryable: false },
    });
    renderScreen();
    fireEvent.changeText(screen.getByLabelText("Authenticator code"), "111111");
    await waitFor(() => expect(screen.getByText("Invalid or expired MFA challenge token.")).toBeTruthy());
    expect(mockEstablishSession).not.toHaveBeenCalled();
  });

  it("passes rememberDevice through to verifyMfa only when it was actually checked earlier in the flow", async () => {
    (authApi.verifyMfa as jest.Mock).mockResolvedValue({
      ok: true, data: { mfa_required: false, access_token: "a", refresh_token: "r", user: {}, tenant: {} }, meta: {},
    });
    renderScreen(true);
    fireEvent.changeText(screen.getByLabelText("Authenticator code"), "222222");
    await waitFor(() => expect(authApi.verifyMfa).toHaveBeenCalledWith(expect.objectContaining({ rememberDevice: true })));
  });

  it("never sends rememberDevice:true when it was not requested", async () => {
    (authApi.verifyMfa as jest.Mock).mockResolvedValue({
      ok: true, data: { mfa_required: false, access_token: "a", refresh_token: "r", user: {}, tenant: {} }, meta: {},
    });
    renderScreen(false);
    fireEvent.changeText(screen.getByLabelText("Authenticator code"), "333333");
    await waitFor(() => expect(authApi.verifyMfa).toHaveBeenCalledWith(expect.objectContaining({ rememberDevice: false })));
  });
});
