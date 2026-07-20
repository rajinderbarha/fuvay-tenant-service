import { parseBookingReviewStatus } from "../booking-review-status-schema";

describe("parseBookingReviewStatus", () => {
  it("accepts a real null-review response (no review submitted yet)", () => {
    expect(parseBookingReviewStatus({ review: null })).toEqual({ review: null });
  });

  it("accepts a real existing-review response", () => {
    const result = parseBookingReviewStatus({ review: { rating: 5, comment: "Great service", created_at: "2026-07-13T00:00:00Z" } });
    expect(result?.review?.rating).toBe(5);
  });

  it("rejects a malformed payload without throwing", () => {
    expect(parseBookingReviewStatus(null)).toBeNull();
    expect(parseBookingReviewStatus({})).toBeNull();
  });
});
