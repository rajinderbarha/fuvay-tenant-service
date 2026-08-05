/**
 * Status-GROUPING is deliberately separate from `bookingStatus.ts`'s
 * receipt-stage adapter -- the stage adapter collapses several real raw
 * statuses (`accepted`/`scheduled`/`in_progress`/`completed`) into the
 * same safe `unknown` PRESENTATION stage (spec correction, Booking
 * Details phase), but My Bookings still needs to group by the REAL raw
 * `status` to answer "is this terminal or not" -- `unknown` alone cannot
 * answer that. Both modules read the same backend truth; they just answer
 * different questions.
 */
export type BookingListFilter = "active" | "completed" | "all";

/** Confirmed real terminal `ServiceBooking.status` values -- only these
 * two are true end-states across `final_records`/`home_service_assignment`
 * (a job/booking never leaves `completed`/`cancelled`). Everything else,
 * including `accepted`/`scheduled`/`in_progress` (real statuses the
 * status-adapter audit found are NOT yet fully proven in the UI), is
 * still active for grouping purposes -- an in-progress job is not done. */
const TERMINAL_BOOKING_STATUSES = new Set(["completed", "cancelled"]);

export function isActiveBookingStatus(rawStatus: string): boolean {
  return !TERMINAL_BOOKING_STATUSES.has(rawStatus);
}

export function isCompletedBookingStatus(rawStatus: string): boolean {
  // Per spec section 4: "Do not classify cancelled, rejected or failed
  // records as completed" -- only the real `completed` status counts,
  // never the broader terminal set.
  return rawStatus === "completed";
}

export function matchesBookingListFilter(rawStatus: string, filter: BookingListFilter): boolean {
  if (filter === "all") return true;
  if (filter === "active") return isActiveBookingStatus(rawStatus);
  return isCompletedBookingStatus(rawStatus);
}
