import React from "react";
import { renderHook, act } from "@testing-library/react-native";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useLogoutAll } from "../use-logout-all";
import { persistSession, getSessionState, __resetSessionStoreForTests } from "../../state/session-store";
import type { CustomerSession } from "../../domain/session";

jest.mock("../../api/auth-api", () => ({ authApi: { logoutAll: jest.fn() } }));
jest.mock("../../../../app/startup/startup-service", () => ({ reevaluateStartup: jest.fn(async () => undefined) }));
// eslint-disable-next-line @typescript-eslint/no-var-requires
const mockedAuthApi = require("../../api/auth-api").authApi;

function session(overrides: Partial<CustomerSession> = {}): CustomerSession {
  return {
    accessToken: "at1",
    refreshToken: "rt1",
    userId: "u1",
    fullName: "Jane Doe",
    displayName: null,
    phone: "+919876543210",
    email: "jane@example.com",
    language: "en",
    role: "customer",
    tenantId: null,
    isVerified: true,
    onboardingComplete: true,
    avatarUrl: null,
    ...overrides,
  };
}

function makeWrapper() {
  const client = new QueryClient();
  return function TestQueryClientWrapper({ children }: { children: React.ReactNode }) {
    return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
  };
}

describe("useLogoutAll", () => {
  let wrapper: ReturnType<typeof makeWrapper>;

  beforeEach(async () => {
    __resetSessionStoreForTests();
    await persistSession(session());
    jest.clearAllMocks();
    wrapper = makeWrapper();
  });

  it("clears the local session and returns the revoked count on success", async () => {
    mockedAuthApi.logoutAll.mockResolvedValue({ sessions_revoked: 3, message: "ok" });
    const { result } = renderHook(() => useLogoutAll(), { wrapper });

    let outcome;
    await act(async () => {
      outcome = await result.current.logoutAll();
    });

    expect(outcome).toEqual({ sessionsRevoked: 3 });
    expect(getSessionState().status).toBe("guest");
  });

  it("still clears the local session when the server call fails", async () => {
    mockedAuthApi.logoutAll.mockRejectedValue(new Error("network down"));
    const { result } = renderHook(() => useLogoutAll(), { wrapper });

    let outcome;
    await act(async () => {
      outcome = await result.current.logoutAll();
    });

    expect(outcome).toBeNull();
    expect(getSessionState().status).toBe("guest");
  });
});
