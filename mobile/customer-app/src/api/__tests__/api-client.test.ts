import { apiClient } from "../api-client";
import { setAuthTokenProvider, setUnauthorizedHandler } from "../request-context";

function jsonResponse(body: unknown, status = 200) {
  return {
    ok: status >= 200 && status < 300,
    status,
    headers: { get: () => null },
    json: async () => body,
  } as unknown as Response;
}

describe("api-client unauthorized-retry integration", () => {
  const originalFetch = global.fetch;

  afterEach(() => {
    global.fetch = originalFetch;
    setAuthTokenProvider(null);
    setUnauthorizedHandler(null);
    jest.restoreAllMocks();
  });

  it("retries exactly once after a successful refresh on a 401", async () => {
    let call = 0;
    global.fetch = jest.fn(async () => {
      call += 1;
      if (call === 1) return jsonResponse({ error_code: "UNAUTHORIZED" }, 401);
      return jsonResponse({ data: { ok: true } }, 200);
    }) as unknown as typeof fetch;

    const refreshHandler = jest.fn(async () => true);
    setUnauthorizedHandler(refreshHandler);

    const result = await apiClient.get<{ ok: boolean }>("/v1/auth/me");
    expect(result).toEqual({ ok: true });
    expect(refreshHandler).toHaveBeenCalledTimes(1);
    expect(call).toBe(2);
  });

  it("does not retry a second time if the retried request also returns 401", async () => {
    global.fetch = jest.fn(async () => jsonResponse({ error_code: "UNAUTHORIZED" }, 401)) as unknown as typeof fetch;
    const refreshHandler = jest.fn(async () => true);
    setUnauthorizedHandler(refreshHandler);

    await expect(apiClient.get("/v1/auth/me")).rejects.toMatchObject({ category: "unauthorized" });
    expect(refreshHandler).toHaveBeenCalledTimes(1);
  });

  it("propagates the 401 without retrying when the handler cannot refresh", async () => {
    global.fetch = jest.fn(async () => jsonResponse({ error_code: "UNAUTHORIZED" }, 401)) as unknown as typeof fetch;
    const refreshHandler = jest.fn(async () => false);
    setUnauthorizedHandler(refreshHandler);

    await expect(apiClient.get("/v1/auth/me")).rejects.toMatchObject({ category: "unauthorized" });
    expect(refreshHandler).toHaveBeenCalledTimes(1);
  });

  it("does not invoke the unauthorized handler for a request that opted out of auth", async () => {
    global.fetch = jest.fn(async () => jsonResponse({ error_code: "UNAUTHORIZED" }, 401)) as unknown as typeof fetch;
    const refreshHandler = jest.fn(async () => true);
    setUnauthorizedHandler(refreshHandler);

    await expect(apiClient.post("/v1/auth/otp/verify", {}, { skipAuth: true })).rejects.toMatchObject({ category: "unauthorized" });
    expect(refreshHandler).not.toHaveBeenCalled();
  });
});
