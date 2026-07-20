import { isCancellationAvailable, isRescheduleAvailable } from "../cancellation-reschedule-availability";

/**
 * CUSTOMER-L5-15: asserts the verified-correct current state (no real,
 * customer-reachable cancellation/reschedule capability exists for the
 * canonical booking pipeline — see baseline-verification.md) rather than a
 * placeholder. If a future sprint closes the backend gap, these tests are
 * expected to be updated alongside the real implementation — not silently
 * left green while the function starts lying.
 */
describe("isCancellationAvailable", () => {
  it("is false for every known and unknown booking status — no real backend endpoint exists for the canonical booking", () => {
    for (const status of [
      "pending_assignment",
      "assigned",
      "scheduled",
      "on_the_way",
      "reached_site",
      "quote_required",
      "awaiting_customer_quote_approval",
      "service_started",
      "work_done",
      "completed",
      "cancelled",
      "some_future_status",
    ]) {
      expect(isCancellationAvailable(status)).toBe(false);
    }
  });
});

describe("isRescheduleAvailable", () => {
  it("is false for every known and unknown booking status — no real backend endpoint exists for the canonical booking", () => {
    for (const status of ["pending_assignment", "scheduled", "quote_required", "completed", "cancelled", "some_future_status"]) {
      expect(isRescheduleAvailable(status)).toBe(false);
    }
  });
});
