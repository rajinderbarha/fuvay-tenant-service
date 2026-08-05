import { isRetryableError, computeBackoffMs, getMaxAttempts } from "../retryPolicy";
import { DomainError } from "../../../domain/errors";

describe("retry policy", () => {
  it("allows retry for a network failure on a GET", () => {
    const err = new DomainError({ category: "NETWORK_UNAVAILABLE", diagnostic: "x" });
    expect(isRetryableError(err, "GET")).toBe(true);
  });

  it("never retries a POST regardless of error category (auth/mutations excluded)", () => {
    const err = new DomainError({ category: "NETWORK_UNAVAILABLE", diagnostic: "x" });
    expect(isRetryableError(err, "POST")).toBe(false);
  });

  it("never retries a validation failure even on GET", () => {
    const err = new DomainError({ category: "VALIDATION_FAILURE", diagnostic: "x" });
    expect(isRetryableError(err, "GET")).toBe(false);
  });

  it("produces bounded, increasing backoff", () => {
    const a1 = computeBackoffMs(1);
    const a3 = computeBackoffMs(3);
    expect(a1).toBeGreaterThan(0);
    expect(a3).toBeGreaterThanOrEqual(a1);
    expect(a3).toBeLessThanOrEqual(4000 * 1.2);
  });

  it("defaults to 3 max attempts", () => {
    expect(getMaxAttempts()).toBe(3);
  });
});
