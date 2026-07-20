import { normalizeApiError, ApiError } from "../api-errors";

describe("normalizeApiError", () => {
  it("normalizes a fetch TypeError into network_error", () => {
    const err = normalizeApiError(new TypeError("Network request failed"));
    expect(err).toBeInstanceOf(ApiError);
    expect(err.category).toBe("network_error");
    expect(err.retryable).toBe(true);
  });

  it("normalizes an AbortError into cancelled", () => {
    const err = normalizeApiError(new DOMException("Aborted", "AbortError"));
    expect(err.category).toBe("cancelled");
  });

  it("normalizes a timeout Error into timeout", () => {
    const err = normalizeApiError(new Error("timeout"));
    expect(err.category).toBe("timeout");
    expect(err.retryable).toBe(true);
  });

  it.each([
    [400, "validation_error"],
    [422, "validation_error"],
    [401, "unauthorized"],
    [403, "forbidden"],
    [404, "not_found"],
    [409, "conflict"],
    [429, "rate_limited"],
    [500, "server_error"],
    [503, "maintenance"],
  ] as const)("maps HTTP %i to category %s", (status, category) => {
    const err = normalizeApiError(null, { status });
    expect(err.category).toBe(category);
  });

  it("maps a status outside every known range to unknown_error", () => {
    const err = normalizeApiError(null, { status: 300 });
    expect(err.category).toBe("unknown_error");
  });

  it("maps any 5xx status not otherwise mapped to server_error", () => {
    const err = normalizeApiError(null, { status: 599 });
    expect(err.category).toBe("server_error");
  });

  it("falls back to unknown_error for an unrecognized failure shape", () => {
    const err = normalizeApiError({ weird: true });
    expect(err.category).toBe("unknown_error");
  });

  it("never leaks a raw server message for user-facing categories", () => {
    const err = normalizeApiError(null, { status: 500 });
    expect(err.message).not.toMatch(/stack|traceback|exception/i);
  });

  it("passes an already-normalized ApiError through unchanged", () => {
    const original = new ApiError({ category: "conflict", message: "x" });
    expect(normalizeApiError(original)).toBe(original);
  });

  it("carries the request id through for correlation", () => {
    const err = normalizeApiError(null, { status: 404, requestId: "req_abc" });
    expect(err.requestId).toBe("req_abc");
  });

  it("rate-limited and server errors are retryable; validation and not-found are not", () => {
    expect(normalizeApiError(null, { status: 429 }).retryable).toBe(true);
    expect(normalizeApiError(null, { status: 500 }).retryable).toBe(true);
    expect(normalizeApiError(null, { status: 400 }).retryable).toBe(false);
    expect(normalizeApiError(null, { status: 404 }).retryable).toBe(false);
  });
});
