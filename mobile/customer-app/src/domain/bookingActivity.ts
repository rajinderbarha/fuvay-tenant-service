import { ServerTimestamp } from "./dates";

export interface CustomerBookingEvent {
  id: string;
  label: string;
  timestamp: ServerTimestamp;
}

/**
 * No customer-visible activity/audit endpoint exists yet (confirmed this
 * task: `final_records` exposes no such route, and
 * `HomeServiceBookingDraftEvent`/final-records audit rows are internal-
 * only). Per spec section 6 ("derive only the booking-created event from
 * the canonical booking creation timestamp... label it clearly as booking
 * state, not a separate audit event"), this is the ONLY event this phase
 * may ever produce -- never "matching started"/"provider notified"/etc.
 */
export function deriveBookingActivity(bookingId: string, bookingNumber: string | null, createdAt: ServerTimestamp): CustomerBookingEvent[] {
  return [{
    id: `${bookingId}:created`,
    label: bookingNumber ? `Booking ${bookingNumber} was created.` : "Service request confirmed.",
    timestamp: createdAt,
  }];
}
