import { isActiveBookingStatus, isCompletedBookingStatus, matchesBookingListFilter } from "../bookingFilters";

describe("isActiveBookingStatus", () => {
  it("treats every real non-terminal status as active", () => {
    for (const status of ["pending_assignment", "assigned", "accepted", "scheduled", "in_progress"]) {
      expect(isActiveBookingStatus(status)).toBe(true);
    }
  });

  it("treats completed and cancelled as not active", () => {
    expect(isActiveBookingStatus("completed")).toBe(false);
    expect(isActiveBookingStatus("cancelled")).toBe(false);
  });
});

describe("isCompletedBookingStatus", () => {
  it("is true only for the real 'completed' status", () => {
    expect(isCompletedBookingStatus("completed")).toBe(true);
  });

  it("never classifies cancelled/rejected/failed as completed", () => {
    for (const status of ["cancelled", "rejected", "failed", "pending_assignment", "in_progress"]) {
      expect(isCompletedBookingStatus(status)).toBe(false);
    }
  });
});

describe("matchesBookingListFilter", () => {
  it("'all' matches every status", () => {
    for (const status of ["pending_assignment", "completed", "cancelled", "some_future_status"]) {
      expect(matchesBookingListFilter(status, "all")).toBe(true);
    }
  });

  it("'active' and 'completed' are mutually exclusive for every real status", () => {
    for (const status of ["pending_assignment", "assigned", "accepted", "scheduled", "in_progress", "completed", "cancelled"]) {
      const active = matchesBookingListFilter(status, "active");
      const completed = matchesBookingListFilter(status, "completed");
      expect(active && completed).toBe(false);
    }
  });
});
