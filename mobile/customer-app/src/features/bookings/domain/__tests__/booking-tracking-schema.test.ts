import { parseBookingTracking } from "../booking-tracking-schema";

describe("parseBookingTracking", () => {
  it("accepts a real timeline with the synthetic first entry plus real assignment events", () => {
    const result = parseBookingTracking({
      booking_number: "BK-20260713-000001",
      status: "assigned",
      assignment_status: "assigned",
      assignment_message: "Technician assigned.",
      timeline: [
        { event: "Booking confirmed", status: "confirmed" },
        { event: "Technician assigned.", event_type: "assignment_created", created_at: "2026-07-13T10:00:00Z" },
      ],
    });
    expect(result?.timeline).toHaveLength(2);
    expect(result?.timeline[0]?.created_at).toBeUndefined();
    expect(result?.timeline[1]?.event_type).toBe("assignment_created");
  });

  it("drops individually-invalid timeline rows rather than failing the whole screen", () => {
    const result = parseBookingTracking({
      booking_number: "BK-1",
      status: "assigned",
      assignment_status: "assigned",
      assignment_message: "x",
      timeline: [{ event: "Booking confirmed" }, { event_type: "missing_event_label" }],
    });
    expect(result?.timeline).toHaveLength(1);
    expect(result?.droppedCount).toBe(1);
  });

  it("accepts an empty timeline (a real, valid shape for a just-created booking with no job yet)", () => {
    const result = parseBookingTracking({
      booking_number: "BK-1",
      status: "pending_assignment",
      assignment_status: "unassigned",
      assignment_message: "x",
      timeline: [],
    });
    expect(result?.timeline).toEqual([]);
  });

  it("rejects a malformed envelope without throwing", () => {
    expect(parseBookingTracking(null)).toBeNull();
    expect(parseBookingTracking({})).toBeNull();
  });
});
