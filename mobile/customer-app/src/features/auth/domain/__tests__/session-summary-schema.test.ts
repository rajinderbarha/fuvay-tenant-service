import { sessionSummarySchema, parseSessionList } from "../session-summary-schema";

function session(overrides: Record<string, unknown> = {}) {
  return {
    session_id: "s1",
    device_name: "iPhone 15",
    device_type: "mobile",
    ip_address: "203.0.113.5",
    last_active_at: "2026-01-01T00:00:00",
    is_current: true,
    is_trusted: true,
    is_approved: true,
    created_at: "2025-12-01T00:00:00",
    ...overrides,
  };
}

describe("sessionSummarySchema", () => {
  it("accepts a valid session", () => {
    expect(sessionSummarySchema.safeParse(session()).success).toBe(true);
  });

  it("accepts a session with null device fields", () => {
    expect(sessionSummarySchema.safeParse(session({ device_name: null, device_type: null, ip_address: null })).success).toBe(true);
  });

  it("rejects a missing session_id", () => {
    const { session_id, ...rest } = session();
    expect(sessionSummarySchema.safeParse(rest).success).toBe(false);
  });

  it("rejects a non-boolean is_current", () => {
    expect(sessionSummarySchema.safeParse(session({ is_current: "yes" })).success).toBe(false);
  });
});

describe("parseSessionList", () => {
  it("keeps valid items and drops invalid ones without throwing", () => {
    const result = parseSessionList([session(), { garbage: true }]);
    expect(result.valid).toHaveLength(1);
    expect(result.droppedCount).toBe(1);
  });
});
