import { redactHeaders, redactForLogging, maskToken } from "../redaction";

describe("redactHeaders", () => {
  it("redacts Authorization, Cookie and idempotency-key headers case-insensitively", () => {
    const result = redactHeaders({ Authorization: "Bearer abc123", Cookie: "session=x", "X-Idempotency-Key": "k1", "Content-Type": "application/json" });
    expect(result.Authorization).toBe("[REDACTED]");
    expect(result.Cookie).toBe("[REDACTED]");
    expect(result["X-Idempotency-Key"]).toBe("[REDACTED]");
    expect(result["Content-Type"]).toBe("application/json");
  });

  it("does not mutate the input object", () => {
    const input = { Authorization: "Bearer abc" };
    redactHeaders(input);
    expect(input.Authorization).toBe("Bearer abc");
  });
});

describe("redactForLogging", () => {
  it("deep-redacts sensitive keys at any nesting depth", () => {
    const result = redactForLogging({ user: { access_token: "abc", refresh_token: "def", nested: { otp: "123456" } }, safe: "ok" }) as any;
    expect(result.user.access_token).toBe("[REDACTED]");
    expect(result.user.refresh_token).toBe("[REDACTED]");
    expect(result.user.nested.otp).toBe("[REDACTED]");
    expect(result.safe).toBe("ok");
  });

  it("redacts within arrays", () => {
    const result = redactForLogging([{ password: "x" }, { safe: "y" }]) as any[];
    expect(result[0].password).toBe("[REDACTED]");
    expect(result[1].safe).toBe("y");
  });

  it("passes through primitives and null/undefined", () => {
    expect(redactForLogging(42)).toBe(42);
    expect(redactForLogging(null)).toBe(null);
    expect(redactForLogging(undefined)).toBe(undefined);
  });
});

describe("maskToken", () => {
  it("shows only the last 4 characters of a real token", () => {
    expect(maskToken("abcdefghijklmnop")).toBe("[REDACTED](mnop)");
  });

  it("fully redacts a short token", () => {
    expect(maskToken("short")).toBe("[REDACTED]");
  });

  it("handles a missing token", () => {
    expect(maskToken(null)).toBe("(none)");
    expect(maskToken(undefined)).toBe("(none)");
  });
});
