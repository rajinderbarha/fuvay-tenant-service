jest.mock("../authApi", () => ({ refreshToken: jest.fn() }));
jest.mock("../sessionStorage", () => ({
  writeSessionBundle: jest.fn().mockResolvedValue(undefined),
  clearSessionBundle: jest.fn().mockResolvedValue(undefined),
}));
jest.mock("../sessionEvents", () => ({ emitSessionEvent: jest.fn() }));

import { refresh } from "../refreshCoordinator";
import * as authApi from "../authApi";
import { writeSessionBundle, clearSessionBundle } from "../sessionStorage";
import { emitSessionEvent } from "../sessionEvents";
import * as tokenCoordinator from "../tokenCoordinator";

beforeEach(() => {
  tokenCoordinator.__resetTokenCoordinatorForTests();
  jest.clearAllMocks();
});

describe("refreshCoordinator.refresh — concurrency safety (spec section 9)", () => {
  it("dedupes concurrent callers into exactly one network call", async () => {
    tokenCoordinator.establishTokens({ accessToken: "a1", refreshToken: "r1", sessionId: "s1" });
    let resolveFn: (v: any) => void;
    (authApi.refreshToken as jest.Mock).mockReturnValue(new Promise(res => { resolveFn = res; }));

    const p1 = refresh();
    const p2 = refresh();
    const p3 = refresh();
    resolveFn!({ ok: true, data: { access_token: "a2", refresh_token: "r2" }, meta: {} });
    const [r1, r2, r3] = await Promise.all([p1, p2, p3]);

    expect(authApi.refreshToken).toHaveBeenCalledTimes(1);
    expect(r1).toEqual(r2);
    expect(r2).toEqual(r3);
  });

  it("on success: persists atomically, updates in-memory tokens, and emits SESSION_REFRESHED", async () => {
    tokenCoordinator.establishTokens({ accessToken: "a1", refreshToken: "r1", sessionId: "s1" });
    (authApi.refreshToken as jest.Mock).mockResolvedValue({ ok: true, data: { access_token: "a2", refresh_token: "r2" }, meta: {} });

    const result = await refresh();

    expect(result).toEqual({ ok: true, accessToken: "a2" });
    expect(writeSessionBundle).toHaveBeenCalledWith({ schemaVersion: 1, accessToken: "a2", refreshToken: "r2", sessionId: "s1" });
    expect(tokenCoordinator.getAccessToken()).toBe("a2");
    expect(emitSessionEvent).toHaveBeenCalledWith({ type: "SESSION_REFRESHED" });
  });

  it("on REFRESH_TOKEN_EXPIRED: clears the session and emits SESSION_EXPIRED", async () => {
    tokenCoordinator.establishTokens({ accessToken: "a1", refreshToken: "r1", sessionId: "s1" });
    (authApi.refreshToken as jest.Mock).mockResolvedValue({ ok: false, error: { code: "REFRESH_TOKEN_EXPIRED", category: "auth", safeMessage: "x", retryable: false } });

    const result = await refresh();

    expect(result).toEqual({ ok: false });
    expect(clearSessionBundle).toHaveBeenCalled();
    expect(tokenCoordinator.getAccessToken()).toBeNull();
    expect(emitSessionEvent).toHaveBeenCalledWith(expect.objectContaining({ type: "SESSION_EXPIRED" }));
  });

  it("on REFRESH_TOKEN_REUSED (theft detection): clears the session and emits SESSION_REVOKED, not SESSION_EXPIRED", async () => {
    tokenCoordinator.establishTokens({ accessToken: "a1", refreshToken: "r1", sessionId: "s1" });
    (authApi.refreshToken as jest.Mock).mockResolvedValue({ ok: false, error: { code: "REFRESH_TOKEN_REUSED", category: "auth", safeMessage: "x", retryable: false } });

    const result = await refresh();

    expect(result).toEqual({ ok: false });
    expect(emitSessionEvent).toHaveBeenCalledWith(expect.objectContaining({ type: "SESSION_REVOKED", reasonCode: "REFRESH_TOKEN_REUSED" }));
  });

  it("fails closed (clears session) when persistence fails after a successful rotation", async () => {
    tokenCoordinator.establishTokens({ accessToken: "a1", refreshToken: "r1", sessionId: "s1" });
    (authApi.refreshToken as jest.Mock).mockResolvedValue({ ok: true, data: { access_token: "a2", refresh_token: "r2" }, meta: {} });
    (writeSessionBundle as jest.Mock).mockRejectedValueOnce(new Error("disk full"));

    const result = await refresh();

    expect(result).toEqual({ ok: false });
    expect(clearSessionBundle).toHaveBeenCalled();
    expect(tokenCoordinator.getAccessToken()).toBeNull();
  });

  it("a transient network failure during refresh does NOT clear the session (still recoverable later)", async () => {
    tokenCoordinator.establishTokens({ accessToken: "a1", refreshToken: "r1", sessionId: "s1" });
    (authApi.refreshToken as jest.Mock).mockResolvedValue({ ok: false, error: { code: "NETWORK_TIMEOUT", category: "network", safeMessage: "x", retryable: true } });

    const result = await refresh();

    expect(result).toEqual({ ok: false });
    expect(clearSessionBundle).not.toHaveBeenCalled();
    expect(tokenCoordinator.getAccessToken()).toBe("a1"); // untouched
  });

  it("with no refresh token present, fails closed immediately without a network call", async () => {
    const result = await refresh();
    expect(result).toEqual({ ok: false });
    expect(authApi.refreshToken).not.toHaveBeenCalled();
  });
});
