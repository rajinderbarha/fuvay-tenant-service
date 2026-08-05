import { deriveBookingActivity } from "../bookingActivity";
import { parseServerTimestamp } from "../dates";

describe("deriveBookingActivity", () => {
  it("produces exactly one real event -- booking creation -- never a fabricated matching/notification step", () => {
    const createdAt = parseServerTimestamp("2026-08-01T09:41:00Z", "created_at");
    const events = deriveBookingActivity("b-1", "SB-2026-01", createdAt);
    expect(events).toHaveLength(1);
    expect(events[0].label).toContain("SB-2026-01");
    expect(events[0].timestamp).toBe(createdAt);
  });

  it("never mentions matching/provider/technician progress not backed by a real event", () => {
    const createdAt = parseServerTimestamp("2026-08-01T09:41:00Z", "created_at");
    const events = deriveBookingActivity("b-1", null, createdAt);
    const serialized = JSON.stringify(events);
    expect(serialized).not.toMatch(/matching started|provider notified|provider viewed|technician selected/i);
  });
});
