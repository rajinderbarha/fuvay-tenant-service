import { mapApiError } from "../errorMapper";

describe("mapApiError", () => {
  it("maps the backend TOKEN_BLACKLISTED code (refresh reuse detection) to SESSION_EXPIRED", () => {
    const err = mapApiError({
      httpStatus: 401,
      body: { error_code: "TOKEN_BLACKLISTED", detail: "Security alert: token reuse detected." },
      diagnostic: "fallback",
    });
    expect(err.category).toBe("SESSION_EXPIRED");
    expect(err.telemetryMeta).toEqual({ backendCode: "TOKEN_BLACKLISTED" });
  });

  it("maps ACCOUNT_LOCKED to ACCOUNT_SUSPENDED", () => {
    const err = mapApiError({ httpStatus: 423, body: { error_code: "ACCOUNT_LOCKED", detail: "locked" }, diagnostic: "x" });
    expect(err.category).toBe("ACCOUNT_SUSPENDED");
  });

  it("maps a 429 to RATE_LIMITED even without a recognized backend code", () => {
    const err = mapApiError({ httpStatus: 429, body: { detail: "slow down" }, diagnostic: "x" });
    expect(err.category).toBe("RATE_LIMITED");
  });

  it("maps a 409 to CONFLICT_STALE_WORKFLOW", () => {
    const err = mapApiError({ httpStatus: 409, body: { detail: "conflict" }, diagnostic: "x" });
    expect(err.category).toBe("CONFLICT_STALE_WORKFLOW");
  });

  it("falls back to the generic HTTP-status mapping for an unrecognized code", () => {
    const err = mapApiError({ httpStatus: 403, body: { error_code: "SOME_NEW_CODE", detail: "denied" }, diagnostic: "x" });
    expect(err.category).toBe("FORBIDDEN");
    expect(err.telemetryMeta).toEqual({ backendCode: "SOME_NEW_CODE" });
  });

  it("never exposes the raw problem+json body as the diagnostic when `detail` is customer-safe", () => {
    const err = mapApiError({ httpStatus: 500, body: { detail: "Service temporarily unavailable." }, diagnostic: "raw stack" });
    expect(err.diagnostic).toBe("Service temporarily unavailable.");
    expect(err.category).toBe("BACKEND_UNAVAILABLE");
  });
});
