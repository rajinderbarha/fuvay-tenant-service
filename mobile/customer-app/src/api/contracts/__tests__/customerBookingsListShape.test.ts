import { bookingListResponseSchema } from "../customerBookings";

/**
 * Regression guard for a real outage of the My Bookings screen.
 *
 * The backend's list endpoint returned `{items, total, limit, offset}` with
 * NO `counts`, while this schema declares `counts` as required -- so the
 * client's parse threw on every load and the screen showed
 * "We couldn't load your bookings. Try again." even though the data was
 * fine. The fix added `counts` server-side (app/engines/final_records/
 * customer_router.py::list_my_bookings).
 *
 * These cases pin BOTH directions: the shipped shape must parse, and the
 * old shape must not silently start passing again.
 */
const base = {
  items: [],
  total: 0,
  limit: 20,
  offset: 0,
};

describe("My Bookings list response contract", () => {
  it("accepts the response shape the backend now returns", () => {
    const result = bookingListResponseSchema.safeParse({
      ...base,
      counts: { active: 6, completed: 0, all: 6 },
    });
    expect(result.success).toBe(true);
  });

  it("rejects a response missing `counts` (the shape that broke the screen)", () => {
    const result = bookingListResponseSchema.safeParse(base);
    expect(result.success).toBe(false);
  });

  it("requires all three bucket counts, not just the requested one", () => {
    // The tabs show totals for every bucket, so a partial counts object
    // must fail rather than render a wrong or blank tab count.
    const result = bookingListResponseSchema.safeParse({
      ...base,
      counts: { active: 6 },
    });
    expect(result.success).toBe(false);
  });
});
