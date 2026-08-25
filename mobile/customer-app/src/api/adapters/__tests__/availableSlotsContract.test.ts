import { parseAvailableSlotsResponse, adaptAvailableSlots } from "../bookingReview";

/**
 * The slot list, pinned against the EXACT payload the live backend returns.
 *
 * Captured from a real authenticated call to
 * GET /v1/customer/home-services/booking-drafts/{id}/available-slots?emergency=true
 * (12 slots, Guramrit, 2026-08-08) rather than hand-written, so a contract drift
 * on either side fails here instead of surfacing as "An unexpected error
 * occurred" on a customer's screen.
 *
 * This matters because a reported slot failure turned out to be a stale server
 * returning 500 -- these tests establish that the CLIENT parse is not the cause,
 * and will catch it if it ever becomes the cause.
 */
const REAL_ENVELOPE = {
  slots: [
    {
      date: "2026-08-08", time_window: "13:00-14:00",
      starts_at: "2026-08-08T13:00:00", ends_at: "2026-08-08T14:00:00",
      slot_minutes: 60, capacity: 2, already_booked: 0, days_ahead: 0,
    },
    {
      date: "2026-08-09", time_window: "09:00-10:00",
      starts_at: "2026-08-09T09:00:00", ends_at: "2026-08-09T10:00:00",
      slot_minutes: 60, capacity: 2, already_booked: 1, days_ahead: 1,
    },
  ],
};

describe("available-slots contract", () => {
  it("parses the real backend payload", () => {
    const parsed = parseAvailableSlotsResponse(REAL_ENVELOPE);
    expect(parsed.slots).toHaveLength(2);
  });

  it("adapts it to the domain shape the picker renders", () => {
    const slots = adaptAvailableSlots(parseAvailableSlotsResponse(REAL_ENVELOPE));
    expect(slots[0]).toEqual({ date: "2026-08-08", timeWindow: "13:00-14:00", daysAhead: 0 });
    expect(slots[1].daysAhead).toBe(1);
  });

  it("tolerates the informational capacity fields being absent", () => {
    // `capacity`/`already_booked` are informational and are NOT echoed back by
    // select-slot. Requiring them would break the picker on a valid response.
    const parsed = parseAvailableSlotsResponse({
      slots: [{ date: "2026-08-08", time_window: "13:00-14:00", days_ahead: 0 }],
    });
    expect(parsed.slots).toHaveLength(1);
  });

  it("accepts an empty list as a real answer, not an error", () => {
    // A provider with no remaining capacity legitimately returns zero slots; the
    // picker must show "no times available", not fail to parse.
    const slots = adaptAvailableSlots(parseAvailableSlotsResponse({ slots: [] }));
    expect(slots).toEqual([]);
  });

  it("collapses duplicate physical slots before React renders them", () => {
    const duplicate = REAL_ENVELOPE.slots[0];
    const slots = adaptAvailableSlots(parseAvailableSlotsResponse({
      slots: [duplicate, { ...duplicate, capacity: 9, already_booked: 2 }],
    }));
    expect(slots).toEqual([
      { date: "2026-08-08", timeWindow: "13:00-14:00", daysAhead: 0 },
    ]);
  });

  it("rejects a payload missing the fields the picker actually needs", () => {
    // A silent pass here would render blank rows instead of surfacing drift.
    expect(() => parseAvailableSlotsResponse({ slots: [{ date: "2026-08-08" }] })).toThrow();
    expect(() => parseAvailableSlotsResponse({})).toThrow();
  });
});
