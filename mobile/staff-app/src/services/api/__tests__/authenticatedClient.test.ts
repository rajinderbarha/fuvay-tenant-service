import { authenticatedRequest, registerRefreshHandler, __resetRefreshHandlerForTests } from "../authenticatedClient";
import * as tokenCoordinator from "../../auth/tokenCoordinator";
import { emitSessionEvent } from "../../auth/sessionEvents";

jest.mock("../apiClient", () => ({ performRequest: jest.fn() }));
jest.mock("../../auth/sessionEvents", () => ({ emitSessionEvent: jest.fn() }));

import { performRequest } from "../apiClient";

beforeEach(() => {
  tokenCoordinator.__resetTokenCoordinatorForTests();
  __resetRefreshHandlerForTests();
  jest.clearAllMocks();
});

describe("authenticatedRequest", () => {
  it("fails closed with AUTH_REQUIRED when there is no access token, without calling the transport", async () => {
    const result = await authenticatedRequest("/v1/auth/me");
    expect(result).toEqual({ ok: false, error: expect.objectContaining({ code: "AUTH_REQUIRED" }) });
    expect(performRequest).not.toHaveBeenCalled();
  });

  it("never triggers a refresh on a 403 (permission) failure", async () => {
    tokenCoordinator.establishTokens({ accessToken: "a1", refreshToken: "r1", sessionId: null });
    (performRequest as jest.Mock).mockResolvedValueOnce({ ok: false, error: { code: "CAPABILITY_REQUIRED", category: "permission", safeMessage: "x", retryable: false } });
    const refreshHandler = jest.fn();
    registerRefreshHandler(refreshHandler);

    const result = await authenticatedRequest("/v1/some/action");

    expect(refreshHandler).not.toHaveBeenCalled();
    expect(performRequest).toHaveBeenCalledTimes(1);
    expect(result.ok).toBe(false);
  });

  it("emits SESSION_EXPIRED for a non-token auth-category failure (e.g. AUTH_REQUIRED) without refreshing", async () => {
    tokenCoordinator.establishTokens({ accessToken: "a1", refreshToken: "r1", sessionId: null });
    (performRequest as jest.Mock).mockResolvedValueOnce({ ok: false, error: { code: "SESSION_REVOKED", category: "auth", safeMessage: "x", retryable: false } });
    await authenticatedRequest("/v1/auth/me");
    expect(emitSessionEvent).toHaveBeenCalledWith(expect.objectContaining({ type: "SESSION_EXPIRED" }));
  });

  it("on ACCESS_TOKEN_EXPIRED, refreshes exactly once and replays the ORIGINAL request exactly once with the new token", async () => {
    tokenCoordinator.establishTokens({ accessToken: "old-token", refreshToken: "r1", sessionId: null });
    (performRequest as jest.Mock)
      .mockResolvedValueOnce({ ok: false, error: { code: "ACCESS_TOKEN_EXPIRED", category: "auth", safeMessage: "x", retryable: false } })
      .mockResolvedValueOnce({ ok: true, data: { hello: "world" }, meta: {} as any });
    const refreshHandler = jest.fn().mockResolvedValue({ ok: true, accessToken: "new-token" });
    registerRefreshHandler(refreshHandler);

    const result = await authenticatedRequest("/v1/auth/me");

    expect(refreshHandler).toHaveBeenCalledTimes(1);
    expect(performRequest).toHaveBeenCalledTimes(2);
    const secondCallHeaders = (performRequest as jest.Mock).mock.calls[1][0].headers;
    expect(secondCallHeaders.Authorization).toBe("Bearer new-token");
    expect(result).toEqual({ ok: true, data: { hello: "world" }, meta: {} });
  });

  it("returns the original error (no replay, no crash) when the refresh itself fails", async () => {
    tokenCoordinator.establishTokens({ accessToken: "old-token", refreshToken: "r1", sessionId: null });
    const originalError = { ok: false, error: { code: "ACCESS_TOKEN_EXPIRED", category: "auth", safeMessage: "x", retryable: false } };
    (performRequest as jest.Mock).mockResolvedValueOnce(originalError);
    registerRefreshHandler(jest.fn().mockResolvedValue({ ok: false }));

    const result = await authenticatedRequest("/v1/auth/me");

    expect(performRequest).toHaveBeenCalledTimes(1); // no replay attempted
    expect(result).toEqual(originalError);
  });

  it("discards a would-be replay if the session generation changed while refreshing (logout/account-switch mid-flight)", async () => {
    tokenCoordinator.establishTokens({ accessToken: "old-token", refreshToken: "r1", sessionId: null });
    (performRequest as jest.Mock).mockResolvedValueOnce({ ok: false, error: { code: "ACCESS_TOKEN_EXPIRED", category: "auth", safeMessage: "x", retryable: false } });
    registerRefreshHandler(jest.fn().mockImplementation(async () => {
      // Simulate a logout happening while this refresh was in flight.
      tokenCoordinator.clearTokens();
      return { ok: true, accessToken: "new-token" };
    }));

    const result = await authenticatedRequest("/v1/auth/me");

    expect(performRequest).toHaveBeenCalledTimes(1); // never replayed into the new generation
    expect(result).toEqual({ ok: false, error: expect.objectContaining({ code: "REQUEST_CANCELLED" }) });
  });
});
