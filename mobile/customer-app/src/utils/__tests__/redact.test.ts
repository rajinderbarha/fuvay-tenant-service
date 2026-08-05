import { redact } from "../redact";

describe("redact", () => {
  it("redacts access tokens and OTPs", () => {
    const result = redact({ accessToken: "abc123", otp: "445566", note: "fine" });
    expect(result.accessToken).toBe("[redacted]");
    expect(result.otp).toBe("[redacted]");
    expect(result.note).toBe("fine");
  });

  it("redacts full addresses and message bodies", () => {
    const result = redact({ address: "221B Baker Street", message: "private text" });
    expect(result.address).toBe("[redacted]");
    expect(result.message).toBe("[redacted]");
  });

  it("redacts coordinates and media URLs", () => {
    const result = redact({ latitude: 12.9, longitude: 77.5, photoUrl: "https://x/y.jpg" });
    expect(result.latitude).toBe("[redacted]");
    expect(result.longitude).toBe("[redacted]");
    expect(result.photoUrl).toBe("[redacted]");
  });

  it("recurses into nested objects", () => {
    const result = redact({ user: { password: "hunter2", name: "Asha" } });
    expect((result.user as Record<string, unknown>).password).toBe("[redacted]");
    expect((result.user as Record<string, unknown>).name).toBe("Asha");
  });

  it("leaves non-sensitive fields untouched", () => {
    const result = redact({ jobId: "job-1", status: "on_the_way" });
    expect(result).toEqual({ jobId: "job-1", status: "on_the_way" });
  });
});
