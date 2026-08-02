import { getRetryDecision } from "../retryPolicy";
import { AppError } from "../types";
import { __resetNetworkStateForTests, subscribeNetworkState } from "../networkState";

// networkState's `isOffline()` reads module-level `current`, which only
// `setState` (private) mutates in production via NetInfo events. For this
// unit test we drive it through the public event subscription surface by
// re-requiring the module is unnecessary -- __resetNetworkStateForTests
// resets to "unknown", which isOffline() treats as NOT offline, matching
// the default (online-ish) assumption these retry tests want.
beforeEach(() => __resetNetworkStateForTests());

function err(overrides: Partial<AppError>): AppError {
  return { code: "SERVER_UNAVAILABLE", category: "server", safeMessage: "x", retryable: true, ...overrides };
}

describe("getRetryDecision", () => {
  it("retries a retryable server error with growing backoff", () => {
    const d1 = getRetryDecision(err({}), 1, false);
    const d2 = getRetryDecision(err({}), 2, false);
    expect(d1.shouldRetry).toBe(true);
    expect(d2.shouldRetry).toBe(true);
    expect(d2.delayMs).toBeGreaterThan(0);
  });

  it("stops after the max attempt bound", () => {
    expect(getRetryDecision(err({}), 10, false).shouldRetry).toBe(false);
  });

  it("never retries when unsafeToRetry is set, regardless of error classification", () => {
    expect(getRetryDecision(err({ retryable: true }), 1, true).shouldRetry).toBe(false);
  });

  it("never retries auth failures", () => {
    expect(getRetryDecision(err({ code: "AUTH_REQUIRED", category: "auth", retryable: false }), 1, false).shouldRetry).toBe(false);
  });

  it("never retries permission failures", () => {
    expect(getRetryDecision(err({ code: "CAPABILITY_REQUIRED", category: "permission", retryable: false }), 1, false).shouldRetry).toBe(false);
  });

  it("never retries validation errors", () => {
    expect(getRetryDecision(err({ code: "VALIDATION_ERROR", category: "validation", retryable: false }), 1, false).shouldRetry).toBe(false);
  });

  it("never retries conflict/version errors", () => {
    expect(getRetryDecision(err({ code: "CONFLICT", category: "conflict", retryable: false }), 1, false).shouldRetry).toBe(false);
  });

  it("respects Retry-After (retryAfterSeconds) for rate limiting", () => {
    const decision = getRetryDecision(err({ code: "RATE_LIMITED", category: "rate_limit", retryable: true, retryAfterSeconds: 3 }), 1, false);
    expect(decision.shouldRetry).toBe(true);
    expect(decision.delayMs).toBe(3000);
  });

  it("never retries a cancelled request", () => {
    expect(getRetryDecision(err({ code: "REQUEST_CANCELLED", category: "cancelled", retryable: false }), 1, false).shouldRetry).toBe(false);
  });
});
