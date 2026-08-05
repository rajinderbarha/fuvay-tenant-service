import { parseServerTimestamp, parseServerDate, isExpired } from "../dates";
import { DomainError } from "../errors";

describe("dates", () => {
  it("accepts a valid ISO timestamp", () => {
    expect(parseServerTimestamp("2026-08-01T09:30:00Z", "created_at")).toBe("2026-08-01T09:30:00Z");
  });

  it("rejects a malformed timestamp", () => {
    expect(() => parseServerTimestamp("not-a-date", "created_at")).toThrow(DomainError);
  });

  it("accepts a valid plain date", () => {
    expect(parseServerDate("2026-08-05", "scheduled_date")).toBe("2026-08-05");
  });

  it("rejects a timestamp passed where a plain date is expected", () => {
    expect(() => parseServerDate("2026-08-05T00:00:00Z", "scheduled_date")).toThrow(DomainError);
  });

  it("treats the server timestamp as authoritative for expiry, device clock only as the read side", () => {
    const expiresAt = parseServerTimestamp("2026-08-01T00:00:00Z", "expires_at");
    expect(isExpired(expiresAt, new Date("2026-08-02T00:00:00Z"))).toBe(true);
    expect(isExpired(expiresAt, new Date("2026-07-31T00:00:00Z"))).toBe(false);
  });
});
