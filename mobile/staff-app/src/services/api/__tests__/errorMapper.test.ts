import { mapProblemDetail, mapNetworkFailure, mapUnknownFailure } from "../errorMapper";
import { ProblemDetailBody } from "../types";

function problem(overrides: Partial<ProblemDetailBody> = {}): ProblemDetailBody {
  return {
    type: "https://serviceos.io/errors/UNAUTHORIZED", title: "Unauthorized", status: 401,
    detail: "Authentication required.", error_code: "UNAUTHORIZED", ...overrides,
  };
}

describe("mapProblemDetail — every required category (spec section 10)", () => {
  it("UNAUTHORIZED -> AUTH_REQUIRED", () => {
    expect(mapProblemDetail(problem(), "authenticated").code).toBe("AUTH_REQUIRED");
  });

  it("INVALID_TOKEN on an authenticated request -> ACCESS_TOKEN_EXPIRED", () => {
    expect(mapProblemDetail(problem({ error_code: "INVALID_TOKEN" }), "authenticated").code).toBe("ACCESS_TOKEN_EXPIRED");
  });

  it("INVALID_TOKEN on a refresh call -> REFRESH_TOKEN_EXPIRED (same backend code, different meaning by context)", () => {
    expect(mapProblemDetail(problem({ error_code: "INVALID_TOKEN" }), "refresh").code).toBe("REFRESH_TOKEN_EXPIRED");
  });

  it("TOKEN_EXPIRED -> REFRESH_TOKEN_EXPIRED", () => {
    expect(mapProblemDetail(problem({ error_code: "TOKEN_EXPIRED" }), "refresh").code).toBe("REFRESH_TOKEN_EXPIRED");
  });

  it("TOKEN_BLACKLISTED on an authenticated request -> SESSION_REVOKED", () => {
    expect(mapProblemDetail(problem({ error_code: "TOKEN_BLACKLISTED" }), "authenticated").code).toBe("SESSION_REVOKED");
  });

  it("TOKEN_BLACKLISTED on a refresh call -> REFRESH_TOKEN_REUSED (theft-detection response)", () => {
    expect(mapProblemDetail(problem({ error_code: "TOKEN_BLACKLISTED" }), "refresh").code).toBe("REFRESH_TOKEN_REUSED");
  });

  it("SESSION_REVOKED passes through unchanged", () => {
    expect(mapProblemDetail(problem({ error_code: "SESSION_REVOKED" }), "authenticated").code).toBe("SESSION_REVOKED");
  });

  it("MFA_REQUIRED / MFA_SETUP_REQUIRED -> MFA_REQUIRED", () => {
    expect(mapProblemDetail(problem({ error_code: "MFA_REQUIRED" }), "public").code).toBe("MFA_REQUIRED");
    expect(mapProblemDetail(problem({ error_code: "MFA_SETUP_REQUIRED" }), "public").code).toBe("MFA_REQUIRED");
  });

  it("ACCOUNT_LOCKED -> ACCOUNT_SUSPENDED, retaining the backend's specific detail as safeMessage", () => {
    const result = mapProblemDetail(problem({ error_code: "ACCOUNT_LOCKED", detail: "Locked for 15 minutes." }), "public");
    expect(result.code).toBe("ACCOUNT_SUSPENDED");
    expect(result.safeMessage).toBe("Locked for 15 minutes.");
    expect(result.backendCode).toBe("ACCOUNT_LOCKED");
  });

  it("PERMISSION_DENIED -> CAPABILITY_REQUIRED and is never retryable", () => {
    const result = mapProblemDetail(problem({ error_code: "PERMISSION_DENIED", status: 403 }), "authenticated");
    expect(result.code).toBe("CAPABILITY_REQUIRED");
    expect(result.category).toBe("permission");
    expect(result.retryable).toBe(false);
  });

  it("TENANT_SUSPENDED -> TENANT_INACTIVE", () => {
    expect(mapProblemDetail(problem({ error_code: "TENANT_SUSPENDED" }), "authenticated").code).toBe("TENANT_INACTIVE");
  });

  it("VALIDATION_ERROR carries field errors and is not retryable", () => {
    const result = mapProblemDetail(problem({
      error_code: "VALIDATION_ERROR", status: 422,
      errors: [{ field: "email", message: "Invalid email" }],
    }), "public");
    expect(result.code).toBe("VALIDATION_ERROR");
    expect(result.category).toBe("validation");
    expect(result.fieldErrors).toEqual([{ field: "email", message: "Invalid email" }]);
    expect(result.retryable).toBe(false);
  });

  it("RATE_LIMITED respects retry_after_seconds from context and is retryable", () => {
    const result = mapProblemDetail(problem({ error_code: "RATE_LIMITED", status: 429, context: { retry_after_seconds: 42 } }), "public");
    expect(result.code).toBe("RATE_LIMITED");
    expect(result.retryAfterSeconds).toBe(42);
    expect(result.retryable).toBe(true);
  });

  it("CONFLICT is a conflict, never treated as a generic network failure", () => {
    const result = mapProblemDetail(problem({ error_code: "CONFLICT", status: 409 }), "authenticated");
    expect(result.category).toBe("conflict");
    expect(result.retryable).toBe(false);
  });

  it("a per-engine *_STALE_VERSION code normalizes to STALE_ENTITY_VERSION", () => {
    const result = mapProblemDetail(problem({ error_code: "DIRECT_PAYMENT_STALE_VERSION", status: 409 }), "authenticated");
    expect(result.code).toBe("STALE_ENTITY_VERSION");
    expect(result.category).toBe("conflict");
  });

  it("an unrecognized 5xx code -> UNKNOWN_API_ERROR with a generic safe message (never leaks backend detail)", () => {
    const result = mapProblemDetail(problem({ error_code: "SOME_NEW_BACKEND_CODE", status: 500, detail: "Traceback (most recent call last)..." }), "authenticated");
    expect(result.code).toBe("UNKNOWN_API_ERROR");
    expect(result.safeMessage).not.toMatch(/Traceback/);
    expect(result.retryable).toBe(true);
  });

  it("an unrecognized 4xx code -> UNKNOWN_API_ERROR but is not retryable", () => {
    const result = mapProblemDetail(problem({ error_code: "SOME_NEW_4XX_CODE", status: 418 }), "authenticated");
    expect(result.code).toBe("UNKNOWN_API_ERROR");
    expect(result.retryable).toBe(false);
  });

  // Phase Final — confirmed real backend codes that previously fell through
  // to a generic UNKNOWN_API_ERROR (audit finding): each must map to its
  // own specific, non-retryable AppErrorCode.
  it("ENTITY_NOT_ASSIGNED (estimate/work-execution/direct-payment 403s) passes through and is a permission error", () => {
    const result = mapProblemDetail(problem({ error_code: "ENTITY_NOT_ASSIGNED", status: 403 }), "authenticated");
    expect(result.code).toBe("ENTITY_NOT_ASSIGNED");
    expect(result.category).toBe("permission");
    expect(result.retryable).toBe(false);
  });

  it("JOB_TYPE_CONTEXT_UNRESOLVED passes through as a validation error", () => {
    const result = mapProblemDetail(problem({ error_code: "JOB_TYPE_CONTEXT_UNRESOLVED", status: 409 }), "authenticated");
    expect(result.code).toBe("JOB_TYPE_CONTEXT_UNRESOLVED");
    expect(result.category).toBe("validation");
    expect(result.retryable).toBe(false);
  });

  it("QUOTE_NOT_CURRENT passes through as a conflict, not UNKNOWN_API_ERROR", () => {
    const result = mapProblemDetail(problem({ error_code: "QUOTE_NOT_CURRENT", status: 409 }), "authenticated");
    expect(result.code).toBe("QUOTE_NOT_CURRENT");
    expect(result.category).toBe("conflict");
    expect(result.retryable).toBe(false);
  });

  it("APPROVED_ESTIMATE_IMMUTABLE passes through as a conflict", () => {
    const result = mapProblemDetail(problem({ error_code: "APPROVED_ESTIMATE_IMMUTABLE", status: 409 }), "authenticated");
    expect(result.code).toBe("APPROVED_ESTIMATE_IMMUTABLE");
    expect(result.category).toBe("conflict");
  });

  it("VERTICAL_DISABLED passes through as a permission error", () => {
    const result = mapProblemDetail(problem({ error_code: "VERTICAL_DISABLED", status: 403 }), "authenticated");
    expect(result.code).toBe("VERTICAL_DISABLED");
    expect(result.category).toBe("permission");
  });

  it("MEDIA_STORAGE_UNAVAILABLE (the real backend string) passes through as a server error", () => {
    const result = mapProblemDetail(problem({ error_code: "MEDIA_STORAGE_UNAVAILABLE", status: 503 }), "authenticated");
    expect(result.code).toBe("MEDIA_STORAGE_UNAVAILABLE");
    expect(result.category).toBe("server");
  });

  it("JOB_ASSIGNMENT_ROLE_NOT_ALLOWED (the real backend string) maps to ROLE_NOT_ALLOWED", () => {
    const result = mapProblemDetail(problem({ error_code: "JOB_ASSIGNMENT_ROLE_NOT_ALLOWED", status: 403 }), "authenticated");
    expect(result.code).toBe("ROLE_NOT_ALLOWED");
    expect(result.category).toBe("permission");
  });
});

describe("mapNetworkFailure", () => {
  it("classifies offline, timeout and cancellation distinctly", () => {
    expect(mapNetworkFailure("offline").code).toBe("NETWORK_OFFLINE");
    expect(mapNetworkFailure("timeout").code).toBe("NETWORK_TIMEOUT");
    expect(mapNetworkFailure("abort").code).toBe("REQUEST_CANCELLED");
  });

  it("a cancellation is never retryable and is categorized as cancelled, not an error", () => {
    const result = mapNetworkFailure("abort");
    expect(result.category).toBe("cancelled");
    expect(result.retryable).toBe(false);
  });
});

describe("mapUnknownFailure", () => {
  it("unparseable 5xx body -> SERVER_UNAVAILABLE, retryable", () => {
    const result = mapUnknownFailure(503);
    expect(result.code).toBe("SERVER_UNAVAILABLE");
    expect(result.retryable).toBe(true);
  });

  it("unparseable 4xx body -> UNKNOWN_API_ERROR, not retryable", () => {
    const result = mapUnknownFailure(400);
    expect(result.code).toBe("UNKNOWN_API_ERROR");
    expect(result.retryable).toBe(false);
  });
});
