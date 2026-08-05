import { request } from "../httpClient";
import { DomainError } from "../../../domain/errors";
import * as networkState from "../../networkState";

function mockFetchOnce(status: number, body: unknown, headers: Record<string, string> = {}) {
  (global.fetch as jest.Mock).mockResolvedValueOnce({
    ok: status >= 200 && status < 300,
    status,
    headers: { get: (name: string) => headers[name.toLowerCase()] ?? headers[name] ?? null },
    text: async () => JSON.stringify(body),
  });
}

describe("httpClient.request", () => {
  beforeEach(() => {
    (global as unknown as { fetch: jest.Mock }).fetch = jest.fn();
    jest.spyOn(networkState, "isOffline").mockReturnValue(false);
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  it("builds the URL by joining the base URL and path without a double slash", async () => {
    mockFetchOnce(200, { success: true, data: {}, meta: { request_id: "r1" } });
    await request({ method: "GET", path: "/v1/auth/me" });
    const calledUrl = (global.fetch as jest.Mock).mock.calls[0][0];
    expect(calledUrl).not.toMatch(/\/\/v1/);
    expect(calledUrl.endsWith("/v1/auth/me")).toBe(true);
  });

  it("attaches Authorization only when an access token is provided", async () => {
    mockFetchOnce(200, { success: true, data: {}, meta: { request_id: "r1" } });
    await request({ method: "GET", path: "/x", accessToken: "abc123" });
    const options = (global.fetch as jest.Mock).mock.calls[0][1];
    expect(options.headers.Authorization).toBe("Bearer abc123");
  });

  it("omits Authorization when no access token is provided", async () => {
    mockFetchOnce(200, { success: true, data: {}, meta: { request_id: "r1" } });
    await request({ method: "GET", path: "/x" });
    const options = (global.fetch as jest.Mock).mock.calls[0][1];
    expect(options.headers.Authorization).toBeUndefined();
  });

  it("attaches Idempotency-Key only when supplied", async () => {
    mockFetchOnce(200, { success: true, data: {}, meta: { request_id: "r1" } });
    await request({ method: "POST", path: "/x", idempotencyKey: "key-1" });
    const options = (global.fetch as jest.Mock).mock.calls[0][1];
    expect(options.headers["Idempotency-Key"]).toBe("key-1");
  });

  it("throws a mapped DomainError on a non-2xx problem+json response", async () => {
    mockFetchOnce(401, { error_code: "UNAUTHORIZED", detail: "Invalid email or password." });
    await expect(request({ method: "POST", path: "/v1/auth/login" })).rejects.toMatchObject({
      category: "AUTH_REQUIRED",
    });
  });

  it("throws NETWORK_UNAVAILABLE immediately when the device is known offline", async () => {
    jest.spyOn(networkState, "isOffline").mockReturnValue(true);
    await expect(request({ method: "GET", path: "/x" })).rejects.toMatchObject({ category: "NETWORK_UNAVAILABLE" });
    expect(global.fetch).not.toHaveBeenCalled();
  });

  it("propagates a fetch-level network failure as NETWORK_UNAVAILABLE", async () => {
    (global.fetch as jest.Mock).mockRejectedValueOnce(new Error("getaddrinfo failed"));
    await expect(request({ method: "GET", path: "/x" })).rejects.toMatchObject({ category: "NETWORK_UNAVAILABLE" });
  });

  it("times out and rejects with TIMEOUT for a request that never resolves", async () => {
    (global.fetch as jest.Mock).mockImplementationOnce(
      (_url: string, opts: { signal: AbortSignal }) =>
        new Promise((_resolve, reject) => {
          opts.signal.addEventListener("abort", () => reject(new DOMException("Aborted", "AbortError")));
        }),
    );
    await expect(request({ method: "GET", path: "/x", timeoutMs: 20 })).rejects.toMatchObject({ category: "TIMEOUT" });
  });

  it("rejects with CONTRACT_MISMATCH when a successful response is not valid JSON", async () => {
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true, status: 200, headers: { get: () => null }, text: async () => "<html>not json</html>",
    });
    await expect(request({ method: "GET", path: "/x" })).rejects.toMatchObject({ category: "CONTRACT_MISMATCH" });
  });
});
