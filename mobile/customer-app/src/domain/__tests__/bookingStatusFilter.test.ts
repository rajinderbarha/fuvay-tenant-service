import { BOOKING_STATUS_FILTERS, bookingStatusFilterLabel } from "../bookingStatusFilter";

/**
 * Confirmed against the live database and engine source (2026-08-07):
 * `service_bookings.status` currently holds pending_assignment, accepted,
 * completed, assigned and on_the_way; `scheduled`, `in_progress` and
 * `cancelled` are written by final_records/home_service_assignment and
 * simply have no rows on this dataset yet.
 *
 * Offering a filter the backend cannot honour would return an empty list
 * with no explanation, so this list must stay a subset of real statuses.
 */
const REAL_BACKEND_STATUSES = new Set([
  "pending_assignment", "assigned", "accepted", "scheduled",
  "on_the_way", "in_progress", "completed", "cancelled",
]);

describe("booking status filters", () => {
  it("offers only statuses the backend actually writes", () => {
    for (const option of BOOKING_STATUS_FILTERS) {
      if (option.value === null) continue;
      expect(REAL_BACKEND_STATUSES.has(option.value)).toBe(true);
    }
  });

  it("includes on_the_way, which the older constants list omitted", () => {
    // Present in the DB and written by the execution engine's workflow --
    // leaving it out would make an en-route booking unfilterable.
    expect(BOOKING_STATUS_FILTERS.some(o => o.value === "on_the_way")).toBe(true);
  });

  it("leads with an explicit no-narrowing option", () => {
    expect(BOOKING_STATUS_FILTERS[0].value).toBeNull();
  });

  it("never shows a raw enum value to the customer", () => {
    for (const option of BOOKING_STATUS_FILTERS) {
      expect(option.label).not.toMatch(/_/);
    }
  });

  it("falls back to the no-narrowing label for an unrecognised value", () => {
    expect(bookingStatusFilterLabel("something_new")).toBe("Any status");
    expect(bookingStatusFilterLabel("completed")).toBe("Completed");
  });
});
