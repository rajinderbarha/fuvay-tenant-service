import { redact } from "../redaction";

describe("redact", () => {
  it("redacts an authorization header value", () => {
    const out = redact({ authorization: "Bearer secret-token" }) as Record<string, unknown>;
    expect(out.authorization).toBe("[redacted]");
  });

  it("redacts token, otp, password, secret, and session id fields", () => {
    const input = { accessToken: "a", otp: "123456", password: "hunter2", secret: "x", session_id: "sess_1" };
    const out = redact(input) as Record<string, unknown>;
    for (const key of Object.keys(input)) {
      expect(out[key]).toBe("[redacted]");
    }
  });

  it("redacts phone, email, and address-shaped fields", () => {
    const out = redact({ phone: "+911234567890", email: "user@example.com", address: "221B Baker Street" }) as Record<string, unknown>;
    expect(out.phone).toBe("[redacted]");
    expect(out.email).toBe("[redacted]");
    expect(out.address).toBe("[redacted]");
  });

  it("redacts latitude/longitude fields", () => {
    const out = redact({ lat: 12.9716, lng: 77.5946 }) as Record<string, unknown>;
    expect(out.lat).toBe("[redacted]");
    expect(out.lng).toBe("[redacted]");
  });

  it("recurses into nested objects and arrays", () => {
    const out = redact({ user: { password: "x" }, items: [{ token: "y" }] }) as any;
    expect(out.user.password).toBe("[redacted]");
    expect(out.items[0].token).toBe("[redacted]");
  });

  it("leaves non-sensitive fields untouched", () => {
    const out = redact({ bookingId: "bk_123", status: "confirmed" }) as Record<string, unknown>;
    expect(out.bookingId).toBe("bk_123");
    expect(out.status).toBe("confirmed");
  });

  it("does not infinitely recurse on deeply nested input", () => {
    let deep: unknown = { password: "x" };
    for (let i = 0; i < 20; i++) deep = { child: deep };
    expect(() => redact(deep)).not.toThrow();
  });
});
