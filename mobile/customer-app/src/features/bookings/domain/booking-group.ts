import { resolveBookingStatus, type BookingStatusGroup } from "./booking-status-registry";

/** Centralized grouping used by the My Bookings list's Active/Past segmented filter (CUSTOMER-L5-12 §11) — never a frontend guess, always derived from the same status registry the detail screen uses. */
export function groupForStatus(status: string): BookingStatusGroup {
  return resolveBookingStatus(status).group;
}
